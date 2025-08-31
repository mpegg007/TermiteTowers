<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 14:14:22 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-kitchenowl.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 13:40:09 %
% ccm_file_name: runbook-kitchenowl.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-kitchenowl.md %
% ccm_blob_sha: 3b77273686717db0b3998c6b613cf2c19430f7ff %
% ccm_exec: no %
% ccm_size: 2204 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: KitchenOwl (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/kitchenowl-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/kitchenowl-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/kitchenowl-dev1.yml down`

## Deploy (copy/paste)
```bash
# Create data dirs with permissions
sudo mkdir -p /mnt/ai_storage/kitchenowl/data
sudo chown -R 2001:1006 /mnt/ai_storage/kitchenowl
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/kitchenowl

# Start the container
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/kitchenowl-dev1.yml up -d

# Enable Nginx site (host uses no .conf suffix)
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/kitchenowl.conf kitchenowl

# Verify
curl -I https://kitchenowl.termitetowers.ca
```

## Ports & URL
- URL: https://kitchenowl.termitetowers.ca
- Host: http://<host>:3300 → container 8080

## Data
- /mnt/ai_storage/kitchenowl/data

## Troubleshooting
- Permission denied at startup: ensure data dir exists and is writable.
  - `sudo mkdir -p /mnt/ai_storage/kitchenowl/data`
  - `sudo chown -R 2001:1006 /mnt/ai_storage/kitchenowl`
  - `sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/kitchenowl`
