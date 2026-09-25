#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 220c05bea884f77d057538c739380cb0645e455b %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
#  %ccm_git_file_name: tt-kea-watchdog-dev1.sh %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6904 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-03-22 mpegg  march updates  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026.1  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# %git_commit_history: 2025-11-30 mpegg  cleanup  % 
# %git_commit_history: november changes % 
# Kea DHCP Watchdog - Smart auto-recovery with diagnostics
# This runs on failure and attempts to diagnose and fix the issue

set -euo pipefail

LOG_FILE="/var/log/tt-kea-watchdog-dev1.log"
RESTART_COUNT_FILE="/var/run/kea/watchdog-restart-count"
MAX_RESTARTS=3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_restart_limit() {
    # Prevent infinite restart loops
    if [ ! -f "$RESTART_COUNT_FILE" ]; then
        echo "1" > "$RESTART_COUNT_FILE"
        return 0
    fi
    
    local count=$(cat "$RESTART_COUNT_FILE" 2>/dev/null || echo "0")
    local last_restart=$(stat -c %Y "$RESTART_COUNT_FILE" 2>/dev/null || echo "0")
    local now=$(date +%s)
    local age=$((now - last_restart))
    
    # Reset counter if last restart was over 1 hour ago (problem resolved itself)
    if [ "$age" -gt 3600 ]; then
        log "Last restart was ${age}s ago, resetting counter"
        echo "1" > "$RESTART_COUNT_FILE"
        return 0
    fi
    
    count=$((count + 1))
    echo "$count" > "$RESTART_COUNT_FILE"
    
    if [ "$count" -gt "$MAX_RESTARTS" ]; then
        log "ERROR: Restart limit exceeded ($count > $MAX_RESTARTS in last hour)"
        log "ERROR: Manual intervention required - not attempting automatic recovery"
        return 1
    fi
    
    log "Restart attempt $count of $MAX_RESTARTS"
    return 0
}

diagnose_failure() {
    # Analyze recent logs to determine failure cause
    local logs=$(journalctl -u kea-dhcp4-dev1.service --since "5 minutes ago" --no-pager 2>/dev/null)
    
    # Check for permission errors
    if echo "$logs" | grep -q "Permission denied"; then
        log "DIAGNOSIS: Permission errors detected"
        return 1  # Permission errors
    fi
    
    if echo "$logs" | grep -q "Unable to open PID file"; then
        log "DIAGNOSIS: Cannot write PID file (permission issue)"
        return 1
    fi
    
    if echo "$logs" | grep -q "Unable to use interprocess sync lockfile"; then
        log "DIAGNOSIS: Cannot access lock files (permission issue)"
        return 1
    fi
    
    # Check for configuration errors
    if echo "$logs" | grep -q "configuration error"; then
        log "DIAGNOSIS: Configuration file error"
        return 2  # Config error
    fi
    
    if echo "$logs" | grep -q "Unable to open database"; then
        log "DIAGNOSIS: Database file access error"
        return 3  # Database issue
    fi
    
    # Check for PostgreSQL connection issues
    if echo "$logs" | grep -q -E "(connection to server.*failed|could not connect to server)"; then
        log "DIAGNOSIS: PostgreSQL connection failure"
        return 4  # PostgreSQL issue
    fi
    
    log "DIAGNOSIS: Unknown failure cause"
    return 0  # Unknown
}

fix_permissions() {
    log "Attempting to fix file permissions..."
    local fixed=0
    
    # Fix /var/run/kea/ ownership and permissions
    if [ -d /var/run/kea ]; then
        local owner=$(stat -c '%U:%G' /var/run/kea)
        if [ "$owner" != "_kea:_kea" ]; then
            log "Fixing /var/run/kea ownership: $owner -> _kea:_kea"
            chown -R _kea:_kea /var/run/kea/
            fixed=1
        fi
        
        local perms=$(stat -c '%a' /var/run/kea)
        if [ "$perms" != "750" ]; then
            log "Fixing /var/run/kea permissions: $perms -> 750"
            chmod 750 /var/run/kea/
            fixed=1
        fi
    fi
    
    # Fix /var/lib/kea/ ownership
    if [ -d /var/lib/kea ]; then
        local owner=$(stat -c '%U:%G' /var/lib/kea)
        if [ "$owner" != "_kea:_kea" ]; then
            log "Fixing /var/lib/kea ownership: $owner -> _kea:_kea"
            chown -R _kea:_kea /var/lib/kea/
            fixed=1
        fi
    fi
    
    # Clean up stale lock files
    if [ -f /var/run/kea/logger_lockfile ]; then
        log "Removing stale logger_lockfile"
        rm -f /var/run/kea/logger_lockfile
        fixed=1
    fi
    
    if [ -f /var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid ]; then
        if ! kill -0 $(cat /var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid 2>/dev/null) 2>/dev/null; then
            log "Removing stale PID file"
            rm -f /var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid
            fixed=1
        fi
    fi
    
    return $fixed
}

log "=== Kea Watchdog Triggered ==="
log "Service: kea-dhcp4-dev1.service has failed"

# Check restart limit
if ! check_restart_limit; then
    log "ABORT: Too many restart attempts - giving up"
    exit 1
fi

# Diagnose the failure
diagnose_failure
diagnosis_code=$?

case $diagnosis_code in
    1)
        log "Attempting to fix permission errors..."
        if fix_permissions; then
            log "Permissions fixed, attempting restart"
        else
            log "No permission fixes needed, but diagnosis indicated permissions issue"
        fi
        ;;
    2)
        log "ERROR: Configuration file error detected"
        log "ERROR: Cannot auto-fix - manual intervention required"
        log "ERROR: Check /etc/kea/tt-kea-dhcp4-dev1.conf for syntax errors"
        exit 1
        ;;
    3)
        log "Database file access issue - checking permissions"
        fix_permissions
        ;;
    4)
        log "PostgreSQL connection issue - checking database"
        ;;
    *)
        log "Unknown failure cause - proceeding with standard recovery"
        ;;
esac

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
    # Reset restart counter on success
    rm -f "$RESTART_COUNT_FILE"
    exit 0
else
    log "FAILURE: Unable to restart Kea services"
    # Check logs again to see what went wrong
    log "Recent error logs:"
    journalctl -u kea-dhcp4-dev1.service --since "30 seconds ago" --no-pager | tail -5 | tee -a "$LOG_FILE"
    exit 1
fi
