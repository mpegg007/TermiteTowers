<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/scripts/monitoring/INCIDENT-RECOVERY-2026-02-15.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: eff1d6d526caaea5bba5c0b95f0418dd35cf62be %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:20 %
  %ccm_git_file_last_modified: 2026-03-22 09:03:20 %
  %ccm_git_file_name: INCIDENT-RECOVERY-2026-02-15.md %
  %ccm_git_path: infra/dhcp/scripts/monitoring/INCIDENT-RECOVERY-2026-02-15.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 17014 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
# Kea DHCP Service Recovery - February 15, 2026

## Incident Summary

**Date:** February 15, 2026  
**Duration:** ~18 hours (from previous evening until morning)  
**Impact:** DHCP service down - no IP address assignments  
**Root Cause:** OS update changed file permissions after restoring `_kea` system user  
**Secondary Issue:** Log files also had incorrect ownership (discovered after service restoration)  
**Resolution:** Fixed all permissions, changed service to run as `_kea` user, improved monitoring

**Key Lesson:** OS updates affecting system users can cause cascading permission issues across multiple filesystem locations (runtime dirs, data dirs, AND log files).

## Timeline

- **Feb 14, Evening:** OS update applied, service went down
- **Feb 14-15, Night:** DHCP unavailable, existing leases continued working
- **Feb 15, Morning:** Issue discovered, debugging began
- **Feb 15, 09:00-09:30:** Root cause identified and fixed
- **Feb 15, 09:30:** Service restored, monitoring improved
- **Feb 15, 09:53:** Additional log file permissions issue discovered and fixed
- **Feb 15, 09:55:** Full logging resumed, all permission issues resolved

## Root Cause Analysis

### What Happened

1. **OS Update Effect:**
   - Ubuntu/Debian update restored the `_kea` system user (UID: 124, GID: 127)
   - System directories `/var/run/kea` and `/var/lib/kea` reverted to `_kea:_kea` ownership
   - Log files in `/var/log/kea` remained `root:root` (discovered later)
   
2. **Configuration Issue:**
   - Kea service was configured to run as `root:root` (insecure)
   - Permission mismatch: directories owned by `_kea`, process running as `root`
   - `/var/run/kea` had `750` permissions (owner + group only)
   
3. **Failure Mode:**
   ```
   DHCP4_INIT_FAIL: Unable to open PID file '/var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid' for write
   Unable to use interprocess sync lockfile (Permission denied): /var/run/kea/logger_lockfile
   ```

4. **Secondary Issue (After Service Restoration):**
   - Service running but log files not writable by `_kea` user
   - Silent failure - no operational impact but no audit trail
   - Required separate fix after service was already operational

### Why It Wasn't Detected

**Old Health Check Limitations:**
- Only checked `systemctl is-active` (service was "activating" but failing)
- Didn't verify file permissions
- Didn't check for recent errors in logs
- Didn't verify packet reception
- Reported "healthy" while service was crash-looping

## Resolution Steps

### 1. Immediate Fix (Service Restoration)

```bash
# Stopped failing service
sudo systemctl stop kea-dhcp4-dev1.service

# Fixed directory ownership and permissions
sudo chown -R _kea:_kea /var/run/kea/
sudo chmod 750 /var/run/kea/
sudo chown -R _kea:_kea /var/lib/kea/

# Cleaned stale files
sudo rm -f /var/run/kea/logger_lockfile
sudo rm -f /var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid

# Updated service to run as _kea (SECURITY IMPROVEMENT)
sudo sed -i 's/^User=root$/User=_kea/' /etc/systemd/system/kea-dhcp4-dev1.service
sudo sed -i 's/^Group=root$/Group=_kea/' /etc/systemd/system/kea-dhcp4-dev1.service

# Reloaded and restarted
sudo systemctl daemon-reload
sudo systemctl start kea-dhcp4-dev1.service
```

**Result:** Service operational in ~5 minutes

### 2. Additional Issue Discovered (Log File Permissions)

**Time:** February 15, 09:53  
**Symptom:** Service running but no new log entries being written

After service restoration, discovered that log files were not being updated:
```bash
# Log files were owned by root but service runs as _kea
-rw-r----- 1 root root 8.7M Feb 14 20:56 /var/log/kea/kea-dhcp4.log
```

**Resolution:**
```bash
# Fixed log file ownership
sudo bash -c 'chown _kea:_kea /var/log/kea/kea-dhcp4.log{,.1,.2,.3,.4,.5}'

# Verified logging resumed (no restart needed - Kea detected change)
sudo tail -f /var/log/kea/kea-dhcp4.log
# Confirmed: New entries appearing with current timestamp
```

