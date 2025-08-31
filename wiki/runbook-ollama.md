<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
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
% ccm_file_last_modified: 2025-08-31 11:51:03 %
% ccm_file_name: runbook-ollama.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-ollama.md %
% ccm_blob_sha: f291e6f782d08d870509ed28bab75a0ade34e642 %
% ccm_exec: no %
% ccm_size: 1596 %
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
- Models: /mnt/ai_storage/ollama/models (OLLAMA_MODELS)

## Notes
- Open WebUI and Lobe Chat use host.docker.internal:11434
- Ensure service user has rw access to /mnt/ai_storage/ollama/models

## Troubleshooting
- Permission errors: `sudo chown -R <svc>:<grp> /mnt/ai_storage/ollama/models`
- Check connectivity: `curl http://localhost:11434/api/tags`
