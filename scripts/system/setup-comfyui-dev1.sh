#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/system/setup-comfyui-dev1.sh:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 52f0cec5e783c7c6a54cb3b3850528237a8f7691 %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:23 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:23 %
#  %ccm_git_file_name: setup-comfyui-dev1.sh %
#  %ccm_git_path: scripts/system/setup-comfyui-dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5763 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 


set -euxo pipefail

# Service account configuration
SERVICE_USER=${SERVICE_USER:-comfyui}
SERVICE_GROUP=${SERVICE_GROUP:-comfyui}

# Create service account if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating service user: $SERVICE_USER"
    sudo groupadd -f "$SERVICE_GROUP"
    # Create system user with home dir, adding to video/render for GPU and tt-ai-storage instead of 'ai_storage'
    EXTRA_GROUPS="video,render"
    if getent group tt-ai-storage >/dev/null; then
        EXTRA_GROUPS="$EXTRA_GROUPS,tt-ai-storage"
    fi
    sudo useradd -r -g "$SERVICE_GROUP" -G "$EXTRA_GROUPS" -d "/srv/dev1/comfyui" -s /usr/sbin/nologin "$SERVICE_USER"
fi

# Create directory tree
# Base app dir: /srv/dev1/comfyui
# Storage dir:  /mnt/ai_storage/comfyui
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /srv/dev1/comfyui
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /mnt/ai_storage/comfyui
# Subdirectories that should persist or be large
for subdir in models input output user; do
    sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" "/mnt/ai_storage/comfyui/$subdir"
done

# Ensure system dependencies
if ! command -v python3 >/dev/null; then
  echo "python3 is required" >&2; exit 1
fi
sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip git build-essential

# Clone ComfyUI if not present
if [ ! -d /srv/dev1/comfyui/ComfyUI ]; then
    sudo -u "$SERVICE_USER" git clone https://github.com/comfyanonymous/ComfyUI.git /srv/dev1/comfyui/ComfyUI
fi

# Link persistent directories
# model subfolders: checkpoints, vae, clip, unet, etc. usually exist inside models/
# We want /srv/dev1/comfyui/ComfyUI/models -> /mnt/ai_storage/comfyui/models ?
# Or specific subfolders. ComfyUI expects a specific structure inside models. 
# It's safest to map the whole directories if they are empty or new.
for dir in models input output user; do
    TARGET_LINK="/srv/dev1/comfyui/ComfyUI/$dir"
    STORAGE_DIR="/mnt/ai_storage/comfyui/$dir"
    
    # If the target is a real directory and not a symlink, handle it
    if [ -d "$TARGET_LINK" ] && [ ! -L "$TARGET_LINK" ]; then
        # For initial setup, if it's empty, remove it. If likely populated by git clone (like models/checkpoints placeholder), 
        # we might want to merge or just replace.
        # Simple strategy: back it up if not empty, or just assume fresh install.
        # Since this is a setup script, we'll try to be safe but aggressive.
        echo "Replacing default $dir directory with symlink to storage..."
        sudo rm -rf "$TARGET_LINK"
    fi
    
    if [ ! -e "$TARGET_LINK" ]; then
        sudo ln -nsf "$STORAGE_DIR" "$TARGET_LINK"
    fi
done

# Create specific model subdirs in storage if they don't exist, to match structure
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /mnt/ai_storage/comfyui/models/{checkpoints,vae,clip,unet,loras,controlnet}

# Python venv using system python
if [ ! -d /srv/dev1/comfyui/.venv ]; then
  sudo -u "$SERVICE_USER" python3 -m venv /srv/dev1/comfyui/.venv
fi

# Install dependencies
# 1. Upgrade pip
sudo -u "$SERVICE_USER" /srv/dev1/comfyui/.venv/bin/python -m pip install --upgrade pip setuptools wheel

# 1.5. Remove conflicting legacy NVIDIA packages (Fix for runtime library mismatch)
# Ensure we don't have mixed cu11/cu12/cu13 environments which cause 'no kernel image' errors
sudo -u "$SERVICE_USER" /srv/dev1/comfyui/.venv/bin/python -m pip uninstall -y \
    nvidia-cublas-cu11 nvidia-cublas-cu12 \
    nvidia-cuda-cupti-cu11 nvidia-cuda-cupti-cu12 \
    nvidia-cuda-nvrtc-cu11 nvidia-cuda-nvrtc-cu12 \
    nvidia-cuda-runtime-cu11 nvidia-cuda-runtime-cu12 \
    nvidia-cudnn-cu11 nvidia-cudnn-cu12 \
    nvidia-cufft-cu11 nvidia-cufft-cu12 \
    nvidia-cufile-cu12 \
    nvidia-curand-cu11 nvidia-curand-cu12 \
    nvidia-cusolver-cu11 nvidia-cusolver-cu12 \
    nvidia-cusparse-cu11 nvidia-cusparse-cu12 \
    nvidia-cusparselt-cu12 \
    nvidia-nccl-cu11 nvidia-nccl-cu12 \
    nvidia-nvjitlink-cu12 \
    nvidia-nvshmem-cu12 \
    nvidia-nvtx-cu11 nvidia-nvtx-cu12 || true

# 2. Install PyTorch (Updated for RTX 50-series/New Hardware)
# Using nightly build to ensure support for newer CUDA architectures (Blackwell/50-series)
sudo -u "$SERVICE_USER" /srv/dev1/comfyui/.venv/bin/python -m pip install --pre --upgrade --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130

# 3. Install ComfyUI requirements
sudo -u "$SERVICE_USER" /srv/dev1/comfyui/.venv/bin/python -m pip install -r /srv/dev1/comfyui/ComfyUI/requirements.txt

# Create run script
sudo install -d -m 2775 -o "$SERVICE_USER" -g "$SERVICE_GROUP" /srv/dev1/comfyui/script
cat <<'RUN' | sudo tee /srv/dev1/comfyui/script/run >/dev/null
#!/usr/bin/env bash
set -euo pipefail
cd /srv/dev1/comfyui/ComfyUI
# Use the venv python. Port 3830 assigned in wiki/ports.md
exec /srv/dev1/comfyui/.venv/bin/python main.py --listen 0.0.0.0 --port 3830 "$@"
RUN

sudo chmod +x /srv/dev1/comfyui/script/run
sudo chown "$SERVICE_USER":"$SERVICE_GROUP" /srv/dev1/comfyui/script/run

# Create Systemd Unit (Inline since one doesn't exist in repo yet)
cat <<EOF | sudo tee /etc/systemd/system/comfyui-dev1.service >/dev/null
[Unit]
Description=ComfyUI Service (Dev1)
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=/srv/dev1/comfyui/ComfyUI
ExecStart=/srv/dev1/comfyui/script/run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now comfyui-dev1

echo "ComfyUI service installed and started on http://0.0.0.0:3830"



