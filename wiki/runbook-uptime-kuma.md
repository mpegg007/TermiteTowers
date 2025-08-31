<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 12:26:15 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-uptime-kuma.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 12:26:15 %
% ccm_file_name: runbook-uptime-kuma.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-uptime-kuma.md %
% ccm_blob_sha: a2dbbfba4a188eae48217f8d6c68a4b1ca6246e2 %
% ccm_exec: no %
% ccm_size: 1489 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Uptime Kuma (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml down`

## Ports & URL
- URL: https://kuma.termitetowers.ca
- Host: http://<host>:3301 → container 3001

## Data
- /mnt/ai_storage/uptime-kuma/data

## Troubleshooting
- Initial permission issues: remove user override and let container chown /app/data on first start, then re-apply user if needed.
