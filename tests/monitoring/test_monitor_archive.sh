#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/monitoring/test_monitor_archive.sh@220 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 9ca5c8f8a5d946a3023d516c457d0ab39fa03959 %
#  %ccm_git_commit_id: f539d83ae45e3bb2efbb8cabc31a866c4e672164 %
#  %ccm_git_commit_count: 220 %
#  %ccm_git_commit_date: 2026-11-13 19:11:14 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(monitoring): archive Kuma history from kuma.db into ttdb_dev1 %
#  %ccm_git_modify_date: 2026-11-13 19:11:14 %
#  %ccm_git_file_last_modified: 2026-11-13 16:33:06 %
#  %ccm_git_file_name: test_monitor_archive.sh %
#  %ccm_git_path: tests/monitoring/test_monitor_archive.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 8779 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Contract tests for scripts/archive-monitor-history.sh.
#
# WHAT IS BEING TESTED
#   The extraction rules that turn kuma.db into the monitoring schema's rows:
#     - stat_daily.timestamp is epoch SECONDS, so a wrong divisor shifts every
#       day into January 1970;
#     - a day with up+down = 0 is a gap and must be skipped, not written as a
#       fake zero-uptime day;
#     - consecutive down checks are ONE outage, and an intervening successful
#       check starts a new one;
#     - status 2 (pending retry) counts as down, because stat_daily counts it in
#       its down total;
#     - a Kuma schema that lacks an expected column stops the script (exit 3)
#       instead of writing silent nonsense.
#
# WHY NO POSTGRES AND NO DOCKER
#   Every assertion runs through --dry-run --extract-dir against a fixture
#   sqlite database. The load half (upserts, FK order, idempotency) is verified
#   against the live database by the runbook procedure, not here; a test that
#   needed a real cluster would not run in CI.
#
# Usage: bash tests/monitoring/test_monitor_archive.sh
# Exit:  0 all checks pass, 1 at least one failure
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/archive-monitor-history.sh"
SERVICE="${REPO_ROOT}/infra/systemd/tt-monitor-archive.service"
TIMER="${REPO_ROOT}/infra/systemd/tt-monitor-archive.timer"

pass=0
fail=0

ok()   { pass=$((pass + 1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail + 1)); printf '  FAIL %s\n' "$1"; }

if ! command -v sqlite3 >/dev/null 2>&1; then
    printf 'sqlite3 is required to run these tests\n' >&2
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/tt-monitor-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# expect_row <tsv> <pipe separated expected fields> <label>
# Compares only the leading fields named in <expected>, so a caller can assert
# the columns it cares about without pinning float formatting it does not.
expect_row() {
    local file="$1" want="$2" label="$3"
    if [ ! -f "$file" ]; then
        bad "$label (missing $(basename "$file"))"
        return
    fi
    if awk -F'\t' -v want="$want" '
        BEGIN { n = split(want, w, "|") }
        {
            okf = 1
            for (i = 1; i <= n; i++) if ($i != w[i]) okf = 0
            if (okf) { found = 1; exit 0 }
        }
        END { exit(found ? 0 : 1) }' "$file"; then
        ok "$label"
    else
        bad "$label"
    fi
}

expect_lines() {
    local file="$1" want="$2" label="$3"
    if [ -f "$file" ] && [ "$(wc -l < "$file")" -eq "$want" ]; then
        ok "$label"
    else
        bad "$label (want ${want}, got $( [ -f "$file" ] && wc -l < "$file" || echo missing ))"
    fi
}

make_fixture() {
    rm -f "$1"
    sqlite3 "$1" <<'SQL'
create table monitor (
    id integer primary key, name text, url text, hostname text, port integer,
    type text, interval integer
);
create table stat_daily (
    monitor_id integer not null, timestamp integer not null, ping float not null,
    ping_max float not null default 0, up integer not null, down integer not null
);
create table heartbeat (
    monitor_id integer not null, status integer not null, time datetime not null,
    end_time datetime, msg text
);

-- monitor 1 carries a tab in its name, which must not reach the TSV.
insert into monitor values
    (1, 'web' || char(9) || 'tier', 'https://example.com', '', null, 'http', 60),
    (2, 'router', 'https://', '10.0.0.1', 22, 'ping', 60);

-- 2026-11-10 measured, 2026-11-11 clean, 2026-11-12 no checks at all.
insert into stat_daily values
    (1, strftime('%s','2026-11-10 00:00:00'), 10.5, 22.0, 1430, 10),
    (1, strftime('%s','2026-11-11 00:00:00'), 12.25, 30.0, 1440, 0),
    (1, strftime('%s','2026-11-12 00:00:00'), 0, 0, 0, 0),
    (2, strftime('%s','2026-11-10 00:00:00'), 1.5, 8.0, 1439, 1);

-- Two outages separated by a recovery, then two consecutive down checks with no
-- recovery between them. The last one is status 2 (pending) and carries the
-- message that must win for that island.
insert into heartbeat values
    (1, 1, '2026-11-13 09:59:00.000', '2026-11-13 09:59:30.000', 'ok'),
    (1, 0, '2026-11-13 10:00:00.000', '2026-11-13 10:00:30.000', 'first outage'),
    (1, 1, '2026-11-13 10:01:00.000', '2026-11-13 10:01:30.000', 'ok'),
    (1, 0, '2026-11-13 10:02:00.000', '2026-11-13 10:02:30.000', 'second outage, part one'),
    (1, 2, '2026-11-13 10:03:00.000', '2026-11-13 10:03:30.000', 'second outage, part two');
SQL
}

