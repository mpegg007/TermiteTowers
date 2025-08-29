#!/bin/bash

LOG_FILE="$HOME/docker-setup.log"
echo "🚀 Starting Docker + container setup at $(date)" > "$LOG_FILE"

# Step 1: Install Docker
echo "🐳 Installing Docker..." | tee -a "$LOG_FILE"
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release \
  >> "$LOG_FILE" 2>&1

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin \
  >> "$LOG_FILE" 2>&1

# Step 2: Enable non-root Docker access
echo "👤 Adding user to docker group..." | tee -a "$LOG_FILE"
sudo usermod -aG docker $USER
newgrp docker

# Step 3: Verify Docker
echo "✅ Verifying Docker..." | tee -a "$LOG_FILE"
docker run hello-world >> "$LOG_FILE" 2>&1

# Step 4: Start Open WebUI
echo "🖥️ Starting Open WebUI container..." | tee -a "$LOG_FILE"
docker rm -f open-webui 2>/dev/null
docker run -d \
  --name open-webui \
  -p 3000:3000 \
  -e OLLAMA_API_BASE_URL=http://monolith.tt.omp:11434 \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main >> "$LOG_FILE" 2>&1

# Step 5: Start LobeChat
echo "💬 Starting LobeChat container..." | tee -a "$LOG_FILE"
docker rm -f lobechat 2>/dev/null
docker run -d \
  --name lobechat \
  -p 3100:3100 \
  -e OPENAI_API_BASE_URL=http://monolith.tt.omp:11434/v1 \
  -e OPENAI_API_KEY="ollama" \
  --restart unless-stopped \
  lobehub/lobe-chat >> "$LOG_FILE" 2>&1

echo "✅ Setup complete!" | tee -a "$LOG_FILE"
echo "🌐 Open WebUI: http://monolith.tt.omp:3000" | tee -a "$LOG_FILE"
echo "💬 LobeChat: http://monolith.tt.omp:3100" | tee -a "$LOG_FILE"
