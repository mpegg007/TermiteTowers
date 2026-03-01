<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/monitoring/UNIQUENESS.md:110 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 5f7e7f34c39a1603f61803eb6e5e2f5eb7748311 %
  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
  %ccm_git_commit_count: 110 %
  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: dhcp logging %
  %ccm_git_modify_date: 2025-10-25 14:11:42 %
  %ccm_git_file_last_modified: 2025-10-14 21:00:17 %
  %ccm_git_file_name: UNIQUENESS.md %
  %ccm_git_path: infra/dhcp/scripts/monitoring/UNIQUENESS.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 6316 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# DHCP Event Uniqueness & Duplicate Prevention

## Problem Statement

When parsing DHCP logs, we need to ensure that:
1. **Log rotation doesn't create duplicates** - Same event in `kea-dhcp4.log` and `kea-dhcp4.log.1`
2. **Multiple runs don't duplicate data** - Re-parsing same file doesn't insert duplicates
3. **Multiple servers are supported** - Events from different DHCP servers are tracked separately

## Solution: Composite Unique Key

### Unique Constraint

```sql
CONSTRAINT unique_dhcp_event UNIQUE (
    dhcp_server_host, 
    timestamp, 
    mac_address, 
    ip_address, 
    event_type
)
```

### Why This Works

#### 1. **dhcp_server_host**
- Distinguishes events from different DHCP servers
- Examples: `monolith` (Kea), `ttdi3-u24-s2501` (ISC DHCP)
- Allows tracking multiple DHCP servers in one database

#### 2. **timestamp**
- Precise to milliseconds
- Kea: `2025-10-14 19:54:15.769`
- ISC DHCP: `2025-10-12T00:06:11.927455-04:00`

#### 3. **mac_address**
- Hardware address of the client device
- Format: `14:08:08:a5:14:d0`

#### 4. **ip_address**
- The IP being assigned/offered
- Format: `192.168.1.129`
- Can be NULL for DISCOVER events

#### 5. **event_type**
- Type of DHCP transaction
- Kea: `ALLOC`, `REUSE`, `OFFER`
- ISC DHCP: `DISCOVER`, `OFFER`, `REQUEST`, `ACK`, `NAK`, `RELEASE`

## Insert Behavior

### ON CONFLICT DO NOTHING

```sql
INSERT INTO dhcp_history.lease_events (...) VALUES (...)
ON CONFLICT (dhcp_server_host, timestamp, mac_address, ip_address, event_type) 
DO NOTHING
```

**What This Means:**
- First insert: Event is added to database
- Duplicate insert: Silently ignored (no error, no duplicate)
- Script reports: "Inserted X new events (Y duplicates skipped)"

## Real-World Scenarios

### Scenario 1: Log Rotation
```
kea-dhcp4.log:       2025-10-14 19:54:15.769 ... 192.168.1.129 ...
kea-dhcp4.log.1:     2025-10-14 19:54:15.769 ... 192.168.1.129 ...
```
**Result:** Only one entry in database (same timestamp + MAC + IP)

### Scenario 2: Re-parsing Same Log
```bash
# First run
sudo python3 parse-kea-logs.py --full-parse
# Result: 25,000 events inserted

# Second run (same command)
sudo python3 parse-kea-logs.py --full-parse
# Result: 0 new events, 25,000 duplicates skipped
```

### Scenario 3: Multiple DHCP Servers

**Kea on monolith:**
```
dhcp_server_host: monolith
timestamp: 2025-10-14 10:00:00
mac: 00:11:22:33:44:55
ip: 192.168.1.100
```

**ISC DHCP on ttdi3-u24-s2501:**
```
dhcp_server_host: ttdi3-u24-s2501
timestamp: 2025-10-14 10:00:00  (same time!)
mac: 00:11:22:33:44:55  (same device!)
ip: 192.168.1.100  (same IP!)
```

**Result:** Two separate entries (different dhcp_server_host)

## Edge Cases

### What if timestamp is identical?

**Unlikely but possible:**
- Two different devices getting leases at exact same millisecond
- Different MAC addresses → different rows ✅

