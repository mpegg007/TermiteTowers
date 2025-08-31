#!/bin/bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/startup.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:34 %
# % ccm_file_name: startup.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: utf-8 %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/startup.sh %
# % ccm_blob_sha: 70d8673a9b4756facd7f358470026b2ec1f3803a %
# % ccm_exec: yes %
# % ccm_size: 3554 %
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
PIPER_SCRIPT="/srv/dev1/piper/script/run"
PIPER_BIN="/srv/dev1/piper/piper"
if [ ! -f "$PIPER_SCRIPT" ]; then
  PIPER_SCRIPT="$HOME/wyoming-piper/script/run"
  PIPER_BIN="$HOME/piper/piper"
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
  if [[ "$PIPER_SCRIPT" == /srv/dev1/* ]]; then
    :
  else
    source "$HOME/wyoming-piper/.venv/bin/activate"
  fi
  "$PIPER_SCRIPT" \
    --piper "$PIPER_BIN" \
    --voice en_US-lessac-medium \
    --uri 'tcp://0.0.0.0:10200' \
    --data-dir "$HOME/piper-data" \
    --download-dir "$HOME/piper-data" >> "$LOG_FILE" 2>&1 &
  if [[ "$PIPER_SCRIPT" == /srv/dev1/* ]]; then
    :
  else
    deactivate
  fi
else
  echo "❌ Piper script not found at $PIPER_SCRIPT" | tee -a "$LOG_FILE"
fi

# Start Ollama
echo "🧠 Starting Ollama..." | tee -a "$LOG_FILE"
ollama serve >> "$LOG_FILE" 2>&1 &

# Start Home Assistant integration
if [ -f "$LLM_HANDLER" ]; then
  echo "🟢 Starting Home Assistant integration..." | tee -a "$LOG_FILE"
  /bin/python3 "$LLM_HANDLER" >> "$LOG_FILE" 2>&1 &
else
  echo "❌ Home Assistant handler not found at $LLM_HANDLER" | tee -a "$LOG_FILE"
fi

# Wait for services to initialize
sleep 5

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
check_port 11434  # Ollama
check_port 5000   # Flask (Home Assistant integration)

# Start Open WebUI
echo "🖥️ Starting Open WebUI container..." | tee -a "$LOG_FILE"
echo docker rm -f open-webui 2>/dev/null
echo docker run -d \
  --name open-webui \
  -p 3000:3000 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_API_BASE_URL=http://host.docker.internal:11434 \
  -e MODEL_PROVIDER=ollama \
  -e DEFAULT_MODEL=llama3 \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main >> "$LOG_FILE" 2>&1

# Done
echo "✅ All services started." | tee -a "$LOG_FILE"
echo "🌐 Open WebUI: http://monolith.tt.omp:3000" | tee -a "$LOG_FILE"
