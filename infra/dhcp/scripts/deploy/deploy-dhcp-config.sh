#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/deploy/deploy-dhcp-config.sh:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 3ee0162aae19a4421c919cb4a3f9eee2cb6b7cb8 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:27:57 %
#  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
#  %ccm_git_file_name: deploy-dhcp-config.sh %
#  %ccm_git_path: infra/dhcp/scripts/deploy/deploy-dhcp-config.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 7826 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 

# DHCP Configuration Deployment Script
# Deploys generated DHCP configuration to remote DHCP servers

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG_FILE="$PROJECT_ROOT/configs/active/dhcp.conf"
LOG_FILE="$PROJECT_ROOT/logs/deployment.log"

# Default DHCP server settings (override in dhcp-servers.conf)
DHCP_SERVERS="${DHCP_SERVERS:-}"
DHCP_USER="${DHCP_USER:-dhcp-admin}"
DHCP_CONFIG_PATH="${DHCP_CONFIG_PATH:-/etc/dhcp/dhcpd.conf}"
DHCP_SERVICE_NAME="${DHCP_SERVICE_NAME:-isc-dhcp-server}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"

# Load server-specific configuration if available
SERVER_CONFIG="$PROJECT_ROOT/configs/dhcp-servers.conf"
if [[ -f "$SERVER_CONFIG" ]]; then
    source "$SERVER_CONFIG"
fi

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -s, --servers SERVERS    Comma-separated list of DHCP server IPs/hostnames
    -u, --user USER         SSH username for DHCP servers (default: dhcp-admin)
    -k, --key KEY_FILE      SSH private key file (default: ~/.ssh/id_rsa)
    -c, --config CONFIG     Local DHCP config file to deploy (default: configs/active/dhcp.conf)
    -p, --path PATH         Remote DHCP config path (default: /etc/dhcp/dhcpd.conf)
    -t, --test-only         Test mode - validate config but don't deploy
    -h, --help              Show this help message

Examples:
    $0 -s "192.168.1.1,dhcp-02.local" -u admin
    $0 --test-only
    $0 -s "dhcp-01.local" -k ~/.ssh/dhcp_key
EOF
}

# Parse command line arguments
TEMP=$(getopt -o s:u:k:c:p:th --long servers:,user:,key:,config:,path:,test-only,help -n "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1
fi
eval set -- "$TEMP"

TEST_ONLY=false

while true; do
    case "$1" in
        -s|--servers)
            DHCP_SERVERS="$2"
            shift 2
            ;;
        -u|--user)
            DHCP_USER="$2"
            shift 2
            ;;
        -k|--key)
            SSH_KEY="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--path)
            DHCP_CONFIG_PATH="$2"
            shift 2
            ;;
        -t|--test-only)
            TEST_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Internal error!"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$DHCP_SERVERS" ]]; then
    log "ERROR: No DHCP servers specified"
    log "Use -s option or set DHCP_SERVERS in dhcp-servers.conf"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    log "ERROR: DHCP configuration file not found: $CONFIG_FILE"
    log "Run generate-config.sh first to create the configuration"
    exit 1
fi

if [[ ! -f "$SSH_KEY" ]]; then
    log "ERROR: SSH key file not found: $SSH_KEY"
    exit 1
fi

# Convert comma-separated servers to array
IFS=',' read -ra SERVER_ARRAY <<< "$DHCP_SERVERS"

log "Starting DHCP configuration deployment"
log "Configuration file: $CONFIG_FILE"
log "Target servers: $DHCP_SERVERS"
log "SSH user: $DHCP_USER"
log "Test mode: $TEST_ONLY"

# Pre-deployment validation
log "Validating local configuration..."

# Check configuration syntax
if command -v dhcpd >/dev/null 2>&1; then
    if ! dhcpd -t -cf "$CONFIG_FILE" 2>/dev/null; then
        log "ERROR: Local configuration syntax validation failed"
        exit 1
    fi
    log "Local configuration syntax is valid"
else
    log "WARNING: dhcpd not available for local syntax validation"
fi

