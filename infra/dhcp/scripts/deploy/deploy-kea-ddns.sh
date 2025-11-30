#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 2b81ce30e8c42d6596a6ccd75cebcc511bba4873 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-11-30 12:10:11 %
#  %ccm_git_file_last_modified: 2025-11-30 12:10:11 %
#  %ccm_git_file_name: deploy-kea-ddns.sh %
#  %ccm_git_path: infra/dhcp/scripts/deploy/deploy-kea-ddns.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2058 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Deploy Kea DHCP-DDNS configuration to local system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SOURCE_CONFIG="$PROJECT_ROOT/configs/kea/tt-kea-dhcp-ddns-dev1.conf"
DEST_CONFIG="/etc/kea/tt-kea-dhcp-ddns-dev1.conf"
BACKUP_DIR="/etc/kea"
SERVICE_NAME="kea-dhcp-ddns-dev1.service"

echo "===================================================================="
echo "Kea DHCP-DDNS Configuration Deployment"
echo "===================================================================="
echo

# Check if source config exists
if [[ ! -f "$SOURCE_CONFIG" ]]; then
    echo "❌ ERROR: Source config not found: $SOURCE_CONFIG"
    exit 1
fi

# Backup existing config
if [[ -f "$DEST_CONFIG" ]]; then
    BACKUP_FILE="${BACKUP_DIR}/tt-kea-dhcp-ddns-dev1.conf.$(date +%Y%m%d-%H%M%S).bak"
    echo "📦 Backing up existing config to: $BACKUP_FILE"
    sudo cp "$DEST_CONFIG" "$BACKUP_FILE"
fi

# Copy new config
echo "📋 Copying new config to: $DEST_CONFIG"
sudo cp "$SOURCE_CONFIG" "$DEST_CONFIG"

# Set proper ownership
echo "🔒 Setting ownership to _kea:_kea"
sudo chown _kea:_kea "$DEST_CONFIG"

# Check if service exists and restart
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "🔄 Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ Service restarted successfully"
        echo
        sudo systemctl status "$SERVICE_NAME" --no-pager | head -20
    else
        echo "❌ Service failed to start"
        echo
        sudo systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
else
    echo "⚠️  Service $SERVICE_NAME not found - config deployed but not restarted"
fi

echo
echo "===================================================================="
echo "✅ Deployment complete!"
echo "===================================================================="
