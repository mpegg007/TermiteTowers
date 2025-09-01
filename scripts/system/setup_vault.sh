#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Create required directories
mkdir -p /srv/dev1/vault/docker/env
mkdir -p /mnt/ai_storage/vault/data

# Set ownership and permissions
chown -R mpegg-adm:mpegg-adm /srv/dev1/vault
chown -R mpegg-adm:mpegg-adm /mnt/ai_storage/vault
chmod -R 775 /srv/dev1/vault
chmod -R 775 /mnt/ai_storage/vault

# Navigate to the Docker directory
cd /srv/dev1/vault/docker || exit

# Create symlink for .env file
ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/env/vault.env env/vault.env

# Create symlink for vault-dev1.yml
ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/vault-dev1.yml vault-dev1.yml

# Start the Docker Compose setup
docker compose -f vault-dev1.yml up -d

# Enable and reload Nginx configuration using nginx-enable-site.sh
/home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/vault.conf
