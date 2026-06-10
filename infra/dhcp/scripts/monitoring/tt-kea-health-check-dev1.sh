#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/tt-kea-health-check-dev1.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 3f97e62b153c907c68380c631db8510cf561aa61 %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
#  %ccm_git_file_name: tt-kea-health-check-dev1.sh %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/tt-kea-health-check-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 18388 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-03-22 mpegg  march updates  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026.1  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# %git_commit_history: 2025-11-30 mpegg  cleanup  % 
# %git_commit_history: november changes % 
# Kea DHCP Health Check Script for Uptime Kuma
# Returns exit code 0 if healthy, non-zero if problems detected
# Compatible with Uptime Kuma Script Monitor
#  tt-secrets.skip


set -euo pipefail

ERRORS=0
WARNINGS=0
LOG_FILE="/var/log/tt-kea-health-check-dev1.log"

KUMA_URL="https://kuma.termitetowers.ca/api/push"
PUSH_TOKEN="D0iXF9tBdBO1gU2JbGJWFZ2HqP1QT2GK"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

push_kuma() {
    local exit_code=$?
    # If script was killed by set -e before completing, treat as error
    if [ "$exit_code" -ne 0 ] && [ "$ERRORS" -eq 0 ]; then
        ERRORS=$((ERRORS + 1))
        log "ERROR: Script aborted unexpectedly (exit code $exit_code) before completing all checks"
    fi

    if [ "$ERRORS" -eq 0 ]; then
        STATUS="up"
        MSG="Healthy: $WARNINGS warnings"
    else
        STATUS="down"
        MSG="Unhealthy: $ERRORS errors, $WARNINGS warnings"
    fi

    MSG_ENCODED=$(echo "$MSG" | sed 's/ /%20/g')
    curl -fsS -m 10 --retry 3 "${KUMA_URL}/${PUSH_TOKEN}?status=${STATUS}&msg=${MSG_ENCODED}" 2>&1 | logger -t kea-health-push
    log "=== Kuma push: status=$STATUS msg=$MSG ==="
}

trap push_kuma EXIT

check_service() {
    local service=$1
    
    # Check if service is active
    if ! systemctl is-active --quiet "$service"; then
        log "ERROR: Service $service is not running"
        ((ERRORS++))
        return 1
    fi
    
    # Check if service is in failed state
    if systemctl is-failed --quiet "$service"; then
        log "ERROR: Service $service is in failed state"
        ((ERRORS++))
        return 1
    fi
    
    # Check for recent failures (crash loop detection)
    local restart_count=$(systemctl show "$service" -p NRestarts --value 2>/dev/null || echo "0")
    if [ "$restart_count" -gt 10 ]; then
        log "ERROR: Service $service has restarted $restart_count times (possible crash loop)"
        ((ERRORS++))
        return 1
    fi
    
    # Check service has been running for at least 30 seconds (not constantly restarting)
    local active_since=$(systemctl show "$service" -p ActiveEnterTimestamp --value 2>/dev/null)
    if [ -n "$active_since" ]; then
        local active_epoch=$(date -d "$active_since" +%s 2>/dev/null || echo "0")
        local now_epoch=$(date +%s)
        local uptime=$((now_epoch - active_epoch))
        if [ "$uptime" -lt 30 ]; then
            log "ERROR: Service $service has only been up for ${uptime}s (unstable)"
            ((ERRORS++))
            return 1
        fi
        log "OK: Service $service is running (uptime: ${uptime}s)"
    else
        log "OK: Service $service is running"
    fi
    
    return 0
}

check_port() {
    local port=$1
    local service=$2
    
    # Check if port is listening
    if ! ss -ulnp 2>/dev/null | grep -q ":$port "; then
        log "ERROR: No process listening on UDP port $port"
        ((ERRORS++))
        return 1
    fi
    
    # Verify it's actually kea-dhcp4 listening
    if [ "$port" = "67" ]; then
        local listening_process=$(ss -ulnp 2>/dev/null | grep ":$port " | grep -o 'kea-dhcp4' || echo "unknown")
        if [ "$listening_process" != "kea-dhcp4" ]; then
            log "ERROR: Port $port is not being used by kea-dhcp4 (found: $listening_process)"
            ((ERRORS++))
            return 1
        fi
        
        # Check which interface it's bound to
        local interface=$(ss -ulnp 2>/dev/null | grep ":$port " | awk '{print $5}')
        log "OK: $service listening on port $port ($interface)"
    else
        log "OK: $service listening on port $port"
    fi
    
    return 0
}

