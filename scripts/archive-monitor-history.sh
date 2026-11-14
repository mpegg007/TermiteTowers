#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/archive-monitor-history.sh@220 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 03cfbcbffe10343e01fd254727f3b434597b0d73 %
#  %ccm_git_commit_id: f539d83ae45e3bb2efbb8cabc31a866c4e672164 %
#  %ccm_git_commit_count: 220 %
#  %ccm_git_commit_date: 2026-11-13 19:11:14 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(monitoring): archive Kuma history from kuma.db into ttdb_dev1 %
#  %ccm_git_modify_date: 2026-11-13 19:11:14 %
#  %ccm_git_file_last_modified: 2026-11-13 19:09:14 %
#  %ccm_git_file_name: archive-monitor-history.sh %
#  %ccm_git_path: scripts/archive-monitor-history.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 18339 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# TermiteTowers - archive Uptime Kuma monitor history into Postgres.
#
# WHY kuma.db AND NOT PROMETHEUS
#   The first design scraped Kuma's /metrics into Prometheus and archived from
#   the Prometheus query API. Two problems killed it. Kuma's /metrics returns
#   401 and needs an API key, so the scrape job needed a bearer credential that
#   cannot live in the repo-mounted Prometheus config. And Prometheus can only
#   ever hold what it scraped, so the ~181 days of history already in kuma.db
#   would never reach Postgres. Reading kuma.db directly captures the backlog on
#   the first run and needs no token, no scrape job and no new container.
#
#   The cost, stated plainly: this is coupled to Kuma's SQLite schema, which
#   changes across 2.x releases. The column guards below turn a schema change
#   into a loud exit 3 instead of silently wrong rows.
#
# WHY IT NEVER OPENS THE LIVE DATABASE
#   /app/data/kuma.db is a live WAL database owned by the application and its
#   directory is root-owned. Instead of copying the db/-wal/-shm trio and hoping
#   the copy is not torn, this runs SQLite's own online backup API inside the
#   container (.backup), which produces one consistent file. That file is copied
#   out, integrity-checked, and every query runs against the copy. The live
#   database is only ever read by SQLite itself.
#
# WHAT IT WRITES
#   monitoring.monitor          dimension row per monitor, upserted
#   monitoring.monitor_daily    one row per monitor per UTC day, from stat_daily
#   monitoring.monitor_incident one row per contiguous down run, from heartbeat
#   monitoring.archive_run      one heartbeat row per run
#
#   Every write is an upsert keyed on its natural key, so re-running is
#   idempotent and never duplicates. Nothing is ever deleted from monitor_daily
#   or monitor_incident: Kuma prunes its own history at keepDataPeriodDays
#   (180 here), and the archive is what outlives that pruning.
#
# WHAT IT CANNOT RECOVER
#   stat_daily is a rollup, so daily uptime and response times backfill fully.
#   Outage boundaries come from the heartbeat table, which Kuma prunes down to
#   roughly two days plus a handful of flagged transitions - so incidents are
#   only captured from the run's own recency onward, and accumulate over time.
#   Outages older than that are not recoverable from any file Kuma still has.
#
# USAGE
#   scripts/archive-monitor-history.sh                 # snapshot, extract, load
#   scripts/archive-monitor-history.sh --dry-run       # report, write nothing
#   scripts/archive-monitor-history.sh --db /tmp/x.db  # use an existing snapshot
#   scripts/archive-monitor-history.sh --since 2026-05-01
#   scripts/archive-monitor-history.sh --dry-run --db x.db --extract-dir /tmp/out
#                                                      # keep the extracted TSVs
#                                                      # (used by tests/monitoring)
#
# ENVIRONMENT
#   PGDATABASE        default ttdb_dev1
#   KUMA_CONTAINER    default uptime-kuma-dev1
#   KUMA_DB           default /app/data/kuma.db (inside the container)
#   KEEP_RUNS         archive_run rows to keep, default 90
#
# EXIT CODES
#   0 ok | 2 missing tool | 3 bad configuration, unexpected Kuma schema, or no data
#   4 snapshot failed | 5 database write failed
# --- end of documentation ---
set -Eeuo pipefail

