#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 094d218cc2360431950ce211d678ac18c7e6253c %
#  %ccm_git_commit_id: 9a5d759366246b925a62863adec0b1df8cc2d5b1 %
#  %ccm_git_commit_count: 127 %
#  %ccm_git_commit_date: 2025-12-18 21:32:12 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-12-20 17:42:37 %
#  %ccm_git_file_last_modified: 2025-12-20 17:39:35 %
#  %ccm_git_file_name: update-ccm-header.sh %
#  %ccm_git_path: git-automation/update-ccm-header.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4853 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

set -euo pipefail

# update-ccm-header.sh
# Updates CCM header variables in a file based on the most recent git commit (HEAD)
# and current file status.

if [ -z "${1-}" ]; then
    echo "Usage: $0 <file>"
    exit 1
fi

FILE="$1"
if [ ! -f "$FILE" ]; then
    echo "Error: File '$FILE' not found."
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

# --- Git/Commit Info (from HEAD) ---
ID=$(git rev-parse HEAD)
REVISION=$(git rev-list --count HEAD)
COMMIT_MESSAGE_RAW=$(git log -1 --pretty=format:'%s')
COMMIT_MESSAGE_SAFE=$(echo "$COMMIT_MESSAGE_RAW" | tr -d '\r\n' | cut -c1-100 | sed 's/%/%%/g')
COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an')
COMMIT_EMAIL=$(git log -1 --pretty=format:'%ae')
COMMIT_DATE=$(git log -1 --pretty=format:'%ci')
BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO="$REPO_NAME"

# --- Current User Info ---
CURRENT_USER=$(git config user.name)
CURRENT_EMAIL=$(git config user.email)

# --- File Info ---
blob_sha=$(git hash-object "$FILE" 2>/dev/null || echo unknown)
exec_flag=$(test -x "$FILE" && echo yes || echo no)
file_size=$(stat -c%s "$FILE" 2>/dev/null || echo 0)
modify_date=$(date +"%Y-%m-%d %H:%M:%S")
file_last_modified=$(stat -c %y "$FILE" 2>/dev/null | cut -d'.' -f1 || echo unknown)
file_name=$(basename "$FILE")
file_type=$(file --brief --mime-type "$FILE" 2>/dev/null || echo unknown)
file_encoding=$(file --brief --mime-encoding "$FILE" 2>/dev/null || echo unknown)
file_eol="$(grep -q $'\r\n' "$FILE" && echo "CRLF" || echo "LF")"
file_path=$(git ls-files --full-name -- "$FILE" 2>/dev/null || echo "$FILE")

# --- Language Mode ---
lang_mode=""
if [ -x "$REPO_ROOT/git-automation/get_language_mode_and_comments.sh" ]; then
    # The helper returns: lang_mode|block_start|block_end|line_comment|line_end|template_file
    IFS='|' read -r lang_mode _ _ _ _ _ <<< "$(bash "$REPO_ROOT/git-automation/get_language_mode_and_comments.sh" "$FILE")"
fi

echo "Updating CCM header in $FILE..."
echo "  Commit: $ID ($COMMIT_DATE)"
echo "  User: $CURRENT_USER"

# --- Update Command ---
# Use sed range to only update lines between the header start and end markers
START_MARKER="TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start"
END_MARKER="TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end"

sed -i "/$START_MARKER/,/$END_MARKER/ {
    s|%ccm_git_repo: .* %|%ccm_git_repo: $REPO %|g
    s|%ccm_git_branch: .* %|%ccm_git_branch: $BRANCH %|g
    s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: $ID %|g
    s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: $REVISION %|g
    s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: $COMMIT_DATE %|g
    s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: $COMMIT_AUTHOR %|g
    s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: $COMMIT_EMAIL %|g
    s|%ccm_git_commit_message: .* %|%ccm_git_commit_message: $COMMIT_MESSAGE_SAFE %|g
    s|%ccm_git_author: .* %|%ccm_git_author: $CURRENT_USER %|g
    s|%ccm_git_author_email: .* %|%ccm_git_author_email: $CURRENT_EMAIL %|g
    s|%ccm_git_modify_date: .* %|%ccm_git_modify_date: $modify_date %|g
    s|%ccm_git_file_last_modified: .* %|%ccm_git_file_last_modified: $file_last_modified %|g
    s|%ccm_git_file_name: .* %|%ccm_git_file_name: $file_name %|g
    s|%ccm_git_file_type: .* %|%ccm_git_file_type: $file_type %|g
    s|%ccm_git_file_encoding: .* %|%ccm_git_file_encoding: $file_encoding %|g
    s|%ccm_git_file_eol: .* %|%ccm_git_file_eol: $file_eol %|g
    s|%ccm_git_path: .* %|%ccm_git_path: $file_path %|g
    s|%ccm_git_blob_sha: .* %|%ccm_git_blob_sha: $blob_sha %|g
    s|%ccm_git_exec: .* %|%ccm_git_exec: $exec_flag %|g
    s|%ccm_git_size: .* %|%ccm_git_size: $file_size %|g
    s|%ccm_git_language_mode: .* %|%ccm_git_language_mode: $lang_mode %|g
}" "$FILE"

echo "Done."