check_storage_mount() {
    if ! mountpoint -q /mnt/ai_storage; then
        log "ERROR: /mnt/ai_storage is not mounted (PostgreSQL data unavailable)"
        ((ERRORS++))
        return 1
    fi
    log "OK: /mnt/ai_storage is mounted"
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

check_recent_errors() {
    # Check for critical errors in last 5 minutes
    local error_patterns=(
        "Permission denied"
        "Unable to open PID file"
        "Unable to use interprocess sync lockfile"
        "DHCP4_INIT_FAIL"
        "Unable to open database"
        "Failed to initialize"
    )
    
    for pattern in "${error_patterns[@]}"; do
        if journalctl -u kea-dhcp4-dev1.service --since "5 minutes ago" --no-pager 2>/dev/null | grep -q "$pattern"; then
            log "ERROR: Found '$pattern' in kea-dhcp4 logs within last 5 minutes"
            ((ERRORS++))
            return 1
        fi
    done
    
    log "OK: No critical error patterns in recent logs"
    return 0
}

check_file_permissions() {
    # Check critical directory and file permissions
    
    # Check /var/run/kea directory
    if [ ! -d /var/run/kea ]; then
        log "ERROR: /var/run/kea directory does not exist"
        ((ERRORS++))
        return 1
    fi
    
    local kea_dir_owner=$(stat -c '%U:%G' /var/run/kea 2>/dev/null)
    local kea_dir_perms=$(stat -c '%a' /var/run/kea 2>/dev/null)
    
    if [ "$kea_dir_owner" != "_kea:_kea" ]; then
        log "ERROR: /var/run/kea has wrong ownership: $kea_dir_owner (expected _kea:_kea)"
        ((ERRORS++))
        return 1
    fi
    
    if [ "$kea_dir_perms" != "750" ]; then
        log "WARNING: /var/run/kea has permissions $kea_dir_perms (expected 750)"
        ((WARNINGS++))
    fi
    
    # Check /var/lib/kea directory
    if [ ! -d /var/lib/kea ]; then
        log "ERROR: /var/lib/kea directory does not exist"
        ((ERRORS++))
        return 1
    fi
    
    local kea_lib_owner=$(stat -c '%U:%G' /var/lib/kea 2>/dev/null)
    if [ "$kea_lib_owner" != "_kea:_kea" ]; then
        log "ERROR: /var/lib/kea has wrong ownership: $kea_lib_owner (expected _kea:_kea)"
        ((ERRORS++))
        return 1
    fi
    
    # Check lease file is writable
    if [ -f /var/lib/kea/kea-leases4.csv ]; then
        if ! sudo -u _kea test -w /var/lib/kea/kea-leases4.csv 2>/dev/null; then
            log "ERROR: Lease file not writable by _kea user"
            ((ERRORS++))
            return 1
        fi
    fi
    
    log "OK: File permissions correct"
    return 0
}

check_control_socket() {
    # Check if Kea control socket exists and is accessible
    local socket="/var/run/kea/kea4-ctrl-socket"
    
    if [ ! -S "$socket" ]; then
        log "ERROR: Kea control socket does not exist: $socket"
        ((ERRORS++))
        return 1
    fi
    
    # Check socket is owned by correct user
    local socket_owner=$(stat -c '%U' "$socket" 2>/dev/null)
    if [ "$socket_owner" != "_kea" ]; then
        log "WARNING: Control socket owned by $socket_owner (expected _kea)"
        ((WARNINGS++))
    fi
    
    # Try to query Kea via control socket if socat is available
    if command -v socat &>/dev/null; then
        if ! echo '{ "command": "list-commands" }' | socat - UNIX-CONNECT:"$socket" 2>/dev/null | grep -q "result.*0"; then
            log "WARNING: Cannot communicate with Kea via control socket"
            ((WARNINGS++))
            return 0
        fi
        log "OK: Kea control socket is functional"
    else
        log "OK: Kea control socket exists (socket: $socket)"
    fi
    
    return 0
}

check_lease_database() {
    # Verify lease database is accessible and has recent activity
    if [ ! -f /var/lib/kea/kea-leases4.csv ]; then
        log "ERROR: Lease database file missing"
        ((ERRORS++))
        return 1
    fi
    
    local lease_count=$(grep -v "^#" /var/lib/kea/kea-leases4.csv 2>/dev/null | wc -l)
    local file_age=$(stat -c %Y /var/lib/kea/kea-leases4.csv 2>/dev/null)
    local now=$(date +%s)
    local age_minutes=$(( (now - file_age) / 60 ))
    
    log "OK: Lease database accessible ($lease_count leases, last modified ${age_minutes}m ago)"
    
    # Warn if file hasn't been modified in over 24 hours (might indicate no DHCP activity)
    if [ $age_minutes -gt 1440 ]; then
        log "WARNING: Lease database not modified in ${age_minutes} minutes (may be normal)"
        ((WARNINGS++))
    fi
    
    return 0
}

check_packet_reception() {
    # CRITICAL: Verify Kea is actually receiving AND responding to DHCP packets

    if command -v socat &>/dev/null; then
        local stats_rx=$(echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-received" } }' | \
            sudo socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket 2>/dev/null)
        local stats_tx=$(echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-sent" } }' | \
            sudo socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket 2>/dev/null)

        if [ -n "$stats_rx" ] && [ -n "$stats_tx" ]; then
            local total_rx=$(echo "$stats_rx" | grep -oP '\[ \K\d+' | head -1)
            local total_tx=$(echo "$stats_tx" | grep -oP '\[ \K\d+' | head -1)
            total_rx=${total_rx:-0}
            total_tx=${total_tx:-0}

            # Detect: receiving packets but sending nothing = silent drop
            if [ "$total_rx" -gt 10 ] && [ "$total_tx" -eq 0 ]; then
                log "ERROR: Kea has received $total_rx packets but sent 0 responses (silent drop - possible raw socket or iptables issue)"
                ((ERRORS++))
                return 1
            fi

            local last_packet=$(echo "$stats_rx" | grep -oP '\[ \d+, "\K[^"]+' | head -1)
            if [ -n "$last_packet" ]; then
                local last_packet_epoch=$(date -d "$last_packet" +%s 2>/dev/null || echo "0")
                local now_epoch=$(date +%s)
                local minutes_ago=$(( (now_epoch - last_packet_epoch) / 60 ))

                # With 50+ active devices renewing hourly, silence >10m is abnormal
                if [ "$minutes_ago" -lt 10 ]; then
                    log "OK: Kea received $total_rx packets, sent $total_tx responses, last client request: $last_packet (${minutes_ago}m ago)"
                elif [ "$minutes_ago" -lt 20 ]; then
                    log "WARNING: Last client DHCP request was ${minutes_ago}m ago ($last_packet) - expected every ~2m with 50+ devices"
                    ((WARNINGS++))
                else
                    log "ERROR: No client DHCP requests in ${minutes_ago}m (last: $last_packet) - DHCP likely broken or all clients offline"
                    ((ERRORS++))
                fi
                return 0
            fi
        fi
    fi
    
    # Fallback: Check for any DHCP activity in recent logs (less reliable)
    local packet_count=$(journalctl -u kea-dhcp4-dev1.service --since "10 minutes ago" --no-pager 2>/dev/null | \
        grep -E "(DHCP4_PACKET_RECEIVED|ALLOC_ENGINE|DHCP4_LEASE|pkt4)" 2>/dev/null | wc -l)
    
    # Ensure packet_count is a valid integer
    packet_count=$(echo "$packet_count" | tr -d '\n\r ' | grep -o '[0-9]*' | head -1)
    packet_count=${packet_count:-0}
    
    # Secondary check: Has lease database been modified recently?
    if [ -f /var/lib/kea/kea-leases4.csv ]; then
        local file_age=$(stat -c %Y /var/lib/kea/kea-leases4.csv 2>/dev/null)
        local now=$(date +%s)
        local age_minutes=$(( (now - file_age) / 60 ))
        
        if [ "$age_minutes" -lt 60 ]; then
            log "OK: Lease database recently modified (${age_minutes}m ago) - DHCP activity present"
            return 0
        fi
    fi
    
    if [ "$packet_count" -eq 0 ]; then
        log "WARNING: No DHCP packet activity detected in logs (last 10m)"
        log "INFO: This may be normal - checking lease database activity instead"
        ((WARNINGS++))
        
        # Check capabilities as additional diagnostic
        local kea_pid=$(pgrep kea-dhcp4)
        if [ -n "$kea_pid" ]; then
            local caps=$(grep CapEff /proc/$kea_pid/status 2>/dev/null | awk '{print $2}')
            if [ "$caps" != "0000000000002400" ]; then
                log "ERROR: Kea process missing required capabilities (CAP_NET_RAW, CAP_NET_BIND_SERVICE)"
                log "ERROR: Current capabilities: $caps, Expected: 0000000000002400"
                ((ERRORS++))
                return 1
            fi
        fi
        
        return 0
    else
        log "OK: Kea activity detected ($packet_count log entries in last 10 minutes)"
    fi
    
    return 0
}

check_dhcp_response_ratio() {
    # Verify Kea is responding to a healthy proportion of received requests.
    # Note: dhcping does not work with Kea raw sockets (sends via kernel UDP
    # stack; Kea only reads raw ethernet frames). We use Kea's own stats instead.
    if ! command -v socat &>/dev/null; then
        log "WARNING: socat not installed, skipping DHCP response ratio check"
        ((WARNINGS++))
        return 0
    fi

    local stats_rx=$(echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-received" } }' | \
        sudo socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket 2>/dev/null)
    local stats_tx=$(echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-sent" } }' | \
        sudo socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket 2>/dev/null)

    local total_rx=$(echo "$stats_rx" | grep -oP '\[ \K\d+' | head -1)
    local total_tx=$(echo "$stats_tx" | grep -oP '\[ \K\d+' | head -1)
    total_rx=${total_rx:-0}
    total_tx=${total_tx:-0}

    if [ "$total_rx" -eq 0 ]; then
        log "WARNING: No DHCP packets received since Kea started (normal if recently restarted)"
        ((WARNINGS++))
        return 0
    fi

    # Response ratio: sent/received as percentage (allow for broadcasts, declines etc)
    local ratio=$(( total_tx * 100 / total_rx ))
    if [ "$ratio" -lt 30 ]; then
        log "ERROR: DHCP response ratio critically low: sent $total_tx / received $total_rx (${ratio}%) - Kea may be dropping requests"
        ((ERRORS++))
        return 1
    elif [ "$ratio" -lt 60 ]; then
        log "WARNING: DHCP response ratio low: sent $total_tx / received $total_rx (${ratio}%)"
        ((WARNINGS++))
    else
        log "OK: DHCP response ratio healthy: sent $total_tx / received $total_rx (${ratio}%)"
    fi
    return 0
}

check_network_interface() {
    # Verify the network interface is up and has the expected configuration
    local interface="eno1"
    
    if ! ip link show "$interface" &>/dev/null; then
        log "ERROR: Network interface $interface does not exist"
        ((ERRORS++))
        return 1
    fi
    
    local if_state=$(ip link show "$interface" | grep -oP 'state \K\w+')
    if [ "$if_state" != "UP" ]; then
        log "ERROR: Network interface $interface is not UP (state: $if_state)"
        ((ERRORS++))
        return 1
    fi
    
    # Check if interface has an IP address
    local ip_addr=$(ip -4 addr show "$interface" | grep -oP 'inet \K[\d.]+' | head -1)
    if [ -z "$ip_addr" ]; then
        log "WARNING: Network interface $interface has no IPv4 address"
        ((WARNINGS++))
    else
        log "OK: Network interface $interface is UP (IP: $ip_addr)"
    fi
    
    return 0
}

# Run all checks
log "=== Starting Kea Health Check ==="

check_service "postgresql"
check_service "kea-dhcp4-dev1.service"
check_service "kea-dhcp-ddns-dev1.service"

# Critical operational checks
check_file_permissions
check_recent_errors
check_network_interface

# Storage mount must be verified before postgres
check_storage_mount
check_postgres_connection
check_kea_postgres_connection

check_control_socket
check_lease_database

# Verify Kea is receiving AND responding to packets
check_packet_reception

# Verify healthy response ratio (sent/received)
check_dhcp_response_ratio

# Note: Kea DDNS uses Unix socket, not TCP port 53001
# Skip port check for DDNS

check_recent_dhcp_activity
check_ddns_updates
check_powerdns

log "=== Health Check Complete: $ERRORS errors, $WARNINGS warnings ==="

# push_kuma is called automatically via trap on EXIT
if [ $ERRORS -gt 0 ]; then
    log "CRITICAL: Health check failed with $ERRORS errors"
    exit 1
fi

exit 0
