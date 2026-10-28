#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/restore-tthealth.sh@189 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 24eb1c3c855121b7b020e5cf21572efc08e3a34d %
#  %ccm_git_commit_id: e4f75cef3cd2cd1877f825652b221973b909b6a1 %
#  %ccm_git_commit_count: 189 %
#  %ccm_git_commit_date: 2026-10-28 12:07:18 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 5 - rotate, rewrap, audit, prune, restore wrapper %
#  %ccm_git_modify_date: 2026-10-28 12:07:19 %
#  %ccm_git_file_last_modified: 2026-10-28 12:06:38 %
#  %ccm_git_file_name: restore-tthealth.sh %
#  %ccm_git_path: infra/backups/scripts/restore-tthealth.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4525 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# --- usage:begin
# restore-tthealth.sh :: decrypt a tthealth dump and hand it to pg_restore.
#
#     restore-tthealth.sh --list <file.dump.age>            # inspect, no DB writes
#     restore-tthealth.sh --to tthealth_dev1 <file.dump.age>
#     restore-tthealth.sh --to scratch_db --gen legacy <file.dump.age>
#
# The tier/generation come from the filename (...__health-2026Q4.dump.age).
# Pre-cutover dumps carry no suffix: they are generation "legacy".
#
# The DEK is unwrapped into /dev/shm, used once and shredded; the dump is streamed
# into pg_restore, so no plaintext copy is ever written. The master identity is
# typed at the prompt and never stored.
#
# Needs: age, pg_restore, and the tt-keys.sh sitting next to this script.
#
# EXIT CODES
#   0 ok | 2 missing tool | 3 bad arguments or configuration
#   4 could not unwrap the DEK | 5 decrypt/restore failed
# --- usage:end
set -Eeuo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TT_KEYS="$SELF_DIR/tt-keys.sh"

MODE=""
TARGET_DB=""
GEN=""
TIER=""
FILE=""

log() { printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "${*:2}"; }
die() { printf '[%s] [ERROR] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >&2; exit "${2:-3}"; }

usage() {
    sed -n '/^# --- usage:begin$/,/^# --- usage:end$/p' "${BASH_SOURCE[0]}" \
        | sed '1d;$d' \
        | sed 's/^# \{0,1\}//'
}

KEY=""
# Scratch file for unlock diagnostics: quiet on success, full detail on failure.
WORK_ERR="$(mktemp "${TMPDIR:-/tmp}/tt-restore.XXXXXX")"
cleanup() {
    rm -f "$WORK_ERR"
    if [ -n "$KEY" ] && [ -f "$KEY" ]; then
        shred -u "$KEY" 2>/dev/null || rm -f "$KEY"
        rmdir "$(dirname "$KEY")" 2>/dev/null || true
    fi
}
trap cleanup EXIT

while [ $# -gt 0 ]; do
    case "$1" in
        --list)    MODE="list"; shift ;;
        --to)      MODE="restore"; TARGET_DB="${2:?--to needs a database name}"; shift 2 ;;
        --to=*)    MODE="restore"; TARGET_DB="${1#*=}"; shift ;;
        --gen)     GEN="${2:?--gen needs a value}"; shift 2 ;;
        --gen=*)   GEN="${1#*=}"; shift ;;
        --tier)    TIER="${2:?--tier needs a value}"; shift 2 ;;
        --tier=*)  TIER="${1#*=}"; shift ;;
        -h|--help) usage; exit 0 ;;
        -*)        usage >&2; die "unknown option: $1" 3 ;;
        *)         [ -z "$FILE" ] || die "exactly one dump file expected" 3
                   FILE="$1"; shift ;;
    esac
done

[ -n "$MODE" ] || { usage >&2; die "choose --list or --to <database>" 3; }
[ -n "$FILE" ] || { usage >&2; die "no dump file given" 3; }
[ -r "$FILE" ] || die "not readable: $FILE" 3
[ -x "$TT_KEYS" ] || die "missing $TT_KEYS (it must sit next to this script)" 3
command -v age        >/dev/null 2>&1 || die "age not found in PATH" 2
command -v pg_restore >/dev/null 2>&1 || die "pg_restore not found in PATH" 2

# tier/generation: filename first, then the flags.
BASE="$(basename "$FILE")"
# bash =~ is ERE - no named groups, just two positional captures.
if [ -z "$GEN" ] && [[ "$BASE" =~ __([a-z][a-z0-9_-]*)-([0-9A-Za-z._-]+)\.dump\.age$ ]]; then
    TIER="${TIER:-${BASH_REMATCH[1]}}"
    GEN="${BASH_REMATCH[2]}"
fi
TIER="${TIER:-health}"
if [ -z "$GEN" ]; then
    case "$BASE" in
        *__*)
            die "cannot parse the generation out of $BASE - pass --gen" 3 ;;
        *)
            GEN="legacy"
            log INFO "no generation in the filename: assuming ${TIER}/legacy (pre-cutover dump)" ;;
    esac
fi

log INFO "dump     : $BASE ($(du -h "$FILE" | cut -f1))"
log INFO "tier/gen : ${TIER}/${GEN}"

KEY=""
if ! KEY_OUT="$("$TT_KEYS" unlock "${TIER}:${GEN}" 2>"$WORK_ERR")"; then
    sed 's/^/    /' "$WORK_ERR" >&2 || true
    die "could not unwrap ${TIER}/${GEN} - wrong master identity?" 4
fi
KEY="$KEY_OUT"
rm -f "$WORK_ERR"
[ -s "$KEY" ] || die "unlock produced no key" 4
log INFO "DEK      : ${KEY} (0600, tmpfs; shredded on exit)"

if [ "$MODE" = "list" ]; then
    # First bytes of the decrypted stream must be the pg_dump custom-format magic.
    log INFO "reading the archive table of contents (no database is touched)"
    age -d -i "$KEY" "$FILE" | pg_restore --list | sed -n '1,20p'
    log INFO "... (truncated to 20 lines; drop --list and use --to <db> to restore)"
    exit 0
fi

log WARNING "restoring INTO ${TARGET_DB} with --clean --if-exists"
age -d -i "$KEY" "$FILE" | pg_restore --clean --if-exists --dbname="$TARGET_DB" || {
    die "decrypt/restore failed (is ${TARGET_DB} reachable and are you its owner?)" 5
}
log INFO "restore into ${TARGET_DB} finished"