PGDATABASE="${PGDATABASE:-ttdb_dev1}"
KUMA_CONTAINER="${KUMA_CONTAINER:-uptime-kuma-dev1}"
KUMA_DB="${KUMA_DB:-/app/data/kuma.db}"
KEEP_RUNS="${KEEP_RUNS:-90}"

DRY_RUN=0
SNAPSHOT=""
SINCE=""
EXTRACT_DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)   DRY_RUN=1; shift ;;
        --db)        SNAPSHOT="${2:?--db needs a path}"; shift 2 ;;
        --db=*)      SNAPSHOT="${1#*=}"; shift ;;
        --since)     SINCE="${2:?--since needs YYYY-MM-DD}"; shift 2 ;;
        --since=*)   SINCE="${1#*=}"; shift ;;
        --extract-dir)  EXTRACT_DIR="${2:?--extract-dir needs a directory}"; shift 2 ;;
        --extract-dir=*) EXTRACT_DIR="${1#*=}"; shift ;;
        -h|--help)
            awk 'NR==1 { next }
                 /^# --- end of documentation ---$/ { exit }
                 { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"
            exit 0 ;;
        *) printf 'unknown argument: %s (try --help)\n' "$1" >&2; exit 3 ;;
    esac
done

case "$KEEP_RUNS" in
    ''|*[!0-9]*) printf 'KEEP_RUNS must be a positive integer, got: %s\n' "$KEEP_RUNS" >&2; exit 3 ;;
esac

if [ -n "$SINCE" ] && ! printf '%s' "$SINCE" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    printf -- '--since must be YYYY-MM-DD, got: %s\n' "$SINCE" >&2
    exit 3
fi

# Errors go to stderr and everything else to stdout, so a caller can capture the
# failure reason without parsing the progress log.
log() {
    local level="$1"
    shift
    local line
    line="$(printf '[%s] [%-5s] %s' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*")"
    if [ "$level" = "ERROR" ]; then
        printf '%s\n' "$line" >&2
    else
        printf '%s\n' "$line"
    fi
}
die() { local rc="$1"; shift; log ERROR "$*"; exit "$rc"; }

for tool in sqlite3 psql awk date; do
    command -v "$tool" >/dev/null 2>&1 || die 2 "required tool not found: $tool"
done

# docker is only needed when this script takes its own snapshot.
if [ -z "$SNAPSHOT" ]; then
    command -v docker >/dev/null 2>&1 || die 2 "required tool not found: docker"
fi

START_MS="$(date +%s%3N)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/tt-monitor-archive.XXXXXX")"
IN_CONTAINER="/tmp/tt-monitor-archive-$$.db"

cleanup() {
    # Remove the container-side snapshot even on failure, so a failed run does
    # not leave a 70 MB file in the container's write layer.
    if [ "$TAKE_SNAPSHOT" -eq 1 ]; then
        docker exec "$KUMA_CONTAINER" rm -f "$IN_CONTAINER" >/dev/null 2>&1 || true
    fi
    rm -rf "$WORK"
}
TAKE_SNAPSHOT=0
trap cleanup EXIT

log INFO "archiving Kuma monitor history from ${KUMA_CONTAINER}:${KUMA_DB} into ${PGDATABASE}"
if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "DRY RUN - nothing will be written"
fi

# --- snapshot ---------------------------------------------------------------
if [ -z "$SNAPSHOT" ]; then
    TAKE_SNAPSHOT=1
    SNAPSHOT="$WORK/kuma.db"
    log INFO "taking a consistent online backup inside ${KUMA_CONTAINER}"
    docker exec "$KUMA_CONTAINER" sqlite3 "$KUMA_DB" ".backup '${IN_CONTAINER}'" \
        || die 4 "sqlite3 .backup failed in ${KUMA_CONTAINER}; is the container running?"
    docker cp -q "${KUMA_CONTAINER}:${IN_CONTAINER}" "$SNAPSHOT" \
        || die 4 "docker cp from ${KUMA_CONTAINER} failed"
fi

[ -s "$SNAPSHOT" ] || die 3 "snapshot is missing or empty: ${SNAPSHOT}"

