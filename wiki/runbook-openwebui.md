# Runbook: Open WebUI (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml down`

## Mounts
- `/mnt/ai_storage/openwebui/data:/app/backend/data`
- `/mnt/ai_storage/models/*` to `/cache/*`

## Env
- OLLAMA_BASE_URL, MODEL_PROVIDER, DEFAULT_MODEL, HF_HOME

## Health
- URL: http://<host>:3000
- Check can reach Ollama: `curl http://host.docker.internal:11434/api/tags`

## Troubleshooting
- Permission errors: verify file owner/group and 664/775 modes
- If Linux host-gateway fails, consider `network_mode: host` (remove ports/extra_hosts)
