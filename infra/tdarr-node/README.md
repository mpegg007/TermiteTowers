<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: infra/tdarr-node/README.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 11:51:02 %
% ccm_file_name: README.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: infra/tdarr-node/README.md %
% ccm_blob_sha: fd9d060c1d3e16ba9cc728a5666055e07bb2723a %
% ccm_exec: no %
% ccm_size: 2021 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Tdarr Node (Docker Compose)

This brings up a Tdarr Node on this machine and connects it to your existing Tdarr Server.

## Layout

- `tdarr-node-dev1.yml` mounts local folders:
	- `./config -> /app/configs` (includes `Tdarr_Node_Config.json`)
	- `./logs   -> /app/logs`
	- `./cache  -> /temp`

GPU overlays (use with -f):
- `tdarr-node-dev1.nvidia.yml` (adds `gpus: all`)
- `tdarr-node-dev1.intel.yml` (adds `/dev/dri` for VAAPI/Quick Sync)

## Quick start

1. Edit `tdarr-node-dev1.yml` to set media mount(s) to your paths.
2. Start the node:

```bash
TDARR_SERVER_IP=192.168.4.63 \
TDARR_SERVER_PORT=8266 \
TDARR_NODE_NAME=$(hostname)-node \
TZ=America/Toronto \
PUID=$(id -u) PGID=$(id -g) \
docker compose -f tdarr-node-dev1.yml up -d
```

NVIDIA GPU:
```bash
docker compose -f tdarr-node-dev1.yml -f tdarr-node-dev1.nvidia.yml up -d
```

Intel Quick Sync / VAAPI:
```bash
docker compose -f tdarr-node-dev1.yml -f tdarr-node-dev1.intel.yml up -d
```

## Notes
- Uses `network_mode: host` so no port mappings are needed; it reaches the server by IP:port.
- Tune `videoProcessors` and `nodeWorkerThreads` to match your CPU/GPU.
- Logs/configs persist under `infra/tdarr-node/{logs,config,cache}`.
