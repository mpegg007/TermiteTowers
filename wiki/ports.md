<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/ports.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 385b85971d0c7cbf3471de05e6ac46e6dccbc336 %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:45 %
  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
  %ccm_git_file_name: ports.md %
  %ccm_git_path: wiki/ports.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 8772 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: big update % -->
<!-- %git_commit_history: service updates % -->


# Ports Inventory 

This page tracks host and service ports used across TermiteTowers using a systematic range-based allocation.

## Docker Network Assignment

**Core Infrastructure Network:**
  - Network: `powerdns-dev1_powerdns-net`
  - Services: Pi-hole, PowerDNS (DNS/Admin), WebAI, and other services in the 3000-3099 range

**App Services Network:**
  - Network: `app-services-net-dev1`
  - Services: KitchenOwl, Mealie, Homarr, LLM Server API, and other Home Automation/Daily Tools in the 3300-3399 range

**Other Categories:**
  - Media, Security, Databases, Monitoring, AI, Asset Management: Use dedicated networks if needed, or default to app-services-net-dev1 if inter-app communication is required.

**Guidance:**
- When adding a new app, check its port category and attach it to the recommended network for isolation and management.

## Port Allocation Strategy

| Range | Category | Description |
|-------|----------|-------------|
| 3000-3099 | Core Infrastructure | Primary services, admin interfaces, DNS |
| 3100-3199 | Development & DevOps | Package registries, development tools |
| 3200-3299 | Content & Documentation | Wiki, documentation, CMS |
| 3300-3399 | Home Automation & Daily | Dashboard, kitchen, daily tools |
| 3400-3499 | Media & Entertainment | Plex, *arr services, torrents |
| 3500-3599 | Security & Secrets | Vault, SOPS, auth services |
| 3600-3699 | Databases & Data | DB admin tools, data management |
| 3700-3799 | Monitoring & Ops | Uptime, logs, metrics, observability |
| 3800-3899 | AI & Machine Learning | Ollama, LLM interfaces, AI tools |
| 3900-3999 | Asset & IT Management | Asset tracking, inventory, tickets |

## Current Service Allocation

| Service        | Subdomain                  | Host Port | Container Port | Category | Status |
|----------------|----------------------------|-----------|----------------|----------|--------|
| Pi-hole Admin  | pihole.termitetowers.ca    | 3010      | 80             | Core     | ✅ **NEW** |
| PowerDNS Admin | dns.termitetowers.ca       | 3020,3021 | 80,8080        | Core     | ✅ **UPDATED** |
| PowerDNS DNS   | (localhost only)           | 3053      | 53             | Core     | ✅ **NEW** |
| LobeChat       | lobe.termitetowers.ca      | 3100      | 3210           | DevOps   | ✅ Correct |
| WebAI          | webai.termitetowers.ca     | 3101      | 8080           | DevOps   | ✅ UPDATED |
| Private PyPI   | packages.termitetowers.ca  | 3110      | 3141           | DevOps   | 🔄 **TO MIGRATE** |
| PyPI Proxy     | pypi.termitetowers.ca      | 3120      | 4080           | DevOps   | 🔄 **TO MIGRATE** |
| SearXNG        | search.termitetowers.ca    | 3130      | 8080           | DevOps   | ✅ Correct |
| Wiki.js        | wiki.termitetowers.ca      | 3200      | 3000           | Content  | ✅ Correct |
| KitchenOwl     | kitchenowl.termitetowers.ca| 3300      | 8080           | Home     | ✅ app-services-net-dev1 |
| Homarr         | home.termitetowers.ca      | 3310      | 7575           | Home     | ✅ **UPDATED** |
| Mealie         | mealie.termitetowers.ca     | 3301      | 80             | Home     | ✅ app-services-net-dev1 |
| EspHome        | esphome.termitetowers.ca   | 6052      | 6052           | Home     | ✅ **HOST** |
| LLM Server API | llmapi.termitetowers.ca    | 3350      | 8000           | Home     | ✅ **NEW** |
| Vault          | vault.termitetowers.ca     | 3500      | 3000           | Security | 🔄 **TO MIGRATE** |
| SOPS           | sops.termitetowers.ca      | 3510      | 3000           | Security | 🔄 **TO MIGRATE** |
| ESO            | eso.termitetowers.ca       | 3520      | 3000           | Security | 🔄 **TO MIGRATE** |
| dbGate         | dba.termitetowers.ca       | 3600      | 3000           | Database | ✅ |
| Uptime Kuma    | kuma.termitetowers.ca      | 3700      | 3001           | Monitor  | ✅ **UPDATED** |
| Uptime Kuma    | kuma.termitetowers.ca      | 3700      | 3001           | Monitor  | ✅ |
| Dozzle         | dozzle.termitetowers.ca    | 3710      | 8080           | Monitor  | ✅ **UPDATED** |
| Prometheus     | prometheus.termitetowers.ca| 3720      | 9090           | Monitor  | ✅ **NEW** |
| Ollama API     | ollama.termitetowers.ca    | 3800      | 11434          | AI       | 🔄 **TO MIGRATE** |
| TensorFlow     | tensorflow.termitetowers.ca| 3810      | 8888           | AI       | ✅ **NEW** |
| Snipe-IT       | asset.termitetowers.ca     | 3900      | 80             | Assets   | ✅ **UPDATED** |


