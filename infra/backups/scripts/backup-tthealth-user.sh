#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-tthealth-user.sh@186 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 36e5534dbae74c34d4c473aefb68fcd92de5d3e4 %
#  %ccm_git_commit_id: 39d8262239b8cbb295886dbe654023e96f65ada9 %
#  %ccm_git_commit_count: 186 %
#  %ccm_git_commit_date: 2026-10-28 11:35:25 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 3 - encrypt to per-tier keys %
#  %ccm_git_modify_date: 2026-10-28 11:35:26 %
#  %ccm_git_file_last_modified: 2026-10-28 11:30:56 %
#  %ccm_git_file_name: backup-tthealth-user.sh %
#  %ccm_git_path: infra/backups/scripts/backup-tthealth-user.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 11260 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# --- usage:begin
# backup-tthealth-user.sh :: on-demand, UNPRIVILEGED export + Jottacloud
#                            upload of the PostgreSQL database tthealth_dev1
#
# Run as your normal admin account. No sudo, no systemd, no service account:
#
#     infra/backups/scripts/backup-tthealth-user.sh              # export + upload
#     infra/backups/scripts/backup-tthealth-user.sh --dry-run    # all but upload
#     infra/backups/scripts/backup-tthealth-user.sh --no-upload  # local only
#
# Why this exists alongside backup-tthealth.sh (the scheduled job):
#   * backup-tthealth.sh runs daily at 03:30 as the "tt-backup" service
#     account, writes into /mnt/ai_storage/backups/tthealth (root-installed,
#     2750 tt-backup:tt-ai-storage - NOT writable by a normal user) and is
#     replicated by jottad's continuous backup.
#   * this script is the "I want a verified export right now" path for a human
#     (before a migration, a restore rehearsal, a risky schema change). It
#     writes to a user-owned directory and uploads the single finished file
#     straight into Jotta's Archive area, so it needs neither root nor any
#     change to jottad's configured backup set.
#
# Both scripts use the SAME age recipient and therefore the SAME restore
# procedure. This dump is PII/PHI: pg_dump streams straight into age, so
# plaintext never reaches the disk in either script.
#
# Authentication: local PostgreSQL socket + peer auth as the invoking user
# (mpegg-adm is a member of tthealth_dev1_owner). No password, no pgpass.
# For a TCP host instead:  DB_HOST=monolith DB_USER=tt_backup PGPASSFILE=~/.pgpass
#
# Exit codes: 0 ok | 2 missing tool | 3 bad configuration | 4 output dir
#             5 dump/encrypt failed | 6 verification failed | 7 upload failed
# --- usage:end
set -Eeuo pipefail

APP_NAME="tthealth"

# Everything below may be overridden from the environment or the flags.
DB_NAME="${DB_NAME:-tthealth_dev1}"
# Default to the local unix socket: peer auth, so no password is involved.
DB_HOST="${DB_HOST:-/var/run/postgresql}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-$(id -un)}"

# User-owned output. NOT /mnt/ai_storage/backups/tthealth - see header.
OUT_DIR="${OUT_DIR:-$HOME/backups/$APP_NAME}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Archive/[REMOTE_PATH]/<file> on Jottacloud, via `jotta-cli archive`.
REMOTE_PATH="${REMOTE_PATH:-tthealth-dev1}"

DO_UPLOAD=1
DRY_RUN=0

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

usage() {
    # Markers, not line numbers: the pre-commit hook prepends a CCM header above
    # the shebang, which would break an "NR >= 3" range.
    sed -n '/^# --- usage:begin$/,/^# --- usage:end$/p' "${BASH_SOURCE[0]}" \
        | sed '1d;$d' \
        | sed 's/^# \{0,1\}//'
}

log() {
    local lvl="$1"
    shift
    local line
    line="$(printf '[%s] [%-5s] %s' "$(date '+%Y-%m-%d %H:%M:%S')" "$lvl" "$*")"
    printf '%s\n' "$line"
    if [ -n "${LOG_FILE:-}" ] && [ -d "${LOG_FILE%/*}" ]; then
        printf '%s\n' "$line" >> "$LOG_FILE" 2>/dev/null || true
    fi
}
die() { log ERROR "$*" >&2; exit "${2:-3}"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)   DRY_RUN=1; shift ;;
        --no-upload) DO_UPLOAD=0; shift ;;
        --keep)      RETENTION_DAYS="${2:?--keep needs a number of days}"; shift 2 ;;
        --keep=*)    RETENTION_DAYS="${1#*=}"; shift ;;
        --out-dir)   OUT_DIR="${2:?--out-dir needs a path}"; shift 2 ;;
        --out-dir=*) OUT_DIR="${1#*=}"; shift ;;
        --remote)    REMOTE_PATH="${2:?--remote needs a Jotta archive path}"; shift 2 ;;
        --remote=*)  REMOTE_PATH="${1#*=}"; shift ;;
        -h|--help)   usage; exit 0 ;;
        *)           die "unknown argument: $1 (try --help)" ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    die "run this as your own account, not root - it is designed to need no privileges" 3
