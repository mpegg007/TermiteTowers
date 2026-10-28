<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/system-patterns.md % -->
<!-- %ccm_git_object_id: wiki/system-patterns.md@190 % -->
<!-- %ccm_git_commit_date: 2026-10-28 16:35:23 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: refactor(context): retire memory-bank and add %%ccm_compact status headers % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# System Patterns

Cross-cutting invariants that hold across the estate. This page exists to state the
*shape* of the system and point at the specialist page for detail — it deliberately does
not restate per-service facts, because duplicated detail goes stale and the copy is what
people read.

When this page and an artefact disagree, the artefact wins (see "Where the canonical
answers live").

## 1. Region-based host layout

Three named regions, each with a different trust level:

```
/srv/dev1/<service>/        # development, driven by this repo
/srv/prd/<svc>/             # production, host "monolith", driven by CI
ttdb-dev1 → ttdb-prd1 → ttdb-arc1   # database promotion path
```

The login shell mirrors this: the prompt derives a region ID from `$PWD` matching
`/srv/<regionID>/...`, falling back to `$TT_DEFAULT_REGION` (default `dev1`), with
`setregion`, `pinregion`, `unpinregion` helpers (`util/README.md`).

## 2. Repo → host binding by symlink, not copy

Dev compose files are authored here and consumed in place, so editing the repo file
changes what the host runs. There is no sync step to forget — and no staging buffer to
protect you either. Detail: `wiki/paths-and-symlinks.md`.

**Known documentation defect:** several pages still write the source path as
`TermiteTowers/docker/<name>-dev1.yml`. `docker/` does not exist at the repo root; compose
files live in `infra/docker/`. Root `README.md` and `infra/README.md` both describe
compatibility symlinks that were never created.

## 3. Documentation is a symlinked tree behind a publishing filter

MkDocs uses `docs_dir: wiki`, with sibling trees grafted in as symlinks:

```
wiki/hams           -> ../hams
wiki/infra          -> ../infra
wiki/git-automation -> ../git-automation
```

That is the central design tension of this repo: docs live beside the code they describe,
so the docs tree also contains env files, `secrets.yaml`, and MCP `config.json` tokens.

The guard is the publishing filter in `mkdocs.yml`:

```yaml
exclude_docs: |
  *
  !*.md
  !**/*.md
  !stylesheets/**
```

Only `*.md` and stylesheets are published. **Any relaxation of that filter is a security
change, not a documentation change.** Consequence to remember: anything placed under
`wiki/` as `.md` **is** published. Material that must stay tracked but unpublished belongs
under `docs/` (outside `docs_dir`), not `wiki/`.

## 4. Specialist pages own their detail

| Concern | Page |
|---|---|
| Compose conventions (identity, logging, restart, networks) | `wiki/compose-conventions.md` |
| Host port bands 3000–3999 | `wiki/ports.md` |
| One Postgres cluster, schema per service, promotion | `wiki/databases.md` |
| Storage ownership, setgid dirs, ACLs | `wiki/paths-and-symlinks.md` |
| Docker network CIDR map | `wiki/docker-networks.md` |

## 5. Backup and key-custody model

Two unrelated strategies share the word "backup" — do not conflate them:

- **`wiki/backup-strategy.md`** — external USB disk rotation for NVMe pools. Physical media
  and offsite scheduling. Nothing to do with application dumps.
- **`infra/backups/`** — per-app backup scripts, age encryption, Jotta replication.

The `infra/backups/` model, as of `897329f`:

- Each app has a script in `infra/backups/scripts/` (stop container → dump DB → archive).
- Dumps land in `/mnt/ai_storage/backups/<app>/`, replicated by `jotta-cli`.
- Scheduled by systemd `.service` + `.timer` pairs linked from `/srv/dev1/systemd/`.
- **Encryption happens before data leaves the host.** `age` is used, and the private
  identity never lives on the backup host or next to the backups it protects.

Key custody was redesigned from a single recipient to **per-tier data encryption keys
wrapped by a master keyring**:

| Artefact | Role |
|---|---|
| `infra/backups/age/general.recipient`, `health.recipient`, `mail.recipient` | public recipients, one per tier — safe to commit |
| `infra/backups/age/master-recipient.txt` | public master recipient — safe to commit |
| `infra/backups/age/registry.json` | tier/key registry |
| `keyring.tar.age` | the wrapped tier keys — **never committed** |
| `master.txt`, `master-identity*.txt`, `*.escrow.age` | master identity and escrow — **never committed**, blocked by `.gitignore` |

Tooling: `scripts/tt-keys.sh` (deploy, audit, verify, rotate, rewrap, prune),
`install-tt-keys.sh`, shared `lib/tt-age.sh`, and `restore-tthealth.sh`.

Landed phases, from the commit log: 1 (per-tier DEKs + master-wrapped keyring),
2 (keyring deploy/audit installer, harden `tt-backup` unit), 3 (encrypt to per-tier keys),
5 (rotate, rewrap, audit, prune, restore wrapper).

**Unverified — do not assert these as current:**

- **Phase 4 has no commit** in the log (`b154cfa` = 1, `0e8a93b` = 2, `142d3b3` = 3,
  `897329f` = 5). Either folded into another commit or still pending; the source of truth
  is the commit log and `infra/backups/README.md`, not this table.
- The earlier documented description of the `tt-backup` account as constrained in **five
  independent layers** (`nologin`, no privileged groups, own 0600 pgpass, read-only DB role,
  recipient-only age, no Jotta credentials) predates the keyring redesign. Re-verify against
  `install-tt-keys.sh` and the unit file before relying on it.

## 6. CCM headers are a maintained invariant

Every tracked text file carries a `TermiteTowers Continuous Code Management Header`,
maintained by the hooks. It is machinery, not authorship. Detail:
`git-automation/v2/README.md`.

- **v2 is active** (`git-automation/v2/`); v1 (`enhanced-*.sh`) is a rollback path only.
- `pre-commit.sh`: apply header (`ccm-apply.sh` via `detect-language.sh`) → secret scan
  (`secret-scanner.sh` patterns + batched `ggshield`) → re-stage.
- `post-commit.sh`: fill commit-bound fields and `git commit --amend`, with a lock file
  preventing recursion and an amend skip when the branch is behind upstream.
- Installer writes **exec stubs, never symlinks** — a symlinked hook resolves
  `BASH_SOURCE[0]` to `.git/hooks`, where the libraries do not exist, and a non-executable
  hook is silently ignored by git. `--verify` exists because both failures are silent.
- Header sources are exempt: `git-automation/*.sh` and `git-automation/**/CCM_*_TEMPLATE.txt`.
- Markdown uses a **9-line** template (`CCM_MARKDOWN_HEADER_TEMPLATE.txt`, introduced in
  `ba072db`). Older pages still carry 24-line legacy headers until they are next staged.
- **Compact mode:** a file whose *first line* carries `%ccm_compact:` is left completely
  untouched — one line, no history trail, no amend. Opt-in and self-declared, for volatile
  status documents. Detection is first-line-only on purpose, so documents that merely
  describe the token are unaffected.

## 7. CI and production deployment

Two workflows, each read from the pushed ref — so the workflow file must be committed on
the branch it triggers from.

**`ci.yml`** — `push` to `dev1`, PRs into `dev1`/`prd`. Python 3.12 →
`pip install -e ".[dev]"` → `ruff check .` → `pytest -q`.

**`deploy-prd.yml`** — `push` to `prd`, self-hosted runner `[self-hosted, linux, tt-prd]`:

1. `actions/checkout@v4`
2. `Synchronize approved revision`: `rsync -a --delete --exclude=.env --exclude=.venv
   --exclude=.git "$GITHUB_WORKSPACE/" /srv/prd/tt/`
3. `Install production dependencies`: `pip install -e /srv/prd/tt`

**Step order is the safety property.** Because rsync is step 1, a red job still means the
code landed. `.env` and `.venv` are excluded so production secrets and the hand-built
virtualenv survive every deploy.

Step 3 fails because there is no root packaging metadata — a known, accepted condition, not
an incident. Watch step 1 for green; treat the job conclusion as expected-red. Detail and
the host bootstrap: `docs/runbooks/host-deploy-runbook.md`.

## 8. Nginx is served from the deployed tree

`sites-available` on the host holds symlinks into `/srv/prd/tt/infra/nginx/sites-available/`
— the **deployed** tree, not the `dev1` working copy — and `sites-enabled` points at
`sites-available`, making every enabled site a uniform 2-hop link. Gates: `nginx -t` must
pass (auto-rollback) before reload, and a pre-change tarball plus manifest is written to
`/var/backups/`. Recorded as applied and verified in `infra/nginx/RELOCATION-PLAN.md`.

**Consequence:** editing `infra/nginx/sites-available/*.conf` on `dev1` does not affect
served sites until it reaches `/srv/prd/tt` via a `prd` deploy.

A second move — web roots `/var/www/*` becoming mirror symlinks into the deployed tree — is
**script ready, apply pending**, blocked by an ordering guard until the mirror carries the
published page.

## 9. Agent context hierarchy

Read in this order; do not start guessing:

1. `wiki/agent-index.md` — 60-second orientation.
2. `docs/status/active-context.md` — current focus, next steps, live decisions.
3. `hams/docs/hal-context.md` — HAL instance snapshot.
4. `hams/docs/SKILL.md` — HA development practice.

Data sources map to MCP namespaces (detail in `wiki/agent-index.md`): `hal-mcp__*` → Home
Assistant; `pg-query-ttdb__*` → `ttdb_dev1`; `pg-query-ttphoto__*` → photo library. HAL
joins to the database on **MAC / IP / hostname**.

**Always query live; never trust a cached state from a doc.**

## 10. Where the canonical answers live

When two documents disagree, prefer the artefact over the prose:

| Question | Check this, not that |
|---|---|
| Does the host path exist? | `ls -ld <path>` — not a paths doc |
| What does CI run? | `.github/workflows/*.yml` — not a runbook template |
| What is on a port? | `wiki/ports.md`, then live `ss -ltnp` on the host |
| Is the deploy green? | the runner's `_diag/Worker_*.log`, step by step |
| Is HAL in state X? | a live `hal-mcp__*` query — not `hal-context.md` |
| What is the project doing now? | `docs/status/active-context.md` and `git log` |
| How current is a status doc? | `git log -1 --format=%cI -- <path>` |
