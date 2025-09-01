#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Create required directories
mkdir -p /srv/dev1/eso/docker/env
mkdir -p /mnt/ai_storage/eso/data

# Set ownership and permissions
chown -R mpegg-adm:mpegg-adm /srv/dev1/eso
chown -R mpegg-adm:mpegg-adm /mnt/ai_storage/eso
chmod -R 775 /srv/dev1/eso
chmod -R 775 /mnt/ai_storage/eso

# Navigate to the Docker directory
cd /srv/dev1/eso/docker || exit

# Create symlink for .env file
ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/env/eso.env env/eso.env

# Create symlink for eso-dev1.yml
ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/eso-dev1.yml eso-dev1.yml

# Start the Docker Compose setup
docker compose -f eso-dev1.yml up -d

# Enable and reload Nginx configuration using nginx-enable-site.sh
/home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/eso.conf