fi

# Normalise the Archive folder name: no leading or trailing slash.
REMOTE_PATH="${REMOTE_PATH#/}"
REMOTE_PATH="${REMOTE_PATH%/}"
[ -n "$REMOTE_PATH" ] || die "--remote / REMOTE_PATH must name a Jotta Archive folder" 3

# --- encryption: one DEK per data classification ------------------------------
# Same tier and key as the scheduled job, so the restore procedure is identical.
AGE_TIER="${AGE_TIER:-health}"
# shellcheck source=lib/tt-age.sh
. "$REPO_DIR/infra/backups/scripts/lib/tt-age.sh"

RECIPIENT_FILE="${AGE_RECIPIENTS:-}"
if [ -z "$RECIPIENT_FILE" ]; then
    RECIPIENT_FILE="$(tt_age_require_recipient "$AGE_TIER" 2>/dev/null || true)"
fi
if [ -z "$RECIPIENT_FILE" ] || [ ! -r "$RECIPIENT_FILE" ]; then
    die "no readable age recipient for tier '${AGE_TIER}' under ${TT_AGE_DIR:-?}" 3
fi
grep -Eqs '^age1[0-9a-z]{50,}$' "$RECIPIENT_FILE" || \
    die "no valid 'age1...' recipient line in $RECIPIENT_FILE" 3
# No default generation: an export that cannot name its key is not restorable.
AGE_GEN="$(tt_age_current_gen "$AGE_TIER" 2>/dev/null || true)"
[ -n "$AGE_GEN" ] || die "cannot determine the ${AGE_TIER} generation from $RECIPIENT_FILE" 3

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
# tier+generation in the NAME, so a later rotation cannot orphan this export.
OUT_FILE="$OUT_DIR/${DB_NAME}_${TIMESTAMP}__${AGE_TIER}-${AGE_GEN}.dump.age"
LOG_FILE="$OUT_DIR/export.log"

# `jotta-cli archive --remote` is the FULL destination path, filename included:
# --remote=tthealth-dev1 alone creates a *file* named "tthealth-dev1", so the
# folder and the filename must both be spelled out. REMOTE_PATH is the folder.
UPLOAD_PATH="${REMOTE_PATH}/$(basename "$OUT_FILE")"

# Never write a plaintext dump, and never leave a readable one behind.
umask 077

# Created before the first log line so the log file exists from the start.
mkdir -p "$OUT_DIR" 2>/dev/null || true
chmod 0700 "$OUT_DIR" 2>/dev/null || true

cleanup() {
    local rc=$?
    if [ "$rc" -ne 0 ] && [ -f "$OUT_FILE" ]; then
        rm -f -- "$OUT_FILE"
        log ERROR "removed incomplete export $(basename "$OUT_FILE") (exit ${rc})" >&2
    fi
    return "$rc"
}
trap cleanup EXIT

log INFO "=== ${APP_NAME} on-demand export started (user=$(id -un)) ==="

# --- preconditions -----------------------------------------------------------
command -v pg_dump >/dev/null 2>&1 || die "pg_dump not found in PATH" 2
command -v age >/dev/null 2>&1 || die "age not found in PATH" 2

# Private identity is NOT required to create a backup - only to verify/restore.
# The decrypt smoke test below needs this tier's DEK, and only the master
# identity can unwrap that. Point AGE_IDENTITY at an unwrapped DEK to enable it:
#   AGE_IDENTITY=$(./tt-keys.sh unlock health) ./backup-tthealth-user.sh
AGE_IDENTITY="${AGE_IDENTITY:-}"

if [ ! -d "$OUT_DIR" ] || [ ! -w "$OUT_DIR" ]; then
    die "output dir missing or not writable: $OUT_DIR" 4
fi

log INFO "Source   : ${DB_NAME} on ${DB_HOST}:${DB_PORT} as ${DB_USER}"
log INFO "Target   : $(basename "$OUT_FILE")  (tier ${AGE_TIER}/${AGE_GEN}, recipient $(basename "$RECIPIENT_FILE"))"
if [ "$DO_UPLOAD" -eq 1 ]; then
    log INFO "Upload   : Archive/${UPLOAD_PATH}"
else
    log INFO "Upload   : skipped (--no-upload)"
fi
if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "Mode     : --dry-run (no upload)"
fi

