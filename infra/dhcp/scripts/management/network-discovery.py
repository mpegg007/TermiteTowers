#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/management/network-discovery.py:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 3beb0beb37cfa47bff1291c33eab4d36135c4847 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:12:09 %
#  %ccm_git_file_last_modified: 2025-09-27 10:44:56 %
#  %ccm_git_file_name: network-discovery.py %
#  %ccm_git_path: infra/dhcp/scripts/management/network-discovery.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 14011 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Network Device Discovery and Display Script
Discovers devices on both 192.168.1.0/24 and 192.168.4.0/24 networks
Displays comprehensive network information without requiring DHCP server access
"""

import subprocess
import threading
import json
import csv
import socket
import ipaddress
import time
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import yaml
from pathlib import Path

# Configuration
NETWORKS = ["192.168.1.0/24", "192.168.4.0/24"]

# Use relative paths for data files in current directory
SCRIPT_DIR = Path(__file__).parent
TUYA_CLOUD_FILE = SCRIPT_DIR / "tuyacloud_devices.json"
STATIC_CSV_FILE = SCRIPT_DIR / "tt.omp.dhcp.csv"
YAML_OUTPUT_FILE = SCRIPT_DIR / "discovered_devices.yaml"
MAX_THREADS = 50
PING_TIMEOUT = 2

class NetworkScanner:
    def __init__(self):
        self.discovered_devices = {}
        self.tuya_devices = {}
        self.static_devices = {}
        self.load_existing_data()

    def load_existing_data(self):
        """Load existing device data from various sources"""
        # Load Tuya cloud devices
        try:
            with open(str(TUYA_CLOUD_FILE), 'r') as f:
                tuya_data = json.load(f)
                for device in tuya_data:
                    ip = device.get('tl_ip', device.get('IP', ''))
                    if ip:
                        self.tuya_devices[ip] = device
            print(f"Loaded {len(self.tuya_devices)} Tuya devices")
        except FileNotFoundError:
            print(f"Tuya cloud file {TUYA_CLOUD_FILE} not found")
        except Exception as e:
            print(f"Error loading Tuya data: {e}")

        # Load static CSV devices
        try:
            with open(str(STATIC_CSV_FILE), 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=["mac", "ip", "name", "location"])
                for row in reader:
                    if row['ip']:
                        self.static_devices[row['ip']] = row
            print(f"Loaded {len(self.static_devices)} static devices")
        except FileNotFoundError:
            print(f"Static CSV file {STATIC_CSV_FILE} not found")
        except Exception as e:
            print(f"Error loading static CSV data: {e}")

    def ping_host(self, ip):
        """Ping a host to check if it's alive"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(PING_TIMEOUT), ip],
                capture_output=True,
                text=True,
                timeout=PING_TIMEOUT + 1
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def get_mac_address(self, ip):
        """Get MAC address from ARP table"""
        try:
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ip in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            mac = parts[2]
                            if ':' in mac and len(mac) == 17:
                                return mac.lower()
        except Exception:
            pass
        return None

    def resolve_hostname(self, ip):
        """Resolve hostname from IP"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return None

    def get_device_vendor(self, mac):
        """Get device vendor from MAC address (simplified)"""
        if not mac:
            return None
        
        # Common prefixes for known devices in your network
        vendor_map = {
            '3c:18:a0': 'Intel',
            '14:da:e9': 'Unknown',
            '08:00:27': 'VirtualBox',
            'cc:8c:bf': 'Tuya Smart',
            'b4:e6:2d': 'Tuya Smart',
            '84:f3:eb': 'Tuya Smart',
            '60:01:94': 'Tuya Smart',
            'e8:db:84': 'Tuya Smart',
            'dc:4f:22': 'Tuya Smart',
            '3c:61:05': 'Tuya Smart',
            '3c:0b:59': 'Tuya Smart',
            'bc:dd:c2': 'Tuya Smart',
            'b8:27:eb': 'Raspberry Pi',
            '00:e0:f8': 'Camera/IP Device',
            'c0:74:ad': 'Camera/IP Device',
        }
        
        mac_prefix = mac[:8].upper()
        for prefix, vendor in vendor_map.items():
            if mac.lower().startswith(prefix.lower()):
                return vendor
        
        return 'Unknown'

    def scan_network(self, network):
        """Scan a network for active devices"""
        net = ipaddress.IPv4Network(network)
        active_devices = {}
        
        print(f"Scanning network {network}...")
        
        # Use threading to speed up scanning
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            # Submit ping jobs
            future_to_ip = {
                executor.submit(self.ping_host, str(ip)): str(ip) 
                for ip in net.hosts()
            }
            
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        print(f"  Found active device: {ip}")
                        active_devices[ip] = {
                            'ip': ip,
                            'network': network,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'active'
                        }
                except Exception as e:
                    print(f"  Error checking {ip}: {e}")
        
        # Get additional info for active devices
        for ip in active_devices:
            device = active_devices[ip]
            
            # Get MAC address
            device['mac'] = self.get_mac_address(ip)
            
            # Get hostname
            device['hostname'] = self.resolve_hostname(ip)
            
            # Get vendor
            device['vendor'] = self.get_device_vendor(device['mac'])
            
            # Merge with existing data
            if ip in self.tuya_devices:
                tuya_info = self.tuya_devices[ip]
                device.update({
                    'device_name': tuya_info.get('tl_name', tuya_info.get('customName', '')),
                    'device_type': 'smart_device',
                    'location': tuya_info.get('tl_location', ''),
                    'model': tuya_info.get('model', ''),
                    'tuya_id': tuya_info.get('tl_deviceid', ''),
                    'product_name': tuya_info.get('productName', ''),
                    'is_online': tuya_info.get('isOnline', False)
                })
            
            if ip in self.static_devices:
                static_info = self.static_devices[ip]
                device.update({
                    'static_name': static_info.get('name', ''),
                    'static_location': static_info.get('location', ''),
                    'is_static': True
                })
        
        return active_devices

    def scan_all_networks(self):
        """Scan all configured networks"""
        all_devices = {}
        
        for network in NETWORKS:
            devices = self.scan_network(network)
            all_devices.update(devices)
        
        self.discovered_devices = all_devices
        return all_devices

    def display_results(self, format='table'):
        """Display scan results in specified format"""
        if not self.discovered_devices:
            print("No devices discovered")
            return

        if format == 'table':
            self.display_table()
        elif format == 'json':
            self.display_json()
        elif format == 'yaml':
            self.display_yaml()

    def display_table(self):
        """Display results in table format"""
        print(f"\n{'='*120}")
        print("NETWORK DEVICE DISCOVERY RESULTS")
        print(f"Scan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*120}")
        
        # Sort by IP address
        sorted_devices = sorted(
            self.discovered_devices.items(),
            key=lambda x: ipaddress.IPv4Address(x[0])
        )
        
        # Header
        print(f"{'IP Address':<15} {'MAC Address':<18} {'Hostname':<20} {'Device Name':<25} {'Type':<15} {'Vendor':<15}")
        print("-" * 120)
        
        for ip, device in sorted_devices:
            ip_str = device.get('ip', '')[:15]
            mac_str = device.get('mac', 'Unknown')[:18]
            hostname = device.get('hostname', device.get('static_name', ''))[:20]
            device_name = device.get('device_name', device.get('static_name', ''))[:25]
            device_type = device.get('device_type', 'unknown')[:15]
            vendor = device.get('vendor', 'Unknown')[:15]
            
            print(f"{ip_str:<15} {mac_str:<18} {hostname:<20} {device_name:<25} {device_type:<15} {vendor:<15}")
        
        print(f"\nTotal devices found: {len(self.discovered_devices)}")
        
        # Network summary
        network_summary = {}
        for device in self.discovered_devices.values():
            network = device.get('network', 'unknown')
            network_summary[network] = network_summary.get(network, 0) + 1
        
        print("\nNetwork Summary:")
        for network, count in network_summary.items():
            print(f"  {network}: {count} devices")

    def display_json(self):
        """Display results in JSON format"""
        print(json.dumps(self.discovered_devices, indent=2, default=str))

    def display_yaml(self):
        """Display results in YAML format"""
        # Prepare data for YAML output
        yaml_data = {
            'scan_info': {
                'timestamp': datetime.now().isoformat(),
                'networks_scanned': NETWORKS,
                'total_devices': len(self.discovered_devices)
            },
            'devices': []
        }
        
        for ip, device in sorted(self.discovered_devices.items(), key=lambda x: ipaddress.IPv4Address(x[0])):
            yaml_device = {
                'ip': ip,
                'mac': device.get('mac'),
                'hostname': device.get('hostname'),
                'device_name': device.get('device_name'),
                'device_type': device.get('device_type', 'unknown'),
                'vendor': device.get('vendor'),
                'network': device.get('network'),
                'location': device.get('location', device.get('static_location', '')),
                'is_static': device.get('is_static', False),
                'is_online': device.get('is_online', True),
                'last_seen': device.get('timestamp')
            }
            yaml_data['devices'].append(yaml_device)
        
        print(yaml.dump(yaml_data, default_flow_style=False, sort_keys=False))

    def save_results(self, filename=None):
        """Save results to YAML file"""
        if filename is None:
            filename = str(YAML_OUTPUT_FILE)
        
        # Prepare data for YAML output
        yaml_data = {
            'scan_info': {
                'timestamp': datetime.now().isoformat(),
                'networks_scanned': NETWORKS,
                'total_devices': len(self.discovered_devices)
            },
            'devices': []
        }
        
        for ip, device in sorted(self.discovered_devices.items(), key=lambda x: ipaddress.IPv4Address(x[0])):
            yaml_device = {
                'ip': ip,
                'mac': device.get('mac'),
                'hostname': device.get('hostname'),
                'device_name': device.get('device_name'),
                'device_type': device.get('device_type', 'unknown'),
                'vendor': device.get('vendor'),
                'network': device.get('network'),
                'location': device.get('location', device.get('static_location', '')),
                'is_static': device.get('is_static', False),
                'is_online': device.get('is_online', True),
                'last_seen': device.get('timestamp')
            }
            # Remove None values
            yaml_device = {k: v for k, v in yaml_device.items() if v is not None}
            yaml_data['devices'].append(yaml_device)
        
        with open(filename, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"Results saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Network Device Discovery and Display')
    parser.add_argument('--format', choices=['table', 'json', 'yaml'], default='table',
                        help='Output format (default: table)')
    parser.add_argument('--save', metavar='FILE',
                        help='Save results to YAML file')
    parser.add_argument('--networks', nargs='+', default=NETWORKS,
                        help='Networks to scan (default: 192.168.1.0/24 192.168.4.0/24)')
    parser.add_argument('--quick', action='store_true',
                        help='Quick scan (faster but less detailed)')
    
    args = parser.parse_args()
    
    # Update networks if specified
    global NETWORKS
    NETWORKS = args.networks
    
    scanner = NetworkScanner()
    
    print("Starting network device discovery...")
    print(f"Networks to scan: {', '.join(NETWORKS)}")
    
    start_time = time.time()
    scanner.scan_all_networks()
    end_time = time.time()
    
    print(f"Scan completed in {end_time - start_time:.2f} seconds")
    
    scanner.display_results(args.format)
    
    if args.save:
        scanner.save_results(args.save)
    elif args.format == 'yaml':
        # Auto-save if outputting YAML
        scanner.save_results()

if __name__ == "__main__":
    main()
