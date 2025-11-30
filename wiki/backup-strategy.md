<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: unknown %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 5f0d8420b44fdcbeb08d478ac8da45cda0402f41 %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: unknown %
  %ccm_git_commit_date: unknown %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-11-30 12:11:10 %
  %ccm_git_file_last_modified: 2025-11-30 12:11:10 %
  %ccm_git_file_name: backup-strategy.md %
  %ccm_git_path: wiki/backup-strategy.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 12553 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# External Disk Backup Strategy

## Overview
This document outlines the backup strategy for the TermiteTowers infrastructure using external USB disks to backup the NVMe storage pools.

## Current Storage Layout
- **Primary Storage:** NVMe disks (ai_storage, ...)
- **Backup Target:** 8TB USB disk (OMP-UD8TB61)
- **Backup Method:** Incremental snapshots using rsync

## Backup Strategy

### Recommended External Disk Configuration
- **Minimum Disks:** 3 external disks
- **Recommended:** 4 external disks
- **Rotation Schedule:** Weekly rotation
- **Connection Model:** Plug in only during backup operations

### Disk Rotation Schedule
```
Week 1: Disk A (onsite, connected for backup)
Week 2: Disk B (onsite, connected for backup) - Disk A stored offsite
Week 3: Disk C (onsite, connected for backup) - Disk B stored offsite
Week 4: Disk D (onsite, connected for backup) - Disk C stored offsite
Week 5: Disk A returns from offsite, repeat cycle
```

### Backup Retention Policy
**On Each 8TB External Disk:**
- Keep 4 weekly snapshots (1 per week, 4 weeks retention)
- Each snapshot is incremental (hardlinked unchanged files)
- Estimated space per snapshot: ~2TB (initial) + ~200GB (weekly changes)

**Why 4 snapshots?**
- Week 1: Most recent backup
- Week 2: 1 week old
- Week 3: 2 weeks old
- Week 4: 3 weeks old (oldest, deleted when week 5 snapshot is created)

This provides 4 weeks of point-in-time recovery across all disks.

### Physical Security
- **Onsite:** 1 disk connected during backup window
- **Offsite:** 2-3 disks stored at separate physical location
- **Rotation:** Weekly physical rotation to offsite location

## Automated Backup Implementation

### Backup Script Location
`/usr/local/bin/backup-to-external.sh`

### Backup Schedule
- **Frequency:** Weekly
- **Day:** Sunday at 2:00 AM
- **Duration:** ~4-6 hours (initial full backup), ~1-2 hours (incremental)
- **Method:** systemd timer or cron job

### Backup Scope
**Include:**
- `/mnt/ai_storage/` - All Docker volumes, application data
- `/home/` - User home directories
- `/etc/` - System configuration
- `/root/` - Root configuration
- `/usr/local/` - Custom scripts and binaries
- `/var/lib/docker/volumes/` - Docker named volumes (if any)

**Exclude:**
- `/mnt/ai_storage/plex/transcodes/` - Temporary transcoding files
- `/mnt/ai_storage/*/cache/` - Application cache directories
- `/mnt/ai_storage/*/logs/*.log` - Rotated log files (keep recent only)
- `*.tmp`, `*.temp` - Temporary files
- Docker image layers (rebuild from compose files)

### Disk Naming Convention
- `OMP-UD8TB61` - Disk A (current)
- `OMP-UD8TB62` - Disk B (to be acquired)
- `OMP-UD8TB63` - Disk C (to be acquired)
- `OMP-UD8TB64` - Disk D (optional, recommended)

Label format: `OMP-UD[Size]TB[Sequence Number]`

## Backup Script

### Installation
```bash
sudo mkdir -p /usr/local/bin
sudo mkdir -p /var/log/backups
sudo touch /var/log/backups/external-backup.log
```

