#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/scripts/pull-journal.sh:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 276c1be37382fee0bc90df8c54384b43b4b2694d %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
#  %ccm_git_file_name: pull-journal.sh %
#  %ccm_git_path: infra/logCollector/scripts/pull-journal.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2071 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: dhcp logging % 
set -euo pipefail

# Usage: pull-journal-proper.sh <host> [--full]
# Pulls only new journal entries since last timestamp, stores marker per host

HOST="$1"
ARG2="${2:-}" # Optional second argument
HOST_RAW="${HOST#*@}"
BASE_LOG_DIR="/mnt/ai_storage/logCollector/logs/$HOST_RAW/drop"
MARKER_DIR="/mnt/ai_storage/logCollector/logs/$HOST_RAW/markers"
MARKER_FILE="$MARKER_DIR/last_journal_timestamp"
OUT_DIR="$BASE_LOG_DIR"
OUT_FILE="$OUT_DIR/journal.log"
mkdir -p "$MARKER_DIR" "$OUT_DIR"

# Logging function
log() {
    echo "[$(date --utc '+%Y-%m-%d %H:%M:%S UTC')] $*"
}

log "---"
log "Script: pull-journal-proper.sh"
log "Start date: $(date --utc '+%Y-%m-%d %H:%M:%S UTC')"
log "Args: $*"
log "Host: $HOST"
log "Marker file: $MARKER_FILE"


# Determine last timestamp
if [ "$ARG2" = "--full" ]; then
    LAST_TIMESTAMP="1970-01-01 00:00:00"
    log "--full specified, using default: $LAST_TIMESTAMP"
elif [ -f "$MARKER_FILE" ]; then
    LAST_TIMESTAMP=$(cat "$MARKER_FILE")
    log "Previous marker value: $LAST_TIMESTAMP"
else
    LAST_TIMESTAMP=$(date --utc --date='1 hour ago' '+%Y-%m-%d %H:%M:%S')
    log "No marker found, using default: $LAST_TIMESTAMP"
fi

# Fetch new journal entries since last timestamp
TMPFILE="$(mktemp)"
log "Fetching journal entries since: $LAST_TIMESTAMP"
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "journalctl -o short-iso --utc --no-pager --since='${LAST_TIMESTAMP}'" > "$TMPFILE" || true

if [ ! -s "$TMPFILE" ]; then
    log "No new journal entries found."
    rm -f "$TMPFILE"
    exit 0
fi

# Append new entries to journal.log
cat "$TMPFILE" >> "$OUT_FILE"
lines=$(wc -l < "$TMPFILE")
log "Fetched $lines new journal entries and appended to $OUT_FILE."

# Update marker with latest timestamp from pulled entries
LATEST_TS=$(awk '{print $1}' "$TMPFILE" | tail -1)
if [ -n "$LATEST_TS" ]; then
    echo "$LATEST_TS" > "$MARKER_FILE"
    log "Updated marker to: $LATEST_TS"
fi

rm -f "$TMPFILE"
log "Completed fetching and processing journal entries."
log "End date: $(date --utc '+%Y-%m-%d %H:%M:%S UTC')"
