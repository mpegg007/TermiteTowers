<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: infra/docker/README.nextcloud.md % -->
<!-- %ccm_git_object_id: infra/docker/README.nextcloud.md@200 % -->
<!-- %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: zoo.261109 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Nextcloud Stack (host PostgreSQL, data on the gallery array)

Nextcloud file sync and sharing, published as **https://filebank.analacres.ca**.

The public name is `filebank`. The **internal identity is still `nextcloud`** — container
name, ZFS dataset, database, env file and this document. The hostname is a URL, not a
rename of the service.

---

## 1. Shape of the deployment

| Item | Value |
| --- | --- |
| Container | `nextcloud-dev1`, image `nextcloud:32.0.5-apache` (pinned) |
| Host port | `3230` → container `80` |
| Public name | `filebank.analacres.ca` on the shared analacres TLS listener, port **3261** |
| Old name | `nextcloud.termitetowers.ca` → permanent redirect to `filebank` |
| Network | `app-services-net-dev1` (external, `10.10.16.0/20`) |
| Database | **own database** `nextcloud` on the host PostgreSQL cluster, role `nextcloud` |
| User data | `/gallery/nextcloud/data` → `/var/www/html/data` (**ZFS dataset**, mirrored array) |
| Code and config | `/mnt/ai_storage/nextcloud/` (NVMe) |
| Application log | `/mnt/ai_storage/nextcloud/log/nextcloud.log` (NVMe, rotated) |

### Why the data directory is a separate mount

[`nextcloud-dev1.yml`](nextcloud-dev1.yml) mounts five paths. Only one is bulk:

| Container path | Host path | Media | Why |
| --- | --- | --- | --- |
| `/var/www/html` | `/mnt/ai_storage/nextcloud/data` | NVMe | image-managed code, rewritten by every upgrade |
| `/var/www/html/config` | `/mnt/ai_storage/nextcloud/config` | NVMe | instance config, restored beside the DB dump |
| `/var/www/html/custom_apps` | `/mnt/ai_storage/nextcloud/custom_apps` | NVMe | installed apps |
| `/var/www/html/data` | `/gallery/nextcloud/data` | ZFS array | user data — the only irreplaceable bytes |
| `/var/log/nextcloud` | `/mnt/ai_storage/nextcloud/log` | NVMe | app log, must never live inside the backed-up tree |

Keeping the log off the array is deliberate. A previous instance accumulated a **2.8 GB
unrotated `nextcloud.log`** inside its data directory, which would have been uploaded to
Jotta byte-for-byte on every backup pass.

---

## 2. Database

### It is a database, not a schema

Nextcloud's `config.php` has **no `db_schema` key** — only `dbname`, `dbhost`, `dbuser` and
`dbtableprefix`. It cannot be pointed at a schema inside a shared database, so the
`wiki/databases.md` schema-per-service pattern does not apply here. Nextcloud's own admin
manual states a dedicated database and user per service.

### Creation statement (from the Nextcloud admin manual)

```sql
CREATE ROLE nextcloud LOGIN PASSWORD '<generated>' CREATEDB;
CREATE DATABASE nextcloud OWNER nextcloud TEMPLATE template0 ENCODING 'UTF8';
GRANT CREATE ON SCHEMA public TO nextcloud;
```

Notes that matter on this cluster:

- **`TEMPLATE template0`** is what guarantees a clean database with the cluster's default
  locale. Building from `template1` inherits anything ever added there.
- **No collation clause.** Nextcloud recommends none; it asks only for `UTF8`.
- **`CREATEDB`** is in the documented statement. Without it the install still fails on some
  paths, so it is granted.
- **`GRANT CREATE ON SCHEMA public`** is required on PostgreSQL 15+, where `PUBLIC` lost
  `CREATE` on the `public` schema.

### Connection details that are easy to get wrong

| Fact | Value | Consequence if wrong |
| --- | --- | --- |
| Container → host address | `host.docker.internal` = **`172.17.0.1`** (docker0), **not** the app-network gateway `10.10.16.1` | a `pg_hba` rule written for `10.10.16.0/20` never matches |
| `password_encryption` | `scram-sha-256` (PostgreSQL 16 default) | an `md5` `pg_hba` rule **cannot** authenticate a scram-stored password; the failure looks like a wrong password |
| Role `search_path` | must be left at the default | if the role carries `search_path=<somename>`, `CREATE TABLE` fails with `no schema has been selected to create in` and the installer dies partway |
| `listen_addresses` | `*` | if loopback-only, nothing reaches the container at all |

`pg_hba.conf` on this host is `0640 postgres:postgres`, so it needs `sudo` to read.
**Confirm a rule with a deliberate wrong-password probe instead** — it needs no privileges:

