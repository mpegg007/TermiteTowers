#!/usr/bin/env bash
#  TermiteTowers Enhanced Secrets Pattern Scanner
#  This script checks a SINGLE file for secrets using:
#    1. Custom regex patterns (easily configurable below)
#    2. GitGuardian ggshield (if installed)
#  
#  Usage: enhanced-secrets-pattern-scanner.sh <file>
#  Exit 0 = pass, Exit 1 = fail (secret detected)

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
LOG_FILE="$REPO_ROOT/git-automation/enhanced-hooks.log"

# Require file argument
if [ $# -ne 1 ]; then
    echo "ERROR: Usage: $0 <file>" >&2
    exit 1
fi

FILE="$1"

# Skip if file doesn't exist
if [ ! -f "$FILE" ]; then
    echo "  ⚠️  File not found: $FILE" >> "$LOG_FILE"
    exit 0
fi

SCAN_FAILED=0

# ============================================================================
# CUSTOM PATTERN DEFINITIONS
# ============================================================================
# Add your custom secret patterns here
# Format: "pattern|severity|description"
declare -a PATTERNS=(
    # Kea DHCP database passwords
    '"password"\s*:\s*"[^"]+"'"|high|Hardcoded database password in Kea config"
    
    # Add more patterns here as needed
    # Example: 'API_KEY\s*=\s*["\047][^"\047]+["\047]|high|Hardcoded API key'
    # Example: 'SECRET_TOKEN\s*=\s*[a-zA-Z0-9]{32,}|critical|Hardcoded secret token'
)

# --- CUSTOM PATTERN SCANNING ---
for PATTERN_ENTRY in "${PATTERNS[@]}"; do
    IFS='|' read -r PATTERN SEVERITY DESCRIPTION <<< "$PATTERN_ENTRY"
    
    if grep -qP "$PATTERN" "$FILE" 2>/dev/null; then
        SCAN_FAILED=1
        echo "  ✘ [$SEVERITY] Custom pattern detected in: $FILE" >&2
        echo "     Pattern: $DESCRIPTION" >&2
        echo "  ✘ [$SEVERITY] Custom pattern in: $FILE - $DESCRIPTION" >> "$LOG_FILE"
        
        # Show the matching lines (masked)
        echo "     Matching line(s):" >&2
        grep -nP "$PATTERN" "$FILE" | sed 's/\(password[^:]*:\s*\)"[^"]*"/\1"***MASKED***"/gi' >&2
    fi
done

# --- GGSHIELD SCANNING ---
if command -v ggshield &> /dev/null; then
    if ! ggshield secret scan path "$FILE" 2>> "$LOG_FILE" 1>/dev/null; then
        SCAN_FAILED=1
        echo "  ✘ GitGuardian detected secret in: $FILE" >&2
        echo "  ✘ GitGuardian detected secret in: $FILE" >> "$LOG_FILE"
    fi
else
    # Only log once at the start, not per-file
    if [ ! -f "$REPO_ROOT/.ggshield-not-installed-warned" ]; then
        echo "  ⚠️  ggshield not installed - only custom patterns checked" >> "$LOG_FILE"
        echo "  Install with: pip install ggshield" >> "$LOG_FILE"
        touch "$REPO_ROOT/.ggshield-not-installed-warned"
    fi
fi

# --- RESULT ---
if [ $SCAN_FAILED -eq 1 ]; then
    echo "" >&2
    echo "❌ SECRET DETECTED in $FILE!" >&2
    echo "   Remove the secret before committing." >&2
    echo "   To bypass: add 'tt-secrets.skip' or 'tt-ggshield.skip' comment to file" >&2
    echo "" >&2
    exit 1
fi

exit 0
