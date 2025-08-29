#!/usr/bin/env bash

# % ccm_modify_date: 2024-10-07 20:10:56 %
# % ccm_author: mpegg %
# % version: 23 %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: git-automation/update-keywords.sh:23 %
# % ccm_commit_id: dbaa495ea5fbbb2a2f55cea4e3491bace9eec020 %
# % ccm_commit_count: 23 %
# % ccm_last_commit_message: exclude update_keywords.py from hook %
# % ccm_last_commit_author: Matthew Pegg %
# % ccm_last_commit_date: 2024-10-07 19:52:23 -0400 %
# % ccm_file_last_modified: 2024-10-07 20:10:41 %
# % ccm_file_name: update-keywords.sh %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %

# Define variables
URL=$(git config --get remote.origin.url)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
# Prefer the committer performing this commit
AUTHOR=${GIT_AUTHOR_NAME:-$(git config --get user.name)}
AUTHOR_EMAIL=${GIT_AUTHOR_EMAIL:-$(git config --get user.email)}
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# Define the log file (use TMPDIR if set, else /tmp)
#LOG_FILE=".git/hooks/pre-commit.log"
LOG_FILE="${TMPDIR:-/tmp}/pre-commit.log"

# Function to detect EOL marker
detect_eol() {
    local file=$1
    if grep -q $'\r\n' "$file"; then
        echo "CRLF"
    elif grep -q $'\n' "$file"; then
        echo "LF"
    elif grep -q $'\r' "$file"; then
        echo "CR"
    else
        echo "Unknown"
    fi
}

# Start logging
echo "Pre-commit hook started at $(date)" >> $LOG_FILE