## Migration Progress

Track the migration of services to the new port allocation:

| Service | Old Port | New Port | Docker ✅ | Nginx ✅ | Complete |
|---------|----------|----------|-----------|----------|----------|
| PowerDNS Admin | 3304 | 3020 | ✅ | ✅ | ⚠️ Docker issue |
| Vault | 3307 | 3500 | ✅ | ✅ | ✅ |
| Private PyPI | 3141 | 3110 | ⏳ | ⏳ | ❌ |
| PyPI Proxy | 4080 | 3120 | ⏳ | ⏳ | ❌ |
| Homarr | 3303 | 3310 | ⏳ | ⏳ | ❌ |
| Vault | 3307 | 3500 | ⏳ | ⏳ | ❌ |
| SOPS | 3306 | 3510 | ⏳ | ⏳ | ❌ |
| ESO | 3305 | 3520 | ⏳ | ⏳ | ❌ |
| dbGate | 3308 | 3600 | ⏳ | ⏳ | ❌ |
| Uptime Kuma | 3301 | 3700 | ⏳ | ⏳ | ❌ |
| Dozzle | 3302 | 3710 | ⏳ | ⏳ | ❌ |
| Ollama API | 11434 | 3800 | ⏳ | ⏳ | ❌ |
| Snipe-IT | 3310 | 3900 | ⏳ | ⏳ | ❌ |

## Notes

- Port allocation follows systematic ranges for easy management and discovery
- Each category has 100 ports available for growth
- Migration should be done service by service: Docker first, then Nginx
- Test each service after migration to ensure functionality
- Update this document as migrations are completed

Updated: 2025-09-29

Additional Information: Port Allocation Rationale & Strategy
Looking at your current port allocation, I can see it's quite scattered and lacks a clear organizational scheme. Here's a better systematic approach:

🎯 Proposed Port Allocation Strategy

Current Issues:

Ports are scattered (3000, 3100, 3200, 3141, 3300-3310, 4080, 11434)
No logical grouping by service type
Hard to remember and manage
Gaps make it unclear what's available
Better Approach: Range-Based Allocation

3000-3099: Core Infrastructure & Admin
3100-3199: Development & DevOps Tools
3200-3299: Content & Documentation
3300-3399: Home Automation & IoT
3400-3499: Media & Entertainment
3500-3599: Security & Secrets Management
3600-3699: Databases & Data Tools
3700-3799: Monitoring & Observability
3800-3899: AI & Machine Learning
3900-3999: Reserved/Future Use
Proposed Port Reassignment:

Core Infrastructure (3000-3099):

3000 - WebAI (keep as-is, primary web interface)
3010 - Nginx Admin/Config UI (future)
3020 - DNS Management (PowerDNS Admin)
3030 - Network Tools (future DHCP admin)
3040 - Load Balancer Admin (future)
Development & DevOps (3100-3199):

3100 - LobeChat (keep as-is)
3110 - Package Registry (PyPI)
3120 - PyPI Proxy
3130 - Git Services (future Gitea/GitLab)
3140 - CI/CD (future Jenkins/GitHub Actions runner)
Content & Documentation (3200-3299):

3200 - Wiki.js (keep as-is)
3210 - Documentation sites (future)
3220 - Blog/CMS (future)
3230 - File sharing (future)
Home Automation & Daily Tools (3300-3399):

3300 - KitchenOwl (keep as-is)
3310 - Home Dashboard (Homarr)
3320 - Calendar/Planning tools (future)
3330 - Note-taking apps (future)
Media & Entertainment (3400-3499):

3400 - Plex/Media Server
3410 - Sonarr
3420 - Radarr
3430 - Prowlarr
3440 - qBittorrent
3450 - Lidarr
3460 - Readarr
Security & Secrets (3500-3599):

3500 - Vault (Infisical)
3510 - SOPS Interface
3520 - ESO (External Secrets Operator)
3530 - Auth/SSO services (future)
3540 - Certificate management (future)
Databases & Data (3600-3699):

3600 - dbGate (primary DB admin)
3610 - pgAdmin (PostgreSQL specific)
3620 - MySQL Workbench equivalent
3630 - Redis admin (future)
3640 - MongoDB admin (future)
Monitoring & Ops (3700-3799):

3700 - Uptime Kuma
3710 - Dozzle (container logs)
3720 - Prometheus
3730 - Grafana (future)
3740 - Log aggregation (Syslog-ng)
3750 - Performance monitoring (future)
AI & ML (3800-3899):

3800 - Ollama API (move from 11434)
3810 - Text generation UI
3820 - Stable Diffusion
3830 - ComfyUI
3840 - Model management
3850 - AI training tools
Asset Management (3900-3999):

3900 - Snipe-IT (asset tracking)
3910 - Inventory management
3920 - IT documentation
3930 - Ticketing system (future)
Benefits of This Approach:

🧠 Memorable: Easy to remember service types by range
📈 Scalable: Room for growth in each category
🔍 Discoverable: Know immediately what type of service a port hosts
🛠️ Maintainable: Easy to add new services without conflicts
📚 Self-Documenting: Port number tells you the service category

