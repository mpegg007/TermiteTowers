#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 093ece29968a6b6725391001f971fa0853afc95e %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-11-30 12:10:12 %
#  %ccm_git_file_last_modified: 2025-11-30 12:10:12 %
#  %ccm_git_file_name: migrate-to-tt-naming.sh %
#  %ccm_git_path: infra/dhcp/scripts/deploy/migrate-to-tt-naming.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6365 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Migration script to rename Kea configs to tt- naming standard
# This is a ONE-TIME migration script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG_DIR="$PROJECT_ROOT/configs/kea"
BACKUP_DIR="/tmp/kea-config-backup-$(date +%Y%m%d-%H%M%S)"

LOG_FILE="/var/log/tt-kea-config-migration.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

log "=== Starting Kea Config Migration to tt- Naming Standard ==="
log "Backup directory: $BACKUP_DIR"

# Create backup
mkdir -p "$BACKUP_DIR"
log "Creating backups..."

# Backup source configs
if [ -f "$CONFIG_DIR/kea-dhcp4-multiscope.conf" ]; then
    cp "$CONFIG_DIR/kea-dhcp4-multiscope.conf" "$BACKUP_DIR/"
    log "✓ Backed up kea-dhcp4-multiscope.conf"
fi

if [ -f "$CONFIG_DIR/kea-dhcp-ddns.conf" ]; then
    cp "$CONFIG_DIR/kea-dhcp-ddns.conf" "$BACKUP_DIR/"
    log "✓ Backed up kea-dhcp-ddns.conf"
fi

if [ -f "$CONFIG_DIR/kea-dhcp4-nodb.conf" ]; then
    cp "$CONFIG_DIR/kea-dhcp4-nodb.conf" "$BACKUP_DIR/"
    log "✓ Backed up kea-dhcp4-nodb.conf"
fi

# Backup deployed configs
if [ -f "/etc/kea/kea-dhcp4.conf" ]; then
    sudo cp /etc/kea/kea-dhcp4.conf "$BACKUP_DIR/deployed-kea-dhcp4.conf"
    log "✓ Backed up deployed /etc/kea/kea-dhcp4.conf"
fi

if [ -f "/etc/kea/kea-dhcp-ddns.conf" ]; then
    sudo cp /etc/kea/kea-dhcp-ddns.conf "$BACKUP_DIR/deployed-kea-dhcp-ddns.conf"
    log "✓ Backed up deployed /etc/kea/kea-dhcp-ddns.conf"
fi

log "=== Renaming source config files ==="

# Rename in source
cd "$CONFIG_DIR"

if [ -f "kea-dhcp4-multiscope.conf" ]; then
    git mv kea-dhcp4-multiscope.conf tt-kea-dhcp4-dev1.conf
    log "✓ Renamed kea-dhcp4-multiscope.conf → tt-kea-dhcp4-dev1.conf"
fi

if [ -f "kea-dhcp-ddns.conf" ]; then
    git mv kea-dhcp-ddns.conf tt-kea-dhcp-ddns-dev1.conf
    log "✓ Renamed kea-dhcp-ddns.conf → tt-kea-dhcp-ddns-dev1.conf"
fi

if [ -f "kea-dhcp4-nodb.conf" ]; then
    git mv kea-dhcp4-nodb.conf tt-kea-dhcp4-dev1-nodb.conf
    log "✓ Renamed kea-dhcp4-nodb.conf → tt-kea-dhcp4-dev1-nodb.conf"
fi

log "=== Updating deployment scripts ==="

# Update deploy-kea-config.sh
DEPLOY_SCRIPT="$PROJECT_ROOT/scripts/deploy/deploy-kea-config.sh"
if [ -f "$DEPLOY_SCRIPT" ]; then
    sed -i 's|kea-dhcp4-multiscope\.conf|tt-kea-dhcp4-dev1.conf|g' "$DEPLOY_SCRIPT"
    sed -i 's|/etc/kea/kea-dhcp4\.conf|/etc/kea/tt-kea-dhcp4-dev1.conf|g' "$DEPLOY_SCRIPT"
    log "✓ Updated deploy-kea-config.sh"
fi

# Update deploy-kea-ddns.sh
DEPLOY_DDNS_SCRIPT="$PROJECT_ROOT/scripts/deploy/deploy-kea-ddns.sh"
if [ -f "$DEPLOY_DDNS_SCRIPT" ]; then
    sed -i 's|kea-dhcp-ddns\.conf|tt-kea-dhcp-ddns-dev1.conf|g' "$DEPLOY_DDNS_SCRIPT"
    sed -i 's|/etc/kea/kea-dhcp-ddns\.conf|/etc/kea/tt-kea-dhcp-ddns-dev1.conf|g' "$DEPLOY_DDNS_SCRIPT"
    log "✓ Updated deploy-kea-ddns.sh"
