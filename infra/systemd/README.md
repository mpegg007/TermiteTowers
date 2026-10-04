<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/systemd/README.md:167 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: a3e36f9e3693c48c244dc3c02b8d392aee53c045 % -->
<!-- %ccm_git_commit_id: af3b4e614eaf7f1e2342aedb19c1c31089a044fd % -->
<!-- %ccm_git_commit_count: 167 % -->
<!-- %ccm_git_commit_date: 2026-10-03 17:41:25 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: backup scripts % -->
<!-- %ccm_git_modify_date: 2026-10-03 17:41:26 % -->
<!-- %ccm_git_file_last_modified: 2026-10-03 17:02:40 % -->
<!-- %ccm_git_file_name: README.md % -->
<!-- %ccm_git_path: infra/systemd/README.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: us-ascii % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 3378 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-02-07 mpegg  comment cleanup  --> 
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
# Systemd Units Deployment Pattern

Preferred pattern: keep units in the repo (via /srv/dev1 symlink) and link them into /etc/systemd/system. Avoid copying with sudo install/cp so changes remain single-sourced.

**Exception:** Logrotate configurations (`/etc/logrotate.d/`) must be **copied** and owned by root, as logrotate enforces strict permission checks that symlinks to user directories often fail.

Steps (example for tt-backup-mealie):

```bash
# from any directory
sudo ln -sf /srv/dev1/systemd/tt-backup-mealie.service /etc/systemd/system/tt-backup-mealie.service
sudo ln -sf /srv/dev1/systemd/tt-backup-mealie.timer   /etc/systemd/system/tt-backup-mealie.timer
sudo systemctl daemon-reload
sudo systemctl enable --now tt-backup-mealie.timer
```

Notes:

- Source of truth: /srv/dev1/systemd (symlink to repo).
- Unit ExecStart paths should use /srv/dev1/... not /home/....
- Verify: `systemctl status <unit>` and `systemctl list-timers --all | grep tt-`.

## Copy-deploy exception: unprivileged backup scripts (`tt-backup`)

Units normally `ExecStart` a path under `/srv/dev1/...` (a symlink into the repo).
That does **not** work for the `tt-backup` jobs, which run as a non-root service
account:

* `/home/mpegg-adm` is mode `0750`, so `tt-backup` cannot even traverse the repo
  to reach an `ExecStart` target inside it.
* Relaxing the home directory to allow that would be a real hardening
  regression, and it would also force `ProtectHome=read-only` instead of the
  stronger `ProtectHome=yes`.

So the backup **script** is copied to a root-owned location, and the unit uses
that (the same precedent as logrotate, which is also copied rather than
symlinked). The repo stays the single source of truth; re-running the installer
is the deploy step.

```bash
# in infra/backups/scripts/install-tt-backup-tthealth.sh
install -o root -g root -m 0755 <repo>/infra/backups/scripts/backup-tthealth.sh \
        /usr/local/lib/tt-backup/backup-tthealth.sh
```

```ini
# tt-backup-tthealth.service
ExecStart=/usr/local/lib/tt-backup/backup-tthealth.sh
ProtectHome=yes
```

The unit **files** themselves are still symlinked into `/etc/systemd/system` as
usual - `systemd` reads those as root, so the `/home` traversal problem does not
apply to them.

