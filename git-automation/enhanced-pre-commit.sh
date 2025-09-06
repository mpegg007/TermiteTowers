#!/usr/bin/env bash

# %git_commit_history: unknown %
# %end of template --- %ccm_git_header_end:
# enhanced-pre-commit.sh: Enhanced pre-commit hook for TermiteTowers
# Incorporates logic from update-keywords.sh, with improvements

# --- Shebang and pseudo-shebang handling for BAT/CMD ---
# If the file is .bat/.cmd and starts with @echo on/off or echo on/off, preserve it as the new shebang (@echo off)
# Otherwise, preserve the original shebang for scripts

# --- CCM Header Management ---
# Remove any existing CCM header and re-add the template from CCM_HEADER_TEMPLATE.txt
# This ensures obsolete fields are dropped and new fields are added automatically

# --- Variable Renaming ---
# All %ccm_ vars in the header are now $ccm_git_ vars in the script logic

# --- Add ccm_git_language_mode ---
# Attempts to detect VSCode language mode, else falls back to file extension logic

# --- No ensure_field logic ---
# Only fields present in the template are added

REPO_ROOT=$(git rev-parse --show-toplevel)
TEMPLATE_FILE="$REPO_ROOT/git-automation/CCM_HEADER_TEMPLATE.txt"
LOG_FILE="$REPO_ROOT/git-automation/enhanced-hooks.log"

echo "Enhanced pre-commit hook started at $(date)" >> "$LOG_FILE"

# Helper: Detect pseudo-shebang for BAT/CMD
pseudo_shebang_for_batch() {
    local file="$1"
    local first_line
    first_line=$(head -n 1 "$file")
    case "$first_line" in
        @echo*|echo*)
            echo "$first_line"
            ;;
        *)
            echo "@echo off"
            ;;
    esac
}

# Helper: Remove CCM header (only static header lines)
remove_ccm_header() {
    local file="$1"
    # Rename commit message field before removing header lines
        local tmpfile="${file}.tmp"
        sed -E \
            -e 's| %ccm_git_commit_history: | %git_commit_history: |g' \
            -e '/^.{0,9}%ccm_.*: .* %/d' \
            -e '/^.{0,9}% ccm_.*: .* %/d' \
            -e '/^.{0,9}TermiteTowers Continuous Code Management Header TEMPLATE/d' \
            -e '/^.{0,9}tt-ccm.header.end/d' "$file" > "$tmpfile"
        if cmp -s "$file" "$tmpfile"; then
            echo "[ERROR] No header lines removed from $file" >> "$LOG_FILE"
            rm -f "$tmpfile"
            return 1
        else
            mv "$tmpfile" "$file" && echo "[INFO] Header lines removed from $file" >> "$LOG_FILE"
            return 0
        fi
}

