#!/usr/bin/env bash
set -euo pipefail

# Post-commit updater: finalize commit-bound fields and amend the commit.
# Safe defaults: skip on merge or if no HEAD.

URL=$(git config --get remote.origin.url)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
AUTHOR=${GIT_AUTHOR_NAME:-$(git log -1 --pretty=format:'%an')}
AUTHOR_EMAIL=${GIT_AUTHOR_EMAIL:-$(git log -1 --pretty=format:'%ae')}
ID=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log -1 --pretty=format:'%s')
REVISION=$(git rev-list --count HEAD)
COMMIT_DATE=$(git log -1 --pretty=format:'%ci')
COMMIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
DATE=$(date +"%Y-%m-%d %H:%M:%S")

LOG_FILE="${TMPDIR:-/tmp}/post-commit.log"
LOCK_FILE=$(git rev-parse --git-path ccm-post-commit.lock)

# Prevent recursion: if lock exists, skip
if [ -f "$LOCK_FILE" ]; then
  echo "Post-commit: lock present, skipping to avoid recursion" >> "$LOG_FILE"
  exit 0
fi
echo "Post-commit updater started at $(date) for $ID" >> "$LOG_FILE"

# Gather changed paths for the last commit (name-only) and filter known types
git --no-pager diff-tree --no-commit-id --name-only -r -z HEAD | while IFS= read -r -d '' FILE; do
  case "$FILE" in
    *.cmd|*.bat|*.sql|*.ctl|*.py|*.sh|*.bash|*.zsh|*.ksh|*.ps1|*.psm1|*.psd1|*.yaml) ;;
    *) continue ;;
  esac

  # Skip automation directory
  case "$FILE" in
    git-automation/*) echo "Skipping $FILE (automation)" >> "$LOG_FILE"; continue ;;
  esac

  echo "Finalizing: $FILE" >> "$LOG_FILE"

  FILE_LAST_MODIFIED=$(date -r "$FILE" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$DATE")
  FILE_TYPE=$(file --mime-type -b "$FILE" 2>/dev/null || echo unknown)
  FILE_ENCODING=$(file -b --mime-encoding "$FILE" 2>/dev/null || echo unknown)

  # Determine insertion point respecting YAML modeline if present
  INSERT_AT_LINE=1
  case "$FILE" in
    *.yml|*.yaml)
      FIRST_LINE=$(head -n 1 "$FILE" 2>/dev/null || echo "")
      if echo "$FIRST_LINE" | grep -q "yaml-language-server: \$schema="; then
        INSERT_AT_LINE=2
      fi
      ;;
  esac

  # Update fields that depend on the new commit
  sed -i "s|% ccm_commit_id: .* %|% ccm_commit_id: $ID %|g" "$FILE"
  sed -i "s|% ccm_commit_count: .* %|% ccm_commit_count: $REVISION %|g" "$FILE"
  sed -i "s|% ccm_object_id: .* %|% ccm_object_id: $FILE:$REVISION %|g" "$FILE"
  sed -i "s|% ccm_commit_author: .* %|% ccm_commit_author: $AUTHOR %|g" "$FILE"
  sed -i "s|% ccm_commit_email: .* %|% ccm_commit_email: $AUTHOR_EMAIL %|g" "$FILE"
  sed -i "s|% ccm_commit_message: .* %|% ccm_commit_message: $COMMIT_MESSAGE %|g" "$FILE"
  sed -i "s|% ccm_commit_date: .* %|% ccm_commit_date: $COMMIT_DATE %|g" "$FILE"
  if [ -n "$COMMIT_TAG" ]; then
    if grep -q "% ccm_tag:" "$FILE"; then
      sed -i "s|% ccm_tag: .* %|% ccm_tag: $COMMIT_TAG %|g" "$FILE"
    else
      # Only insert if a CCM header exists
      if grep -q "% ccm_modify_date:" "$FILE"; then
        # Choose a reasonable comment prefix based on existing header line
        if grep -q "^# % ccm_modify_date:" "$FILE"; then
          sed -i "${INSERT_AT_LINE}i # % ccm_tag: $COMMIT_TAG %" "$FILE"
        elif grep -q "^// % ccm_modify_date:" "$FILE"; then
          sed -i "${INSERT_AT_LINE}i // % ccm_tag: $COMMIT_TAG %" "$FILE"
        elif grep -q "^-- % ccm_modify_date:" "$FILE"; then
          sed -i "${INSERT_AT_LINE}i -- % ccm_tag: $COMMIT_TAG %" "$FILE"
        elif grep -q "^REM % ccm_modify_date:" "$FILE"; then
          sed -i "${INSERT_AT_LINE}i REM % ccm_tag: $COMMIT_TAG %" "$FILE"
        else
          echo "Skipping ccm_tag insert for block or unknown style: $FILE" >> "$LOG_FILE"
        fi
      fi
    fi
  fi
  sed -i "s|% ccm_repo: .* %|% ccm_repo: $URL %|g" "$FILE"
  sed -i "s|% ccm_branch: .* %|% ccm_branch: $BRANCH_NAME %|g" "$FILE"
  sed -i "s|% ccm_file_name: .* %|% ccm_file_name: $(basename "$FILE") %|g" "$FILE"
  sed -i "s|% ccm_file_last_modified: .* %|% ccm_file_last_modified: $FILE_LAST_MODIFIED %|g" "$FILE"
  sed -i "s|% ccm_file_type: .* %|% ccm_file_type: $FILE_TYPE %|g" "$FILE"
  sed -i "s|% ccm_file_encoding: .* %|% ccm_file_encoding: $FILE_ENCODING %|g" "$FILE"
  sed -i "s|% ccm_modify_date: .* %|% ccm_modify_date: $DATE %|g" "$FILE"
  # Ensure ccm_tag line exists (blank if not tagged yet)
  if ! grep -q "% ccm_tag:" "$FILE"; then
    if grep -q "^# % ccm_modify_date:" "$FILE"; then
      sed -i "${INSERT_AT_LINE}i # % ccm_tag:  %" "$FILE"
    elif grep -q "^// % ccm_modify_date:" "$FILE"; then
      sed -i "${INSERT_AT_LINE}i // % ccm_tag:  %" "$FILE"
    elif grep -q "^-- % ccm_modify_date:" "$FILE"; then
      sed -i "${INSERT_AT_LINE}i -- % ccm_tag:  %" "$FILE"
    elif grep -q "^REM % ccm_modify_date:" "$FILE"; then
      sed -i "${INSERT_AT_LINE}i REM % ccm_tag:  %" "$FILE"
    fi
  fi
done

# If there are changes, amend the commit (no edit to message). Avoid recursion.
if ! git diff --quiet; then
  git add -A
  # Create lock and ensure cleanup
  echo $$ > "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT
  # Safe amend: avoid if behind upstream (to not rewrite shared history)
  AHEAD_BEHIND=$(git rev-list --left-right --count @{u}...HEAD 2>/dev/null || echo "")
  if [ -n "$AHEAD_BEHIND" ]; then
    AHEAD=$(echo "$AHEAD_BEHIND" | awk '{print $2}')
    BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
  else
    AHEAD=0; BEHIND=0
  fi
  if [ "$BEHIND" = "0" ]; then
    # Amend without running hooks again
    git -c core.hooksPath=/dev/null commit --amend --no-edit
  else
    echo "Skipping amend: branch is behind upstream (would rewrite history)" >> "$LOG_FILE"
  fi
  echo "Amended commit $ID with finalized CCM fields" >> "$LOG_FILE"
else
  echo "No final CCM updates needed" >> "$LOG_FILE"
fi

echo "Post-commit updater finished at $(date)" >> "$LOG_FILE"