#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-db-user.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 4c8869f0270c473d993c99e68b3fcfc53edea668 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:44 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:36 %
#  %ccm_git_file_name: backup-db-user.sh %
#  %ccm_git_path: infra/backups/scripts/backup-db-user.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10204 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# tt-backup :: scheduled PostgreSQL dump as the invoking user (no root, no
# service account, no password).
#
# WHY THIS EXISTS
#   backup-tthealth.sh is root-installed, runs as the no-login "tt-backup"
#   account and reaches the cluster over TCP with a pgpass. That shape is
#   justified for PHI, but it needs sudo to deploy. ttdb_dev1 and ttphoto_dev1
#   had NO backup at all, and "needs sudo" was the reason. This script trades
#   the service account for peer auth over the local unix socket: same
#   pg_dump | age pipeline, arranged so a user-level systemd timer can run it.
#
# DIFFERENCE FROM backup-tthealth.sh THAT MATTERS
#   That job streams pg_dump straight into age, so plaintext never touches a
#   file. This one cannot do that AND prove what it dumped, because inspecting
#   the table of contents requires plaintext. So it dumps to a 0600 temp file
#   inside OUT_DIR, asserts the expected schemas are present, encrypts it, then
#   shreds the temp. USE THIS ONLY FOR NON-PHI DATA - the general tier. For
#   PHI the streaming job remains the rule, precisely so no plaintext lands.
#
# THE ASSERTION IS THE POINT
#   pg_dump exiting 0 only means "I did not fail". It does not mean the schema
#   you care about was visible to the role. ttphoto_dev1 has a v2 schema that a
#   read-only account could not see, and an unnoticed empty dump is how you end
#   up with a backup that restores nothing. EXPECT_SCHEMAS makes that loud.
#
# USAGE
#   APP_NAME=ttdb DB_NAME=ttdb_dev1 EXPECT_SCHEMAS=dhcp_history,kea \
#     backup-db-user.sh
#
#   APP_NAME=ttphoto DB_NAME=ttphoto_dev1 AGE_TIER=general \
#     EXPECT_SCHEMAS=public,v2 backup-db-user.sh
#
# ENVIRONMENT
#   APP_NAME        required; names OUT_DIR and the log
#   DB_NAME         required; database to dump
#   EXPECT_SCHEMAS  optional comma-separated schemas that must appear in the TOC
#   AGE_TIER        default general
#   OUT_DIR         default /mnt/ai_storage/backups/$APP_NAME
#   RETENTION_DAYS  default 14
#   DB_HOST         default /var/run/postgresql (peer auth; no password)
#   DB_USER         default the invoking user
#
# EXIT CODES
#   0 ok | 2 missing tool | 3 bad configuration | 4 output dir
#   5 dump/encrypt failed | 6 verification failed
# ---------------------------------------------------------------------------
set -Eeuo pipefail

APP_NAME="${APP_NAME:?APP_NAME is required (names the output directory)}"
DB_NAME="${DB_NAME:?DB_NAME is required}"
EXPECT_SCHEMAS="${EXPECT_SCHEMAS:-}"
AGE_TIER="${AGE_TIER:-general}"

# Local socket + peer auth is the whole authentication story: no pgpass, no
# password in the environment, nothing to leak. Override only for a remote host.
DB_HOST="${DB_HOST:-/var/run/postgresql}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-$(id -un)}"

OUT_DIR="${OUT_DIR:-/mnt/ai_storage/backups/${APP_NAME}}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
LOG_FILE="${LOG_FILE:-$OUT_DIR/backup.log}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

log() {
    local lvl="$1"; shift
    local line
    line="$(printf '[%s] [%-5s] %s' "$(date '+%Y-%m-%d %H:%M:%S')" "$lvl" "$*")"
    printf '%s\n' "$line"
    if [ -n "${LOG_FILE:-}" ] && [ -d "${LOG_FILE%/*}" ]; then
        printf '%s\n' "$line" >> "$LOG_FILE" 2>/dev/null || true
    fi
}
die() { log ERROR "$*"; exit "${2:-3}"; }

# Refuse root: the whole design is "runs as you", and a root run would create
# files jottad cannot read (jottad is a user unit running as you).
[ "$(id -u)" -ne 0 ] || die "run as your own account, not root" 3

# --- encryption: per-tier DEK, public recipient only ------------------------
# shellcheck source=lib/tt-age.sh
LIB="$REPO_DIR/infra/backups/scripts/lib/tt-age.sh"
[ -r "$LIB" ] || die "missing $LIB" 3
# shellcheck disable=SC1090
. "$LIB"

RECIPIENT_FILE="$(tt_age_require_recipient "$AGE_TIER" 2>/dev/null || true)"
[ -n "$RECIPIENT_FILE" ] && [ -r "$RECIPIENT_FILE" ] || \
    die "no readable age recipient for tier '${AGE_TIER}' under ${TT_AGE_DIR:-?}" 3
# No default generation: a dump that cannot name its key is not restorable.
AGE_GEN="$(tt_age_current_gen "$AGE_TIER" 2>/dev/null || true)"
[ -n "$AGE_GEN" ] || die "cannot determine the ${AGE_TIER} generation" 3

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/${DB_NAME}_${TIMESTAMP}__${AGE_TIER}-${AGE_GEN}.dump.age"
TMP_DUMP="${OUT_DIR}/.${DB_NAME}_${TIMESTAMP}.partial.dump"
WORK_TOC="${OUT_DIR}/.${DB_NAME}_${TIMESTAMP}.toc"

