#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/install-tt-backup-tthealth.sh:168 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c06fed9b05468e24ac157cc0fb3e7fd60eab307c %
#  %ccm_git_commit_id: 20459b8b5721abe5147d1bde58911ce436c14619 %
#  %ccm_git_commit_count: 168 %
#  %ccm_git_commit_date: 2026-10-03 17:43:26 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: install %
#  %ccm_git_modify_date: 2026-10-03 17:43:26 %
#  %ccm_git_file_last_modified: 2026-10-03 17:43:18 %
#  %ccm_git_file_name: install-tt-backup-tthealth.sh %
#  %ccm_git_path: infra/backups/scripts/install-tt-backup-tthealth.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 8211 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# tt-backup :: one-time installer for the encrypted tthealth_dev1 backup job.
#
# RUN AS ROOT (this is the only privileged step; everything else about this
# backup design is unprivileged):
#
#   sudo TTBACKUP_PG_PASSWORD='<pw>' \
#        /home/mpegg-adm/source/TermiteTowers/infra/backups/scripts/install-tt-backup-tthealth.sh
#
# Optional: REPO_DIR=... to point at a different checkout.
# Idempotent: safe to re-run (also the deploy path when the repo changes).
#
# What it does:
#   1. creates the no-login tt-backup service account (member of tt-ai-storage)
#   2. /etc/tt-backup/{tthealth.pgpass(0600),age-recipient.txt(0644)}
#   3. /mnt/ai_storage/backups/tthealth  (tt-backup:tt-ai-storage 2750, setgid)
#   4. installs the script to /usr/local/lib/tt-backup/ and copies the README
#   5. installs+verifies /etc/logrotate.d/tt-backup.conf
#   6. links the systemd units through /srv/dev1/systemd and enables the timer
#
# What it CANNOT do for you (printed at the end):
#   * create the PostgreSQL role  (needs a DB superuser)
#   * add the Jotta backup folder (jotta-cli runs as mpegg-adm, not root)
# ---------------------------------------------------------------------------
# tt-secrets.skip

set -Eeuo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

SERVICE_USER="tt-backup"
SERVICE_GROUP="tt-backup"
STORAGE_GROUP="tt-ai-storage"

DB_HOST="monolith"
DB_PORT="5432"
DB_NAME="tthealth_dev1"
DB_USER="tt_backup"

ETC_DIR="/etc/tt-backup"
PGPASS_FILE="$ETC_DIR/tthealth.pgpass"
RECIPIENT_FILE="$ETC_DIR/age-recipient.txt"
LIB_DIR="/usr/local/lib/tt-backup"
BACKUP_DIR="/mnt/ai_storage/backups/tthealth"
LOGROTATE_FILE="/etc/logrotate.d/tt-backup.conf"
UNITS=(tt-backup-tthealth.service tt-backup-tthealth.timer)

PG_PASSWORD="${TTBACKUP_PG_PASSWORD:-}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }
run() { printf '   + %s\n' "$*"; "$@"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --pg-password)   PG_PASSWORD="${2:?--pg-password needs a value}"; shift 2 ;;
        --pg-password=*) PG_PASSWORD="${1#*=}"; shift ;;
        -h|--help)       sed -n '2,24p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *)               die "unknown argument: $1 (try --help)" ;;
    esac
done

[ "$(id -u)" -eq 0 ] || die "must run as root (try: sudo $0)"
[ -f "$REPO_DIR/infra/backups/scripts/backup-tthealth.sh" ] || \
    die "not a TermiteTowers checkout: $REPO_DIR (set REPO_DIR=...)"
command -v age >/dev/null 2>&1 || die "age is not installed"
getent group "$STORAGE_GROUP" >/dev/null || die "group $STORAGE_GROUP does not exist"
[ -d /mnt/ai_storage/backups ] || die "/mnt/ai_storage/backups is not mounted"

step "1. Service account ($SERVICE_USER)"
if getent group "$SERVICE_GROUP" >/dev/null; then
    echo "   group $SERVICE_GROUP already exists"
else
    run groupadd --system "$SERVICE_GROUP"
fi
if id -u "$SERVICE_USER" >/dev/null 2>&1; then
    echo "   user $SERVICE_USER already exists"
else
    run useradd --system --gid "$SERVICE_GROUP" --home-dir /nonexistent \
        --no-create-home --shell /usr/sbin/nologin \
        --comment "TermiteTowers backup service account" "$SERVICE_USER"
fi
# Supplementary group: /mnt/ai_storage/backups is root:tt-ai-storage 0770.
run usermod -aG "$STORAGE_GROUP" "$SERVICE_USER"

step "2. Directories"
run install -d -o root        -g "$SERVICE_GROUP" -m 0750 "$ETC_DIR"
run install -d -o root        -g root             -m 0755 "$LIB_DIR"
# 2750 = 0750 + setgid. The setgid bit is load-bearing, not cosmetic: jottad
# replicates this folder as mpegg-adm (in tt-ai-storage, NOT in tt-backup), and
# only the file's *group* grants that read. Without setgid a new backup inherits
# the writer's primary group (tt-backup) and the upload silently never happens.
# Do not "tidy" this back to 0750 - see "Permissions are the upload contract" in
# infra/backups/README.md.
run install -d -o "$SERVICE_USER" -g "$STORAGE_GROUP" -m 2750 "$BACKUP_DIR"