# Deploy to each server
DEPLOYMENT_SUCCESS=true
SUCCESSFUL_DEPLOYMENTS=()
FAILED_DEPLOYMENTS=()

for server in "${SERVER_ARRAY[@]}"; do
    server=$(echo "$server" | xargs)  # Trim whitespace
    log "Deploying to server: $server"
    
    # Test SSH connectivity
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$DHCP_USER@$server" "echo 'SSH test successful'" >/dev/null 2>&1; then
        log "ERROR: Cannot connect to $server via SSH"
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
        continue
    fi
    
    if [[ "$TEST_ONLY" == "true" ]]; then
        log "TEST MODE: Would deploy to $server"
        continue
    fi
    
    # Create backup on remote server
    BACKUP_NAME="dhcpd.conf.backup.$(date +%Y%m%d_%H%M%S)"
    log "Creating backup on $server: $BACKUP_NAME"
    
    if ! ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo cp '$DHCP_CONFIG_PATH' '$DHCP_CONFIG_PATH.$BACKUP_NAME'" 2>/dev/null; then
        log "ERROR: Failed to create backup on $server"
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
        continue
    fi
    
    # Upload new configuration
    log "Uploading configuration to $server..."
    TEMP_CONFIG="/tmp/dhcpd.conf.new"
    
    if ! scp -i "$SSH_KEY" "$CONFIG_FILE" "$DHCP_USER@$server:$TEMP_CONFIG" >/dev/null 2>&1; then
        log "ERROR: Failed to upload configuration to $server"
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
        continue
    fi
    
    # Validate configuration on remote server
    log "Validating configuration on $server..."
    if ! ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo dhcpd -t -cf '$TEMP_CONFIG'" >/dev/null 2>&1; then
        log "ERROR: Configuration validation failed on $server"
        ssh -i "$SSH_KEY" "$DHCP_USER@$server" "rm -f '$TEMP_CONFIG'" >/dev/null 2>&1
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
        continue
    fi
    
    # Deploy configuration
    log "Installing configuration on $server..."
    if ! ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo mv '$TEMP_CONFIG' '$DHCP_CONFIG_PATH'"; then
        log "ERROR: Failed to install configuration on $server"
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
        continue
    fi
    
    # Restart DHCP service
    log "Restarting DHCP service on $server..."
    if ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo systemctl restart '$DHCP_SERVICE_NAME'" >/dev/null 2>&1; then
        # Verify service is running
        sleep 2
        if ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo systemctl is-active '$DHCP_SERVICE_NAME' >/dev/null"; then
            log "Successfully deployed and restarted DHCP service on $server"
            SUCCESSFUL_DEPLOYMENTS+=("$server")
        else
            log "ERROR: DHCP service failed to start on $server"
            log "Attempting to restore backup..."
            ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo mv '$DHCP_CONFIG_PATH.$BACKUP_NAME' '$DHCP_CONFIG_PATH'" >/dev/null 2>&1
            ssh -i "$SSH_KEY" "$DHCP_USER@$server" "sudo systemctl restart '$DHCP_SERVICE_NAME'" >/dev/null 2>&1
            FAILED_DEPLOYMENTS+=("$server")
            DEPLOYMENT_SUCCESS=false
        fi
    else
        log "ERROR: Failed to restart DHCP service on $server"
        FAILED_DEPLOYMENTS+=("$server")
        DEPLOYMENT_SUCCESS=false
    fi
done

# Deployment summary
log "Deployment Summary:"
log "Successful deployments: ${#SUCCESSFUL_DEPLOYMENTS[@]}"
for server in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
    log "  ✓ $server"
done

log "Failed deployments: ${#FAILED_DEPLOYMENTS[@]}"
for server in "${FAILED_DEPLOYMENTS[@]}"; do
    log "  ✗ $server"
done

if [[ "$TEST_ONLY" == "true" ]]; then
    log "TEST MODE: No actual deployments performed"
    exit 0
elif [[ "$DEPLOYMENT_SUCCESS" == "true" ]]; then
    log "All deployments completed successfully"
    exit 0
else
    log "Some deployments failed - check logs above"
    exit 1
fi
