<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dns/scripts/monitoring/README.md:125 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 5fef4de31ab2b583bc4ddf9f47846be4d048ec96 %
  %ccm_git_commit_id: c1f5aa954a589e43600caffa76969fcd4a57b2f1 %
  %ccm_git_commit_count: 125 %
  %ccm_git_commit_date: 2025-12-15 10:05:29 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: monday drop %
  %ccm_git_modify_date: 2025-12-15 10:05:30 %
  %ccm_git_file_last_modified: 2025-12-02 15:57:21 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dns/scripts/monitoring/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3236 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# DNS Health Monitoring

**Location:** `/home/mpegg-adm/source/TermiteTowers/infra/dns/scripts/monitoring/`  
**Created:** 2025-12-02

## Overview

Automated health monitoring for the DNS infrastructure (Pi-hole + PowerDNS) similar to the Kea DHCP health check system.

## Components

### Health Check Script

**File:** `tt-dns-health-check-dev1.sh`

Performs comprehensive DNS health checks:

1. **Container Health**
   - `pihole-dev1` - Pi-hole DNS + ad blocking
   - `powerdns-dev1` - PowerDNS authoritative server
   - `powerdns-admin-dev1` - PowerDNS web management
   - `powerdns-db-dev1` - MySQL database for zones
   - `powerdns-admin-db-dev1` - PostgreSQL for admin

2. **Port Checks**
   - Pi-hole: 192.168.1.10:53, 192.168.4.10:53
   - PowerDNS: 192.168.1.10:3053, 192.168.4.10:3053

3. **DNS Resolution Tests**
   - External domain (google.com) via Pi-hole
   - Local domain (kea.tt.omp) via Pi-hole
   - Direct PowerDNS authoritative queries

4. **Database Health**
   - PowerDNS MySQL connectivity
   - Zone count validation

5. **Web Interface Checks**
   - Pi-hole admin interface (port 3010)
   - PowerDNS API (port 3021)

6. **Query Activity**
   - Pi-hole daily query statistics
   - Recent error log review

### Systemd Units

**Service:** `tt-dns-health-check-dev1.service`
- Type: oneshot
- User: root
- Runs the health check script

**Timer:** `tt-dns-health-check-dev1.timer`
- Runs 2 minutes after boot
- Repeats every 5 minutes
- Enabled by default

## Installation

```bash
# Copy files to system directories
sudo cp tt-dns-health-check-dev1.service /etc/systemd/system/
sudo cp tt-dns-health-check-dev1.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable --now tt-dns-health-check-dev1.timer
```

## Usage

### Manual Test

```bash
sudo /home/mpegg-adm/source/TermiteTowers/infra/dns/scripts/monitoring/tt-dns-health-check-dev1.sh
```

### Check Timer Status

```bash
systemctl status tt-dns-health-check-dev1.timer
systemctl list-timers | grep dns
```

### View Logs

```bash
# Service logs
journalctl -u tt-dns-health-check-dev1.service -f

# Health check log file
tail -f /var/log/tt-dns-health-check-dev1.log
```

## Uptime Kuma Integration

The script pushes health status to Uptime Kuma:

- **URL:** `https://kuma.termitetowers.ca/api/push`
- **Token:** Update `PUSH_TOKEN` variable in script
- **Status:** `up` (healthy) or `down` (errors detected)
- **Message:** Error/warning count summary

### Setup Uptime Kuma Monitor

1. Create new monitor in Uptime Kuma
2. Type: Push
3. Copy the push token
4. Update token in the script

## Exit Codes

- `0` - All checks passed (warnings allowed)
- `1` - Critical errors detected

## Customization

Edit the script to adjust:

- Test domains (`TEST_EXTERNAL`, `TEST_LOCAL`, `TEST_AA`)
- DNS server IPs (`PIHOLE_IP1`, `PIHOLE_IP2`)
- PowerDNS port (`POWERDNS_PORT`)
- Check intervals (edit timer unit)

## Related Documentation

- Critical Infrastructure: `/home/mpegg-adm/source/TermiteTowers/wiki/critical-infrastructure.md`
- DNS Configuration: `/home/mpegg-adm/source/TermiteTowers/infra/dns/README.md`
- Kea Health Check: `/srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh`