```bash
docker exec nextcloud-dev1 php -r 'try { new PDO("pgsql:host=host.docker.internal;port=5432;dbname=nextcloud","nextcloud","deliberately-wrong"); } catch (PDOException $e) { echo $e->getMessage(), "\n"; }'
```

- `password authentication failed for user "nextcloud"` → a rule exists and matched.
- `no pg_hba.conf entry for host ...` → no rule matches; add one for `172.17.0.0/16` with
  `scram-sha-256`.

Checking the role's configuration without superuser rights:

```bash
psql -d postgres -At -c "select rolname, rolconfig from pg_roles where rolname='nextcloud';"
# expected: nextcloud | (empty)
# repair:   ALTER ROLE nextcloud RESET search_path;   -- requires postgres
```

---

## 3. Filesystem ownership — the Jotta contract

`/gallery` is mounted **`noacl`**, so POSIX ACLs cannot be used. `setfacl` will fail. The
mechanism is **setgid plus group ownership**:

```
/gallery/nextcloud/data     drwxrws---  33:1006   (www-data:tt-ai-storage)
```

Nextcloud writes `0644` files and `0755` directories as `www-data` (uid 33). With the setgid
bit on the directory, created files inherit group `tt-ai-storage` (gid 1006), so `jottad` —
which runs as `mpegg-adm`, a member of `tt-ai-storage` but **not** of `tt-backup` — can read
them.

The image is **deliberately not run as a non-root user.** Its apache entrypoint is built
around starting as root, and setgid on the mount achieves the same contract with no
entrypoint risk. Verified by canary rather than assumed:

```bash
docker exec nextcloud-dev1 sh -c 'echo probe > /var/www/html/data/.jotta-perm-canary'
stat -c '%A %U:%G %n' /gallery/nextcloud/data/.jotta-perm-canary   # expect ... www-data tt-ai-storage
test -r /gallery/nextcloud/data/.jotta-perm-canary && echo READ-OK  # as mpegg-adm, not root
docker exec nextcloud-dev1 rm -f /var/www/html/data/.jotta-perm-canary
```

If a file stops being group-readable, `jotta-cli status` will still list the folder and
`~/.jottad/jottabackup.log` will say nothing. There is no error to find — only a file that
never uploads.

---

## 4. Secrets

`infra/docker/env/nextcloud.env` is **gitignored** ([`.gitignore`](../../.gitignore) line
`infra/docker/env/*.env`) and must be mode `600`. Keys:

| Key | Purpose |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | consumed **only on first install** |
| `NEXTCLOUD_DATA_DIR` | `/var/www/html/data` |
| `NEXTCLOUD_ADMIN_USER`, `NEXTCLOUD_ADMIN_PASSWORD` | first admin account, created on install |
| `NEXTCLOUD_TRUSTED_DOMAINS` | `filebank.analacres.ca nextcloud.termitetowers.ca localhost` |
| `TZ` | container timezone |

There is no `POSTGRES_SCHEMA` key. It existed in the old file and was dead configuration —
Nextcloud ignores it.

**These values are read only when the instance is installed.** Changing them later does not
re-point a live instance; `config.php` wins. To rotate the database password you must change
it in both places (`ALTER ROLE` and the env file).

---

## 5. Directory layout and symlinks

```bash
sudo mkdir -p /srv/dev1/nextcloud/docker/env
sudo ln -sfn /home/mpegg-adm/source/TermiteTowers/infra/docker/nextcloud-dev1.yml \
             /srv/dev1/nextcloud/docker/nextcloud-dev1.yml
sudo ln -sfn /home/mpegg-adm/source/TermiteTowers/infra/docker/env/nextcloud.env \
             /srv/dev1/nextcloud/docker/env/nextcloud.env
```

The dataset and its permissions are created with one privileged step:

```bash
sudo bash -c '
zfs create -o mountpoint=/gallery/nextcloud -o compression=lz4 -o refquota=1500G gallery/nextcloud
mkdir -p /gallery/nextcloud/data /mnt/ai_storage/nextcloud/log
chown 33:1006 /gallery/nextcloud/data /mnt/ai_storage/nextcloud/log
chmod 2770 /gallery/nextcloud/data
chmod 2750 /mnt/ai_storage/nextcloud/log'
```

`refquota=1500G` is the backstop. Per-user quota (`default_quota`) is the normal control, so
one runaway sync cannot fill the pool and stall Immich writes.

---

## 6. Start and verify

```bash
cd /srv/dev1/nextcloud/docker
docker compose -f nextcloud-dev1.yml up -d
docker compose -f nextcloud-dev1.yml config --quiet    # validates without printing secrets

docker exec -u www-data nextcloud-dev1 php occ status
# the one line that proves the rebuild worked:
#   dbtype must be pgsql, not sqlite3
```

