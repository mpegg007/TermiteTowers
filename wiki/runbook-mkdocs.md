<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/runbook-mkdocs.md:125 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 3fa245605ed461ab152c5ef770e19225a432887a %
  %ccm_git_commit_id: c1f5aa954a589e43600caffa76969fcd4a57b2f1 %
  %ccm_git_commit_count: 125 %
  %ccm_git_commit_date: 2025-12-15 10:05:29 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: monday drop %
  %ccm_git_modify_date: 2025-12-15 10:05:40 %
  %ccm_git_file_last_modified: 2025-12-15 10:05:40 %
  %ccm_git_file_name: runbook-mkdocs.md %
  %ccm_git_path: wiki/runbook-mkdocs.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3797 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: Add MkDocs documentation site % -->

# Runbook: MkDocs (dev1)

## Overview
MkDocs Material documentation site serving the TermiteTowers wiki folder. Git-first workflow - edit markdown files directly in the repo, changes appear immediately in dev mode.

## Service Details
- **Subdomain**: docs.termitetowers.ca
- **Host Port**: 3210
- **Container Port**: 8000
- **Category**: Content & Documentation (3200-3299 range)
- **Network**: productivity-apps-net-dev1

## Start/Stop

- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml down`

## Deployment Checklist

Initial setup requires these steps (already completed):

1. ✅ Create data directory: `sudo mkdir -p /mnt/ai_storage/mkdocs/site && sudo chown -R 2001:1006 /mnt/ai_storage/mkdocs`
2. ✅ Start container (see Start command above)
3. ✅ Enable Nginx site: `bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/docs.conf docs`
4. ✅ Test Nginx: `sudo nginx -t && sudo systemctl reload nginx`
5. ✅ Deploy chat tile: `bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-www.sh`
6. ✅ Add DNS CNAME: `docs` -> `imono.termitetowers.ca`
7. ✅ Update wiki/ports.md
8. ✅ Create this runbook

## Mounts
- `/home/mpegg-adm/source/TermiteTowers:/docs` (repo mounted for mkdocs.yml + wiki source files)
- `/mnt/ai_storage/mkdocs/site:/docs/site` (build output cache)

## Configuration
- **mkdocs.yml**: Located at repo root `/home/mpegg-adm/source/TermiteTowers/mkdocs.yml`
- **docs_dir**: Points to `wiki` subfolder
- **Theme**: Material theme with dark/light mode toggle
- **Features**: Navigation tabs, search, code copy, Mermaid diagrams

## Usage
1. Edit markdown files in `/home/mpegg-adm/source/TermiteTowers/wiki/`
2. Changes appear immediately (dev server auto-reloads)
3. Access at http://docs.termitetowers.ca:3210 or http://localhost:3210

## Production Build
To build static site for production:
```bash
docker run --rm -v /home/mpegg-adm/source/TermiteTowers:/docs squidfunk/mkdocs-material:latest build
```
Output will be in `/home/mpegg-adm/source/TermiteTowers/site/`

## Navigation Structure
Navigation defined in mkdocs.yml:
- Home: README.md
- Infrastructure: Ports, Device Naming, Domains
- Docker: How-to guides, Compose conventions, Nginx config
- Operations: Backup strategy, Runbooks
- Development: Git automation, VS Code docs
- Media & Home Automation: Health, ESPHome

## Notes
- Runs as user 2001:1006 (storage-svc:tt-ai-storage)
- No database required - pure Git workflow
- Supports Mermaid diagrams, code syntax highlighting, search
- Material theme includes navigation, search, and content features
- Container has access to host via host.docker.internal

## Troubleshooting

### MkDocs fails to start
- Check mkdocs.yml syntax: `docker run --rm -v /home/mpegg-adm/source/TermiteTowers:/docs squidfunk/mkdocs-material:latest build --strict`
- Verify wiki folder exists and has markdown files

### Changes not appearing
- Dev server should auto-reload, check container logs
- Verify file permissions (should be readable by user 2001)

### Navigation not showing files
- Add files to `nav:` section in mkdocs.yml
- Or remove `nav:` to use automatic navigation based on file structure

### Port conflict
- Check if 3210 is already in use: `sudo netstat -tlnp | grep :3210`
- See wiki/ports.md for port allocation

## Related Documentation
- [How to Add Docker App](how-to-add-docker-app.md)
- [Compose Conventions](compose-conventions.md)
- [Ports Inventory](ports.md)
- [Nginx Configuration](nginx-configuration.md)
