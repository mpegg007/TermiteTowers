#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-tthealth.sh@187 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 55cd849f5f79a6ad8fa2fab8ffa81d9efcfdb554 %
#  %ccm_git_commit_id: 7018a976837891f434e9ab0e56b714507e4259fa %
#  %ccm_git_commit_count: 187 %
#  %ccm_git_commit_date: 2026-10-28 11:35:49 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: fix(backups): fail loudly when lib/tt-age.sh is missing beside the script %
#  %ccm_git_modify_date: 2026-10-28 11:35:50 %
#  %ccm_git_file_last_modified: 2026-10-28 11:35:41 %
#  %ccm_git_file_name: backup-tthealth.sh %
#  %ccm_git_path: infra/backups/scripts/backup-tthealth.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 9903 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# tt-backup :: encrypted PostgreSQL backup  (database: tthealth_dev1)
#
# Runs as the unprivileged, no-login service account "tt-backup", which can
# read the database and write its own backup folder - and nothing else. It has
# no sudo, no docker, no Jotta credentials and no age identity, so it can
# create backups but can never restore or decrypt them.
#
# pg_dump streams straight into age: encrypted output is the only thing that
# ever reaches the disk, so plaintext PHI is never written to a file.
#
# Encryption is per data classification - this job uses the "health" tier, and
# only that tier's PUBLIC recipient is visible from this account. The private
# half lives in the master-wrapped keyring (mpegg-adm, 0700), which tt-backup
# cannot read or even traverse; install-tt-keys.sh --check asserts that. The
# tier and generation are part of the filename, so restore knows which key a
# given dump needs even after a rotation.
#
# Deployed by scripts/install-tt-backup-tthealth.sh to
#   /usr/local/lib/tt-backup/backup-tthealth.sh
# and executed by tt-backup-tthealth.service.
#
# Exit codes: 0 ok | 2 missing tool | 3 missing secret | 4 backup dir
#             5 dump/encrypt failed | 6 verification failed
# ---------------------------------------------------------------------------
set -Eeuo pipefail

APP_NAME="tthealth"

# All of the below may be overridden from the environment (staging, testing,
# or pointing the same script at another database without editing it).
DB_NAME="${DB_NAME:-tthealth_dev1}"
DB_HOST="${DB_HOST:-monolith}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-tt_backup}"

BACKUP_ROOT="${BACKUP_ROOT:-/mnt/ai_storage/backups}"
BACKUP_DIR="${BACKUP_ROOT}/${APP_NAME}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# The group that must be able to READ the finished file: jottad uploads this
# folder as mpegg-adm, who is in tt-ai-storage but NOT in tt-backup.
BACKUP_GROUP="${BACKUP_GROUP:-tt-ai-storage}"

# /var/log/tt-backup is created (and owned) by LogsDirectory=tt-backup in the
# systemd unit. Deliberately NOT /var/log/tt-backup-*.log, which
# /etc/logrotate.d/tt-apps owns with "su root adm" - see logrotate/tt-backup.conf.
LOG_DIR="${LOG_DIR:-/var/log/tt-backup}"
LOG_FILE="${LOG_DIR}/${APP_NAME}.log"

PGPASS_FILE="${PGPASSFILE:-/etc/tt-backup/tthealth.pgpass}"

# --- encryption: one DEK per data classification, never a shared key ---------
AGE_TIER="${AGE_TIER:-health}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# lib/ sits next to the script in both layouts: the repo (scripts/lib/) and the
# deployed copy (/usr/local/lib/tt-backup/lib/, installed with the script).
LIB_FILE="$SCRIPT_DIR/lib/tt-age.sh"
if [ ! -r "$LIB_FILE" ]; then
    printf 'ERROR: %s is missing - re-run install-tt-backup-tthealth.sh\n' "$LIB_FILE" >&2
    exit 3
fi
# shellcheck source=lib/tt-age.sh
. "$LIB_FILE"

AGE_RECIPIENTS="${AGE_RECIPIENTS:-$(tt_age_require_recipient "$AGE_TIER" 2>/dev/null || true)}"
if [ -z "$AGE_RECIPIENTS" ] || [ ! -r "$AGE_RECIPIENTS" ]; then
    printf 'ERROR: no readable age recipient for tier %s under %s\n' \
        "$AGE_TIER" "${TT_AGE_DIR:-?}" >&2
    exit 3
fi
# No default generation: a dump that cannot name its key is not restorable.
AGE_GEN="$(tt_age_current_gen "$AGE_TIER" 2>/dev/null || true)"
if [ -z "$AGE_GEN" ]; then
    printf 'ERROR: cannot determine the %s generation from %s\n' \
        "$AGE_TIER" "$AGE_RECIPIENTS" >&2
    exit 3
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
# tier+generation travel in the NAME: restore selects the key from it and a
# later rotation cannot orphan this file. Retention globs match the
# ".dump.age" suffix only, so they are unaffected.
OUT_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}__${AGE_TIER}-${AGE_GEN}.dump.age"

# Backup files must stay group-readable by tt-ai-storage (jottad replicates the
# folder as mpegg-adm) and never world-readable. 0027 plus the setgid bit on
# BACKUP_DIR (2750, set by install-tt-backup-tthealth.sh) yields
# tt-backup:tt-ai-storage 0640. The chgrp/chmod pair after the dump re-asserts
# the group, so losing the setgid bit cannot quietly stop Jotta uploads.
umask 0027

