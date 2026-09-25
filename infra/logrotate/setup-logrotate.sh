#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logrotate/setup-logrotate.sh:124 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: b35524480a1feabc7ed3f5f6924cf602c3c477c5 %
#  %ccm_git_commit_id: 8b4b8c60fcc3a47d5432304b72990dd91eef1e93 %
#  %ccm_git_commit_count: 124 %
#  %ccm_git_commit_date: 2025-12-12 21:43:31 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: friday checkin %
#  %ccm_git_modify_date: 2025-12-12 21:43:35 %
#  %ccm_git_file_last_modified: 2025-12-12 21:43:35 %
#  %ccm_git_file_name: setup-logrotate.sh %
#  %ccm_git_path: infra/logrotate/setup-logrotate.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1642 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: cleanup % 

# Setup script to symlink repository-maintained logrotate configs to home directory
# Run this once after cloning the repository to enable logrotate for git hooks

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")/../.." && pwd)")
LOGROTATE_CONF="$REPO_ROOT/infra/logrotate/logrotate.conf"
LOGROTATE_STATE="$HOME/.logrotate.state"
LOG_DIR="$HOME/log"

echo "=== Git Hooks Logrotate Setup ==="
echo ""

# Create log directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory: $LOG_DIR"
    mkdir -p "$LOG_DIR"
else
    echo "✓ Log directory exists: $LOG_DIR"
fi

# Create logrotate state directory if needed
if [ ! -f "$LOGROTATE_STATE" ]; then
    echo "Creating logrotate state file: $LOGROTATE_STATE"
    touch "$LOGROTATE_STATE"
else
    echo "✓ Logrotate state file exists: $LOGROTATE_STATE"
fi

# Verify logrotate config exists in repo
if [ ! -f "$LOGROTATE_CONF" ]; then
    echo "ERROR: Logrotate config not found at $LOGROTATE_CONF"
    exit 1
fi

echo "✓ Repository logrotate config found: $LOGROTATE_CONF"
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Git hooks will now use logrotate with configs maintained in:"
echo "  Main config:  $LOGROTATE_CONF"
echo "  Hook configs: $REPO_ROOT/infra/logrotate/logrotate.d/"
echo ""
echo "Logs will be stored in: $LOG_DIR"
echo "Logrotate state file:   $LOGROTATE_STATE"
echo ""
echo "To test logrotate manually:"
echo "  logrotate -v -s ~/.logrotate.state $LOGROTATE_CONF"
echo ""
echo "To force rotation (for testing):"
echo "  logrotate -f -s ~/.logrotate.state $LOGROTATE_CONF"
