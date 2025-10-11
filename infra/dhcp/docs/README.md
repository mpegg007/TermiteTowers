<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/dhcp/docs/README.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: service updates % -->
# Technitium DHCP Automation

This directory contains scripts to automatically add DHCP reservations to your Technitium DNS server from your network device inventory.

## Quick Start

1. **Setup** (run once):
   ```bash
   cd /home/mpegg-adm/source/TermiteTowers/infra/dhcp
   ./setup.sh
   ```

2. **List devices** that will be added:
   ```bash
   ./scripts/management/manage-dhcp.sh list-devices
   ```

3. **Test run** (see what would happen without making changes):
   ```bash
   ./scripts/management/manage-dhcp.sh dry-run
   ```

4. **Add all devices** as DHCP reservations:
   ```bash
   ./scripts/management/manage-dhcp.sh add-all --skip-existing
   ```

## What It Does

The automation script:

1. **Reads your CSV file** (`inventory/network_devices-20250925.csv`)
2. **Extracts all 192.168.1.x devices** with valid MAC addresses (found **63 devices**)
3. **Connects to Technitium** via REST API
4. **Adds DHCP reservations** for each device (IP ↔ MAC binding)
5. **Uses device hostnames** when available for better identification

## Devices Found

Your CSV contains **63 devices** in the 192.168.1.x range:

- **Smart home devices**: Globe plugs, smart bulbs, switches, sensors
- **Network infrastructure**: Gateway, access points, cameras
- **Computers/servers**: monolith, homeassistant, terminus  
- **IoT devices**: ESP32 nodes, vacuum cleaner, tablets
- **Networking equipment**: Various switches and routers

## Configuration

Edit `configs/technitium.conf` to customize:

- **Server URL**: Default `http://localhost:5380`
- **Credentials**: Username/password for Technitium
- **Scope name**: DHCP scope to use (default: "LAN")
- **Filtering options**: Exclude specific IPs, validation rules

## Commands

| Command | Description |
|---------|-------------|
| `list-devices` | Show all devices from CSV |
| `dry-run` | Preview changes without making them |
| `add-all` | Add all devices as DHCP reservations |
| `add-all --skip-existing` | Add devices, skip ones already configured |
| `status` | Check if Technitium server is accessible |
| `remove-all` | Remove all reservations (dangerous!) |

## Authentication

Set password via environment variable to avoid prompts:
```bash
export TECHNITIUM_PASSWORD="your-password"
./scripts/management/manage-dhcp.sh add-all --skip-existing
```

Or it will prompt you securely when needed.

## Logging

All operations are logged to:
- `logs/technitium-reservations.log`

## Safety Features

- **Dry-run mode**: Test before making changes
- **Skip existing**: Won't overwrite existing reservations  
- **Validation**: Checks MAC address and IP format
- **Logging**: Full audit trail of changes
- **Error handling**: Continues on individual failures

## Docker Integration

Since your Technitium is running in Docker, make sure:
1. The API port (5380) is accessible
2. The container has the correct network configuration  
3. Your script can reach `http://localhost:5380` (or adjust URL)

## Troubleshooting

1. **Connection errors**: Check Technitium is running and API enabled
2. **Authentication errors**: Verify username/password
3. **Permission errors**: Ensure user has DHCP admin rights in Technitium
4. **MAC format errors**: Script validates standard MAC formats (xx:xx:xx:xx:xx:xx)

## Network Impact

Adding DHCP reservations:
- ✅ **Safe operation** - doesn't disrupt existing clients
- ✅ **No downtime** - clients continue working normally  
- ✅ **Gradual effect** - devices get reserved IPs on next DHCP renewal
- ✅ **Reversible** - can remove reservations if needed

Your network has excellent organization with clear device naming and consistent IP usage patterns!