# --- logging: append to the log file, degrade to stdout/journald ------------
log() {
    local type="$1"; shift
    local line
    line="[$(date '+%Y-%m-%d %H:%M:%S')] [$type] $*"
    printf '%s\n' "$line" | tee -a "$LOG_FILE" 2>/dev/null || printf '%s\n' "$line"
}

# --- never leave a half-written .age file behind -----------------------------
SUCCESS=0
cleanup() {
    local rc=$?
    if [ "$SUCCESS" -ne 1 ] && [ -f "$OUT_FILE" ]; then
        rm -f "$OUT_FILE"
        log WARNING "Removed incomplete backup $(basename "$OUT_FILE") (exit ${rc})"
    fi
    return "$rc"
}
trap cleanup EXIT

mkdir -p "$LOG_DIR" 2>/dev/null || true
log INFO "=== ${APP_NAME} backup started (user=$(id -un), pid=$$) ==="

# --- preconditions -----------------------------------------------------------
command -v pg_dump >/dev/null 2>&1 || { log ERROR "pg_dump not found in PATH"; exit 2; }
command -v age     >/dev/null 2>&1 || { log ERROR "age not found in PATH"; exit 2; }

[ -r "$PGPASS_FILE" ]    || { log ERROR "pgpass not readable: $PGPASS_FILE"; exit 3; }
[ -r "$AGE_RECIPIENTS" ] || { log ERROR "age recipients not readable: $AGE_RECIPIENTS"; exit 3; }

mkdir -p "$BACKUP_DIR" || { log ERROR "cannot create backup dir: $BACKUP_DIR"; exit 4; }

# libpq reads the password from this file. It must be owned by *this* user with
# no group/other bits, otherwise libpq silently ignores it (hence 0600 below,
# not 0640).
export PGPASSFILE="$PGPASS_FILE"
export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-15}"

log INFO "Dumping ${DB_NAME}@${DB_HOST}:${DB_PORT} as ${DB_USER} -> $(basename "$OUT_FILE") [tier ${AGE_TIER}/${AGE_GEN}]"

# --no-password guarantees a fast, non-interactive failure instead of a prompt
# hanging until TimeoutStartSec. pipefail makes a mid-stream pg_dump failure
# fail the whole pipeline.
if ! pg_dump --format=custom --no-password \
             --host="$DB_HOST" --port="$DB_PORT" \
             --username="$DB_USER" --dbname="$DB_NAME" \
     | age --encrypt --recipients-file "$AGE_RECIPIENTS" --output "$OUT_FILE"; then
    log ERROR "pg_dump | age pipeline failed"
    exit 5
fi

# --- verification ------------------------------------------------------------
if [ ! -s "$OUT_FILE" ]; then
    log ERROR "Backup is missing or empty: $OUT_FILE"
    exit 6
fi

# 21 = strlen("age-encryption.org/v1")
if [ "$(head -c 21 "$OUT_FILE")" != "age-encryption.org/v1" ]; then
    log ERROR "Output is not an age file: $OUT_FILE"
    exit 6
fi

# --- publishing permissions --------------------------------------------------
# Re-assert owner:group:mode instead of trusting the setgid bit on BACKUP_DIR.
# chgrp to a group we belong to needs no privileges. Failing here does not
# invalidate the local backup, but it does stop cloud replication - so it must be
# loud rather than silent.
chgrp "$BACKUP_GROUP" "$OUT_FILE" 2>/dev/null || \
    log WARNING "chgrp ${BACKUP_GROUP} failed on $(basename "$OUT_FILE")"
chmod 0640 "$OUT_FILE" 2>/dev/null || \
    log WARNING "chmod 0640 failed on $(basename "$OUT_FILE")"

ACTUAL_GROUP="$(stat -c '%G' "$OUT_FILE" 2>/dev/null || echo unknown)"
if [ "$ACTUAL_GROUP" != "$BACKUP_GROUP" ]; then
    log WARNING "group of $(basename "$OUT_FILE") is '${ACTUAL_GROUP}', expected '${BACKUP_GROUP}': jottad (mpegg-adm) canNOT read it, so it will never upload"
fi

SUCCESS=1
log INFO "Backup OK: $(basename "$OUT_FILE") ($(du -h "$OUT_FILE" | cut -f1)) [$(stat -c '%U:%G %a' "$OUT_FILE" 2>/dev/null)]"

# --- retention (local; Jotta keeps the long-term history) --------------------
PRUNED="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name "${DB_NAME}_*.dump.age" \
          -mtime +"$RETENTION_DAYS" -print -delete 2>/dev/null | wc -l)"
log INFO "Retention: pruned ${PRUNED} local backup(s) older than ${RETENTION_DAYS} days"

# Cloud replication is intentionally NOT done here: this account holds no Jotta
# credentials. jottad (running as mpegg-adm) scans BACKUP_DIR and uploads.
log INFO "Cloud replication handled out-of-band by jottad scanning ${BACKUP_DIR}"
log INFO "=== ${APP_NAME} backup finished ==="

# Restore (two steps - the DEK must be unwrapped by the master identity first,
# and neither of those is reachable from tt-backup):
#   ./tt-keys.sh unlock health:2026Q4 --out /dev/shm/health.key
#   age -d -i /dev/shm/health.key <file>.dump.age \
#     | pg_restore --clean --if-exists -h monolith -U tthealth_dev1_owner -d tthealth_dev1
#   shred -u /dev/shm/health.key
# The generation to unlock is the "__health-<gen>" part of the filename.
