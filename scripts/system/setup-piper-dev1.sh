#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-31 11:51:03 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/setup-piper-dev1.sh:63 %
# % ccm_commit_id: c4e2a8f2e016fb9e651719db70eee32449231a16 %
# % ccm_commit_count: 63 %
# % ccm_commit_message: general cleanup, add kitchenowl % ccm_commit_message: unknown % uptimekuma %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-08-31 11:51:01 -0400 %
# % ccm_file_last_modified: 2025-08-31 11:51:03 %
# % ccm_file_name: setup-piper-dev1.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/setup-piper-dev1.sh %
# % ccm_blob_sha: 38c802d58a00a7d5cdee96bdec1efcd5b1b30b10 %
# % ccm_exec: yes %
# % ccm_size: 3244 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euxo pipefail

# Service account (use same as Docker if desired)
SERVICE_USER=${SERVICE_USER:-mpegg-adm}
SERVICE_GROUP=${SERVICE_GROUP:-mpegg-adm}

# Create directory tree
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /srv/dev1/piper/{data,script}
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /mnt/ai_storage/piper
if [ ! -L /srv/dev1/piper/data ]; then
  sudo rm -rf /srv/dev1/piper/data
  sudo ln -s /mnt/ai_storage/piper /srv/dev1/piper/data
fi

# Python venv using system python
if [ ! -d /srv/dev1/piper/.venv ]; then
  sudo -u "$SERVICE_USER" python3 -m venv /srv/dev1/piper/.venv
fi

# Install dependencies (wyoming-piper)
sudo -u "$SERVICE_USER" /srv/dev1/piper/.venv/bin/python -m pip install --upgrade pip
sudo -u "$SERVICE_USER" /srv/dev1/piper/.venv/bin/python -m pip install wyoming-piper

# Download Piper binary if not present (lightweight helper)
if [ ! -x /srv/dev1/piper/piper ]; then
  sudo -u mpegg-adm mkdir -p /srv/dev1/piper
  # Placeholder: user-provided binary path preferred; else attempt to fetch latest prebuilt
  echo "Please place the Piper binary at /srv/dev1/piper/piper (chmod +x)." >&2
fi

# Create a simple run script compatible with your home setup
cat <<'RUN' | sudo tee /srv/dev1/piper/script/run >/dev/null
#!/usr/bin/env bash
set -euo pipefail
# Delegate to wyoming-piper with system paths
DATA_DIR="${WYOMING_PIPER_DATA:-/srv/dev1/piper/data}"
exec /srv/dev1/piper/.venv/bin/python -m wyoming_piper \
  --piper /srv/dev1/piper/piper \
  --voice en_US-lessac-medium \
  --uri tcp://0.0.0.0:10200 \
  --data-dir "$DATA_DIR" \
  --download-dir "$DATA_DIR"
RUN

sudo chmod +x /srv/dev1/piper/script/run
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" /srv/dev1/piper

# Install systemd unit
sudo install -m 0644 /home/mpegg-adm/source/TermiteTowers/infra/systemd/wyoming-piper-dev1.service /etc/systemd/system/

# Override User/Group via systemd drop-in so we can match Docker service account
sudo install -d -m 0755 /etc/systemd/system/wyoming-piper-dev1.service.d
cat <<EOF | sudo tee /etc/systemd/system/wyoming-piper-dev1.service.d/override.conf >/dev/null
[Service]
User=$SERVICE_USER
Group=$SERVICE_GROUP
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now wyoming-piper-dev1

echo "Piper TTS service installed and started on tcp://0.0.0.0:10200"