### Script: `/usr/local/bin/backup-to-external.sh`
```bash
#!/bin/bash
# External Disk Backup Script
# Performs incremental snapshot backups to external USB disk

set -euo pipefail

# Configuration
BACKUP_SOURCE="/mnt/ai_storage"
BACKUP_MOUNT="/mnt/OMP-UD8TB61"
BACKUP_DEST="${BACKUP_MOUNT}/backups"
LOG_FILE="/var/log/backups/external-backup.log"
MAX_SNAPSHOTS=4
SNAPSHOT_DATE=$(date +%Y-%m-%d_%H-%M-%S)
SNAPSHOT_DIR="${BACKUP_DEST}/snapshot-${SNAPSHOT_DATE}"
LATEST_LINK="${BACKUP_DEST}/latest"

# Exclude patterns
EXCLUDE_FILE="/usr/local/etc/backup-exclude.txt"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if external disk is mounted
if ! mountpoint -q "$BACKUP_MOUNT"; then
    error_exit "External disk not mounted at $BACKUP_MOUNT"
fi

# Check available space
AVAILABLE_SPACE=$(df -BG "$BACKUP_MOUNT" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 500 ]; then
    error_exit "Insufficient space on external disk (${AVAILABLE_SPACE}GB available)"
fi

log "=== Starting backup to external disk ==="
log "Source: $BACKUP_SOURCE"
log "Destination: $SNAPSHOT_DIR"

# Create snapshot directory
mkdir -p "$SNAPSHOT_DIR"

# Perform incremental backup using rsync with hardlinks
log "Running rsync (this may take several hours)..."
rsync -aAXHv \
    --delete \
    --delete-excluded \
    --exclude-from="$EXCLUDE_FILE" \
    --link-dest="$LATEST_LINK" \
    "$BACKUP_SOURCE/" \
    "$SNAPSHOT_DIR/" 2>&1 | tee -a "$LOG_FILE"

# Update latest symlink
rm -f "$LATEST_LINK"
ln -s "$SNAPSHOT_DIR" "$LATEST_LINK"

log "Backup completed successfully"

# Cleanup old snapshots (keep only MAX_SNAPSHOTS)
log "Cleaning up old snapshots (keeping $MAX_SNAPSHOTS most recent)..."
cd "$BACKUP_DEST"
ls -dt snapshot-* | tail -n +$((MAX_SNAPSHOTS + 1)) | while read -r old_snapshot; do
    log "Removing old snapshot: $old_snapshot"
    rm -rf "$old_snapshot"
done

# Generate backup report
SNAPSHOT_SIZE=$(du -sh "$SNAPSHOT_DIR" | cut -f1)
TOTAL_SNAPSHOTS=$(ls -d "$BACKUP_DEST"/snapshot-* 2>/dev/null | wc -l)

log "=== Backup Summary ==="
log "Snapshot size: $SNAPSHOT_SIZE"
log "Total snapshots: $TOTAL_SNAPSHOTS"
log "Disk usage: $(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $3 " used of " $2 " (" $5 " full)"}')"
log "=== Backup complete ==="

# Optional: Send notification (if notification system configured)
# notify-send "Backup Complete" "External disk backup completed successfully"
```

### Exclude File: `/usr/local/etc/backup-exclude.txt`
```
# Temporary files
*.tmp
*.temp
*.cache
.cache/

# Plex transcoding
plex/transcodes/
plex/*/Cache/

# Application caches
*/cache/
*/Cache/
*/tmp/

# Log files (keep recent only)
*.log.[0-9]*
*.log.gz
*.log.bz2

# Docker build cache
docker/buildx/

# System runtime files
/proc/
/sys/
/dev/
/run/
/tmp/

# Large media files that can be re-obtained
# (uncomment if needed)
# *.iso
# *.mkv
# *.mp4
```

### Make Script Executable
```bash
sudo chmod +x /usr/local/bin/backup-to-external.sh
sudo mkdir -p /usr/local/etc
sudo nano /usr/local/etc/backup-exclude.txt
# (paste exclude patterns above)
```

## Automation Setup

### Option 1: Systemd Timer (Recommended)

#### Service File: `/etc/systemd/system/external-backup.service`
```ini
[Unit]
Description=External Disk Backup Service
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-to-external.sh
User=root
StandardOutput=journal
StandardError=journal
```

#### Timer File: `/etc/systemd/system/external-backup.timer`
```ini
[Unit]
Description=External Disk Backup Timer
Requires=external-backup.service

[Timer]
OnCalendar=Sun *-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### Enable Timer
```bash
sudo systemctl daemon-reload
sudo systemctl enable external-backup.timer
sudo systemctl start external-backup.timer
sudo systemctl status external-backup.timer
```

### Option 2: Cron Job
```bash
sudo crontab -e
# Add line:
0 2 * * 0 /usr/local/bin/backup-to-external.sh
```

## Manual Backup Procedure

### Before Backup
1. Connect external USB disk to server
2. Verify disk is detected: `lsblk | grep OMP-UD8TB`
3. Mount disk: `sudo mount UUID=979e622e-47ec-49e7-abd7-cff655170da3 /mnt/OMP-UD8TB61`
4. Verify mount: `df -h /mnt/OMP-UD8TB61`

### Run Backup
```bash
sudo /usr/local/bin/backup-to-external.sh
```

### After Backup
1. Check log: `tail -n 50 /var/log/backups/external-backup.log`
2. Verify snapshots: `ls -lh /mnt/OMP-UD8TB61/backups/`
3. Safely unmount: `sudo umount /mnt/OMP-UD8TB61`
4. Disconnect disk and store securely

## Restore Procedure

### Full System Restore
```bash
# Mount external disk
sudo mount UUID=979e622e-47ec-49e7-abd7-cff655170da3 /mnt/OMP-UD8TB61

# Choose snapshot to restore
ls /mnt/OMP-UD8TB61/backups/

# Restore entire dataset
sudo rsync -aAXHv \
    /mnt/OMP-UD8TB61/backups/snapshot-YYYY-MM-DD_HH-MM-SS/ \
    /mnt/ai_storage/
