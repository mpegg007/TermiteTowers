#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dns/scripts/management/generate-zones.sh:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a8524a95eb94d9fa0d06139bda88a53dec2019f5 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:27:57 %
#  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
#  %ccm_git_file_name: generate-zones.sh %
#  %ccm_git_path: infra/dns/scripts/management/generate-zones.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 10832 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 

# DNS Zone File Generator
# Generates BIND zone files from YAML inventory

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DNS_RECORDS_FILE="$PROJECT_ROOT/inventory/dns-records.yaml"
FORWARD_TEMPLATE="$PROJECT_ROOT/zones/templates/forward-zone.template"
REVERSE_TEMPLATE="$PROJECT_ROOT/zones/templates/reverse-zone.template"
FORWARD_OUTPUT_DIR="$PROJECT_ROOT/zones/forward"
REVERSE_OUTPUT_DIR="$PROJECT_ROOT/zones/reverse"
LOG_FILE="$PROJECT_ROOT/logs/zone-generation.log"

# Ensure directories exist
mkdir -p "$FORWARD_OUTPUT_DIR" "$REVERSE_OUTPUT_DIR" "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [DOMAIN]

Options:
    -a, --all              Generate all configured zones
    -f, --forward-only     Generate forward zones only  
    -r, --reverse-only     Generate reverse zones only
    -v, --validate         Validate zone files after generation
    -h, --help             Show this help message

Examples:
    $0 -a                           # Generate all zones
    $0 termitetowers.local          # Generate specific domain
    $0 -f termitetowers.local       # Forward zone only
    $0 -r 192.168.1.0/24           # Reverse zone only
EOF
}

# Parse command line arguments  
TEMP=$(getopt -o afrv h --long all,forward-only,reverse-only,validate,help -n "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1
fi
eval set -- "$TEMP"

GENERATE_ALL=false
FORWARD_ONLY=false
REVERSE_ONLY=false
VALIDATE_ZONES=false
TARGET_DOMAIN=""

while true; do
    case "$1" in
        -a|--all)
            GENERATE_ALL=true
            shift
            ;;
        -f|--forward-only)
            FORWARD_ONLY=true
            shift
            ;;
        -r|--reverse-only)
            REVERSE_ONLY=true
            shift
            ;;
        -v|--validate)
            VALIDATE_ZONES=true
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

