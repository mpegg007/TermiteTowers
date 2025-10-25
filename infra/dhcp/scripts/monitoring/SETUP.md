<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/monitoring/SETUP.md:110 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 1028cff899417c7fff33cd82481b382f9daa75cc %
  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
  %ccm_git_commit_count: 110 %
  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: dhcp logging %
  %ccm_git_modify_date: 2025-10-25 14:11:42 %
  %ccm_git_file_last_modified: 2025-10-14 20:48:41 %
  %ccm_git_file_name: SETUP.md %
  %ccm_git_path: infra/dhcp/scripts/monitoring/SETUP.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 6056 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# DHCP History Monitoring Setup Guide

## Architecture

```
Database:  ttdb_dev1
Schema:    dhcp_history (dedicated schema)
User:      dhcp_history (dedicated role, isolated from kea user)
Purpose:   Historical DHCP lease tracking (not current state)
```

## Design Principles

Following TermiteTowers database strategy:

1. **Dedicated Role**: `dhcp_history` user owns only the `dhcp_history` schema
2. **Schema Isolation**: Separate from Kea's native tables
3. **Development First**: Start in `ttdb_dev1`, promote later
4. **Future Migration**: Will move to `ttdb_arc1` (archive DB) when created

## Installation

### Step 1: Database Setup

Run the database setup script to create user, schema, and permissions:

```bash
cd /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring
./setup-dhcp-history-db.sh
```

This creates:
- PostgreSQL role: `dhcp_history`
- Schema: `dhcp_history` in `ttdb_dev1`
- Proper permissions and ownership

### Step 2: Initialize Schema

Create tables, indexes, and views:

```bash
sudo python3 parse-kea-logs.py --init-schema
```

### Step 3: Grant Log Access

The script needs to read Kea logs:

```bash
# Option A: Add user to adm group (recommended)
sudo usermod -a -G adm mpegg-adm

# Option B: Set ACLs on log files
sudo setfacl -m u:mpegg-adm:r /var/log/kea/kea-dhcp4.log
sudo setfacl -m u:mpegg-adm:r /var/log/kea/kea-dhcp4.log.*
```

### Step 4: Test Parse

Dry run to verify parsing works:

```bash
sudo python3 parse-kea-logs.py --dry-run
```

### Step 5: Initial Load

Parse all existing logs:

```bash
sudo python3 parse-kea-logs.py --full-parse
```

## Database Schema

### Ownership & Permissions

```sql
-- Schema owned by dedicated user
dhcp_history schema OWNER: dhcp_history

-- Tables
dhcp_history.lease_events        OWNER: dhcp_history
dhcp_history.device_summary      OWNER: dhcp_history  
dhcp_history.log_file_state      OWNER: dhcp_history
```

### Isolation from Kea

The `dhcp_history` schema is **completely separate** from Kea's native tables:

```
ttdb_dev1/
├── public/               (default schema)
├── kea/                  (future: Kea native tables)
│   ├── lease4           (current state only)
│   └── lease6
└── dhcp_history/        (NEW: historical tracking)
    ├── lease_events     (full history)
    ├── device_summary
    └── log_file_state
```

## Verification

### Check User & Schema

```sql
-- Verify role exists
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = 'dhcp_history';

-- Verify schema ownership
SELECT schema_name, schema_owner 
FROM information_schema.schemata 
WHERE schema_name = 'dhcp_history';

-- List tables
\dt dhcp_history.*
```

### Check Permissions

```sql
-- Schema privileges
SELECT * FROM information_schema.role_table_grants 
WHERE grantee = 'dhcp_history' AND table_schema = 'dhcp_history';

-- Table ownership
SELECT tablename, tableowner 
FROM pg_tables 
WHERE schemaname = 'dhcp_history';
```

### Test Connection

```bash
# Test as dhcp_history user
psql -h localhost -U dhcp_history -d ttdb_dev1 -c "SELECT current_user, current_schema();"

# Should show:
#  current_user | current_schema
# --------------+----------------
#  dhcp_history | dhcp_history
```

## Operational Use

### Manual Parse

```bash
# Incremental (only new entries)
sudo python3 parse-kea-logs.py

# Full reparse
sudo python3 parse-kea-logs.py --full-parse
```

### Automated Monitoring

Add to cron for continuous updates:

```bash
# Edit crontab
sudo crontab -e

# Add line (every 5 minutes):
*/5 * * * * /usr/bin/python3 /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/parse-kea-logs.py >> /var/log/dhcp-history-parser.log 2>&1
```

### Query Historical Data

```sql
-- Recent assignments
SELECT * FROM dhcp_history.recent_assignments LIMIT 20;

-- Device history
SELECT timestamp, event_type, ip_address, lease_duration
FROM dhcp_history.lease_events
WHERE mac_address = '14:08:08:a5:14:d0'
ORDER BY timestamp DESC;

-- Active devices
SELECT * FROM dhcp_history.active_devices;
```

## Migration Path

### Future: Move to Archive DB

When `ttdb_arc1` is created:

```bash
# 1. Export schema
pg_dump -h localhost -U dhcp_history -d ttdb_dev1 -n dhcp_history -F c -f dhcp_history.dump

# 2. Create user in ttdb_arc1
psql -h localhost -U postgres -d ttdb_arc1 -c "CREATE ROLE dhcp_history LOGIN PASSWORD 'termitetowers-db';"

# 3. Restore to archive DB
pg_restore -h localhost -U postgres -d ttdb_arc1 dhcp_history.dump

# 4. Update script config
# Change DB_CONFIG["database"] to "ttdb_arc1"

# 5. Verify and cutover
```

## Troubleshooting

### Permission Denied: Database

```sql
-- Grant connect if needed
GRANT CONNECT ON DATABASE ttdb_dev1 TO dhcp_history;
```

### Permission Denied: Schema

```sql
-- Verify schema ownership
ALTER SCHEMA dhcp_history OWNER TO dhcp_history;

-- Grant all on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dhcp_history TO dhcp_history;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dhcp_history TO dhcp_history;
```

### Cannot Read Logs

```bash
# Check log permissions
ls -la /var/log/kea/

# Add ACL
sudo setfacl -R -m u:mpegg-adm:r /var/log/kea/
```

### Role Does Not Exist

```bash
# Re-run setup
./setup-dhcp-history-db.sh
```

## Security Notes

1. **Dedicated User**: `dhcp_history` can only access its own schema
2. **Read-Only Logs**: Script only reads log files, never writes
3. **No Kea Impact**: Completely independent from Kea's operation
4. **Password**: Change default password in production!

## Monitoring the Monitor

Track parser health:

```sql
-- Last parse time per log file
SELECT 
    log_file_path,
    last_parsed,
    total_events_parsed,
    EXTRACT(EPOCH FROM (NOW() - last_parsed))/60 AS minutes_since_parse
FROM dhcp_history.log_file_state
ORDER BY last_parsed DESC;

-- Recent ingestion rate
SELECT 
    DATE_TRUNC('hour', processed_at) AS hour,
    COUNT(*) AS events_processed
FROM dhcp_history.lease_events
WHERE processed_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```
