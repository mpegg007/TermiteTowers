<!-- %ccm_compact: path=docs/status/active-context.md branch=dev1 committed=2026-11-13T12:45:45-05:00 sha=bffeccc -->
# Active Context

What the project is doing right now. Freshness is deliberately **not** hand-written —
it comes from git:

```bash
git log -1 --format=%cI -- docs/status/active-context.md
```

`docs/` is outside `docs_dir: wiki`, so this page is tracked and CCM-managed but never
published.

Line 1 is a **compact CCM header**: the hook maintains `committed=` and `sha=` from the
last commit that touched this file, so the file states its own provenance without the
9-line block and the 50-entry history trail the full header carries. Everything after
line 1 is content. Do not hand-edit the `committed=` or `sha=` values — the hook
overwrites them, and a hand-written date is how the retired memory bank came to claim a
date nine commits behind reality.

## Current work focus

Six threads, ordered by whether they are live risk:

1. **Database backups for `ttdb_dev1` and `ttphoto_dev1` — built, installed, scheduled and
   proven once.** Both databases had no backup at all until 2026-11-13. A user-level job
   (`infra/backups/scripts/backup-db-user.sh`) dumps over the local socket as `mpegg-adm`
   with peer auth, asserts the expected schemas are present in the dump's table of
   contents, encrypts with `age` under the `general` tier and prunes at 14 days. Four units
   in `infra/systemd/user/` are installed in `~/.config/systemd/user`, both timers are
   enabled, `Linger=yes`, and the next fires are **Sat 2026-11-14 03:54 and 04:10 EST**.
   First manual dumps verified and uploaded to Jotta. What is *not* done: no timer-triggered
   run has occurred yet, no restore has ever been tested, and `infra/backups/README.md` does
   not mention either job.
2. **Monitoring archive, Kuma → Postgres.** `infra/sql/monitoring/schema.sql` and
   `scripts/archive-monitor-metrics.sh` are written. Phase A — the Prometheus scrape job for
   Kuma's `/metrics` — does **not** exist, so the archiver currently has no data source.
   There is no systemd timer, no `tests/monitoring/`, no runbook, and the `monitoring`
   schema has not been applied to `ttdb_dev1` (verified: absent).
3. **Backup key custody redesign** (`infra/backups/`). Per-tier DEKs wrapped by a master
   keyring. Phases 1, 2, 3 and 5 are committed; see `wiki/system-patterns.md` §5. Phase 4
   still has no commit.
4. **Promotion manifest redesign** — parked 2026-11-09 mid-design, see
   [`promotion-manifest-handoff.md`](promotion-manifest-handoff.md). Cross-repo promotion and
   the promote repo as the approval boundary are settled and written into
   `docs/design/promotion-model.md` §4.5/§4.6; the manifest field list is open and nothing is
   implemented. The §4.5 ownership table is known-wrong: policy and manifests move to the
   promote repo.
5. **MkDocs live-reload defect** (`scripts/mkdocs/`). The staging fix is **designed and
   approved, partially written, and NOT deployed**. `stage-docs.sh` has since been repaired
   in the working tree (the writable-scratch guard has its `exit 1` and `fi` again, and
   `cleanup` is defined before the `trap`), so the earlier "not currently runnable" note is
   stale. Live state is unchanged: `mkdocs.yml` still declares `docs_dir: wiki`, the
   entrypoint is not overridden, the container runs `mkdocs serve` directly, and a reload
   build still aborts on `/docs/wiki/infra/docker/env/ha-mcp.env`. **Hold** until instructed.
6. **Project-context housekeeping.** `memory-bank/` is retired; volatile status lives here.
   This page and [`progress.md`](progress.md) had drifted three weeks behind reality and were
   rewritten on 2026-11-13 from measured host state rather than from the repo.

## Repository state

A **snapshot**, not a live claim — it describes the working tree when this page was last
rewritten. Re-derive before relying on it:

```bash
git log --oneline -1 && git status --short
```

At 2026-11-13 12:44 EST, `HEAD` is `33d69ac chore(uptime-kuma): pin 2.5.11 after upgrading
from 2.4.0`. The working tree carries roughly 30 modified tracked files, 8 tracked deletions
and 45 untracked paths. **None of the 2026-11-13 backup, Prometheus or monitoring work is
committed.**

Untracked and material:

- `infra/backups/scripts/backup-db-user.sh`, `install-tt-backup-db-user.sh`,
  `infra/backups/sql/tt-read-grant-mpegg.sql`
- `infra/systemd/user/tt-backup-db-{ttdb,ttphoto}.{service,timer}`
- `infra/sql/monitoring/schema.sql`, `scripts/archive-monitor-metrics.sh`
- `infra/docker/prometheus/`, `infra/systemd/tt-prometheus-{alerts,metrics}.*`,
  `tests/prometheus/`, `tests/tier-paths/`, `scripts/check-tier-paths.py`
