<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 14:31:46 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/how-to-add-docker-app.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 14:30:32 %
% ccm_file_name: how-to-add-docker-app.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/how-to-add-docker-app.md %
% ccm_blob_sha: 1001ab7378865e12c1a44ea5f85456f5ed79ffce %
% ccm_exec: no %
% ccm_size: 5752 %
% ccm_tag:  %
tt-ccm.header.end
-->

# How to add a new Docker app (dev1)

This is the repeatable pattern we use for adding services (Compose + Nginx + Chat tile), with optional secrets and the /srv/dev1 symlink convention.

## TL;DR checklist
- Pick a subdomain and host port; confirm no conflicts.
- Create data dir(s) under /mnt/ai_storage/<service> and set perms (2001:1006, group-writable).
- Add a Compose file under infra/docker/<service>-dev1.yml (schema hint, ports, volumes, logging).
- If the app needs secrets, add env_file: infra/docker/env/<service>.env (keep example next to it).
- Add an Nginx site at infra/nginx/sites-available/<short>.conf; enable without .conf on host.
- Add a tile to infra/nginx/www/chat/index.html and deploy it.
- add DNS CNAME record for <short> to imono.termitetowers.ca.
- (Optional) Create /srv/dev1/<short>/docker and symlink the Compose file for convenience.
- Update wiki/ports.md and (optionally) add a service runbook.

## 1) Choose names and ports
- Subdomain: e.g., example.termitetowers.ca
- Host port: follow the 3300+ pattern when possible
- Check for collisions:
```bash
rg -n "proxy_pass\\s+http://localhost:(\\d+)" infra/nginx/sites-available/*.conf
rg -n "(?:0\\.0\\.0\\.0:)?(\\d{2,5}):(\\d{2,5})" infra/docker/*.yml
```

## 2) Create data directories and permissions
```bash
SERVICE=example   # short, lowercase
sudo mkdir -p /mnt/ai_storage/$SERVICE/data
sudo chown -R 2001:1006 /mnt/ai_storage/$SERVICE
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/$SERVICE
```

## 3) Compose file (infra/docker/<service>-dev1.yml)
- Include:
  - image, container_name, restart: unless-stopped
  - ports: "0.0.0.0:<host>:<container>"
  - volumes for data
  - logging: json-file with size/rotate
  - env_file for secrets when applicable

Note on VS Code schema validation:
- Keep the yaml-language-server schema hint as the very first line of the file.
- Our CCM header hooks are modeline-aware and will insert/update header lines after the modeline automatically.

Example skeleton:
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json
name: example-dev1
services:
  example:
    image: registry/image:latest
    container_name: example-dev1
    restart: unless-stopped
    ports:
      - "0.0.0.0:330X:CONTPORT"
    # env_file:
    #  - ./env/example.env
    environment:
      - TZ=UTC
    volumes:
      - /mnt/ai_storage/example/data:/app/data
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

## 4) Secrets (optional)
- Place secrets in infra/docker/env/<service>.env and commit an adjacent <service>.env.example.
- Generate 64-char hex when needed (e.g., Homarr SECRET_ENCRYPTION_KEY):
```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/gen-secret-hex.sh
```
- Example env placeholders:
```dotenv
# infra/docker/env/example.env.example
SECRET_SOMETHING=
TZ=UTC
```

## 5) Start the container
```bash
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/<service>-dev1.yml up -d
```

## 6) Nginx reverse proxy
- Create infra/nginx/sites-available/<short>.conf with standard proxy to localhost:<hostport>.
- Enable on host WITHOUT .conf suffix using the helper:
```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/<short>.conf <short>
```
- Verify:
```bash
sudo nginx -t && sudo systemctl reload nginx
curl -I https://<short>.termitetowers.ca
```

## 7) Chat tile + deploy
- Edit infra/nginx/www/chat/index.html to add a tile.
- Deploy to /var/www/chat:
```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-chat.sh
```

## 8) /srv/dev1 convenience path and symlink (optional but recommended)
We keep a per-service folder with a docker subdir for quick access, and symlink the Compose file back to the repo.
```bash
SHORT=example
COMPOSE=example-dev1.yml
sudo mkdir -p /srv/dev1/$SHORT/docker
sudo ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/$COMPOSE /srv/dev1/$SHORT/docker/$COMPOSE
# Now you can run compose from /srv/dev1/$SHORT/docker if you prefer
(cd /srv/dev1/$SHORT/docker && docker compose -f $COMPOSE up -d)
```
Note: the compose file remains source-controlled in TermiteTowers; /srv/dev1 just provides a stable runtime path.

## 9) Bookkeeping
- Update wiki/ports.md with the new service row.
- (Optional) Add a runbook under wiki/runbook-<service>.md with Start/Stop, Ports & URL, Data, Troubleshooting, and a Deploy block.

## 10) Sanity and troubleshooting
- Check container logs:
```bash
docker logs --tail 200 <container_name>
```
- Check Nginx and connectivity:
```bash
sudo nginx -t
curl -I https://<short>.termitetowers.ca
```
- Permissions: most services use 2001:1006 and require group-writable mounts (umask 002). Some may need initial root-owned chown on first start (remove user override if applicable).