# Get remaining arguments
if [[ $# -gt 0 ]]; then
    TARGET_DOMAIN="$1"
fi

# Validate inputs
if [[ ! -f "$DNS_RECORDS_FILE" ]]; then
    log "ERROR: DNS records file not found: $DNS_RECORDS_FILE"
    exit 1
fi

if [[ ! -f "$FORWARD_TEMPLATE" ]] && [[ "$REVERSE_ONLY" != "true" ]]; then
    log "ERROR: Forward zone template not found: $FORWARD_TEMPLATE"
    exit 1
fi

if [[ ! -f "$REVERSE_TEMPLATE" ]] && [[ "$FORWARD_ONLY" != "true" ]]; then
    log "ERROR: Reverse zone template not found: $REVERSE_TEMPLATE"
    exit 1
fi

# Check for required tools
for tool in yq python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        log "ERROR: $tool is required but not installed"
        exit 1
    fi
done

if ! python3 -c "import yaml, jinja2" 2>/dev/null; then
    log "ERROR: Required Python modules not found (yaml, jinja2)"
    log "Install with: pip3 install pyyaml jinja2"
    exit 1
fi

log "Starting DNS zone generation..."
log "Records file: $DNS_RECORDS_FILE"
log "Forward template: $FORWARD_TEMPLATE"
log "Reverse template: $REVERSE_TEMPLATE"

# Create zone generation script
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOF'
#!/usr/bin/env python3
import yaml
import sys
from jinja2 import Template
from datetime import datetime
import ipaddress
import os

def load_dns_records(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def load_template(file_path):
    with open(file_path, 'r') as f:
        return Template(f.read())

def generate_serial():
    """Generate DNS serial number in YYYYMMDDNN format"""
    return datetime.now().strftime('%Y%m%d01')

def generate_forward_zone(data, template, domain=None):
    """Generate forward DNS zone file"""
    dns_config = data.get('dns_config', {})
    
    if domain and domain != dns_config.get('domain'):
        return None
    
    # Prepare template variables
    template_vars = {
        'DOMAIN_NAME': dns_config.get('domain', 'example.local'),
        'GENERATION_DATE': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'PRIMARY_NS': dns_config.get('primary_ns', 'ns1.example.local'),
        'ADMIN_EMAIL': dns_config.get('admin_email', 'admin.example.local'),
        'SERIAL': generate_serial(),
        'DEFAULT_TTL': dns_config.get('default_ttl', 86400),
        'REFRESH': dns_config.get('refresh', 3600),
        'RETRY': dns_config.get('retry', 1800),  
        'EXPIRE': dns_config.get('expire', 604800),
        'MIN_TTL': dns_config.get('min_ttl', 86400),
        'SECONDARY_NS': dns_config.get('secondary_ns', []),
        'MX_RECORDS': dns_config.get('mx_records', []),
        'A_RECORDS': data.get('a_records', []),
        'AAAA_RECORDS': data.get('aaaa_records', []),
        'CNAME_RECORDS': data.get('cname_records', []),
        'TXT_RECORDS': data.get('txt_records', []),
        'SRV_RECORDS': data.get('srv_records', [])
    }
    
    return template.render(**template_vars)

def generate_reverse_zones(data, template, target_network=None):
    """Generate reverse DNS zone files"""
    dns_config = data.get('dns_config', {})
    reverse_zones = data.get('reverse_zones', [])
    
    generated_zones = {}
    
    for zone_config in reverse_zones:
        network = zone_config.get('network')
        zone_name = zone_config.get('zone_name')
        
        if target_network and network != target_network:
            continue
        
        template_vars = {
            'NETWORK': network,
            'GENERATION_DATE': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'PRIMARY_NS': dns_config.get('primary_ns', 'ns1.example.local'),
            'ADMIN_EMAIL': dns_config.get('admin_email', 'admin.example.local'),
            'SERIAL': generate_serial(),
            'DEFAULT_TTL': dns_config.get('default_ttl', 86400),
            'REFRESH': dns_config.get('refresh', 3600),
            'RETRY': dns_config.get('retry', 1800),
            'EXPIRE': dns_config.get('expire', 604800),
            'MIN_TTL': dns_config.get('min_ttl', 86400),
            'SECONDARY_NS': dns_config.get('secondary_ns', []),
            'PTR_RECORDS': zone_config.get('records', [])
        }
        
        generated_zones[zone_name] = template.render(**template_vars)
    
    return generated_zones

def main():
    if len(sys.argv) < 6:
        print("Usage: script.py <records_file> <forward_template> <reverse_template> <forward_dir> <reverse_dir> [domain] [network]")
        sys.exit(1)
    
    records_file = sys.argv[1]
    forward_template_file = sys.argv[2] if sys.argv[2] != "SKIP" else None
    reverse_template_file = sys.argv[3] if sys.argv[3] != "SKIP" else None
    forward_dir = sys.argv[4]
    reverse_dir = sys.argv[5]
    target_domain = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "ALL" else None
    target_network = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] != "ALL" else None
    
    # Load data
    data = load_dns_records(records_file)
    
    # Generate forward zone
    if forward_template_file:
        template = load_template(forward_template_file)
        forward_zone = generate_forward_zone(data, template, target_domain)
        
        if forward_zone:
            domain = target_domain or data.get('dns_config', {}).get('domain', 'example.local')
            output_file = os.path.join(forward_dir, f"{domain}.zone")
            
            with open(output_file, 'w') as f:
                f.write(forward_zone)
            print(f"Generated forward zone: {output_file}")
    
    # Generate reverse zones
    if reverse_template_file:
        template = load_template(reverse_template_file)
        reverse_zones = generate_reverse_zones(data, template, target_network)
        
        for zone_name, zone_content in reverse_zones.items():
            output_file = os.path.join(reverse_dir, f"{zone_name}.zone")
            
            with open(output_file, 'w') as f:
                f.write(zone_content)
            print(f"Generated reverse zone: {output_file}")

if __name__ == "__main__":
    main()
EOF

chmod +x "$TEMP_SCRIPT"

# Determine what to generate
FORWARD_TEMPLATE_ARG="$FORWARD_TEMPLATE"
REVERSE_TEMPLATE_ARG="$REVERSE_TEMPLATE"
DOMAIN_ARG="ALL"
NETWORK_ARG="ALL"

if [[ "$REVERSE_ONLY" == "true" ]]; then
    FORWARD_TEMPLATE_ARG="SKIP"
fi

if [[ "$FORWARD_ONLY" == "true" ]]; then
    REVERSE_TEMPLATE_ARG="SKIP"
fi

if [[ -n "$TARGET_DOMAIN" ]]; then
    DOMAIN_ARG="$TARGET_DOMAIN"
fi

# Generate zones
log "Generating DNS zones..."
if python3 "$TEMP_SCRIPT" "$DNS_RECORDS_FILE" "$FORWARD_TEMPLATE_ARG" "$REVERSE_TEMPLATE_ARG" "$FORWARD_OUTPUT_DIR" "$REVERSE_OUTPUT_DIR" "$DOMAIN_ARG" "$NETWORK_ARG"; then
    log "Zone generation completed successfully"
    
    # Validate zones if requested
    if [[ "$VALIDATE_ZONES" == "true" ]]; then
        log "Validating generated zone files..."
        
        if command -v named-checkzone >/dev/null 2>&1; then
            # Validate forward zones
            for zone_file in "$FORWARD_OUTPUT_DIR"/*.zone; do
                if [[ -f "$zone_file" ]]; then
                    zone_name=$(basename "$zone_file" .zone)
                    log "Validating forward zone: $zone_name"
                    if named-checkzone "$zone_name" "$zone_file" >/dev/null 2>&1; then
                        log "  ✓ Valid"
                    else
                        log "  ✗ Invalid"
                    fi
                fi
            done
            
            # Validate reverse zones
            for zone_file in "$REVERSE_OUTPUT_DIR"/*.zone; do
                if [[ -f "$zone_file" ]]; then
                    zone_name=$(basename "$zone_file" .zone)
                    log "Validating reverse zone: $zone_name"
                    if named-checkzone "$zone_name" "$zone_file" >/dev/null 2>&1; then
                        log "  ✓ Valid"
                    else
                        log "  ✗ Invalid"
                    fi
                fi
            done
        else
            log "WARNING: named-checkzone not available for validation"
        fi
    fi
    
    # Summary
    FORWARD_COUNT=$(find "$FORWARD_OUTPUT_DIR" -name "*.zone" 2>/dev/null | wc -l)
    REVERSE_COUNT=$(find "$REVERSE_OUTPUT_DIR" -name "*.zone" 2>/dev/null | wc -l)
    
    log "Generation summary:"
    log "  Forward zones: $FORWARD_COUNT"
    log "  Reverse zones: $REVERSE_COUNT"
    
else
    log "ERROR: Zone generation failed"
    rm -f "$TEMP_SCRIPT"
    exit 1
fi

# Cleanup
rm -f "$TEMP_SCRIPT"

log "DNS zone generation completed successfully"
