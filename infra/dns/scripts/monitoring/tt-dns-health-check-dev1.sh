#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dns/scripts/monitoring/tt-dns-health-check-dev1.sh:148 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 75223ce8b0c6d6b709d29b126a9f395abdbddffc %
#  %ccm_git_commit_id: a05e23946842d7f627bba10740a39e328f03d84e %
#  %ccm_git_commit_count: 148 %
#  %ccm_git_commit_date: 2026-06-14 10:37:47 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: sunday updates %
#  %ccm_git_modify_date: 2026-06-14 10:37:48 %
#  %ccm_git_file_last_modified: 2026-06-14 10:37:48 %
#  %ccm_git_file_name: tt-dns-health-check-dev1.sh %
#  %ccm_git_path: infra/dns/scripts/monitoring/tt-dns-health-check-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 8222 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-03-22 mpegg  march updates  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026.1  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  
# DNS Health Check Script for Uptime Kuma
# Returns exit code 0 if healthy, non-zero if problems detected
# Compatible with Uptime Kuma Script Monitor
#  tt-secrets.skip

set -eu

ERRORS=0
WARNINGS=0
LOG_FILE="/var/log/tt-dns-health-check-dev1.log"

# Test domains
TEST_EXTERNAL="google.com"
TEST_LOCAL="kea.tt.omp"
TEST_AA="test.aa.omp"

# DNS server IPs
PIHOLE_IP1="192.168.1.10"
PIHOLE_IP2="192.168.4.10"
POWERDNS_PORT="3053"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_container() {
    local container=$1
    if ! docker ps --filter "name=${container}" --filter "status=running" --format "{{.Names}}" | grep -q "^${container}$"; then
        log "ERROR: Container $container is not running"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    # Check if container is healthy (if it has a healthcheck)
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
    if [ "$health" = "unhealthy" ]; then
        log "ERROR: Container $container is unhealthy"
        ERRORS=$((ERRORS + 1))
        return 1
    elif [ "$health" = "healthy" ]; then
        log "OK: Container $container is running (healthy)"
    else
        log "OK: Container $container is running"
    fi
    return 0
}

check_dns_resolution() {
    local server=$1
    local domain=$2
    local description=$3
    local port=${4:-53}
    
    if ! timeout 5 dig @"$server" -p "$port" "$domain" +short +time=2 >/dev/null 2>&1; then
        log "ERROR: DNS resolution failed for $domain via $server:$port ($description)"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    local result=$(timeout 5 dig @"$server" -p "$port" "$domain" +short +time=2 2>/dev/null | head -1)
    log "OK: $description resolved $domain: $result"
    return 0
}

check_port_listening() {
    local ip=$1
    local port=$2
    local service=$3
    
    # For DNS, test with actual query instead of port check
    if [ "$port" = "53" ]; then
        if ! timeout 3 dig @"$ip" -p "$port" google.com +short +time=2 >/dev/null 2>&1; then
            log "ERROR: $service not responding on ${ip}:${port}"
            ERRORS=$((ERRORS + 1))
            return 1
        fi
    else
        # For non-DNS ports, use regular query test
        if ! timeout 3 dig @"$ip" -p "$port" version.bind chaos txt +short +time=2 >/dev/null 2>&1; then
            log "ERROR: $service not responding on ${ip}:${port}"
            ERRORS=$((ERRORS + 1))
            return 1
        fi
    fi
    log "OK: $service listening on ${ip}:${port}"
    return 0
}

check_pihole_web() {
    # Check Pi-hole web interface is accessible (root returns 403 but with Pi-hole content)
    local url="http://localhost:3010/"
    
    if curl -s -m 5 "$url" 2>/dev/null | grep -q "Pi-hole"; then
        log "OK: Pi-hole web interface responding"
    else
        log "WARNING: Pi-hole web interface not responding"
        WARNINGS=$((WARNINGS + 1))
    fi
    return 0
}

check_powerdns_api() {
    # Check PowerDNS API - 401 means API is up but needs auth (expected)
    local url="http://localhost:3021/api/v1/servers"
    local response=$(curl -s -w "\n%{http_code}" -m 5 "$url" 2>/dev/null | tail -1)
    
    if [ "$response" = "401" ] || [ "$response" = "200" ]; then
        log "OK: PowerDNS API responding (HTTP $response)"
    else
        log "WARNING: PowerDNS API not responding (HTTP $response)"
        WARNINGS=$((WARNINGS + 1))
    fi
    return 0
}

check_dns_database() {
    local container="powerdns-db-dev1"
    
    # Check if MySQL database is accessible
    if ! docker exec "$container" mysqladmin ping -h localhost --silent 2>/dev/null; then
        log "ERROR: PowerDNS MySQL database not responding"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    # Get zone count
    local zone_count=$(docker exec "$container" mysql -N -e "SELECT COUNT(*) FROM pdns.domains" 2>/dev/null || echo "0")
    log "OK: PowerDNS database accessible ($zone_count zones)"
    return 0
}