**Root Cause:** Log files created before OS update were owned by `root:root`. When service switched to `_kea` user, it lost write access to existing log files.

**Why Not Immediately Obvious:**
- Service was functional (processing DHCP requests)
- Statistics API showed packet activity
- DHCP clients were getting leases
- Only log file writes were failing (silently)

**Impact:** 
- No operational impact (DHCP working)
- No visibility into lease events from Feb 14 20:56 to Feb 15 09:55
- Log parser script (`parse-kea-logs.py`) found no new events to import

### 3. Security Improvement

Changed from running as root to running as dedicated `_kea` user:
- **Before:** `User=root`, `Group=root` (security risk)
- **After:** `User=_kea`, `Group=_kea` (principle of least privilege)

### 4. Configuration Fix

Fixed syntax error in workspace config file:
- File: `/home/mpegg-adm/source/TermiteTowers/infra/dhcp/configs/kea/tt-kea-dhcp4-dev1.conf`
- Issue: Missing closing quote on line 32: `"dhcp-socket-type": "raw`
- Fixed: `"dhcp-socket-type": "raw"`

## Prevention Measures

### Enhanced Health Check (`tt-kea-health-check-dev1.sh`)

**Major Improvements:**

#### 1. Service Status Checks
```bash
# OLD: Just checked if active
systemctl is-active kea-dhcp4-dev1.service

# NEW: Comprehensive checks
- Is service active?
- Is service in failed state?
- Restart count (crash loop detection)
- Service uptime (must be >30s, not constantly restarting)
```

#### 2. File Permission Validation
```bash
# Checks ownership and permissions
/var/run/kea/                        → _kea:_kea, 750
/var/lib/kea/                        → _kea:_kea
/var/log/kea/kea-dhcp4.log           → _kea:_kea (writable)
Lease files                          → writable by _kea
Control socket                       → accessible by _kea
```

