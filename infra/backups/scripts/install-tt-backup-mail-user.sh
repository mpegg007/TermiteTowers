#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/install-tt-backup-mail-user.sh@186 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5c27725ff412ad701ecfbb75d204232abdc98bd3 %
#  %ccm_git_commit_id: 39d8262239b8cbb295886dbe654023e96f65ada9 %
#  %ccm_git_commit_count: 186 %
#  %ccm_git_commit_date: 2026-10-28 11:35:25 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 3 - encrypt to per-tier keys %
#  %ccm_git_modify_date: 2026-10-28 11:35:26 %
#  %ccm_git_file_last_modified: 2026-10-28 11:35:01 %
#  %ccm_git_file_name: install-tt-backup-mail-user.sh %
#  %ccm_git_path: infra/backups/scripts/install-tt-backup-mail-user.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 3156 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# Install the Thunderbird mail archive as a systemd USER timer.
#
# RUN AS YOURSELF - no sudo anywhere:
#
#     infra/backups/scripts/install-tt-backup-mail-user.sh
#
# What it does:
#   1. creates the archive directory (0700) - /mnt/ai_storage/backups/thunderbird
#   2. installs tt-backup-mail.{service,timer} into ~/.config/systemd/user/
#      with @REPO_DIR@ resolved to this checkout
#   3. systemctl --user daemon-reload + enable --now the timer
#
# What it CANNOT do for you (printed at the end):
#   * the first full archive (it takes a while - run it yourself)
#   * tell Jotta about the folder (jotta-cli runs as you, not root)
#
# Idempotent: safe to re-run, and it is also the deploy path after edits.
# ---------------------------------------------------------------------------
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_DIR="${OUT_DIR:-/mnt/ai_storage/backups/thunderbird}"
UNIT_SRC="$REPO_DIR/infra/systemd/user"
UNIT_DST="$HOME/.config/systemd/user"
UNITS=(tt-backup-mail.service tt-backup-mail.timer)

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }
run() { printf '   + %s\n' "$*"; "$@"; }

if [ "$(id -u)" -eq 0 ]; then
    die "run as your own account, not root - user timers must be owned by you"
fi

step "1. archive directory ($OUT_DIR)"
run mkdir -p "$OUT_DIR"
run chmod 0700 "$OUT_DIR"

step "2. systemd user units -> $UNIT_DST"
run mkdir -p "$UNIT_DST"
for unit in "${UNITS[@]}"; do
    [ -f "$UNIT_SRC/$unit" ] || die "missing $UNIT_SRC/$unit"
    sed "s|@REPO_DIR@|$REPO_DIR|g" "$UNIT_SRC/$unit" > "$UNIT_DST/$unit"
    run chmod 0644 "$UNIT_DST/$unit"
done

step "3. enable the timer"
run systemctl --user daemon-reload
run systemctl --user enable --now "${UNITS[1]}"
systemctl --user list-timers --all 2>/dev/null | grep -E 'tt-backup-mail|NEXT' || true

cat <<NEXT

-----------------------------------------------------------------------------
INSTALLED. Two things left, both as your own account:

1) First archive (full history - expect several minutes, ~10 GB encrypted):
     $REPO_DIR/infra/backups/scripts/backup-mail.py --dry-run   # see the plan
     $REPO_DIR/infra/backups/scripts/backup-mail.py             # build it

2) Jotta (no root involved - jottad already runs as you):
     jotta-cli add $OUT_DIR
     jotta-cli scan

Verify:
     systemctl --user list-timers tt-backup-mail.timer
     $REPO_DIR/infra/backups/scripts/backup-mail.py --list
     jotta-cli status

Restore one year (two steps - unwrap the mail DEK first):
     $REPO_DIR/infra/backups/scripts/tt-keys.sh unlock mail:2026Q4 --out /dev/shm/mail.key
     age -d -i /dev/shm/mail.key $OUT_DIR/mail-2018.tar.zst.age \\
       | zstd -d | tar -xf - -C /tmp/mail-restore
     # each member is an mbox fragment: 2018/ImapMail/<server>/<folder>
     # 'shred -u /dev/shm/mail.key' when done
     # chunks sealed before the cutover are "legacy": use ~/.config/age/tthealth-backup.txt
-----------------------------------------------------------------------------
NEXT
