#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/install-tt-backup-db-user.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 45b6a50088a260932fc8ef460eaea202d300caea %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:44 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:36 %
#  %ccm_git_file_name: install-tt-backup-db-user.sh %
#  %ccm_git_path: infra/backups/scripts/install-tt-backup-db-user.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 5581 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# Install tt-backup-db-ttdb and tt-backup-db-ttphoto as systemd USER timers.
#
# RUN AS YOURSELF - no sudo anywhere:
#
#     infra/backups/scripts/install-tt-backup-db-user.sh
#
# What it does:
#   1. creates both backup directories (0700, owned by you, which is also who
#      jottad uploads as)
#   2. installs the four units into ~/.config/systemd/user/ with @REPO_DIR@
#      resolved to this checkout
#   3. daemon-reload + enable --now both timers
#   4. reports whether the ttdb job has the database privilege it needs
#
# The one thing it cannot do (and prints the exact command for) is the
# pg_read_all_data grant that ttdb_dev1 requires - that needs a superuser.
# ttphoto_dev1 needs nothing: you already own it.
#
# Idempotent: safe to re-run, and it is the deploy path after edits.
# ---------------------------------------------------------------------------
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/ai_storage/backups}"
UNIT_SRC="$REPO_DIR/infra/systemd/user"
UNIT_DST="$HOME/.config/systemd/user"
SERVICE_SCRIPT="$REPO_DIR/infra/backups/scripts/backup-db-user.sh"

UNITS=(
    tt-backup-db-ttdb.service
    tt-backup-db-ttdb.timer
    tt-backup-db-ttphoto.service
    tt-backup-db-ttphoto.timer
)
TIMERS=(tt-backup-db-ttdb.timer tt-backup-db-ttphoto.timer)

die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }
run()  { printf '   + %s\n' "$*"; "$@"; }

[ "$(id -u)" -ne 0 ] || die "run as your own account, not root - user timers must be owned by you"
[ -f "$SERVICE_SCRIPT" ] || die "missing $SERVICE_SCRIPT"
[ -x "$SERVICE_SCRIPT" ] || die "$SERVICE_SCRIPT is not executable - run: chmod +x it"

step "1. backup directories"
for app in ttdb ttphoto; do
    run mkdir -p "$BACKUP_ROOT/$app"
    run chmod 0700 "$BACKUP_ROOT/$app"
done

step "2. systemd user units -> $UNIT_DST"
run mkdir -p "$UNIT_DST"
for unit in "${UNITS[@]}"; do
    [ -f "$UNIT_SRC/$unit" ] || die "missing $UNIT_SRC/$unit"
    sed "s|@REPO_DIR@|$REPO_DIR|g" "$UNIT_SRC/$unit" > "$UNIT_DST/$unit"
    run chmod 0644 "$UNIT_DST/$unit"
done

step "3. enable the timers"
run systemctl --user daemon-reload
for timer in "${TIMERS[@]}"; do
    run systemctl --user enable --now "$timer"
done
systemctl --user list-timers --all 2>/dev/null | grep -E 'tt-backup-db|NEXT' || true

step "4. database privilege check"
if command -v psql >/dev/null 2>&1; then
    GRANTED="$(psql -d ttdb_dev1 -tAc \
        "select coalesce(pg_has_role(current_user,'pg_read_all_data','member'), false)" 2>/dev/null || echo unknown)"
    case "$GRANTED" in
        t) printf '   ok   pg_read_all_data is already granted\n' ;;
        f) printf '   ACTION REQUIRED: ttdb_dev1 needs one superuser grant (see below)\n' ;;
        *) printf '   ?    could not determine pg_read_all_data membership\n' ;;
    esac
else
    printf '   ?    psql not found; skipping the privilege check\n'
fi

cat <<NEXT

-----------------------------------------------------------------------------
INSTALLED.

The ttphoto job needs nothing further - it is running-capable now.

The ttdb job needs ONE superuser grant, once, because mpegg-adm can read kea
tables but not its sequences (pg_dump fails on dhcp4_audit_id_seq) and several
schemas give no USAGE at all:

    sudo -u postgres psql -d ttdb_dev1 -f $REPO_DIR/infra/backups/sql/tt-read-grant-mpegg.sql

Then prove it end to end, as yourself:

    APP_NAME=ttdb DB_NAME=ttdb_dev1 AGE_TIER=general \\
      EXPECT_SCHEMAS=dhcp_history,kea,powerdns,snipeit,water_meter,watchyourlan \\
      $SERVICE_SCRIPT

Jotta (no root involved - jottad runs as you). Add each folder that now has a
dump in it:

    jotta-cli add $BACKUP_ROOT/ttphoto
    jotta-cli add $BACKUP_ROOT/ttdb
    jotta-cli scan

Verify:

    systemctl --user list-timers tt-backup-db-ttdb.timer tt-backup-db-ttphoto.timer
    tail -n 20 $BACKUP_ROOT/ttphoto/backup.log
    jotta-cli status -v | grep -A2 ttphoto

Restore one dump (the DEK must be unwrapped first, so this needs the master):

    $REPO_DIR/infra/backups/scripts/tt-keys.sh unlock general:2026Q4 --out /dev/shm/general.key
    age -d -i /dev/shm/general.key <file>.dump.age \\
      | pg_restore --clean --if-exists -d <target_db>
    shred -u /dev/shm/general.key
-----------------------------------------------------------------------------
NEXT
