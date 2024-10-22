import subprocess
import time

def check_vpn_status():
    try:
        # Run the NordVPN status command
        result = subprocess.run(['nordvpn', 'status'], capture_output=True, text=True)
        output = result.stdout
        
        # Check if the VPN is connected
        if 'Connected' in output:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking VPN status: {e}")
        return False

def restart_vpn():
    try:
        # Disconnect and reconnect NordVPN
        subprocess.run(['nordvpn', 'disconnect'], capture_output=True, text=True)
        time.sleep(5)  # Wait for a few seconds before reconnecting
        subprocess.run(['nordvpn', 'connect'], capture_output=True, text=True)
        print("NordVPN restarted.")
    except Exception as e:
        print(f"Error restarting VPN: {e}")

def monitor_vpn(interval=60):
    while True:
        if not check_vpn_status():
            print("VPN is not active. Restarting...")
            restart_vpn()
        else:
            print("VPN is active.")
        
        # Wait for the specified interval before checking again
        time.sleep(interval)

if __name__ == "__main__":
    monitor_vpn()