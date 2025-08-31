<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-ha-handler.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 11:51:03 %
% ccm_file_name: runbook-ha-handler.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-ha-handler.md %
% ccm_blob_sha: ee0e6ab0af6141cde27bc4ee7de18bd90151b74c %
% ccm_exec: no %
% ccm_size: 1545 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: LLM Home Assistant Handler (dev1)

## Install
- scripts/system/setup-llm-ha-handler-dev1.sh (SERVICE_USER/GROUP supported)

## Start/Stop
- Start: `sudo systemctl start llm-ha-handler-dev1`
- Stop: `sudo systemctl stop llm-ha-handler-dev1`
- Enable on boot: `sudo systemctl enable llm-ha-handler-dev1`
- Status/logs: `sudo systemctl status llm-ha-handler-dev1 -l` and `journalctl -u llm-ha-handler-dev1 -f`

## Ports
- Internal client; no external port.

## Paths
- Program: /home/mpegg-adm/source/llm-server

## Config
- Update `llm-server/llm_server/handlers/home_assistant.py` as needed

## Troubleshooting
- Check logs with journalctl
- Ensure Python deps are installed in system Python if required
