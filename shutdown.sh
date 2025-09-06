#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_modify_date: 2025-09-05 20:33:05 %
#  %ccm_git_author:  %
#  %ccm_git_author_email:  %
#  %ccm_git_repo:  %
#  %ccm_git_branch:  %
#  %ccm_git_object_id: :0 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_file_last_modified:  %
#  %ccm_git_file_name:  %
#  %ccm_git_file_type:  %
#  %ccm_git_file_encoding:  %
#  %ccm_git_file_eol:  %
#  %ccm_git_path:  %
#  %ccm_git_blob_sha: ca1805011eeadea3ed05d372d9d749bcd0aa0d93 %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1571 %
#  %ccm_git_tag:  %
#  %ccm_git_language_mode: shellscript %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_modify_date: 2025-09-05 20:33:05 %
#  %ccm_git_author:  %
#  %ccm_git_author_email:  %
#  %ccm_git_repo:  %
#  %ccm_git_branch:  %
#  %ccm_git_object_id: :0 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_file_last_modified:  %
#  %ccm_git_file_name:  %
#  %ccm_git_file_type:  %
#  %ccm_git_file_encoding:  %
#  %ccm_git_file_eol:  %
#  %ccm_git_path:  %
#  %ccm_git_blob_sha: ca1805011eeadea3ed05d372d9d749bcd0aa0d93 %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1571 %
#  %ccm_git_tag:  %
#  %ccm_git_language_mode: shellscript %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
 
pkill -f "wyoming-faster-whisper/script/run"
pkill -f "wyoming-piper/script/run"
pkill -f "ollama serve"
pkill -f "llm_server/handlers/home_assistant.py"
docker stop open-webui lobechat >> "$LOG_FILE" 2>&1
# Wrapper: forward to moved script
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
TARGET="$SCRIPT_DIR/scripts/system/shutdown.sh"
if [[ -f "$TARGET" ]]; then
	exec "$TARGET" "$@"
else
	echo "Moved script not found: $TARGET" >&2
	exit 1
fi
