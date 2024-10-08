#!/bin/sh

# Define variables
URL=$(git config --get remote.origin.url)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
AUTHOR=$(git log -1 --pretty=format:'%an')
AUTHOR_EMAIL=$(git log -1 --pretty=format:'%ae')
ID=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log -1 --pretty=format:'%s')
DATE=$(date +"%Y-%m-%d %H:%M:%S")
REVISION=$(git rev-list --count HEAD)
LAST_COMMIT_DATE=$(git log -1 --pretty=format:'%ci')

# Define the log file using the %TMP% environment variable
#LOG_FILE=".git/hooks/pre-commit.log"
LOG_FILE="$TMP/pre-commit.log"

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

# Get the list of staged files with specified extensions
STAGED_FILES=$(git diff --cached --name-only | grep -E '\.(cmd|bat|sql|ctl|py|sh|bash|zsh|ksh|ps1|psm1|psd1|yaml)$')

# Update the placeholders in each staged file
for FILE in $STAGED_FILES; do
    # Skip files in the git-automation directory
    if [[ "$FILE" == git-automation/* ]]; then
        echo "Skipping file in git-automation directory: $FILE" >> $LOG_FILE
        continue
    fi
    echo "Processing file: $FILE" >> $LOG_FILE

    FILE_LAST_MODIFIED=$(date -r "$FILE" +"%Y-%m-%d %H:%M:%S")
    FILE_TYPE=$(file --mime-type -b "$FILE")
    FILE_ENCODING=$(file -b --mime-encoding "$FILE")
    FILE_EOL=$(detect_eol "$FILE")

    sed -i "s|% ccm_repo: .* %|% ccm_repo: $URL %|g" "$FILE"
    sed -i "s|% ccm_branch: .* %|% ccm_branch: $BRANCH_NAME %|g" "$FILE"
    sed -i "s|% ccm_commit_id: .* %|% ccm_commit_id: $ID %|g" "$FILE"
    sed -i "s|% ccm_commit_count: .* %|% ccm_commit_count: $REVISION %|g" "$FILE"
    sed -i "s|% ccm_object_id: .* %|% ccm_object_id: $FILE:$REVISION %|g" "$FILE" 
    sed -i "s|% ccm_last_commit_author: .* %|% ccm_last_commit_author: $AUTHOR %|g" "$FILE"
    sed -i "s|% ccm_last_commit_email: .* %|% ccm_last_commit_email: $AUTHOR_EMAIL %|g" "$FILE"
    sed -i "s|% ccm_last_commit_message: .* %|% ccm_last_commit_message: $COMMIT_MESSAGE %|g" "$FILE"
    sed -i "s|% ccm_last_commit_date: .* %|% ccm_last_commit_date: $LAST_COMMIT_DATE %|g" "$FILE"
    sed -i "s|% ccm_file_name: .* %|% ccm_file_name: $(basename "$FILE") %|g" "$FILE"
    sed -i "s|% ccm_version: .* %|% ccm_version: $REVISION %|g" "$FILE"
    sed -i "s|% ccm_file_last_modified: .* %|% ccm_file_last_modified: $FILE_LAST_MODIFIED %|g" "$FILE"
    sed -i "s|% ccm_file_type: .* %|% ccm_file_type: $FILE_TYPE %|g" "$FILE"
    sed -i "s|% ccm_file_encoding: .* %|% ccm_file_encoding: $FILE_ENCODING %|g" "$FILE"
    sed -i "s|% ccm_file_eol: .* %|% ccm_file_eol: $FILE_EOL %|g" "$FILE"
    sed -i "s|% ccm_modify_date: .* %|% ccm_modify_date: $DATE %|g" "$FILE"

    # Check if the file was modified
    if git diff --name-only --exit-code "$FILE"; then
        echo "File $FILE was not modified" >> $LOG_FILE 
    else
        echo "File $FILE was modified, adding to staging" >> $LOG_FILE
        # Add the updated file to the staging area
        git add "$FILE"
    fi
done

# End logging
echo "Pre-commit hook finished at $(date)" >> $LOG_FILE
