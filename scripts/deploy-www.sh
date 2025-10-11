#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
#  %ccm_git_branch: main %
#  %ccm_git_object_id: scripts/deploy-www.sh:97 %
#  %ccm_git_author: CCM Maintainer %
#  %ccm_git_author_email: ccm@test %
#  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
#  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
#  %ccm_git_commit_count: 97 %
#  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: big update %
#  %ccm_git_modify_date: 2025-08-29 07:37:53 %
#  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
#  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_language_mode:  %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 659 %
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
