<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: unknown %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 50d9f3cd3420564171b2a1a2da37f662f8903aeb %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: unknown %
  %ccm_git_commit_date: unknown %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2026-02-07 15:39:15 %
  %ccm_git_file_last_modified: 2026-01-02 18:10:06 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/backups/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1370 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Backup Strategy

This directory contains scripts and configuration for backing up applications and services in TermiteTowers.

## Strategy

1. **App-Specific Scripts**: Each application has a dedicated script in `scripts/` that handles the backup logic (e.g., stopping containers, dumping databases, archiving files).
2. **Local Storage**: Backups are stored locally in `/mnt/ai_storage/backups/<app_name>/`.
3. **Cloud Replication**: The local backup directory is monitored by Jotta CLI for replication to cloud storage.
4. **Scheduling**: Systemd timers are used to schedule the backup jobs.

## Installation

To enable a backup job (e.g., for Mealie):

1. **Link Systemd Units**:

    ```bash
    sudo ln -s /srv/dev1/systemd/tt-backup-mealie.service /etc/systemd/system/
    sudo ln -s /srv/dev1/systemd/tt-backup-mealie.timer /etc/systemd/system/
    ```

2. **Reload Systemd**:

    ```bash
    sudo systemctl daemon-reload
    ```

3. **Enable and Start Timer**:

    ```bash
    sudo systemctl enable --now tt-backup-mealie.timer
    ```

4. **Verify**:

    ```bash
    systemctl list-timers --all
    ```

## Jotta Configuration

Ensure `jotta-cli` is installed and authenticated. The backup scripts attempt to add the backup directory to Jotta's backup set automatically.

To manually add a folder:

```bash
jotta-cli add /mnt/ai_storage/backups/mealie
```