check_recent_queries() {
    # Check Pi-hole is processing queries by verifying FTL is running
    local container="pihole-dev1"
    
    if docker exec "$container" pgrep pihole-FTL >/dev/null 2>&1; then
        log "OK: Pi-hole FTL (DNS engine) is running"
    else
        log "WARNING: Pi-hole FTL not running"
        WARNINGS=$((WARNINGS + 1))
    fi
    return 0
}

check_container_logs() {
    # Check for errors in recent container logs (last 10 minutes only)
    local container=$1
    local service=$2
    
    # Filter out expected "errors" and old logs
    if docker logs --since 10m "$container" 2>&1 | grep -i "error\|fatal\|fail" | grep -v "WARNING" | grep -v "Authentication by API Key failed" >/dev/null 2>&1; then
        log "WARNING: Recent errors found in $service logs"
        WARNINGS=$((WARNINGS + 1))
    fi
    return 0
}

# Run all checks
log "=== Starting DNS Health Check ==="

# Check containers are running
check_container "pihole-dev1"
check_container "powerdns-dev1"
check_container "powerdns-admin-dev1"
check_container "powerdns-db-dev1"
check_container "powerdns-admin-db-dev1"

# Check DNS ports
check_port_listening "$PIHOLE_IP1" "53" "Pi-hole DNS (192.168.1.10)"
check_port_listening "$PIHOLE_IP2" "53" "Pi-hole DNS (192.168.4.10)"
check_port_listening "$PIHOLE_IP1" "$POWERDNS_PORT" "PowerDNS (192.168.1.10)"
check_port_listening "$PIHOLE_IP2" "$POWERDNS_PORT" "PowerDNS (192.168.4.10)"

# Check DNS resolution
check_dns_resolution "$PIHOLE_IP1" "$TEST_EXTERNAL" "External DNS via Pi-hole 1"
check_dns_resolution "$PIHOLE_IP2" "$TEST_EXTERNAL" "External DNS via Pi-hole 2"
check_dns_resolution "$PIHOLE_IP1" "$TEST_LOCAL" "Local DNS (tt.omp) via Pi-hole 1"
check_dns_resolution "$PIHOLE_IP1" "$TEST_LOCAL" "PowerDNS authoritative (tt.omp)" "$POWERDNS_PORT"

# Check web interfaces
check_pihole_web
check_powerdns_api

# Check databases
check_dns_database

# Check recent activity
check_recent_queries

# Check for errors in logs (non-critical)
check_container_logs "pihole-dev1" "Pi-hole"
check_container_logs "powerdns-dev1" "PowerDNS"

log "=== Health Check Complete: $ERRORS errors, $WARNINGS warnings ==="

# ========================================================================
# Uptime Kuma Monitoring Architecture
# ========================================================================
# This script is part of a layered monitoring strategy:
#
# 1. DNS Monitor (this script - Push type):
#    - Checks Pi-hole and PowerDNS containers, ports, resolution, databases
#    - Validates local and external DNS resolution through our infrastructure
#    - Runs via systemd timer every 1 minute
#
# 2. Internet Up Monitor (simple Kuma Ping type):
#    - Simple ping to 1.1.1.1 to verify WAN connectivity
#    - No custom script needed - Kuma native ping monitor
#    - If this fails, DNS external resolution will also fail
#
# 3. DHCP Monitor (separate script - Push type):
#    - Located at: /srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh
#    - Checks Kea DHCP server health
#    - Runs via systemd timer
#
# This separation provides clear failure isolation and targeted alerting.
# ========================================================================

# Push to Uptime Kuma
# Token is stored in secrets file, not in git - tt-secrets.skip marker at top prevents commit
KUMA_URL="https://kuma.termitetowers.ca/api/push"
PUSH_TOKEN="${KUMA_DNS_PUSH_TOKEN:-PRi8xzKBrGvWDAicTU0QU0hMOR2FAOsD}"

if [ $ERRORS -eq 0 ]; then
    STATUS="up"
    MSG="Healthy: $WARNINGS warnings"
else
    STATUS="down"
    MSG="Unhealthy: $ERRORS errors, $WARNINGS warnings"
fi

MSG_ENCODED=$(echo "$MSG" | sed 's/ /%20/g')
curl -fsS -m 10 --retry 3 "${KUMA_URL}/${PUSH_TOKEN}?status=${STATUS}&msg=${MSG_ENCODED}" 2>&1 | logger -t dns-health-push

# Exit with error if any critical issues found
if [ $ERRORS -gt 0 ]; then
    exit 1
fi

exit 0
