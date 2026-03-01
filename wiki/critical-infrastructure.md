<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/critical-infrastructure.md:125 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: bc973b665b5f8e8645d43afcaf2d80bf7f3cc904 %
  %ccm_git_commit_id: c1f5aa954a589e43600caffa76969fcd4a57b2f1 %
  %ccm_git_commit_count: 125 %
  %ccm_git_commit_date: 2025-12-15 10:05:29 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: monday drop %
  %ccm_git_modify_date: 2025-12-15 10:05:35 %
  %ccm_git_file_last_modified: 2025-12-02 15:37:49 %
  %ccm_git_file_name: critical-infrastructure.md %
  %ccm_git_path: wiki/critical-infrastructure.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3096 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Critical Infrastructure Services

**Last Updated:** 2025-12-02  
**System:** monolith

This document identifies the core services required for basic network operation. If these services fail, the entire network may be impacted.

## Network Infrastructure (Critical)

### DHCP Stack

**Purpose:** Assigns IP addresses to all network devices

- `kea-dhcp4-dev1.service` - Kea DHCPv4 Server (listens on port 67, IP 192.168.1.10)
- `kea-dhcp-ddns-dev1.service` - Kea DHCP-DDNS Server (dynamic DNS updates)
- `kea-ctrl-agent.service` - Kea Control Agent (management interface)
- `postgresql@16-main.service` - PostgreSQL database (stores 62+ host reservations)

**Impact if down:** No new DHCP leases, devices cannot get IP addresses, network connectivity fails for new connections

**Monitoring:**

- Health check: `tt-kea-health-check-dev1.service` (timer-based)
- Auto-recovery: `tt-kea-watchdog-dev1.service` (restarts on failure)

### DNS Stack

**Purpose:** Resolves domain names, provides ad blocking

- `pihole-dev1` - Pi-hole DNS + ad blocking (port 53 on 192.168.1.10 & 192.168.4.10)
- `powerdns-dev1` - PowerDNS Authoritative Server (port 3053)
- `powerdns-admin-dev1` - PowerDNS web management interface (port 3020)
- `powerdns-db-dev1` - MySQL database for PowerDNS zones
- `powerdns-admin-db-dev1` - PostgreSQL database for PowerDNS Admin

**Impact if down:** DNS resolution fails, devices cannot reach internet or local services by name

### Web Infrastructure

**Purpose:** Reverse proxy for all web services

- `nginx.service` - Nginx web server and reverse proxy

**Impact if down:** Web interfaces for all services become inaccessible

## Monitoring Stack (High Priority)

**Purpose:** Service health monitoring, alerting, and troubleshooting

- `uptime-kuma-dev1` - Uptime monitoring and alerting (port 3700)
- `prometheus-dev1` - Metrics collection and time-series database (port 3720)
- `dozzle-dev1` - Docker container log viewer (port 3710)

**Impact if down:** No visibility into service health, delayed incident detection

## Service Dependencies

```text
Network Devices
    ↓
DHCP (kea-dhcp4-dev1)
    ↓
PostgreSQL (host)
    ↓
DNS (pihole-dev1 + powerdns-dev1)
    ↓
Web Services (nginx)
    ↓
Monitoring (uptime-kuma, prometheus)
```

## Recovery Priority

1. **PostgreSQL** - Required by DHCP
2. **Kea DHCP services** - Network connectivity depends on this
3. **DNS services** - Required for name resolution
4. **Nginx** - Required for web interface access
5. **Monitoring services** - Required for visibility

## Startup Order

Services have systemd dependencies configured:

- Kea services wait for `postgresql.service` and `network.target`
- Docker containers have restart policies configured
- Watchdog services auto-recover failed Kea instances

## Related Documentation

- DHCP configuration: `/home/mpegg-adm/source/TermiteTowers/infra/dhcp/`
- Kea monitoring scripts: `/srv/dev1/kea/scripts/monitoring/`
- Docker compose files: `/home/mpegg-adm/source/TermiteTowers/infra/docker/`
- Nginx configs: `/home/mpegg-adm/source/TermiteTowers/infra/nginx/`
