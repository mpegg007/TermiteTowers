#!/usr/bin/env bash
# post-commit.sh: V2 post-commit hook — thin wrapper.
#
# After a commit, fills in final commit-bound CCM fields:
#   commit_id, commit_count, commit_message, commit_author,
#   commit_email, commit_date, object_id
#
# Safety: lock file prevents recursion during amend.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

source "$SCRIPT_DIR/ccm-lib.sh"

LOG_DIR="$HOME/log"
LOG_FILE="$LOG_DIR/${REPO_NAME}-enhanced-hooks.log"
LOCK_FILE=$(git rev-parse --git-path ccm-post-commit.lock)

mkdir -p "$LOG_DIR"

# Prevent recursion
if [ -f "$LOCK_FILE" ]; then
    echo "Post-commit: lock present, skipping" >> "$LOG_FILE"
    exit 0
fi

echo "=== V2 post-commit started at $(date) ===" >> "$LOG_FILE"

# ─────────────────────────────────────────────────────────────
# Commit variables
# ─────────────────────────────────────────────────────────────
COMMIT_ID=$(git rev-parse HEAD)
COMMIT_COUNT=$(git rev-list --count HEAD)
COMMIT_MSG_RAW=$(git log -1 --pretty=format:'%s')
COMMIT_MSG_SAFE=$(echo "$COMMIT_MSG_RAW" | tr -d '\r\n' | cut -c1-100 | sed 's/%/%%/g')
COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an')
COMMIT_EMAIL=$(git log -1 --pretty=format:'%ae')
COMMIT_DATE=$(git log -1 --pretty=format:'%ci')

# ─────────────────────────────────────────────────────────────
# File list
# ─────────────────────────────────────────────────────────────
FILES_TO_PROCESS=()
GIT_MODE="Y"

if [ -n "${1-}" ] && [ -f "$1" ]; then
    FILES_TO_PROCESS=("$1")
    GIT_MODE="N"
else
    mapfile -d '' -t FILES_TO_PROCESS < <(git --no-pager diff-tree --no-commit-id --name-only -r -z HEAD)
fi

try_mode=""
if [ "${2-}" = "--try" ] || [ "$GIT_MODE" = "N" ]; then
    try_mode="--try"
fi

echo "[DEBUG] Post-commit: ${#FILES_TO_PROCESS[@]} file(s), try_mode=$try_mode" >> "$LOG_FILE"

# ─────────────────────────────────────────────────────────────
# Process each committed file
# ─────────────────────────────────────────────────────────────
for FILE in "${FILES_TO_PROCESS[@]}"; do

    # Safety exclusions
    case "$FILE" in
        git-automation/CCM_*_TEMPLATE.txt|git-automation/*/CCM_*_TEMPLATE.txt|.git/hooks/*)
            echo "[INFO] SAFETY: Skipping $FILE (template/hook)" >> "$LOG_FILE"
            continue ;;
        git-automation/*.sh)
            if [ "$GIT_MODE" = "Y" ]; then
                echo "[INFO] SAFETY: Skipping $FILE (automation script)" >> "$LOG_FILE"
                continue
            else
                echo "[INFO] NOTICE: Processing $FILE (explicitly requested)" >> "$LOG_FILE"
            fi ;;
    esac

    # Skip marker
    grep -q "tt-hooks.skip-post-commit" "$FILE" 2>/dev/null && {
        echo "[INFO] Skipping $FILE (skip marker)" >> "$LOG_FILE"
        continue
    }

    # Extra exclusion for automation scripts
    if [ "$try_mode" != "--try" ]; then
        case "$FILE" in
            git-automation/enhanced-pre-commit.sh|git-automation/enhanced-post-commit.sh)
                echo "[INFO] Skipping $FILE (git-automation)" >> "$LOG_FILE"
                continue ;;
        esac
    fi

    # Only process files with CCM header
    if ! grep -qE '%ccm_git_.*: .* %' "$FILE" 2>/dev/null; then
        echo "[DEBUG] Skipping $FILE: no CCM header" >> "$LOG_FILE"
        continue
    fi

    # Skip binary
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then
        echo "[DEBUG] Skipping $FILE: binary" >> "$LOG_FILE"
        continue
    fi

    echo "[DEBUG] Updating commit fields in $FILE" >> "$LOG_FILE"

    # Update commit-bound fields
    sed -i \
        -e "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: $COMMIT_ID %|g" \
        -e "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: $COMMIT_COUNT %|g" \
        -e "s|%ccm_git_object_id: .* %|%ccm_git_object_id: $FILE:$COMMIT_COUNT %|g" \
        -e "s|%ccm_git_commit_message: .* %|%ccm_git_commit_message: $COMMIT_MSG_SAFE %|g" \
        -e "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: $COMMIT_AUTHOR %|g" \
        -e "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: $COMMIT_EMAIL %|g" \
        -e "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: $COMMIT_DATE %|g" \
        "$FILE"

done

# ─────────────────────────────────────────────────────────────
# Amend if changes exist
# ─────────────────────────────────────────────────────────────
if ! git diff --quiet; then
    if [ "$try_mode" = "--try" ]; then
        echo "[INFO] --try: skipping git add/amend" >> "$LOG_FILE"
    else
        # Deleted files appear in the commit's file list but no longer exist;
        # `git add <deleted path>` is a fatal pathspec error, which aborts this
        # hook before the amend and leaves the refreshed fields uncommitted.
        EXISTING_FILES=()
        for f in "${FILES_TO_PROCESS[@]}"; do
            if [ -f "$f" ]; then EXISTING_FILES+=("$f"); fi
        done
        if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
            git add "${EXISTING_FILES[@]}"
        fi
    fi

    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT

    # Check if safe to amend (not behind upstream)
    AHEAD_BEHIND=$(git rev-list --left-right --count @{u}...HEAD 2>/dev/null || echo "")
    AHEAD=0
    BEHIND=0
    if [ -n "$AHEAD_BEHIND" ]; then
        AHEAD=$(echo "$AHEAD_BEHIND" | awk '{print $2}')
        BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
    fi

    if [ "$BEHIND" = "0" ]; then
        if [ "$try_mode" != "--try" ]; then
            git -c core.hooksPath=/dev/null commit --amend --no-edit
        fi
        echo "Amended commit $COMMIT_ID with finalized CCM fields" >> "$LOG_FILE"
    else
        echo "Skipping amend: branch is behind upstream" >> "$LOG_FILE"
    fi
else
    echo "No final CCM updates needed" >> "$LOG_FILE"
fi

echo "=== V2 post-commit finished at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"