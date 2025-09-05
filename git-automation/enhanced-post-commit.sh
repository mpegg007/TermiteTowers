#!/usr/bin/env bash

set -euo pipefail

# Post-commit updater: finalize commit-bound fields and amend the commit.
# Safe defaults: skip on merge or if no HEAD.


URL_RAW=$(git config --get remote.origin.url)
URL_SAFE=$(echo "$URL_RAW" | sed 's/%/%%/g')
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
AUTHOR=${GIT_AUTHOR_NAME:-$(git log -1 --pretty=format:'%an')}
AUTHOR_EMAIL=${GIT_AUTHOR_EMAIL:-$(git log -1 --pretty=format:'%ae')}
ID=$(git rev-parse HEAD)
COMMIT_MESSAGE_RAW=$(git log -1 --pretty=format:'%s')
COMMIT_MESSAGE_SAFE=$(echo "$COMMIT_MESSAGE_RAW" | tr -d '\r\n' | cut -c1-100 | sed 's/%/%%/g')
REVISION=$(git rev-list --count HEAD)
COMMIT_DATE=$(git log -1 --pretty=format:'%ci')
COMMIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
DATE=$(date +"%Y-%m-%d %H:%M:%S")

LOG_FILE="$REPO_ROOT/git-automation/enhanced-hooks.log"
LOCK_FILE=$(git rev-parse --git-path ccm-post-commit.lock)

# Prevent recursion: if lock exists, skip
if [ -f "$LOCK_FILE" ]; then
  echo "Post-commit: lock present, skipping to avoid recursion" >> "$LOG_FILE"
  exit 0
fi
echo "Post-commit updater started at $(date) for $ID" >> "$LOG_FILE"


# Only operate on changed files with CCM header, skip binary
git --no-pager diff-tree --no-commit-id --name-only -r -z HEAD | while IFS= read -r -d '' FILE; do
  # Skip automation directory
  case "$FILE" in
    git-automation/*|*/git-automation/*) continue ;;
  esac
  # Only process files with CCM header
  if ! grep -qE '%ccm_git_[a-z_]+: .* %' "$FILE"; then continue; fi
  # Skip binary files
  MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
  if echo "$MIME_INFO" | grep -qi 'charset=binary'; then continue; fi
  # Update only commit-bound fields
  sed -i "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: $ID %|g" "$FILE"
  sed -i "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: $REVISION %|g" "$FILE"
  sed -i "s|%git_commit_history: .* %|%ccm_git_commit_message: $COMMIT_MESSAGE_SAFE %|g" "$FILE"
  sed -i "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: $AUTHOR %|g" "$FILE"
  sed -i "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: $AUTHOR_EMAIL %|g" "$FILE"
  sed -i "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: $COMMIT_DATE %|g" "$FILE"
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