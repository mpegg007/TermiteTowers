#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_modify_date: 2025-09-06 09:41:53 %
#  %ccm_git_author:  %
#  %ccm_git_author_email:  %
#  %ccm_git_repo:  %
#  %ccm_git_branch:  %
#  %ccm_git_object_id: :0 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_file_last_modified:  %
#  %ccm_git_file_name:  %
#  %ccm_git_file_type:  %
#  %ccm_git_file_encoding:  %
#  %ccm_git_file_eol:  %
#  %ccm_git_path:  %
#  %ccm_git_blob_sha: 5c16c9c03ec02d69389c7eabc0e218d99b39492c %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1178 %
#  %ccm_git_tag:  %
#  %ccm_git_language_mode: shellscript %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 


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

if [[ ! -d "$SRC_DIR/..media" ]]; then
  echo "Source directory not found: $SRC_DIR/..media" >&2
  exit 1
fi

sudo mkdir -p "$DEST_DIR/..media"
sudo cp -a "$SRC_DIR/..media/." "$DEST_DIR/..media/"

# Set owner if www-data exists; ignore otherwise
if id -u www-data >/dev/null 2>&1; then
  sudo chown -R www-data:www-data "$DEST_DIR/..media"
fi

echo "Media page deployed to $DEST_DIR/..media"
