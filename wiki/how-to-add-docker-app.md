<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/how-to-add-docker-app.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 32f1c35543b8b999a55a5a551bd962c9243aa3b5 %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:45 %
  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
  %ccm_git_file_name: how-to-add-docker-app.md %
  %ccm_git_path: wiki/how-to-add-docker-app.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 9180 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: big update % -->
<!--
-->

# How to add a new Docker app (dev1)

This is the repeatable pattern we use for adding services (Compose + Nginx + Chat tile), with optional secrets and the /srv/dev1 symlink convention.

## Docker Network Selection
Services should be grouped by function and port category. Use:
- `powerdns-dev1_powerdns-net` for core infrastructure (DNS, Pi-hole, PowerDNS, etc.)
- `app-services-net-dev1` for app services (KitchenOwl, Mealie, Homarr, LLM Server API, etc.)
- Create additional networks for other categories if needed (media, monitoring, AI, etc.)

When adding a new app service (e.g., Mealie, KitchenOwl), attach it to `app-services-net-dev1` for isolation and easier management.

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

### Service naming
- Subdomain: e.g., example.termitetowers.ca
- Short name: lowercase, no special chars (e.g., `example`)

### Port selection (IMPORTANT!)
**Always consult wiki/ports.md for the port allocation strategy before choosing a port.**

Port ranges are organized by category:

| Range | Category | Examples |
|-------|----------|----------|
| 3000-3099 | Core Infrastructure | DNS, admin interfaces |
| 3100-3199 | Development & DevOps | Package registries, CI/CD |
| 3200-3299 | Content & Documentation | Wiki, CMS |
| 3300-3399 | Home Automation & Daily | Dashboard, kitchen tools |
| 3400-3499 | Media & Entertainment | Plex, *arr services |
| 3500-3599 | Security & Secrets | Vault, SOPS, auth |
| 3600-3699 | Databases & Data | DB admin tools |
| 3700-3799 | Monitoring & Ops | Uptime, logs, metrics |
| 3800-3899 | AI & Machine Learning | Ollama, LLM interfaces |
| 3900-3999 | Asset & IT Management | Asset tracking, tickets |

**Steps to pick a port:**
1. Identify which category your service belongs to
2. Check wiki/ports.md for already-allocated ports in that range
3. Choose the next available port in sequence (e.g., if 3720 is taken, use 3730)
4. Update wiki/ports.md with your new allocation

### Check for port conflicts
```bash
# Check Nginx configs for port usage
rg -n "proxy_pass\\s+http://localhost:(\\d+)" infra/nginx/sites-available/*.conf

# Check Docker compose files for port bindings
rg -n "(?:0\\.0\\.0\\.0:)?(\\d{2,5}):(\\d{2,5})" infra/docker/*.yml

# Check if port is already listening on host
sudo netstat -tlnp | grep :3XXX
```

**Example:**
- Service: Prometheus (monitoring tool)
- Category: Monitoring & Ops
- Range: 3700-3799
- Check ports.md: 3700 (Uptime Kuma), 3710 (Dozzle) are taken
- Choose: 3720 ✅

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
    networks:
      - app-services-net-dev1  # Use this for app services
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