fi

log "=== Deploying renamed configs ==="

# Deploy to /etc/kea with new names
sudo cp "$CONFIG_DIR/tt-kea-dhcp4-dev1.conf" /etc/kea/tt-kea-dhcp4-dev1.conf
sudo chown root:root /etc/kea/tt-kea-dhcp4-dev1.conf
sudo chmod 644 /etc/kea/tt-kea-dhcp4-dev1.conf
log "✓ Deployed tt-kea-dhcp4-dev1.conf to /etc/kea/"

sudo cp "$CONFIG_DIR/tt-kea-dhcp-ddns-dev1.conf" /etc/kea/tt-kea-dhcp-ddns-dev1.conf
sudo chown root:root /etc/kea/tt-kea-dhcp-ddns-dev1.conf
sudo chmod 644 /etc/kea/tt-kea-dhcp-ddns-dev1.conf
log "✓ Deployed tt-kea-dhcp-ddns-dev1.conf to /etc/kea/"

log "=== Updating systemd services ==="

# Update kea-dhcp4-dev1.service
cat <<'SYSTEMD_EOF' | sudo tee /etc/systemd/system/kea-dhcp4-dev1.service
[Unit]
Description=Kea DHCPv4 Server (dev1)
After=network.target postgresql.service
Requires=postgresql.service
OnFailure=tt-kea-watchdog-dev1.service

[Service]
ExecStart=/usr/sbin/kea-dhcp4 -c /etc/kea/tt-kea-dhcp4-dev1.conf
Restart=on-failure
RestartSec=10
User=root
Group=root

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

log "✓ Updated kea-dhcp4-dev1.service to use tt-kea-dhcp4-dev1.conf"

# Update kea-dhcp-ddns service if it exists
if systemctl list-unit-files | grep -q kea-dhcp-ddns.service; then
    cat <<'SYSTEMD_EOF' | sudo tee /etc/systemd/system/kea-dhcp-ddns-dev1.service
[Unit]
Description=Kea DHCP-DDNS Server (dev1)
After=network.target

[Service]
ExecStart=/usr/sbin/kea-dhcp-ddns -c /etc/kea/tt-kea-dhcp-ddns-dev1.conf
Restart=on-failure
User=root
Group=root

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF
    log "✓ Updated kea-dhcp-ddns-dev1.service to use tt-kea-dhcp-ddns-dev1.conf"
fi

# Reload systemd
sudo systemctl daemon-reload
log "✓ Reloaded systemd"

log "=== Restarting services ==="

# Restart services
sudo systemctl restart kea-dhcp4-dev1.service
log "✓ Restarted kea-dhcp4-dev1.service"

if systemctl is-active --quiet kea-dhcp-ddns-dev1.service; then
    sudo systemctl restart kea-dhcp-ddns-dev1.service
    log "✓ Restarted kea-dhcp-ddns-dev1.service"
fi

sleep 3

log "=== Verifying services ==="

if systemctl is-active --quiet kea-dhcp4-dev1.service; then
    log "✓ kea-dhcp4-dev1.service is active"
else
    error_exit "kea-dhcp4-dev1.service failed to start!"
fi

log "=== Running health check ==="
if /srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh; then
    log "✓ Health check PASSED"
else
    log "⚠ Health check reported issues (check /var/log/tt-kea-health-check-dev1.log)"
fi

log "=== Migration Complete ==="
log ""
log "SUMMARY:"
log "  ✓ Old configs backed up to: $BACKUP_DIR"
log "  ✓ Source configs renamed with tt- prefix and -dev1 suffix"
log "  ✓ Deployed configs to /etc/kea/"
log "  ✓ Updated systemd services"
log "  ✓ Services restarted and running"
log ""
log "OLD FILES (can be removed after verification):"
log "  - /etc/kea/kea-dhcp4.conf (replaced by tt-kea-dhcp4-dev1.conf)"
log "  - /etc/kea/kea-dhcp-ddns.conf (replaced by tt-kea-dhcp-ddns-dev1.conf)"
log ""
log "NEXT STEPS:"
log "  1. Verify DHCP is working: sudo journalctl -u kea-dhcp4-dev1.service -n 20"
log "  2. Check for lease allocations: sudo tail -f /var/log/kea/kea-dhcp4.log"
log "  3. Commit changes: cd $PROJECT_ROOT && git add -A && git commit -m 'Migrate Kea configs to tt- naming standard'"
log "  4. After 24 hours, remove old deployed configs: sudo rm /etc/kea/kea-dhcp{4,-ddns}.conf"

exit 0
