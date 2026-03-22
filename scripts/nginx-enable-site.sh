#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/nginx-enable-site.sh:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0f7cdf18efd331a79341c7ec6682f7b82707fa2b %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:23 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:23 %
#  %ccm_git_file_name: nginx-enable-site.sh %
#  %ccm_git_path: scripts/nginx-enable-site.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1384 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2025-10-29 mpegg  docker updates  % 


set -euo pipefail

# Enable an Nginx site using a source config file from the repo.
# This installs the config into /etc/nginx/sites-available without a .conf suffix
# to align with the host's convention, creates/updates the sites-enabled symlink,
# validates Nginx config, and reloads Nginx.
#
# Usage:
#   ./scripts/nginx-enable-site.sh /path/to/source.conf [site-name]
# Example:
#   ./scripts/nginx-enable-site.sh \
#     /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/kuma.conf
#   ./scripts/nginx-enable-site.sh /path/to/kitchenowl.conf kitchenowl

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/source.conf [site-name]" >&2
  exit 2
fi

SRC="$1"
if [[ ! -f "$SRC" ]]; then
  echo "Source file not found: $SRC" >&2
  exit 1
fi

SRC_BASE="$(basename "$SRC")"
BASE_NO_EXT="${SRC_BASE%.*}"
SITE_NAME="${2:-$BASE_NO_EXT}"

DEST_AVAIL="/etc/nginx/sites-available/$SITE_NAME"
DEST_ENABLED="/etc/nginx/sites-enabled/$SITE_NAME"

echo "Installing $SRC -> $DEST_AVAIL"
## sudo install -m 0644 -D "$SRC" "$DEST_AVAIL"
sudo ln -sf "$(realpath "$SRC")" "$DEST_AVAIL"

echo "Linking $DEST_AVAIL -> $DEST_ENABLED"
sudo ln -sf "$DEST_AVAIL" "$DEST_ENABLED"

echo "Validating Nginx config"
sudo nginx -t

echo "Reloading Nginx"
sudo systemctl reload nginx

echo "Done: $SITE_NAME enabled."
