<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/monitoring/README.md:110 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: a542381d7f150105e77ffbddb823fa6fef04fb86 %
  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
  %ccm_git_commit_count: 110 %
  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: dhcp logging %
  %ccm_git_modify_date: 2025-10-25 14:11:42 %
  %ccm_git_file_last_modified: 2025-10-14 20:32:17 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/dhcp/scripts/monitoring/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 7007 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Kea DHCP Log Monitoring and Historical Tracking

## Overview

This monitoring system parses Kea DHCP log files and maintains a comprehensive historical record of all lease assignments in PostgreSQL. Unlike Kea's native lease tables (which only track current state), this provides full historical tracking.

## Components

### `parse-kea-logs.py`
Main script that:
- Parses Kea DHCP4 log files (`/var/log/kea/kea-dhcp4.log`)
- Extracts lease events (ALLOC, REUSE, OFFER)
- Stores historical data in `ttdb_dev1.dhcp_history` schema
- Tracks parsing progress (resume from last position)
- Maintains device assignment summaries

## Database Schema

### Tables

#### `dhcp_history.lease_events`
Complete historical record of all lease events.

```sql
CREATE TABLE dhcp_history.lease_events (
    event_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(20) NOT NULL,  -- ALLOC, REUSE, OFFER
    ip_address INET NOT NULL,
    mac_address MACADDR,
    client_id VARCHAR(255),
    transaction_id VARCHAR(50),
    lease_duration INTEGER,
    raw_log_line TEXT,
    processed_at TIMESTAMP DEFAULT NOW()
);
```

#### `dhcp_history.device_summary`
Per-device statistics and current state.

```sql
CREATE TABLE dhcp_history.device_summary (
    mac_address MACADDR PRIMARY KEY,
    current_ip INET,
    last_seen TIMESTAMP,
    first_seen TIMESTAMP,
    total_assignments INTEGER,
    hostnames TEXT[],
    updated_at TIMESTAMP
);
```

#### `dhcp_history.log_file_state`
Tracks parsing progress for incremental updates.

```sql
CREATE TABLE dhcp_history.log_file_state (
    log_file_path VARCHAR(500) PRIMARY KEY,
    last_position BIGINT,
    last_parsed TIMESTAMP,
    total_events_parsed BIGINT
);
```

### Views

#### `dhcp_history.recent_assignments`
Last 1000 lease assignments.

#### `dhcp_history.active_devices`
Devices seen in last 7 days with activity summary.

## Setup

### 1. Initialize Schema

```bash
cd /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring
sudo python3 parse-kea-logs.py --init-schema
```

### 2. Grant Log File Access

The script needs read access to Kea logs:

```bash
# Add user to appropriate group
sudo usermod -a -G adm mpegg-adm

# Or create specific permissions
sudo setfacl -m u:mpegg-adm:r /var/log/kea/kea-dhcp4.log
sudo setfacl -m u:mpegg-adm:r /var/log/kea/kea-dhcp4.log.*
```

### 3. Test Parse (Dry Run)

```bash
sudo python3 parse-kea-logs.py --dry-run
```

### 4. Full Parse (Initial Load)

```bash
sudo python3 parse-kea-logs.py --full-parse
```

## Usage

### Regular Incremental Parse
Parses only new log entries since last run:

```bash
sudo python3 parse-kea-logs.py
```

### Parse Specific Log Files

```bash
sudo python3 parse-kea-logs.py --log-files /var/log/kea/kea-dhcp4.log /var/log/kea/kea-dhcp4.log.1
```

### Cron Job for Automatic Updates

Add to crontab for periodic updates:

```bash
# Parse Kea logs every 5 minutes
*/5 * * * * /usr/bin/python3 /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/parse-kea-logs.py >> /var/log/dhcp-history-parser.log 2>&1
```

## Queries

### Recent Lease Assignments

```sql
SELECT 
    timestamp,
    event_type,
    ip_address,
    mac_address,
    lease_duration
FROM dhcp_history.recent_assignments
LIMIT 20;
```

### Device Assignment History

```sql
SELECT 
    timestamp,
    event_type,
    ip_address,
    lease_duration
FROM dhcp_history.lease_events
WHERE mac_address = '14:08:08:a5:14:d0'
ORDER BY timestamp DESC;
```

### IP Address History

