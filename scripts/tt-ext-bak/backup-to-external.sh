#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/tt-ext-bak/backup-to-external.sh:121 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 33fd198d26d78dc5df39d440a83cbfdbb1c6847b %
#  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
#  %ccm_git_commit_count: 121 %
#  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-11-30 12:27:15 %
#  %ccm_git_file_last_modified: 2025-11-30 12:27:15 %
#  %ccm_git_file_name: backup-to-external.sh %
#  %ccm_git_path: scripts/tt-ext-bak/backup-to-external.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 10520 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: november changes % 
# External Disk Backup Script
# Performs incremental snapshot backups to external USB disk
# Detects backup drive by label, mounts it, runs backup, then unmounts

set -euo pipefail

# Configuration
BACKUP_SOURCE="/mnt/ai_storage"
BACKUP_LABEL="OMP-UD4TB42"  # Drive label to look for
BACKUP_MOUNT="/mnt/${BACKUP_LABEL}"
BACKUP_DEST="${BACKUP_MOUNT}/backups"
MAX_SNAPSHOTS=4
SNAPSHOT_DATE=$(date +%Y-%m-%d_%H-%M-%S)
SNAPSHOT_DIR="${BACKUP_DEST}/snapshot-${SNAPSHOT_DATE}"
LATEST_LINK="${BACKUP_DEST}/latest"

# Exclude patterns
EXCLUDE_FILE="/home/mpegg-adm/source/TermiteTowers/scripts/backup-exclude.txt"

# Log configuration - similar to OneShow.robocopy.cmd
LOG_DIR_HOST="/mnt/ai_storage/metadata/logs"
LOG_DIR_BACKUP="${BACKUP_MOUNT}/logs"
LOG_SUMMARY="${LOG_DIR_HOST}/backup-to-external.history.log"
LOG_DETAIL="${LOG_DIR_BACKUP}/backup-to-external.${SNAPSHOT_DATE}.log"

# Track if we mounted the drive (so we know to unmount it)
MOUNTED_BY_SCRIPT=0

# Create log directories
mkdir -p "$LOG_DIR_HOST"

# Logging function - writes to detail log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DETAIL"
}

# Summary logging function - writes one-liner to summary/history
log_summary() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_SUMMARY"
}

# Error handler
error_exit() {
    local exit_code="${2:-1}"
    log "ERROR: $1"
    log_summary "rc:[${exit_code}] status:[FAILED] src:[${BACKUP_SOURCE}] dst:[${SNAPSHOT_DIR}] error:[$1]"
    
    # Unmount if we mounted it
    if [ "$MOUNTED_BY_SCRIPT" -eq 1 ]; then
        log "INFO - Unmounting backup drive before exit"
        sudo umount "$BACKUP_MOUNT" 2>&1 | tee -a "$LOG_DETAIL" || true
    fi
    
    exit "$exit_code"
}

# Detect backup drive by label
log_summary "INFO - Looking for backup drive with label: $BACKUP_LABEL"
BACKUP_DEVICE=$(blkid -l -t LABEL="$BACKUP_LABEL" -o device)

