#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/tt-ext-bak/backup-to-external-v2.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 56f8fba19f0b5d43602c0c1264a64d4143aebdaf %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
#  %ccm_git_file_name: backup-to-external-v2.sh %
#  %ccm_git_path: scripts/tt-ext-bak/backup-to-external-v2.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 8337 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-03-22 mpegg  march updates  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  comment cleanup  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# TermiteTowers v2 External & Root Disk Backup Script
# Performs incremental snapshot backups of /mnt/ai_storage and / (monolith_root) to external USB disk
# Excludes system/runtime folders for root backup using an exclude file

set -euo pipefail

# Configuration
AI_STORAGE_SOURCE="/mnt/ai_storage"
MONOLITH_ROOT_SOURCE="/"
BACKUP_LABEL="OMP-UD4TB43"  # Drive label to look for
BACKUP_MOUNT="/mnt/${BACKUP_LABEL}"
BACKUP_DEST="${BACKUP_MOUNT}/backups"
MAX_SNAPSHOTS=8
SNAPSHOT_DATE=$(date +%Y-%m-%d_%H-%M-%S)
SNAPSHOT_DIR="${BACKUP_DEST}/snapshot-${SNAPSHOT_DATE}"
LATEST_LINK="${BACKUP_DEST}/latest"

# Exclude patterns
AI_EXCLUDE_FILE="/home/mpegg-adm/source/TermiteTowers/scripts/tt-ext-bak/backup-exclude.txt"
MONOLITH_EXCLUDE_FILE="/home/mpegg-adm/source/TermiteTowers/scripts/tt-ext-bak/backup-exclude-monolith.txt"

# Log configuration
LOG_DIR_HOST="/mnt/ai_storage/metadata/logs"
LOG_DIR_BACKUP="${BACKUP_MOUNT}/logs"
LOG_SUMMARY="${LOG_DIR_HOST}/backup-to-external.history.log"
LOG_DETAIL="${LOG_DIR_BACKUP}/backup-to-external.${SNAPSHOT_DATE}.log"

