<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/docs/DHCP_ALTERNATIVES.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 257a0e679bb49274d17c0d28a1c5a08e5b3361dc %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:12:09 %
  %ccm_git_file_last_modified: 2025-09-25 19:47:24 %
  %ccm_git_file_name: DHCP_ALTERNATIVES.md %
  %ccm_git_path: infra/dhcp/docs/DHCP_ALTERNATIVES.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 2666 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# DHCP Server Solutions with Reliable APIs

## Current Issue: Technitium API Broken
- ✅ Web interface works
- ❌ API returns success but doesn't persist data
- ❌ Binary configuration files - not directly editable
- ❌ No reliable automation path

## Alternative DHCP Solutions

### 1. **ISC DHCP + Kea DHCP (Recommended)**
- **API**: Full REST API for all operations
- **Web Interface**: Stork management interface
- **Automation**: Python/curl friendly JSON APIs
- **Enterprise**: Production-ready, widely used
- **Docker**: Official containers available

**Migration Path:**
```yaml
# docker-compose.yml
services:
  kea-dhcp:
    image: jonasal/kea-dhcp4:latest
    network_mode: host
    volumes:
      - ./kea-config:/etc/kea
    environment:
      - KEA_DHCP4_CONFIG=/etc/kea/kea-dhcp4.conf
```

### 2. **OpenWrt/pfSense DHCP**
- **API**: Full REST/XML-RPC API
- **Web Interface**: Complete web management
- **Automation**: Well-documented APIs
- **Features**: Advanced DHCP with reservations, scopes, etc.

### 3. **Windows DHCP Server**
- **API**: PowerShell cmdlets + WMI
- **Web Interface**: RSAT management tools
- **Automation**: Full PowerShell automation
- **Docker**: Can run in Windows containers

### 4. **dnsmasq with Custom Management**
- **Config**: Plain text files
- **API**: Build custom REST wrapper
- **Web Interface**: Custom or existing solutions
- **Automation**: Direct file editing + SIGHUP reload

## Immediate Solution Options

### Option A: Switch to Kea DHCP (Best Long-term)
- **Time**: 2-3 hours migration
- **Benefit**: Proper REST API, reliable automation
- **Risk**: Configuration migration needed

### Option B: Build Technitium File Parser (Hacky but Fast)
- **Time**: 1-2 hours
- **Benefit**: Keep existing setup
- **Risk**: Reverse engineering binary format

### Option C: Web Automation (Selenium/Playwright)
- **Time**: 2-4 hours
- **Benefit**: Works with current setup
- **Risk**: Fragile, breaks with UI changes

## Recommended: Kea DHCP Migration

Kea has a **proper REST API** that actually works:

```bash
# Add reservation via API
curl -X POST http://localhost:8080/dhcp4/reservation-add \
  -H "Content-Type: application/json" \
  -d '{
    "command": "reservation-add",
    "arguments": {
      "subnet-id": 1,
      "hw-address": "aa:bb:cc:dd:ee:ff",
      "ip-address": "192.168.1.100",
      "hostname": "device-name"
    }
  }'
```

**This actually persists and works reliably.**

Would you prefer:
1. **Migrate to Kea DHCP** (proper solution)
2. **Build web automation** for Technitium (keep current)
3. **Research Technitium binary format** (reverse engineering)

Which approach do you want to pursue?
