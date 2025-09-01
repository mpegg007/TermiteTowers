<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-vault.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-09-01 15:47:13 %
% ccm_file_name: runbook-vault.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-vault.md %
% ccm_blob_sha: 372491695a3dba1b8916d074aabbc597d4493ac7 %
% ccm_exec: no %
% ccm_size: 3846 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: Vault (Infisical) - dev1

Last updated: 2025-09-01

## Summary
Self-hosted Infisical (vault) on dev1 using docker compose with a dedicated Postgres container and internal network.

## Compose
- File: `infra/docker/vault-dev1.yml`
- Network: `vault-dev1_vaultnet`
- Volumes:
  - Postgres data: `/mnt/ai_storage/vault/data -> /var/lib/postgresql/data`
- Env file: `infra/docker/env/vault.env` (symlinked to `/srv/dev1/vault/docker/env/vault.env`)

## Required env
- `ENCRYPTION_KEY` (hex)
- `AUTH_SECRET` (hex)
- `REDIS_URL` (e.g., `redis://localhost:6379` or sentinel variant)
- `DB_CONNECTION_URI` (Infisical expects this):
  - `postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}`
- Also present (for convenience/compose): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`

## Bring-up steps
1) Ensure env values in `vault.env` are set.
2) Ensure host folders exist/owned:
   - `/mnt/ai_storage/vault/data` (775, owner `mpegg-adm:mpegg-adm`)
3) Start:
   - `cd /srv/dev1/vault/docker`
   - `sudo docker compose -f vault-dev1.yml up -d`

## Common errors and fixes
- Invalid URL (postgresql://undefined...): app not receiving DB vars; fix by setting `DB_CONNECTION_URI` and using host `postgres`.
- Auth failures for user `vault`: data dir was previously initialized with different creds.
  - Fix A (non-destructive): inside `vault-postgres`, `ALTER USER vault WITH PASSWORD '...';` and `createdb -O vault vault`.
  - Fix B (destructive): stop stack, backup and delete `/mnt/ai_storage/vault/data`, then start to re-init.
- Network not found (`vaultnet` vs prefixed): use `vault-dev1_vaultnet` (Compose adds project prefix).

## Postgres health + ordering
- `vault` depends on `postgres` health with `pg_isready` check to avoid race conditions.

## Current state (2025-09-01)
- Fresh re-init succeeded; Postgres is accepting connections.
- App logs previously failed with invalid URL; switched to `DB_CONNECTION_URI`.
- Now seeing `relation "infisical_migrations" does not exist` from Postgres, which indicates app migrations must run on first successful app start. Expectation: once `vault` (Infisical) starts successfully with correct DB URI, it runs migrations and creates this table.

## Next session TODO
- Verify `vault-dev1` logs after fresh start to confirm migrations run.
- If migrations don’t run, check container tag (`infisical/infisical:latest` vs `latest-postgres`) and consider using `latest-postgres` as in upstream compose.
- Validate connectivity from app container: `env | grep DB_CONNECTION_URI` and `nc -zv postgres 5432`.
- Back up DB after successful migration.

## Useful commands
- `sudo docker logs -f vault-postgres`
- `sudo docker logs -f vault-dev1`
- `sudo docker exec -it vault-dev1 env | grep -E 'DB_CONNECTION_URI|POSTGRES_'`
- `sudo docker exec -it vault-postgres psql -U postgres -c "\du+"`
- `sudo docker compose -f vault-dev1.yml down && sudo docker compose -f vault-dev1.yml up -d`
