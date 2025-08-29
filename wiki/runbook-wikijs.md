# Runbook: Wiki.js (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/wiki-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/wiki-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/wiki-dev1.yml down`

## Mounts
- `/mnt/ai_storage/wiki/postgres-data:/var/lib/postgresql/data`
- `/mnt/ai_storage/wiki/wikijs-data:/wiki/data`

## Env
- For DB service: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- For app: DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

## Notes
- Both services run as 2001:1006 and inherit group-writable defaults via umask 002 (Postgres entrypoint wrapped).

## Troubleshooting
- If DB files end up root-owned, double-check the `command` wrapper and `user` in the postgres service.
