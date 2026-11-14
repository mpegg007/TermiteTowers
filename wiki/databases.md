<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/databases.md % -->
<!-- %ccm_git_object_id: wiki/databases.md@220 % -->
<!-- %ccm_git_commit_date: 2026-11-13 19:11:14 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: feat(monitoring): archive Kuma history from kuma.db into ttdb_dev1 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2025-10-10 mpegg big update -->
🧠 PostgreSQL Database Strategy — Termite Towers
🎯 Purpose
Establish a clear, traceable PostgreSQL structure for service isolation, environment promotion, and archival hygiene. This replaces legacy kea usage with a structured multi-DB approach.

🗂 Database Layout
Database	Purpose
kea	Legacy — used by Kea DHCP; slated for migration
ttdb-dev1	Development — all new services and schemas start here
ttdb-prd1	Production — promoted from ttdb-dev1 after validation
ttdb-arc1	Archive — long-term storage of historical or retired data
🔁 Promotion Workflow
Develop in ttdb-dev1

New schemas (e.g. powerdns, havoc, inventory) created here

Full forensic traceability: schema ownership, role privileges, audit triggers

Promote to ttdb-prd1

After validation, schema is exported and rehydrated in ttdb-prd1

Roles and privileges re-applied with production constraints

Archive to ttdb-arc1

Retired or historical data moved here

Read-only roles enforced, indexing optimized for cold storage

🔐 Role Strategy
Each service gets a dedicated role:

kea, powerdns, havoc, etc.

Roles are scoped to their schema only

Passwords managed via secrets vault or .pgpass

🧪 Migration Plan for Kea
Create kea schema inside ttdb-dev1

Export data from legacy kea DB

Re-import into ttdb-dev1.kea

Validate backend hooks and schema alignment

Promote to ttdb-prd1.kea once confirmed

🧼 Operational Hygiene
No cross-schema access

No shared roles across databases

All schema changes tracked via Git + audit triggers

Archive DB (ttdb-arc1) purged quarterly of expired data

📊 Schemas in ttdb_dev1

| Schema | Contents | Created by |
|---|---|---|
| `dhcp_history` | DHCP lease events | `infra/dhcp/scripts/monitoring/setup-dhcp-history-db.sh` |
| `watchyourlan` | Host presence history | WatchYourLAN |
| `kea`, `powerdns`, `snipeit`, `water_meter` | Per-service state | the service |
| `monitoring` | Uptime Kuma availability archive: `monitor`, `monitor_daily`, `monitor_incident`, `archive_run` | [`infra/sql/monitoring/schema.sql`](../infra/sql/monitoring/schema.sql) |

`monitoring` is written nightly by
[`scripts/archive-monitor-history.sh`](../scripts/archive-monitor-history.sh),
which reads Uptime Kuma's `kuma.db` directly — **not** Prometheus — so the ~180
days Kuma already holds are captured rather than only what a scrape job saw.
Daily granularity plus discrete incidents; see
[`runbook-monitoring-archive.md`](runbook-monitoring-archive.md).

Two notes for anyone querying it:

- `monitor_key` is `kuma:<numeric id>`, which survives monitor renames.
- The read-only MCP role (`mcp_readonly`) is granted `USAGE` on the schema and
  `SELECT` on its tables explicitly. A schema recreated from scratch needs those
  grants re-applied; ownership alone does not give it access.
