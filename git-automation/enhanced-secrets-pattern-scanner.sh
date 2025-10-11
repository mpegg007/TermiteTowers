#!/usr/bin/env bash
#  TermiteTowers Enhanced Secrets Pattern Scanner
#  This script checks staged files for secrets using:
#    1. Custom regex patterns (easily configurable below)
#    2. GitGuardian ggshield (if installed)
#  Exit 0 = pass (continue commit), Exit 1 = fail (block commit)

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
LOG_FILE="$REPO_ROOT/git-automation/enhanced-hooks.log"

echo "Running enhanced secret scanning..." >> "$LOG_FILE"

# Check for bypass markers
BYPASS_CUSTOM=false
BYPASS_GGSHIELD=false

for file in $(git diff --cached --name-only); do
    if [ -f "$file" ]; then
        if grep -q "tt-secrets.skip" "$file"; then
            BYPASS_CUSTOM=true
            echo "  ⚠️  Custom secrets bypass marker found in $file" >> "$LOG_FILE"
        fi
        if grep -q "tt-ggshield.skip" "$file"; then
            BYPASS_GGSHIELD=true
            echo "  ⚠️  GitGuardian bypass marker found in $file" >> "$LOG_FILE"
        fi
    fi
done

SCAN_FAILED=0

# ============================================================================
# CUSTOM PATTERN SCANNING
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

if [ "$BYPASS_CUSTOM" = false ]; then
    echo "  Running custom pattern scan..." >> "$LOG_FILE"
    
    # Get list of staged files
    STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
    
    if [ -n "$STAGED_FILES" ]; then
        FOUND_SECRETS=0
        
        # Check each pattern against staged files
        for PATTERN_ENTRY in "${PATTERNS[@]}"; do
            IFS='|' read -r PATTERN SEVERITY DESCRIPTION <<< "$PATTERN_ENTRY"
            
            for FILE in $STAGED_FILES; do
                # Skip binary files
                if ! file --mime "$FILE" 2>/dev/null | grep -q "charset=.*text\|charset=us-ascii\|charset=utf-8"; then
                    continue
                fi
                
                # Check if pattern matches in the file
                if grep -qP "$PATTERN" "$FILE" 2>/dev/null; then
                    FOUND_SECRETS=1
                    echo "  ✘ [$SEVERITY] Custom pattern detected in: $FILE" >&2
                    echo "     Pattern: $DESCRIPTION" >&2
                    echo "  ✘ [$SEVERITY] Custom pattern in: $FILE - $DESCRIPTION" >> "$LOG_FILE"
                    
                    # Show the matching lines (masked)
                    echo "     Matching line(s):" >&2
                    grep -nP "$PATTERN" "$FILE" | sed 's/\(password[^:]*:\s*\)"[^"]*"/\1"***MASKED***"/gi' >&2
                fi
            done
        done
        
        if [ $FOUND_SECRETS -eq 0 ]; then
            echo "  ✓ No custom secrets detected" >> "$LOG_FILE"
        else
            echo "" >&2
            echo "  ✘ Custom secret patterns detected!" >&2
            echo "  Please remove hardcoded secrets before committing." >&2
            SCAN_FAILED=1
        fi
    else
        echo "  ✓ No staged files to scan" >> "$LOG_FILE"
    fi
else
    echo "  ⏭️  Custom secret scan bypassed due to tt-secrets.skip marker" >> "$LOG_FILE"
fi

# ============================================================================
# GITGUARDIAN GGSHIELD SCANNING
# ============================================================================
if [ "$BYPASS_GGSHIELD" = false ]; then
    if command -v ggshield &> /dev/null; then
        echo "  Running ggshield scan..." >> "$LOG_FILE"
        if ! ggshield secret scan pre-commit 2>> "$LOG_FILE"; then
            echo "" >&2
            echo "❌ SECRET DETECTED by GitGuardian!" >&2
            echo "   Review the secrets above and remove them." >&2
            SCAN_FAILED=1
        else
            echo "  ✓ No secrets detected by ggshield" >> "$LOG_FILE"
        fi
    else
        echo "  ⚠️  ggshield not installed - skipping GitGuardian scan" >> "$LOG_FILE"
        echo "  Install with: pip install ggshield" >> "$LOG_FILE"
    fi
else
    echo "  ⏭️  GitGuardian scan bypassed due to tt-ggshield.skip marker" >> "$LOG_FILE"
fi

# ============================================================================
# FINAL RESULT
# ============================================================================
if [ $SCAN_FAILED -eq 1 ]; then
    echo "" >&2
    echo "To bypass custom patterns: add 'tt-secrets.skip' comment to file" >&2
    echo "To bypass GitGuardian: add 'tt-ggshield.skip' comment to file" >&2
    echo "" >&2
    exit 1
fi

echo "  ✓ All secret scans passed" >> "$LOG_FILE"
exit 0
