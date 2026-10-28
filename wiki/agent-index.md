<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/agent-index.md % -->
<!-- %ccm_git_object_id: wiki/agent-index.md@190 % -->
<!-- %ccm_git_commit_date: 2026-10-28 16:35:23 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: refactor(context): retire memory-bank and add %%ccm_compact status headers % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-10 mpegg  docs(hal): correct stale audit facts against live HA  -->
 <!-- %git_commit_history: 2026-09-25 mpegg  docs: mark Homarr retired in the network map and agent index  -->
# Agent Index — TermiteTowers

> The single entry point for AI-agent sessions (and any human who wants the same
> 60-second orientation). Read this first, then `hams/docs/hal-context.md`.

## What this is

This repo is the source of truth for the TermiteTowers smart-home / infrastructure
estate: Home Assistant ("HAL"), the Docker app stack, networking, and the ops wiki.

The **wiki** is the Markdown in `wiki/` (plus docs living in `hams/`, `infra/`, and
`git-automation/`), rendered by MkDocs Material — `site_url: https://docs.termitetowers.ca`,
served on host port **3210**. It is **not** Wiki.js (see "Status notes" below).

## First 60 seconds

1. Read this file.
2. Read `docs/status/active-context.md` — what the project is doing **now**: current
   focus, live decisions, next steps.
3. Read `hams/docs/hal-context.md` — the HAL instance snapshot (topology, entity
   naming, integration/add-on stack, gotchas).
4. If the task touches Home Assistant, also read `hams/docs/SKILL.md`.
5. Before an architectural change read `wiki/system-patterns.md`; before a dependency or
   tooling change read `wiki/tech-context.md`.

## Where things live

| Kind of content | Where | Published? |
|---|---|---|
| Orientation, how-tos, service runbooks | `wiki/` | yes — `*.md` only |
| Cross-cutting invariants and tech constraints | `wiki/system-patterns.md`, `wiki/tech-context.md` | yes |
| Volatile status: focus, decisions, progress | `docs/status/` | **no** |
| Long-form runbooks and investigations | `docs/runbooks/`, `docs/investigations/` | **no** |

`docs/` is tracked and CCM-managed but sits outside `docs_dir: wiki`, so it never reaches
the published site. That is deliberate — status documents name hosts, accounts and failure
modes that are operationally useful and not useful to publish.

**Never hand-write a "last updated" date.** Freshness comes from git:

```bash
git log -1 --format=%cI -- docs/status/active-context.md
```

## Out of scope for this repo

- The photo-library database is a separate store; this repo only holds scripts that read
  or export from it (`media/`).
- Home Assistant *runtime* state is not stored here. Docs are snapshots, not truth — query
  `hal-mcp__*`.

## Data sources (MCP → live stores)

| Namespace | Backing store | Key schemas/tables | Join keys |
|---|---|---|---|
| `hal-mcp__*` | Home Assistant | entities, devices, automations, add-ons | identifiers, mac, ieee_address, mqtt_topic |
| `pg-query-ttdb__*` | Postgres `ttdb_dev1` (host) | dhcp_history, kea, watchyourlan, water_meter, powerdns, nextcloud, snipeit | mac_address, ip_address, hostname |
| `pg-query-ttphoto__*` | Postgres (photo library) | images, image_tags, tag_history, stacks | — |

Join HAL ↔ `ttdb` on **MAC / IP / hostname**. Always query live — never trust a
cached state from a doc.

## Naming & standards

- Devices: `wiki/Device-Naming-Standard.md`, `hams/esphome/ESP32-Naming-Standard.md`
- Docker networks (CIDR map): `wiki/docker-networks.md`
- Port allocation: `wiki/ports.md`
- Compose conventions: `wiki/compose-conventions.md`
- Script standards: `wiki/script-standards.md`
- Database strategy: `wiki/databases.md` (one Postgres, schema-per-service,
  `dev1 → prd1 → arc1` promotion)

## Operational how-tos

- Add a Docker app: `wiki/how-to-add-docker-app.md`
- Add an MCP server: `wiki/how-to-add-mcp-server.md`
- Decommission a Docker app: `wiki/how-to-decommission-docker-app.md`

## Service runbooks

`wiki/runbook-*.md` — one per service (openwebui, lobechat, mkdocs, uptime-kuma,
dozzle, ha-hal-bridge, ha-handler, water-meter, vault, ollama, …).

## Status notes & gotchas

- **Wiki.js is deprecated and on hold** — do not decommission it yet. MkDocs is the live wiki.
- **Homarr is retired (2026-09-26)** - container removed, the `home` vhost disabled, compose + env files deleted. `wiki/runbook-homarr.md` carries the revival path.
- Node-RED add-on is stopped and a candidate for removal — back up its flows first.
- The phantom "YAML-defined automation" (`automation.llm_hooktest_1`) is **gone**
  (deleted 2026-10-10). It was a config-less *registry* orphan — no YAML body ever
  existed and the repo has **no `automations.yaml`**; the stale registry entry
  (`unique_id: office_light_webhook`) was removed with `ha_remove_entity`. There is
  no longer a blind spot in any "scan all automations".
- MkDocs publishes only `*.md` (plus stylesheets); every other repo file (env files,
  secrets, scripts) is excluded by `mkdocs.yml`.

## Backups

- `wiki/backup-strategy.md` · `wiki/critical-infrastructure.md`
