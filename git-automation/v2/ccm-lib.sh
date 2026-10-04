#!/usr/bin/env bash
# ccm-lib.sh: Shared library for CCM header management
# Source this from other scripts: source "$REPO_ROOT/git-automation/v2/ccm-lib.sh"

set -euo pipefail

# ─────────────────────────────────────────────────────────────────
# capture_file_metadata "$file" "$rel_path"
#
# Captures ALL file-level metadata BEFORE any modification.
# This fixes the exec_flag timing bug: v1 captured exec_flag
# AFTER remove_ccm_header had already stripped +x.
# ─────────────────────────────────────────────────────────────────
capture_file_metadata() {
    local file="$1"
    local rel_path="$2"

    # These are exposed globally for the caller
    FILE_EXEC_FLAG=$(test -x "$file" && echo yes || echo no)
    FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo 0)
    FILE_MODIFY_DATE=$(date +"%Y-%m-%d %H:%M:%S")
    FILE_LAST_MODIFIED=$(stat -c %y "$file" 2>/dev/null | cut -d'.' -f1 || echo unknown)
    FILE_NAME=$(basename "$file")
    FILE_TYPE=$(file --brief --mime-type "$file" 2>/dev/null || echo unknown)
    FILE_ENCODING=$(file --brief --mime-encoding "$file" 2>/dev/null || echo unknown)
    FILE_EOL=$(grep -q $'\r\n' "$file" && echo "CRLF" || echo "LF")
    FILE_PATH="$rel_path"
    FILE_BLOB_SHA=$(git hash-object "$file" 2>/dev/null || echo unknown)
}

