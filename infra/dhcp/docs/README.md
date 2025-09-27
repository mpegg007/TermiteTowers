<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/docs/README.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 788db23f33e033c02e1db9b82e10b06c7da474d7 %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:12:09 %
  %ccm_git_file_last_modified: 2025-09-25 18:17:39 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dhcp/docs/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3648 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
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
