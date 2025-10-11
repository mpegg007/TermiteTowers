<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/dns/README.md:97 %
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
