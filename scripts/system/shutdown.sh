#!/bin/bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/shutdown.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:34 %
# % ccm_file_name: shutdown.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: utf-8 %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/shutdown.sh %
# % ccm_blob_sha: 8a7612e959f8427519cb4ccc271e6c26f83c3d81 %
# % ccm_exec: yes %
# % ccm_size: 1735 %
# % ccm_tag:  %
# tt-ccm.header.end


LOG_FILE="$HOME/shutdown.log"
echo "🛑 Shutting down services at $(date)" > "$LOG_FILE"

# Stop Whisper
echo "🔻 Stopping Whisper STT..." | tee -a "$LOG_FILE"
pkill -f "wyoming-faster-whisper/script/run" || true

# Stop Piper
echo "🔻 Stopping Piper TTS..." | tee -a "$LOG_FILE"
pkill -f "wyoming-piper/script/run" || true

# Stop Ollama
echo "🔻 Stopping Ollama..." | tee -a "$LOG_FILE"
pkill -f "ollama serve" || true

# Stop Home Assistant integration
echo "🔻 Stopping Home Assistant integration..." | tee -a "$LOG_FILE"
pkill -f "llm_server/handlers/home_assistant.py" || true

# Stop Docker containers
echo "🔻 Stopping Docker containers..." | tee -a "$LOG_FILE"
docker stop open-webui lobechat >> "$LOG_FILE" 2>&1 || true
docker rm open-webui lobechat >> "$LOG_FILE" 2>&1 || true

# Done
echo "✅ All services stopped." | tee -a "$LOG_FILE"
