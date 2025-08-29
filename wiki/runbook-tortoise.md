# Runbook: Tortoise TTS (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/tortoise-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/tortoise-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/tortoise-dev1.yml down`

## Mounts
- `../source:/app` (local code)
- `/mnt/ai_storage/models/*` to `/cache/*`
- `/mnt/ai_storage/tortoise/voices:/app/voices`
- `/mnt/ai_storage/tortoise/outputs:/app/outputs`

## GPU
- `runtime: nvidia` with GPU reservations

## Env
- PYTHONUNBUFFERED, HF_HOME, HF_HUB_ENABLE_PROGRESS_BARS, PIP_INDEX_URL, PIP_EXTRA_INDEX_URL

## Notes
- Init command sets `umask 002` and installs required packages; consider pre-building an image to speed up restarts.

## Troubleshooting
- If outputs are root-owned, verify `user: 2001:1006` and umask 002
