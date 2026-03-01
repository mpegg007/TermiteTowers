<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/mkdocs-deployment-checklist.md:125 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: b5dccf39b9c599a3eb986f457e9c532629a2d923 %
  %ccm_git_commit_id: c1f5aa954a589e43600caffa76969fcd4a57b2f1 %
  %ccm_git_commit_count: 125 %
  %ccm_git_commit_date: 2025-12-15 10:05:29 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: monday drop %
  %ccm_git_modify_date: 2025-12-15 10:05:38 %
  %ccm_git_file_last_modified: 2025-12-15 10:05:38 %
  %ccm_git_file_name: mkdocs-deployment-checklist.md %
  %ccm_git_path: wiki/mkdocs-deployment-checklist.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3339 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: Add MkDocs deployment checklist % -->

# MkDocs Deployment Checklist

## Files Created/Updated

### ✅ Created Files

1. `/home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml` - Docker Compose file
2. `/home/mpegg-adm/source/TermiteTowers/mkdocs.yml` - MkDocs configuration
3. `/home/mpegg-adm/source/TermiteTowers/wiki/runbook-mkdocs.md` - Service runbook
4. `/home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/docs.conf` - Nginx config

### ✅ Updated Files

1. `/home/mpegg-adm/source/TermiteTowers/wiki/ports.md` - Added MkDocs on port 3210
2. `/home/mpegg-adm/source/TermiteTowers/infra/nginx/www/chat/index.html` - Added Docs tile

### ❌ Deleted Files

1. `/home/mpegg-adm/source/TermiteTowers/infra/docker/start-mkdocs.sh` - Removed (not standard)

## Remaining Manual Steps

These steps need to be run on the host to complete deployment:

### 1. Create Data Directory

```bash
sudo mkdir -p /mnt/ai_storage/mkdocs/site
sudo chown -R 2001:1006 /mnt/ai_storage/mkdocs
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/mkdocs
```

### 2. Create /srv/dev1 Convenience Path and Symlink

```bash
sudo mkdir -p /srv/dev1/mkdocs/docker
sudo ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml \
  /srv/dev1/mkdocs/docker/mkdocs-dev1.yml
```

### 3. Ensure Network Exists

```bash
docker network inspect productivity-apps-net-dev1 >/dev/null 2>&1 || \
  docker network create productivity-apps-net-dev1
```

### 4. Start MkDocs Container

```bash
goapp mkdocs
dcup
```

Or without aliases:

```bash
cd /srv/dev1/mkdocs/docker
docker compose -f mkdocs-dev1.yml up -d
```

### 5. Enable Nginx Site

This script will install, enable, test, and reload Nginx automatically:

```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/docs.conf \
  docs
```

### 6. Deploy Chat Tile

```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-www.sh
```

### 7. Add DNS CNAME Record

Add DNS CNAME record: `docs.termitetowers.ca` -> `imono.termitetowers.ca`

(Use your DNS management tool - PowerDNS at <https://dns.termitetowers.ca>)

## Verification

After completing the steps above:

1. Check container is running: `docker ps | grep mkdocs`
2. Test local access: `curl -I http://localhost:3210`
3. Test HTTPS access: `curl -I https://docs.termitetowers.ca`
4. Verify chat tile: Visit <https://chat.termitetowers.ca>

## Design Decisions

### Volume Mounting Strategy

Following ESPHome pattern:

- **Source files** (Git-controlled): Mounted from `/home/mpegg-adm/source/TermiteTowers`
- **Generated data** (build output): Stored in `/mnt/ai_storage/mkdocs/site`

This allows:

- Instant updates when editing wiki markdown files
- Git-first workflow (no database sync required)
- Build cache persists across container restarts

### No Custom Start Script

Unlike the initial implementation, there is no custom start script. All services use standard `docker compose` commands directly, per TermiteTowers conventions.

### Port Allocation

Port 3210 was already reserved for "Documentation Sites" in the Content & Documentation range (3200-3299).

## Related Documentation

- [Runbook: MkDocs](runbook-mkdocs.md)
- [How to Add Docker App](how-to-add-docker-app.md)
- [Compose Conventions](compose-conventions.md)
- [Ports Inventory](ports.md)