# Repair files written before the setgid bit existed: one that is not group
# tt-ai-storage is invisible to Jotta and will never be uploaded.
if [ -n "$(find "$BACKUP_DIR" -maxdepth 1 -type f -print -quit 2>/dev/null)" ]; then
    echo "   + repairing group/mode on existing files in $BACKUP_DIR"
    find "$BACKUP_DIR" -maxdepth 1 -type f -exec chgrp "$STORAGE_GROUP" {} + 2>/dev/null || true
    find "$BACKUP_DIR" -maxdepth 1 -type f -exec chmod 0640 {} +            2>/dev/null || true
fi

step "3. Backup script + documentation"
run install -o root -g root -m 0755 \
    "$REPO_DIR/infra/backups/scripts/backup-tthealth.sh" "$LIB_DIR/backup-tthealth.sh"
run install -o root -g root -m 0644 \
    "$REPO_DIR/infra/backups/README.md" "$LIB_DIR/README.md"

step "4. age recipient (public key)"
SRC_RECIPIENT="$REPO_DIR/infra/backups/age/tthealth-recipient.txt"
[ -f "$SRC_RECIPIENT" ] || die "missing $SRC_RECIPIENT"
run install -o root -g root -m 0644 "$SRC_RECIPIENT" "$RECIPIENT_FILE"
grep -Eqs '^age1[0-9a-z]{50,}$' "$RECIPIENT_FILE" || \
    echo "   WARNING: no valid 'age1...' recipient line in $RECIPIENT_FILE"

step "5. Database secret (pgpass 0600 - libpq ignores group/other-readable files)"
if [ -n "$PG_PASSWORD" ]; then
    OLD_UMASK="$(umask)"; umask 077
    NEW_PGPASS="$(mktemp)"
    printf '%s:%s:%s:%s:%s\n' "$DB_HOST" "$DB_PORT" "$DB_NAME" "$DB_USER" "$PG_PASSWORD" > "$NEW_PGPASS"
    run install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 "$NEW_PGPASS" "$PGPASS_FILE"
    rm -f "$NEW_PGPASS"; umask "$OLD_UMASK"
    echo "   wrote $PGPASS_FILE"
elif [ -s "$PGPASS_FILE" ]; then
    echo "   no password given; keeping existing $PGPASS_FILE"
else
    run install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 /dev/null "$PGPASS_FILE"
    echo "   WARNING: created EMPTY $PGPASS_FILE - populate it before the timer fires:"
    echo "     sudo sh -c \"printf '%s:%s:%s:%s:%s\\\\n' $DB_HOST $DB_PORT $DB_NAME $DB_USER '<pw>' > $PGPASS_FILE\""
    echo "     sudo chown $SERVICE_USER:$SERVICE_GROUP $PGPASS_FILE"
fi

step "6. Logrotate (copy, not symlink - see infra/logrotate/README.md)"
SRC_LR="$REPO_DIR/infra/logrotate/logrotate.d/tt-backup.conf"
[ -f "$SRC_LR" ] || die "missing $SRC_LR"
run install -o root -g root -m 0644 "$SRC_LR" "$LOGROTATE_FILE"
printf '   + logrotate -d /etc/logrotate.conf (dry-run, tt-backup lines)\n'
logrotate -d /etc/logrotate.conf 2>&1 | grep -i 'tt-backup' | sed 's/^/     /' || true

step "7. systemd units (symlinked through /srv/dev1/systemd)"
for u in "${UNITS[@]}"; do
    SRC="/srv/dev1/systemd/$u"
    [ -f "$SRC" ] || SRC="$REPO_DIR/infra/systemd/$u"
    run ln -sfn "$SRC" "/etc/systemd/system/$u"
done
run systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/tt-backup-tthealth.service >/dev/null 2>&1 || true
run systemctl enable --now tt-backup-tthealth.timer

cat <<'NEXT'

-----------------------------------------------------------------------------
INSTALL COMPLETE. Three things still require a human:

1) PostgreSQL role (once, as a DB superuser):
     sudo -u postgres psql -d tthealth_dev1 -f <repo>/infra/backups/sql/tt_backup-role.sql
     sudo -u postgres psql -d tthealth_dev1 -c "\password tt_backup"
   Any later password change must be re-installed here via --pg-password,
   otherwise the job starts failing with an authentication error.

2) Jotta backup folder (as mpegg-adm - root has no Jotta session):
     jotta-cli add /mnt/ai_storage/backups/tthealth
     jotta-cli scan tthealth

3) age identity escrow - CRITICAL:
     The private identity is /home/mpegg-adm/.config/age/tthealth-backup.txt
     (0600). Without it the encrypted backups CANNOT be restored. Escrow it
     offline (password manager / paper) now. Never copy it into
     /mnt/ai_storage: jottad would upload it right next to the backups it
     protects, defeating the encryption.

Verify (as root):
     sudo -u tt-backup /usr/local/lib/tt-backup/backup-tthealth.sh
     systemctl list-timers tt-backup-tthealth.timer
     sudo journalctl -u tt-backup-tthealth.service -n 40
-----------------------------------------------------------------------------
NEXT
