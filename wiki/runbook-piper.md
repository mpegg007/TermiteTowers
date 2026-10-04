<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-piper.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 11:51:03 %
% ccm_file_name: runbook-piper.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-piper.md %
% ccm_blob_sha: 0725e9e936b423f59576dc78280248ccb5d4a5c8 %
% ccm_exec: no %
% ccm_size: 1640 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Piper TTS (dev1)

## Install
- scripts/system/setup-piper-dev1.sh (SERVICE_USER/GROUP supported)

## Start/Stop
- Start: `sudo systemctl start wyoming-piper-dev1`
- Stop: `sudo systemctl stop wyoming-piper-dev1`
- Enable on boot: `sudo systemctl enable wyoming-piper-dev1`
- Status/logs: `sudo systemctl status wyoming-piper-dev1 -l` and `journalctl -u wyoming-piper-dev1 -f`

## Ports
- TTS service: tcp://0.0.0.0:10200

## Paths
- Program: /srv/dev1/piper
- Data (symlink): /srv/dev1/piper/data -> /mnt/ai_storage/piper

## Notes
- Place Piper binary at /srv/dev1/piper/piper (chmod +x)
- Run script respects WYOMING_PIPER_DATA; unit sets it to /mnt/ai_storage/piper

## Troubleshooting
- Permission errors: `sudo chown -R <svc>:<grp> /mnt/ai_storage/piper`
- Port busy: check for another TTS instance on 10200
