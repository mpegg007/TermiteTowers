<!-- %ccm_compact: path=docs/status/progress.md branch=dev1 committed=2026-10-28T17:04:18-04:00 sha=474193c -->
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
| MkDocs documentation site | Working | `mkdocs.yml` complete; `docs_dir: wiki`, port 3210 |
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
| Backup encryption | Redesigned | per-tier age recipients + master-wrapped keyring, phases 1/2/3/5 |
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
