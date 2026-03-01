#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-mealie.sh:130 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 586a2f714dd806087ac0f98ffec10d4f47ee1c92 %
#  %ccm_git_commit_id: 3395da0009f399bd9abd836085b72ec8a4d7f2f3 %
#  %ccm_git_commit_count: 130 %
#  %ccm_git_commit_date: 2026-02-07 15:49:15 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feb2026.1 %
#  %ccm_git_modify_date: 2026-02-07 15:49:16 %
#  %ccm_git_file_last_modified: 2026-02-07 15:49:16 %
#  %ccm_git_file_name: backup-mealie.sh %
#  %ccm_git_path: infra/backups/scripts/backup-mealie.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2338 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
set -e

# Configuration
APP_NAME="mealie"
CONTAINER_NAME="mealie-dev1"
DATA_DIR="/mnt/ai_storage/docker/mealie-data"
BACKUP_ROOT="/mnt/ai_storage/backups"
BACKUP_DIR="$BACKUP_ROOT/$APP_NAME"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/tt-backup-$APP_NAME.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting backup for $APP_NAME..."

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    CONTAINER_WAS_RUNNING=true
    log "Stopping container $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME"
else
    CONTAINER_WAS_RUNNING=false
    log "Container $CONTAINER_NAME is not running. Proceeding with backup..."
fi

# Create Backup
BACKUP_FILE="$BACKUP_DIR/${APP_NAME}_backup_$TIMESTAMP.tar.gz"
log "Creating archive $BACKUP_FILE from $DATA_DIR..."
tar -czf "$BACKUP_FILE" -C "$DATA_DIR" .

# Restart container if it was running
if [ "$CONTAINER_WAS_RUNNING" = true ]; then
    log "Starting container $CONTAINER_NAME..."
    docker start "$CONTAINER_NAME"
fi

# Verify Backup
if [ -f "$BACKUP_FILE" ]; then
    log "Backup created successfully: $BACKUP_FILE"
    
    # Jotta Integration
    # Assuming Jotta CLI is installed and configured to watch the backup root or we add it now
    if command -v jotta-cli &> /dev/null; then
        log "Jotta CLI found. Ensuring backup directory is added to backup..."
        # This command adds the folder to Jotta's backup set if not already present
        # We suppress output to avoid clutter, but log errors
        jotta-cli add "$BACKUP_DIR" || log "Warning: Failed to add $BACKUP_DIR to Jotta backup"
        
        # Trigger a scan/backup if possible (Jotta usually watches, but 'archive' is another option)
        # For 'backup' mode, it's automatic.
        log "Jotta should automatically detect and upload the new file."
    else
        log "Warning: jotta-cli not found. Cloud replication skipped."
    fi

    # Prune old backups
    log "Pruning backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "${APP_NAME}_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
else
    log "Error: Backup file was not created!"
    exit 1
fi

log "Backup process completed."