- `ttmail/` (now documented at `ttmail/README.md`), `scripts/mkdocs/`, `.roo/`,
  `.clinerules/workflows/`, `util/cline-titles/`

Tracked deletions: `memory-bank/cline-per-window-isolation.md`,
`memory-bank/host-deploy-runbook.md`, `infra/docker/tensorflow-dev1.yml`,
`infra/nginx/sites-available/tensorflow.conf`, `scripts/deploy-prometheus-tensorflow.sh`,
`infra/docker/env/tensorflow.env.example`.

### Verified host state, 2026-11-13

The repo cannot tell you any of this; it was measured.

| Fact | Value |
|---|---|
| `mpegg-adm` role membership | `pg_read_all_data`, `tthealth_dev1_owner`, `ttphoto_dev1_owner`, `test_dev1_owner` |
| `ttdb_dev1` size | 1622 MB |
| `ttdb` dump | `ttdb_dev1_20261113_123001__general-2026Q4.dump.age`, 75 M, 818 objects; schemas verified `dhcp_history` 24, `kea` 525, `powerdns` 15, `snipeit` 1, `water_meter` 4, `watchyourlan` 11 |
| `ttphoto` dump | `ttphoto_dev1_20261113_120019__general-2026Q4.dump.age`, 53 M, 189 objects; `public` 47 and `v2` 73 TOC entries |
| Timer schedule | `ttdb` 03:50 + 10 m jitter, `ttphoto` 04:10; `Persistent=true`; last run `-` (never fired) |
| Jotta backup roots | `/gallery/immich/pics`, `backups/{mealie,thunderbird,tt-keys,ttdb,tthealth,ttphoto}` — all reported **Up to date**; `ttdb` 74.01 MiB, `ttphoto` 105.68 MiB |
| Kuma | pinned `louislam/uptime-kuma:2.5.11`, rollback tag `2.4.0-rollback`, snapshot `pre-2.4.0-20261113`; `/metrics` returns 401 without an API key |
| `monitoring` schema | **does not exist** in `ttdb_dev1` |

## Live decisions

1. **Database backups run as user-level systemd timers, not root.** Peer auth over
   `/var/run/postgresql` as `mpegg-adm`, `general` tier, no service account and no pgpass, so
   the whole job installs without sudo. The accepted cost is stated plainly: that identity
   can also unlock the `general` DEK, so "the backup identity cannot decrypt what it
   protects" does **not** hold for these two jobs. The alternative was a root-only install,
   and these databases had no backup at all for exactly that reason.
2. **The database backup gap closes before the monitoring archive lands.** Adding a second
   schema to a database with no backup multiplies an unbacked surface rather than shrinking
   it. That ordering is respected: backups are live, the `monitoring` schema is still absent.
3. **Do not "fix" the TT production deploy.** The `Install production dependencies` step
   fails by design. `Synchronize approved revision` (rsync) is step 1, so code lands before
   the failing step runs. Watch step 1 for green; treat the job conclusion as expected-red.
   If a real dependency need appears, add **root** packaging metadata (Option B).
4. **The publishing filter stays restrictive.** `exclude_docs` publishes only `*.md` and
   `stylesheets/**`, because `wiki/` symlinks whole trees containing live secrets. Any
   relaxation is a security change. The approved staging fix makes this filter defence in
   depth; it does not license relaxing it.
5. **The MkDocs fix is staging, not relocation** (2026-10-30). Only `*.md` plus
   `stylesheets/*.css` are staged into a separate `docs_dir`; no documentation file changes
   repository location.
6. **MkDocs is the live wiki; Wiki.js is deprecated but must not be decommissioned yet.**
7. **The 1st-bath morning greeting keeps the Echo Pop's Alexa voice — only its wording
   changes.** The trigger is the 45 s-debounced
   `binary_sensor.mwave_1stbath_presence_confirmed`; the "not Matt" identity gate was
   **deferred deliberately**.
8. **Cline stages and commits; the user pushes. Never run `git push`.**
9. **Volatile project context lives in `docs/status/`, not a memory-bank directory.**
10. **Backup key custody is per-tier DEKs wrapped by a master keyring.** Tier and master
    *recipients* are public and committed; private material (`master.txt`,
    `master-identity*.txt`, `*.escrow.age`, `keyring.tar.age`) must never be.
11. **Kuma is pinned, not floating.** A Kuma upgrade migrates `kuma.db` forward-only, so the
    tag is bumped deliberately after snapshotting the data directory.

## Open questions and unverified claims

- **Kuma metric names are unknown.** `/metrics` returns 401 without an API key, so the
  archiver's `monitor_status` / `monitor_response_time` defaults are unverified. They are
  environment-overridable for exactly this reason.
- **No timer-triggered backup run has happened.** Both 2026-11-13 dumps were manual; the
  first scheduled fire is 2026-11-14 03:54/04:10 EST.
