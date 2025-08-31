#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-31 11:51:03 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/setup-whisper-dev1.sh:63 %
# % ccm_commit_id: c4e2a8f2e016fb9e651719db70eee32449231a16 %
# % ccm_commit_count: 63 %
# % ccm_commit_message: general cleanup, add kitchenowl % ccm_commit_message: unknown % uptimekuma %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-08-31 11:51:01 -0400 %
# % ccm_file_last_modified: 2025-08-31 11:51:03 %
# % ccm_file_name: setup-whisper-dev1.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/setup-whisper-dev1.sh %
# % ccm_blob_sha: 6aa747a6bfe7ad59049d388be06524cc0abe1c55 %
# % ccm_exec: yes %
# % ccm_size: 3524 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euxo pipefail

# Service account (use same as Docker if desired)
SERVICE_USER=${SERVICE_USER:-mpegg-adm}
SERVICE_GROUP=${SERVICE_GROUP:-mpegg-adm}

# Create directory tree
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /srv/dev1/whisper/{data,script}
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /mnt/ai_storage/whisper
if [ ! -L /srv/dev1/whisper/data ]; then
  sudo rm -rf /srv/dev1/whisper/data
  sudo ln -s /mnt/ai_storage/whisper /srv/dev1/whisper/data
fi

# Ensure system dependencies
if ! command -v python3 >/dev/null; then
  echo "python3 is required" >&2; exit 1
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg libsndfile1 || true

# Python venv using system python
if [ ! -d /srv/dev1/whisper/.venv ]; then
  sudo -u "$SERVICE_USER" python3 -m venv /srv/dev1/whisper/.venv
fi

# Install dependencies (server + backend)
sudo -u "$SERVICE_USER" /srv/dev1/whisper/.venv/bin/python -m pip install --upgrade pip setuptools wheel
sudo -u "$SERVICE_USER" /srv/dev1/whisper/.venv/bin/python -m pip install wyoming wyoming-faster-whisper faster-whisper

# Create a simple run script compatible with your home setup
cat <<'RUN' | sudo tee /srv/dev1/whisper/script/run >/dev/null
#!/usr/bin/env bash
set -euo pipefail
# Delegate to the Wyoming Faster Whisper module; pass through all args from systemd ExecStart
exec /srv/dev1/whisper/.venv/bin/python -m wyoming_faster_whisper "$@"
RUN

sudo chmod +x /srv/dev1/whisper/script/run
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" /srv/dev1/whisper

# Remove any stray local module directories that could shadow site-packages
if [ -d /srv/dev1/whisper/wyoming_faster_whisper ]; then
  echo "Removing stray /srv/dev1/whisper/wyoming_faster_whisper to avoid module shadowing"
  sudo rm -rf /srv/dev1/whisper/wyoming_faster_whisper
fi

# Install systemd unit
sudo install -m 0644 /home/mpegg-adm/source/TermiteTowers/infra/systemd/wyoming-faster-whisper-dev1.service /etc/systemd/system/

# Override User/Group via systemd drop-in so we can match Docker service account
sudo install -d -m 0755 /etc/systemd/system/wyoming-faster-whisper-dev1.service.d
cat <<EOF | sudo tee /etc/systemd/system/wyoming-faster-whisper-dev1.service.d/override.conf >/dev/null
[Service]
User=$SERVICE_USER
Group=$SERVICE_GROUP
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now wyoming-faster-whisper-dev1

echo "Whisper service installed and started on tcp://0.0.0.0:10300"
