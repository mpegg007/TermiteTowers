<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/critical-infrastructure.md % -->
<!-- %ccm_git_object_id: wiki/critical-infrastructure.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2025-12-15 mpegg monday drop -->
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

- `uptime-kuma-dev1` - Availability probes and alerting (port 3700). The
  authority on "is it up right now".
- `prometheus-dev1` - Metrics, rule evaluation and capacity trending
  (127.0.0.1:3720, authenticated vhost). Answers "how fast is it filling".
- `node-exporter-dev1` - Host metrics feed for Prometheus (no published port).
- `dozzle-dev1` - Docker container log viewer (port 3710)

**Impact if down:** No visibility into service health, delayed incident detection.

Specifically: with `node-exporter-dev1` down, Prometheus cannot see filesystem
capacity, so every disk alert is blind - the failure is silent, which is why
`TargetDown` and `HostDown` exist. With `prometheus-dev1` down, trends and
backup-freshness alerting stop, but Uptime Kuma still reports availability.
Runbooks: [`runbook-prometheus.md`](runbook-prometheus.md).

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
