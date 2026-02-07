<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: unknown %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 2d5ee7ddea0e40f4e1de2168627472bbd1cca930 %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: unknown %
  %ccm_git_commit_date: unknown %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2026-02-07 15:40:18 %
  %ccm_git_file_last_modified: 2026-02-07 15:27:26 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/systemd/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 966 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
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