# A torn or corrupt copy must never reach Postgres. This is cheap and it is the
# only thing standing between a bad snapshot and wrong history.
integrity="$(sqlite3 "$SNAPSHOT" 'PRAGMA integrity_check;' 2>&1)" || \
    die 3 "cannot open ${SNAPSHOT}: ${integrity}"
[ "$integrity" = "ok" ] || die 3 "integrity_check on ${SNAPSHOT} returned: ${integrity}"
log INFO "snapshot integrity ok ($(du -h "$SNAPSHOT" | cut -f1))"

# --- schema guards ----------------------------------------------------------
# Kuma's schema moves between 2.x releases. Assert the tables AND the columns we
# read, so a release that renames something stops this script instead of
# producing empty or wrong rows.
for table in monitor stat_daily heartbeat; do
    present="$(sqlite3 "$SNAPSHOT" \
        "select count(*) from sqlite_master where type='table' and name='${table}';")"
    [ "$present" = "1" ] || die 3 "kuma.db has no table '${table}' - unexpected Kuma version"
done

need_cols() {
    local table="$1"; shift
    local want="$*"
    local found
    for col in $want; do
        found="$(sqlite3 "$SNAPSHOT" \
            "select count(*) from pragma_table_info('${table}') where name='${col}';")"
        [ "$found" = "1" ] || die 3 "kuma.db table '${table}' has no column '${col}' - unexpected Kuma version"
    done
}
need_cols monitor   id name url hostname port type interval
need_cols stat_daily monitor_id timestamp ping ping_max up down
need_cols heartbeat  monitor_id status time end_time msg

# --- extract ----------------------------------------------------------------
# Text fields are stripped of tabs and newlines: the load is TSV, and one tab in
# a monitor name would silently shift every column after it.
#
# sanitise wraps a column reference in those replaces. It must be expanded by the
# shell, not by SQLite's printf(): printf('replace(...)', x) would return the
# literal text "replace(..." with x substituted, and the sanitisation would
# silently not happen.
SANITISE="replace(replace(replace(coalesce(%s,''), char(9), ' '), char(10), ' '), char(13), ' ')"
sanitise() { printf "$SANITISE" "$1"; }

gen_where=""
if [ -n "$SINCE" ]; then
    gen_where="and date(datetime(s.timestamp, 'unixepoch')) >= '${SINCE}'"
fi

# Dimension. target prefers a real URL; Kuma stores a bare 'https://' filler on
# ping/dns monitors, which is not a target and must not be copied as one.
sqlite3 -tabs "$SNAPSHOT" "
    select 'kuma:' || m.id,
           $(sanitise 'm.name') as name,
           coalesce(m.type, '') as type,
           coalesce(
               nullif(nullif(nullif(coalesce(m.url, ''), ''), 'https://'), 'http://'),
               case when m.hostname is not null and trim(m.hostname) <> '' and m.port is not null
                    then m.hostname || ':' || m.port
                    else nullif(trim(coalesce(m.hostname, '')), '') end,
               ''
           ) as target
    from monitor m
    order by m.id;" > "$WORK/dims.tsv"

# Daily rollups. timestamp is epoch SECONDS in kuma.db (verified on 2.5.11), not
# milliseconds - dividing by 1000 puts every row in January 1970. datetime(...)
# without a modifier yields UTC, which is the day boundary this schema promises.
# Rows where up+down is 0 carry no measurement and are skipped rather than
# written as a fake zero-uptime day.
sqlite3 -tabs "$SNAPSHOT" "
    select 'kuma:' || s.monitor_id,
           date(datetime(s.timestamp, 'unixepoch')) as day,
           s.up + s.down as checks,
           s.up as up_checks,
           round(s.ping, 3) as avg_ms,
           round(s.ping_max, 3) as max_ms
    from stat_daily s
    where s.timestamp is not null
      and (s.up + s.down) > 0
      ${gen_where}
    order by s.monitor_id, s.timestamp;" > "$WORK/daily.tsv"

