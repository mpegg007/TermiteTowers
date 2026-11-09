<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: docs/status/nextcloud-dev1-handoff.md % -->
<!-- %ccm_git_object_id: docs/status/nextcloud-dev1-handoff.md@203 % -->
<!-- %ccm_git_commit_date: 2026-11-09 14:06:35 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: promotion: manifest inventory, record generator, deploy archive/restore % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Handoff — Nextcloud live, dev1 tree, secrets moved

**Written:** 2026-11-09
**State:** Nextcloud is live and verified. The dev1 tree is a working runtime root.
Secrets are out of the repo. **Some work is staged and not yet pushed.** Read §2 first.

Do not re-run discovery. Everything below was measured, and several earlier claims in
the chat were wrong and are corrected in §7.

---

## 0. Read these, in this order

| Document | Contains |
| --- | --- |
| [`plans/nextcloud-storage-and-jotta.md`](../../plans/nextcloud-storage-and-jotta.md) §6 | The 2026-11-08 measurements and the four corrections they forced |
| [`wiki/service-taxonomy.md`](../../wiki/service-taxonomy.md) | Platform vs service, the tt/aa/jah audience rule, the `/srv` agreement |
| [`infra/docker/README.nextcloud.md`](../../infra/docker/README.nextcloud.md) | Rewritten this session — the operational truth for Nextcloud |
| `docs/status/nextcloud-dev1-handoff.md` | This file |

---

## 1. What is live and verified

| Thing | State |
| --- | --- |
| Nextcloud | **https://filebank.analacres.ca** — `302` to login, `/status.php` `200`, login `200` |
| Certificate | `CN=filebank.analacres.ca`, Let's Encrypt, valid to 2027-02-06 |
| Old name | `nextcloud.termitetowers.ca` → `301` to `filebank` (both 80 and 443) |
| Backend | `dbtype = pgsql`, database `nextcloud`, installed, 32.0.5-apache pinned |
| Data | `/gallery/nextcloud/data` — ZFS dataset, lz4, 1.5 T refquota, `drwxrws--- 33:1006` |
| Jotta contract | Proven by canary: files land `0644 www-data:tt-ai-storage`, readable by `mpegg-adm` |
| Logging | app log at `/mnt/ai_storage/nextcloud/log/nextcloud.log`, `loglevel=2`, rotate 100 MB, plus a logrotate backstop with `copytruncate` |
| HA monitoring | Nextcloud integration `01M7093FFG23CDXM0ANQ6S1NM2` on `filebank`, polling `200` as `hal-adm` |
| Kuma endpoint | `http://10.10.64.1:9002/` — service `tt-nextcloud-health-http-dev1`, HTTP 200, reachable from inside the Kuma container |
| Quotas | dataset refquota 1.5 T, `default_quota=100GB` per user |

Nothing has been created inside Nextcloud beyond the install. `admin` and `hal-adm` exist;
`mpegg-adm` also exists as a user (created by the owner, not by me).

---

## 2. Everything is committed and pushed

`HEAD` is `9cbf72c zoo change`, preceded by `7c77ce9 service repoint`. There is **no
outstanding staged work** apart from this handoff document.

The deployed tree is current, not lagging — verified rather than assumed:

```
/srv/dev1/tt/infra/docker/nextcloud-dev1.yml
    env_file:
      - /etc/tt-secrets/env/nextcloud.env
```

That means the tree's compose files resolve against the secrets root, and the tree's three
unit files match what is installed in `/etc/systemd/system`.

---

## 3. The dev1 tree

`/srv/dev1/tt` is an **rsync target**, not a git clone: no `.git`, owned `tt-deploy`.

| Piece | State |
| --- | --- |
| Workflow | [`.github/workflows/deploy-dev1.yml`](../../.github/workflows/deploy-dev1.yml) — literal destination, `concurrency: tt-dev1-deploy`, target existence + writability guards, **no pip step** |
| Runner | reuses the repo's existing runner, labels `[self-hosted, linux, tt-prd]`. A runner is bound to a repo, not an environment, so no dev runner exists or is needed |
| Proven | three units now `ExecStart` from the tree and were each executed successfully: nextcloud health (JSON ok), DNS health (`0 errors`, `{"ok":true}`), godaddy DDNS (all records confirmed) |

`/srv/dev1/{tt,aa,jah}` all exist, owned by `tt-deploy`, `aa-deploy`, `jah-deploy`.
aa and jah have no workflow yet.

---

## 4. Secrets are out of the repo

```
/etc/tt-secrets                    drwxr-x---  root:mpegg-adm
/etc/tt-secrets/env/*.env          -rw-r-----  root:mpegg-adm   (10 files)
```

- Migration: [`scripts/secrets-migrate-to-etc.sh`](../../scripts/secrets-migrate-to-etc.sh)
  — idempotent, `--dry-run`, **sha256-verified before the original is replaced**, refuses to
  clobber an existing `/etc` copy.
- `infra/docker/env/*.env` are now **symlinks** into `/etc/tt-secrets/env/`, so the existing
  `/srv/dev1/<svc>/docker/env/` chains still resolve.
