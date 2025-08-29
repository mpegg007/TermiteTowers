# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: shutdown.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:34 %
# % ccm_file_name: shutdown.sh %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: shutdown.sh %
# % ccm_blob_sha: 153f02455492fe84931f25d1adb1357f194442e0 %
# % ccm_exec: yes %
# % ccm_size: 1333 %
# % ccm_tag:  %
# tt-ccm.header.end

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
