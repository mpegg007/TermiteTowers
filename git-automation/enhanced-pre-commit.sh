#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: git-automation/enhanced-pre-commit.sh:100 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 818b10f80f16e03e7862112837844d98e3d5cff1 %
#  %ccm_git_commit_id: 043d1161f28704961fc3977112b42f1a9c83dd93 %
#  %ccm_git_commit_count: 100 %
#  %ccm_git_commit_date: 2025-10-11 10:56:22 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: libre logon fix plus hook rework for win.os %
#  %ccm_git_modify_date: 2025-09-06 12:02:06 %
#  %ccm_git_file_last_modified: 2025-09-06 11:52:11 %
#  %ccm_git_file_name: enhanced-pre-commit.sh %
#  %ccm_git_path: git-automation/enhanced-pre-commit.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10950 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

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
REPO_NAME=$(basename "$REPO_ROOT")
LOG_DIR="$HOME/log"
LOG_FILE="$LOG_DIR/${REPO_NAME}-enhanced-hooks.log"
LOGROTATE_CONF="$REPO_ROOT/infra/logrotate/logrotate.conf"
LOGROTATE_STATE="$HOME/.logrotate.state"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Trigger logrotate check (uses repo-maintained config)
if [ -f "$LOGROTATE_CONF" ]; then
    logrotate -s "$LOGROTATE_STATE" "$LOGROTATE_CONF" 2>/dev/null || true
fi

echo "Enhanced pre-commit hook started at $(date)" >> "$LOG_FILE"

