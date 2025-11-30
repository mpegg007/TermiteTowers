#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: f9100610e0b3a358dd48108af9eebf3a5248900f %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-11-30 12:10:13 %
#  %ccm_git_file_last_modified: 2025-11-30 12:10:13 %
#  %ccm_git_file_name: tt-kea-health-check-dev1.sh %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/tt-kea-health-check-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 4069 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Kea DHCP Health Check Script for Uptime Kuma
# Returns exit code 0 if healthy, non-zero if problems detected
# Compatible with Uptime Kuma Script Monitor
#  tt-secrets.skip


set -euo pipefail

ERRORS=0
WARNINGS=0
LOG_FILE="/var/log/tt-kea-health-check-dev1.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_service() {
    local service=$1
    if ! systemctl is-active --quiet "$service"; then
        log "ERROR: Service $service is not running"
        ((ERRORS++))
        return 1
    fi
    log "OK: Service $service is running"
    return 0
}

check_port() {
    local port=$1
    local service=$2
    if ! lsof -i ":$port" >/dev/null 2>&1; then
        log "ERROR: $service not listening on port $port"
        ((ERRORS++))
        return 1
    fi
    log "OK: $service listening on port $port"
    return 0
}

check_postgres_connection() {
    if ! sudo -u postgres psql -d ttdb_dev1 -c "SELECT 1 FROM kea.hosts LIMIT 1" >/dev/null 2>&1; then
        log "ERROR: Cannot query PostgreSQL kea.hosts table"
        ((ERRORS++))
        return 1
    fi
    
    local count=$(sudo -u postgres psql -d ttdb_dev1 -t -c "SELECT COUNT(*) FROM kea.hosts" 2>/dev/null | xargs)
    log "OK: PostgreSQL connection successful ($count host reservations)"
    return 0
}

check_kea_postgres_connection() {
    # Check if Kea can actually talk to PostgreSQL by looking at recent logs
    if journalctl -u kea-dhcp4-dev1.service --since "5 minutes ago" --no-pager 2>/dev/null | grep -q "connection to server.*failed"; then
        log "ERROR: Kea reported PostgreSQL connection failure in last 5 minutes"
        ((ERRORS++))
        return 1
    fi
    log "OK: No Kea PostgreSQL connection errors in last 5 minutes"
    return 0
}

check_recent_dhcp_activity() {
    # Check for DHCP lease allocations in last hour
    if [ -f /var/log/kea/kea-dhcp4.log ]; then
        local last_lease=$(grep "DHCP4_LEASE_ALLOC" /var/log/kea/kea-dhcp4.log 2>/dev/null | tail -1 | awk '{print $1, $2}')
        if [ -n "$last_lease" ]; then
            log "OK: Last DHCP lease allocation: $last_lease"
        else
            log "WARNING: No DHCP lease allocations found in log (may be normal if no new clients)"
            ((WARNINGS++))
        fi
    fi
    return 0
}

check_ddns_updates() {
    # Check if DDNS is working
    if [ -f /var/log/kea/kea-ddns.log ]; then
        if journalctl -u kea-dhcp-ddns-dev1.service --since "10 minutes ago" --no-pager 2>/dev/null | grep -q "DHCP_DDNS.*FAIL"; then
            log "ERROR: DDNS failures detected in last 10 minutes"
            ((ERRORS++))
            return 1
        fi
        log "OK: No DDNS failures in last 10 minutes"
    fi
    return 0
}

check_powerdns() {
    # Check if PowerDNS is responding
    if ! dig @192.168.1.10 -p 3053 kea.tt.omp SOA +short +time=2 >/dev/null 2>&1; then
        log "ERROR: PowerDNS not responding on port 3053"
        ((ERRORS++))
        return 1
    fi
    log "OK: PowerDNS responding on port 3053"
    return 0
}

# Run all checks
log "=== Starting Kea Health Check ==="

check_service "postgresql"
check_service "kea-dhcp4-dev1.service"
check_service "kea-dhcp-ddns-dev1.service"

check_postgres_connection
check_kea_postgres_connection

check_port 67 "Kea DHCP"

# Note: Kea DDNS uses Unix socket, not TCP port 53001
# Skip port check for DDNS

check_recent_dhcp_activity
check_ddns_updates
check_powerdns

log "=== Health Check Complete: $ERRORS errors, $WARNINGS warnings ==="

# Exit with error if any critical issues found
if [ $ERRORS -gt 0 ]; then
    exit 1
fi


# Push to Uptime Kuma
KUMA_URL="https://kuma.termitetowers.ca/api/push"
PUSH_TOKEN="D0iXF9tBdBO1gU2JbGJWFZ2HqP1QT2GK"

if [ $ERRORS -eq 0 ]; then
    STATUS="up"
    MSG="Healthy: $WARNINGS warnings"
else
    STATUS="down"
    MSG="Unhealthy: $ERRORS errors, $WARNINGS warnings"
fi

MSG_ENCODED=$(echo "$MSG" | sed 's/ /%20/g')
curl -fsS -m 10 --retry 3 "${KUMA_URL}/${PUSH_TOKEN}?status=${STATUS}&msg=${MSG_ENCODED}" 2>&1 | logger -t kea-health-push
exit 0
