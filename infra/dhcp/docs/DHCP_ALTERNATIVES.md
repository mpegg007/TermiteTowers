<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/dhcp/docs/DHCP_ALTERNATIVES.md:97 %
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