if [ -z "$BACKUP_DEVICE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup drive with label '$BACKUP_LABEL' not found" | tee -a "$LOG_SUMMARY"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO - Please plug in the backup drive and try again" | tee -a "$LOG_SUMMARY"
    exit 1
fi

log_summary "INFO - Found backup drive: $BACKUP_DEVICE with label $BACKUP_LABEL"

# Check if already mounted
if mountpoint -q "$BACKUP_MOUNT"; then
    log_summary "INFO - Backup drive already mounted at $BACKUP_MOUNT"
else
    # Create mount point if needed
    sudo mkdir -p "$BACKUP_MOUNT"
    
    # Mount the drive
    log_summary "INFO - Mounting $BACKUP_DEVICE to $BACKUP_MOUNT"
    if ! sudo mount "$BACKUP_DEVICE" "$BACKUP_MOUNT"; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to mount $BACKUP_DEVICE" | tee -a "$LOG_SUMMARY"
        exit 1
    fi
    MOUNTED_BY_SCRIPT=1
    log_summary "INFO - Successfully mounted backup drive"
fi

# Create backup log directory on external disk
mkdir -p "$LOG_DIR_BACKUP"

# Initialize detail log
log "=========================================="
log "External Disk Backup - Starting"
log "=========================================="
log "INFO - Backup Source: $BACKUP_SOURCE"
log "INFO - Backup Mount: $BACKUP_MOUNT"
log "INFO - Snapshot Directory: $SNAPSHOT_DIR"
log "INFO - Detail Log: $LOG_DETAIL"
log "INFO - Summary Log: $LOG_SUMMARY"
log "INFO - Current User: $(whoami)"
log "INFO - Script: $0"

# Check available space
AVAILABLE_SPACE=$(df -BG "$BACKUP_MOUNT" | awk 'NR==2 {print $4}' | sed 's/G//')
log "INFO - Available space on backup disk: ${AVAILABLE_SPACE}GB"
if [ "$AVAILABLE_SPACE" -lt 500 ]; then
    error_exit "Insufficient space on external disk (${AVAILABLE_SPACE}GB available, need 500GB minimum)" 2
fi

log "=========================================="
log "Starting Backup Process"
log "=========================================="

# Create backup root directory
mkdir -p "$BACKUP_DEST"
log "INFO - Backup destination directory verified: $BACKUP_DEST"

# Create snapshot directory
mkdir -p "$SNAPSHOT_DIR"
log "INFO - Created snapshot directory: $SNAPSHOT_DIR"

# Perform incremental backup using rsync with hardlinks
log "=========================================="
log "Running rsync (this may take several hours)"
log "=========================================="

# Track rsync start time
RSYNC_START=$(date +%s)

# If latest link exists, use it for hardlinks
if [ -L "$LATEST_LINK" ] && [ -d "$LATEST_LINK" ]; then
    log "INFO - Using previous snapshot for hardlinks: $LATEST_LINK"
    rsync -aAXHv \
        --delete \
        --delete-excluded \
        --exclude-from="$EXCLUDE_FILE" \
        --link-dest="$LATEST_LINK" \
        "$BACKUP_SOURCE/" \
        "$SNAPSHOT_DIR/" 2>&1 | tee -a "$LOG_DETAIL"
    RSYNC_RC=$?
else
    log "INFO - No previous snapshot found, performing full backup"
    rsync -aAXHv \
        --delete \
        --delete-excluded \
        --exclude-from="$EXCLUDE_FILE" \
        "$BACKUP_SOURCE/" \
        "$SNAPSHOT_DIR/" 2>&1 | tee -a "$LOG_DETAIL"
    RSYNC_RC=$?
fi

# Track rsync end time and calculate duration
RSYNC_END=$(date +%s)
RSYNC_DURATION=$((RSYNC_END - RSYNC_START))
RSYNC_HOURS=$((RSYNC_DURATION / 3600))
RSYNC_MINUTES=$(((RSYNC_DURATION % 3600) / 60))
RSYNC_SECONDS=$((RSYNC_DURATION % 60))

log "INFO - rsync completed with exit code: $RSYNC_RC"
log "INFO - rsync duration: ${RSYNC_HOURS}h ${RSYNC_MINUTES}m ${RSYNC_SECONDS}s"

# Handle rsync exit codes (similar to robocopy)
if [ $RSYNC_RC -eq 0 ]; then
    log "INFO - rsync completed successfully - no files changed"
elif [ $RSYNC_RC -eq 23 ]; then
    log "WARNING - rsync completed with partial transfer (some files could not be transferred)"
elif [ $RSYNC_RC -eq 24 ]; then
    log "WARNING - rsync completed but some files vanished before they could be transferred"
elif [ $RSYNC_RC -gt 0 ]; then
    error_exit "rsync failed with exit code $RSYNC_RC" $RSYNC_RC
fi

# Update latest symlink
log "=========================================="
log "Updating Latest Symlink"
log "=========================================="
log "INFO - Current user: $(whoami)"
log "INFO - Backup dest ownership: $(ls -ld "$BACKUP_DEST" 2>&1)"
log "INFO - Removing old symlink: $LATEST_LINK"

if ! rm -f "$LATEST_LINK" 2>&1 | tee -a "$LOG_DETAIL"; then
    log "ERROR: Failed to remove old latest symlink"
    log "  Exit code: $?"
    log "  Permissions: $(ls -l "$BACKUP_DEST" 2>&1)"
    error_exit "Failed to remove old latest symlink" 3
fi

log "INFO - Creating symlink: $LATEST_LINK -> $SNAPSHOT_DIR"
if ! ln -s "$SNAPSHOT_DIR" "$LATEST_LINK" 2>&1 | tee -a "$LOG_DETAIL"; then
    log "ERROR: Failed to create latest symlink"
    log "  Exit code: $?"
    log "  Target: $SNAPSHOT_DIR"
    log "  Link: $LATEST_LINK"
    log "  Directory permissions: $(ls -ld "$BACKUP_DEST" 2>&1)"
    error_exit "Failed to create latest symlink - check permissions and ownership" 4
fi

log "✓ Symlink updated successfully"

# Cleanup old snapshots (keep only MAX_SNAPSHOTS)
log "=========================================="
log "Cleaning Up Old Snapshots"
log "=========================================="
log "INFO - Keeping $MAX_SNAPSHOTS most recent snapshots"
SNAPSHOT_COUNT=$(ls -d "$BACKUP_DEST"/snapshot-* 2>/dev/null | wc -l)
log "INFO - Current snapshot count: $SNAPSHOT_COUNT"
if [ "$SNAPSHOT_COUNT" -gt "$MAX_SNAPSHOTS" ]; then
    REMOVE_COUNT=$((SNAPSHOT_COUNT - MAX_SNAPSHOTS))
    log "INFO - Removing $REMOVE_COUNT old snapshot(s)"
    (cd "$BACKUP_DEST" && ls -dt snapshot-* | tail -n +$((MAX_SNAPSHOTS + 1))) | while read -r old_snapshot; do
        log "INFO - Removing old snapshot: $old_snapshot"
        rm -rf "$BACKUP_DEST/$old_snapshot"
    done
    log "✓ Cleanup completed"
else
    log "INFO - No cleanup needed (only $SNAPSHOT_COUNT snapshots exist)"
fi

# Generate backup report
log "=========================================="
log "Generating Backup Report"
log "=========================================="
SNAPSHOT_SIZE=$(du -sh "$SNAPSHOT_DIR" 2>/dev/null | cut -f1)
TOTAL_SNAPSHOTS=$(ls -d "$BACKUP_DEST"/snapshot-* 2>/dev/null | wc -l)
DISK_USED=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $3}')
DISK_TOTAL=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $2}')
DISK_PERCENT=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $5}')

