<!-- %ccm_compact: path=docs/status/active-context.md branch=dev1 committed=2026-10-28T17:04:18-04:00 sha=474193c -->
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

Two threads are open:

1. **Backup key custody redesign** (`infra/backups/`). Single recipient was replaced by
   per-tier data encryption keys wrapped by a master keyring. Phases 1, 2, 3 and 5 are
   committed; see `wiki/system-patterns.md` §5 for the artefact layout.
2. **Project-context restructure** (uncommitted, this change). The old `memory-bank/`
   directory was retired: durable architecture moved to `wiki/system-patterns.md` and
   `wiki/tech-context.md`, volatile status lives here, and a `%ccm_compact` header mode was
   added so status files carry one line instead of nine plus a growing history trail.

## Repository state

A **snapshot**, not a live claim — it describes the working tree when this page was last
rewritten. Re-derive before relying on it:

```bash
git log --oneline -1 && git status --short
```

Modified: `.clinerules/00-cline-behavioral-rules.md`, `.clinerules/memory-bank.md`,
`git-automation/v2/ccm-apply.sh`, `git-automation/v2/README.md`, `hams/docs/*` (4 files),
`wiki/README.md`, `wiki/how-to-add-mcp-server.md`, `wiki/ports.md`, `wiki/agent-index.md`.

Untracked: `docs/`, `ttmail/`, `.roo/`, `.clinerules/workflows/`, `wiki/runbook-ha-mcp.md`,
`infra/docker/mediawiki-mirror-dev1.yml`, `infra/docker/mediawiki-mirror/`,
`util/cline-titles/`, `tests/git-automation/test_eol_and_markdown.sh`,
`tests/git-automation/test_compact_header.sh`.

Tracked deletions: `memory-bank/cline-per-window-isolation.md`,
`memory-bank/host-deploy-runbook.md` — their content already lives at
`docs/investigations/` and `docs/runbooks/`. **A fresh clone gets neither document until
the relocation is committed.**

## Live decisions

1. **Do not "fix" the TT production deploy.** The `Install production dependencies` step
   fails by design. `Synchronize approved revision` (rsync) is step 1, so code lands before
   the failing step runs. Watch step 1 for green; treat the job conclusion as expected-red.
   If a real dependency need appears, add **root** packaging metadata (Option B) — never
   repoint pip at a sub-project.
2. **The publishing filter stays restrictive.** `exclude_docs` publishes only `*.md` and
   `stylesheets/**`, because `wiki/` symlinks whole trees containing live secrets. Any
   relaxation is a security change.
3. **MkDocs is the live wiki; Wiki.js is deprecated but must not be decommissioned yet.**
4. **The 1st-bath morning greeting keeps the Echo Pop's Alexa voice — only its wording
   changes.** `alexa_devices` exposes only `notify.speak` / `notify.announce`; a different
   timbre needs new hardware, which is out of scope. The trigger was repointed from
   `binary_sensor.mwave_1stbath_presence` to the 45 s-debounced
   `binary_sensor.mwave_1stbath_presence_confirmed`, costing 45 s of greeting lag and any
   visit under 45 s. The "not Matt" identity gate was **deferred deliberately**.
5. **Cline stages and commits; the user pushes. Never run `git push`.** (2026-10-27, stated
   explicitly.) `git push origin dev1` fails here anyway: no credential helper, no
   `~/.git-credentials`, no `gh`, no `GITHUB_TOKEN`, and the only SSH key is not registered
   with GitHub. Working agreement: commit, verify it landed, hand back the exact `git push`
   command.
6. **Volatile project context lives in `docs/status/`, not a memory-bank directory.**
   Durable architecture belongs in `wiki/`, where it is trackable, publishable and
   reviewable. Status documents use the `%ccm_compact` header so they cost one line.
7. **Backup key custody is per-tier DEKs wrapped by a master keyring.** Tier and master
   *recipients* are public and committed; private material (`master.txt`,
   `master-identity*.txt`, `*.escrow.age`, `keyring.tar.age`) must never be.

## Open questions and unverified claims

- **Backup phase 4 has no commit.** Log shows 1 (`b154cfa`), 2 (`0e8a93b`), 3 (`142d3b3`),
  5 (`897329f`). Either folded elsewhere or outstanding.
- **The five-layer `tt-backup` constraint description predates the keyring redesign** and
  has not been re-verified against `install-tt-keys.sh` or the hardened unit.
- **`ttmail/` is undocumented.** It is untracked, appears to be a Python package, and its
  scope is unknown. Do not assume.
- **CI packaging contradiction is unresolved.** `ci.yml` runs `pip install -e ".[dev]"` from
  the repo root, where no packaging metadata exists.
- **Root `README.md` and `infra/README.md` are stale**, describing root `docker/`/`nginx/`
  compatibility symlinks that do not exist. Root `README.md` is a UTF-8/UTF-16 hybrid.
- **`deploy-prd.yml` uses `group: jah-prd-deploy`** — a copy-paste artefact. Cosmetic but
  misleading in logs.
- **JAH sudoers grant unverified.** `/etc/sudoers.d/jah-deploy` could not be diffed
  non-interactively; if it omits `--quiet`, `systemctl is-active --quiet` is uncovered.

## Next steps

1. Commit the `docs/` relocation, the `memory-bank/` retirement and the `%ccm_compact` mode
   together, so no clone ever sees the deletions without the replacements.
2. Determine what `ttmail/` is and decide whether to track it.
3. Resolve the CI packaging contradiction via Option B (fixes CI and the deploy step at once).
4. Refresh both stale READMEs; normalise root `README.md` encoding while there.
5. Fix `concurrency.group` in `deploy-prd.yml`.
6. Verify the JAH sudoers grant by hand.
7. Confirm whether backup phase 4 exists and close the gap.

## Learnings worth keeping

- **Hook guards that grep whole files are blunt instruments.** Existing bypass markers work
  by whole-file `grep`, which is why the hook READMEs themselves carry no CCM header. The
  `%ccm_compact` check is **first-line-only** on purpose, so documentation *about* the token
  is unaffected.
- **A hand-maintained "updated" line will drift.** The retired memory bank claimed
  `Updated: 2026-10-17` while containing 2026-10-27 content, and pinned a HEAD nine commits
  stale. Derive freshness from git instead of asserting it.
- **Verify before asserting emptiness.** An earlier note claimed batched reads returned empty
  for non-empty files; the real causes were encoding-related (`file` reporting UTF-16LE as
  text) and client behaviour. Confirm independently before concluding a file is missing.
