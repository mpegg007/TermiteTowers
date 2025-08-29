# TermiteTowers util

Reusable shell customizations for Ubuntu login shells:
- Dynamic prompt: `mm.dd HH:MM:SS user:path [regionID]`
- Region detection based on `/srv/<regionID>/...` (defaults to `dev1` when outside /srv)
- Project helper functions and aliases (e.g., `golobe`) that source app env scripts under `/srv/<region>/APP/scripts/`
- Simple installer to wire this into `~/.bashrc`

## Install
Run the installer once to add a sourcing line to your `~/.bashrc`.

1) Review the scripts
- `init.sh` – one-line entry point sourced by your shell
- `prompt.sh` – prompt + region detection
- `aliases.sh` – helper functions and aliases
- `install.sh` – idempotently updates `~/.bashrc`

2) Install (idempotent)
- Execute `./util/install.sh`

3) Start a new shell or source your bashrc
- `source ~/.bashrc`

## Usage
- Prompt shows: `08.25 14:33:12 mpegg:/path [dev1]` (date/time updates every prompt)
- Region logic:
  - If `$PWD` starts with `/srv/<region>/...`, that `<region>` is used
  - Otherwise the fallback is `$TT_DEFAULT_REGION` (defaults to `dev1`)
  - Change fallback (current shell): `setregion dev1`
  - Temporarily pin region for this shell: `pinregion dev1` (clear with `unpinregion`)
  - Persist a default globally by adding `export TT_DEFAULT_REGION=dev1` to your own dotfiles

- LobeChat helpers (adjusts to region automatically):
  - `golobe` – sources `/srv/<region>/lobechat/scripts/appEnv.sh`
  - `cdlobe` – `cd` to `/srv/<region>/lobechat`

- Generic app helpers:
  - `goapp <app>` – source `/srv/<region>/<app>/scripts/appEnv.sh` if present, else just `cd`
  - `cdapp <app>` – `cd` to `/srv/<region>/<app>`

Errors are informative if a directory/script isn’t found.

## Template
See `templates/appEnv.sh.example` for a starter env script to place under `/srv/<region>/<app>/scripts/appEnv.sh`.

## Uninstall
Remove the block between the BEGIN/END markers from `~/.bashrc`.