# Incidents. Kuma's own "incident" table is status-page posts, not outages, so
# boundaries come from heartbeat.status: 0 is down and 2 is pending-retry, and
# stat_daily counts both toward its down total, so both are treated as down here
# to stay consistent with the daily rows. end_time is when that check cleared.
#
# Consecutive down checks are one outage, not many. The run boundary is a
# RECOVERY, not a time gap: up_before counts how many status=1 checks preceded
# each row, so every down row sharing an up_before value sits in the same
# uninterrupted run. A time-gap threshold would merge two outages separated by a
# brief successful check, which is exactly the case worth keeping distinct.
#
# Rows with a NULL end_time are kept: that is a check still in flight, and the
# schema represents it as an open incident (ended_at NULL) that a later run
# closes.
sqlite3 -tabs "$SNAPSHOT" "
    with seq as (
        select h.monitor_id,
               h.time,
               h.end_time,
               h.status,
               $(sanitise 'h.msg') as msg,
               sum(case when h.status = 1 then 1 else 0 end)
                   over (partition by h.monitor_id order by h.time
                         rows between unbounded preceding and current row) as up_before
        from heartbeat h
    ),
    islands as (
        select * from seq where status in (0, 2)
    ),
    agg as (
        select monitor_id, up_before,
               min(time) as started_at,
               max(end_time) as ended_at
        from islands
        group by monitor_id, up_before
    ),
    latest as (
        select monitor_id, up_before, msg,
               row_number() over (partition by monitor_id, up_before order by time desc) as rn
        from islands
    )
    select 'kuma:' || a.monitor_id,
           a.started_at || '+00',
           case when a.ended_at is null then '' else a.ended_at || '+00' end,
           substr(coalesce(l.msg, ''), 1, 500)
    from agg a
    join latest l on l.monitor_id = a.monitor_id and l.up_before = a.up_before and l.rn = 1
    order by a.monitor_id, a.started_at;" > "$WORK/incidents.tsv"

# --- guards ----------------------------------------------------------------
# A run that finds nothing must fail rather than record an empty heartbeat: the
# whole point of archive_run is that a silent failure is visible in the data.
[ -s "$WORK/dims.tsv" ] || die 3 "no monitor rows in the snapshot - is this a Kuma database?"
[ -s "$WORK/daily.tsv" ] || die 3 "no stat_daily rows to archive${SINCE:+ since ${SINCE}}; nothing written"

MONITORS="$(wc -l < "$WORK/dims.tsv")"
DAILY="$(wc -l < "$WORK/daily.tsv")"
INCIDENTS="$(wc -l < "$WORK/incidents.tsv")"
# No head -1 here: an early-exiting reader sends SIGPIPE to sort, and pipefail
# turns that into exit 141. sed reads to end of input.
FIRST_DAY="$(cut -f2 "$WORK/daily.tsv" | sort -u | sed -n '1p')"
LAST_DAY="$(cut -f2 "$WORK/daily.tsv" | sort -u | sed -n '$p')"
DAYS="$(cut -f2 "$WORK/daily.tsv" | sort -u | wc -l)"

log INFO "extracted ${DAILY} daily rows across ${DAYS} days (${FIRST_DAY} .. ${LAST_DAY}) for ${MONITORS} monitors"
log INFO "extracted ${INCIDENTS} incident rows from heartbeat"

# Test hook: keep the prepared TSVs so a test can assert exact values instead of
# re-implementing these queries. Only reached for callers that ask for it.
if [ -n "$EXTRACT_DIR" ]; then
    mkdir -p "$EXTRACT_DIR"
    cp "$WORK/dims.tsv" "$WORK/daily.tsv" "$WORK/incidents.tsv" "$EXTRACT_DIR"/
    log INFO "extracted TSVs kept in ${EXTRACT_DIR}"
fi

if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "dry run - daily rows per monitor:"
    cut -f1 "$WORK/daily.tsv" | sort | uniq -c | sed 's/^/    /'
    exit 0
fi

# --- write ------------------------------------------------------------------
# All aggregation is done in SQLite above; this loads prepared TSVs and upserts.
# \copy is used rather than COPY WITH STDIN so psql executes the file directly.
DURATION_MS=$(( $(date +%s%3N) - START_MS ))
NOTE="source=kuma.db container=${KUMA_CONTAINER} monitors=${MONITORS} days=${DAYS} incidents=${INCIDENTS}"

cat > "$WORK/load.sql" <<SQL
BEGIN;

