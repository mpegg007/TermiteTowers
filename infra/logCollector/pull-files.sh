#!/bin/bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/pull-files.sh:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: f4cd22e4c8d337a0a34dae839d177e95beabe463 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2025-10-23 18:38:13 %
#  %ccm_git_file_name: pull-files.sh %
#  %ccm_git_path: infra/logCollector/pull-files.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1094 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# id_ed25519_<hostname>_<username>
# keyname="id_ed25519_$(hostname)_$(whoami)"
# ssh-keygen -t ed25519 -C "$(whoami)@$(hostname)" -f ~/.ssh/$keyname
# ssh-copy-id -i ~/.ssh/$keyname.pub username@remote_host
set -euo pipefail

HOST="$1"
REMOTE_FILE="$2"

BASE_LOG_DIR="/mnt/ai_storage/logCollector/logs/$HOST/drop"
MARKER_DIR="/mnt/ai_storage/logCollector/logs/$HOST/markers"
OUT_DIR="$BASE_LOG_DIR"
SQLITE_DB="/mnt/ai_storage/logCollector/logs/dedupe.db"
mkdir -p "$MARKER_DIR" "$OUT_DIR" "$(dirname "$SQLITE_DB")"
OFFSET_FILE="$MARKER_DIR/$(basename "$REMOTE_FILE").offset"

OFFSET="$(cat "$OFFSET_FILE" 2>/dev/null || echo 0)"
TMPFILE="$(mktemp)"

ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "awk 'NR>$OFFSET' \"$REMOTE_FILE\"" > "$TMPFILE" || true

if [ ! -s "$TMPFILE" ]; then
  rm -f "$TMPFILE"
  exit 0
fi

cat "$TMPFILE" | ./dedupe-ingest.py "$SQLITE_DB" "$OUT_DIR/archive.log"

NEW_OFFSET="$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "wc -l < $REMOTE_FILE" 2>/dev/null)"
if [ -n "$NEW_OFFSET" ]; then
  echo "$NEW_OFFSET" > "$OFFSET_FILE"
fi
rm -f "$TMPFILE"
