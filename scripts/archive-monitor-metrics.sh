#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/archive-monitor-metrics.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 482cc8814237de4ce880d45748395b16a4a754a5 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:38 %
#  %ccm_git_file_name: archive-monitor-metrics.sh %
#  %ccm_git_path: scripts/archive-monitor-metrics.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 14131 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# monitoring archive :: roll Uptime Kuma availability into Postgres for keeps
#
# WHAT IT DOES
#   Reads Prometheus (30 days of raw samples), aggregates each monitor into one
#   row per day plus one row per contiguous outage, and upserts into
#   ttdb_dev1's "monitoring" schema. Once Prometheus rolls past retention this
#   archive is the ONLY copy of that history, which is why it runs on a timer
#   and not on demand.
#
# WHERE THE AGGREGATION HAPPENS
#   Two range queries return every raw sample in the window. Postgres does the
#   per-day grouping, the response-time aggregates and the outage
#   gap-and-islands scan. One place to change a rule, and a missed night is
#   repairable by simply widening the window.
#
# IDEMPOTENT
#   Every write is an upsert keyed on (monitor_key, day) or
#   (monitor_key, started_at), so re-running a window changes nothing and
#   duplicates nothing. An outage still open at the end of the window is
#   rewritten, not duplicated, once the monitor recovers.
#
# THE METRIC NAMES ARE CONFIGURABLE BECAUSE THEY ARE NOT VERIFIED YET
#   Kuma's /metrics returns 401 without an API key, so neither metric names nor
#   labels could be confirmed against a live endpoint. Override M_STATUS and
#   M_RESP rather than editing PromQL here. The script FAILS LOUDLY when the
#   named metric has no series, rather than writing an empty day - a silent zero
#   is the failure mode this whole archive exists to prevent.
#
# USAGE
#   scripts/archive-monitor-metrics.sh                 # normal run
#   scripts/archive-monitor-metrics.sh --dry-run       # report, write nothing
#   scripts/archive-monitor-metrics.sh --lookback 7    # repair a longer gap
#
# ENVIRONMENT
#   PROM_URL       default http://127.0.0.1:3720 (loopback-only by design)
#   JOB            Prometheus job name for Kuma, default uptime-kuma
#   M_STATUS       status metric, default monitor_status
#   M_RESP         response-time metric, default monitor_response_time
#   LOOKBACK_DAYS  default 3
#   STEP           sample resolution for the scan, default 60s
#   PGDATABASE     default ttdb_dev1
#   KEEP_RUNS      archive_run rows to keep, default 90
#
# EXIT CODES
#   0 ok | 2 missing tool | 3 bad configuration or no series found
#   4 Prometheus query failed | 5 database write failed
# --- end of documentation ---
set -Eeuo pipefail

PROM_URL="${PROM_URL:-http://127.0.0.1:3720}"
JOB="${JOB:-uptime-kuma}"
M_STATUS="${M_STATUS:-monitor_status}"
M_RESP="${M_RESP:-monitor_response_time}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-3}"
STEP="${STEP:-60s}"
PGDATABASE="${PGDATABASE:-ttdb_dev1}"
KEEP_RUNS="${KEEP_RUNS:-90}"

DRY_RUN=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)      DRY_RUN=1; shift ;;
        --lookback)     LOOKBACK_DAYS="${2:?--lookback needs a day count}"; shift 2 ;;
        --lookback=*)   LOOKBACK_DAYS="${1#*=}"; shift ;;
        -h|--help)
            awk 'NR==1 { next }
                 /^# --- end of documentation ---$/ { exit }
                 { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"
            exit 0 ;;
        *) printf 'unknown argument: %s (try --help)\n' "$1" >&2; exit 3 ;;
    esac
done

case "$LOOKBACK_DAYS" in
    ''|*[!0-9]*) printf 'lookback must be a positive integer, got: %s\n' "$LOOKBACK_DAYS" >&2; exit 3 ;;