# Update the placeholders in each staged file (NUL-safe handling for spaces)
while IFS= read -r -d '' FILE; do
    # Skip files in the git-automation directory
    case "$FILE" in
        git-automation/*)
            echo "Skipping file in git-automation directory: $FILE" >> "$LOG_FILE"
            continue
            ;;
    esac

    # Repo-relative path for filters and insertion
    REL_PATH=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")

    # Deny-list common generated/vendor paths
    case "$REL_PATH" in
        vendor/*|build/*|dist/*|node_modules/*|.venv/*|venv/*|.tox/*|.cache/*)
            echo "Skipping excluded path: $REL_PATH" >> "$LOG_FILE"
            continue
            ;;
    esac

    # Treat only text files; skip binary
    MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
    if echo "$MIME_INFO" | grep -qi 'charset=binary'; then
        echo "Skipping binary file: $REL_PATH ($MIME_INFO)" >> "$LOG_FILE"
        continue
    fi
    if ! echo "$MIME_INFO" | grep -qiE '^text/|charset='; then
        echo "Skipping non-text mime: $REL_PATH ($MIME_INFO)" >> "$LOG_FILE"
        continue
    fi

    # Auto-insert a minimal header at top if missing (hash-style comments)
    if ! grep -qE '^[[:space:]]*# % ccm_' -- "$FILE"; then
        case "$REL_PATH" in
            *.sh|*.bash|*.zsh|*.ksh|*.py|*.yaml|*.yml|*.ps1|*.psm1|*.psd1)
                FILE_EOL=$(detect_eol "$FILE")
                TMP=$(mktemp)
                {
                  echo "# % ccm_modify_date: 1970-01-01 00:00:00 %"
                  echo "# % ccm_author: unknown %"
                  echo "# % ccm_author_email: unknown %"
                  echo "# % ccm_repo: $URL %"
                  echo "# % ccm_branch: $BRANCH_NAME %"
                  echo "# % ccm_object_id: $REL_PATH:0 %"
                  echo "# % ccm_commit_id: unknown %"
                  echo "# % ccm_commit_count: 0 %"
                  echo "# % ccm_commit_message: unknown %"
                  echo "# % ccm_commit_author: unknown %"
                  echo "# % ccm_commit_email: unknown %"
                  echo "# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %"
                  echo "# % ccm_file_last_modified: 1970-01-01 00:00:00 %"
                  echo "# % ccm_file_name: $(basename "$FILE") %"
                  echo "# % ccm_file_type: text/plain %"
                  echo "# % ccm_file_encoding: us-ascii %"
                  echo "# % ccm_file_eol: $FILE_EOL %"
                  echo "# % ccm_path: $REL_PATH %"
                  echo "# % ccm_blob_sha: unknown %"
                  echo "# % ccm_exec: no %"
                  echo "# % ccm_size: 0 %"
                  echo "# % ccm_tag:  %"
                  echo
                  cat "$FILE"
                } > "$TMP"
                mv "$TMP" "$FILE"
                ;;
            *)
                echo "No header and unsupported comment style for: $REL_PATH; skipping insert" >> "$LOG_FILE"
                continue
                ;;
        esac
    fi

    echo "Processing file: $FILE" >> $LOG_FILE

        FILE_LAST_MODIFIED=$(date -r "$FILE" +"%Y-%m-%d %H:%M:%S")
    FILE_TYPE=$(file --mime-type -b "$FILE")
    FILE_ENCODING=$(file -b --mime-encoding "$FILE")
    FILE_EOL=$(detect_eol "$FILE")

    # Repo-relative path already computed as REL_PATH
        # Staged blob SHA for this path (index state)
        BLOB_SHA=$(git rev-parse ":$REL_PATH" 2>/dev/null || echo unknown)
        # Executable bit from index (100755 vs 100644)
        FILE_MODE=$(git ls-files --stage -- "$REL_PATH" 2>/dev/null | awk '{print $1}')
        if [[ "$FILE_MODE" == 100755 ]]; then EXEC_FLAG=yes; else EXEC_FLAG=no; fi
        # File size (working tree, good proxy for staged for text files)
        FILE_SIZE=$(stat -c%s "$FILE" 2>/dev/null || echo 0)

    sed -i "s|% ccm_repo: .* %|% ccm_repo: $URL %|g" "$FILE"
    sed -i "s|% ccm_branch: .* %|% ccm_branch: $BRANCH_NAME %|g" "$FILE"
    sed -i "s|% ccm_author: .* %|% ccm_author: $AUTHOR %|g" "$FILE"
    sed -i "s|% ccm_author_email: .* %|% ccm_author_email: $AUTHOR_EMAIL %|g" "$FILE"
    sed -i "s|% ccm_file_name: .* %|% ccm_file_name: $(basename "$FILE") %|g" "$FILE"
    # Remove deprecated redundant fields if present
    sed -i "/% version: .* %/d" "$FILE"
    sed -i "/% ccm_version: .* %/d" "$FILE"
    sed -i "s|% ccm_file_last_modified: .* %|% ccm_file_last_modified: $FILE_LAST_MODIFIED %|g" "$FILE"
    sed -i "s|% ccm_file_type: .* %|% ccm_file_type: $FILE_TYPE %|g" "$FILE"
    sed -i "s|% ccm_file_encoding: .* %|% ccm_file_encoding: $FILE_ENCODING %|g" "$FILE"
    sed -i "s|% ccm_file_eol: .* %|% ccm_file_eol: $FILE_EOL %|g" "$FILE"
    sed -i "s|% ccm_modify_date: .* %|% ccm_modify_date: $DATE %|g" "$FILE"

        # Extra reliable fields
        sed -i "s|% ccm_path: .* %|% ccm_path: $REL_PATH %|g" "$FILE"
        sed -i "s|% ccm_blob_sha: .* %|% ccm_blob_sha: $BLOB_SHA %|g" "$FILE"
        sed -i "s|% ccm_exec: .* %|% ccm_exec: $EXEC_FLAG %|g" "$FILE"
        sed -i "s|% ccm_size: .* %|% ccm_size: $FILE_SIZE %|g" "$FILE"

    # Check if the file was modified
    if git diff --name-only --exit-code "$FILE"; then
        echo "File $FILE was not modified" >> $LOG_FILE 
    else
        echo "File $FILE was modified, adding to staging" >> $LOG_FILE
        # Add the updated file to the staging area
        git add "$FILE"
    fi
done < <(git diff --cached --name-only -z)

# End logging
echo "Pre-commit hook finished at $(date)" >> $LOG_FILE
