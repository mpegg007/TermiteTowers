<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/nginx/RELOCATION-PLAN.md:179 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 675709bd1b3e8e8b85f2cf5d5d05f73ca34b74f4 % -->
<!-- %ccm_git_commit_id: 5374d00e1d9cc50947a2b000c73308e0263dce3c % -->
<!-- %ccm_git_commit_count: 179 % -->
<!-- %ccm_git_commit_date: 2026-10-08 20:03:29 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: impl www from prd branch % -->
<!-- %ccm_git_modify_date: 2026-10-08 20:03:29 % -->
<!-- %ccm_git_file_last_modified: 2026-10-08 19:46:35 % -->
<!-- %ccm_git_file_name: RELOCATION-PLAN.md % -->
<!-- %ccm_git_path: infra/nginx/RELOCATION-PLAN.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 9009 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-10-07 mpegg  migration scripts  --> 
# Nginx Site Config Relocation — `/etc/nginx` → `/srv/prd/tt`

**Status:** ✅ APPLIED & VERIFIED (2026-10-07 21:13). `sites-available` symlinks
now target `/srv/prd/tt`; `sites-enabled` is uniformly 2-hop. See run record below.
**Scope:** retarget the host's Nginx site symlinks only. No conf content, no
web roots, no physical move of config files.

## Run record (2026-10-07 21:13)

`sudo bash scripts/nginx-relocate-symlinks.sh` was executed and post-verified:

- `sites-available`: **39/39** symlinks → `/srv/prd/tt/infra/nginx/sites-available/<name>.conf`;
  real file `default` untouched.
- `sites-enabled`: **37/37** symlinks → `/etc/nginx/sites-available/<name>`.
  The legacy 1-hop `dns` (`→ …/TermiteTowers/…/dns.conf`) and the relative
  `dba`/`hal` (`../sites-available/*`) were normalized; **3 repoints** total.
- **0** broken symlinks; **0** symlinks still reference `/home/mpegg-adm`.
- `nginx -t` passed (apply-mode auto-rollback did not trigger); `nginx` reloaded.
- Backup: `/var/backups/nginx-symlinks-20261007-211336.tgz`
  (+ `.manifest` of the pre-change `link -> target` layout).
- `/srv/prd/tt/infra/nginx/sites-available` holds all **42** `.conf` (matches authoring repo).

---

## Run record - web roots `/var/www/*` -> mirror symlinks

**Status:** SCRIPT READY, APPLY PENDING. `scripts/www-relocate-to-srv.sh` is
authored, dry-run-validated, and self-escalates **once** via sudo. The swap has
**not** been applied yet - the mirror must first carry the published page (the
ordering guard below blocks an early link).

- **Goal:** end perms/ownership drift between hand-copied `/var/www/chat` and the
  CI tree by making the docroot a symlink into the mirror:
  `/var/www/chat` -> `/srv/prd/tt/infra/nginx/www/chat`.
- **No conf change:** `chat.conf` keeps `root /var/www/chat`; nginx resolves the
  path *through* the symlink. `media.conf` and `immich.conf`'s
  `alias /var/www/tag-viewer/` are untouched (`tag-viewer` is owned by its own
  service and is refused by the script).
- **Ordering guard (default on):** the script `diff -rq`'s the mirror against the
  repo source `infra/nginx/www/<name>` and **aborts** when they differ, so an
  un-published page can never be linked live early. Bypass: `--no-sync-check`.
- **Publish path shifts:** after the swap, live content updates only via
  `dev1 -> prd` merge -> push -> `deploy-prd.yml` rsync (no longer the dev1
  working tree).
- **`scripts/deploy-www.sh` is now fail-closed:** it refuses to run when a
  destination is a symlink (it would otherwise `cp -a`/`chown -R` through the link
  into the mirror, desyncing it from git until the next `rsync --delete`).
- **Run (exactly one sudo password prompt):**
  ```bash
  bash scripts/www-relocate-to-srv.sh --dry-run          # preview, no sudo
  bash scripts/www-relocate-to-srv.sh                    # apply chat
  bash scripts/www-relocate-to-srv.sh --include-media    # apply chat + media
  ```
- **Rollback:** `sudo tar -xzf /var/backups/www-relocate-<ts>.tgz -C /var/www &&
  sudo systemctl reload nginx`.

---

## Objective

Make the deployed production tree **`/srv/prd/tt`** the source of truth that
Nginx reads, instead of the developer checkout under
`/home/mpegg-adm/source/TermiteTowers`. Also collapse the one irregular
sites-enabled symlink so **every** enabled site resolves through
`sites-available` (2 hops), and retire the stale chat-page tile.

Authoring does **not** move: the repo (branch `dev1`) remains where configs are
written, CI deploys the `prd` branch into `/srv/prd/tt`, and `/etc/nginx`
symlinks are repointed at that mirror.

