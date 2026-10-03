<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: memory-bank/cline-per-window-isolation.md:167 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: e5c1144d9108eb200234ffa464cf753feb653940 % -->
<!-- %ccm_git_commit_id: af3b4e614eaf7f1e2342aedb19c1c31089a044fd % -->
<!-- %ccm_git_commit_count: 167 % -->
<!-- %ccm_git_commit_date: 2026-10-03 17:41:25 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: backup scripts % -->
<!-- %ccm_git_modify_date: 2026-10-03 17:41:26 % -->
<!-- %ccm_git_file_last_modified: 2026-10-03 16:02:47 % -->
<!-- %ccm_git_file_name: cline-per-window-isolation.md % -->
<!-- %ccm_git_path: memory-bank/cline-per-window-isolation.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 11099 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Cline per-window isolation on VS Code (snap, Linux) — investigation record

> Why two VS Code windows **cannot** be given separate Cline data directories on
> this machine, what was tried, what the binaries actually do, and the supported
> fallback. Read this before re-opening the question.

_Investigation closed 2026-10-03. All binary evidence below was re-extracted from
the installed snap during this session._

## Question

Cline's data store lives in `~/.cline/data`. On a machine with a plan/act
two-window workflow, both windows share that one store. Can each VS Code window
be pointed at its own Cline store (ideally via a per-window `CLINE_DATA_DIR`)?

**Answer: no — not with any supported per-window surface.** VS Code has real
per-window environment plumbing internally, but no external switch to set it
per window. The only supported isolation is **per instance**, via
`--user-data-dir` plus a `CLINE_DATA_DIR` environment variable set before launch.

## Environment (verified this session)

| Fact                          | Value                                                              |
| ----------------------------- | ------------------------------------------------------------------ |
| Snap package                  | `code` rev **266**, tracking `latest/stable`, publisher `vscode**` |
| Snap version                  | `04c0d99f`                                                         |
| Confinement                   | `classic`                                                          |
| Base                          | `core20`                                                           |
| Launcher command              | `electron-launch $SNAP/usr/share/code/bin/code --no-sandbox`       |
| Launcher tail                 | `exec "$@" --ozone-platform=x11`                                   |
| CLI surfaces in `code --help` | `--user-data-dir <dir>`, `--profile <profileName>` (no `--env`)    |

`/snap/code/current/electron-launch` (the snap's entry wrapper) performs desktop
integration exports, then ends with `exec "$@" --ozone-platform=x11`. It does
**not** pin `--user-data-dir`, and it does **not** touch `CLINE_DATA_DIR`. The
snap passes the `code` command line straight through, so any CLI argument is
delivered intact to Electron — the wrapper is not a blocker, it is just
transparent.

### The shared Cline store

Both windows resolve to the same directory (verified by listing it):

```text
~/.cline/data/
├── db/sessions.db            (+ sessions.db-shm, sessions.db-wal)
├── globalState.json
├── secrets.json
├── sessions/
├── workspaces/
├── settings/
├── logs/
├── checkpoint-scratch/
└── remote-config-workspace/
```

Nothing in the environment exported a `CLINE_DATA_DIR` for the running
extension hosts, so the default `~/.cline/data` is in use for both windows.

## The three refuted leads

Three plausible "set env per window" leads were each traced to the byte and
refuted for Linux.

| #   | Lead                                                          | Evidence                                                                                                                                                                                                                                                                                                                   | Verdict                                                                                                                                                                                                               |
| --- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `cli.js` forwards `--env K=V` into the new window             | `cli.js` @ **248,504**: a loop over the env object pushes `"--env"` then a `key=value` string for each entry; the whole block sits inside `if (ye) { … }`, whose sibling call is `Rn("open", …)`. The `else` branch spawns directly: `l=Rn(process.execPath, c, a)`.                                                       | **macOS-only.** On Linux the `else` path runs and no `--env` is ever forwarded.                                                                                                                                       |
| 2   | `--force-user-env` is a CLI flag that hands the window an env | `main.js` @ **689,224 / 689,446**: the tokens are `--force-user-env` and `--force-disable-user-env`, and the surrounding traces are `resolveShellEnv(): skipped (Windows)`, `resolveShellEnv(): skipped (VSCODE_CLI is set)`, `resolveShellEnv(): running (--force-user-env)`, `resolveShellEnv(): running (macOS/Linux)`. | **Not a CLI flag.** An internal shell-environment _resolution_ switch (`main.js` only), never advertised by `--help`. It controls whether the login-shell env is harvested; it does not inject a caller-supplied env. |
| 3   | `main.js` @ **1,031,905** `env` is the extension-host env     | The node is `env:{type:"object",…}, cwd:{…}, url:{…}, headers:{…}` — that is an **MCP server** definition schema.                                                                                                                                                                                                          | **Unrelated.** MCP server config, not the ext-host/window env.                                                                                                                                                        |

## What the binaries actually do (`userEnv`)

The real per-window mechanism is an internal object called `userEnv` that travels
with a window's open-config over IPC. Anchors (byte offsets in the snap's `out/`
assets):