```

### Selective File Restore
```bash
# Mount external disk
sudo mount UUID=979e622e-47ec-49e7-abd7-cff655170da3 /mnt/OMP-UD8TB61

# Browse and copy specific files
cp -a /mnt/OMP-UD8TB61/backups/latest/path/to/file /mnt/ai_storage/path/to/file
```

## Testing & Validation

### Monthly Test Restore
- Restore a random file from the latest snapshot
- Verify file integrity and timestamps
- Document test results in `/var/log/backups/restore-tests.log`

### Quarterly Full Validation
- Mount all external disks
- Verify all snapshots are readable
- Check disk health with `smartctl`
- Test full directory restore to temporary location

## Disk Health Monitoring

### SMART Monitoring
```bash
# Install smartmontools
sudo apt install smartmontools

# Check disk health
sudo smartctl -H /dev/sda
sudo smartctl -a /dev/sda
```

### Disk Replacement Criteria
Replace external disk if:
- SMART health status is "FAILING"
- Reallocated sector count > 5
- Pending sector count > 0
- CRC errors increasing
- Disk age > 5 years

## Cost & Hardware

### Recommended Hardware
- **Disk Type:** Seagate Backup Plus 8TB USB 3.0
- **Quantity:** 3-4 disks
- **Estimated Cost:** $150-180 per disk (CAD)
- **Total Investment:** $450-720 CAD

### External Disk Enclosure (Alternative)
- Purchase bare 8TB HDDs: ~$120 each
- USB 3.0 SATA enclosure: ~$30-40
- Total per disk: ~$150-160

## Security Considerations

### Encryption (Optional)
For sensitive data, consider LUKS encryption:
```bash
# One-time setup per disk
sudo cryptsetup luksFormat /dev/sda1
sudo cryptsetup luksOpen /dev/sda1 backup-encrypted
sudo mkfs.ext4 -L "OMP-UD8TB61-ENC" /dev/mapper/backup-encrypted
```

**Note:** Adds complexity to automation; only use if data sensitivity requires it.

### Physical Security
- Store offsite disks at trusted location (family member, safety deposit box)
- Never leave all backup disks in same location as primary server
- Label disks with rotation number only (no sensitive information)

## Disaster Recovery Scenarios

### Scenario 1: Single File Corruption
- **Recovery Time:** < 5 minutes
- **Action:** Mount latest snapshot, copy file

### Scenario 2: Service Data Loss (e.g., database corruption)
- **Recovery Time:** < 30 minutes
- **Action:** Restore service directory from latest snapshot

### Scenario 3: Full NVMe Disk Failure
- **Recovery Time:** 4-8 hours (restore time)
- **Action:** Replace disk, restore from most recent backup

### Scenario 4: Complete Server Loss (fire, theft)
- **Recovery Time:** 1-2 days (new hardware + restore)
- **Action:** Provision new server, restore from offsite backup disk

## Monitoring & Alerts

### Backup Success Monitoring
Create systemd service to check backup age:
```bash
#!/bin/bash
# /usr/local/bin/check-backup-age.sh
LATEST_BACKUP=$(ls -dt /mnt/OMP-UD8TB61/backups/snapshot-* 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "CRITICAL: No backups found"
    exit 2
fi

BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 86400 ))
if [ "$BACKUP_AGE" -gt 10 ]; then
    echo "WARNING: Backup is $BACKUP_AGE days old"
    exit 1
fi

echo "OK: Backup is $BACKUP_AGE days old"
exit 0
```

### Integration with Monitoring
- Add check to existing monitoring system
- Send alert if backup > 10 days old
- Weekly reminder to rotate external disks

## Maintenance Schedule

### Weekly
- Connect next disk in rotation sequence
- Run backup (automatic or manual)
- Verify backup completion
- Safely eject disk
- Store previous disk offsite

### Monthly
- Review backup logs
- Test restore of random files
- Check disk SMART status

### Quarterly
- Full validation of all backup disks
- Test full directory restore
- Review and update exclude patterns
- Verify offsite storage security

### Annually
- Review backup strategy effectiveness
- Consider disk upgrades if capacity issues
- Replace any disks showing age/wear

## Future Enhancements

### Potential Improvements
1. **Cloud Backup Integration:** Add cloud storage as tertiary backup (encrypted)
2. **Backup Verification:** Automated checksum verification of restored files
3. **Deduplication:** Consider using `borg backup` or `restic` for better space efficiency
4. **Monitoring Dashboard:** Integrate backup status into existing monitoring (Grafana)
5. **Automated Disk Rotation:** NFC/RFID tags to track which disk is which

## References

- rsync documentation: https://rsync.samba.org/
- Backup best practices: https://www.backblaze.com/blog/the-3-2-1-backup-strategy/
- SMART monitoring: https://www.smartmontools.org/

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-11  
**Author:** mpegg-adm  
**Review Schedule:** Quarterly