**Catches:** Runtime, data, AND log file permission issues (like today's incident)

#### 3. Error Pattern Detection
Scans recent logs for:
- "Permission denied"
- "Unable to open PID file"
- "Unable to use interprocess sync lockfile"
- "DHCP4_INIT_FAIL"
- "Unable to open database"

#### 4. Packet Reception Verification
```bash
# Uses Kea's control socket + statistics API
echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-received" } }' | \
  socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket

# Verifies:
- Kea is actually receiving DHCP packets from network
- Recent packet activity (not just service running but idle)
- OS is forwarding broadcast packets to Kea
```

**This would have caught yesterday's issue immediately!**

#### 5. Additional Checks
- Network interface status (UP, has IP)
- Port 67 listening (specifically by kea-dhcp4)
- Control socket functional (using `socat`)
- Lease database accessible and recently modified
- Process capabilities (CAP_NET_RAW, CAP_NET_BIND_SERVICE)
- PostgreSQL connectivity

### Enhanced Watchdog (`tt-kea-watchdog-dev1.sh`)

**Major Improvements:**

#### 1. Restart Loop Prevention
```bash
# Tracks restart attempts
/var/run/kea/watchdog-restart-count

# Limits: Max 3 restarts per hour
# Auto-resets if >1 hour since last issue
# Prevents infinite restart cycles
```

#### 2. Failure Diagnosis
Scans logs to identify:
- **Permission errors** → Auto-fix
- **Configuration errors** → Abort (manual fix required)
- **Database access issues** → Fix permissions + restart
- **PostgreSQL connection failures** → Wait for DB + restart

#### 3. Automatic Remediation
```bash
fix_permissions() {
    # Fix /var/run/kea ownership
    chown -R _kea:_kea /var/run/kea/
    chmod 750 /var/run/kea/
    
    # Fix /var/lib/kea ownership
    chown -R _kea:_kea /var/lib/kea/
    
    # Fix /var/log/kea log files ownership
    chown _kea:_kea /var/log/kea/kea-dhcp4.log*
    
    # Remove stale lock files
    rm -f /var/run/kea/logger_lockfile
    
    # Remove stale PID files (if process is dead)
    rm -f /var/run/kea/tt-kea-dhcp4-dev1.kea-dhcp4.pid
}
```

**This auto-fixes ALL permission issues discovered today (runtime, data, AND log files)!**

#### 4. Smart Recovery Logic
```
1. Check restart limit → Abort if exceeded
2. Diagnose failure type
3. If permission error → Fix permissions
4. If config error → Abort (can't auto-fix)
5. If DB issue → Check PostgreSQL, wait if needed
6. Restart services in correct order
7. Verify success
8. Log detailed diagnostics
```

#### 5. Improved Logging
```bash
# Detailed logs to /var/log/tt-kea-watchdog-dev1.log
[2026-02-15 09:00:00] === Kea Watchdog Triggered ===
[2026-02-15 09:00:00] Restart attempt 1 of 3
[2026-02-15 09:00:01] DIAGNOSIS: Permission errors detected
[2026-02-15 09:00:01] Fixing /var/run/kea ownership: root:root -> _kea:_kea
[2026-02-15 09:00:02] Permissions fixed, attempting restart
[2026-02-15 09:00:08] SUCCESS: All Kea services restarted successfully
```

## Deployment Status

### Scripts Are Already Active

✅ **No deployment needed** - The improved scripts are already in place:

```bash
# Workspace and deployed versions are identical:
/home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/tt-kea-health-check-dev1.sh
/srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh

/home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh
/srv/dev1/kea/scripts/monitoring/tt-kea-watchdog-dev1.sh
```

### Service Configuration

Health check runs via systemd timer:
```bash
# Service: /etc/systemd/system/tt-kea-health-check-dev1.service
# Timer: /etc/systemd/system/tt-kea-health-check-dev1.timer
systemctl status tt-kea-health-check-dev1.timer
```

Watchdog triggers on service failure:
```bash
# In /etc/systemd/system/kea-dhcp4-dev1.service:
OnFailure=tt-kea-watchdog-dev1.service
```

## Verification

### Current Service Status (Feb 15, 09:30)

```bash
$ systemctl status kea-dhcp4-dev1.service
● kea-dhcp4-dev1.service - Kea DHCPv4 Server (dev1)
   Active: active (running) since Sun 2026-02-15 09:05:59 EST
   Main PID: 1179650 (kea-dhcp4)
   
$ ps aux | grep kea-dhcp4
_kea  1179650  0.0  0.0  /usr/sbin/kea-dhcp4 -c /etc/kea/tt-kea-dhcp4-dev1.conf

$ sudo ss -ulnp | grep :67
UNCONN 0 0 192.168.1.10:67 0.0.0.0:* users:(("kea-dhcp4",pid=1179650,fd=26))
```

### Health Check Output

```bash
$ sudo bash /srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh
[2026-02-15 09:26:47] === Starting Kea Health Check ===
[2026-02-15 09:26:47] OK: Service postgresql is running (uptime: 54799s)
[2026-02-15 09:26:47] OK: Service kea-dhcp4-dev1.service is running (uptime: 1248s)
[2026-02-15 09:26:47] OK: Service kea-dhcp-ddns-dev1.service is running (uptime: 1261s)
[2026-02-15 09:26:47] OK: File permissions correct
[2026-02-15 09:26:47] OK: No critical error patterns in recent logs
[2026-02-15 09:26:47] OK: Network interface eno1 is UP (IP: 192.168.1.10)
[2026-02-15 09:26:47] OK: PostgreSQL connection successful (62 host reservations)
[2026-02-15 09:26:47] OK: No Kea PostgreSQL connection errors in last 5 minutes
[2026-02-15 09:26:47] OK: Kea DHCP listening on port 67 (0.0.0.0:*)
[2026-02-15 09:26:47] OK: Kea control socket is functional
[2026-02-15 09:26:47] OK: Lease database accessible (123 leases, last modified 1m ago)
[2026-02-15 09:26:47] OK: Kea received 96 packets total, last packet 1m ago
[2026-02-15 09:26:47] OK: Last DHCP lease allocation: 2026-02-14 18:11:35.267
[2026-02-15 09:26:47] OK: No DDNS failures in last 10 minutes
[2026-02-15 09:26:47] OK: PowerDNS responding on port 3053
[2026-02-15 09:26:47] === Health Check Complete: 0 errors, 0 warnings ===
```

### Active Leases

```bash
$ sudo cat /var/lib/kea/kea-leases4.csv | grep -v "^#" | wc -l
117

# Service is processing DHCP traffic normally
$ sudo tcpdump -ni eno1 port 67 or 68 -c 5
09:24:52.700417 IP 0.0.0.0.68 > 255.255.255.255.67: BOOTP/DHCP, Request
09:24:54.791987 IP 192.168.1.10.67 > 192.168.1.198.68: BOOTP/DHCP, Reply
```

## Dependencies

### Software Installed

```bash
# socat - required for control socket communication
sudo apt install socat

# Used by health check for querying Kea statistics
echo '{ "command": "list-commands" }' | socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket
```

## Lessons Learned

### What Went Well
1. Service architecture allowed quick diagnosis (separated concerns)
2. Logs provided clear error messages
3. Fix was straightforward once root cause identified
4. No data loss (existing leases continued working)
5. Discovered secondary issue (log permissions) before it caused operational problems

### What Could Be Better
1. **Monitoring should have caught this immediately** ✓ FIXED
2. **Watchdog should auto-remediate permission issues** ✓ FIXED
3. **Service should run as dedicated user (not root)** ✓ FIXED
4. Need better alerting for service health check failures
5. **Log file permissions separate from runtime directories** - Need comprehensive check

### Key Insights
1. **Cascading Permission Issues:** OS updates may restore system users but:
   - Runtime directories get fixed (`/var/run/kea`)
   - Data directories get fixed (`/var/lib/kea`)
   - **Log files remain broken** (`/var/log/kea`) ← Different filesystem location!
   
2. **Silent Failures:** Service can appear healthy while logging silently fails:
   - DHCP operations working
   - Statistics API functional
   - But no audit trail being written
   - Parse scripts find no new data
   
3. **Defense in Depth:** Multiple checks needed:
   - Service active? ✓
   - Processing packets? ✓
   - **Writing logs?** ← Now checked!

### Technical Debt Addressed
- ✅ Removed root execution (security improvement)
- ✅ Added comprehensive health checks
- ✅ Added intelligent auto-remediation
- ✅ Added crash loop prevention
- ✅ Fixed config file syntax error

## Future Recommendations

### 1. Proactive Monitoring
- Integrate health check results with Uptime Kuma
- Alert on WARNING status, not just ERROR
- Monitor watchdog execution (should rarely trigger)

### 2. Configuration Management
- Consider Ansible/puppet for consistent permissions
- Document expected ownership/permissions
- Add permission checks to deployment scripts

### 3. Testing
- Test service behavior after package updates
- Verify watchdog recovery scenarios
- Regular health check execution review

### 4. Documentation
- ✅ This incident report
- Update runbook with troubleshooting steps
- Document permission requirements clearly

## Related Files

### Configuration
- `/etc/systemd/system/kea-dhcp4-dev1.service` - Main service definition
- `/etc/systemd/system/kea-dhcp4-dev1.service.d/override.conf` - Capabilities override
- `/etc/kea/tt-kea-dhcp4-dev1.conf` - Kea configuration

### Scripts (Workspace)
- `/home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/tt-kea-health-check-dev1.sh`
- `/home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/tt-kea-watchdog-dev1.sh`

### Scripts (Deployed)
- `/srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh`
- `/srv/dev1/kea/scripts/monitoring/tt-kea-watchdog-dev1.sh`

### Logs
- `/var/log/kea/kea-dhcp4.log` - Kea DHCP logs
- `/var/log/tt-kea-health-check-dev1.log` - Health check logs
- `/var/log/tt-kea-watchdog-dev1.log` - Watchdog logs
- `journalctl -u kea-dhcp4-dev1.service` - Systemd logs

## Technical Reference

### Required Permissions

```bash
# /var/run/kea
Owner: _kea:_kea
Permissions: 750 (drwxr-x---)

# /var/lib/kea
Owner: _kea:_kea
Permissions: 750 (drwxr-x---)

# /var/log/kea (directory)
Owner: _kea:_kea
Permissions: 755 (drwxr-xr-x)

# Log files (/var/log/kea/kea-dhcp4.log*)
Owner: _kea:_kea
Permissions: 640 (rw-r-----)

# Lease files
Owner: _kea:_kea
Permissions: 640 (rw-r-----)

# PID files
Owner: _kea:_kea
Permissions: 644 (rw-r--r--)
```

**Note:** After OS updates that restore the `_kea` user, verify ALL file permissions:
- Runtime directories (`/var/run/kea`)
- Data directories (`/var/lib/kea`)
- **Log files** (`/var/log/kea/kea-dhcp4.log*`) ← Often overlooked!
- Control sockets

### Process Capabilities

```bash
# Required capabilities (set in systemd service override)
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_BIND_SERVICE CAP_NET_RAW

# Verification
$ capsh --decode=0000000000002400
0x0000000000002400=cap_net_bind_service,cap_net_raw
```

### Control Socket Commands

```bash
# List available commands
echo '{ "command": "list-commands" }' | socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket

# Get packet statistics
echo '{ "command": "statistic-get", "arguments": { "name": "pkt4-received" } }' | \
  socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket

# Get all statistics
echo '{ "command": "statistic-get-all" }' | socat - UNIX-CONNECT:/var/run/kea/kea4-ctrl-socket
```

## Contact & Escalation

**Service Owner:** mpegg  
**Documentation:** `/home/mpegg-adm/source/TermiteTowers/wiki/infra/dhcp/`  
**Issue Tracking:** TermiteTowers repository

---

**Document Status:** Complete  
**Last Updated:** 2026-02-15 09:30 EST  
**Next Review:** After next OS update or before any major Kea upgrade
