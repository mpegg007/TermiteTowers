<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/how-to-decommission-docker-app.md:125 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 65a17f6abd3903a07342d77eb3932ff0a60d4ade %
  %ccm_git_commit_id: c1f5aa954a589e43600caffa76969fcd4a57b2f1 %
  %ccm_git_commit_count: 125 %
  %ccm_git_commit_date: 2025-12-15 10:05:29 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: monday drop %
  %ccm_git_modify_date: 2025-12-15 10:05:37 %
  %ccm_git_file_last_modified: 2025-12-15 10:05:37 %
  %ccm_git_file_name: how-to-decommission-docker-app.md %
  %ccm_git_path: wiki/how-to-decommission-docker-app.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 2536 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->

# How to Decommission a Docker App (dev1)

This guide outlines the steps to properly remove a service from the TermiteTowers infrastructure.

## TL;DR Checklist
- [ ] Stop and remove the Docker container.
- [ ] Remove the Docker Compose file (`infra/docker/<service>-dev1.yml`).
- [ ] Remove environment files (`infra/docker/env/<service>.env`).
- [ ] Remove the Nginx configuration (`infra/nginx/sites-available/<short>.conf`) and the symlink in `sites-enabled`.
- [ ] Remove the dashboard tile from `infra/dns/web/index.html` (or `infra/nginx/www/chat/index.html`).
- [ ] Remove the port allocation from `wiki/ports.md`.
- [ ] Remove DNS records (if applicable).
- [ ] Archive or delete data directories (`/mnt/ai_storage/<service>`).
- [ ] Remove symlinks in `/srv/dev1/<short>`.

## 1) Stop and Remove Container

```bash
# Find the running container
docker ps | grep <service>

# Stop and remove
docker stop <container_name>
docker rm <container_name>
```

## 2) Remove Configuration Files

### Docker Compose
Remove the service definition file:
```bash
rm infra/docker/<service>-dev1.yml
```

### Environment Files
Remove any associated environment files or secrets:
```bash
rm infra/docker/env/<service>.env
# Check for example files too
rm infra/docker/env/<service>.env.example
```

## 3) Remove Nginx Configuration

Remove the site configuration and disable it:
```bash
# Remove the config file (from repo)
rm infra/nginx/sites-available/<service>.conf

# Remove the system symlinks (if they exist)
sudo rm /etc/nginx/sites-available/<service>
sudo rm /etc/nginx/sites-enabled/<service>
```

## 4) Update Dashboard

Edit `infra/dns/web/index.html` (or `infra/nginx/www/chat/index.html`) to remove the service tile.
Look for the `<div class="grid-item">` block corresponding to your service and delete it.

## 5) Release Port Allocation

Edit `wiki/ports.md` and remove the entry for the service to free up the port for future use.

## 6) Clean Up Data and Symlinks

Remove the data directories and convenience symlinks.

```bash
# Remove symlink in /srv/dev1
rm -rf /srv/dev1/<service>

# Remove data directory (WARNING: Irreversible)
# sudo rm -rf /mnt/ai_storage/<service>
```

## 7) Remove Docker Image

Free up disk space by removing the unused Docker image.

```bash
# Find the image using a filter (more reliable than grep)
docker images --filter reference='*<service>*'

# Remove the image
docker rmi <image_id>
```

## 8) Verify Removal

Check that the service is no longer accessible and that all artifacts are gone.
