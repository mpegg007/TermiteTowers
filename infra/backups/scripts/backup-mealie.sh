#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-mealie.sh:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c56747d61714f1869d265e66f0cb9588f09be801 %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:20 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:20 %
#  %ccm_git_file_name: backup-mealie.sh %
#  %ccm_git_path: infra/backups/scripts/backup-mealie.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2504 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026.1  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# Enhanced backup script for mealie application with improved error handling and logging

set -e # Exit immediately if a command exits with a non-zero status

log() {
    local type=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$type] $*" | tee -a "$LOG_FILE"
}

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
mkdir -p "$BACKUP_DIR" || { log ERROR "Failed to create backup directory $BACKUP_DIR"; exit 1; }

log INFO "Starting backup for $APP_NAME..."

# Check if container is running and stop it if necessary
if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    CONTAINER_RUNNING=true
    log INFO "Stopping container $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME" || { log ERROR "Failed to stop container $CONTAINER_NAME"; exit 1; }
fi

# Create Backup
BACKUP_FILE="$BACKUP_DIR/${APP_NAME}_backup_$TIMESTAMP.tar.gz"
log INFO "Creating archive $BACKUP_FILE from $DATA_DIR..."
tar -czf "$BACKUP_FILE" -C "$DATA_DIR" . || { log ERROR "Failed to create backup file $BACKUP_FILE"; exit 1; }

# Restart container if it was running
if [ "$CONTAINER_RUNNING" = true ]; then
    log INFO "Starting container $CONTAINER_NAME..."
    docker start "$CONTAINER_NAME" || { log WARNING "Failed to start container $CONTAINER_NAME"; }
fi

# Verify Backup
if [ -f "$BACKUP_FILE" ]; then
    log INFO "Backup created successfully: $BACKUP_FILE"
    
    # Jotta Integration
    if command -v jotta-cli &> /dev/null; then
        log INFO "Jotta CLI found. Ensuring backup directory is added to backup..."
        jolla-cli add "$BACKUP_DIR" || { log WARNING "Failed to add $BACKUP_DIR to Jotta backup"; }
    else
        log WARNING "Warning: jotta-cli not found. Cloud replication skipped."
    fi

    # Prune old backups
    log INFO "Pruning backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "${APP_NAME}_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete || { log WARNING "Failed to prune old backups"; }
    
else
    log ERROR "Error: Backup file was not created!"
    exit 1
fi

log INFO "Backup process completed."