# Helper: Insert CCM header from template
insert_ccm_header() {
    local file="$1"
    local rel_path="$2"
    local eol="$3"
    local lang_mode="$4"
    local block_start="$5"
    local block_end="$6"
    local line_comment="$7"

    blob_sha=$(git hash-object "$file" 2>/dev/null || echo unknown)
    exec_flag=$(test -x "$file" && echo yes || echo no)
    file_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    modify_date=$(date +"%Y-%m-%d %H:%M:%S")

    # Format header with block and line comments
    tmp_header=$(mktemp)
    cp "$TEMPLATE_FILE" "$tmp_header"
    formatted_header=$(mktemp)
    header_lines=()
    while IFS= read -r line; do
        header_lines+=("$line")
    done < "$tmp_header"
    {
        if [ -n "$block_start" ]; then echo "$block_start"; fi
        for i in "${!header_lines[@]}"; do
            l="${header_lines[$i]}"
            if [ -n "$line_comment" ]; then
                out_line="$line_comment $l"
            else
                out_line="$l"
            fi
            # Add block_end to last line
            if [ "$i" -eq $((${#header_lines[@]}-1)) ] && [ -n "$block_end" ]; then
                out_line="$out_line $block_end"
            fi
            echo "$out_line"
        done
    } > "$formatted_header"

    # Insert header after shebang or pseudo-shebang
    if head -n 1 "$file" | grep -q '^#!'; then
        { head -n 1 "$file"; cat "$formatted_header"; tail -n +2 "$file"; } > "$file.new"
    elif [[ "$file" == *.bat || "$file" == *.cmd ]]; then
        { pseudo_shebang_for_batch "$file"; cat "$formatted_header"; tail -n +2 "$file"; } > "$file.new"
    else
        { cat "$formatted_header"; cat "$file"; } > "$file.new"
    fi
    if cmp -s "$file" "$file.new"; then
        echo "[ERROR] Header insertion failed for $file" >> "$LOG_FILE"
        rm -f "$tmp_header" "$formatted_header" "$file.new"
        return 1
    else
        mv "$file.new" "$file" && echo "[INFO] Header inserted for $file" >> "$LOG_FILE"
        rm -f "$tmp_header" "$formatted_header"
    fi

    # Now update all static and commit-bound fields using a single sed block
    sed -i \
        -e "s|%ccm_git_modify_date: .* %|%ccm_git_modify_date: $modify_date %|g" \
        -e "s|%ccm_git_author: .* %|%ccm_git_author: $author %|g" \
        -e "s|%ccm_git_author_email: .* %|%ccm_git_author_email: $author_email %|g" \
        -e "s|%ccm_git_repo: .* %|%ccm_git_repo: $repo %|g" \
        -e "s|%ccm_git_branch: .* %|%ccm_git_branch: $branch %|g" \
        -e "s|%ccm_git_object_id: .* %|%ccm_git_object_id: $file_path:0 %|g" \
        -e "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: unknown %|g" \
        -e "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: 0 %|g" \
        -e "s|%git_commit_history: .* %|%ccm_git_commit_message: unknown %|g" \
        -e "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: unknown %|g" \
        -e "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: unknown %|g" \
        -e "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %|g" \
        -e "s|%ccm_git_file_last_modified: .* %|%ccm_git_file_last_modified: $file_last_modified %|g" \
        -e "s|%ccm_git_file_name: .* %|%ccm_git_file_name: $file_name %|g" \
        -e "s|%ccm_git_file_type: .* %|%ccm_git_file_type: $file_type %|g" \
        -e "s|%ccm_git_file_encoding: .* %|%ccm_git_file_encoding: $file_encoding %|g" \
        -e "s|%ccm_git_file_eol: .* %|%ccm_git_file_eol: $file_eol %|g" \
        -e "s|%ccm_git_path: .* %|%ccm_git_path: $file_path %|g" \
        -e "s|%ccm_git_blob_sha: .* %|%ccm_git_blob_sha: $blob_sha %|g" \
        -e "s|%ccm_git_exec: .* %|%ccm_git_exec: $exec_flag %|g" \
        -e "s|%ccm_git_size: .* %|%ccm_git_size: $file_size %|g" \
        -e "s|%ccm_git_tag: .* %|%ccm_git_tag:  %|g" \
        -e "s|%ccm_git_language_mode: .* %|%ccm_git_language_mode: $lang_mode %|g" "$file"
}

# Main loop: process staged files
while IFS= read -r -d '' FILE; do
    # Skip files in git-automation folder
    case "$FILE" in
        git-automation/*|*/git-automation/*) continue ;;
    esac
    REL_PATH=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then continue; fi 
    if ! echo "$MIME_INFO" | grep -qiE '^text/|charset='; then continue; fi
    FILE_EOL="$(grep -q $'\r\n' "$FILE" && echo "CRLF" || echo "LF")"
    IFS='|' read -r lang_mode block_start block_end line_comment <<< "$(bash "$REPO_ROOT/git-automation/get_language_mode_and_comments.sh" "$FILE")"
    remove_ccm_header "$FILE"
    insert_ccm_header "$FILE" "$REL_PATH" "$FILE_EOL" "$lang_mode" "$block_start" "$block_end" "$line_comment"

    git add "$FILE"
done < <(git diff --cached --name-only -z)

echo "Enhanced pre-commit hook finished at $(date)" >> "$LOG_FILE"
