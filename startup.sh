#!/bin/bash

LOG_FILE="$HOME/startup.log"
echo "🔄 Starting services at $(date)" > "$LOG_FILE"

# Define paths
WHISPER_SCRIPT="$HOME/wyoming-faster-whisper/script/run"
PIPER_SCRIPT="$HOME/wyoming-piper/script/run"
PIPER_BIN="$HOME/piper/piper"
LLM_HANDLER="/home/mpegg-adm/source/llm-server/llm_server/handlers/home_assistant.py"

# Start Whisper (STT)
if [ -f "$WHISPER_SCRIPT" ]; then
  echo "🟢 Starting Whisper STT..." | tee -a "$LOG_FILE"
  source "$HOME/wyoming-faster-whisper/.venv/bin/activate"
  "$WHISPER_SCRIPT" \
    --model base \
    --language en \
    --uri 'tcp://0.0.0.0:10300' \
    --data-dir "$HOME/whisper-data" \
    --download-dir "$HOME/whisper-data" >> "$LOG_FILE" 2>&1 &
  deactivate
else
  echo "❌ Whisper script not found at $WHISPER_SCRIPT" | tee -a "$LOG_FILE"
fi

# Start Piper (TTS)
if [ -f "$PIPER_SCRIPT" ]; then
  echo "🟢 Starting Piper TTS..." | tee -a "$LOG_FILE"
  source "$HOME/wyoming-piper/.venv/bin/activate"
  "$PIPER_SCRIPT" \
    --piper "$PIPER_BIN" \
    --voice en_US-lessac-medium \
    --uri 'tcp://0.0.0.0:10200' \
    --data-dir "$HOME/piper-data" \
    --download-dir "$HOME/piper-data" >> "$LOG_FILE" 2>&1 &
  deactivate
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

# Step 4: Start Open WebUI
echo "🖥️ Starting Open WebUI container..." | tee -a "$LOG_FILE"
docker rm -f open-webui 2>/dev/null
docker run -d \
  --name open-webui \
  -p 3000:3000 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_API_BASE_URL=http://host.docker.internal:11434 \
  -e MODEL_PROVIDER=ollama \
  -e DEFAULT_MODEL=llama3 \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main >> "$LOG_FILE" 2>&1

# Step 5: Start LobeChat
##echo "💬 Starting LobeChat container..." | tee -a "$LOG_FILE"
##docker rm -f lobechat 2>/dev/null
##docker run -d \
##  --name lobechat \
##  -p 3100:3100 \docker rm -f openwebui-dev1
##  --add-host=host.docker.internal:host-gateway \
##  -e OPENAI_API_BASE_URL=http://host.docker.internal:11434/v1 \
##  -e OPENAI_API_KEY="ollama" \
##  --restart unless-stopped \
##  lobehub/lobe-chat >> "$LOG_FILE" 2>&1


echo "✅ All services started." | tee -a "$LOG_FILE"
echo "🌐 Open WebUI: http://monolith.tt.omp:3000" | tee -a "$LOG_FILE"
echo "💬 LobeChat: http://monolith.tt.omp:3100" | tee -a "$LOG_FILE"
