<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: wiki/runbook-homarr.md:163 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: dd8c77022dd320828f60f8396db43cb68a92e940 % -->
<!-- %ccm_git_commit_id: ca6361a00a0e93d3da54f4cc925c6430ac7c8a1f % -->
<!-- %ccm_git_commit_count: 163 % -->
<!-- %ccm_git_commit_date: 2026-09-26 16:02:46 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: docs(homarr): the data volume has been purged, so the leaked key is inert % -->
<!-- %ccm_git_modify_date: 2026-09-26 16:02:47 % -->
<!-- %ccm_git_file_last_modified: 2026-09-26 16:02:46 % -->
<!-- %ccm_git_file_name: runbook-homarr.md % -->
<!-- %ccm_git_path: wiki/runbook-homarr.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 4261 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-09-25 mpegg  chore(homarr): retire Homarr - configured but never used day to day  --> 
<!--
-->

# Runbook: Homarr (dev1)

> **⛔ RETIRED 2026-09-26** — Homarr was stood up, configured with three
> integrations, and never used day to day. The container has been removed, the
> `home` nginx vhost disabled, and `infra/docker/homarr-dev1.yml` together with
> `infra/docker/env/homarr.env` deleted from the repo. The deploy block below is
> kept as the revival path.
>
> **Revival:** restore the compose file from git (`git log --diff-filter=D --
> infra/docker/homarr-dev1.yml`, then `git show <commit>^:infra/docker/homarr-dev1.yml
> > infra/docker/homarr-dev1.yml`), generate a key with `scripts/gen-secret-hex.sh`,
> create `env/homarr.env` from `env/homarr.env.example`, `docker compose -f
> infra/docker/homarr-dev1.yml up -d`, then re-enable the site with
> `scripts/nginx-enable-site.sh infra/nginx/sites-available/home.conf home`.
>
> **Security note (resolved 2026-09-26):** the old database lived in the anonymous
> volume behind `/appdata` (`34cf8e7f...`), holding three secrets encrypted with the
> old `SECRET_ENCRYPTION_KEY` - a key published in this repo's history. That volume
> has now been purged, so the leaked key decrypts nothing. No rotation is outstanding.


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