- **No restore has been tested.** Only `restore-tthealth.sh` exists; there is no
  `restore-db-user.sh`, and the general-tier dumps need `tt-keys.sh unlock general:2026Q4`
  with the master. Until one restore runs, "backed up" means "a file exists offsite".
- **`infra/backups/README.md` does not document the two new jobs**, although their units
  name it as `Documentation=`.
- **A duplicate `ttphoto` dump exists** from the 12:00 retry. Harmless under 14-day
  retention; noted so it is not mistaken for a scheduling fault.
- **Jotta CLI is outdated**: 0.17.148769 installed, 0.17.176206 available.
- **Backup phase 4 has no commit.** Log shows 1 (`b154cfa`), 2 (`0e8a93b`), 3 (`142d3b3`),
  5 (`897329f`). Either folded elsewhere or outstanding.
- **The five-layer `tt-backup` constraint description predates the keyring redesign** and
  has not been re-verified against `install-tt-keys.sh` or the hardened unit.
- **The MkDocs staging fix is half-written and unverified.** Verified facts only: uid 2001
  can write `/mnt/ai_storage/mkdocs/` and **cannot** write the repo mount, so `docs_dir` must
  be an absolute path or a mount point (`/staging/docs` in the current draft). Unverified:
  whether `watchdog` is present in `squidfunk/mkdocs-material:latest`, whether debounced
  re-staging produces exactly one rebuild, and whether the tripwire's `find` expressions
  behave identically under the image's BusyBox.
- **The Kuma snapshot directory is not in the backup-metrics job list.** Adding
  `/mnt/ai_storage/uptime-kuma/backups/` to `emit-backup-metrics.sh` would make Kuma
  snapshots a `BackupStale` series like everything else. Cheap, not done.
- **CI packaging contradiction is unresolved.** `ci.yml` runs `pip install -e ".[dev]"` from
  the repo root, where no packaging metadata exists.
- **Root `README.md` and `infra/README.md` are stale**, describing root `docker/`/`nginx/`
  compatibility symlinks that do not exist. Root `README.md` is a UTF-8/UTF-16 hybrid.
- **`deploy-prd.yml` uses `group: jah-prd-deploy`** — a copy-paste artefact.
- **JAH sudoers grant unverified.** `/etc/sudoers.d/jah-deploy` could not be diffed
  non-interactively; if it omits `--quiet`, `systemctl is-active --quiet` is uncovered.
- **Web-root relocation is script-ready, apply-pending**, blocked by an ordering guard until
  the mirror carries the published page.
- **`uat1`/`prd1` secrets roots do not exist.** Per-tier separation is complete for `dev1`
  only.

## Next steps

1. Confirm the first scheduled backup runs — after 2026-11-14 04:15 EST,
   `systemctl --user list-timers 'tt-backup*'` must show a `LAST`, and
   `jotta-cli status` must still say **Up to date** for both roots.
2. Write `restore-db-user.sh` and test one restore of each database, documenting the DEK
   unlock step. A backup that has never been restored is unproven.
3. Document the two jobs in `infra/backups/README.md` — install path, schedule, tier,
   retention, and the decryption/restore route.
4. Commit the 2026-11-13 backup work; it is entirely uncommitted.
5. Add the `uptime-kuma` scrape job with an API token, read the real series names, then
   apply `infra/sql/monitoring/schema.sql`, install the archive timer, add `tests/monitoring/`
   and the runbook.
6. Housekeeping: refresh both stale READMEs, fix `concurrency.group`, verify the JAH sudoers
   grant, resolve the CI packaging contradiction, close the backup phase 4 question.
7. **Hold.** Do not resume the MkDocs staging work until instructed. When resumed: change
   `docs_dir`, then compose, then prove reload three times.

## Learnings worth keeping

- **"Backup done" needs four proofs**: job installed, dump produced, schema asserted,
  offsite copy confirmed. The 2026-11-13 failures show why all four matter — `pg_dump` exited
  5 before the grant, and `ttphoto` refused to publish a dump with no `public` schema.
- **Ask the tool that owns the state, not a grep.** A search of `jottabackup.log` found no
  `ttdb` entry while `jotta-cli status` listed the root as present and already up to date.
  The log records what the daemon did; the CLI records what the service holds.
- **A directory being scheduled for backup is not the same as its files being offsite.**
  `jotta-cli status` is the only authority for that, per root.
- **Hook guards that grep whole files are blunt instruments.** Existing bypass markers work
  by whole-file `grep`, which is why the hook READMEs themselves carry no CCM header. The
  `%ccm_compact` check is **first-line-only** on purpose.
- **A hand-maintained "updated" line will drift.** The retired memory bank claimed
  `Updated: 2026-10-17` while containing 2026-10-27 content, and pinned a HEAD nine commits
  stale. Derive freshness from git instead of asserting it.
- **Verify before asserting emptiness.** An earlier note claimed batched reads returned empty
  for non-empty files; the real causes were encoding-related and client behaviour. Confirm
  independently before concluding a file — or a backup root — is missing.
