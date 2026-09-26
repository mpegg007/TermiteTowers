#!/usr/bin/env bash
# secret-scanner.sh: V2 secret scanner with improved UX.
#
# Scans a single file for secrets using:
#   1. Custom regex patterns from secrets-patterns.conf (data file)
#   2. GitGuardian ggshield (if installed and not already batch-scanned)
#
# All findings go to stderr AND log file. No "check the log" workflow.
#
# Usage: secret-scanner.sh <file>
#        secret-scanner.sh --list-patterns
#        secret-scanner.sh --dry-run <file>
# Exit: 0 = pass, 1 = secret detected

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

LOG_DIR="$HOME/log"
LOG_FILE="$LOG_DIR/${REPO_NAME}-enhanced-hooks.log"

mkdir -p "$LOG_DIR"

PATTERNS_FILE="$SCRIPT_DIR/secrets-patterns.conf"

# --- --list-patterns mode ---
if [ "${1-}" = "--list-patterns" ]; then
    echo "Custom secret patterns:"
    echo "-----------------------"
    grep -v '^#' "$PATTERNS_FILE" | grep -v '^$' | while IFS='|' read -r pattern severity desc; do
        echo "  [$severity] $desc"
        echo "    Regex: $pattern"
    done
    exit 0
fi

# --- Require file argument ---
DRY_RUN=""
FILE=""

if [ "${1-}" = "--dry-run" ]; then
    DRY_RUN="1"
    FILE="${2-}"
else
    FILE="${1-}"
fi

if [ -z "$FILE" ]; then
    echo "ERROR: Usage: $0 [--dry-run] <file>" >&2
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "  [WARN] File not found: $FILE" >> "$LOG_FILE"
    exit 0
fi

# --- Custom pattern scanning (from config file) ---
SCAN_FAILED=0

if [ -f "$PATTERNS_FILE" ]; then
    # Read patterns into array to avoid subshell scope issues
    PATTERN_LINES=()
    while IFS= read -r line; do
        PATTERN_LINES+=("$line")
    done < <(grep -v '^#' "$PATTERNS_FILE" | grep -v '^$')

    for PATTERN_ENTRY in "${PATTERN_LINES[@]}"; do
        IFS='|' read -r PATTERN SEVERITY DESCRIPTION <<< "$PATTERN_ENTRY"

        if [ "$DRY_RUN" = "1" ]; then
            if grep -qP "$PATTERN" "$FILE" 2>/dev/null; then
                echo "  [WARN] [$SEVERITY] WOULD FLAG in $FILE: $DESCRIPTION" >&2
            fi
        else
            if grep -qP "$PATTERN" "$FILE" 2>/dev/null; then
                SCAN_FAILED=1
                echo "  [FAIL] [$SEVERITY] Secret detected in: $FILE" >&2
                echo "         Pattern: $DESCRIPTION" >&2
                echo "  [FAIL] [$SEVERITY] $FILE: $DESCRIPTION" >> "$LOG_FILE"
                echo "         Matching line(s) (masked):" >&2
                grep -nP "$PATTERN" "$FILE" \
                    | sed 's/\(password[^:]*:\s*\)"[^"]*"/\1"***MASKED***"/gi' \
                    | sed 's/^/           /' >&2
            fi
        fi
    done
fi

# --- GitGuardian scan (if not already batch-scanned by pre-commit) ---
if [ "${SKIP_GGSHIELD:-0}" -ne 1 ] && command -v ggshield &> /dev/null; then
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [INFO] Would run: ggshield secret scan path $FILE" >&2
    else
        ggshield_output=$(ggshield secret scan path "$FILE" 2>&1) || {
            SCAN_FAILED=1
            echo "$ggshield_output" >> "$LOG_FILE"
            echo "  [FAIL] GitGuardian detected secret in: $FILE" >&2
            echo "$ggshield_output" | grep -iE '(incident|secret|file|breach|leak|policy)' | sed 's/^/         /' >&2
        }
    fi
else
    if [ "${SKIP_GGSHIELD:-0}" -eq 1 ]; then
        :
    elif [ ! -f "$REPO_ROOT/.ggshield-not-installed-warned" ]; then
        echo "  [WARN] ggshield not installed - only custom patterns checked" >&2
        echo "         Install: pip install ggshield" >&2
        touch "$REPO_ROOT/.ggshield-not-installed-warned"
    fi
fi

# --- Result ---
if [ "$DRY_RUN" = "1" ]; then
    echo "  [INFO] Dry run complete" >&2
    exit 0
fi

if [ $SCAN_FAILED -eq 1 ]; then
    echo "" >&2
    echo "  SECRET(S) DETECTED in $FILE!" >&2
    echo "  Remove the secret before committing." >&2
    echo "  To bypass: add 'tt-secrets.skip' or 'tt-ggshield.skip' comment to file" >&2
    echo "  Full log: $LOG_FILE" >&2
    echo "" >&2
    exit 1
fi

exit 0