| Artifact  | Offset    | What it is                                                                                                                                                                                                                                             |
| --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `main.js` | 759,190   | Window-open options: `userEnv: n["preserve-env"] \|\| t===0 ? e : void 0` — value comes from the `--preserve-env` switch / first window, **not** from arbitrary caller env.                                                                            |
| `main.js` | 875,397   | Parent→child merge: `let o = xi(r) && !xi(e.userEnv), s = this.isExtensionDevelopmentHost; (o \|\| s) && (e.userEnv = {...r, ...e.userEnv})`. A new window **inherits/merges** the parent's env; it never accepts a fresh per-window set from outside. |
| `main.js` | 912,208   | Per-window payload: `userEnv:{...this.initialUserEnv, ...e.userEnv}`.                                                                                                                                                                                  |
| `main.js` | 1,111,402 | `CodeMain` constructor assigns `userEnv=t` (alongside `this.userDataProfilesMainService=g`).                                                                                                                                                           |
| `cli.js`  | 248,504   | The macOS-only `--env` forwarding loop (refuted lead #1).                                                                                                                                                                                              |

**Conclusion:** the plumbing exists (`userEnv` is genuinely per window), but every
path that populates it is internal — CLI inheritance, `--preserve-env`, or
first-window defaults. There is **no supported external surface** on Linux to set
an arbitrary environment variable (e.g. `CLINE_DATA_DIR`) for one window only.

### Caveat: offsets are revision-scoped

Those offsets are byte positions inside `out/main.js` (1,307,150 B) and
`out/cli.js` (273,424 B) **as shipped in snap revision 266 / version
`04c0d99f`**. A snap refresh changes them. Treat the offsets as evidence for
_this_ revision, not as stable addresses.

## Supported fallback — per _instance_, not per _window_

If genuine store separation is needed, isolate whole VS Code **instances**:

```bash
CLINE_DATA_DIR="$HOME/.cline-data-act" \
  code --user-data-dir "$HOME/.vscode-act" --profile act
```

- `--user-data-dir <dir>` is advertised in `code --help` and passes through the
  snap cleanly. It gives that instance its own window/session state.
- `CLINE_DATA_DIR` is read by the Cline extension, so a launch-time environment
  variable moves the store.
- **This is per instance, not per window.** A second bare `code` invocation hands
  off to the _already-running_ instance (`cli.js` non-macOS path spawns/forwards
  into the existing process rather than starting a second one), so you cannot get
  two _windows_ with different `CLINE_DATA_DIR` values from one running instance.
  You get two _instances_ with two stores — which is the honest limit.

## Rejected approach — byte-patching the snap

Patching `main.js`/`cli.js` inside the snap to inject a per-window
`CLINE_DATA_DIR` was considered and **rejected**: the snap refreshes replace the
whole revision directory, so any patch is destroyed on the next refresh (current
revision `04c0d99f`, rev 266 — already moved once during this line of
investigation). It is unmaintainable and would silently regress.

## Accepted cost of the current setup

With the two-window plan/act workflow sharing one `~/.cline/data`:

- Two extension hosts may write to one `db/sessions.db` concurrently
  (SQLite WAL is in use — `sessions.db-wal` and `-shm` are present), which can
  surface `SQLITE_BUSY`-class errors.
- Task history, workspace state, and `secrets.json` are a single shared pool
  across both windows.

This is a known, accepted trade-off of the current layout — not a bug.

## If this is ever revisited

1. Re-extract the offsets first (`dd if=… bs=1 skip=<off> count=<n>`) — they are
   revision-scoped; do not trust the numbers above on a newer snap.
2. Check whether a newer VS Code adds a supported per-window env flag
   (`code --help`; look specifically for anything `--env`-shaped and whether it
   is gated to macOS).
3. If per-window is still impossible, prefer the per-instance
   `CLINE_DATA_DIR` + `--user-data-dir` fallback over any patching.
