<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/ports.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-09-01 10:51:53 %
% ccm_file_name: ports.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/ports.md %
% ccm_blob_sha: 376f68556ce024928b54f7f65083cf70e0652de5 %
% ccm_exec: no %
% ccm_size: 2823 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Ports Inventory

This page tracks host and service ports used across TermiteTowers.

| Service        | Subdomain                  | Host Port | Container Port | Notes                                      |
|----------------|----------------------------|-----------|----------------|--------------------------------------------|
| WebAI          | webai.termitetowers.ca     | 3000      | 8080/3000      | Nginx -> localhost:3000                    |
| LobeChat       | lobe.termitetowers.ca      | 3100      | 3210/3100      | Nginx -> localhost:3100                    |
| Wiki.js        | wiki.termitetowers.ca      | 3200      | 3000           | Nginx -> localhost:3200; Docker 3200:3000  |
| Private PyPI   | packages.termitetowers.ca  | 3141      | 3141           | Nginx -> localhost:3141                    |
| KitchenOwl     | kitchenowl.termitetowers.ca| 3300      | 8080           | Nginx -> localhost:3300; Docker 3300:8080  |
| Uptime Kuma    | kuma.termitetowers.ca      | 3301      | 3001           | Nginx -> localhost:3301; Docker 3301:3001  |
| Dozzle         | dozzle.termitetowers.ca    | 3302      | 8080           | Nginx -> localhost:3302; Docker 3302:8080  |
| Homarr         | home.termitetowers.ca      | 3303      | 7575           | Nginx -> localhost:3303; Docker 3303:7575  |
| Ollama API     | ollama.termitetowers.ca    | 11434     | 11434          | Nginx -> localhost:11434                   |
| Private PyPI Proxy | pypi.termitetowers.ca  | 4080      | 4080           | Nginx -> localhost:4080                    |

## Allocated Ports

| Service | Port  |
|---------|-------|
| Vault   | 3304  |
| ESO     | 3305  |
| SOPS    | 3306  |

## Notes
- Ensure no port conflicts before assigning new ports.
- Update this document whenever a new service is added or ports are reallocated.

Notes:
- Host ports are typically bound on 0.0.0.0 in Compose where applicable.
- Nginx proxies HTTPS subdomains to the above localhost ports.
- Keep this list updated when adding services.

Updated: 2025-08-31
