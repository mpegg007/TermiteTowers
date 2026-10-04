#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy-prometheus-tensorflow.sh:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0f17188aba1038a3db7ad549e9f460cf4cae852b %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
#  %ccm_git_file_name: deploy-prometheus-tensorflow.sh %
#  %ccm_git_path: scripts/deploy-prometheus-tensorflow.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6378 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

set -euo pipefail

# Deploy Prometheus and TensorFlow Docker Services
# This script automates the setup process from wiki/how-to-add-docker-app.md

REPO_ROOT="/home/mpegg-adm/source/TermiteTowers"
STORAGE_ROOT="/mnt/ai_storage"
USER_ID="2001"
GROUP_ID="1006"

echo "=========================================="
echo "Prometheus & TensorFlow Deployment Script"
echo "=========================================="

# Function to setup a service
setup_service() {
    local SERVICE=$1
    local COMPOSE_FILE=$2
    local PORT=$3
    local EXTRA_SETUP=${4:-}
    
    echo ""
    echo "Setting up ${SERVICE}..."
    echo "---"
    
    # 1. Create data directories
    echo "[1/7] Creating data directories..."
    if [ "$SERVICE" == "prometheus" ]; then
        sudo mkdir -p "${STORAGE_ROOT}/${SERVICE}/data"
        sudo mkdir -p "${STORAGE_ROOT}/${SERVICE}/config"
    elif [ "$SERVICE" == "tensorflow" ]; then
        sudo mkdir -p "${STORAGE_ROOT}/${SERVICE}/notebooks"
        sudo mkdir -p "${STORAGE_ROOT}/${SERVICE}/data"
        sudo mkdir -p "${STORAGE_ROOT}/${SERVICE}/models"
    fi
    
    sudo chown -R ${USER_ID}:${GROUP_ID} "${STORAGE_ROOT}/${SERVICE}"
    sudo chmod -R u+rwX,g+rwX "${STORAGE_ROOT}/${SERVICE}"
    echo "✓ Data directories created and permissions set"
    
    # 2. Extra setup (configs, env files, etc.)
    if [ -n "$EXTRA_SETUP" ]; then
        echo "[2/7] Running extra setup..."
        eval "$EXTRA_SETUP"
        echo "✓ Extra setup completed"
    else
        echo "[2/7] No extra setup needed"
    fi
    
    # 3. Create /srv/dev1 convenience path
    echo "[3/7] Creating /srv/dev1 convenience path..."
    sudo mkdir -p "/srv/dev1/${SERVICE}/docker"
    sudo ln -sf "${REPO_ROOT}/infra/docker/${COMPOSE_FILE}" \
                "/srv/dev1/${SERVICE}/docker/${COMPOSE_FILE}"
    echo "✓ Symlink created at /srv/dev1/${SERVICE}/docker/${COMPOSE_FILE}"
    
    # 4. Start the container
    echo "[4/7] Starting Docker container..."
    docker compose -f "${REPO_ROOT}/infra/docker/${COMPOSE_FILE}" up -d
    echo "✓ Container started"
    
    # 5. Enable Nginx site
    echo "[5/7] Enabling Nginx site..."
    if [ -f "${REPO_ROOT}/scripts/nginx-enable-site.sh" ]; then
        bash "${REPO_ROOT}/scripts/nginx-enable-site.sh" \
            "${REPO_ROOT}/infra/nginx/sites-available/${SERVICE}.conf" \
            "${SERVICE}"
    else
        echo "⚠ nginx-enable-site.sh not found, skipping automatic enable"
        echo "  Manual command: sudo ln -sf ${REPO_ROOT}/infra/nginx/sites-available/${SERVICE}.conf /etc/nginx/sites-enabled/${SERVICE}"
    fi
    
    # 6. Test Nginx config
    echo "[6/7] Testing Nginx configuration..."
    sudo nginx -t && sudo systemctl reload nginx || echo "⚠ Nginx test failed - check configuration"
    
    # 7. Verify container
    echo "[7/7] Verifying container..."
    sleep 3
    docker logs --tail 20 "${SERVICE}-dev1"
    
    echo ""
    echo "✓ ${SERVICE} setup complete!"
    echo "  Container: ${SERVICE}-dev1"
    echo "  Port: ${PORT}"
    echo "  URL: https://${SERVICE}.termitetowers.ca"
    echo "  Logs: docker logs -f ${SERVICE}-dev1"
}

# ========================================
# PROMETHEUS SETUP
# ========================================
PROMETHEUS_EXTRA_SETUP='
# Create basic prometheus.yml config
cat > /tmp/prometheus.yml << "EOF"
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: "termitetowers"
    environment: "dev1"

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
  
  - job_name: "node-exporter"
    static_configs:
      - targets: ["localhost:9100"]
        labels:
          instance: "monolith"
  
  - job_name: "docker"
    static_configs:
      - targets: ["172.17.0.1:9323"]
EOF

sudo cp /tmp/prometheus.yml "${STORAGE_ROOT}/prometheus/config/prometheus.yml"
sudo chown ${USER_ID}:${GROUP_ID} "${STORAGE_ROOT}/prometheus/config/prometheus.yml"
rm /tmp/prometheus.yml
echo "✓ Prometheus config created"
'

setup_service "prometheus" "prometheus-dev1.yml" "3720" "$PROMETHEUS_EXTRA_SETUP"

# ========================================
# TENSORFLOW SETUP
# ========================================
TENSORFLOW_EXTRA_SETUP='
# Generate Jupyter token
TOKEN=$(openssl rand -hex 32)
cat > "${REPO_ROOT}/infra/docker/env/tensorflow.env" << EOF
# TensorFlow Jupyter Configuration
JUPYTER_TOKEN=${TOKEN}
EOF

sudo chown ${USER_ID}:${GROUP_ID} "${REPO_ROOT}/infra/docker/env/tensorflow.env"
sudo chmod 640 "${REPO_ROOT}/infra/docker/env/tensorflow.env"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠  SAVE THIS JUPYTER TOKEN!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Token: ${TOKEN}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Also saved to: ${REPO_ROOT}/infra/docker/env/tensorflow.env"
echo ""
'

setup_service "tensorflow" "tensorflow-dev1.yml" "3810" "$TENSORFLOW_EXTRA_SETUP"

# ========================================
# FINAL STEPS
# ========================================
echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Add DNS CNAME records:"
echo "     - prometheus.termitetowers.ca -> imono.termitetowers.ca"
echo "     - tensorflow.termitetowers.ca -> imono.termitetowers.ca"
echo ""
echo "  2. Update wiki/ports.md with:"
echo "     - Prometheus: 3720 (Monitoring & Ops)"
echo "     - TensorFlow: 3810 (AI & ML)"
echo ""
echo "  3. Add tiles to chat dashboard:"
echo "     - Edit: ${REPO_ROOT}/infra/nginx/www/chat/index.html"
echo "     - Deploy: bash ${REPO_ROOT}/scripts/deploy-www.sh"
echo ""
echo "Access URLs:"
echo "  Prometheus: https://prometheus.termitetowers.ca"
echo "  TensorFlow: https://tensorflow.termitetowers.ca"
echo ""
echo "Useful commands:"
echo "  docker logs -f prometheus-dev1"
echo "  docker logs -f tensorflow-dev1"
echo "  docker compose -f /srv/dev1/prometheus/docker/prometheus-dev1.yml restart"
echo "  docker compose -f /srv/dev1/tensorflow/docker/tensorflow-dev1.yml restart"
echo ""
