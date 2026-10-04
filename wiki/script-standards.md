<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/script-standards.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: e966f5c8b0195d83b46ecccdda532b8384bbe045 %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:27:22 %
  %ccm_git_file_last_modified: 2025-11-30 12:27:22 %
  %ccm_git_file_name: script-standards.md %
  %ccm_git_path: wiki/script-standards.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 6255 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# Script Standards

This document outlines the coding and logging standards for bash scripts in TermiteTowers.

## Script Structure

### Header
All scripts should include the CCM (Continuous Code Management) header for tracking and start with proper bash options:

```bash
#!/usr/bin/env bash
# [CCM Header Block]

set -euo pipefail
```

**Options explained:**
- `-e`: Exit immediately if a command exits with a non-zero status
- `-u`: Treat unset variables as an error
- `-o pipefail`: Return the exit status of the last command in a pipe that failed

## Logging Standards

### Dual Logging System

For backup and critical operations, implement a dual-logging system similar to `OneShow.robocopy.cmd`:

1. **Detail Log**: Complete verbose output stored on backup media
2. **Summary/History Log**: One-line entries stored on the host for quick review

```bash
# Log configuration
LOG_DIR_HOST="/mnt/ai_storage/metadata/logs"
LOG_DIR_BACKUP="${BACKUP_MOUNT}/logs"
LOG_SUMMARY="${LOG_DIR_HOST}/backup-to-external.history.log"
LOG_DETAIL="${LOG_DIR_BACKUP}/backup-to-external.${SNAPSHOT_DATE}.log"

# Create log directories
mkdir -p "$LOG_DIR_HOST"
mkdir -p "$LOG_DIR_BACKUP"

# Logging function - writes to detail log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DETAIL"
}

# Summary logging function - writes one-liner to summary/history
log_summary() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_SUMMARY"
}
```

**Summary log format** (one line per run):
```
[2025-11-12 14:20:45] rc:[0] status:[SUCCESS] src:[/mnt/ai_storage] dst:[/mnt/backup/snapshot-2025-11-12_14-20-45] size:[192GB] duration:[2h15m30s] snapshots:[4]
```

### Basic Logging Function
Every script that performs significant operations should include a logging function:

```bash
# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}
```

### Logging Best Practices

#### 1. Use Progress Indicators
Show users what step is being executed:

```bash
echo "[1/7] Creating data directories..."
# ... commands ...
echo "✓ Data directories created and permissions set"

echo "[2/7] Running extra setup..."
# ... commands ...
echo "✓ Extra setup completed"
```

#### 2. Use Visual Separators
Make output readable with separators:

```bash
echo "=========================================="
echo "Backup Process Starting"
echo "=========================================="
```

#### 3. Use Status Symbols
- `✓` for success
- `⚠` for warnings (non-critical issues)
- `ERROR:` for failures

#### 4. Log Diagnostic Information
When operations fail, log comprehensive diagnostic information:

```bash
log "Updating latest symlink..."
log "  Current user: $(whoami)"
log "  Backup dest ownership: $(ls -ld "$BACKUP_DEST" 2>&1)"
log "  Removing old symlink: $LATEST_LINK"

if ! rm -f "$LATEST_LINK" 2>&1 | tee -a "$LOG_FILE"; then
    log "ERROR: Failed to remove old latest symlink"
    log "  Exit code: $?"
    log "  Permissions: $(ls -l "$BACKUP_DEST" 2>&1)"
    error_exit "Failed to remove old latest symlink"
fi
```

**Key diagnostic info to log:**
- Current user running the command: `$(whoami)`
- File/directory ownership: `$(ls -ld "$PATH" 2>&1)`
- Exit codes: `$?`
- Full paths being used
- Actual error output from commands

#### 5. Capture Command Output
Use `tee` to both display and log command output:

```bash
rsync -aAXHv \
    --delete \
    "$SOURCE/" \
    "$DEST/" 2>&1 | tee -a "$LOG_FILE"
```

#### 6. Log Before Actions
Always log what you're about to do before doing it:

```bash
log "Starting Docker container..."
docker compose -f "$COMPOSE_FILE" up -d
log "✓ Container started"
```

### Error Handling Examples

#### Good Error Handling
```bash
if ! command_that_might_fail 2>&1 | tee -a "$LOG_FILE"; then
    log "ERROR: Command failed"
    log "  Exit code: $?"
    log "  Context: $VARIABLE"
    log "  Permissions: $(ls -l "$FILE" 2>&1)"
    error_exit "Descriptive error message with context"
fi
```

#### Bad Error Handling
```bash
# Too vague - doesn't help debugging
command || error_exit "Failed"

# No diagnostic info
command || error_exit "Command failed (check permissions)"
```

## Input Validation

### Check Required Files/Directories
```bash
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Config file not found: $CONFIG_FILE" >&2
    exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Source directory not found: $SOURCE_DIR" >&2
    exit 1
fi
```

### Check System State
```bash
# Check if mounted
if ! mountpoint -q "$MOUNT_POINT"; then
    error_exit "External disk not mounted at $MOUNT_POINT"
fi

# Check available space
AVAILABLE_SPACE=$(df -BG "$MOUNT_POINT" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 500 ]; then
    error_exit "Insufficient space (${AVAILABLE_SPACE}GB available, need 500GB)"
fi
```

## Output Formatting

### Summary Reports
Provide a clear summary at the end:

```bash
log "=== Backup Summary ==="
log "Snapshot size: $SNAPSHOT_SIZE"
log "Total snapshots: $TOTAL_SNAPSHOTS"
log "Disk usage: $(df -h "$BACKUP_MOUNT" | awk 'NR==2 {print $3 " used of " $2 " (" $5 " full)"}')"
log "=== Backup complete ==="
```

### Next Steps
Tell users what to do next:

```bash
echo ""
echo "Next steps:"
echo "  1. Add DNS CNAME records"
echo "  2. Update wiki/ports.md"
echo "  3. Add dashboard tiles"
echo ""
echo "Useful commands:"
echo "  docker logs -f container-name"
echo "  systemctl status service-name"
```

## Examples

### Good Script Structure
See these reference implementations:
- `scripts/backup-to-external.sh` - Comprehensive logging for backup operations
- `scripts/deploy-prometheus-tensorflow.sh` - Multi-step deployment with progress tracking
- `scripts/nginx-enable-site.sh` - Simple script with clear error messages

### Key Principles
1. **Fail fast** with `set -euo pipefail`
2. **Log everything** that matters for debugging
3. **Show progress** so users know what's happening
4. **Provide context** in error messages
5. **Give next steps** when complete

## References
- Bash Error Handling: https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html
- Logging Best Practices: https://google.github.io/styleguide/shellguide.html
