#!/bin/bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-09-01 15:47:13 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/startup.sh:68 %
# % ccm_commit_id: fe785a319b8d06e69d2978b17dc9bb8512161977 %
# % ccm_commit_count: 68 %
# % ccm_commit_message: misc updated %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-09-01 15:47:12 -0400 %
# % ccm_file_last_modified: 2025-09-01 15:47:12 %
# % ccm_file_name: startup.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: utf-8 %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/startup.sh %
# % ccm_blob_sha: 256daafbe745eebb8b3addb1269673659541aabb %
# % ccm_exec: yes %
# % ccm_size: 4276 %
# % ccm_tag:  %
# tt-ccm.header.end


LOG_FILE="$HOME/startup.log"
echo "🔄 Starting services at $(date)" > "$LOG_FILE"

# Define paths
# Prefer the original user-space run script (known-good); fall back to /srv if missing
WHISPER_SCRIPT="$HOME/wyoming-faster-whisper/script/run"
if [ ! -f "$WHISPER_SCRIPT" ]; then
  WHISPER_SCRIPT="/srv/dev1/whisper/script/run"
fi
PIPER_SCRIPT="$HOME/wyoming-piper/script/run"
PIPER_BIN="$HOME/piper/piper"
if [ ! -f "$PIPER_SCRIPT" ]; then
  PIPER_SCRIPT="/srv/dev1/piper/script/run"
  PIPER_BIN="/srv/dev1/piper/piper"
fi
LLM_HANDLER="/home/mpegg-adm/source/llm-server/llm_server/handlers/home_assistant.py"

# Start Whisper (STT)
if [ -f "$WHISPER_SCRIPT" ]; then
  echo "🟢 Starting Whisper STT..." | tee -a "$LOG_FILE"
  if [[ "$WHISPER_SCRIPT" == /home/* ]]; then
    source "$HOME/wyoming-faster-whisper/.venv/bin/activate"
  else
    : # /srv path uses its own venv via the run script
  fi
  if [[ "$WHISPER_SCRIPT" == "$HOME"/* ]]; then
    # Original user-space invocation
    "$WHISPER_SCRIPT" \
      --model base \
      --language en \
      --uri 'tcp://0.0.0.0:10300' \
      --data-dir "$HOME/whisper-data" \
      --download-dir "$HOME/whisper-data" >> "$LOG_FILE" 2>&1 &
  else
    # System path invocation, use system data dir
    "$WHISPER_SCRIPT" \
      --model base \
      --uri 'tcp://0.0.0.0:10300' \
      --download-dir "/srv/dev1/whisper/data" >> "$LOG_FILE" 2>&1 &
  fi
  if [[ "$WHISPER_SCRIPT" == /home/* ]]; then
    deactivate
  else
    :
  fi
else
  echo "❌ Whisper script not found at $WHISPER_SCRIPT" | tee -a "$LOG_FILE"
fi

# Start Piper (TTS)
if [ -f "$PIPER_SCRIPT" ]; then
  echo "🟢 Starting Piper TTS..." | tee -a "$LOG_FILE"
  if [[ "$PIPER_SCRIPT" == /home/* ]]; then
    source "$HOME/wyoming-piper/.venv/bin/activate"
  else
    : # /srv path uses its own venv via the run script
  fi
  if [[ "$PIPER_SCRIPT" == "$HOME"/* ]]; then
    # Original user-space invocation
    "$PIPER_SCRIPT" \
      --piper "$PIPER_BIN" \
      --voice en_US-lessac-medium \
      --uri 'tcp://0.0.0.0:10200' \
      --data-dir "$HOME/piper-data" \
      --download-dir "$HOME/piper-data" >> "$LOG_FILE" 2>&1 &
  else
    # System path invocation, use system data dir
    "$PIPER_SCRIPT" \
      --piper "$PIPER_BIN" \
      --voice en_US-lessac-medium \
      --uri 'tcp://0.0.0.0:10200' \
      --data-dir "/srv/dev1/piper/data" \
      --download-dir "/srv/dev1/piper/data" >> "$LOG_FILE" 2>&1 &
  fi
  if [[ "$PIPER_SCRIPT" == /home/* ]]; then
    deactivate
  else
    :
  fi
else
  echo "❌ Piper script not found at $PIPER_SCRIPT" | tee -a "$LOG_FILE"
fi

# Start Home Assistant integration
if [ -f "$LLM_HANDLER" ]; then
  echo "🟢 Starting Home Assistant integration..." | tee -a "$LOG_FILE"
  /bin/python3 "$LLM_HANDLER" >> "$LOG_FILE" 2>&1 &
else
  echo "❌ Home Assistant handler not found at $LLM_HANDLER" | tee -a "$LOG_FILE"
fi

# Health Checks
echo "🔍 Running health checks..." | tee -a "$LOG_FILE"

check_port() {
  local PORT=$1
  nc -z localhost "$PORT"
  if [ $? -eq 0 ]; then
    echo "✅ Port $PORT is open" | tee -a "$LOG_FILE"
  else
    echo "⚠️ Port $PORT is not responding" | tee -a "$LOG_FILE"
  fi
}

check_port 10300  # Whisper
check_port 10200  # Piper
check_port 5000   # Flask (Home Assistant integration)

