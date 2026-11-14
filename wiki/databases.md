<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/databases.md % -->
<!-- %ccm_git_object_id: wiki/databases.md@222 % -->
<!-- %ccm_git_commit_date: 2026-11-13 19:48:39 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: database doc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-11-13 mpegg feat(monitoring): archive Kuma history from kuma.db into ttdb_dev1 -->
<!-- %git_commit_history: 2025-10-10 mpegg big update -->
🧠 PostgreSQL Database Strategy — Termite Towers
🎯 Purpose
Establish a clear, traceable PostgreSQL structure for service isolation, environment promotion, and archival hygiene. Development state lives in a dedicated database and, **only where the service supports it**, in a dedicated schema of `ttdb_dev1`. Services that ship with their own database engine (PowerDNS, PowerDNS Admin, Snipe-IT) run that engine in their own container and are not on the host cluster at all.

🗂 Databases on the host cluster (PostgreSQL 16, monolith, port 5432)

| Database | Purpose |
|---|---|
| `ttdb_dev1` | Development — shared home for services that store state in a schema. **Kea DHCP's live store.** |
| `ttdb_prd1` | Production — promoted from `ttdb_dev1` after validation (not yet created) |
| `ttdb_arc1` | Archive — long-term storage of historical or retired data (not yet created) |
| `ttphoto_dev1` | Photo library — own database, own owner role |
| `tthealth_dev1` | Health data — own database, own owner role |
| `nextcloud` | Nextcloud — **own database** `nextcloud`, role `nextcloud`. Nextcloud's `config.php` has no `db_schema` key, so it cannot target a schema inside `ttdb_dev1` |
| `kea` | **Legacy and inactive.** Pre-migration Kea store. Kea no longer connects to it; it is in no backup job |
| `powerdns` | **Empty vestige** — `template1`-sized shell with no user objects. PowerDNS does not use it |
| `test_dev1` | Scratch database |

`dev1`, `prd1` and `arc1` are spelled with underscores by the server (`ttdb_dev1`). The hyphenated `ttdb-dev1` in older prose is the same database.

🔁 Promotion Workflow
Develop in ttdb_dev1

New schemas (e.g. `dhcp_history`, `monitoring`, `havoc`, `inventory`) created here

Full forensic traceability: schema ownership, role privileges, audit triggers

Promote to ttdb_prd1

After validation, schema is exported and rehydrated in ttdb_prd1

Roles and privileges re-applied with production constraints

Archive to ttdb_arc1

Retired or historical data moved here

Read-only roles enforced, indexing optimized for cold storage

🗄 Where each service's state actually lives

| Service | Store | Where it is configured |
|---|---|---|
| Kea DHCP | host cluster → `ttdb_dev1`, schema `kea` | `hosts-database` in `/etc/kea/tt-kea-dhcp4-dev1.conf`: `"name": "ttdb_dev1"`, `"user": "kea"`. `kea.hosts` is the authoritative reservation set. Leases are **not** in Postgres — `lease-database` is `memfile` (`/var/lib/kea/kea-leases4.csv`) |
| DHCP log history | host cluster → `ttdb_dev1.dhcp_history` | [`infra/dhcp/scripts/monitoring/parse-kea-logs.py`](../infra/dhcp/scripts/monitoring/parse-kea-logs.py) |
| WatchYourLAN | host cluster → `ttdb_dev1.watchyourlan` | the service writes its own schema |
| Uptime Kuma archive | host cluster → `ttdb_dev1.monitoring` | [`scripts/archive-monitor-history.sh`](../scripts/archive-monitor-history.sh) |
| Water meter | host cluster → `ttdb_dev1.water_meter` | table `meter_readings` |
| PowerDNS (zones) | **own container** `powerdns-db-dev1`, MySQL 8.0, database `powerdns` | [`infra/docker/powerdns-dev1.yml`](../infra/docker/powerdns-dev1.yml) |
| PowerDNS Admin | **own container** `powerdns-admin-db-dev1`, PostgreSQL 15, database `powerdnsadmin` | [`infra/docker/powerdns-dev1.yml`](../infra/docker/powerdns-dev1.yml) |
| Nextcloud | host cluster → **own database** `nextcloud` | `POSTGRES_DB=nextcloud`, `POSTGRES_HOST=host.docker.internal` |
| Snipe-IT | **own container** `snipeit-db-dev1`, MariaDB 10.11, database `snipeit` | [`infra/docker/snipeit-dev1.yml`](../infra/docker/snipeit-dev1.yml) |

