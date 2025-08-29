# 1. Create service account
sudo useradd --system --no-create-home --shell /usr/sbin/nologin tt-pypiuser

# 2. Create virtual environment
sudo mkdir -p /opt/pypi-server-env
sudo chown tt-pypiuser:tt-pypiuser /opt/pypi-server-env
python3 -m venv /opt/pypi-server-env

# 3. Activate and install pypiserver
source /opt/pypi-server-env/bin/activate
pip install --upgrade pip
pip install pypiserver

# 4. Create data directory
sudo mkdir -p /mnt/ai-storage/pypi-packages
sudo chown tt-pypiuser:tt-pypiuser /mnt/ai-storage/pypi-packages
