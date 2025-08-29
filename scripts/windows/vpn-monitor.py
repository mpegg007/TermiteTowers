# % ccm_tag:  %
# % ccm_size: 4888 %
# % ccm_exec: no %
# % ccm_blob_sha: 88bf5cf64b5c7b03eaf1935995bc0b0fadf8b692 %
# % ccm_path: scripts/windows/vpn-monitor.py %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_commit_email: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_message: unknown %
# % ccm_author_email: mpegg@hotmail.com %
"""
% ccm_modify_date: 2025-08-29 15:31:33 %
% ccm_author: mpegg %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: vpn-monitor.py:43 %
% ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
% ccm_commit_count: 43 %
% ccm_file_last_modified: 2025-08-29 13:51:08 %
% ccm_file_name: vpn-monitor.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

import subprocess
import time
import requests
import logging
import os
from datetime import datetime  # Import datetime for timestamps


# Configure logging
log_file_path = r"c:\jobLogs\vpn-monitor.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Ensure the directory exists
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Function to log messages to both console and file
def log_message(message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current timestamp
    formatted_message = f"{timestamp} - {message}"  # Prepend timestamp to the message
    if level == "info":
        logging.info(formatted_message)
    elif level == "error":
        logging.error(formatted_message)
    print(formatted_message)

def check_vpn_status():
    try:
        # Run the command to check network interfaces
        result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        output = result.stdout
        
        # Initialize variables for IPv4 address and default gateway
        ipv4_address = None
        default_gateway = None
        
        # Parse the output for "Unknown adapter NordLynx"
        lines = output.splitlines()
        in_nordlynx_section = False
        skip_blank_line = False

        for line in lines:
            line = line.strip()
            if "Unknown adapter NordLynx:" in line:
                in_nordlynx_section = True
                skip_blank_line = True
            elif in_nordlynx_section:
                if "IPv4 Address" in line:
                    ipv4_address = line.split(":")[-1].strip()
                elif "Default Gateway" in line:
                    default_gateway = line.split(":")[-1].strip()
                # Exit the section when encountering an empty line
                elif line == "":
                    if not skip_blank_line:                      
                       break
                    else:
                        skip_blank_line = False
        
        # Log extracted values
        if ipv4_address and default_gateway:
            log_message(f"NordLynx IPv4 Address: {ipv4_address}")
            log_message(f"NordLynx Default Gateway: {default_gateway}")
        else:
            log_message("Failed to find NordLynx adapter details.", level="error")
        
        # Use an external service to get the public IP address
        response = requests.get('https://api.ipify.org?format=text')
        if response.status_code == 200:
            external_address = response.text
            log_message(f"External IP Address: {external_address}")
        else:
            log_message("Failed to retrieve external IP address.", level="error")

        # Check if at least one domain can be resolved
        for domain in ['api-ca.libreview.io', 'www.cibc.com']:
            nslookup_result = subprocess.run(['nslookup', domain], capture_output=True, text=True)
            if nslookup_result.returncode == 0:
                log_message(f"Successfully resolved {domain}. VPN is up.")
                return True
        
        log_message("Failed to resolve any domain. VPN might be down.", level="error")
        return False
    except Exception as e:
        log_message(f"Error checking VPN status: {e}", level="error")
        return False

def restart_vpn():
    try:
        # Disconnect and reconnect NordVPN
        subprocess.run(['C:\\Program Files\\NordVPN\\nordvpn', '--disconnect'], capture_output=True, text=True)
        time.sleep(5)  # Wait for a few seconds before reconnecting
        subprocess.run(['C:\\Program Files\\NordVPN\\nordvpn', '--connect'], capture_output=True, text=True)
        log_message("NordVPN restarted.")
    except Exception as e:
        log_message(f"Error restarting VPN: {e}", level="error")

def monitor_vpn(interval=60):
    while True:
        if not check_vpn_status():
            log_message("VPN is not active. Restarting...")
            restart_vpn()
        else:
            log_message("VPN is active.   Sleeping for the next check.")
        
        # Wait for the specified interval before checking again
        time.sleep(interval)

if __name__ == "__main__":
    monitor_vpn()
