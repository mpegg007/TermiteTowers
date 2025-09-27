<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dns/README.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 8ea92fd2ce69d22eb26303ab11e13aecb4edf36c %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:27:57 %
  %ccm_git_file_last_modified: 2025-09-27 11:27:57 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dns/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1648 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: service updates % -->
# DNS Infrastructure Management

This directory contains all DNS server configurations, zone files, and management scripts.

## Directory Structure

### zones/

- **forward/**: Forward DNS zone files (A, AAAA, CNAME records)
- **reverse/**: Reverse DNS zone files (PTR records)
- **templates/**: Template zone files for generating new zones

### configs/

- **bind/**: BIND DNS server configuration files
- **unbound/**: Unbound DNS resolver configuration files
- **pihole/**: Pi-hole DNS filtering configuration files

### scripts/

- **zone-management/**: Scripts for creating, updating, and validating DNS zones
- **deploy/**: Scripts for deploying DNS configurations to servers
- **monitoring/**: Scripts for monitoring DNS server health and query performance

### inventory/

- DNS server lists and configurations
- Domain and subdomain inventories
- DNS record management files

### logs/

- Zone deployment logs
- DNS query logs
- Configuration change logs

### docs/

- DNS architecture documentation
- Zone file formatting guides
- Troubleshooting procedures

## Usage

1. Create or update zone files in `zones/forward/` and `zones/reverse/`
2. Validate zone files using scripts in `scripts/zone-management/`
3. Deploy configurations using scripts in `scripts/deploy/`
4. Monitor DNS performance using scripts in `scripts/monitoring/`

## Quick Start

```bash
# Create a new DNS zone
./scripts/zone-management/create-zone.sh example.com

# Validate zone files
./scripts/zone-management/validate-zones.sh

# Deploy to DNS servers
./scripts/deploy/deploy-dns-config.sh

# Monitor DNS performance
./scripts/monitoring/check-dns-health.sh
```
