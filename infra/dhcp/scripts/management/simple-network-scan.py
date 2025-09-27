#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/management/simple-network-scan.py:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 07c9a4fbf04dae7cd90fd7ab892339e8c5665964 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-27 11:27:57 %
#  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
#  %ccm_git_file_name: simple-network-scan.py %
#  %ccm_git_path: infra/dhcp/scripts/management/simple-network-scan.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 20944 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 
"""
Simple Network Device Scanner
Lightweight version that doesn't require external dependencies
Scans both 192.168.1.0/24 and 192.168.4.0/24 networks for active devices
"""

import subprocess
import threading
import json
import csv
import socket
import ipaddress
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import os
import struct
from pathlib import Path

# Configuration
NETWORKS = ["192.168.1.0/24", "192.168.4.0/24"]
MAX_THREADS = 50
PING_TIMEOUT = 2

class SimpleNetworkScanner:
    def __init__(self):
        self.discovered_devices = {}
        self.tuya_devices = {}
        self.static_devices = {}
        
    def load_tuya_data(self):
        """Load Tuya device data if available"""
        script_dir = Path(__file__).parent
        tuya_file = script_dir / "tuyacloud_devices.json"
        if os.path.exists(tuya_file):
            try:
                with open(tuya_file, 'r') as f:
                    tuya_data = json.load(f)
                    # Handle both list and dict formats
                    if isinstance(tuya_data, list):
                        for device in tuya_data:
                            if isinstance(device, dict):
                                ip = device.get('tl_ip', device.get('IP', ''))
                                if ip:
                                    self.tuya_devices[ip] = device
                    elif isinstance(tuya_data, dict):
                        for key, device in tuya_data.items():
                            if isinstance(device, dict):
                                ip = device.get('tl_ip', device.get('IP', ''))
                                if ip:
                                    self.tuya_devices[ip] = device
                print(f"Loaded {len(self.tuya_devices)} Tuya devices")
            except Exception as e:
                print(f"Error loading Tuya data: {e}")
    
    def load_static_data(self):
        """Load static device data if available"""
        script_dir = Path(__file__).parent
        static_file = script_dir / "tt.omp.dhcp.csv"
        if os.path.exists(static_file):
            try:
                with open(static_file, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile, fieldnames=["mac", "ip", "name", "location"])
                    for row in reader:
                        if row['ip']:
                            self.static_devices[row['ip']] = row
                print(f"Loaded {len(self.static_devices)} static devices")
            except Exception as e:
                print(f"Error loading static data: {e}")

    def ping_host(self, ip):
        """Check if host is alive"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(PING_TIMEOUT), ip],
                capture_output=True,
                text=True,
                timeout=PING_TIMEOUT + 1
            )
            return result.returncode == 0
        except:
            return False

    def get_mac_from_arp(self, ip):
        """Get MAC address from ARP table"""
        try:
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ip in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            mac = parts[2]
                            if ':' in mac and len(mac) == 17:
                                return mac.lower()
        except:
            pass
        return None

    def get_mdns_services(self):
        """Get all mDNS services and their IP mappings - simplified version"""
        mdns_map = {}
        try:
            # Get ESPHome devices with longer timeout
            result = subprocess.run(['avahi-browse', '-rt', '_esphomelib._tcp'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                current_service = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('=') and '_esphomelib._tcp' in line:
                        # Extract service name
                        parts = line.split()
                        if len(parts) >= 4:
                            current_service = parts[3]
                    elif line.startswith('address = [') and current_service:
                        # Extract IP address
                        ip = line.replace('address = [', '').replace(']', '')
                        if ip and current_service:
                            mdns_map[ip] = current_service
                            print(f"  Found mDNS: {ip} -> {current_service}")
            
            # Also try HTTP services for additional IoT devices
            try:
                result2 = subprocess.run(['avahi-browse', '-rt', '_http._tcp'], 
                                       capture_output=True, text=True, timeout=8)
                if result2.returncode == 0:
                    current_service = None
                    for line in result2.stdout.split('\n'):
                        line = line.strip()
                        if line.startswith('=') and '_http._tcp' in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                current_service = parts[3]
                        elif line.startswith('address = [') and current_service:
                            ip = line.replace('address = [', '').replace(']', '')
                            if ip and current_service and ip not in mdns_map:
                                mdns_map[ip] = current_service
                                print(f"  Found mDNS (HTTP): {ip} -> {current_service}")
            except:
                pass  # HTTP services are optional
                
        except Exception as e:
            print(f"mDNS discovery failed: {e}")
        
        return mdns_map

    def get_hostname(self, ip):
        """Get hostname via multiple methods including mDNS"""
        hostname = None
        
        # Try mDNS resolution first (like Home Assistant does)
        try:
            # Try avahi-resolve for mDNS names
            result = subprocess.run(['avahi-resolve', '-a', ip], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                parts = result.stdout.strip().split('\t')
                if len(parts) >= 2:
                    mdns_name = parts[1].replace('.local', '')
                    if mdns_name and not mdns_name.startswith(ip):
                        return mdns_name
        except FileNotFoundError:
            # avahi-resolve not available
            pass
        except:
            pass
        
        # Try using dig for mDNS if avahi not available
        try:
            # Reverse IP for mDNS query
            octets = ip.split('.')
            reversed_ip = f"{octets[3]}.{octets[2]}.{octets[1]}.{octets[0]}.in-addr.arpa"
            result = subprocess.run(['dig', '+short', '-x', ip, '@224.0.0.251'], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                mdns_name = result.stdout.strip().replace('.local.', '').replace('.local', '')
                if mdns_name and not mdns_name.startswith(ip):
                    return mdns_name
        except:
            pass
        
        # Try nmap for hostname detection
        try:
            result = subprocess.run(['nmap', '-sn', ip], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Nmap scan report for' in line and '(' in line:
                        # Extract hostname from "Nmap scan report for hostname (ip)"
                        hostname_part = line.split(' for ')[1].split(' (')[0]
                        if hostname_part and not hostname_part.startswith('192.168'):
                            return hostname_part
        except FileNotFoundError:
            # nmap not available
            pass
        except:
            pass
        
        # Try reverse DNS lookup
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            if hostname and not hostname.startswith(ip) and '.' in hostname:
                return hostname
        except:
            pass
        
        # Try ARP table for NetBIOS names (sometimes shows hostnames)
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ip in line and '(' in line and ')' in line:
                        # Look for patterns like "hostname (192.168.1.126) at mac"
                        before_ip = line.split(f'({ip})')[0].strip()
                        if before_ip and not before_ip.startswith('?'):
                            return before_ip
        except:
            pass
        
        return None

    def identify_vendor(self, mac):
        """Enhanced vendor identification"""
        if not mac:
            return "Unknown"
        
        vendor_prefixes = {
            '3c:18:a0': 'Intel',
            '14:da:e9': 'Generic Device',
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
            '00:e0:f8': 'IP Camera',
            'c0:74:ad': 'IP Camera',
            'a0:ad:9f': 'Network Device',
            '78:1c:3c': 'ESP32 Device',  # ESP32 common prefix
            '6c:c8:40': 'ESP32 Device',  # ESP32 common prefix
            '24:6f:28': 'ESP32 Device',  # ESP32 common prefix
            '30:ae:a4': 'ESP32 Device',  # ESP32 common prefix
            'd8:32:14': 'Generic Device',
            'dc:66:72': 'Samsung',
            'f8:17:2d': 'Generic Device',
            'e0:46:9a': 'Router/Gateway',
        }
        
        for prefix, vendor in vendor_prefixes.items():
            if mac.lower().startswith(prefix.lower()):
                return vendor
        
        return "Unknown"
    
    def get_device_info(self, ip, mac):
        """Get additional device information"""
        info = {}
        
        # Try to identify ESP32 devices by common characteristics
        if mac and any(mac.lower().startswith(prefix) for prefix in ['78:1c:3c', '6c:c8:40', '24:6f:28', '30:ae:a4']):
            info['device_type'] = 'esp32'
            
            # Try common ESP32 web interface ports with shorter timeout
            for port in [80]:  # Just check port 80 to speed up
                try:
                    result = subprocess.run(['curl', '-m', '1', '--connect-timeout', '1', f'http://{ip}:{port}'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0 and ('ESP32' in result.stdout or 'esp32' in result.stdout):
                        info['web_interface'] = f'http://{ip}:{port}'
                        break
                except:
                    continue
        
        return info

    def expand_network_range(self, network):
        """Expand range notation like 192.168.1.120-130 to individual IPs"""
        if '-' in network and not '/' in network:
            # Handle range notation
            parts = network.split('.')
            if len(parts) == 4 and '-' in parts[-1]:
                base = '.'.join(parts[:3])
                range_part = parts[-1]
                if '-' in range_part:
                    start, end = range_part.split('-')
                    ips = []
                    for i in range(int(start), int(end) + 1):
                        ips.append(f"{base}.{i}/32")
                    return ips
        # Return single network/IP as list
        return [network]

    def scan_network(self, network):
        """Scan a single network"""
        # Expand ranges if needed
        networks = self.expand_network_range(network)
        all_devices = {}
        
        for net_str in networks:
            net = ipaddress.IPv4Network(net_str)
            devices = {}
            
            if len(networks) == 1:
                print(f"\nScanning {network}...")
            elif len(networks) <= 11:  # Show individual IPs for small ranges
                print(f"  {net_str.replace('/32', '')}")
            
            # Ping sweep
            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                if net.num_addresses == 1:
                    # Single IP (like /32)
                    future_to_ip = {executor.submit(self.ping_host, str(net.network_address)): str(net.network_address)}
                else:
                    # Network range
                    future_to_ip = {
                        executor.submit(self.ping_host, str(ip)): str(ip) 
                        for ip in net.hosts()
                    }
                
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    if future.result():
                        if len(networks) <= 11:
                            print(f"  Active: {ip}")
                        devices[ip] = {'ip': ip, 'network': network}
            
            # Get details for active devices (process each network's devices)
            device_count = len(devices)
            for idx, ip in enumerate(devices, 1):
                device = devices[ip]
                print(f"  Gathering info for {ip} ({idx}/{device_count})...")
                device['mac'] = self.get_mac_from_arp(ip)
                
                # Check mDNS services first
                if hasattr(self, 'mdns_services') and ip in self.mdns_services:
                    device['hostname'] = self.mdns_services[ip]
                    device['mdns_name'] = self.mdns_services[ip]
                else:
                    device['hostname'] = self.get_hostname(ip)
                
                device['vendor'] = self.identify_vendor(device['mac'])
                device['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Get additional device info
                extra_info = self.get_device_info(ip, device['mac'])
                device.update(extra_info)
                
                # Add Tuya info if available
                if ip in self.tuya_devices:
                    tuya = self.tuya_devices[ip]
                    device['device_name'] = tuya.get('tl_name', tuya.get('customName', ''))
                    device['location'] = tuya.get('tl_location', '')
                    device['device_type'] = 'smart_device'
                
                # Add static info if available
                if ip in self.static_devices:
                    static = self.static_devices[ip]
                    device['static_name'] = static.get('name', '')
                    device['static_location'] = static.get('location', '')
                    
                # Override with better names if we have them
                if not device.get('device_name'):
                    if device.get('static_name'):
                        device['device_name'] = device['static_name']
                    elif device.get('mdns_name'):
                        device['device_name'] = device['mdns_name']
            
            # Add this network's devices to the overall collection
            all_devices.update(devices)
            
            if len(networks) > 11 and devices:
                print(f"  Found {len(devices)} active devices in this range")
        
        return all_devices

    def scan_all(self, skip_mdns=False):
        """Scan all networks"""
        self.load_tuya_data()
        self.load_static_data()
        
        # Get mDNS services first (unless skipped)
        if not skip_mdns:
            print("Discovering mDNS services...")
            self.mdns_services = self.get_mdns_services()
            print(f"Found {len(self.mdns_services)} mDNS services")
        else:
            self.mdns_services = {}
        
        all_devices = {}
        for network in NETWORKS:
            devices = self.scan_network(network)
            all_devices.update(devices)
        
        self.discovered_devices = all_devices
        return all_devices

    def display_table(self):
        """Display results in table format"""
        if not self.discovered_devices:
            print("No devices found")
            return

        print(f"\n{'='*100}")
        print("TERMITE TOWERS NETWORK SCAN RESULTS")
        print(f"Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")
        
        # Sort by IP
        sorted_devices = sorted(
            self.discovered_devices.items(),
            key=lambda x: ipaddress.IPv4Address(x[0])
        )
        
        # Table header
        fmt = "{:<15} {:<18} {:<20} {:<25} {:<15}"
        print(fmt.format("IP", "MAC", "Hostname", "Device Name", "Vendor"))
        print("-" * 100)
        
        for ip, device in sorted_devices:
            hostname = device.get('hostname', device.get('static_name', ''))
            device_name = device.get('device_name', device.get('static_name', ''))
            
            print(fmt.format(
                ip[:15],
                (device.get('mac') or 'Unknown')[:18],
                hostname[:20] if hostname else '',
                device_name[:25] if device_name else '',
                device.get('vendor', 'Unknown')[:15]
            ))
        
        # Summary
        print(f"\nDevices found: {len(self.discovered_devices)}")
        
        # Network breakdown
        net_counts = {}
        for device in self.discovered_devices.values():
            net = device.get('network', 'unknown')
            net_counts[net] = net_counts.get(net, 0) + 1
        
        for network, count in net_counts.items():
            print(f"  {network}: {count} devices")

    def save_simple_report(self, filename="network_scan_report.txt"):
        """Save a simple text report"""
        with open(filename, 'w') as f:
            f.write(f"Termite Towers Network Scan Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Networks: {', '.join(NETWORKS)}\n")
            f.write(f"{'='*80}\n\n")
            
            sorted_devices = sorted(
                self.discovered_devices.items(),
                key=lambda x: ipaddress.IPv4Address(x[0])
            )
            
            for ip, device in sorted_devices:
                f.write(f"IP: {ip}\n")
                if device.get('mac'):
                    f.write(f"  MAC: {device['mac']}\n")
                if device.get('hostname'):
                    f.write(f"  Hostname: {device['hostname']}\n")
                if device.get('device_name'):
                    f.write(f"  Device: {device['device_name']}\n")
                if device.get('location'):
                    f.write(f"  Location: {device['location']}\n")
                f.write(f"  Vendor: {device.get('vendor', 'Unknown')}\n")
                f.write(f"  Network: {device.get('network', 'Unknown')}\n")
                f.write("\n")
        
        print(f"Report saved to {filename}")

def main():
    global NETWORKS
    
    parser = argparse.ArgumentParser(description='Simple Network Scanner')
    parser.add_argument('--save', metavar='FILE', 
                        help='Save report to file')
    parser.add_argument('--networks', nargs='+', default=NETWORKS,
                        help='Networks to scan')
    parser.add_argument('--skip-mdns', action='store_true',
                        help='Skip mDNS discovery for faster scanning')
    
    args = parser.parse_args()
    
    if args.networks != NETWORKS:
        NETWORKS = args.networks
    
    scanner = SimpleNetworkScanner()
    
    print("Starting network scan...")
    print(f"Scanning: {', '.join(NETWORKS)}")
    
    start_time = time.time()
    scanner.scan_all(skip_mdns=args.skip_mdns)
    scan_time = time.time() - start_time
    
    print(f"\nScan completed in {scan_time:.1f} seconds")
    
    scanner.display_table()
    
    if args.save:
        scanner.save_simple_report(args.save)

if __name__ == "__main__":
    main()