```sql
SELECT 
    timestamp,
    mac_address,
    event_type,
    lease_duration
FROM dhcp_history.lease_events
WHERE ip_address = '192.168.1.129'
ORDER BY timestamp DESC;
```

### Active Devices Summary

```sql
SELECT * FROM dhcp_history.active_devices
ORDER BY last_seen DESC;
```

### Daily Assignment Stats

```sql
SELECT 
    DATE(timestamp) as date,
    event_type,
    COUNT(*) as events
FROM dhcp_history.lease_events
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), event_type
ORDER BY date DESC, event_type;
```

### Device Mobility (IP Changes)

```sql
SELECT 
    mac_address,
    COUNT(DISTINCT ip_address) as unique_ips,
    ARRAY_AGG(DISTINCT ip_address ORDER BY ip_address) as ips_used,
    COUNT(*) as total_assignments
FROM dhcp_history.lease_events
WHERE event_type IN ('ALLOC', 'REUSE')
GROUP BY mac_address
HAVING COUNT(DISTINCT ip_address) > 1
ORDER BY unique_ips DESC;
```

## Log Format Examples

The parser handles these Kea log formats:

```
2025-10-14 19:54:15.769 INFO [kea-dhcp4.leases/...] DHCP4_LEASE_ALLOC [hwtype=1 14:08:08:a5:14:d0], cid=[01:14:08:08:a5:14:d0], tid=0xa918cb8b: lease 192.168.1.129 has been allocated for 3600 seconds

2025-10-14 19:54:15.769 INFO [kea-dhcp4.leases/...] DHCP4_LEASE_REUSE [hwtype=1 14:08:08:a5:14:d0], cid=[01:14:08:08:a5:14:d0], tid=0xa918cb8b: lease 192.168.1.129 has been reused for 3596 seconds

2025-10-14 19:54:15.760 INFO [kea-dhcp4.leases/...] DHCP4_LEASE_OFFER [hwtype=1 14:08:08:a5:14:d0], cid=[01:14:08:08:a5:14:d0], tid=0xa918cb8b: lease 192.168.1.129 will be offered
```

## Maintenance

### View Statistics

```sql
SELECT 
    'Total Events' as metric,
    COUNT(*)::TEXT as value
FROM dhcp_history.lease_events
UNION ALL
SELECT 
    'Unique Devices',
    COUNT(*)::TEXT
FROM dhcp_history.device_summary
UNION ALL
SELECT 
    'Date Range',
    MIN(timestamp)::TEXT || ' to ' || MAX(timestamp)::TEXT
FROM dhcp_history.lease_events;
```

### Cleanup Old Data

```sql
-- Delete events older than 1 year
DELETE FROM dhcp_history.lease_events
WHERE timestamp < NOW() - INTERVAL '1 year';

-- Vacuum to reclaim space
VACUUM ANALYZE dhcp_history.lease_events;
```

### Reset Parser Position (Reparse)

```sql
-- Reset specific log file
DELETE FROM dhcp_history.log_file_state 
WHERE log_file_path = '/var/log/kea/kea-dhcp4.log';

-- Reset all
TRUNCATE dhcp_history.log_file_state;
```

## Troubleshooting

### Permission Denied on Log Files

```bash
# Check current permissions
ls -la /var/log/kea/

# Add ACL for user
sudo setfacl -R -m u:mpegg-adm:r /var/log/kea/

# Verify
getfacl /var/log/kea/kea-dhcp4.log
```

### Database Connection Errors

Update credentials in script:
```python
DB_CONFIG = {
    "host": "localhost",
    "database": "ttdb_dev1",
    "user": "kea",
    "password": "your-password"
}
```

### No Events Parsed

Check if Kea is logging at INFO level:
```bash
sudo tail -f /var/log/kea/kea-dhcp4.log
```

If no lease events appear, update Kea config:
```json
"loggers": [{
    "name": "kea-dhcp4",
    "severity": "INFO"
}]
```

## Integration with Monitoring

### Grafana Dashboard

Use PostgreSQL datasource to query `dhcp_history` views:
- Active devices count
- Assignments per hour/day
- Device activity timeline
- IP utilization history

### Alerts

Create triggers for anomalies:
```sql
-- Alert on unusual assignment rate
SELECT COUNT(*) as assignments_last_hour
FROM dhcp_history.lease_events
WHERE timestamp > NOW() - INTERVAL '1 hour'
  AND event_type = 'ALLOC';
```
