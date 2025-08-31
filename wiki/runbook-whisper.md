<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-whisper.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 11:51:03 %
% ccm_file_name: runbook-whisper.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-whisper.md %
% ccm_blob_sha: 65cfeabfc5ff43a627ed9703856cb78dd294602b %
% ccm_exec: no %
% ccm_size: 1927 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Whisper (Wyoming Faster Whisper, dev1)

## Install
- scripts/system/setup-whisper-dev1.sh (uses SERVICE_USER/GROUP; creates venv and systemd unit)

## Start/Stop
- Start: `sudo systemctl start wyoming-faster-whisper-dev1`
- Stop: `sudo systemctl stop wyoming-faster-whisper-dev1`
- Enable on boot: `sudo systemctl enable wyoming-faster-whisper-dev1`
- Status/logs: `sudo systemctl status wyoming-faster-whisper-dev1 -l` and `journalctl -u wyoming-faster-whisper-dev1 -f`

## Ports
- STT service: tcp://0.0.0.0:10300

## Paths
- Program: /srv/dev1/whisper
- Data (symlink): /srv/dev1/whisper/data -> /mnt/ai_storage/whisper
- HF cache: /mnt/ai_storage/models/huggingface (via HF_HOME)

## Tune
- Edit /etc/systemd/system/wyoming-faster-whisper-dev1.service.d/override.conf to change User/Group
- To adjust model/language/compute, edit ExecStart in the unit, then: `sudo systemctl daemon-reload && sudo systemctl restart wyoming-faster-whisper-dev1`

## Troubleshooting
- Permission errors: `sudo chown -R <svc>:<grp> /mnt/ai_storage/whisper`
- Port busy: check for another STT instance on 10300