esac
[ "$LOOKBACK_DAYS" -ge 1 ] || { printf 'lookback must be >= 1\n' >&2; exit 3; }

case "$KEEP_RUNS" in
    ''|*[!0-9]*) printf 'KEEP_RUNS must be a positive integer, got: %s\n' "$KEEP_RUNS" >&2; exit 3 ;;
esac

log() { printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "${*:2}"; }
die() { local rc="$1"; shift; log ERROR "$*"; exit "$rc"; }

for tool in curl jq psql awk; do
    command -v "$tool" >/dev/null 2>&1 || die 2 "required tool not found: $tool"
done

START_MS="$(date +%s%3N)"

# Window: whole UTC days, ending at today 00:00. Whole days keep the daily
# rollup free of partial-day rows at the boundary.
WINDOW_END="$(date -u +%Y-%m-%dT00:00:00Z)"
WINDOW_START="$(date -u -d "${LOOKBACK_DAYS} days ago" +%Y-%m-%dT00:00:00Z)"
WINDOW_START_EPOCH="$(date -u -d "$WINDOW_START" +%s)"
WINDOW_END_EPOCH="$(date -u -d "$WINDOW_END" +%s)"

log INFO "archiving ${JOB} from ${WINDOW_START} to ${WINDOW_END} (${LOOKBACK_DAYS}d lookback, step ${STEP})"
if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "DRY RUN - nothing will be written"
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/tt-monitor-archive.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# prom_range <promql> <outfile>
# --data-urlencode everywhere: a label matcher contains quotes and braces, and
# an unencoded query silently returns a parse error instead of data.
prom_range() {
    local expr="$1" out="$2"
    curl -sS --max-time 60 -G "${PROM_URL}/api/v1/query_range" \
        --data-urlencode "query=${expr}" \
        --data-urlencode "start=${WINDOW_START_EPOCH}" \
        --data-urlencode "end=${WINDOW_END_EPOCH}" \
        --data-urlencode "step=${STEP}" > "$out" || \
        die 4 "Prometheus request failed for: ${expr}"
    local status
    status="$(jq -r '.status // "missing"' "$out" 2>/dev/null || echo unparseable)"
    [ "$status" = "success" ] || \
        die 4 "Prometheus returned status '${status}' for: ${expr} ($(jq -r '.error // empty' "$out" 2>/dev/null))"
}

SEL="{job=\"${JOB}\"}"

prom_range "${M_STATUS}${SEL}" "$WORK/status.json"
prom_range "${M_RESP}${SEL}"   "$WORK/resp.json"