MOUNTED_BY_SCRIPT=0
mkdir -p "$LOG_DIR_HOST"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DETAIL"
}
log_summary() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_SUMMARY"
}
error_exit() {
    local exit_code="${2:-1}"
    log "ERROR: $1"
    log_summary "rc:[${exit_code}] status:[FAILED] error:[$1]"
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
    exit 1
fi
log_summary "INFO - Found backup drive: $BACKUP_DEVICE with label $BACKUP_LABEL"

if mountpoint -q "$BACKUP_MOUNT"; then
    log_summary "INFO - Backup drive already mounted at $BACKUP_MOUNT"
else
    sudo mkdir -p "$BACKUP_MOUNT"
    log_summary "INFO - Mounting $BACKUP_DEVICE to $BACKUP_MOUNT"
    if ! sudo mount "$BACKUP_DEVICE" "$BACKUP_MOUNT"; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to mount $BACKUP_DEVICE" | tee -a "$LOG_SUMMARY"
        exit 1
    fi
    MOUNTED_BY_SCRIPT=1
    log_summary "INFO - Successfully mounted backup drive"
fi
mkdir -p "$LOG_DIR_BACKUP"
log "=========================================="
log "External Disk Backup v2 - Starting"
log "=========================================="
log "INFO - AI Storage Source: $AI_STORAGE_SOURCE"
log "INFO - Monolith Root Source: $MONOLITH_ROOT_SOURCE"
log "INFO - Backup Mount: $BACKUP_MOUNT"
log "INFO - Snapshot Directory: $SNAPSHOT_DIR"
log "INFO - Detail Log: $LOG_DETAIL"
log "INFO - Summary Log: $LOG_SUMMARY"
log "INFO - Current User: $(whoami)"
log "INFO - Script: $0"

AVAILABLE_SPACE=$(df -BG "$BACKUP_MOUNT" | awk 'NR==2 {print $4}' | sed 's/G//')
log "INFO - Available space on backup disk: ${AVAILABLE_SPACE}GB"
if [ "$AVAILABLE_SPACE" -lt 500 ]; then
    error_exit "Insufficient space on external disk (${AVAILABLE_SPACE}GB available, need 500GB minimum)" 2
fi

mkdir -p "$BACKUP_DEST"
mkdir -p "$SNAPSHOT_DIR/ai_storage"
mkdir -p "$SNAPSHOT_DIR/monolith_root"

# --- AI STORAGE BACKUP ---
log "=========================================="
log "Backing up ai_storage..."
log "=========================================="
AI_LATEST_LINK="$LATEST_LINK/ai_storage"
if [ -L "$AI_LATEST_LINK" ] && [ -d "$AI_LATEST_LINK" ]; then
    log "INFO - Using previous ai_storage snapshot for hardlinks: $AI_LATEST_LINK"
    rsync -aAXHv --delete --delete-excluded --exclude-from="$AI_EXCLUDE_FILE" --link-dest="$AI_LATEST_LINK" "$AI_STORAGE_SOURCE/" "$SNAPSHOT_DIR/ai_storage/" 2>&1 | tee -a "$LOG_DETAIL"
    AI_RSYNC_RC=$?
else
    log "INFO - No previous ai_storage snapshot found, performing full backup"
    rsync -aAXHv --delete --delete-excluded --exclude-from="$AI_EXCLUDE_FILE" "$AI_STORAGE_SOURCE/" "$SNAPSHOT_DIR/ai_storage/" 2>&1 | tee -a "$LOG_DETAIL"
    AI_RSYNC_RC=$?
fi

# --- MONOLITH ROOT BACKUP ---
log "=========================================="
log "Backing up monolith_root..."
log "=========================================="
MONOLITH_LATEST_LINK="$LATEST_LINK/monolith_root"
if [ -L "$MONOLITH_LATEST_LINK" ] && [ -d "$MONOLITH_LATEST_LINK" ]; then
    log "INFO - Using previous monolith_root snapshot for hardlinks: $MONOLITH_LATEST_LINK"
    rsync -aAXHv --delete --delete-excluded --exclude-from="$MONOLITH_EXCLUDE_FILE" --link-dest="$MONOLITH_LATEST_LINK" "$MONOLITH_ROOT_SOURCE" "$SNAPSHOT_DIR/monolith_root/" 2>&1 | tee -a "$LOG_DETAIL"
    MONOLITH_RSYNC_RC=$?
else
    log "INFO - No previous monolith_root snapshot found, performing full backup"
    rsync -aAXHv --delete --delete-excluded --exclude-from="$MONOLITH_EXCLUDE_FILE" "$MONOLITH_ROOT_SOURCE" "$SNAPSHOT_DIR/monolith_root/" 2>&1 | tee -a "$LOG_DETAIL"
    MONOLITH_RSYNC_RC=$?
fi

# --- Update latest symlinks ---
log "=========================================="
log "Updating Latest Symlinks"
log "=========================================="
rm -rf "$LATEST_LINK"
mkdir -p "$LATEST_LINK"
ln -s "$SNAPSHOT_DIR/ai_storage" "$LATEST_LINK/ai_storage"
ln -s "$SNAPSHOT_DIR/monolith_root" "$LATEST_LINK/monolith_root"

# --- Cleanup old snapshots ---
log "=========================================="
log "Cleaning Up Old Snapshots"
log "=========================================="
SNAPSHOT_COUNT=$(ls -d "$BACKUP_DEST"/snapshot-* 2>/dev/null | wc -l)
if [ "$SNAPSHOT_COUNT" -gt "$MAX_SNAPSHOTS" ]; then
    REMOVE_COUNT=$((SNAPSHOT_COUNT - MAX_SNAPSHOTS))
    (cd "$BACKUP_DEST" && ls -dt snapshot-* | tail -n +$((MAX_SNAPSHOTS + 1))) | while read -r old_snapshot; do
        log "INFO - Removing old snapshot: $old_snapshot"
        rm -rf "$BACKUP_DEST/$old_snapshot"
    done
    log "✓ Cleanup completed"
else
    log "INFO - No cleanup needed (only $SNAPSHOT_COUNT snapshots exist)"
fi

# --- Report ---
log "=========================================="
log "Backup Summary"
log "=========================================="
SNAPSHOT_SIZE=$(du -sh "$SNAPSHOT_DIR" 2>/dev/null | cut -f1)
TOTAL_SNAPSHOTS=$(ls -d "$BACKUP_DEST"/snapshot-* 2>/dev/null | wc -l)
DISK_USED=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $3}')
DISK_TOTAL=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $2}')
DISK_PERCENT=$(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $5}')
log "Snapshot: $SNAPSHOT_DIR"
log "Snapshot Size: $SNAPSHOT_SIZE"
log "Total Snapshots: $TOTAL_SNAPSHOTS"
log "Disk Usage: $DISK_USED of $DISK_TOTAL ($DISK_PERCENT full)"
log "=== Backup Complete ==="

log_summary "rc:[AI:$AI_RSYNC_RC|ROOT:$MONOLITH_RSYNC_RC] status:[SUCCESS] ai_storage:[${AI_STORAGE_SOURCE}] monolith_root:[${MONOLITH_ROOT_SOURCE}] dst:[${SNAPSHOT_DIR}] size:[${SNAPSHOT_SIZE}] snapshots:[${TOTAL_SNAPSHOTS}]"

log "✓ Backup completed successfully"
log "Detail log saved to: $LOG_DETAIL"
log "Summary log saved to: $LOG_SUMMARY"

# Unmount the backup drive
if [ "$MOUNTED_BY_SCRIPT" -eq 1 ]; then
    log "INFO - Unmounting $BACKUP_MOUNT"
    cd /tmp
    sync
    sleep 2
    if sudo umount "$BACKUP_MOUNT" 2>&1; then
        echo "✓ Backup drive unmounted successfully"
        log_summary "INFO - Backup drive unmounted - safe to unplug"
    else
        echo "WARNING - Normal unmount failed, trying lazy unmount"
        if sudo umount -l "$BACKUP_MOUNT" 2>&1; then
            echo "✓ Backup drive unmounted (lazy) - safe to unplug after processes release"
            log_summary "INFO - Backup drive unmounted (lazy) - safe to unplug"
        else
            echo "ERROR - Failed to unmount backup drive"
            log_summary "WARNING - Failed to unmount backup drive - manually unmount before unplugging"
        fi
    fi
else
    log "INFO - Drive was already mounted, leaving it mounted"
fi

echo "=========================================="
echo "Backup process complete - drive safe to remove"
echo "=========================================="
exit 0
