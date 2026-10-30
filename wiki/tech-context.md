# Tech Context

Technologies, toolchain, environment facts, and the constraints that actually bite. This
page records the things that fail silently or corrupt files if ignored — not a general
inventory.

## Languages and runtimes

| Layer | Technology | Where |
|---|---|---|
| Application code | Python (packaged projects) | `water-meter/`, `ttmail/` |
| Ops glue | Bash | `scripts/`, `util/`, `infra/*/scripts/` |
| Backup/infra Python | Python | `infra/backups/scripts/*.py` |
| Commit hooks | Bash | `git-automation/v2/` |
| CI/CD | GitHub Actions YAML | `.github/workflows/` |
| Docs | Markdown + MkDocs Material | `mkdocs.yml`, `wiki/` |
| Containers | Docker Compose | `infra/docker/*-dev1.yml` |
| Windows-only legacy | PowerShell / `.cmd` / `.bat` | `scripts/windows/`, `health/libre/*.ps1` |

Host production Python is `3.12.11` at `/usr/bin/python3`; CI pins `3.12`;
`water-meter` declares `requires-python = ">=3.10"`.

## There is no root-level packaging metadata

**No root `pyproject.toml`, `setup.py`, `setup.cfg`, or `requirements.txt` exists.** At the
time of writing the only packaging metadata in the tree is per-project
(`water-meter/pyproject.toml`).

This single fact explains two separate symptoms that look unrelated:

1. `deploy-prd.yml` step 3 (`pip install -e /srv/prd/tt`) fails — accepted, see
   `wiki/system-patterns.md` §7.
2. `ci.yml`'s `pip install -e ".[dev]"` cannot succeed as written.

If a root dependency need genuinely appears, the agreed fix is **Option B** — add root
`pyproject.toml` or root `requirements.txt`. Do **not** repoint pip at a sub-project: that
couples production to a package it may never run.

## Documentation toolchain

`mkdocs.yml` — Material theme, `docs_dir: wiki`, `site_url: https://docs.termitetowers.ca`,
served on host port **3210**. Plugins: `search`, `tags`. Markdown extensions include
`pymdownx.superfences` with a **mermaid** custom fence, `tabbed`, `admonition`, `toc`
(permalinks), `attr_list`, `md_in_html`.

Navigation is explicit. The `nav:` key lists pages in seven tabs (Infrastructure,
Services, Home Assistant, AI and Voice, Docker and Dev, Infra Source). A new `.md` file
still builds without a `nav:` entry, but it is unreachable from the site until it is
added, so add the file to `nav:` in the same commit that creates it.

`exclude_docs` publishes only `*.md`, `stylesheets/**` and the theme bundle under
`assets/**`. The `!assets/**` line is load-bearing: MkDocs adds the theme's files to the
same collection that `exclude_docs` filters, so a catch-all `*` without that negation
also excludes Material's own CSS and the site renders unstyled. See
`wiki/system-patterns.md` §3 before touching the block.

## CI/CD toolchain

`actions/checkout@v4`, `actions/setup-python@v5`. Quality gates: `ruff check .` and
`pytest -q`. Deploy transport: `rsync` over a self-hosted runner
(`actions-runner-linux-x64-2.337.0`) installed as a systemd service on `monolith`
(Ubuntu 24.04.5 LTS, kernel 7.0.0-34-generic).

## File-format and encoding constraints

These are not cosmetic; they break tools if ignored.

1. **Most tracked files are CRLF**, declared per-file as `ccm_file_eol: CRLF`. Hooks
   preserve the file's own EOL when injecting headers (`detect-eol.sh` is the single source
   of truth, shared by header injection and metadata capture).
2. **A CCM header block sits at the top of every tracked file**, in the language's comment
   syntax. Fields are hook-generated — **never hand-edit them**, and never hand-maintain a
   "last updated" date; the header (or `git log`) is the authority.
3. **Root `README.md` is a hybrid.** `file` reports `data`: a UTF-8 CCM comment block
   followed by a UTF-16LE body with BOM. `iconv -f UTF-16` mangles the first half; `utf-8`
   with `errors='replace'` mangles the second. Read the prefix and the body separately.
   The hook skips files containing NUL bytes for exactly this reason — a charset test alone
   let byte-oriented rewriting corrupt that file once already.
4. **The hook log path is load-bearing.** Logs go to `$HOME/log/<repo>-enhanced-hooks.log`,
   and `infra/logrotate/logrotate.d/git-hooks.conf` rotates on `*-enhanced-hooks.log`.
   Renaming the log requires updating the logrotate pattern in the same change.
5. **Whole-file marker text excludes a file from hook processing.** A plain `grep` over
   content means any file *mentioning* a bypass marker (`tt-hooks.skip-post-commit`,
   `tt-secrets.skip`, `tt-ggshield.skip`) — including the hook READMEs that document them —
   receives no CCM header. Intentional, documented, not a bug. By contrast, `%ccm_compact`
   is checked on **line 1 only**, precisely so that documents describing it are unaffected.

## Development environment

- Working tree `/home/mpegg-adm/source/TermiteTowers`, branch `dev1`.
- `.venv/` at the repo root (gitignored). `site/` holds built MkDocs output.
- Present: `.vscode/`, `.trunk/`, `.pytest_cache/`, `.yamllint.yml`, `.editorconfig`,
  `.gitattributes`, `.gitguardian.yml`, `.roo/`, `.clinerules/`.
- Tests: `tests/git-automation/` — shell tests for header insertion, JSON headers,
  language-mode detection, EOL handling, and `%ccm_compact` mode.

## Runtime facts that shape development

- **Water meter:** FastAPI + single-file SPA at `src/water_meter/webapp/static/index.html`,
  `./run.sh [port] [host]`, default `localhost:3414`. Batch entry point:
  `python -m water_meter.core.pipeline`.
- External state is environment-driven, not repo-stored: `WATER_METER_DB_DSN` (default
  `postgresql:///ttdb_dev1`), `WATER_METER_ROOT` (default `~/pictures/water_meter/`).
- **HAL MCP endpoint** is planned at host port 3340 → container 8086 (`wiki/ports.md`).
- **`ttmail/`** exists at HEAD but is untracked and undocumented here; treat its scope as
  unknown rather than assuming.

## Tooling discipline for agents

- **Never edit CCM header blocks by hand**; the hooks own them.
- **Never loosen `mkdocs.yml`'s `exclude_docs`.**
- **Query live state** (`hal-mcp__*`, `pg-query-ttdb__*`, `pg-query-ttphoto__*`) instead of
  trusting doc snapshots.
- **Verify emptiness before asserting it.** Earlier notes recorded that batched/parallel
  reads "returned empty for non-empty files"; that was a tooling artefact of one client, not
  a property of the files. Parallel reads work. If output looks unexpectedly empty, confirm
  independently (`wc -l`, `git log`, `ls -ld`) before concluding a file is missing or blank.