# ─────────────────────────────────────────────────────────────────
# extract_preserved_history "$file"
#
# Scans the old header for commit message, date, and author
# before header removal. Also collects old %git_commit_history lines
# so they can be re-emitted after the new header.
# ─────────────────────────────────────────────────────────────────
extract_preserved_history() {
    local file="$1"

    PRESERVED_COMMIT_MSG=""
    PRESERVED_COMMIT_DATE=""
    PRESERVED_COMMIT_AUTHOR=""
    OLD_HISTORY_LINES=()

    local line

    # Extract commit message
    line=$(grep -m1 '%ccm_git_commit_message' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_message\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_MSG="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_message:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_MSG="${BASH_REMATCH[1]}"
    fi

    # Extract commit date (YYYY-MM-DD portion)
    line=$(grep -m1 '%ccm_git_commit_date' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_date\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_date:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    fi
    if [[ "$PRESERVED_COMMIT_DATE" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    fi

    # Extract commit author
    line=$(grep -m1 '%ccm_git_commit_author' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_author\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_AUTHOR="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_author:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_AUTHOR="${BASH_REMATCH[1]}"
    fi

    # Collect old history lines (survive header removal, float in file body)
    while IFS= read -r line; do
        if [[ "$line" =~ %git_commit_history ]]; then
            OLD_HISTORY_LINES+=("$line")
        fi
    done < "$file"

    # Sanitize: blank "unknown" messages
    [ "$PRESERVED_COMMIT_MSG" = "unknown" ] && PRESERVED_COMMIT_MSG=""

    # Sanitize: blank if no alphanumeric content (placeholders)
    if [ -n "$PRESERVED_COMMIT_MSG" ] && ! [[ "$PRESERVED_COMMIT_MSG" =~ [A-Za-z0-9] ]]; then
        PRESERVED_COMMIT_MSG=""
    fi
}

# ─────────────────────────────────────────────────────────────────
# remove_ccm_header "$file"
#
# Strips CCM header lines from the file. Does NOT remove
# %git_commit_history lines — those survive as a history trail.
# ─────────────────────────────────────────────────────────────────
remove_ccm_header() {
    local file="$1"
    local tmpfile="${file}.tmp.removeccm"

    local line_count_before
    line_count_before=$(wc -l < "$file")

    # Remove CCM header lines and template markers
    sed -E \
        -e '/^.{0,9}%ccm_.*: .* %/d' \
        -e '/^.{0,9}% ccm_.*: .* %/d' \
        -e '/^.{0,9}TermiteTowers Continuous Code Management Header TEMPLATE/d' \
        -e '/^.{0,9}tt-ccm.header.end/d' \
        "$file" > "$tmpfile"

    local line_count_after
    line_count_after=$(wc -l < "$tmpfile")
    local lines_removed=$((line_count_before - line_count_after))

    if [ "$lines_removed" -gt 30 ]; then
        echo "[ERROR] SAFETY: Would remove $lines_removed lines from $file (max 30). Aborting." >&2
        rm -f "$tmpfile"
        return 1
    fi

    if cmp -s "$file" "$tmpfile"; then
        echo "[WARN] No header lines removed from $file" >&2
        rm -f "$tmpfile"
        return 1  # No header found — signal to caller
    fi

    mv "$tmpfile" "$file"
    return 0
}

# ─────────────────────────────────────────────────────────────────
# parse_template_directives "$template_file"
#
# Returns template directives: TEMPLATE_ASIS, HISTORY_ASIS,
# COMMIT_HISTORY_FORMAT. Also strips directive lines from the
# working copy.
# ─────────────────────────────────────────────────────────────────
parse_template_directives() {
    local tmpfile="$1"

    TEMPLATE_ASIS=""
    HISTORY_ASIS=""
    COMMIT_HISTORY_FORMAT=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^##TEMPLATE_ASIS ]]; then
            TEMPLATE_ASIS="yes"
        elif [[ "$line" =~ ^##HISTORY_ASIS ]]; then
            HISTORY_ASIS="yes"
        elif [[ "$line" =~ ^##COMMIT_HISTORY:[[:space:]]*(.*) ]]; then
            COMMIT_HISTORY_FORMAT="${BASH_REMATCH[1]}"
        fi
    done < "$tmpfile"

    # Remove directive lines from working copy
    sed -i '/^##TEMPLATE_ASIS$/d; /^##HISTORY_ASIS$/d; /^##COMMIT_HISTORY:/d' "$tmpfile"
}

# ─────────────────────────────────────────────────────────────────
# format_ccm_header "$template_file" "$block_start" "$block_end" \
#                    "$line_comment" "$line_end"
#
# Formats the CCM header lines and writes them to stdout.
# Output is captured by the caller into a temp file.
# ─────────────────────────────────────────────────────────────────
format_ccm_header() {
    local tpl_file="$1"
    local block_start="$2"
    local block_end="$3"
    local line_comment="$4"
    local line_end="$5"

    local tmp_header
    tmp_header=$(mktemp)
    cp "$tpl_file" "$tmp_header"

    parse_template_directives "$tmp_header"

    # Read all template lines (stripped of CR)
    local header_lines=()
    local line
    while IFS= read -r line; do
        line="${line%$'\r'}"
        header_lines+=("$line")
    done < "$tmp_header"

    if [ "$TEMPLATE_ASIS" = "yes" ]; then
        # ASIS mode: emit every line verbatim
        for l in "${header_lines[@]}"; do
            echo "$l"
        done
    else
        # Default mode: wrap with language comment syntax
        local count=${#header_lines[@]}
        for i in "${!header_lines[@]}"; do
            local out_line="${header_lines[$i]}"
            if [ "$i" -eq 0 ]; then
                out_line="${block_start}${line_comment} $out_line"
            else
                out_line="$line_comment $out_line"
            fi
            if [ "$i" -eq $((count - 1)) ]; then
                out_line="$out_line $block_end"
            fi
            if [ -n "$line_end" ]; then
                out_line="$out_line$line_end"
            fi
            echo "$out_line"
        done
    fi

    # Append preserved commit history as a new line
    if [ -n "$PRESERVED_COMMIT_MSG" ] && [ -n "$COMMIT_HISTORY_FORMAT" ]; then
        local hist="${COMMIT_HISTORY_FORMAT}"
        hist="${hist//\$MESSAGE/$PRESERVED_COMMIT_MSG}"
        hist="${hist//\$DATE/$PRESERVED_COMMIT_DATE}"
        hist="${hist//\$AUTHOR/$PRESERVED_COMMIT_AUTHOR}"
        if [ "$HISTORY_ASIS" = "yes" ]; then
            echo "$hist"
        else
            echo "${block_start}${line_comment} $hist $block_end"
        fi
    fi

    # Re-emit old history lines (survived header removal)
    for old_line in "${OLD_HISTORY_LINES[@]}"; do
        echo "$old_line"
    done

    rm -f "$tmp_header"
}

# ─────────────────────────────────────────────────────────────────
# apply_ccm_field_updates "$file" "$lang_mode" "$author" "$author_email" \
#     "$repo" "$branch"
#
# Applies sed replacements for all CCM fields. Shared between
# pre-commit (sets unknown for commit-bound fields) and post-commit
# (fills final values) and update-ccm-header.
# ─────────────────────────────────────────────────────────────────
apply_ccm_field_updates() {
    local file="$1"
    local lang_mode="$2"
    local author="${3-}"
    local author_email="${4-}"
    local repo="${5-}"
    local branch="${6-}"
    local commit_id="${7:-unknown}"
    local commit_count="${8:-unknown}"
    local commit_message="${9:-unknown}"
    local commit_author="${10:-unknown}"
    local commit_email="${11:-unknown}"
    local commit_date="${12:-unknown}"

    sed -i \
        -e "s|%ccm_git_modify_date: .* %|%ccm_git_modify_date: $FILE_MODIFY_DATE %|g" \
        -e "s|%ccm_git_author: .* %|%ccm_git_author: ${author:-unknown} %|g" \
        -e "s|%ccm_git_author_email: .* %|%ccm_git_author_email: ${author_email:-unknown} %|g" \
        -e "s|%ccm_git_repo: .* %|%ccm_git_repo: ${repo:-unknown} %|g" \
        -e "s|%ccm_git_branch: .* %|%ccm_git_branch: ${branch:-unknown} %|g" \
        -e "s|%ccm_git_object_id: .* %|%ccm_git_object_id: unknown %|g" \
        -e "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: ${commit_id} %|g" \
        -e "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: ${commit_count} %|g" \
        -e "s|%ccm_git_commit_message: .* %|%ccm_git_commit_message: ${commit_message} %|g" \
        -e "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: ${commit_author} %|g" \
        -e "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: ${commit_email} %|g" \
        -e "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: ${commit_date} %|g" \
        -e "s|%ccm_git_file_last_modified: .* %|%ccm_git_file_last_modified: $FILE_LAST_MODIFIED %|g" \
        -e "s|%ccm_git_file_name: .* %|%ccm_git_file_name: $FILE_NAME %|g" \
        -e "s|%ccm_git_file_type: .* %|%ccm_git_file_type: $FILE_TYPE %|g" \
        -e "s|%ccm_git_file_encoding: .* %|%ccm_git_file_encoding: $FILE_ENCODING %|g" \
        -e "s|%ccm_git_file_eol: .* %|%ccm_git_file_eol: $FILE_EOL %|g" \
        -e "s|%ccm_git_path: .* %|%ccm_git_path: $FILE_PATH %|g" \
        -e "s|%ccm_git_blob_sha: .* %|%ccm_git_blob_sha: $FILE_BLOB_SHA %|g" \
        -e "s|%ccm_git_exec: .* %|%ccm_git_exec: $FILE_EXEC_FLAG %|g" \
        -e "s|%ccm_git_size: .* %|%ccm_git_size: $FILE_SIZE %|g" \
        -e "s|%ccm_git_tag: .* %|%ccm_git_tag:  %|g" \
        -e "s|%ccm_git_language_mode: .* %|%ccm_git_language_mode: $lang_mode %|g" \
        "$file"
}

# ─────────────────────────────────────────────────────────────────
# preserve_permissions "$file"
#
# Restores original execute bit after all file modifications.
# Uses FILE_EXEC_FLAG captured by capture_file_metadata().
# ─────────────────────────────────────────────────────────────────
preserve_permissions() {
    local file="$1"
    if [ "$FILE_EXEC_FLAG" = "yes" ]; then
        chmod +x "$file"
    fi
}

# ─────────────────────────────────────────────────────────────────
# insert_header_after_shebang "$file" "$formatted_header"
#
# Inserts the formatted header into the file, preserving shebang
# or pseudo-shebang as the first line. Replaces file in-place.
# ─────────────────────────────────────────────────────────────────
insert_header_after_shebang() {
    local file="$1"
    local header_file="$2"

    local first_line
    first_line=$(head -n 1 "$file")

    local newfile="${file}.new"

    if head -n 1 "$file" | grep -q '^#!'; then
        { head -n 1 "$file"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif echo "$first_line" | grep -qiE '^(#!|#Requires |# yaml-language-server:|# *coding[:=]|# *-\*- coding:|<\?xml|<!DOCTYPE html|<\?php)'; then
        { echo "$first_line"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif [[ "$file" == *.json ]] && echo "$first_line" | grep -q '^{'; then
        { echo "$first_line"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif [[ "$file" == *.bat || "$file" == *.cmd ]]; then
        { head -n 1 "$file" | grep -qiE '^@echo|^echo' && head -n 1 "$file" || echo "@echo off"
          cat "$header_file"
          tail -n +2 "$file"; } > "$newfile"
    else
        { cat "$header_file"; cat "$file"; } > "$newfile"
    fi

    if cmp -s "$file" "$newfile"; then
        echo "[ERROR] Header insertion produced no change for $file" >&2
        rm -f "$newfile"
        return 1
    fi

    mv "$newfile" "$file"
    return 0
}