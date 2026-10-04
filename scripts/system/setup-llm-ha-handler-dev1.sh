#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-31 11:51:03 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/setup-llm-ha-handler-dev1.sh:63 %
# % ccm_commit_id: c4e2a8f2e016fb9e651719db70eee32449231a16 %
# % ccm_commit_count: 63 %
# % ccm_commit_message: general cleanup, add kitchenowl % ccm_commit_message: unknown % uptimekuma %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-08-31 11:51:01 -0400 %
# % ccm_file_last_modified: 2025-08-31 11:51:03 %
# % ccm_file_name: setup-llm-ha-handler-dev1.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/setup-llm-ha-handler-dev1.sh %
# % ccm_blob_sha: ca89e85ec73b522b0282ad65aa91b4ec365556f3 %
# % ccm_exec: yes %
# % ccm_size: 1570 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euxo pipefail

SERVICE_USER=${SERVICE_USER:-mpegg-adm}
SERVICE_GROUP=${SERVICE_GROUP:-mpegg-adm}

# Install systemd unit
sudo install -m 0644 /home/mpegg-adm/source/TermiteTowers/infra/systemd/llm-ha-handler-dev1.service /etc/systemd/system/

# Override user/group
sudo install -d -m 0755 /etc/systemd/system/llm-ha-handler-dev1.service.d
cat <<EOF | sudo tee /etc/systemd/system/llm-ha-handler-dev1.service.d/override.conf >/dev/null
[Service]
User=$SERVICE_USER
Group=$SERVICE_GROUP
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now llm-ha-handler-dev1

echo "LLM Home Assistant Handler service installed and started."
