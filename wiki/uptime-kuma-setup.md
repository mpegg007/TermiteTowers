<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/uptime-kuma-setup.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 9aa37a0cddfb25b23c3fd80cd46170bb54dfc35b %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:28:05 %
  %ccm_git_file_last_modified: 2025-11-30 12:28:05 %
  %ccm_git_file_name: uptime-kuma-setup.md %
  %ccm_git_path: wiki/uptime-kuma-setup.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4234 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# Uptime Kuma Monitoring for Kea DHCP

## Access Uptime Kuma

- **URL**: http://192.168.1.10:3700 (or http://kuma.termitetowers.ca)
- **Container**: uptime-kuma-dev1
- **Compose File**: `/home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml`

## Monitors to Add

### 1. Kea Full Health Check (Recommended)
**Monitor Type**: Script

- **Name**: `tt-kea-health-dev1`
- **Script**: 
  ```bash
  /scripts/monitoring/tt-kea-health-check-dev1.sh
  ```
  *(Scripts are mounted read-only in Uptime Kuma container at /scripts)*
- **Interval**: 5 minutes
- **Retry**: 2 times
- **Expected**: Exit code 0
- **Checks**: All services, PostgreSQL connection, DHCP/DDNS functionality, PowerDNS integration

### 2. PostgreSQL Database
**Monitor Type**: PostgreSQL

- **Name**: `Kea PostgreSQL`
- **Connection String**: `postgresql://postgres@localhost:5432/ttdb_dev1`
- **Query**: `SELECT COUNT(*) FROM kea.hosts`
- **Interval**: 5 minutes
- **Alert if**: Query fails or returns unexpected count

### 3. DHCP Port Check
**Monitor Type**: Port

- **Name**: `Kea DHCP Port 67`
- **Hostname**: `192.168.1.10`
- **Port**: `67`
- **Interval**: 2 minutes
- **Alert if**: Port not accessible

### 4. PowerDNS Check
**Monitor Type**: DNS

- **Name**: `Kea DDNS (PowerDNS)`
- **Hostname**: `kea.tt.omp`
- **Resolver Server**: `192.168.1.10:3053`
- **DNS Record Type**: `SOA`
- **Interval**: 5 minutes
- **Alert if**: DNS query fails

### 5. Kea DHCP4 Service
**Monitor Type**: Script

- **Name**: `kea-dhcp4-dev1 service`
- **Script**: `systemctl is-active kea-dhcp4-dev1.service`
- **Interval**: 3 minutes
- **Expected**: Output "active"

### 6. Kea DDNS Service
**Monitor Type**: Script

- **Name**: `kea-dhcp-ddns-dev1 service`
- **Script**: `systemctl is-active kea-dhcp-ddns-dev1.service`
- **Interval**: 3 minutes
- **Expected**: Output "active"

## Notification Setup

### Recommended Notification Rules

1. **Critical Alerts** (send immediately):
   - PostgreSQL down
   - Kea DHCP4 service stopped
   - Port 67 not accessible
   - Full health check fails

2. **Warnings** (send after 2 failures):
   - DDNS service issues
   - PowerDNS query failures

### Notification Channels to Configure

In Uptime Kuma Settings → Notifications:

1. **Email** - for critical alerts
2. **Discord/Slack** - for all alerts (if you use them)
3. **Webhook** - for automation/integration with other tools

## Auto-Recovery with Watchdog

The systemd service is configured to automatically restart on failure:

- **Service File**: `/etc/systemd/system/kea-dhcp4-dev1.service`
- **OnFailure Handler**: `tt-kea-watchdog-dev1.service`
- **Watchdog Script**: `/srv/dev1/kea/scripts/monitoring/tt-kea-watchdog-dev1.sh`

When Kea fails:
1. Systemd triggers `tt-kea-watchdog-dev1.service`
2. Watchdog checks PostgreSQL status
3. Starts PostgreSQL if needed
4. Restarts Kea services in correct order
5. Logs recovery attempt to `/var/log/tt-kea-watchdog-dev1.log`

## Log Files

Monitor these logs in Uptime Kuma (optional - use Dozzle on port 3710):

- `/var/log/kea/kea-dhcp4.log` - DHCP operations
- `/var/log/kea/kea-ddns.log` - DNS updates
- `/var/log/tt-kea-health-check-dev1.log` - Health check results
- `/var/log/tt-kea-watchdog-dev1.log` - Auto-recovery actions
- `/var/log/tt-dhcp-log-parser-dev1.log` - Log parsing to PostgreSQL

## Testing the Setup

1. **Test health check manually**:
   ```bash
   sudo /srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh
   echo $?  # Should return 0
   ```

2. **Simulate failure**:
   ```bash
   sudo systemctl stop kea-dhcp4-dev1.service
   # Wait for Uptime Kuma alert
   # Watchdog should auto-restart
   ```

3. **Check PostgreSQL dependency**:
   ```bash
   sudo systemctl restart postgresql
   # Kea should NOT fail with connection errors
   ```

## Troubleshooting

If Uptime Kuma can't run the script:

1. **Make scripts executable**:
   ```bash
   chmod +x /srv/dev1/kea/scripts/monitoring/*.sh
   ```

2. **Check script permissions**:
   ```bash
   ls -la /srv/dev1/kea/scripts/monitoring/
   ```

3. **Alternative: HTTP Endpoint** (if script execution doesn't work from container):
   - Create simple nginx endpoint serving script output
   - Use HTTP monitor type instead of Script type
