#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE %ccm_git_header_start: 
# %ccm_git_modify_date: 2025-08-29 07:37:53 %
# %ccm_git_author: CCM Maintainer %
# %ccm_git_author_email: ccm@test %
# %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
# %ccm_git_branch: main %
# %ccm_git_object_id: git-automation/enhanced-pre-commit.sh:0 %
# %ccm_git_commit_id: unknown %
# %ccm_git_commit_count: 0 %
# %ccm_git_commit_message: unknown %
# %ccm_git_commit_author: unknown %
# %ccm_git_commit_email: unknown %
# %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
# %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
# %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
# %ccm_git_file_type: text/plain %
# %ccm_git_file_encoding: us-ascii %
# %ccm_git_file_eol: CRLF %
# %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
# %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
# %ccm_git_exec: no %
# %ccm_git_size: 659 %
# %ccm_git_tag:  %
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

# Helper: Remove CCM header (regex logic for all specified patterns)
remove_ccm_header() {
    local file="$1"
    # Replace commit message line with git_commit_history
    sed -i -E 's|%git_commit_history: (.*) %|%git_commit_history: \1 %|g' "$file"
    # Remove header lines
    sed -i -E \
        -e '/ %ccm_git_[a-z_]+: .* %/d' \
        -e '/^# TermiteTowers Continuous Code Management Header TEMPLATE/d' \
        -e '/^# tt-ccm.header.end/d' \
        -e '/^# % ccm_[a-z_]+: .* %/d' "$file"
}

# Helper: Insert CCM header from template
insert_ccm_header() {
    local file="$1"
    local rel_path="$2"
    local eol="$3"
    local tmp_header
    tmp_header=$(mktemp)
    awk -v path="$rel_path" -v eol="$eol" '{
        gsub(/<PATH>/, path)
        if ($0 ~ /% ccm_file_name:/) gsub(/% ccm_file_name: .*/, "% ccm_file_name: " path " %")
        if ($0 ~ /% ccm_file_eol:/) gsub(/% ccm_file_eol: .*/, "% ccm_file_eol: " eol " %")
        print
    }' "$TEMPLATE_FILE" > "$tmp_header"
    # Insert header after shebang or pseudo-shebang
    if head -n 1 "$file" | grep -q '^#!'; then
        { head -n 1 "$file"; cat "$tmp_header"; tail -n +2 "$file"; } > "$file.new"
    elif [[ "$file" == *.bat || "$file" == *.cmd ]]; then
        { pseudo_shebang_for_batch "$file"; cat "$tmp_header"; tail -n +2 "$file"; } > "$file.new"
    else
        { cat "$tmp_header"; cat "$file"; } > "$file.new"
    fi
    mv "$file.new" "$file"
    rm -f "$tmp_header"
}



# Helper: Get language mode for a file
get_language_mode() {
    local file="$1"
    local ext="${file##*.}"
    local mode=""
    if [ -n "$VSCODE_LANGUAGE_MODE" ]; then
        mode="$VSCODE_LANGUAGE_MODE"
    else
        case "$ext" in
            sh|bash) mode="shellscript" ;;
            py) mode="python" ;;
            js) mode="javascript" ;;
            ts) mode="typescript" ;;
            bat|cmd) mode="bat" ;;
            ps1) mode="powershell" ;;
            yaml|yml) mode="yaml" ;;
            sql) mode="sql" ;;
            *) mode="$ext" ;;
        esac
    fi
    echo "$mode"
}

# Main loop: process staged files
while IFS= read -r -d '' FILE; do
    REL_PATH=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then continue; fi
    if ! echo "$MIME_INFO" | grep -qiE '^text/|charset='; then continue; fi
    FILE_EOL="$(grep -q $'\r\n' "$FILE" && echo "CRLF" || echo "LF")"
    remove_ccm_header "$FILE"
    insert_ccm_header "$FILE" "$REL_PATH" "$FILE_EOL"
    LANG_MODE="$(get_language_mode "$FILE")"
    sed -i "s|% ccm_git_language_mode: shellscript %|g" "$FILE"
    git add "$FILE"
done < <(git diff --cached --name-only -z)

echo "Enhanced pre-commit hook finished at $(date)" >> "$LOG_FILE"
