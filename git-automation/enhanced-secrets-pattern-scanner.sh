#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d16a3c4c5ea4d5689f22d0da3eb723b46e094698 %
#  %ccm_git_commit_id: 9a5d759366246b925a62863adec0b1df8cc2d5b1 %
#  %ccm_git_commit_count: 127 %
#  %ccm_git_commit_date: 2025-12-18 21:32:12 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-12-20 17:38:18 %
#  %ccm_git_file_last_modified: 2025-10-12 10:25:12 %
#  %ccm_git_file_name: enhanced-secrets-pattern-scanner.sh %
#  %ccm_git_path: git-automation/enhanced-secrets-pattern-scanner.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4261 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: #  %ccm_git_commit_message: unknown % 
# %git_commit_history: #  %ccm_git_commit_message: testing hooks again % 
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
    # Kea DHCP database passwords (JSON format)
    '"password"\s*:\s*"[^"]+"'"|high|Hardcoded database password in Kea config (JSON)"
    
    # Kea DHCP database passwords (key=value format)
    'password\s*=\s*[^\s;,#]+|high|Hardcoded database password (key=value)'
    
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
