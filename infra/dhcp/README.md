<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/dhcp/README.md:97 %
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