# --- Commit-wide variables ---
author=$(git config user.name)
author_email=$(git config user.email)
repo="$REPO_NAME"
branch=$(git rev-parse --abbrev-ref HEAD)

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
        
        # Base sed command for all files
        # NOTE: We do NOT remove %git_commit_history lines - they accumulate as a history trail
        local sed_cmd=(sed -E \
            -e '/^.{0,9}%ccm_.*: .* %/d' \
            -e '/^.{0,9}% ccm_.*: .* %/d' \
            -e '/^.{0,9}TermiteTowers Continuous Code Management Header TEMPLATE/d' \
            -e '/^.{0,9}tt-ccm.header.end/d')

        "${sed_cmd[@]}" "$file" > "$tmpfile"
        
        if cmp -s "$file" "$tmpfile"; then
            echo "[WARN] No header lines removed from $file" >> "$LOG_FILE"
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
    local lang_mode="$3"
    local block_start="$4"
    local block_end="$5"
    local line_comment="$6"
    local line_end="$7"
    local template_file="$8"

    # Scan file for first commit message before header removal
    local preserved_commit_message
    local line
    line=$(grep -m1 '%ccm_git_commit_message' "$file" || echo "")
    if [[ "$line" =~ %ccm_git_commit_message\":[[:space:]]*\"([^\"]*)\" ]]; then
        # JSON format: "key": "value"
        preserved_commit_message="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_message:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        # Standard format: key: value %
        preserved_commit_message="${BASH_REMATCH[1]}"
    else
        preserved_commit_message=""
    fi
    
    # Extract commit date from header (just the date portion YYYY-MM-DD)
    local preserved_commit_date=""
    line=$(grep -m1 '%ccm_git_commit_date' "$file" || echo "")
    if [[ "$line" =~ %ccm_git_commit_date\":[[:space:]]*\"([^\"]*)\" ]]; then
        preserved_commit_date="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_date:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        preserved_commit_date="${BASH_REMATCH[1]}"
    fi
    # Extract just YYYY-MM-DD from date string
    if [[ "$preserved_commit_date" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        preserved_commit_date="${BASH_REMATCH[1]}"
    fi
    
    # Extract commit author from header
    local preserved_commit_author=""
    line=$(grep -m1 '%ccm_git_commit_author' "$file" || echo "")
    if [[ "$line" =~ %ccm_git_commit_author\":[[:space:]]*\"([^\"]*)\" ]]; then
        preserved_commit_author="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_author:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        preserved_commit_author="${BASH_REMATCH[1]}"
    fi
    
    local history_commit_message
    line=$(grep -m1 '%git_commit_history' "$file" || echo "")
    if [[ "$line" =~ %git_commit_history\":[[:space:]]*\"([^\"]*)\" ]]; then
        # JSON format: "key": "value"
        history_commit_message="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %git_commit_history:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        # Standard format: key: value %
        history_commit_message="${BASH_REMATCH[1]}"
    else
        history_commit_message=""
    fi

    echo "[DEBUG] Found preserved_commit_message='$preserved_commit_message' for $file" >> "$LOG_FILE"
    echo "[DEBUG] Found preserved_commit_date='$preserved_commit_date' for $file" >> "$LOG_FILE"
    echo "[DEBUG] Found preserved_commit_author='$preserved_commit_author' for $file" >> "$LOG_FILE"
    echo "[DEBUG] Found history_commit_message='$history_commit_message' for $file" >> "$LOG_FILE"

    # Only preserve if not "unknown"
    if [ "$preserved_commit_message" = "unknown" ]; then
        echo "[DEBUG] Blanking preserved_commit_message for $file because it is 'unknown'" >> "$LOG_FILE"
        preserved_commit_message=""
    fi
    # If both are present and equal, blank out preserved_commit_message
    if [ -n "$preserved_commit_message" ] && [ -n "$history_commit_message" ] && [ "$preserved_commit_message" = "$history_commit_message" ]; then
        echo "[DEBUG] Blanking preserved_commit_message for $file because it matches history_commit_message" >> "$LOG_FILE"
        preserved_commit_message=""
    fi

    # Remove CCM header
    if [ "${do_gitAF}" = "--force" ]; then
      echo "[INFO] --force specified, skipping header removal" >> "$LOG_FILE"
    else
      remove_ccm_header "$file"
    fi

    # --- File-specific variables ---
    blob_sha=$(git hash-object "$file" 2>/dev/null || echo unknown)
    exec_flag=$(test -x "$file" && echo yes || echo no)
    file_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    modify_date=$(date +"%Y-%m-%d %H:%M:%S")
    file_last_modified=$(stat -c %y "$file" 2>/dev/null | cut -d'.' -f1 || echo unknown)
    file_name=$(basename "$file")
    file_type=$(file --brief --mime-type "$file" 2>/dev/null || echo unknown)
    file_encoding=$(file --brief --mime-encoding "$file" 2>/dev/null || echo unknown)
    file_eol="$(grep -q $'\r\n' "$file" && echo "CRLF" || echo "LF")"
    file_path="$rel_path"

    # Format header with block and line comments
    local current_template="$TEMPLATE_FILE"
    if [ -n "$template_file" ]; then
        current_template="$REPO_ROOT/git-automation/$template_file"
    fi

    tmp_header=$(mktemp)
    cp "$current_template" "$tmp_header"
    
    # Parse template directives
    local template_asis=""
    local history_asis=""
    local commit_history_format=""
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^##TEMPLATE_ASIS ]]; then
            template_asis="yes"
        elif [[ "$line" =~ ^##HISTORY_ASIS ]]; then
            history_asis="yes"
        elif [[ "$line" =~ ^##COMMIT_HISTORY:[[:space:]]*(.*) ]]; then
            commit_history_format="${BASH_REMATCH[1]}"
        fi
    done < "$tmp_header"
    
    echo "[DEBUG] Template directives: template_asis='$template_asis', history_asis='$history_asis', commit_history_format='$commit_history_format'" >> "$LOG_FILE"
    
    # Remove directive lines from template
    sed -i '/^##TEMPLATE_ASIS$/d; /^##HISTORY_ASIS$/d; /^##COMMIT_HISTORY:/d' "$tmp_header"
    
    formatted_header=$(mktemp)
    header_lines=()
    while IFS= read -r line; do
        # Strip trailing whitespace and carriage returns (Windows CRLF compatibility)
        line="${line%$'\r'}"
        header_lines+=("$line")
    done < "$tmp_header"
    {
        for i in "${!header_lines[@]}"; do
            out_line="${header_lines[$i]}"
            # Apply block_start/line_comment/block_end only if NOT template_asis
            if [ "$template_asis" = "yes" ]; then
                # Insert as-is
                echo "$out_line"
            else
                # Prepend block_start and line_comment to first line (no space between)
                if [ "$i" -eq 0 ]; then
                    out_line="${block_start}${line_comment} $out_line"
                else
                    out_line="$line_comment $out_line"
                fi
                # Append block_end to last line
                if [ "$i" -eq $((${#header_lines[@]}-1)) ]; then
                    out_line="$out_line $block_end"
                fi
                # Append line_end if specified
                if [ -n "$line_end" ]; then
                    out_line="$out_line$line_end"
                fi
                echo "$out_line"
            fi
        done
        # Add preserved commit message as a single line after header block
        if [ -n "$preserved_commit_message" ] && [ -n "$commit_history_format" ]; then
            # Use the template-defined format and substitute placeholders
            history_line="${commit_history_format}"
            history_line="${history_line//\$MESSAGE/$preserved_commit_message}"
            history_line="${history_line//\$DATE/$preserved_commit_date}"
            history_line="${history_line//\$AUTHOR/$preserved_commit_author}"
            if [ "$history_asis" = "yes" ]; then
                echo "$history_line"
            else
                echo "${block_start}${line_comment} $history_line $block_end"
            fi
            echo "[DEBUG] Preserved commit message inserted for $file using format: $commit_history_format" >> "$LOG_FILE"
        else
            echo "[DEBUG] No preserved commit message inserted for $file" >> "$LOG_FILE"
        fi
    } > "$formatted_header"

    # Now update all static and commit-bound fields using a single sed block
    sed -i \
        -e "s|%ccm_git_modify_date: .* %|%ccm_git_modify_date: $modify_date %|g" \
        -e "s|%ccm_git_author: .* %|%ccm_git_author: $author %|g" \
        -e "s|%ccm_git_author_email: .* %|%ccm_git_author_email: $author_email %|g" \
        -e "s|%ccm_git_repo: .* %|%ccm_git_repo: $repo %|g" \
        -e "s|%ccm_git_branch: .* %|%ccm_git_branch: $branch %|g" \
        -e "s|%ccm_git_object_id: .* %|%ccm_git_object_id: unknown %|g" \
        -e "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: unknown %|g" \
        -e "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: unknown %|g" \
        -e "s|%ccm_git_commit_message: .* %|%ccm_git_commit_message: unknown %|g" \
        -e "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: unknown %|g" \
        -e "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: unknown %|g" \
        -e "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: unknown %|g" \
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
        -e "s|%ccm_git_language_mode: .* %|%ccm_git_language_mode: $lang_mode %|g" "$formatted_header"

    # Insert header after shebang or pseudo-shebang
    first_line=$(head -n 1 "$file")
    if head -n 1 "$file" | grep -q '^#!'; then
        { head -n 1 "$file"; cat "$formatted_header"; tail -n +2 "$file"; } > "$file.new"
    elif echo "$first_line" | grep -qiE '^(#!|# yaml-language-server:|# *coding[:=]|# *-\*- coding:|<\?xml|<!DOCTYPE html|<\?php)'; then
        { echo "$first_line"; cat "$formatted_header"; tail -n +2 "$file"; } > "$file.new"
    elif [[ "$file" == *.json ]] && echo "$first_line" | grep -q '^{'; then
        { echo "$first_line"; cat "$formatted_header"; tail -n +2 "$file"; } > "$file.new"
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

}

# Build list of files to process
if [ -n "${1-}" ] && [ -f "$1" ]; then
  echo "[DEBUG] Arg1 present and is a file: processing '$1'" >> "$LOG_FILE"
  FILES_TO_PROCESS=("$1")
  GIT_MODE=N
else
    # Read staged files into array (fix: use correct read and git diff command)
    mapfile -d '' -t FILES_TO_PROCESS < <(git diff --cached --name-only -z)
    GIT_MODE=Y
fi

if [ "${2-}" == "--try" ] || [ "$GIT_MODE" == "N" ]; then
  try_mode="--try"
else
  try_mode=""
fi

echo "[DEBUG] try_mode set to '$try_mode'" >> "$LOG_FILE"

for FILE in "${FILES_TO_PROCESS[@]}"; do

  # --- CRITICAL: Never process hook files or git-automation scripts ---
  case "$FILE" in
    git-automation/*.sh|.git/hooks/*)
      echo "[INFO] SAFETY: Skipping $FILE (hook/automation script - never process)" >> "$LOG_FILE"
      continue
      ;;
  esac

  # --- Exclude git-automation folder from processing ---
  if grep -q "tt-hooks.skip-post-commit" "$FILE"; then
    echo "[INFO] Skipping $FILE (contains tt-hooks.skip-post-commit)" >> "$LOG_FILE"
    continue
  fi

  # Skip files in git-automation folder
  if [ "${try_mode}" = "--try" ]; then
    echo "[INFO] --try specified, skipping directory exclusion" >> "$LOG_FILE"
  else
    case "$FILE" in
      git-automation/enhanced-pre-commit.sh|git-automation/enhanced-post-commit.sh)
        echo "[INFO] Skipping $FILE (in git-automation folder)" >> "$LOG_FILE"
        continue
        ;;
    esac 
  fi

    REL_PATH=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then
        echo "[INFO] Skipping $FILE (binary file detected)" >> "$LOG_FILE"
        continue
    fi
    if ! echo "$MIME_INFO" | grep -qiE '^text/|charset='; then
        echo "[INFO] Skipping $FILE (not a text file)" >> "$LOG_FILE"
        continue
    fi

    echo "[INFO] Processing $FILE (relative path: $REL_PATH, mime: $MIME_INFO)" >> "$LOG_FILE"
    
    # --- Enhanced Secret Scanning (per-file) ---
    # Skip secret scanning for example/template/sample files by pattern
    case "$FILE" in
        *.example|*.example.*|*.template|*.template.*|*.sample|*.sample.*|*-example.*|*-template.*|*-sample.*)
            echo "[INFO] Skipping secret scan for $FILE (example/template/sample file)" >> "$LOG_FILE"
            ;;
        *)
            # Check for bypass marker in this file
            if grep -q "tt-secrets.skip\|tt-ggshield.skip" "$FILE" 2>/dev/null; then
                echo "[INFO] Skipping secret scan for $FILE (bypass marker found)" >> "$LOG_FILE"
            else
                # Call secret scanner with this specific file
                if [ -x "$REPO_ROOT/git-automation/enhanced-secrets-pattern-scanner.sh" ]; then
                    if ! "$REPO_ROOT/git-automation/enhanced-secrets-pattern-scanner.sh" "$FILE"; then
                        echo "[ERROR] Secret detected in $FILE, aborting commit" >> "$LOG_FILE"
                        exit 1
                    fi
                fi
            fi
            ;;
    esac
    
    IFS='|' read -r lang_mode block_start block_end line_comment line_end template_file <<< "$(bash "$REPO_ROOT/git-automation/get_language_mode_and_comments.sh" "$FILE")"
    echo "[INFO] Language mode: $lang_mode, block_start: $block_start, block_end: $block_end, line_comment: $line_comment, line_end: $line_end, template_file: $template_file" >> "$LOG_FILE"

    insert_ccm_header "$FILE" "$REL_PATH" "$lang_mode" "$block_start" "$block_end" "$line_comment" "$line_end" "$template_file"
    if [ $? -ne 0 ]; then
        echo "[WARN] Failed to insert CCM header for $FILE, skipping file" >> "$LOG_FILE"
        continue
    fi

    if [ "${try_mode-}" = "--try" ]; then
      echo "[INFO] --try specified, skipping git add command" >> "$LOG_FILE"
    else
        # git add -A
        git add "$FILE"
        echo "[INFO] Added $FILE to git index" >> "$LOG_FILE"
    fi
  
done

echo "Enhanced pre-commit hook finished at $(date)" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"