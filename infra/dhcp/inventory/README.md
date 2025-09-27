<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/inventory/README.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: eec5c0447b66adcbe7264e6f6b6ce1ee2f7c3540 %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:12:09 %
  %ccm_git_file_last_modified: 2025-09-20 12:46:35 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dhcp/inventory/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 871 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Network Device Inventory

## Format
Each device entry should include:
- hostname
- mac_address
- ip_address
- device_type (server, workstation, iot, printer, etc.)
- location
- description
- dhcp_options (optional)

## Device Categories

### Servers
- Static IP assignments
- DNS entries
- Critical network services

### Workstations
- Dynamic or reserved IPs
- User-assigned devices

### IoT Devices
- Isolated VLAN assignments
- Limited network access

### Network Infrastructure
- Switches, routers, access points
- Management interfaces

## Example Entry Format

```yaml
devices:
  - hostname: server-01
    mac_address: "aa:bb:cc:dd:ee:ff"
    ip_address: "192.168.1.10"
    device_type: "server"
    location: "rack-1"
    description: "Main file server"
    dhcp_options:
      - "option domain-name-servers 192.168.1.1"
      - "option routers 192.168.1.1"
```
