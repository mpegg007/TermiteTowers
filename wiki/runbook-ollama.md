<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-ollama.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-09-01 15:40:43 %
% ccm_file_name: runbook-ollama.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-ollama.md %
% ccm_blob_sha: 1752f4633ff162b0e818e42cb6a748c1fcb74681 %
% ccm_exec: no %
% ccm_size: 1597 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Ollama (dev1)

## Install
- scripts/system/setup-ollama-dev1.sh (SERVICE_USER/GROUP supported)

## Start/Stop
- Start: `sudo systemctl start ollama-dev1`
- Stop: `sudo systemctl stop ollama-dev1`
- Enable on boot: `sudo systemctl enable ollama-dev1`
- Status/logs: `sudo systemctl status ollama-dev1 -l` and `journalctl -u ollama-dev1 -f`

## Ports
- HTTP API: 0.0.0.0:11434

## Paths
- Program: /srv/dev1/ollama
- Models: /mnt/ai_storage/models/ollama (OLLAMA_MODELS)

## Notes
- Open WebUI and Lobe Chat use host.docker.internal:11434
- Ensure service user has rw access to /mnt/ai_storage/models/ollama

## Troubleshooting
- Permission errors: `sudo chown -R <svc>:<grp> /mnt/ai_storage/models/ollama`
- Check connectivity: `curl http://localhost:11434/api/tags`
