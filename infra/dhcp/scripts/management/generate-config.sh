#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/management/generate-config.sh:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a6d6e0cd88872d304a55a481a3b69770d5cfa253 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:12:09 %
#  %ccm_git_file_last_modified: 2025-09-27 10:05:13 %
#  %ccm_git_file_name: generate-config.sh %
#  %ccm_git_path: infra/dhcp/scripts/management/generate-config.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 5487 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

# DHCP Configuration Generator
# Generates DHCP server configuration from YAML inventory

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
INVENTORY_FILE="$PROJECT_ROOT/inventory/devices.yaml"
TEMPLATE_FILE="$PROJECT_ROOT/configs/isc-dhcp/templates/dhcp.conf.template"
OUTPUT_DIR="$PROJECT_ROOT/configs/isc-dhcp/active"
BACKUP_DIR="$PROJECT_ROOT/configs/isc-dhcp/backups"
LOG_FILE="$PROJECT_ROOT/logs/config-generation.log"

# Ensure directories exist
mkdir -p "$OUTPUT_DIR" "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Validate required files
if [[ ! -f "$INVENTORY_FILE" ]]; then
    log "ERROR: Inventory file not found: $INVENTORY_FILE"
    exit 1
fi

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    log "ERROR: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

# Check for required tools
if ! command -v yq >/dev/null 2>&1; then
    log "ERROR: yq (YAML processor) is required but not installed"
    log "Install with: sudo apt-get install yq"
    exit 1
fi

# Backup existing configuration
if [[ -f "$OUTPUT_DIR/dhcp.conf" ]]; then
    backup_file="$BACKUP_DIR/dhcp.conf.$(date +%Y%m%d_%H%M%S)"
    cp "$OUTPUT_DIR/dhcp.conf" "$backup_file"
    log "Backed up existing config to: $backup_file"
fi

log "Starting DHCP configuration generation..."
log "Inventory: $INVENTORY_FILE"
log "Template: $TEMPLATE_FILE"
log "Output: $OUTPUT_DIR/dhcp.conf"

# Extract values from YAML inventory
DOMAIN_NAME=$(yq e '.network_info.domain' "$INVENTORY_FILE")
DNS_SERVERS=$(yq e '.network_info.dns_servers | join(", ")' "$INVENTORY_FILE")
DEFAULT_LEASE_TIME="86400"  # 24 hours
MAX_LEASE_TIME="604800"     # 7 days

# Generate configuration
log "Processing template..."

# Create temporary processing script
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOF'
#!/usr/bin/env python3
import yaml
import sys
from jinja2 import Template
import ipaddress

def load_inventory(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def load_template(file_path):
    with open(file_path, 'r') as f:
        return Template(f.read())

def process_subnets(network_info):
    subnets = []
    for subnet in network_info.get('subnets', []):
        net = ipaddress.IPv4Network(subnet['network'])
        subnets.append({
            'description': subnet.get('description', ''),
            'network_addr': str(net.network_address),
            'netmask': str(net.netmask),
            'broadcast': str(net.broadcast_address),
            'gateway': subnet.get('gateway', network_info.get('default_gateway')),
            'dhcp_start': str(net.network_address + 100),
            'dhcp_end': str(net.broadcast_address - 10),
            'dns_servers': ', '.join(network_info.get('dns_servers', []))
        })
    return subnets

def main():
    if len(sys.argv) != 4:
        print("Usage: script.py <inventory> <template> <output>")
        sys.exit(1)
    
    inventory_file, template_file, output_file = sys.argv[1:4]
    
    # Load data
    data = load_inventory(inventory_file)
    template = load_template(template_file)
    
    # Process data
    network_info = data.get('network_info', {})
    devices = data.get('devices', [])
    
    # Filter static devices
    static_devices = [d for d in devices if d.get('ip_address')]
    
    # Prepare template variables
    template_vars = {
        'DOMAIN_NAME': network_info.get('domain', 'local'),
        'DNS_SERVERS': ', '.join(network_info.get('dns_servers', ['8.8.8.8'])),
        'DEFAULT_LEASE_TIME': 86400,
        'MAX_LEASE_TIME': 604800,
        'SUBNETS': process_subnets(network_info),
        'STATIC_DEVICES': static_devices,
        'DEVICE_TYPES': []
    }
    
    # Render template
    config = template.render(**template_vars)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(config)
    
    print(f"Generated DHCP configuration: {output_file}")

if __name__ == "__main__":
    main()
EOF

# Make script executable and run it
chmod +x "$TEMP_SCRIPT"

# Check if Python and required modules are available
if ! python3 -c "import yaml, jinja2" 2>/dev/null; then
    log "ERROR: Required Python modules not found (yaml, jinja2)"
    log "Install with: pip3 install pyyaml jinja2"
    rm -f "$TEMP_SCRIPT"
    exit 1
fi

# Generate configuration
if python3 "$TEMP_SCRIPT" "$INVENTORY_FILE" "$TEMPLATE_FILE" "$OUTPUT_DIR/dhcp.conf"; then
    log "Successfully generated DHCP configuration"
    
    # Validate configuration syntax (if dhcpd is available)
    if command -v dhcpd >/dev/null 2>&1; then
        log "Validating DHCP configuration syntax..."
        if dhcpd -t -cf "$OUTPUT_DIR/dhcp.conf" 2>/dev/null; then
            log "Configuration syntax is valid"
        else
            log "WARNING: Configuration syntax validation failed"
        fi
    else
        log "DHCP daemon not available for syntax validation"
    fi
    
    # Display summary
    log "Configuration summary:"
    log "  - Static reservations: $(grep -c "^host " "$OUTPUT_DIR/dhcp.conf" || echo 0)"
    log "  - Subnets configured: $(grep -c "^subnet " "$OUTPUT_DIR/dhcp.conf" || echo 0)"
    
else
    log "ERROR: Failed to generate DHCP configuration"
    rm -f "$TEMP_SCRIPT"
    exit 1
fi

# Cleanup
rm -f "$TEMP_SCRIPT"

log "DHCP configuration generation completed successfully"
