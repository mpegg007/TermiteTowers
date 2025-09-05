#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_modify_date: 2025-08-29 07:37:53 %
#  %ccm_git_author: CCM Maintainer %
#  %ccm_git_author_email: ccm@test %
#  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
#  %ccm_git_branch: main %
#  %ccm_git_object_id: <PATH>:0 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
#  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
#  %ccm_git_exec: no %
#  %ccm_git_size: 659 %
#  %ccm_git_tag:  %
#  %ccm_git_language_mode:  %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
 TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
 %ccm_git_modify_date: 2025-08-29 07:37:53 %
 %ccm_git_author: CCM Maintainer %
 %ccm_git_author_email: ccm@test %
 %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
 %ccm_git_branch: main %
 %ccm_git_object_id: <PATH>:0 %
 %ccm_git_commit_id: unknown %
 %ccm_git_commit_count: 0 %
 %ccm_git_commit_message: unknown %
 %ccm_git_commit_author: unknown %
 %ccm_git_commit_email: unknown %
 %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
 %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
 %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
 %ccm_git_file_type: text/plain %
 %ccm_git_file_encoding: us-ascii %
 %ccm_git_file_eol: CRLF %
 %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
 %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
 %ccm_git_exec: no %
 %ccm_git_size: 659 %
 %ccm_git_tag:  %
 %ccm_git_language_mode:  %
 TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 

pkill -f "wyoming-faster-whisper/script/run"
pkill -f "wyoming-piper/script/run"
pkill -f "ollama serve"
pkill -f "llm_server/handlers/home_assistant.py"
docker stop open-webui lobechat >> "$LOG_FILE" 2>&1
#!/usr/bin/env bash
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
