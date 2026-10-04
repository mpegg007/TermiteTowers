#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy-www.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 68cb7322456474aaf1ed2471fedf6af77084fee8 %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
#  %ccm_git_file_name: deploy-www.sh %
#  %ccm_git_path: scripts/deploy-www.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1382 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-03-22 mpegg  march updates  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2025-10-30 mpegg  index page, comments  % 
# %git_commit_history: docker updates % 
# %git_commit_history: big update % 


set -euo pipefail

# Deploy chat landing page assets to /var/www/chat
# Usage: ./scripts/deploy-chat.sh [SRC_DIR]
# Default SRC_DIR resolves relative to this script: ../infra/nginx/www/chat

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_SRC_DIR="$SCRIPT_DIR/../infra/nginx/www/chat"
SRC_DIR="${1:-$DEFAULT_SRC_DIR}"
DEST_DIR="/var/www/chat"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory not found: $SRC_DIR" >&2
  exit 1
fi

sudo mkdir -p "$DEST_DIR"
sudo cp -a "$SRC_DIR/." "$DEST_DIR/"

# Set owner if www-data exists; ignore otherwise
if id -u www-data >/dev/null 2>&1; then
  sudo chown -R www-data:www-data "$DEST_DIR"
fi

echo "Chat page deployed to $DEST_DIR"


# now deploy media page assets to relative to chat: ../media

if [[ ! -d "$SRC_DIR/../media" ]]; then
  echo "Source directory not found: $SRC_DIR/../media" >&2
  exit 1
fi

sudo mkdir -p "$DEST_DIR/../media"
sudo cp -a "$SRC_DIR/../media/." "$DEST_DIR/../media/"

# Set owner if www-data exists; ignore otherwise
if id -u www-data >/dev/null 2>&1; then
  sudo chown -R www-data:www-data "$DEST_DIR/../media"
fi

echo "Media page deployed to $DEST_DIR/../media"
