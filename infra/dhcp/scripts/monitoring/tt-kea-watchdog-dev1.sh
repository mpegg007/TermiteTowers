#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh:130 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 604aece44f742c0ed2f70fcd59bce61819b852df %
#  %ccm_git_commit_id: 3395da0009f399bd9abd836085b72ec8a4d7f2f3 %
#  %ccm_git_commit_count: 130 %
#  %ccm_git_commit_date: 2026-02-07 15:49:15 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feb2026.1 %
#  %ccm_git_modify_date: 2026-02-07 15:49:18 %
#  %ccm_git_file_last_modified: 2026-02-07 15:49:18 %
#  %ccm_git_file_name: tt-kea-watchdog-dev1.sh %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1325 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# %git_commit_history: 2025-11-30 mpegg  cleanup  % 
# %git_commit_history: november changes % 
# Kea DHCP Watchdog - Auto-restart services if PostgreSQL connection fails
# This runs on failure to attempt recovery

set -euo pipefail

LOG_FILE="/var/log/tt-kea-watchdog-dev1.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Kea Watchdog Triggered ==="

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log "PostgreSQL is down, starting it..."
    systemctl start postgresql
    sleep 5
fi

# Wait for PostgreSQL to be ready
for i in {1..10}; do
    if sudo -u postgres psql -c "SELECT 1" >/dev/null 2>&1; then
        log "PostgreSQL is ready"
        break
    fi
    log "Waiting for PostgreSQL... ($i/10)"
    sleep 2
done

# Restart Kea services in correct order
log "Restarting Kea DDNS service..."
systemctl restart kea-dhcp-ddns-dev1.service
sleep 2

log "Restarting Kea DHCP4 service..."
systemctl restart kea-dhcp4-dev1.service
sleep 3

# Verify services are running
if systemctl is-active --quiet kea-dhcp4-dev1.service && systemctl is-active --quiet kea-dhcp-ddns-dev1.service; then
    log "SUCCESS: All Kea services restarted successfully"
    exit 0
else
    log "FAILURE: Unable to restart Kea services"
    exit 1
fi
