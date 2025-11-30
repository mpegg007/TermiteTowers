#!/usr/bin/env bash

# Setup script to symlink repository-maintained logrotate configs to home directory
# Run this once after cloning the repository to enable logrotate for git hooks

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")/.." && pwd)")
LOGROTATE_CONF="$REPO_ROOT/git-automation/logrotate.conf"
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
echo "  Hook configs: $REPO_ROOT/git-automation/logrotate.d/"
echo ""
echo "Logs will be stored in: $LOG_DIR"
echo "Logrotate state file:   $LOGROTATE_STATE"
echo ""
echo "To test logrotate manually:"
echo "  logrotate -v -s ~/.logrotate.state $LOGROTATE_CONF"
echo ""
echo "To force rotation (for testing):"
echo "  logrotate -f -s ~/.logrotate.state $LOGROTATE_CONF"
