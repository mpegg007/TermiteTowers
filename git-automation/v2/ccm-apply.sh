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
# Step 0: Compact-mode short circuit (opt-in, self-declared)
#
# A file whose FIRST line carries the %ccm_compact: token is left
# completely untouched. The token IS the header: no strip, no
# reformatting, no field rewrite, no %git_commit_history trail.
# Idempotent by construction — re-running the hook is a no-op
# because the file is never written.
#
# Why this lives here and not in pre-commit.sh: ccm-apply.sh is the
# single choke point every caller goes through (pre-commit.sh today,
# any bulk reheader tool later), so one guard covers them all.
#
# The test is deliberately HEAD-FIRST-LINE-ONLY. This mode is
# documented in git-automation/v2/README.md and in .clinerules/, so a
# whole-file grep would silently opt those documents out of CCM.
# ─────────────────────────────────────────────────────────────
if head -n 1 "$FILE" 2>/dev/null | grep -q '%ccm_compact'; then
    echo "[INFO] $FILE: %ccm_compact on line 1 — leaving file untouched (compact mode)" >&2
    exit 0
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

_line_end_label="none"
if [ -n "$line_end" ]; then
    _line_end_label="CR"
fi
echo "[INFO] $FILE: lang=$lang_mode block=($block_start,$block_end) comment=$line_comment line_terminator=$_line_end_label template=${template_file:-default}" >&2

# ─────────────────────────────────────────────────────────────
# Step 4: Remove old CCM header (if any)
# ─────────────────────────────────────────────────────────────
if [ "$FORCE" = "--force" ]; then
    echo "[INFO] --force: skipping header removal for $FILE" >&2
else
    if ! remove_ccm_header "$FILE"; then
        # Two very different causes, and they must not be conflated:
        #   1. the file simply has no header yet (normal for a new file), or
        #   2. a header exists but the strip tripped the safety assertion (a bug).
        # In case 2, continuing would insert a second header above the first and
        # silently corrupt the file. Refuse instead, so the bug surfaces here
        # rather than as duplicated content in a commit.
        #
        # The test inspects the TOP of the file only. A whole-file grep for a
        # %ccm_ token matches body text -- a heredoc in a test fixture, or a doc
        # showing the marker -- and would declare "header present" for files that
        # have none, blocking them forever. The start marker is the only reliable
        # signal that an unstripped header is still sitting at the top.
        if head -n 40 "$FILE" | grep -q 'ccm_git_header_start'; then
            echo "[ERROR] $FILE: CCM header still present after strip; refusing to append a second header" >&2
            exit 1
        fi
    fi
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