CREATE TEMP TABLE _dim (monitor_key text, name text, type text, target text)
    ON COMMIT DROP;
\copy _dim FROM '${WORK}/dims.tsv' WITH (FORMAT text, DELIMITER E'\t')

CREATE TEMP TABLE _daily (monitor_key text, day date, checks integer,
                          up_checks integer, avg_ms numeric, max_ms numeric)
    ON COMMIT DROP;
\copy _daily FROM '${WORK}/daily.tsv' WITH (FORMAT text, DELIMITER E'\t')

CREATE TEMP TABLE _inc (monitor_key text, started_at timestamptz,
                        ended_at timestamptz, error text)
    ON COMMIT DROP;
\copy _inc FROM '${WORK}/incidents.tsv' WITH (FORMAT text, DELIMITER E'\t')

-- Dimension first: both fact tables carry an FK onto it.
INSERT INTO monitoring.monitor
    (monitor_key, name, type, target, first_seen, last_seen)
SELECT monitor_key, name, nullif(type, ''), nullif(target, ''), now(), now()
FROM _dim
ON CONFLICT (monitor_key) DO UPDATE
SET name      = EXCLUDED.name,
    type      = COALESCE(EXCLUDED.type, monitoring.monitor.type),
    target    = COALESCE(EXCLUDED.target, monitoring.monitor.target),
    last_seen = now();

-- uptime_ratio is computed here so the NULL-means-no-checks rule lives in one
-- place: a gap in monitoring is not an outage.
INSERT INTO monitoring.monitor_daily
    (monitor_key, day, checks, up_checks, uptime_ratio, avg_response_ms, max_response_ms)
SELECT monitor_key, day, checks, up_checks,
       CASE WHEN checks = 0 THEN NULL
            ELSE round(up_checks::numeric / checks, 4) END,
       avg_ms, max_ms
FROM _daily
ON CONFLICT (monitor_key, day) DO UPDATE
SET checks          = EXCLUDED.checks,
    up_checks       = EXCLUDED.up_checks,
    uptime_ratio    = EXCLUDED.uptime_ratio,
    avg_response_ms = EXCLUDED.avg_response_ms,
    max_response_ms = EXCLUDED.max_response_ms;

INSERT INTO monitoring.monitor_incident
    (monitor_key, started_at, ended_at, duration_s, last_status, error)
SELECT monitor_key, started_at, ended_at,
       CASE WHEN ended_at IS NULL THEN NULL
            ELSE GREATEST(0, extract(epoch FROM ended_at - started_at)::int) END,
       'down', nullif(error, '')
FROM _inc
ON CONFLICT (monitor_key, started_at) DO UPDATE
SET ended_at    = EXCLUDED.ended_at,
    duration_s  = EXCLUDED.duration_s,
    last_status = EXCLUDED.last_status,
    error       = EXCLUDED.error;

INSERT INTO monitoring.archive_run
    (window_start, window_end, days_written, rows_written, incidents, duration_ms, note)
SELECT (SELECT min(day)::timestamptz FROM _daily),
       (SELECT (max(day) + 1)::timestamptz FROM _daily),
       (SELECT count(DISTINCT day) FROM _daily),
       (SELECT count(*) FROM _daily),
       (SELECT count(*) FROM _inc),
       :duration_ms::int,
       :'note'
ON CONFLICT (run_at) DO NOTHING;

DELETE FROM monitoring.archive_run
WHERE run_at NOT IN (
    SELECT run_at FROM monitoring.archive_run ORDER BY run_at DESC LIMIT :keep
);

COMMIT;
SQL

psql -X -q -v ON_ERROR_STOP=1 \
    -d "$PGDATABASE" \
    -v duration_ms="$DURATION_MS" \
    -v note="$NOTE" \
    -v keep="$KEEP_RUNS" \
    -f "$WORK/load.sql" || die 5 "database write failed for ${PGDATABASE}"

DURATION_MS=$(( $(date +%s%3N) - START_MS ))
log INFO "done in ${DURATION_MS}ms - ${DAILY} daily rows (${FIRST_DAY} .. ${LAST_DAY}), ${INCIDENTS} incidents, ${MONITORS} monitors"