Consequence: `ttdb_dev1` still contains empty `powerdns`, `snipeit` and `nextcloud` schemas left over from the original schema-per-service plan. Nothing writes to them; see the schema table below.

🔐 Role Strategy
Each service that stores state in the shared database gets a dedicated role:

kea, dhcp_history, watchyourlan, water_meter

Roles are scoped to their schema only

Passwords managed via secrets vault or .pgpass

`snipeit`, `nextcloud` and `powerdns` roles also exist but own only empty schemas (or, for `nextcloud`, an empty schema in `ttdb_dev1` — its real database is `nextcloud`).

✅ Kea migration — complete
Kea's `hosts-database` points at `ttdb_dev1` with role `kea`, and `ttdb_dev1.kea.hosts` holds the live reservation set. The legacy `kea` database received no writes and hosts no application connections; it remains on the cluster only until someone confirms its contents and drops it. It is not in any backup job, so anything still inside it is the only copy.

🧼 Operational Hygiene
No cross-schema access

No shared roles across databases

All schema changes tracked via Git + audit triggers

Archive DB (ttdb_arc1) purged quarterly of expired data

📊 Schemas in ttdb_dev1

| Schema | Contents | Created by |
|---|---|---|
| `dhcp_history` | DHCP lease events | [`infra/dhcp/scripts/monitoring/setup-dhcp-history-db.sh`](../infra/dhcp/scripts/monitoring/setup-dhcp-history-db.sh) |
| `watchyourlan` | Host presence history | WatchYourLAN |
| `kea` | Kea host reservations (`hosts`, 62 rows). Lease/subnet/pool tables are empty by design | Kea, via `hosts-database` |
| `water_meter` | Water meter readings (`meter_readings`) | the service |
| `monitoring` | Uptime Kuma availability archive: `monitor`, `monitor_daily`, `monitor_incident`, `archive_run` | [`infra/sql/monitoring/schema.sql`](../infra/sql/monitoring/schema.sql) |
| `powerdns` | **Empty.** `domains` and `records` exist with 0 rows; PowerDNS uses its own MySQL container instead | planned, never populated |
| `snipeit` | **Empty.** No tables; Snipe-IT uses its own MariaDB container | planned, never populated |
| `nextcloud` | **Empty.** No tables; Nextcloud uses its own `nextcloud` database | planned, never populated |

`monitoring` is written nightly by
[`scripts/archive-monitor-history.sh`](../scripts/archive-monitor-history.sh),
which reads Uptime Kuma's `kuma.db` directly — **not** Prometheus — so the ~180
days Kuma already holds are captured rather than only what a scrape job saw.
Daily granularity plus discrete incidents; see
[`runbook-monitoring-archive.md`](runbook-monitoring-archive.md).

Only `ttdb_dev1` is dumped by the scheduled backup
([`infra/systemd/user/tt-backup-db-ttdb.service`](../infra/systemd/user/tt-backup-db-ttdb.service)),
which asserts the presence of `dhcp_history`, `kea`, `monitoring`, `powerdns`,
`snipeit`, `water_meter` and `watchyourlan`. The `nextcloud` database and the
legacy `kea` and `powerdns` databases have no backup job of their own.

Two notes for anyone querying `monitoring`:

- `monitor_key` is `kuma:<numeric id>`, which survives monitor renames.
- The read-only MCP role (`mcp_readonly`) is granted `USAGE` on the schema and
  `SELECT` on its tables explicitly. A schema recreated from scratch needs those
  grants re-applied; ownership alone does not give it access.
