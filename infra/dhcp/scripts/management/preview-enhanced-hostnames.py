#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/management/preview-enhanced-hostnames.py:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 6d5978d6d0c67d1bb0376bf830ad74544865c4f3 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:27:57 %
#  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
#  %ccm_git_file_name: preview-enhanced-hostnames.py %
#  %ccm_git_path: infra/dhcp/scripts/management/preview-enhanced-hostnames.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3909 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 
"""
Enhanced hostname generator for Technitium DHCP reservations
Creates descriptive hostnames using all available CSV data
"""

import csv
import re
from typing import Dict, Optional

def create_enhanced_hostname(row: Dict[str, str]) -> str:
    """Create a descriptive hostname from CSV data"""
    
    # Priority order for hostname components
    custom_name = row.get('customName', '').strip()
    location = row.get('tl_location', '').strip()
    model = row.get('model', '').strip()
    product_name = row.get('productName', '').strip()
    hostname = row.get('Hostname', '').strip()
    ip = row.get('IP', '').strip()
    
    # Clean and prepare components
    parts = []
    
    # 1. Custom name (highest priority)
    if custom_name and custom_name not in ['', 'device']:
        parts.append(clean_name(custom_name))
    
    # 2. Location information
    if location and location not in ['', 'device']:
        parts.append(f"[{clean_name(location)}]")
    
    # 3. Product type/model (if meaningful)
    if product_name and len(product_name) < 30:
        clean_product = clean_name(product_name)
        if clean_product and clean_product not in ['device', 'smart']:
            parts.append(f"({clean_product})")
    
    # 4. Fallback to hostname if available
    if not parts and hostname:
        parts.append(clean_name(hostname))
    
    # 5. Final fallback to IP-based name
    if not parts and ip:
        parts.append(f"device-{ip.split('.')[-1]}")
    
    # Combine parts and ensure reasonable length
    result = "-".join(parts)
    if len(result) > 60:  # Technitium hostname limit
        result = result[:57] + "..."
    
    return result or "unknown-device"

def clean_name(name: str) -> str:
    """Clean and sanitize names for hostnames"""
    if not name:
        return ""
    
    # Remove common prefixes/suffixes
    cleaned = name.strip()
    prefixes_to_remove = ['tl.', 'smart ', 'Smart ', 'device-', 'Device ']
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    
    # Replace invalid characters with hyphens
    cleaned = re.sub(r'[^a-zA-Z0-9\-_]', '-', cleaned)
    
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    
    # Ensure not empty
    return cleaned if cleaned else ""

def generate_enhanced_device_list(csv_file: str) -> None:
    """Generate enhanced device list showing what will be visible in Technitium"""
    
    print("Enhanced DHCP Reservation Preview")
    print("=" * 80)
    print(f"{'IP':<15} {'MAC':<18} {'Enhanced Hostname'}")
    print("-" * 80)
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            ip = row.get('IP', '').strip()
            mac = row.get('MAC', '').strip()
            
            # Filter for 192.168.1.x with valid MAC
            if ip.startswith('192.168.1.') and mac and is_valid_mac(mac):
                enhanced_name = create_enhanced_hostname(row)
                print(f"{ip:<15} {mac:<18} {enhanced_name}")
                count += 1
    
    print("-" * 80)
    print(f"Total: {count} enhanced entries")

def is_valid_mac(mac: str) -> bool:
    """Validate MAC address format"""
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(mac_pattern.match(mac))

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # Default to relative path
    SCRIPT_DIR = Path(__file__).parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up to infra/dhcp
    default_csv = str(PROJECT_ROOT / "inventory" / "network_devices-20250925.csv")
    
    csv_file = sys.argv[1] if len(sys.argv) > 1 else default_csv
    generate_enhanced_device_list(csv_file)