# --- dump + encrypt ----------------------------------------------------------
# --no-password guarantees a fast, non-interactive failure instead of a prompt
# hanging forever. pipefail makes a mid-stream pg_dump failure fail the whole
# pipeline, and the cleanup trap then removes the partial .age file.
if ! pg_dump --format=custom --no-password \
             --host="$DB_HOST" --port="$DB_PORT" \
             --username="$DB_USER" --dbname="$DB_NAME" \
     | age --encrypt --recipients-file "$RECIPIENT_FILE" --output "$OUT_FILE"; then
    log ERROR "pg_dump | age pipeline failed"
    log ERROR "check DB_USER/DB_HOST: peer auth over '${DB_HOST}' requires DB_USER=$(id -un)"
    exit 5
fi

# --- verification ------------------------------------------------------------
[ -s "$OUT_FILE" ] || { log ERROR "export is missing or empty: $OUT_FILE"; exit 6; }

# 21 = strlen("age-encryption.org/v1")
if [ "$(head -c 21 "$OUT_FILE")" != "age-encryption.org/v1" ]; then
    log ERROR "output is not an age file: $OUT_FILE"
    exit 6
fi

if [ -n "$AGE_IDENTITY" ] && [ -r "$AGE_IDENTITY" ]; then
    # Read only the first bytes: a pg_dump custom-format archive starts with
    # PGDMP. head closes the pipe early so age exits non-zero - hence "|| true".
    MAGIC="$(age --decrypt -i "$AGE_IDENTITY" "$OUT_FILE" 2>/dev/null | head -c 5 || true)"
    if [ "$MAGIC" != "PGDMP" ]; then
        log ERROR "decrypted stream does not start with PGDMP (got '${MAGIC}')"
        log ERROR "wrong generation? this file needs ${AGE_TIER}/${AGE_GEN}"
        exit 6
    fi
    log INFO "Verified : decrypts with $(basename "$AGE_IDENTITY") to a pg_dump custom-format archive"
else
    log WARNING "skipped the decrypt smoke test - set AGE_IDENTITY to an unwrapped ${AGE_TIER} DEK to run it"
fi

log INFO "Export OK: $(basename "$OUT_FILE") ($(du -h "$OUT_FILE" | cut -f1), mode $(stat -c '%a' "$OUT_FILE"))"

# --- upload ------------------------------------------------------------------
if [ "$DO_UPLOAD" -eq 1 ]; then
    if ! command -v jotta-cli >/dev/null 2>&1; then
        log ERROR "jotta-cli not found in PATH - encrypted export kept locally at $OUT_FILE"
        exit 2
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        log INFO "DRY-RUN: would run: jotta-cli archive \"$OUT_FILE\" --remote=\"$UPLOAD_PATH\" --nogui"
    else
        log INFO "Uploading to Jottacloud Archive/${UPLOAD_PATH} ..."
        if ! jotta-cli archive "$OUT_FILE" --remote="$UPLOAD_PATH" --nogui; then
            log ERROR "jotta-cli archive failed - encrypted export kept locally at $OUT_FILE"
            exit 7
        fi
        # Confirmation only. A single-file archive is synchronous, but the
        # remote index can lag, so this never fails the run. The Archive root
        # listing shows only direct children, hence listing the folder itself
        # and matching the exact remote path in its JSON.
        if jotta-cli ls --json "archive/${REMOTE_PATH}" 2>/dev/null \
             | grep -qF "\"/archive/${UPLOAD_PATH}\""; then
            log INFO "Confirmed remotely: Archive/${UPLOAD_PATH}"
        else
            log WARNING "not visible in the Archive listing yet - check the Jottacloud web UI for /archive/${UPLOAD_PATH}"
        fi
    fi
fi

# --- retention (local only; Jottacloud keeps the long history) ---------------
PRUNED="$(find "$OUT_DIR" -maxdepth 1 -type f -name "${DB_NAME}_*.dump.age" \
          -mtime +"$RETENTION_DAYS" -print -delete 2>/dev/null | wc -l)"
log INFO "Retention: pruned ${PRUNED} local export(s) older than ${RETENTION_DAYS} days"

log INFO "=== ${APP_NAME} on-demand export finished ==="

# Restore (two steps - the DEK must be unwrapped by the master identity first,
# which is exactly why a service account can never decrypt these):
#   GEN=$(grep -o 'health-[0-9A-Za-z]*' <<< "<file>.dump.age")
#   ./tt-keys.sh unlock "health:${GEN#health-}" --out /dev/shm/health.key
#   age --decrypt -i /dev/shm/health.key <file>.dump.age \
#     | pg_restore --clean --if-exists -d tthealth_dev1
#   shred -u /dev/shm/health.key