# --- extract ----------------------------------------------------------------
# Identity: an explicit id label wins when Kuma exports one, then the name,
# then instance. The same precedence is used for every file, so the rows join.
jq -r '
    .data.result[]
    | [ (.metric.monitor_id // .metric.monitor_name // .metric.instance // "unknown"),
        (.metric.monitor_name // .metric.monitor_url // .metric.instance // "unknown"),
        (.metric.monitor_type // ""),
        (.metric.monitor_url // .metric.monitor_hostname // .metric.monitor_port // "") ]
    | @tsv' "$WORK/status.json" \
    | awk -F'\t' '!seen[$1]++' > "$WORK/dim.tsv"

# One row per sample: key, epoch seconds, value. tonumber? // empty drops the
# NaN/+Inf that Prometheus emits for a gap, so a hole in the data never becomes
# a zero - and never a blank field, which COPY would reject as a bad numeric.
jq -r '
    .data.result[]
    | (.metric.monitor_id // .metric.monitor_name // .metric.instance // "unknown") as $k
    | .values[]
    | (.[1] | tonumber? // empty) as $v
    | [$k, (.[0] | floor), $v] | @tsv' "$WORK/status.json" \
    | awk -F'\t' '!seen[$0]++' > "$WORK/status.tsv"

jq -r '
    .data.result[]
    | (.metric.monitor_id // .metric.monitor_name // .metric.instance // "unknown") as $k
    | .values[]
    | (.[1] | tonumber? // empty) as $v
    | [$k, (.[0] | floor), $v] | @tsv' "$WORK/resp.json" \
    | awk -F'\t' '!seen[$0]++' > "$WORK/resp.tsv" || : > "$WORK/resp.tsv"

if [ ! -s "$WORK/status.tsv" ]; then
    die 3 "no series for ${M_STATUS}${SEL} in Prometheus - is the Kuma scrape job configured and is the token working? (nothing written)"
fi

MONITORS="$(wc -l < "$WORK/dim.tsv")"
SAMPLES="$(wc -l < "$WORK/status.tsv")"
RESP_SAMPLES="$(wc -l < "$WORK/resp.tsv")"
log INFO "extracted ${SAMPLES} status samples for ${MONITORS} monitors, ${RESP_SAMPLES} response samples"

if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "dry run - first status samples:"
    head -3 "$WORK/status.tsv" | sed 's/^/    /'
    log INFO "dry run - first dimension rows:"
    head -3 "$WORK/dim.tsv" | sed 's/^/    /'
    log INFO "dry run - first response samples:"
    head -3 "$WORK/resp.tsv" | sed 's/^/    /'
    exit 0
fi

# --- write ------------------------------------------------------------------
# Postgres does every aggregate: the temp tables hold the raw samples, the
# inserts group by day, and the incident pass is a gap-and-islands scan.
cat > "$WORK/load.sql" <<SQL
BEGIN;

CREATE TEMP TABLE _dim (monitor_key text, name text, type text, target text)
    ON COMMIT DROP;
\copy _dim FROM '$WORK/dim.tsv' WITH (FORMAT text, DELIMITER E'\t')

CREATE TEMP TABLE _status (monitor_key text, epoch numeric, val numeric)
    ON COMMIT DROP;
\copy _status FROM '$WORK/status.tsv' WITH (FORMAT text, DELIMITER E'\t')

CREATE TEMP TABLE _resp (monitor_key text, epoch numeric, val numeric)
    ON COMMIT DROP;
\copy _resp FROM '$WORK/resp.tsv' WITH (FORMAT text, DELIMITER E'\t')

-- Dimension first: monitor_daily and monitor_incident carry an FK onto it.
INSERT INTO monitoring.monitor
    (monitor_key, name, type, target, first_seen, last_seen)
SELECT monitor_key, name, NULLIF(type, ''), NULLIF(target, ''), now(), now()
FROM _dim
ON CONFLICT (monitor_key) DO UPDATE
SET name      = EXCLUDED.name,
    type      = COALESCE(EXCLUDED.type, monitoring.monitor.type),
    target    = COALESCE(EXCLUDED.target, monitoring.monitor.target),
    last_seen = now();

WITH agg AS (
    SELECT monitor_key,
           (to_timestamp(epoch) AT TIME ZONE 'UTC')::date AS day,
           count(*)                                        AS checks,
           count(*) FILTER (WHERE val >= 1)                AS up_checks
    FROM _status
    GROUP BY 1, 2
), resp AS (
    SELECT monitor_key,
           (to_timestamp(epoch) AT TIME ZONE 'UTC')::date AS day,
           round(avg(val), 3) AS avg_ms,
           round(max(val), 3) AS max_ms
    FROM _resp
    GROUP BY 1, 2
)
INSERT INTO monitoring.monitor_daily
    (monitor_key, day, checks, up_checks, uptime_ratio, avg_response_ms, max_response_ms)
SELECT a.monitor_key, a.day, a.checks, a.up_checks,
       CASE WHEN a.checks = 0 THEN NULL
            ELSE round(a.up_checks::numeric / a.checks, 4) END,
       r.avg_ms, r.max_ms
FROM agg a
LEFT JOIN resp r USING (monitor_key, day)
ON CONFLICT (monitor_key, day) DO UPDATE
SET checks          = EXCLUDED.checks,
    up_checks       = EXCLUDED.up_checks,
    uptime_ratio    = EXCLUDED.uptime_ratio,
    avg_response_ms = EXCLUDED.avg_response_ms,
    max_response_ms = EXCLUDED.max_response_ms;

SQL

cat >> "$WORK/load.sql" <<SQL

-- Incidents. A contiguous down run is one island: number the up samples that
-- precede each down sample, and every down sample sharing that counter value
-- belongs to the same outage. ended_at is the first up sample after the run,
-- or NULL when the monitor was still down at the window end - the next run
-- closes it rather than duplicating it.
CREATE TEMP TABLE _island ON COMMIT DROP AS
WITH s AS (
    SELECT monitor_key, to_timestamp(epoch) AS ts, val
    FROM _status
), marked AS (
    SELECT monitor_key, ts, val, (val < 1) AS down,
           sum(CASE WHEN val >= 1 THEN 1 ELSE 0 END)
               OVER (PARTITION BY monitor_key ORDER BY ts, val
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS grp
    FROM s
), runs AS (
    SELECT monitor_key, grp, min(ts) AS started_at, max(ts) AS last_down
    FROM marked
    WHERE down
    GROUP BY monitor_key, grp
)
SELECT r.monitor_key,
       r.started_at,
       (SELECT min(m.ts)
          FROM marked m
         WHERE m.monitor_key = r.monitor_key
           AND m.ts > r.last_down
           AND NOT m.down) AS ended_at
FROM runs r;

INSERT INTO monitoring.monitor_incident
    (monitor_key, started_at, ended_at, duration_s, last_status, error)
SELECT monitor_key, started_at, ended_at,
       CASE WHEN ended_at IS NULL THEN NULL
            ELSE GREATEST(0, extract(epoch FROM ended_at - started_at)::int) END,
       'down', NULL
FROM _island
ON CONFLICT (monitor_key, started_at) DO UPDATE
SET ended_at    = EXCLUDED.ended_at,
    duration_s  = EXCLUDED.duration_s,
    last_status = EXCLUDED.last_status;

-- Run heartbeat: without this a dead timer looks identical to "nothing
-- interesting happened", which is the failure the archive exists to prevent.
INSERT INTO monitoring.archive_run
    (window_start, window_end, days_written, rows_written, incidents, duration_ms, note)
SELECT :'wstart'::timestamptz,
       :'wend'::timestamptz,
       (SELECT count(*) FROM (SELECT DISTINCT monitor_key,
                (to_timestamp(epoch) AT TIME ZONE 'UTC')::date FROM _status) d),
       (SELECT count(*) FROM _status),
       (SELECT count(*) FROM _island),
       :duration_ms::int,
       format('job=%s lookback=%sd step=%s', :'job', :'lookback', :'step')
ON CONFLICT (run_at) DO NOTHING;

DELETE FROM monitoring.archive_run
WHERE run_at NOT IN (
    SELECT run_at FROM monitoring.archive_run ORDER BY run_at DESC LIMIT :keep
);

COMMIT;
SQL

DURATION_MS=$(( $(date +%s%3N) - START_MS ))

psql -X -q -v ON_ERROR_STOP=1 \
    -d "$PGDATABASE" \
    -v wstart="$WINDOW_START" \
    -v wend="$WINDOW_END" \
    -v duration_ms="$DURATION_MS" \
    -v job="$JOB" \
    -v lookback="$LOOKBACK_DAYS" \
    -v step="$STEP" \
    -v keep="$KEEP_RUNS" \
    -f "$WORK/load.sql" || die 5 "database write failed for $PGDATABASE"

DURATION_MS=$(( $(date +%s%3N) - START_MS ))
log INFO "done in ${DURATION_MS}ms - ${SAMPLES} samples across ${MONITORS} monitors, window ${WINDOW_START} .. ${WINDOW_END}"