run_extract() {
    local db="$1" out="$2"
    shift 2
    rm -rf "$out"
    bash "$SCRIPT" --db "$db" --dry-run --extract-dir "$out" "$@" >"$WORK/stdout" 2>"$WORK/stderr"
}

printf '\n== files and units ==\n'
if [ -x "$SCRIPT" ]; then ok "archiver is executable"; else bad "archiver is executable"; fi
if [ -f "$SERVICE" ]; then ok "systemd service exists"; else bad "systemd service exists"; fi
if [ -f "$TIMER" ]; then ok "systemd timer exists"; else bad "systemd timer exists"; fi
if [ -f "$SERVICE" ] && grep -q "ExecStart=.*archive-monitor-history.sh" "$SERVICE"; then
    ok "service runs the archiver"
else
    bad "service runs the archiver"
fi
if [ -f "$TIMER" ] && grep -q 'OnCalendar=\*-\*-\* 05:15:00' "$TIMER"; then
    ok "timer fires at 05:15"
else
    bad "timer fires at 05:15"
fi

printf '\n== extraction ==\n'
make_fixture "$WORK/kuma.db"
OUT="$WORK/out"
if run_extract "$WORK/kuma.db" "$OUT"; then
    ok "extract exits 0"
else
    bad "extract exits 0 ($(cat "$WORK/stderr" 2>/dev/null))"
fi

expect_lines "$OUT/daily.tsv" 3 "three daily rows, the zero-check day skipped"
expect_row "$OUT/daily.tsv" "kuma:1|2026-11-10|1440|1430|10.5|22.0" \
    "epoch seconds map to the right day; checks is up+down"
expect_row "$OUT/daily.tsv" "kuma:1|2026-11-11|1440|1440" "clean day recorded as all up"
expect_row "$OUT/daily.tsv" "kuma:2|2026-11-10|1440|1439" "second monitor recorded"

printf '\n== dimensions ==\n'
expect_row "$OUT/dims.tsv" "kuma:1|web tier|http|https://example.com" \
    "tab stripped from the name; real URL kept as target"
expect_row "$OUT/dims.tsv" "kuma:2|router|ping|10.0.0.1:22" \
    "bare https:// filler replaced by hostname:port"

printf '\n== incidents ==\n'
expect_lines "$OUT/incidents.tsv" 2 "a recovery splits outages; consecutive checks merge"
expect_row "$OUT/incidents.tsv" "kuma:1|2026-11-13 10:00:00.000+00|2026-11-13 10:00:30.000+00|first outage" \
    "first outage bounded by its own check"
expect_row "$OUT/incidents.tsv" "kuma:1|2026-11-13 10:02:00.000+00|2026-11-13 10:03:30.000+00|second outage, part two" \
    "status 2 counted as down; island ends at the last check; latest message wins"

printf '\n== --since ==\n'
if run_extract "$WORK/kuma.db" "$OUT" --since 2026-11-11; then
    expect_lines "$OUT/daily.tsv" 1 "--since keeps only later days"
    expect_row "$OUT/daily.tsv" "kuma:1|2026-11-11|1440|1440" "--since keeps the right row"
else
    bad "--since run exits 0 ($(cat "$WORK/stderr" 2>/dev/null))"
fi

printf '\n== guards ==\n'
make_fixture "$WORK/empty.db"
sqlite3 "$WORK/empty.db" 'delete from stat_daily;'
if run_extract "$WORK/empty.db" "$WORK/out-empty"; then
    bad "no stat_daily rows exits 3"
else
    if [ "$?" -eq 3 ]; then ok "no stat_daily rows exits 3"; else bad "no stat_daily rows exits 3"; fi
fi

# ping_max is present so that "down" is genuinely the first column the guard
# finds missing, which keeps the assertion below about the right column.
sqlite3 "$WORK/short.db" <<'SQL'
create table monitor (id integer primary key, name text, url text, hostname text, port integer, type text, interval integer);
create table stat_daily (monitor_id integer, timestamp integer, ping float, ping_max float, up integer);
create table heartbeat (monitor_id integer, status integer, time datetime, end_time datetime, msg text);
insert into monitor values (1,'m','https://','',null,'ping',60);
SQL
if run_extract "$WORK/short.db" "$WORK/out-short"; then
    bad "missing stat_daily column exits 3"
else
    if [ "$?" -eq 3 ] && grep -q "no column 'down'" "$WORK/stderr"; then
        ok "missing stat_daily column exits 3 and names the column"
    else
        bad "missing stat_daily column exits 3 and names the column"
    fi
fi

printf '\n== summary ==\n'
printf '  %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
