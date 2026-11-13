<!-- %ccm_compact: path=docs/status/progress.md branch=dev1 committed=2026-11-13T12:45:45-05:00 sha=bffeccc -->
# Progress

What works, what is broken, what will bite. Freshness comes from git, not a hand-written
date:

```bash
git log -1 --format=%cI -- docs/status/progress.md
```

Entries marked **(carried forward)** came from the retired memory bank and were not
re-verified in the current session. Treat them as leads, not facts.

## What works

| Capability | Status | Evidence |
|---|---|---|
| MkDocs documentation site | Working, live reload broken | `mkdocs.yml` complete; `docs_dir: wiki`, port 3210; edits need `docker restart mkdocs_app-dev1` (see Broken #10) |
| Wiki content breadth | Working | 50+ pages including service runbooks |
| Documentation symlink layout | Working | `wiki/hams`, `wiki/infra`, `wiki/git-automation` |
| CCM header automation | v2 active | `git-automation/v2/`; v1 is rollback-only |
| Header traceability | Working | `install-hooks.sh --verify` reports runtime evidence, because stub and symlink failures are both silent |
| `%ccm_compact` mode | Working | `tests/git-automation/test_compact_header.sh`, 9 assertions pass |
| Production deploy pipeline | rsync step works | `deploy-prd.yml`; runner `tt-prd` active on `monolith` |
| Water-meter project | Working, self-contained | `water-meter/` + FastAPI viewer on 3414 |
| Postgres schema strategy | Defined | `wiki/databases.md`; `ttdb-dev1 → ttdb-prd1 → ttdb-arc1` |
| Port allocation scheme | Defined and in use | `wiki/ports.md`, 3000–3999 in ten bands |
| Nginx served from prod tree | Applied and verified | `infra/nginx/RELOCATION-PLAN.md`, 39/39 + 37/37 links retargeted |
| Backup encryption | Redesigned | per-tier age recipients + master-wrapped keyring, phases 1/2/3/5; phase 4 unaccounted |
| Database backups `ttdb_dev1` + `ttphoto_dev1` | **Working, first run proven 2026-11-13** | user-level timers, schema-asserted dumps (818 / 189 objects), Jotta **Up to date** for both roots; first scheduled fire 2026-11-14 03:54/04:10 EST |
| Uptime Kuma | 2.5.11 pinned | upgraded from 2.4.0 2026-11-13; snapshot `pre-2.4.0-20261113`; rollback tag `2.4.0-rollback`; upgrade log in `wiki/runbook-uptime-kuma.md` |
| Monitoring archive | Schema + archiver written, **not scheduled** | `infra/sql/monitoring/schema.sql`, `scripts/archive-monitor-metrics.sh`; no Prometheus job, no timer, schema not applied |
| Per-tier secrets (`dev1`) | Complete | every dev1 service on the tiered root; path check enforced in CI and pre-commit; `uat1`/`prd1` roots outstanding |
| Prometheus metrics layer | Implemented, phases 0-7 | `infra/docker/prometheus/`, node-exporter, docker metrics, textfile backup freshness, alert timer |
| Shell environment tooling | Working | `util/install.sh`, region-aware prompt, `goapp`/`cdapp` |
| Git hook tests | Present | `tests/git-automation/` |

## Broken or blocked

### 1. Production deploy is red — one step, by decision

`Install production dependencies` runs `pip install -e /srv/prd/tt` against a repo with no
root packaging. **Not urgent** — rsync is step 1 and succeeds, so code lands. The
documented rule is to watch step 1. Deferred by decision 2026-10-07; fix only when a real
Python dependency need appears, via Option B (root packaging metadata). Option A
(repointing pip at `water-meter/`) was explicitly rejected.

### 2. CI install step cannot succeed as written

`ci.yml` runs `pip install -e ".[dev]"` from the repo root; no root packaging metadata
exists. Same root cause as (1), different workflow. Not observed failing — flagged, not
confirmed.

### 3. `docs/` relocation was uncommitted **(resolved by this change)**

The two tracked `memory-bank/` documents showed as deleted while their replacements sat
untracked under `docs/`, so a fresh clone received neither. Committing the relocation
together with the retirement of `memory-bank/` resolves it.

### 4. Stale READMEs

- Root `README.md` — describes root `nginx/`/`docker/` compatibility symlinks; neither
  exists. Body is UTF-16LE behind a UTF-8 prefix; its CCM header still claims
  `ccm_size: 1899` and `ccm_file_encoding: binary`.
- `infra/README.md` — still presents its layout as "Proposed".

### 5. Web-root relocation pending

`/var/www/*` → mirror-symlink migration is **SCRIPT READY, APPLY PENDING**, blocked by an
ordering guard until the mirror carries the published page. Deliberate, not a failure.

### 6. Backup phase 4 unaccounted for

Commit log covers phases 1, 2, 3, 5. Phase 4 has no commit. Unverified whether it was
folded into another change or is outstanding.

### 7. `ttmail/` undocumented

Untracked Python package at the repo root. Scope unknown.

### 8. Cosmetic: wrong concurrency group

`deploy-prd.yml` uses `group: jah-prd-deploy`. Repository-scoped, so no cross-repo
collision, but it misreports which service a queued deploy belongs to.

### 9. Unverified: JAH sudoers grant

`/etc/sudoers.d/jah-deploy` could not be diffed non-interactively. If the grant omits
`--quiet`, the workflow's `systemctl is-active --quiet` call presents as
`sudo: a password is required` with no TTY. Requires a manual `sudo cat`.

### 10. MkDocs live reload is dead — served pages go stale silently

The first build after a container start succeeds. Every `mkdocs serve` **reload** build passes
`serve_url`, which sets `InclusionLevel.is_in_serve`, treats `DRAFT` as included, and then
fails while copying a static file it cannot read:

```
PermissionError: [Errno 13] Permission denied: '/docs/wiki/infra/docker/env/ha-mcp.env'
```

That is a real `-rw-------` secret reachable through the `wiki/infra` symlink. When the
reload build raises, the container keeps serving the previous build, so an edit looks
applied when it is not. Workaround: `docker restart mkdocs_app-dev1` after every edit, then
confirm with `curl -s https://docs.termitetowers.ca/<page>/ | grep <marker>`.

That the live site does not publish the secret today is **luck, not a control** — the build
dies before it can serve it. The structural fix (stage only `*.md` into `docs_dir`) is
designed and approved but **not deployed**; three untracked scripts exist under
`scripts/mkdocs/`, and `stage-docs.sh` has since been repaired in the working tree (guard
has its `exit 1` and `fi`, `cleanup` defined before the `trap`). See
`docs/status/active-context.md` for the exact in-tree state.

### 11. The new database backups have never been restored

`ttdb_dev1` and `ttphoto_dev1` now have verified dumps and confirmed offsite copies, but no
restore has been attempted and there is no `restore-db-user.sh`. Only
[`infra/backups/scripts/restore-tthealth.sh`](../infra/backups/scripts/restore-tthealth.sh:1)
exists, and the general-tier dumps additionally need `tt-keys.sh unlock general:2026Q4` with
the master. Until one restore runs, "backed up" means "a file exists offsite", not "the data
can come back".

Also outstanding on this thread: the first timer-triggered run (manual runs only so far),
and `infra/backups/README.md` does not document either job although the units name it as
`Documentation=`.

### 12. Monitoring archive is half-built

`infra/sql/monitoring/schema.sql` and `scripts/archive-monitor-metrics.sh` exist, but the
archiver has no data source: there is no `uptime-kuma` job in
[`infra/docker/prometheus/prometheus.yml`](../infra/docker/prometheus/prometheus.yml:31).
Also missing: the systemd service/timer, `tests/monitoring/`, `wiki/runbook-monitoring-archive.md`,
and the `monitoring` schema itself (verified absent from `ttdb_dev1` on 2026-11-13). Kuma's
`/metrics` returns 401 without an API key, so the metric names the script defaults to are
unverified.

## Landmines

| Issue | Consequence |
|---|---|
| A dot in a sudoers filename | Silently ignored; `/etc/sudoers.d/x.conf` never loads |
| Non-executable git hook | Silently ignored by git, no warning |
| Symlinked git hook | `BASH_SOURCE[0]` resolves to `.git/hooks`; libraries not found; header never applies |
| `remove_ccm_header` with a fixed line cap | History trail is unbounded; a too-small cap aborts the strip and a second header is appended silently. Now uses a subset assertion |
| Relaxing `mkdocs.yml` `exclude_docs` | Would publish env files, `secrets.yaml`, MCP tokens |
| Writing a NUL-byte / UTF-16 file through the hook | Byte-oriented rewriting corrupts it — the root `README.md` hybrid happened this way |
| `config.sh`'s first prompt is the runner **group**, not a label | Answering `tt-prd` there fails with `TaskAgentPoolNotFoundException` |
| Prod `.venv` is hand-made, never created by CI | Deleting it breaks the pip step |
| `rsync --exclude=.env` | Prod `.env` is never managed by CI; on TT it is 0 bytes, owned by `mpegg-adm` not `tt-deploy` |
| Age private material in the tree | `.gitignore` blocks `master.txt`, `master-identity*.txt`, `*.escrow.age`, `keyring.tar.age`, `*.age-identity` as defence in depth; the live identity also lives off `/mnt/ai_storage` so it cannot be uploaded beside the backups it protects |
| `%ccm_compact` checked by whole-file grep | Would silently exempt every doc describing the token from CCM. The check must stay `head -n 1` |
| Per-window `CLINE_DATA_DIR` | Impossible on Linux with the snap; both windows share `~/.cline/data` and can surface `SQLITE_BUSY` |
| The repo mount is not writable by the container user | Any staging/scratch directory placed under `/docs` fails with `EACCES` as uid 2001; it must live on a dedicated writable mount |
| `rsync -a` when staging docs | Preserves symlinks, so the staged tree gets an `infra -> ../infra` link and MkDocs walks straight back into the secret trees. Staging must filter to `*.md` or dereference |
| `mkdocs serve` reload vs `docker restart` | A reload build that raises leaves the old build served; the browser shows stale content with no error. Always confirm with a `curl` marker |
| A table-level grant is not enough for `pg_dump` | `mpegg-adm` could read `kea` tables but not its sequences; the dump died at `dhcp4_audit_id_seq`. `pg_read_all_data` is the grant that covers tables, views **and** sequences |
| `jotta-cli add` is per directory | Adding one root never adopts its siblings, and nothing warns. `jotta-cli status` is the only authority on which roots are covered and whether they are up to date |
| A backup log line that asserts cloud replication | `backup-db-user.sh` prints "cloud replication handled out-of-band" without checking. It is true only while the root is actually registered with jottad — verify with `jotta-cli status` |
| systemd **user** timers need lingering | Without `Linger=yes` a user timer only fires while that user has a live session. `mpegg-adm` has `Linger=yes`; a new account would not |
| Trusting a grep over the owning tool | A search of `jottabackup.log` showed no `ttdb` root while `jotta-cli status` listed it as up to date. Ask the CLI, not the log |

## Accepted trade-offs

- **Red production deploy** — accepted with a structural safety argument until a real Python
  dependency need appears.
- **Two VS Code windows share one Cline store** — accepted cost of the plan/act workflow.
- **Wiki.js remains deployed although deprecated** — do not decommission yet.
- **Compact status files carry no in-file provenance** — one line, no history trail; diff
  history and `git log` are the record.
- **(carried forward)** Committed CCM headers are machinery, not authorship; never hand-edit.

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2025-08-29 | Root-level legacy scripts become thin wrappers | Backward compatibility after relocation into `scripts/system`, `scripts/windows`, `health/libre` |
| 2026-09-25 | Homarr retired | Container removed, vhost disabled, compose + env deleted; `wiki/runbook-homarr.md` keeps the revival path |
| 2026-09-26 | Homarr retirement recorded in network map and agent index | Keeps the "what is running" view honest |
| 2026-10-03 | Cline per-window isolation investigation closed | No supported per-window env surface on Linux; per-instance fallback adopted; snap patching rejected as unmaintainable |
| 2026-10-04 | Deploy workflow's `test` job removed (`40282aa`) | It did not touch the failing pip line |
| 2026-10-07 | Nginx site symlinks retargeted to `/srv/prd/tt` | Host nginx consumes the deployed tree; `nginx -t` gate + tarball backup |
| 2026-10-07 | Prod deploy failing step left red, by decision | rsync runs first, so code lands; Option B chosen for any future fix |
| 2026-10-10 | Phantom automation `automation.llm_hooktest_1` removed | Config-less registry orphan; the repo has no `automations.yaml` |
| 2026-10-17 | Project context written from verified reads only | Unresolved items marked unverified rather than guessed |
| 2026-10-18 | 1st-bath greeting keeps Alexa voice, wording only | `alexa_devices` exposes only `notify.speak`/`notify.announce`; hardware change out of scope |
| 2026-10-27 | Cline stages and commits; the user pushes | Push cannot succeed from this environment, and the user does not want the agent attempting it |
| 2026-10-28 | Backup key custody moved to per-tier DEKs + master-wrapped keyring | Per-tier blast radius; recipients public, private material never committed |
| 2026-10-28 | `memory-bank/` retired in favour of `wiki/` + `docs/status/` | One source of truth; the wiki is tracked, CCM-managed and published, the bank was none of those |
| 2026-10-28 | `%ccm_compact` added for volatile status files | One line instead of nine plus a 50-entry history trail, with no amend churn |
| 2026-10-30 | MkDocs secret exposure fixed by **staging**, not by relocating docs | `docs_dir` becomes a filtered copy of `*.md` + `stylesheets/*.css`; the 42 doc files outside `wiki/` stay where they are, `exclude_docs` becomes defence in depth, and the dev server is kept as-is. Implementation halted before deployment pending instruction |
| 2026-11-13 | Uptime Kuma upgraded 2.4.0 → 2.5.11 and pinned exactly | A floating `:2` let any restart run an unreviewed forward-only SQLite migration. Snapshot taken, integrity `ok`, rollback tag kept locally |
| 2026-11-13 | Database backups use user-level systemd timers, not root | Peer auth over the local socket as `mpegg-adm` needs no sudo, no service account and no pgpass. Accepted cost: that identity can also unlock the `general` DEK, so "the backup identity cannot decrypt what it protects" does not hold for these two jobs. The alternative was no backup at all |
| 2026-11-13 | Database backup lands **before** the monitoring archive | Adding a second schema to an unbacked database multiplies the unbacked surface. Backups are live; the `monitoring` schema is deliberately still absent |
| 2026-11-13 | Status documents rewritten from measured host state | Both files had drifted three weeks; several claims (ttmail undocumented, `stage-docs.sh` unrunable, dedup of `jottabackup.log`) were checkable and wrong. Host facts are now recorded with their evidence |