Publishing is handled by the house script, which snapshots nginx, issues the per-host
certificate, runs `nginx -t` and refuses to reload on failure:

```bash
./scripts/deploy-analacres-hosts.sh            # includes the nextcloud vhost + filebank cert
./scripts/deploy-analacres-hosts.sh --dry-run  # show what it would do
```

The A record is published by [`infra/dns/godaddy-ddns.sh`](../../infra/dns/godaddy-ddns.sh),
which carries an explicit `analacres.ca:filebank` entry.

Verify over loopback first, so LAN DNS and router hairpinning cannot mask a bad vhost:

```bash
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  --resolve filebank.analacres.ca:3261:127.0.0.1 https://filebank.analacres.ca:3261/
# expect: 302 https://filebank.analacres.ca/index.php/login
```

### Installing by hand

If the entrypoint does not install automatically, the usual cause is a **0-byte
`config/config.php`** — its mere presence makes the installer think the instance exists.
Remove it and install explicitly:

```bash
docker exec nextcloud-dev1 rm -f /var/www/html/config/config.php
docker exec -u www-data nextcloud-dev1 php occ maintenance:install \
  --database pgsql --database-name nextcloud --database-host host.docker.internal \
  --database-user nextcloud --database-pass '<generated>' \
  --admin-user admin --admin-pass '<generated>' --data-dir /var/www/html/data
```

---

## 7. Runtime configuration applied after install

```bash
occ config:system:set trusted_domains 0 --value=filebank.analacres.ca
occ config:system:set trusted_proxies 0 --value=172.17.0.1
occ config:system:set overwritehost --value=filebank.analacres.ca
occ config:system:set overwriteprotocol --value=https
occ config:system:set overwrite.cli.url --value=https://filebank.analacres.ca
occ config:system:set logfile --value=/var/log/nextcloud/nextcloud.log
occ config:system:set loglevel --value=2 --type=integer
occ config:system:set log_rotate_size --value=104857600 --type=integer
occ config:system:set default_quota --value=100GB
occ background:cron
```

`trusted_proxies` is what makes `X-Forwarded-For` authoritative. Without it every request
appears to come from the proxy, which breaks per-client rate limiting and makes brute-force
protection act on the wrong identity.

`log_rotate_size` is 100 MB, and the host runs `logrotate` with `copytruncate` on the same
file — the app rotates its own log, and `logrotate` is the backstop if it ever stops doing so.
See [`infra/logrotate/logrotate.d/tt-apps.conf`](../../infra/logrotate/logrotate.d/tt-apps.conf).

---

## 8. Gating

The vhost is **gate-ready, not gated**: `location /` includes `snippets/tt-gate.conf`, which
is inert until Authelia is deployed. The client-facing prefixes deliberately do **not**
include it, because they authenticate per request or are opened by people with no account:

`/remote.php/` (WebDAV, app passwords), `/public.php/` (share links), `/ocs/`, `/status.php`,
`/login`, `/index.php/login`, `/apps/theming/`, `/dist/`, `/core/`

Getting that list wrong breaks desktop sync in a way that looks like a network fault.

---

## 9. Monitoring

Home Assistant's Nextcloud integration polls
`/ocs/v2.php/apps/serverinfo/api/v1/info` once a minute as **`hal-adm`**. It needs an
admin-capable account, and it must be configured with the `filebank` hostname — a redirect
to another host drops the basic-auth header, which is what produced a stream of `401`s and
brute-force throttling on the previous instance.

An unauthenticated client hitting that endpoint will always trip brute-force protection.
Point non-authenticating checks at `/status.php`, which needs no session.

---

## 10. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Login failed: <user>` | the account does not exist — `occ user:list` is authoritative. `mpegg-adm` is a **Unix** account, not necessarily a Nextcloud one |
| `429 Reached maximum delay` | brute-force protection; a poller is authenticating with wrong credentials. Check `occ security:bruteforce:attempts <ip>` and `reset <ip>` |
| `no schema has been selected to create in` | the role carries a stale `search_path`; `ALTER ROLE nextcloud RESET search_path` |
| `password authentication failed` from the container only | `pg_hba` rule uses `md5` against a scram cluster, or the wrong CIDR |
| Sync works, files never reach Jotta | the `tt-ai-storage` group or setgid bit is missing on `/gallery/nextcloud/data` |
| Login page loads but login redirects in a loop | `overwritehost` / `overwriteprotocol` / `trusted_proxies` disagree with the vhost |

---

See [`scripts/deploy-analacres-hosts.sh`](../../scripts/deploy-analacres-hosts.sh),
[`plans/nextcloud-storage-and-jotta.md`](../../plans/nextcloud-storage-and-jotta.md) §6 for the
2026-11-08 measurements, and [`wiki/how-to-add-docker-app.md`](../../wiki/how-to-add-docker-app.md)
for house standards.
