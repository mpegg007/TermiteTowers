#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/management/update-kea-config.py:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 6fff8a3adfe46716b64e78c7e9bcaeb276274f0e %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:27:57 %
#  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
#  %ccm_git_file_name: update-kea-config.py %
#  %ccm_git_path: infra/dhcp/scripts/management/update-kea-config.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2647 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 
"""
Direct Kea JSON Config Editor
Reads CSV, updates kea-dhcp4.conf directly with all reservations
"""

import csv
import json
import re
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up to infra/dhcp
CSV_FILE = str(PROJECT_ROOT / "inventory" / "network_devices-20250925.csv")
KEA_CONFIG = str(PROJECT_ROOT / "configs" / "kea" / "kea-dhcp4.conf")

def sanitize_hostname(hostname: str) -> str:
    if not hostname:
        return ""
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', hostname.lower())
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    if sanitized and sanitized[0].isdigit():
        sanitized = f"device-{sanitized}"
    return sanitized[:63]

def create_enhanced_hostname(row, ip):
    hostname_sources = [
        row.get('customName', '').strip(),
        row.get('tl_name', '').strip(), 
        row.get('Hostname', '').strip(),
        row.get('productName', '').strip(),
    ]
    
    for source in hostname_sources:
        if source and source.lower() not in ['', 'unknown', 'null']:
            base_name = sanitize_hostname(source)
            location = row.get('tl_location', '').strip()
            if location and location.lower() not in ['', 'unknown', 'null']:
                location_clean = sanitize_hostname(location)
                return f"{base_name}-{location_clean}"
            return base_name
    
    last_octet = ip.split('.')[-1]
    return f"device-{last_octet}"

# Load CSV devices
devices = []
with open(CSV_FILE, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ip = row.get('IP', '').strip()
        mac = row.get('MAC', '').strip()
        if ip and mac and ip.startswith('192.168.1.'):
            devices.append(row)

print(f"Found {len(devices)} devices from CSV")

# Load existing Kea config
with open(KEA_CONFIG, 'r') as f:
    config = json.load(f)

# Clear existing reservations and add all from CSV
reservations = []
for device in devices:
    ip = device['IP']
    mac = device['MAC']
    hostname = create_enhanced_hostname(device, ip)
    
    reservation = {
        "hw-address": mac.lower(),
        "ip-address": ip,
        "hostname": hostname
    }
    reservations.append(reservation)
    print(f"Added: {ip} -> {mac} ({hostname})")

# Update the config
config['Dhcp4']['subnet4'][0]['reservations'] = reservations

# Write updated config
with open(KEA_CONFIG, 'w') as f:
    json.dump(config, f, indent=4)

print(f"\nUpdated {KEA_CONFIG} with {len(reservations)} reservations")
print("Restart Kea to apply changes")
