#!/usr/bin/env bash
# ccm-apply.sh: Apply CCM header to a single file.
#
# Orchestrates: metadata capture → history extraction → header removal →
#               header formatting → insertion → field updates →
#               permission preservation
#
# Usage: ccm-apply.sh <file> <rel-path> [--force]
#
# Depends on: ccm-lib.sh, detect-language.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT=$(git rev-parse --show-toplevel)

source "$SCRIPT_DIR/ccm-lib.sh"

FILE="$1"
REL_PATH="$2"
FORCE="${3-}"

if [ ! -f "$FILE" ]; then
    echo "[ERROR] File not found: $FILE" >&2
    exit 1
fi

# ─────────────────────────────────────────────────────────────
# Step 1: Capture metadata BEFORE any modification
#   This is the bug fix — v1 computed exec_flag AFTER
#   remove_ccm_header had already stripped +x.
# ─────────────────────────────────────────────────────────────
capture_file_metadata "$FILE" "$REL_PATH"

# ─────────────────────────────────────────────────────────────
# Step 2: Extract preserved history from old header
# ─────────────────────────────────────────────────────────────
extract_preserved_history "$FILE"

# ─────────────────────────────────────────────────────────────
# Step 3: Detect language mode and comment syntax
# ─────────────────────────────────────────────────────────────
IFS='|' read -r lang_mode block_start block_end line_comment line_end template_file \
    <<< "$(bash "$SCRIPT_DIR/detect-language.sh" "$FILE")"

echo "[INFO] $FILE: lang=$lang_mode block=($block_start,$block_end) comment=$line_comment line_end=$line_end template=$template_file" >&2

# ─────────────────────────────────────────────────────────────
# Step 4: Remove old CCM header (if any)
# ─────────────────────────────────────────────────────────────
if [ "$FORCE" = "--force" ]; then
    echo "[INFO] --force: skipping header removal for $FILE" >&2
else
    remove_ccm_header "$FILE" || true
fi

# ─────────────────────────────────────────────────────────────
# Step 5: Determine template path
# ─────────────────────────────────────────────────────────────
TEMPLATE_FILE="$SCRIPT_DIR/CCM_HEADER_TEMPLATE.txt"
if [ -n "$template_file" ]; then
    TEMPLATE_FILE="$SCRIPT_DIR/$template_file"
fi

# ─────────────────────────────────────────────────────────────
# Step 6: Format new CCM header into temp file
# ─────────────────────────────────────────────────────────────
formatted_header=$(mktemp)
format_ccm_header "$TEMPLATE_FILE" "$block_start" "$block_end" "$line_comment" "$line_end" > "$formatted_header"

# ─────────────────────────────────────────────────────────────
# Step 7: Apply field updates to formatted header
#   (commit-bound fields set to "unknown" — post-commit fills them)
# ─────────────────────────────────────────────────────────────
author=$(git config user.name)
author_email=$(git config user.email)
repo=$(basename "$REPO_ROOT")
branch=$(git rev-parse --abbrev-ref HEAD)

apply_ccm_field_updates \
    "$formatted_header" \
    "$lang_mode" \
    "$author" \
    "$author_email" \
    "$repo" \
    "$branch"

# ─────────────────────────────────────────────────────────────
# Step 8: Insert header into file
# ─────────────────────────────────────────────────────────────
if ! insert_header_after_shebang "$FILE" "$formatted_header"; then
    rm -f "$formatted_header"
    echo "[ERROR] Failed to insert header into $FILE" >&2
    exit 1
fi

rm -f "$formatted_header"

# ─────────────────────────────────────────────────────────────
# Step 9: Preserve original permissions (the bug fix)
# ─────────────────────────────────────────────────────────────
preserve_permissions "$FILE"

echo "[INFO] CCM header applied to $FILE" >&2