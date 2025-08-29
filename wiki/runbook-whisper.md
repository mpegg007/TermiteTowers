# Runbook: Whisper Faster (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/whisper-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/whisper-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/whisper-dev1.yml down`

## Mounts
- `../source:/app` (local code)
- `../audio:/app/audio`
- `../output:/app/output`
- `/mnt/ai_storage/models/whisper:/app/models`
- `/mnt/ai_storage/models/*` to `/cache/*`

## GPU
- `runtime: nvidia` with GPU reservations

## Env
- PYTHONUNBUFFERED, HF_HOME

## Notes
- Command uses `umask 002`, installs Python deps, and runs `transcribe.py`.

## Troubleshooting
- Permission errors writing to output: check group ownership and default ACLs under `/mnt/ai_storage`
