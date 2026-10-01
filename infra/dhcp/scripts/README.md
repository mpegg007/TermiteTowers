<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/dhcp/scripts/README.md:162 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 82054a7596b82c7ed459430201a60d25d67d65ff % -->
<!-- %ccm_git_commit_id: 2dd3c0f7b311b738f89cecd1f28f55e0b795b3cb % -->
<!-- %ccm_git_commit_count: 162 % -->
<!-- %ccm_git_commit_date: 2026-09-26 15:43:25 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: chore(kea): placeholder the rotated credential and retire the dead deploy scripts % -->
<!-- %ccm_git_modify_date: 2026-09-26 15:43:25 % -->
<!-- %ccm_git_file_last_modified: 2026-09-26 15:43:18 % -->
<!-- %ccm_git_file_name: README.md % -->
<!-- %ccm_git_path: infra/dhcp/scripts/README.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: us-ascii % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 3631 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-03-22 mpegg  march updates  --> 
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: 2025-10-10 mpegg  big update  % -->
<!-- %git_commit_history: service updates % -->
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

## Retired scripts (2026-09-26)

Three deploy scripts were removed as dead code - none had a runnable target:

- `deploy-kea-config.sh`, `deploy-dhcp-config.sh` - pushed configs to *remote* DHCP
  servers via ssh/scp using a server list (`configs/dhcp-servers.conf` or
  `$DHCP_SERVERS`) that no longer exists, so they cannot run. `deploy-dhcp-config.sh`
  additionally targets the ISC DHCP predecessor (`isc-dhcp-server`), replaced by Kea.
- `migrate-to-tt-naming.sh` - self-described as a one-time migration, already done.

`deploy-kea-ddns.sh` is kept: it installs the DDNS config locally (`/etc/kea`) and
restarts `kea-dhcp-ddns-dev1.service`.

Kea configs are now edited directly in `/etc/kea/tt-kea-dhcp4-dev1.conf`; the repo copy
under `configs/kea/` is a template whose DB password is `${KEA_DB_PASSWORD}`. The live
value lives only in `/etc/kea/` and is never committed.