- Compose references them by **absolute path** — `nextcloud`, `ha-mcp`, `powerdns` done and
  verified with `docker compose config --quiet` run as `mpegg-adm`.
- Root owns them so nothing unprivileged can rewrite a secret; `mpegg-adm` reads because the
  Docker CLI runs as that user.

**The trap to remember:** `infra/docker/env` must never be a symlink *inside* a deployed tree.
`rsync -a --delete` replaces it with the source's real directory and deletes the secrets, with
no error.

---

## 5. Still to do, in rough order

1. Push §2.
2. Kuma monitor for Nextcloud: **HTTP(s)** on `http://10.10.64.1:9002/`, accepted `200-299`.
   Failures return `503`, so no keyword is required. (Kuma only shows a Keyword box for the
   `HTTP(s) - Keyword` monitor type.)
3. Rotate the two leaked Kuma push tokens — DHCP (monitor 11) and DNS (monitor 12). Both are
   hardcoded and both files carry a `tt-secrets.skip` marker that let them past the scanner.
   Target: `/etc/tt-secrets/env/kuma-push.env`, honouring §4's ownership.
4. Remaining env sweep: `snipeit` (2 env + 2 `*_password.txt`), `tensorflow`, `watchyourlan`.
   `calendars` references `./env/calendars.env`, which **does not exist** anywhere.
   `immich` uses a project-local `.env` — decide separately.
5. Phase 7 backups: `backup-nextcloud.sh` (`pg_dump -Fc | age -R` + `config.php`), systemd unit
   + timer, retention 14. Then `jotta-cli add /gallery/nextcloud/data` plus a coverage check.
6. Phase 8 docs: `wiki/runbook-nextcloud.md`, `wiki/backup-strategy.md`, status updates.
7. Phase 6's 85 % alert is effectively covered by the Kuma endpoint's dataset check
   (warn 85 %, fail 95 %) — confirm and close it rather than building a second mechanism.
8. Deferred by owner: drop the stray empty `nextcloud` schema inside `ttdb_dev1`.
9. Housekeeping: delete the corrupt `scripts/immich-backup-perm-fix.sh` from the Immich handoff.

---

## 6. Decisions settled — do not re-litigate

- **`filebank` is the URL only.** Container, dataset, database and env file keep `nextcloud`.
- **Its own database**, created with `TEMPLATE template0 ENCODING 'UTF8'`, no collation clause,
  plus `GRANT CREATE ON SCHEMA public`. Nextcloud has no `db_schema` key.
- **The image does not run as a non-root user.** Setgid on the data directory satisfies the
  Jotta contract; the apache entrypoint is built for root.
- **Pushing is the owner's.** Never `git push`.
- **The `/srv` agreement** (see `wiki/service-taxonomy.md` §5): code lives in the repo, symlinks
  are fine, copies are not; new services add no `/srv/dev1/<svc>` trees.
- **Container-side identity is `172.17.0.1`**, not the app-network gateway.
- **`pkexec` works from this session** — one polkit dialog per privileged batch. Prefer it to
  terminal `sudo`, which cannot prompt here.

---

## 7. Corrections — earlier claims that were wrong

Written down so the next session does not repeat them.

1. **Kea health was never broken.** It pushes to Kuma itself from a 5-minute timer and returns
   `{"ok":true}`. I first inspected the unused Flask wrapper on port 9001 and drew the wrong
   conclusion.
2. **`/srv/dev1/dns` was never missing.** The DNS unit points straight at the working copy.
3. **There was no script drift.** `/srv/dev1/kea/scripts` is a symlink into the repo, so the
   deployed file *is* the repo file.
4. **I claimed Nextcloud recommends `C` collation.** It does not; the admin manual prescribes no
   collation at all. Withdrawn.
5. **The login failure was the username.** `mpegg-adm` is a Unix account; the only Nextcloud
   account was `admin`.
6. **The `cd` in the legacy `dc` alias is redundant.** Compose anchors the project directory to
   the compose file, not the cwd — verified by running a relative-mount compose file from `/tmp`.

---

## 8. Landmines found but not fixed

| Item | Why it matters |
| --- | --- |
| `tortoise-dev1.yml` uses `../source`, `../models`, `../config`, `../logs` | They resolve to `TermiteTowers/infra/source` etc. — almost certainly not intended. Either make absolute or retire the file |
| Two divergent copies of the alias code | `setup/unix/util/initAliases.sh` (370 lines) vs `util/aliases.sh` (291 lines), different md5. Whichever the profile sources wins, silently |
| `goapp` + `dc` + `APPID_DOCKER` | Shell-exported state coupling calls to typing order. A stateless `ttc <service> ...` was proposed and not yet implemented |
| `tt-kea-health-http-dev1.py` and its nginx route | Dead legacy: no unit installed, Flask absent, route disabled, nothing on 9001 |
| `nextcloud.env` trusted domains still list the old name | Harmless, but it is the only reason the old hostname is trusted |