# 077: the temp dump holds plaintext, and the finished file needs to be
# readable only by this user, who is also the jottad uploader.
umask 077

mkdir -p "$OUT_DIR" || die "cannot create $OUT_DIR" 4
LOG_FILE="$OUT_DIR/backup.log"

cleanup() {
    local rc=$?
    # The plaintext temp is the dangerous artifact here, so it goes first and
    # unconditionally - not only on failure.
    if [ -f "$TMP_DUMP" ]; then
        shred -u "$TMP_DUMP" 2>/dev/null || rm -f "$TMP_DUMP"
    fi
    rm -f "$WORK_TOC"
    if [ "$rc" -ne 0 ] && [ -f "$OUT_FILE" ]; then
        rm -f "$OUT_FILE"
        log WARNING "removed incomplete dump $(basename "$OUT_FILE") (exit ${rc})"
    fi
    return "$rc"
}
trap cleanup EXIT

log INFO "=== ${APP_NAME} backup started (user=$(id -un), pid=$$) ==="

# --- preconditions ----------------------------------------------------------
command -v pg_dump   >/dev/null 2>&1 || die "pg_dump not found in PATH" 2
command -v pg_restore >/dev/null 2>&1 || die "pg_restore not found in PATH" 2
command -v age       >/dev/null 2>&1 || die "age not found in PATH" 2
command -v shred     >/dev/null 2>&1 || log WARNING "shred not found; falling back to rm for the temp dump"

touch "$LOG_FILE" 2>/dev/null || true

log INFO "dumping ${DB_NAME}@${DB_HOST} as ${DB_USER} [tier ${AGE_TIER}/${AGE_GEN}]"

# --- dump to a private temp file -------------------------------------------
# --no-password: a prompt would hang until the unit's TimeoutStartSec. Peer
# auth needs none, so a failure here is a real configuration error.
if ! pg_dump --format=custom --no-password \
             --host="$DB_HOST" --port="$DB_PORT" \
             --username="$DB_USER" --dbname="$DB_NAME" \
             --file="$TMP_DUMP"; then
    die "pg_dump failed for ${DB_NAME}" 5
fi

[ -s "$TMP_DUMP" ] || die "pg_dump produced an empty file" 6

# Fails loudly if the archive is not actually a custom-format dump.
pg_restore --list "$TMP_DUMP" >/dev/null 2>&1 || die "dump is not a readable pg_dump archive" 6

# --- assert the expected schemas are IN the dump ---------------------------
# Do NOT grep for "SCHEMA - <name>". pg_dump does not emit a SCHEMA entry for
# public on PostgreSQL 15+, so a plain text match reports a perfectly good dump
# as missing public - which is exactly how this check first failed. Match the
# TOC's namespace FIELD instead, which every entry type carries:
#
#   214; 1259 16385 TABLE public images ttphoto_dev1_owner   -> field 5
#   5;   2615 23120 SCHEMA - v2 mpegg-adm                    -> field 5
#   3715; 0 0 ACL - SCHEMA public pg_database_owner          -> fields 6/7
if [ -n "$EXPECT_SCHEMAS" ]; then
    TOC_FILE="$WORK_TOC"
    pg_restore --list "$TMP_DUMP" > "$TOC_FILE" 2>/dev/null || \
        die "could not read the dump table of contents" 6
    TOC_OBJECTS="$(grep -c '^[0-9]' "$TOC_FILE" || true)"
    IFS=',' read -r -a _schemas <<< "$EXPECT_SCHEMAS"
    for schema in "${_schemas[@]}"; do
        schema="${schema// /}"
        [ -n "$schema" ] || continue
        matched="$(awk -v s="$schema" \
            '$5==s || ($6=="SCHEMA" && $7==s) {n++} END{print n+0}' "$TOC_FILE")"
        if [ "$matched" -gt 0 ]; then
            log INFO "verified schema in dump: ${schema} (${matched} TOC entries)"
        else
            die "expected schema '${schema}' is NOT in the dump of ${DB_NAME} - refusing to publish a partial backup" 6
        fi
    done
    log INFO "dump contains ${TOC_OBJECTS} objects; expected schemas all present"
fi

# --- encrypt, then destroy the plaintext -----------------------------------
if ! age --encrypt --recipients-file "$RECIPIENT_FILE" \
         --output "$OUT_FILE" "$TMP_DUMP"; then
    die "age encryption failed" 5
fi

shred -u "$TMP_DUMP" 2>/dev/null || rm -f "$TMP_DUMP"

[ -s "$OUT_FILE" ] || die "encrypted output is missing or empty" 6
# 21 = strlen("age-encryption.org/v1")
if [ "$(head -c 21 "$OUT_FILE")" != "age-encryption.org/v1" ]; then
    die "output is not an age file: $OUT_FILE" 6
fi

chmod 0600 "$OUT_FILE" || log WARNING "chmod 0600 failed on $(basename "$OUT_FILE")"

log INFO "Backup OK: $(basename "$OUT_FILE") ($(du -h "$OUT_FILE" | cut -f1))"

# --- retention (local; Jotta keeps the long-term history) ------------------
PRUNED="$(find "$OUT_DIR" -maxdepth 1 -type f -name "${DB_NAME}_*.dump.age" \
          -mtime +"$RETENTION_DAYS" -print -delete 2>/dev/null | wc -l)"
log INFO "retention: pruned ${PRUNED} local dump(s) older than ${RETENTION_DAYS} days"
log INFO "cloud replication handled out-of-band by jottad scanning ${OUT_DIR}"
log INFO "=== ${APP_NAME} backup finished ==="
