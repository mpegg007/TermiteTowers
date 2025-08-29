#!/bin/bash

LOG_FILE="$HOME/shutdown.log"
echo "🛑 Shutting down services at $(date)" > "$LOG_FILE"

# Stop Whisper
echo "🔻 Stopping Whisper STT..." | tee -a "$LOG_FILE"
pkill -f "wyoming-faster-whisper/script/run"

# Stop Piper
echo "🔻 Stopping Piper TTS..." | tee -a "$LOG_FILE"
pkill -f "wyoming-piper/script/run"

# Stop Ollama
echo "🔻 Stopping Ollama..." | tee -a "$LOG_FILE"
pkill -f "ollama serve"

# Stop Home Assistant integration
echo "🔻 Stopping Home Assistant integration..." | tee -a "$LOG_FILE"
pkill -f "llm_server/handlers/home_assistant.py"

# Stop Docker containers
echo "🔻 Stopping Docker containers..." | tee -a "$LOG_FILE"
docker stop open-webui lobechat >> "$LOG_FILE" 2>&1
docker rm open-webui lobechat >> "$LOG_FILE" 2>&1

echo "✅ All services stopped." | tee -a "$LOG_FILE"
