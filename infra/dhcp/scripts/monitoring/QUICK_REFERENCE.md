<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/monitoring/QUICK_REFERENCE.md:110 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 5e2df01a9203f3886f3cd11f0688833c4347a092 %
  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
  %ccm_git_commit_count: 110 %
  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: dhcp logging %
  %ccm_git_modify_date: 2025-10-25 14:11:42 %
  %ccm_git_file_last_modified: 2025-10-14 21:03:35 %
  %ccm_git_file_name: QUICK_REFERENCE.md %
  %ccm_git_path: infra/dhcp/scripts/monitoring/QUICK_REFERENCE.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 2902 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Quick Reference Guide

## Supported Log Sources

### 1. Kea DHCP Server (monolith)
**Source**: `/var/log/kea/kea-dhcp4.log` (live Kea logs)  
**Server**: monolith  
**Contains**: Actual DHCP lease assignments (ALLOC, REUSE, OFFER)

### 2. ISC DHCP Server (ttdi3)  
**Source**: `dhcp.syslog` (syslog grep from ttdi3-u24-s2501)  
**Server**: ttdi3-u24-s2501  
**Contains**: ISC DHCP events (DISCOVER, OFFER, REQUEST, ACK)

### 3. NOT USEFUL: dhcp.syslog.mono
**Contains**: NetworkManager DHCP **client** events (monolith getting its own IP)  
**Not useful for**: DHCP server history tracking

## Parse Kea DHCP Logs (monolith server)

```bash
cd /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring

# Dry run (test)
sudo python3 parse-kea-logs.py --dry-run --server-host monolith

# Full parse (first time)
sudo python3 parse-kea-logs.py --full-parse --server-host monolith

# Incremental parse (cron job)
sudo python3 parse-kea-logs.py --server-host monolith
```

## Parse ISC DHCP Syslog (ttdi3 server)

```bash
# Dry run
sudo python3 parse-kea-logs.py --dry-run \
    --log-type isc \
    --log-files /home/mpegg-adm/source/TermiteTowers/infra/dhcp/inventory/dhcp.syslog

# Full parse
sudo python3 parse-kea-logs.py --full-parse \
    --log-type isc \
    --log-files /home/mpegg-adm/source/TermiteTowers/infra/dhcp/inventory/dhcp.syslog
```

## Parse Both (Combined Import)

```bash
# Parse both Kea and ISC DHCP logs in one command
sudo python3 parse-kea-logs.py --full-parse \
    --server-host monolith \
    --log-files \
        /var/log/kea/kea-dhcp4.log \
        /var/log/kea/kea-dhcp4.log.1 \
        /home/mpegg-adm/source/TermiteTowers/infra/dhcp/inventory/dhcp.syslog
```

## Query Examples

### Recent DHCP Activity

```sql
SELECT * FROM dhcp_history.recent_assignments LIMIT 50;
```

### Device History

```sql
SELECT 
    timestamp,
    dhcp_server_host,
    event_type,
    ip_address,
    hostname
FROM dhcp_history.lease_events
WHERE mac_address = '14:08:08:a5:14:d0'
ORDER BY timestamp DESC;
```

### Server Comparison

```sql
SELECT 
    dhcp_server_host,
    dhcp_server_type,
    COUNT(*) as events,
    MIN(timestamp) as first_event,
    MAX(timestamp) as last_event
FROM dhcp_history.lease_events
GROUP BY dhcp_server_host, dhcp_server_type;
```

### Check for Duplicates

```sql
SELECT 
    COUNT(*) as unique_events,
    (SELECT COUNT(*) FROM dhcp_history.lease_events) as total_events
FROM (
    SELECT DISTINCT dhcp_server_host, timestamp, mac_address, ip_address, event_type
    FROM dhcp_history.lease_events
) sub;
-- Should show: unique_events = total_events
```

## Duplicate Prevention

✅ **Composite unique key:** `(dhcp_server_host, timestamp, mac_address, ip_address, event_type)`

✅ **Safe to re-run:** Duplicates are automatically skipped

✅ **Multi-server support:** Each DHCP server tracked separately

See `UNIQUENESS.md` for details.
