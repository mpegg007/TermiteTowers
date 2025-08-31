<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 14:14:22 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-homarr.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 14:14:22 %
% ccm_file_name: runbook-homarr.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-homarr.md %
% ccm_blob_sha: 3be7130eba94c4b526fc3e15fd2e7b31cb42f689 %
% ccm_exec: no %
% ccm_size: 2633 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Homarr (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/homarr-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/homarr-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/homarr-dev1.yml down`

## Ports & URL
- URL: https://home.termitetowers.ca
- Host: http://<host>:3303 → container 7575

## Data
- /mnt/ai_storage/homarr/configs
- /mnt/ai_storage/homarr/icons
- /mnt/ai_storage/homarr/data

## Troubleshooting
- If assets are not saved, ensure bind-mount paths exist and are writable:
  - `sudo mkdir -p /mnt/ai_storage/homarr/{configs,icons,data}`
  - `sudo chown -R 2001:1006 /mnt/ai_storage/homarr`
  - `sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/homarr`

## Deploy (copy/paste)
```bash
# Create data dirs with permissions
sudo mkdir -p /mnt/ai_storage/homarr/{configs,icons,data}
sudo chown -R 2001:1006 /mnt/ai_storage/homarr
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/homarr

# Create env file with a 64-char hex secret key
cp -n /home/mpegg-adm/source/TermiteTowers/infra/docker/env/homarr.env.example \
  /home/mpegg-adm/source/TermiteTowers/infra/docker/env/homarr.env
SECRET=$(bash /home/mpegg-adm/source/TermiteTowers/scripts/gen-secret-hex.sh)
sed -i "s/^SECRET_ENCRYPTION_KEY=.*/SECRET_ENCRYPTION_KEY=$SECRET/" \
  /home/mpegg-adm/source/TermiteTowers/infra/docker/env/homarr.env

# Start the container
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/homarr-dev1.yml up -d

# Enable Nginx site (host uses no .conf suffix)
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
  /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/home.conf home

# Verify
curl -I https://home.termitetowers.ca
```
