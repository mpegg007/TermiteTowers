<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/README.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 2ce069073d349dba94dbf93ba6483427749310db %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:20 %
  %ccm_git_file_last_modified: 2026-03-22 09:03:20 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dhcp/scripts/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1620 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: 2025-10-10 mpegg  big update  % -->
<!-- %git_commit_history: service updates % -->
# DHCP Infrastructure Management

This directory contains all DHCP server configuration files, management scripts, and network device inventories.

## Directory Structure

### configs/
- **active/**: Currently deployed DHCP configurations
- **templates/**: Template files for generating DHCP configurations
- **backups/**: Backup copies of DHCP configurations with timestamps

### scripts/
- **deploy/**: Scripts for deploying configurations to DHCP servers
- **management/**: Scripts for managing DHCP reservations, scopes, and leases
- **monitoring/**: Scripts for monitoring DHCP server health and lease usage

### inventory/
- Network device lists, MAC addresses, IP assignments
- Device categorization (servers, workstations, IoT devices, etc.)
- Reservation management files

### logs/
- Deployment logs
- Script execution logs
- DHCP server interaction logs

### docs/
- Network topology documentation
- Configuration change procedures
- Troubleshooting guides

## Usage

1. Update device inventory in `inventory/`
2. Generate configurations using templates in `configs/templates/`
3. Test configurations locally
4. Deploy using scripts in `scripts/deploy/`
5. Monitor using scripts in `scripts/monitoring/`

## Quick Start

```bash
# Generate DHCP config from inventory
./scripts/management/generate-config.sh

# Deploy to DHCP server
./scripts/deploy/deploy-dhcp-config.sh

# Monitor lease usage
./scripts/monitoring/check-lease-usage.sh
```
