#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 733f3bff13603c10f12c453198217e29a393623a %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-10-12 10:23:19 %
#  %ccm_git_file_last_modified: 2025-10-12 10:23:19 %
#  %ccm_git_file_name: install_kea.sh %
#  %ccm_git_path: infra/dhcp/scripts/install_kea.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1713 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: #  %ccm_git_commit_message: unknown % 
# %git_commit_history: #  %ccm_git_commit_message: testing hooks again % 
# %git_commit_history: service updates % 

# DHCP KEA Install Script
# Installs KEA DHCP service on a Debian-based system

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/kea-install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Starting KEA DHCP installation..."
# Update package list and install dependencies
echo "Updating package list..."
sudo apt-get update
echo "Installing dependencies..."

sudo dpkg -i isc-kea-dhcp4_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-common_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-hook-libpgsql_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-pgsql_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-ctrl-agent_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-dhcp6_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-hooks_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-dhcp-ddns_3.0.1-isc20250909094157_amd64.deb
sudo dpkg -i isc-kea-admin_3.0.1-isc20250909094157_amd64.deb




# some i forget work




# Enable and start KEA services
echo "Enabling and starting KEA services..."
sudo systemctl enable kea-dhcp4
sudo systemctl start kea-dhcp4
sudo systemctl enable kea-ctrl-agent
sudo systemctl start kea-ctrl-agent
# Verify installation
echo "Verifying KEA installation..."
if systemctl is-active --quiet kea-dhcp4 && systemctl is-active --quiet kea-ctrl-agent; then
    echo "KEA DHCP installation completed successfully!"
else
    echo "KEA DHCP installation failed. Please check the log at $LOG_FILE for details."
    exit 1
fi