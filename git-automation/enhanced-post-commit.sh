#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: git-automation/enhanced-post-commit.sh:85 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 818b10f80f16e03e7862112837844d98e3d5cff1 %
#  %ccm_git_commit_id: 6ed8d9d5fb6be216e7e0f9c5e931d0b5364b8a67 %
#  %ccm_git_commit_count: 85 %
#  %ccm_git_commit_date: 2025-09-06 12:09:11 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: git-automation cleanup %
#  %ccm_git_modify_date: 2025-09-06 12:02:06 %
#  %ccm_git_file_last_modified: 2025-09-06 11:52:11 %
#  %ccm_git_file_name: enhanced-post-commit.sh %
#  %ccm_git_path: git-automation/enhanced-post-commit.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10950 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

set -euo pipefail

# Post-commit updater: finalize commit-bound fields and amend the commit.
# Safe defaults: skip on merge or if no HEAD.

REPO_ROOT=$(git rev-parse --show-toplevel)

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
if [ -n "${1-}" ] && [ -f "$1" ]; then
  echo "[DEBUG] Arg1 present and is a file: processing '$1'" >> "$LOG_FILE"
  FILES_TO_PROCESS=("$1")
else
  if [ -n "${1-}" ]; then
    echo "[DEBUG] Arg1 present but is NOT a file ('$1'), defaulting to staged files" >> "$LOG_FILE"
  else
    echo "[DEBUG] No arg1: staged files mode" >> "$LOG_FILE"
  fi
  # Fix: use mapfile for proper array population
  mapfile -d '' -t FILES_TO_PROCESS < <(git --no-pager diff-tree --no-commit-id --name-only -r -z HEAD)
fi

echo "[DEBUG] FILES_TO_PROCESS: ${FILES_TO_PROCESS[*]}" >> "$LOG_FILE"

for FILE in "${FILES_TO_PROCESS[@]}"; do
  echo "[DEBUG] Considering file: $FILE" >> "$LOG_FILE"
  # Only process files with CCM header
  if ! grep -qE '%ccm_git_.*: .* %' "$FILE"; then
    echo "[DEBUG] Skipping $FILE: no CCM header found" >> "$LOG_FILE"
    continue
  fi
  # Skip binary files
  MIME_INFO=$(file --mime -b "$FILE" 2>/dev/null || echo '')
  if echo "$MIME_INFO" | grep -qi 'charset=binary'; then
    echo "[DEBUG] Skipping $FILE: binary file detected ($MIME_INFO)" >> "$LOG_FILE"
    continue
  fi

  echo "[DEBUG] Updating CCM fields in $FILE" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_id: $ID" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_count: $REVISION" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_object_id: $FILE:$REVISION" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_message (-> %ccm_git_commit_message): $COMMIT_MESSAGE_SAFE" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_author: $AUTHOR" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_email: $AUTHOR_EMAIL" >> "$LOG_FILE"
  echo "[DEBUG] %ccm_git_commit_date: $COMMIT_DATE" >> "$LOG_FILE"

  sed -i "s|%ccm_git_commit_id: 6ed8d9d5fb6be216e7e0f9c5e931d0b5364b8a67 %|g" "$FILE"
  sed -i "s|%ccm_git_commit_count: 85 %|g" "$FILE"
  sed -i "s|%ccm_git_object_id: git-automation/enhanced-post-commit.sh:85 %|g" "$FILE"
  sed -i "s|%ccm_git_commit_message: git-automation cleanup %|g" "$FILE"
  sed -i "s|%ccm_git_commit_author: mpegg %|g" "$FILE"
  sed -i "s|%ccm_git_commit_email: mpegg@hotmail.com %|g" "$FILE"
  sed -i "s|%ccm_git_commit_date: 2025-09-06 12:09:11 -0400 %|g" "$FILE"
done

# If there are changes, amend the commit (no edit to message). Avoid recursion.
if ! git diff --quiet; then
  if [ "${2-}" = "--try" ]; then
    echo "[INFO] --try specified, skipping git add command" >> "$LOG_FILE"
  else
    git add -A
  fi
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
    if [ "${2-}" == "--try" ]; then
      echo "[INFO] --try specified, skipping git amend command" >> "$LOG_FILE"
    else
      git -c core.hooksPath=/dev/null commit --amend --no-edit
    fi
  else
    echo "Skipping amend: branch is behind upstream (would rewrite history)" >> "$LOG_FILE"
  fi
  echo "Amended commit $ID with finalized CCM fields" >> "$LOG_FILE"
else
  echo "No final CCM updates needed" >> "$LOG_FILE"
fi

echo "Post-commit updater finished at $(date)" >> "$LOG_FILE"