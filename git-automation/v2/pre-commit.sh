#!/usr/bin/env bash
# pre-commit.sh: V2 pre-commit hook — thin wrapper.
#
# For each staged file:
#   1. Apply CCM header (ccm-apply.sh)
#   2. Scan for secrets (secret-scanner.sh)
#   3. git add
#
# Safety: Never processes git-automation/*.sh or .git/hooks/*
# Supports: --try mode for testing without git operations

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

LOG_DIR="$HOME/log"
LOG_FILE="$LOG_DIR/${REPO_NAME}-enhanced-hooks.log"

mkdir -p "$LOG_DIR"
echo "=== V2 pre-commit started at $(date) ===" >> "$LOG_FILE"

# ─────────────────────────────────────────────────────────────
# Build file list
# ─────────────────────────────────────────────────────────────
FILES_TO_PROCESS=()
GIT_MODE="Y"

if [ -n "${1-}" ] && [ -f "$1" ]; then
    echo "[DEBUG] Single file mode: $1" >> "$LOG_FILE"
    FILES_TO_PROCESS=("$1")
    GIT_MODE="N"
else
    mapfile -d '' -t FILES_TO_PROCESS < <(git diff --cached --name-only -z)
fi

try_mode=""
if [ "${2-}" = "--try" ] || [ "$GIT_MODE" = "N" ]; then
    try_mode="--try"
fi

echo "[DEBUG] Processing ${#FILES_TO_PROCESS[@]} file(s), try_mode=$try_mode" >> "$LOG_FILE"

# ─────────────────────────────────────────────────────────────
# Batch GitGuardian scan (optimization)
# ─────────────────────────────────────────────────────────────
GG_SKIP_FILES_STAGED=()
if command -v ggshield &> /dev/null; then
    for FILE in "${FILES_TO_PROCESS[@]}"; do
        case "$FILE" in
            git-automation/CCM_*_TEMPLATE.txt|git-automation/*/CCM_*_TEMPLATE.txt|.git/hooks/*) continue ;;
            git-automation/*.sh)
                [ "$try_mode" != "--try" ] && continue ;;
        esac
        # Deleted files are listed by `git diff --cached` but have no content to
        # scan; handing a missing path to ggshield aborts the whole commit.
        [ -f "$FILE" ] || continue
        grep -q "tt-hooks.skip-post-commit" "$FILE" 2>/dev/null && continue
        file --mime -b "$FILE" 2>/dev/null | grep -qi 'charset=binary' && continue
        case "$FILE" in
            *.example|*.example.*|*.template|*.template.*|*.sample|*.sample.*|*-example.*|*-template.*|*-sample.*) continue ;;
        esac
        grep -q "tt-secrets.skip\|tt-ggshield.skip" "$FILE" 2>/dev/null && continue
        GG_SKIP_FILES_STAGED+=("$FILE")
    done

    if [ ${#GG_SKIP_FILES_STAGED[@]} -gt 0 ]; then
        echo "[INFO] Batch GitGuardian scan on ${#GG_SKIP_FILES_STAGED[@]} file(s)..." >> "$LOG_FILE"
        if ! ggshield_output=$(ggshield secret scan path "${GG_SKIP_FILES_STAGED[@]}" 2>&1); then
            echo "$ggshield_output" >> "$LOG_FILE"
            echo "" >&2
            echo "❌ GitGuardian detected secrets!" >&2
            echo "   Affected files:" >&2
            echo "$ggshield_output" | grep -iE '(incident|secret|file|breach|leak)' | sed 's/^/   /' >&2
            echo "   Full details: $LOG_FILE" >&2
            echo "" >&2
            exit 1
        fi
        echo "[INFO] Batch scan passed." >> "$LOG_FILE"
        export SKIP_GGSHIELD=1
    fi
fi

# ─────────────────────────────────────────────────────────────
# Per-file processing loop
# ─────────────────────────────────────────────────────────────
for FILE in "${FILES_TO_PROCESS[@]}"; do

    # Safety: never process automation/hook files
    case "$FILE" in
        git-automation/CCM_*_TEMPLATE.txt|git-automation/*/CCM_*_TEMPLATE.txt|.git/hooks/*)
            echo "[INFO] SAFETY: Skipping $FILE (template/hook)" >> "$LOG_FILE"
            continue ;;
        git-automation/*.sh)
            if [ "$try_mode" != "--try" ]; then
                echo "[INFO] SAFETY: Skipping $FILE (automation script)" >> "$LOG_FILE"
                continue
            else
                echo "[INFO] NOTICE: Processing automation script $FILE (--try mode)" >> "$LOG_FILE"
            fi ;;
    esac

    # Skip post-commit exclusion
    grep -q "tt-hooks.skip-post-commit" "$FILE" 2>/dev/null && {
        echo "[INFO] Skipping $FILE (tt-hooks.skip-post-commit)" >> "$LOG_FILE"
        continue
    }

    # Binary check
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then
        echo "[INFO] Skipping $FILE (binary)" >> "$LOG_FILE"
        continue
    fi
    if ! echo "$MIME_INFO" | grep -qiE '^text/|charset='; then
        echo "[INFO] Skipping $FILE (not text)" >> "$LOG_FILE"
        continue
    fi

    REL_PATH=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")
    echo "[INFO] Processing $FILE ($REL_PATH)" >> "$LOG_FILE"

    # ── Secret scanning (per-file, custom patterns) ──
    case "$FILE" in
        *.example|*.example.*|*.template|*.template.*|*.sample|*.sample.*|*-example.*|*-template.*|*-sample.*)
            echo "[INFO] Skipping secret scan for $FILE (template/example)" >> "$LOG_FILE" ;;
        *)
            if ! grep -q "tt-secrets.skip\|tt-ggshield.skip" "$FILE" 2>/dev/null; then
                if [ -x "$SCRIPT_DIR/secret-scanner.sh" ]; then
                    if ! "$SCRIPT_DIR/secret-scanner.sh" "$FILE"; then
                        echo "[ERROR] Secret detected in $FILE, aborting commit" >> "$LOG_FILE"
                        exit 1
                    fi
                fi
            fi ;;
    esac

    # ── Apply CCM header ──
    if ! "$SCRIPT_DIR/ccm-apply.sh" "$FILE" "$REL_PATH"; then
        echo "[WARN] Failed to apply CCM header to $FILE, skipping" >> "$LOG_FILE"
        continue
    fi

    # ── Stage ──
    if [ "$try_mode" = "--try" ]; then
        echo "[INFO] --try: skipping git add for $FILE" >> "$LOG_FILE"
    else
        git add "$FILE"
        echo "[INFO] Staged $FILE" >> "$LOG_FILE"
    fi

done

echo "=== V2 pre-commit finished at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"