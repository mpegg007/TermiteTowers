<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/runbook-uptime-kuma.md % -->
<!-- %ccm_git_object_id: wiki/runbook-uptime-kuma.md@216 % -->
<!-- %ccm_git_commit_date: 2026-11-13 11:40:17 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: chore(uptime-kuma): pin 2.5.11 after upgrading from 2.4.0 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!--
-->

# Runbook: Uptime Kuma (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml down`

## Ports & URL
- URL: https://kuma.termitetowers.ca
- Host: http://<host>:3700 → container 3001

## Data
- `/mnt/ai_storage/uptime-kuma/data` — holds `kuma.db` plus its `-wal`/`-shm` siblings. Copy the
  whole directory, never `kuma.db` alone.
- Snapshots: `/mnt/ai_storage/uptime-kuma/backups/pre-<version>-<YYYYMMDD>/`
- Healthcheck: supplied by the image itself, which is why `docker ps` shows `(healthy)`. Do not add
  a compose-level healthcheck — there is nothing to add.

## Updating

The image tag is **pinned** in `infra/docker/uptime-kuma-dev1.yml`. A Kuma upgrade migrates
`kuma.db` in place and the migration is forward-only, so an older image cannot open a migrated
database. The snapshot below is mandatory, not advisory.

```bash
KUMA=/home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml
VERSION=$(docker exec uptime-kuma-dev1 node -p "require('/app/package.json').version")
DATE=$(date +%Y%m%d)

# 1. Keep the running image as an explicit rollback tag, so a later pull cannot remove it.
docker tag "louislam/uptime-kuma:${VERSION}" "louislam/uptime-kuma:${VERSION}-rollback"

# 2. Stop, snapshot the whole data directory, start again. The directory is root-owned;
#    going through a throwaway container avoids needing a root shell.
docker compose -f "$KUMA" stop
docker run --rm -v /mnt/ai_storage/uptime-kuma:/u alpine \
  sh -c "mkdir -p /u/backups/pre-${VERSION}-${DATE} && cp -a /u/data /u/backups/pre-${VERSION}-${DATE}/data"
du -sh "/mnt/ai_storage/uptime-kuma/backups/pre-${VERSION}-${DATE}/data"
docker compose -f "$KUMA" start

# 3. Pull and recreate.
docker compose -f "$KUMA" pull
docker compose -f "$KUMA" up -d

# 4. Watch the migration finish. A migration error means restore, not retry.
docker logs -f uptime-kuma-dev1
```

Verification after the recreate:

```bash
docker ps --filter name=uptime-kuma-dev1      # version and (healthy)
docker exec uptime-kuma-dev1 node -p "require('/app/package.json').version"
curl -s -o /dev/null -w 'root=%{http_code}\n' http://127.0.0.1:3700/        # expect 302
curl -s -o /dev/null -w 'metrics=%{http_code}\n' http://127.0.0.1:3700/metrics  # expect 401, see below
```

`/metrics` returning `401` is correct: the endpoint exists but requires a bearer token from the
Kuma settings UI. `404` would mean the endpoint is absent on this build.

Row counts are the fastest proof that history survived. Compare against the last known baseline
for the release being upgraded from:

```bash
rm -rf /tmp/kuma-chk && mkdir -p /tmp/kuma-chk
cp /mnt/ai_storage/uptime-kuma/data/kuma.db* /tmp/kuma-chk/
sqlite3 /tmp/kuma-chk/kuma.db 'PRAGMA integrity_check;'      # expect: ok
for t in monitor heartbeat stat_daily stat_hourly stat_minutely notification; do
  printf '%-16s ' "$t"; sqlite3 /tmp/kuma-chk/kuma.db "select count(*) from $t;"
done
```

Copying into `/tmp` first matters: SQLite needs write access to the directory to create `-shm`, so a
`-readonly` open of the root-owned directory fails with `attempt to write a readonly database`.

Finally, record the new exact tag in `infra/docker/uptime-kuma-dev1.yml`. The whole point of pinning
is that the next restart cannot migrate the database without a human deciding to.

### Upgrade log

| Date | From | To | Result |
|---|---|---|---|
| 2026-11-13 | 2.4.0 | 2.5.11 | Snapshot `pre-2.4.0-20261113`. Integrity `ok`; monitors 15/15, heartbeats 24107 → 24131, stat_daily 2337, stat_hourly 9473, stat_minutely 17867, notification 1 — all unchanged or grown. No migration error in logs. |

## Rollback

Use the snapshot, not an in-place downgrade: the migrated schema will not open under the old image.

```bash
KUMA=/home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml

docker compose -f "$KUMA" stop
mv /mnt/ai_storage/uptime-kuma/data "/mnt/ai_storage/uptime-kuma/data.failed-$(date +%Y%m%d-%H%M%S)"
cp -a /mnt/ai_storage/uptime-kuma/backups/pre-<version>-<YYYYMMDD>/data /mnt/ai_storage/uptime-kuma/data
# point the compose file's image line back at <version>-rollback, then:
docker compose -f "$KUMA" up -d
```

Monitors stop being polled for the duration of the rollback, so expect one gap in every monitor's
uptime chart. That is cheaper than a run against a half-migrated database.

## Troubleshooting
- Initial permission issues: remove user override and let container chown /app/data on first start, then re-apply user if needed.

## Deploy (copy/paste)
```bash
# Create data dir with permissions
sudo mkdir -p /mnt/ai_storage/uptime-kuma/data
sudo chown -R 2001:1006 /mnt/ai_storage/uptime-kuma
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/uptime-kuma

# Start the container
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/uptime-kuma-dev1.yml up -d

# Enable Nginx site (host uses no .conf suffix)
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh \
	/home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/kuma.conf kuma

# Verify
curl -I https://kuma.termitetowers.ca
```
