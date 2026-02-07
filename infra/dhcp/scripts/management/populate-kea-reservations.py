#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: f8dd826b24cf6b73d1e0c5ec214e1919b53c0a30 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-02-07 15:39:16 %
#  %ccm_git_file_last_modified: 2025-09-27 11:32:31 %
#  %ccm_git_file_name: populate-kea-reservations.py %
#  %ccm_git_path: infra/dhcp/scripts/management/populate-kea-reservations.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 8545 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Kea DHCP Reservation Population Script
Automatically populates DHCP reservations from CSV inventory into Kea DHCP server
"""

import csv
import json
import socket
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up to infra/dhcp
CSV_FILE = str(PROJECT_ROOT / "inventory" / "network_devices-20250925.csv")
KEA_SOCKET = "/mnt/ai_storage/dhcp/kea-run/kea4-ctrl-socket"  # ⚠️ CANNOT CHANGE: Runtime socket path
SUBNET_ID = 1  # From our kea-dhcp4.conf

# Multi-scope IP ranges for categorization
IP_RANGES = {
    "Core-Infrastructure": (1, 9),      # Network appliances
    "Servers": (10, 49),                # Server infrastructure  
    "Smart-Home-Fixed": (100, 199),     # Smart home devices
    "Dynamic-Clients": (200, 249),      # Mobile devices, guests
    "Special-Services": (250, 254),     # Special network services
}

def get_ip_category(ip: str) -> str:
    """Determine the category of an IP address based on our ranges."""
    try:
        last_octet = int(ip.split('.')[-1])
        for category, (start, end) in IP_RANGES.items():
            if start <= last_octet <= end:
                return category
        return "Unknown"
    except (ValueError, IndexError):
        return "Unknown"

def sanitize_hostname(hostname: str) -> str:
    """Sanitize hostname to be DNS-compliant."""
    if not hostname:
        return ""
    
    # Remove non-alphanumeric chars except hyphens, convert to lowercase
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', hostname.lower())
    
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    
    # Ensure it doesn't start with a number (DNS requirement)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"device-{sanitized}"
    
    return sanitized[:63]  # Max DNS label length

def create_enhanced_hostname(row: Dict[str, str], ip: str) -> str:
    """Create an enhanced hostname based on device information."""
    # Get category for prefix
    category = get_ip_category(ip)
    
    # Try different hostname sources
    hostname_sources = [
        row.get('customName', '').strip(),
        row.get('tl_name', '').strip(), 
        row.get('Hostname', '').strip(),
        row.get('productName', '').strip(),
        row.get('model', '').strip()
    ]
    
    base_name = None
    for source in hostname_sources:
        if source and source.lower() not in ['', 'unknown', 'null']:
            base_name = source
            break
    
    if not base_name:
        # Create generic name based on IP
        last_octet = ip.split('.')[-1]
        base_name = f"device-{last_octet}"
    
    # Sanitize the base name
    sanitized_base = sanitize_hostname(base_name)
    
    # Add location info if available
    location = row.get('tl_location', '').strip()
    if location and location.lower() not in ['', 'unknown', 'null']:
        location_clean = sanitize_hostname(location)
        return f"{sanitized_base}-{location_clean}"
    
    return sanitized_base

def send_kea_command(socket_path: str, command: dict) -> dict:
    """Send a command to Kea via Unix socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        
        # Send the command as JSON
        message = json.dumps(command)
        sock.sendall(message.encode())
        
        # Receive the response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # Try to parse as JSON - if successful, we have the full message
            try:
                json.loads(response.decode())
                break
            except json.JSONDecodeError:
                continue
                
        sock.close()
        return json.loads(response.decode())
    
    except Exception as e:
        print(f"Error communicating with Kea: {e}")
        return {"result": 1, "text": str(e)}

def load_csv_devices(csv_file: str) -> List[Dict[str, str]]:
    """Load device information from CSV file."""
    devices = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row.get('IP', '').strip()
            mac = row.get('MAC', '').strip()
            
            # Skip rows without both IP and MAC
            if not ip or not mac or ip == '' or mac == '':
                continue
                
            # Only process 192.168.1.x addresses
            if not ip.startswith('192.168.1.'):
                continue
                
            devices.append(row)
    
    return devices

def create_reservation(device: Dict[str, str]) -> Dict:
    """Create a Kea reservation from device data."""
    ip = device['IP'].strip()
    mac = device['MAC'].strip().lower()
    hostname = create_enhanced_hostname(device, ip)
    category = get_ip_category(ip)
    
    reservation = {
        "subnet-id": SUBNET_ID,
        "hw-address": mac,
        "ip-address": ip,
    }
    
    if hostname:
        reservation["hostname"] = hostname
        
    return reservation

def add_reservation_to_kea(reservation: Dict) -> bool:
    """Add a single reservation to Kea DHCP server."""
    command = {
        "command": "reservation-add",
        "service": ["dhcp4"],
        "arguments": reservation
    }
    
    response = send_kea_command(KEA_SOCKET, command)
    
    if response.get("result") == 0:
        return True
    else:
        error_text = response.get("text", "Unknown error")
        print(f"Failed to add reservation for {reservation.get('ip-address')}: {error_text}")
        return False

def main():
    print("Kea DHCP Reservation Population Script")
    print("=" * 50)
    
    # Check if CSV file exists
    if not Path(CSV_FILE).exists():
        print(f"Error: CSV file not found: {CSV_FILE}")
        sys.exit(1)
    
    # Check if Kea socket exists
    if not Path(KEA_SOCKET).exists():
        print(f"Error: Kea control socket not found: {KEA_SOCKET}")
        print("Make sure Kea DHCP server is running and the socket path is correct.")
        sys.exit(1)
    
    # Load devices from CSV
    print(f"Loading devices from {CSV_FILE}...")
    devices = load_csv_devices(CSV_FILE)
    print(f"Found {len(devices)} devices with valid IP/MAC pairs")
    
    # Group devices by category for reporting
    categories = {}
    for device in devices:
        category = get_ip_category(device['IP'])
        if category not in categories:
            categories[category] = []
        categories[category].append(device)
    
    print("\nDevice breakdown by category:")
    for category, devs in categories.items():
        print(f"  {category}: {len(devs)} devices")
    
    # Test Kea connectivity
    print(f"\nTesting connection to Kea...")
    test_command = {"command": "list-commands", "service": ["dhcp4"]}
    response = send_kea_command(KEA_SOCKET, test_command)
    
    if response.get("result") != 0:
        print(f"Error: Cannot communicate with Kea DHCP server")
        print(f"Response: {response}")
        sys.exit(1)
    
    print("Successfully connected to Kea DHCP server")
    
    # Process each device
    print(f"\nAdding {len(devices)} reservations...")
    successful = 0
    failed = 0
    
    for i, device in enumerate(devices, 1):
        ip = device['IP']
        mac = device['MAC']
        hostname = create_enhanced_hostname(device, ip)
        category = get_ip_category(ip)
        
        print(f"[{i:2d}/{len(devices)}] {ip} ({mac}) -> {hostname} [{category}]", end=" ")
        
        reservation = create_reservation(device)
        
        if add_reservation_to_kea(reservation):
            print("✓")
            successful += 1
        else:
            print("✗")
            failed += 1
    
    print(f"\nSummary:")
    print(f"  Successfully added: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(devices)}")
    
    if successful > 0:
        print(f"\n✓ DHCP reservations have been populated!")
        print(f"  You can now manage them via Kea's web interface or API")
    
    if failed > 0:
        print(f"\n⚠ {failed} reservations failed - check logs for details")

if __name__ == "__main__":
    main()
