#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy-www.sh:179 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 247adef559f7f7f3480160e3be95a03f2acb8468 %
#  %ccm_git_commit_id: 5374d00e1d9cc50947a2b000c73308e0263dce3c %
#  %ccm_git_commit_count: 179 %
#  %ccm_git_commit_date: 2026-10-08 20:03:29 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: impl www from prd branch %
#  %ccm_git_modify_date: 2026-10-08 20:03:30 %
#  %ccm_git_file_last_modified: 2026-10-08 19:46:31 %
#  %ccm_git_file_name: deploy-www.sh %
#  %ccm_git_path: scripts/deploy-www.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3289 %
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

# --- Safety guard -----------------------------------------------------------
# /var/www/<name> may now be a symlink into the CI-managed mirror
# (/srv/prd/tt/infra/nginx/www) - see infra/nginx/RELOCATION-PLAN.md and
# scripts/www-relocate-to-srv.sh. `cp -a`/`chown -R` through that link would
# write into the mirror, desync it from git, and the next deploy-prd.yml
# `rsync --delete` would silently wipe the changes. Refuse instead.
for _d in "$DEST_DIR" "$DEST_DIR/../media"; do
  if [[ -L "$_d" ]]; then
    echo "REFUSING: $_d is a symlink -> $(readlink "$_d")" >&2
    echo "  Web content is now served directly from the CI mirror. Publish by" >&2
    echo "  merging dev1 -> prd (deploy-prd.yml rsyncs into /srv/prd/tt)." >&2
    exit 1
  fi
done

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
