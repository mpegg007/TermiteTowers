#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-31 12:10:53 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/deploy-chat.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-31 12:10:53 %
# % ccm_file_name: deploy-chat.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/deploy-chat.sh %
# % ccm_blob_sha: 77c108485904adf32db26901507d8ffb80c6ad38 %
# % ccm_exec: yes %
# % ccm_size: 1575 %
# % ccm_tag:  %
# tt-ccm.header.end

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
