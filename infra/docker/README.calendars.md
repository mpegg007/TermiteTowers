<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/docker/README.calendars.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: c05526f7b5c4eb6bd94ab01f14b320be15ac488f %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:21 %
  %ccm_git_file_last_modified: 2026-03-22 09:03:21 %
  %ccm_git_file_name: README.calendars.md %
  %ccm_git_path: infra/docker/README.calendars.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1983 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
# Calendars Stack (Radicale + vdirsyncer)

This stack provides a local CalDAV server (Radicale) and two-way sync with Google and Outlook calendars using vdirsyncer. It follows the TermiteTowers standard for Docker app deployment.

## 1. Ports and Networks
- Radicale: 3232 (internal 5232)
- Network: app-services-net-dev1 (external)

## 2. Data Directories
- /mnt/ai_storage/calendars/radicale
- /mnt/ai_storage/calendars/vdirsyncer_google_cache
- /mnt/ai_storage/calendars/vdirsyncer_outlook_cache

Set permissions:
```bash
sudo mkdir -p /mnt/ai_storage/calendars/radicale
sudo mkdir -p /mnt/ai_storage/calendars/vdirsyncer_google_cache
sudo mkdir -p /mnt/ai_storage/calendars/vdirsyncer_outlook_cache
sudo chown -R 2001:1006 /mnt/ai_storage/calendars
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/calendars
```

## 3. Compose File
- Place at infra/docker/calendars-dev1.yml
- Uses env_file: ./env/calendars.env (see .env.example)
- Attach to app-services-net-dev1

## 4. Secrets
- Copy infra/docker/env/calendars.env.example to calendars.env and fill in credentials.

## 5. Symlink for /srv/dev1
```bash
sudo mkdir -p /srv/dev1/calendars/docker
sudo ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/calendars-dev1.yml /srv/dev1/calendars/docker/calendars-dev1.yml
```

## 6. Start the Stack
```bash
cd /srv/dev1/calendars/docker
docker compose -f calendars-dev1.yml up -d
```

## 7. Nginx Reverse Proxy
- Add infra/nginx/sites-available/calendars.conf to proxy 3232 → 5232
- Enable with nginx-enable-site.sh

## 8. vdirsyncer Configs
- Google: infra/docker/vdirsyncer/google/config
- Outlook: infra/docker/vdirsyncer/outlook/config

## 9. Scaling Up
- Duplicate vdirsyncer containers and config sections for each new account.
- Add new cache/data dirs as needed.

## 10. Bookkeeping
- Update wiki/ports.md and add a runbook if desired.

---

See wiki/how-to-add-docker-app.md for full standards and troubleshooting.
