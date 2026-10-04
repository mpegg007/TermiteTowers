# git-automation

Commit hooks that maintain the CCM (Continuous Code Management) header on every
tracked file, plus secret scanning that runs before a commit lands.

## Which version is active

**v2 (`git-automation/v2/`) is the active implementation.**
**v1 (`git-automation/enhanced-*.sh`) is kept only as a rollback path.**

|  | v1 (rollback only) | v2 (active) |
|---|---|---|
| Entry point | `enhanced-pre-commit.sh`<br>`enhanced-post-commit.sh` | `v2/pre-commit.sh`<br>`v2/post-commit.sh` |
| Layout | one ~500-line script with an inline 220-line `insert_ccm_header` | thin wrappers over `ccm-lib.sh` + `ccm-apply.sh` |
| Templates | `CCM_HEADER_TEMPLATE.txt` | `v2/CCM_*_TEMPLATE.txt` |
| Secret patterns | inline bash array | `v2/secrets-patterns.conf` (data file) |
| Docs | `HOOK-SAFETY-GUIDE.md`<br>`SECRET-SCANNING-README.md` | `v2/README.md` |

Only one is wired into `.git/hooks` at a time — whichever the stubs point at.
Run `./install-hooks.sh --verify` to see which that is.

## Install / repair / roll back

```bash
./git-automation/install-hooks.sh            # install or repair v2
./git-automation/install-hooks.sh --verify   # check only; non-zero exit if broken
./git-automation/install-hooks.sh --v1       # switch back to v1
```

`.git/hooks` is never version-controlled, so hooks must be reinstalled after a
fresh clone. Run the installer once and you are done.

## Why stubs and not symlinks

The installer writes small exec-stubs rather than symlinking the v2 scripts, and
this is not cosmetic:

1. **Git silently ignores non-executable hooks.** No warning, no error — the
   hook simply never runs. A `-rw-rw-r--` entry point looks installed and is
   inert.
2. **A symlinked hook breaks dependency lookup.** bash sets `BASH_SOURCE[0]` to
   the path it was invoked with, so for a symlink that is the *symlink*. The v2
   scripts derive `SCRIPT_DIR` from `BASH_SOURCE[0]`, so it resolves to
   `.git/hooks` — where `ccm-apply.sh`, `ccm-lib.sh` and `secret-scanner.sh` do
   not exist. The header never applies and `post-commit.sh` dies at its `source`
   line.

Both failures are silent. `--verify` exists so they stop being silent: the
final `runtime evidence` line reports whether the hook has actually executed.

## What the hooks do

`pre-commit` — for each staged file: apply the CCM header (`ccm-apply.sh`, via
`detect-language.sh` for comment syntax), scan for secrets (`secret-scanner.sh`
custom patterns + a batched `ggshield` run), then re-stage the file.

`post-commit` — fill the commit-bound header fields (`commit_id`,
`commit_count`, `commit_message`, author/email/date, `object_id`) and amend the
commit. A lock file prevents recursion during the amend, and the amend is
skipped if the branch is behind upstream.

Bypass markers, if you need them:

- `tt-secrets.skip` — skip the custom pattern scan for that file
- `tt-ggshield.skip` — skip GitGuardian for that file
- `tt-hooks.skip-post-commit` — skip all hook processing for that file

## Things that bite

- **A file that documents the bypass markers is itself skipped.** The marker check is a
  plain `grep` over file content, so this README and `v2/README.md` are excluded from
  header processing and secret scanning - they contain the marker strings. That is why
  neither carries a CCM header. It is not an oversight.

- **Never let a header be inserted into a file under `git-automation/`.** The
  templates are header *sources*; a header inside one would be emitted into every
  header generated afterwards. The hook excludes `git-automation/*.sh` and
  `git-automation/CCM_*_TEMPLATE.txt` (plus nested `git-automation/*/CCM_*_TEMPLATE.txt`).
- **Logs** live at `$HOME/log/<repo>-enhanced-hooks.log`. The basename matters:
  `infra/logrotate/logrotate.d/git-hooks.conf` rotates on the
  `*-enhanced-hooks.log` glob, so renaming the log requires updating that
  pattern in the same change.
- **`remove_ccm_header` refuses to strip more than 30 lines.** Generated headers
  are 24 (default), 26 (markdown) and 27 (JSON) lines, so headroom is thin. If
  the templates grow by ~7 lines, stripping starts failing and — because
  `ccm-apply.sh` calls it with `|| true` — a second header is silently appended.

## See also

- `v2/README.md` — v2 architecture, tag list, template directives, manual tests
- `HOOK-SAFETY-GUIDE.md`, `SECRET-SCANNING-README.md` — v1-era documentation
- `../infra/logrotate/README.md` — log rotation for hook logs
