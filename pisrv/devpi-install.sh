sudo groupadd tt-devpi
sudo useradd -r -s /usr/sbin/nologin -g tt-devpi tt-devpi

sudo mkdir -p /mnt/ai-storage/devpi
sudo chown tt-devpi:tt-devpi /mnt/ai-storage/devpi
sudo chmod 750 /mnt/ai-storage/devpi

sudo mkdir -p /opt/devpi
sudo chown tt-devpi:tt-devpi /opt/devpi
sudo -u tt-devpi python3 -m venv /opt/devpi/venv
sudo -u tt-devpi /opt/devpi/venv/bin/pip install devpi-server devpi-client

# /etc/systemd/system/devpi.service
[Unit]
Description=Devpi PyPI Caching Server
After=network.target

[Service]
User=tt-devpi
Group=tt-devpi
ExecStart=/opt/devpi/venv/bin/devpi-server \
  --serverdir /mnt/ai-storage/devpi \
  --host 0.0.0.0 --port 3141
Restart=always

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable devpi
sudo systemctl start devpi

pip config set global.index-url http://your-server-ip:3141/root/pypi/+simple/


sudo nano /etc/nginx/sites-available/packages
server {
    listen 443 ssl;
    server_name packages.termitetowers.ca;

    ssl_certificate /etc/letsencrypt/live/termitetowers.ca/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/termitetowers.ca/privkey.pem;

    location / {
        proxy_pass http://localhost:3141;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

sudo ln -s /etc/nginx/sites-available/packages /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo -u tt-devpi /opt/devpi/venv/bin/devpi-init --serverdir /mnt/ai-storage/devpi

sudo systemctl restart devpi
sudo systemctl status devpi

curl http://localhost:3141
https://packages.termitetowers.ca/root/pypi/+simple/


sudo -u tt-devpi HOME=/opt/devpi /opt/devpi/venv/bin/devpi login tt-devpi --password securecuda123


sudo -u tt-devpi HOME=/opt/devpi /opt/devpi/venv/bin/devpi index -c torch-cu118 \
  mirror_url=https://download.pytorch.org/whl/cu118 \
  type=mirror



sudo -u tt-devpi HOME=/opt/devpi /opt/devpi/venv/bin/devpi use https://packages.termitetowers.ca/tt-devpi/torch-cu118


python3 -m pip install torch torchvision torchaudio \
  --index-url https://packages.termitetowers.ca/tt-devpi/torch-cu118/+simple


sudo -u tt-devpi HOME=/opt/devpi /opt/devpi/venv/bin/devpi index -c cuda-stack \
  bases=tt-devpi/torch-cu118,tt-devpi/cuda
