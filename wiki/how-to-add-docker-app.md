<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: wiki/how-to-add-docker-app.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!--
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
bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-www.sh
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

### Container logs
```bash
docker logs --tail 200 <container_name>
```

### Nginx and connectivity
```bash
sudo nginx -t
curl -I https://<short>.termitetowers.ca
```

### Permissions
Most services use 2001:1006 and require group-writable mounts (umask 002). Some may need initial root-owned chown on first start (remove user override if applicable).

### GitHub Container Registry (ghcr.io) Pull Issues

**Symptom:** `Error response from daemon: Head "https://ghcr.io/v2/.../manifests/...": denied: denied`

**Problem:** 
- Stale cached images (e.g., `:main` tag from months ago)
- GitHub rate limits on anonymous pulls
- Expired authentication tokens

**Diagnosis:**
```bash
# Check when your cached image was created
docker images <image-name> --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"

# Example: Image shows "2025-08-22" but current date is "2025-10-08" = 2 months old!
```

**Fix - Force Fresh Pull:**

1. Stop and remove container:
```bash
docker stop <container-name>
docker rm <container-name>
```

2. Remove stale cached image:
```bash
# Check for ghost containers
docker ps -a | grep <container-name>

# Force remove any blocking containers by ID
docker rm -f <container-id>

# Force remove old cached image
docker rmi -f ghcr.io/<org>/<image>:<tag>
```

3. Pull fresh image:
```bash
# Docker will use credentials from ~/.docker/config.json if available
docker pull ghcr.io/<org>/<image>:<tag>

# If still denied, logout and retry (sometimes helps)
docker logout ghcr.io
docker pull ghcr.io/<org>/<image>:<tag>
```

4. Restart with fresh image:
```bash
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/<service>-dev1.yml up -d
```

**Real Example - Open WebUI Stuck on Old Version:**
```bash
# Problem: openwebui-dev1 stuck on v0.6.25, need v0.6.31+ for MCP support
# Cached image was from August, need October version

# Solution:
docker stop openwebui-dev1
docker rm openwebui-dev1
docker rm -f $(docker ps -aq --filter name=openwebui)  # Remove any ghost containers
docker rmi -f ghcr.io/open-webui/open-webui:main
docker pull ghcr.io/open-webui/open-webui:main
docker compose -f infra/docker/openweb-dev1.yml up -d

# Verify new version
docker exec openwebui-dev1 python -c "from open_webui.env import VERSION; print(f'Version: {VERSION}')"
```

**Prevention:**
- Periodically clean old images: `docker image prune -a`
- For production, use specific version tags (`:v0.6.33`) instead of `:main` or `:latest`
- Keep GitHub token fresh in `~/.docker/config.json`
- Schedule manual update checks for rolling tags like `:main`

