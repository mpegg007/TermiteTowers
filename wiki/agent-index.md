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
2. Read `hams/docs/hal-context.md` — the HAL instance snapshot (topology, entity
   naming, integration/add-on stack, gotchas).
3. If the task touches Home Assistant, also read `hams/docs/SKILL.md`.

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
dozzle, homarr, ha-hal-bridge, ha-handler, water-meter, vault, ollama, …).

## Status notes & gotchas

- **Wiki.js is deprecated and on hold** — do not decommission it yet. MkDocs is the live wiki.
- Node-RED add-on is stopped and a candidate for removal — back up its flows first.
- One YAML-defined automation (`automation.llm_hooktest_1`) is invisible to the REST
  config API — account for it in any "scan all automations".
- MkDocs publishes only `*.md` (plus stylesheets); every other repo file (env files,
  secrets, scripts) is excluded by `mkdocs.yml`.

## Backups

- `wiki/backup-strategy.md` · `wiki/critical-infrastructure.md`
