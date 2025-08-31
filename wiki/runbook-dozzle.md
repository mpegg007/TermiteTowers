<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 14:14:22 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-dozzle.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 13:40:09 %
% ccm_file_name: runbook-dozzle.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-dozzle.md %
% ccm_blob_sha: fc7aa09409edb99e77e661f14db22e7e71735e38 %
% ccm_exec: no %
% ccm_size: 1831 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Dozzle (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/dozzle-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/dozzle-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/dozzle-dev1.yml down`

## Ports & URL
- URL: https://dozzle.termitetowers.ca
- Host: http://<host>:3302 → container 8080

## Data
- No persistent data. Reads Docker socket read-only.

## Troubleshooting
- Ensure Docker API socket is accessible: `/var/run/docker.sock` mounted read-only.

## Deploy (copy/paste)
```bash
# Start the container
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/dozzle-dev1.yml up -d

# Enable Nginx site (host uses no .conf suffix)
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
	/home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/dozzle.conf dozzle

# Verify
curl -I https://dozzle.termitetowers.ca
```