log "=== Backup Summary ==="
log "Snapshot: $SNAPSHOT_DIR"
log "Snapshot Size: $SNAPSHOT_SIZE"
log "Total Snapshots: $TOTAL_SNAPSHOTS"
log "Disk Usage: $DISK_USED of $DISK_TOTAL ($DISK_PERCENT full)"
log "Rsync Duration: ${RSYNC_HOURS}h ${RSYNC_MINUTES}m ${RSYNC_SECONDS}s"
log "Rsync Exit Code: $RSYNC_RC"
log "=== Backup Complete ==="
log "=========================================="

# Write summary to history log (one-liner like robocopy)
log_summary "rc:[${RSYNC_RC}] status:[SUCCESS] src:[${BACKUP_SOURCE}] dst:[${SNAPSHOT_DIR}] size:[${SNAPSHOT_SIZE}] duration:[${RSYNC_HOURS}h${RSYNC_MINUTES}m${RSYNC_SECONDS}s] snapshots:[${TOTAL_SNAPSHOTS}]"

log "✓ Backup completed successfully"
log "Detail log saved to: $LOG_DETAIL"
log "Summary log saved to: $LOG_SUMMARY"

# Unmount the backup drive
log "=========================================="
log "Unmounting Backup Drive"
log "=========================================="

# Function to log without tee (for after unmount)
log_no_detail() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if [ "$MOUNTED_BY_SCRIPT" -eq 1 ]; then
    log "INFO - Unmounting $BACKUP_MOUNT"
    log "INFO - Closing detail log file"
    
    # Change to a safe directory (not on the backup drive)
    cd /tmp
    
    # Give filesystem time to flush buffers
    sync
    sleep 2
    
    # Try normal unmount first
    if sudo umount "$BACKUP_MOUNT" 2>&1; then
        log_no_detail "✓ Backup drive unmounted successfully"
        log_summary "INFO - Backup drive unmounted - safe to unplug"
    else
        log_no_detail "WARNING - Normal unmount failed, trying lazy unmount"
        if sudo umount -l "$BACKUP_MOUNT" 2>&1; then
            log_no_detail "✓ Backup drive unmounted (lazy) - safe to unplug after processes release"
            log_summary "INFO - Backup drive unmounted (lazy) - safe to unplug"
        else
            log_no_detail "ERROR - Failed to unmount backup drive"
            log_summary "WARNING - Failed to unmount backup drive - manually unmount before unplugging"
        fi
    fi
else
    log "INFO - Drive was already mounted, leaving it mounted"
fi

log_no_detail "=========================================="
log_no_detail "Backup process complete - drive safe to remove"
log_no_detail "=========================================="

exit 0
