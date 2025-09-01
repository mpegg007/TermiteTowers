#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-09-01 15:47:13 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/nginx-enable-site.sh:68 %
# % ccm_commit_id: fe785a319b8d06e69d2978b17dc9bb8512161977 %
# % ccm_commit_count: 68 %
# % ccm_commit_message: misc updated %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-09-01 15:47:12 -0400 %
# % ccm_file_last_modified: 2025-09-01 15:47:12 %
# % ccm_file_name: nginx-enable-site.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/nginx-enable-site.sh %
# % ccm_blob_sha: 0a56c39a3e5414fb294d0ea076715e886f2596a7 %
# % ccm_exec: yes %
# % ccm_size: 2156 %
# % ccm_tag:  %
# tt-ccm.header.end

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
sudo install -m 0644 -D "$SRC" "$DEST_AVAIL"

echo "Linking $DEST_AVAIL -> $DEST_ENABLED"
sudo ln -sf "$DEST_AVAIL" "$DEST_ENABLED"

echo "Validating Nginx config"
sudo nginx -t

echo "Reloading Nginx"
sudo systemctl reload nginx

echo "Done: $SITE_NAME enabled."