### What if device gets same IP twice?

**Common scenario:**
```
Event 1: 2025-10-14 10:00:00 - ACK - 192.168.1.100 - aa:bb:cc:dd:ee:ff
Event 2: 2025-10-14 11:00:00 - ACK - 192.168.1.100 - aa:bb:cc:dd:ee:ff
```
**Result:** Two entries (different timestamp) ✅

### What if two servers assign same IP?

**Split-brain scenario (shouldn't happen but...):**
```
Server 1: monolith assigns 192.168.1.100 to device A
Server 2: ttdi3 assigns 192.168.1.100 to device B (conflict!)
```
**Result:** Both recorded (different dhcp_server_host and/or MAC) ✅

## NULL Handling

### DISCOVER events (no IP yet)
```
event_type: DISCOVER
ip_address: NULL
mac_address: 00:11:22:33:44:55
```

**Unique key includes NULL:**
- PostgreSQL allows NULL in unique constraints
- Same device can DISCOVER multiple times (different timestamps)

## Performance

### Index Strategy

```sql
-- Primary lookup: Recent events
CREATE INDEX idx_lease_events_timestamp ON lease_events(timestamp DESC);

-- Device history
CREATE INDEX idx_lease_events_mac ON lease_events(mac_address);

-- IP history  
CREATE INDEX idx_lease_events_ip ON lease_events(ip_address);

-- Server filtering
CREATE INDEX idx_lease_events_server ON lease_events(dhcp_server_host);

-- Unique constraint creates implicit index on composite key
```

### Duplicate Check Performance

- **ON CONFLICT** uses index-backed constraint
- Fast lookup: O(log n) with B-tree index
- No performance penalty for duplicates

## Verification Queries

### Check for Duplicates (Should Return 0)

```sql
SELECT 
    dhcp_server_host,
    timestamp,
    mac_address,
    ip_address,
    event_type,
    COUNT(*) as count
FROM dhcp_history.lease_events
GROUP BY dhcp_server_host, timestamp, mac_address, ip_address, event_type
HAVING COUNT(*) > 1;
```

### View Insert Statistics

```sql
SELECT 
    dhcp_server_host,
    dhcp_server_type,
    COUNT(*) as total_events,
    MIN(timestamp) as earliest_event,
    MAX(timestamp) as latest_event
FROM dhcp_history.lease_events
GROUP BY dhcp_server_host, dhcp_server_type
ORDER BY dhcp_server_host;
```

### Test Duplicate Prevention

```bash
# Parse once
sudo python3 parse-kea-logs.py --full-parse
# Output: Inserted 25000 new events (0 duplicates skipped)

# Parse again (same data)
sudo python3 parse-kea-logs.py --full-parse
# Output: Inserted 0 new events (25000 duplicates skipped)
```

## Migration Considerations

### If Unique Key Needs to Change

**Example: Add `client_id` to unique constraint**

```sql
-- 1. Drop old constraint
ALTER TABLE dhcp_history.lease_events 
DROP CONSTRAINT unique_dhcp_event;

-- 2. Remove duplicates if any exist with new key
DELETE FROM dhcp_history.lease_events a
WHERE event_id < (
    SELECT MAX(event_id) 
    FROM dhcp_history.lease_events b
    WHERE b.dhcp_server_host = a.dhcp_server_host
      AND b.timestamp = a.timestamp
      AND b.mac_address = a.mac_address
      AND b.ip_address = a.ip_address
      AND b.event_type = a.event_type
      AND b.client_id = a.client_id
);

-- 3. Add new constraint
ALTER TABLE dhcp_history.lease_events
ADD CONSTRAINT unique_dhcp_event 
UNIQUE (dhcp_server_host, timestamp, mac_address, ip_address, event_type, client_id);
```

## Summary

✅ **Prevents duplicates** across log rotations
✅ **Idempotent** - safe to re-run parser
✅ **Multi-server** - tracks events from different DHCP servers
✅ **Performant** - index-backed constraint
✅ **Flexible** - supports both Kea and ISC DHCP formats