## Verified current state

| Location | Contents |
|---|---|
| repo `infra/nginx/sites-available/` | **42** `.conf` files (authoring source) |
| `/etc/nginx/sites-available/` | **39** symlinks → repo `.conf` + **1** real file `default` (disabled, not enabled) |
| `/etc/nginx/sites-enabled/` | **37** symlinks; 36 go through `sites-available`, **`dns` is a 1-hop** straight to the repo |
| `/srv/prd/tt` | CI `--delete` mirror of the `prd` branch (owned by `tt-deploy`) |

- **Repo-only** confs (not symlinked anywhere): `calendars`, `kea-health-endpoint`, `water-meter`.
- **Available-but-not-enabled**: `home`, `vault`.
- **Zero** `include`/config-dir references inside any conf; **zero** confs
  reference the repo path or `/srv/prd/tt` — every `root`/`alias` points at
  `/var/www/*`, so retargeting symlinks changes nothing inside the confs.

## Target state (Option A)

| Where | Before | After |
|---|---|---|
| `sites-available/*` (39 symlinks) | → home repo `.conf` | → **`/srv/prd/tt/infra/nginx/sites-available/*.conf`** |
| `sites-enabled/*` (37 symlinks) | 36× → sites-available; `dns` → repo | **all 37 → `/etc/nginx/sites-available/<name>`** |
| `sites-available/default` | real file, disabled | **untouched** |
| conf content | — | **unchanged** |
| repo `infra/nginx/sites-available` | authoring source | **still authoring source** |

### Invariants (deliberately NOT changed)

- `justanotherhuman.conf` bare `listen 3259` (no TLS) — intended.
- `kea-health-endpoint.conf` loopback bind — intended.
- `sites-available/default` — left in place, disabled.
- `tag-viewer` / `justanotherhuman` web content — owned by their own
  service/python deploy, **not** nginx (`deploy-www.sh` only ships
  `chat`→`/var/www/chat` and `media`→`/var/www/media`).

---

## Execution

All privileged work is in **one** script (a single `sudo` approval, not 37
individual `sudo ln`):

```bash
# 1. Preview (no root needed) — prints every intended change
bash scripts/nginx-relocate-symlinks.sh --dry-run

# 2. Apply (one sudo approval)
sudo bash scripts/nginx-relocate-symlinks.sh
```

The script, in order:

1. **Backup** — `tar` of the current `sites-available` + `sites-enabled` into
   `/var/backups/nginx-symlinks-<ts>.tgz`, plus a `…manifest` of every
   `link -> target` for diffing.
2. **sites-available** → repoint each symlink to
   `/srv/prd/tt/infra/nginx/sites-available/<name>.conf` (real files skipped).
3. **sites-enabled** → repoint each symlink to
   `/etc/nginx/sites-available/<name>` (fixes the `dns` 1-hop).
4. **Verify** every symlink resolves, run `nginx -t`, `systemctl reload`;
   on a failed `nginx -t` it **auto-restores the backup and exits non-zero**.

Flags: `--dry-run`, `--no-reload`, `--no-backup`, `--root <path>`.

### Rollback (if ever needed)

```bash
sudo tar -xzf /var/backups/nginx-symlinks-<ts>.tgz -C /etc/nginx
sudo systemctl reload nginx
```

## Follow-ups (repo work, no privileges)

1. **Chat landing page** — keep the classic tiled page reachable via a click,
   and add a new "wow" page:
   - new page becomes `www/chat/index.html`; classic moves to
     `www/chat/classic.html` (served by `chat.conf`, `root /var/www/chat`).
   - remove the dead **`calendars`** tile (conf exists but is not enabled).
   - publish via a `dev1 -> prd` merge (CI rsync), then
     `bash scripts/www-relocate-to-srv.sh` to (re)point `/var/www/chat` at the
     mirror. `scripts/deploy-www.sh` is retired to a fail-closed guard.
2. **CI auto-enable** — consider having `deploy-prd.yml` re-assert the
   `sites-enabled` links after the rsync so a fresh `/srv/prd/tt` can never
   leave a site unlinked.

### Chat tile audit (22 tiles)

- **Live:** 21 (lobe, webai, mealie, news, search, pihole, hal, wiki, docs,
  nextcloud, kuma, dozzle, netalertx, watchyourlan, dns, asset, dba,
  prometheus, tensorflow, comfyui, esphome).
- **Dead:** `calendars` — remove.
- **Enabled sites with no tile (16):** chat (the page itself), immich,
  justanotherhuman, library, lidarr, llmapi, media, music, ollama, packages,
  prowlarr, pypi, qbit, radarr, readarr, sonarr — candidates for the wow page.

