<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/backups/README.md:167 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 3148f1cac5c6309191c07d9f2b3b6f4a1cf3d723 % -->
<!-- %ccm_git_commit_id: af3b4e614eaf7f1e2342aedb19c1c31089a044fd % -->
<!-- %ccm_git_commit_count: 167 % -->
<!-- %ccm_git_commit_date: 2026-10-03 17:41:25 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: backup scripts % -->
<!-- %ccm_git_modify_date: 2026-10-03 17:41:25 % -->
<!-- %ccm_git_file_last_modified: 2026-10-03 17:40:37 % -->
<!-- %ccm_git_file_name: README.md % -->
<!-- %ccm_git_path: infra/backups/README.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 12819 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: unknown  unknown  unknown  --> 
 <!-- %git_commit_history: unknown  unknown  unknown  --> 
 <!-- %git_commit_history: 2026-02-07 mpegg  feb2026.1  --> 
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
 <!-- %git_commit_history: 2026-02-07 mpegg  feb2026.1  --> 
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
 <!-- %git_commit_history: unknown  unknown  unknown  --> 
 <!-- %git_commit_history: 2026-02-07 mpegg  feb2026.1  --> 
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
 <!-- %git_commit_history: 2026-02-07 mpegg  feb2026.1  --> 
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
<!-- %git_commit_history: 2026-02-07 mpegg  feb2026  % -->
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

## PostgreSQL backups - `tthealth_dev1` (encrypted, `tt-backup` account)

Database backups use a single generic, least-privilege service account,
**`tt-backup`**, intended to own *all* future database/application backups. The
Mealie job predates it (see Follow-ups).

### Why a dedicated account

PHI must be encrypted before it leaves the host, and the backup identity must
not be able to undo what it protects. `tt-backup` is constrained by five
independent layers - compromise of the job yields "can read the DB, can write
encrypted blobs", nothing more:

| Layer | What is denied |
| --- | --- |
| OS | `nologin` shell; not in `sudo`, `tt-admin`, `tt-dbadmin`, `docker` or `adm`; only member of `tt-ai-storage` |
| Secrets | own pgpass at `/etc/tt-backup/tthealth.pgpass` (0600); cannot read `/srv/prd/jah/.env` |
| Database | role `tt_backup` = `pg_read_all_data` + `default_transaction_read_only=on`; no INSERT/UPDATE/DELETE/DDL |
| Crypto | holds only the age **recipient**; the private identity stays with `mpegg-adm` |
| Cloud | no Jotta credentials - `jottad` (running as `mpegg-adm`) performs the upload |

### Files

| Path (repo) | Purpose |
| --- | --- |
| `infra/backups/scripts/backup-tthealth.sh` | the backup itself (`pg_dump -Fc \| age -R`) |
| `infra/backups/scripts/install-tt-backup-tthealth.sh` | one-time root installer, also the deploy path |
| `infra/backups/sql/tt_backup-role.sql` | PostgreSQL role provisioning |
| `infra/backups/age/tthealth-recipient.txt` | age public key (public - safe to commit) |
| `infra/systemd/tt-backup-tthealth.{service,timer}` | schedule (daily 03:30 + up to 10m jitter) |
| `infra/logrotate/logrotate.d/tt-backup.conf` | rotation for `/var/log/tt-backup/` |

### Data flow

```
pg_dump -Fc --(pipe; never on disk)--> age -R <recipient> --> /mnt/ai_storage/backups/tthealth/*.dump.age
                                                                          |
                                                     jottad (as mpegg-adm, hourly scan)
                                                                          v
                                                                    Jottacloud
```

* The dump streams straight into `age` - plaintext PHI is never written to a file.
* Local retention is 7 days (`RETENTION_DAYS`); Jottacloud holds the long history.
* Files `0640`, directory `2750` (setgid), group `tt-ai-storage` so `jottad` can read them - see [Permissions are the upload contract](#permissions-are-the-upload-contract).
* A failed `pg_dump` leaves **no** partial `.age` file behind (cleanup trap, exit 5).

### Deploy

```bash
# 0. once, as DB superuser: create the read-only backup role
sudo -u postgres psql -d tthealth_dev1 -f infra/backups/sql/tt_backup-role.sql
sudo -u postgres psql -d tthealth_dev1 -c "\password tt_backup"

# 1. once, as root: account + secrets + dirs + units + logrotate
sudo TTBACKUP_PG_PASSWORD='<the-password>' \
     infra/backups/scripts/install-tt-backup-tthealth.sh

# 2. once, as mpegg-adm: tell Jotta about the new folder
jotta-cli add /mnt/ai_storage/backups/tthealth
jotta-cli scan tthealth
```

Re-run step 1 whenever these files change - it is the deploy path. The script is
**copied** to `/usr/local/lib/tt-backup/`, not symlinked; see
`infra/systemd/README.md` for why.

### Verify

```bash
sudo -u tt-backup /usr/local/lib/tt-backup/backup-tthealth.sh   # run on demand
systemctl list-timers tt-backup-tthealth.timer
sudo journalctl -u tt-backup-tthealth.service -n 40
sudo cat /var/log/tt-backup/tthealth.log
```

Restore (requires the age identity, i.e. an administrator - never `tt-backup`):

```bash
age --decrypt -i ~/.config/age/tthealth-backup.txt \
    /mnt/ai_storage/backups/tthealth/tthealth_dev1_YYYYmmdd_HHMMSS.dump.age \
  | pg_restore --clean --if-exists -h monolith -U tthealth_dev1_owner -d tthealth_dev1
```

### Upload verification (Jotta)

`tt-backup` and the systemd unit only prove the *local* backup exists. Nothing in
them proves it reached Jottacloud, so the uploader is checked separately:

```bash
jotta-cli status               # per-folder Files / Status
jotta-cli scan tthealth        # force a rescan (run as mpegg-adm)
jotta-cli list uploads         # transfer history
tail -f ~/.jottad/jottabackup.log
```

Healthy looks like this:

```
Path      : /mnt/ai_storage/backups/tthealth
Files     : 1 (11.46MiB)
Status    : Up to date - 2026-10-04 03:31:22
```

`jottad` scans on an interval, so a freshly written file can legitimately sit in
`have not been backed up` for a while. It is only a problem if it stays there
(see the next section).

### Permissions are the upload contract

`jottad` runs as `mpegg-adm`; the backup files are written by `tt-backup`.
`mpegg-adm` is in `tt-ai-storage` but **not** in `tt-backup`, so the file **group**
is the only thing that grants the uploader read access:

| Object | Required | Why |
| --- | --- | --- |
| `/mnt/ai_storage/backups/tthealth` | `tt-backup:tt-ai-storage` **`2750`** | group needs `r-x` to list; setgid makes new files inherit `tt-ai-storage` |
| `*.dump.age` | `tt-backup:tt-ai-storage` **`0640`** | `mpegg-adm` reads via group; never world-readable |

The **setgid bit is load-bearing**. At `0750` a new file inherits the *writer's*
primary group (`tt-backup`) rather than the directory's group, so the file lands
as `tt-backup:tt-backup 0640` and `mpegg-adm` cannot read it. `backup-tthealth.sh`
now also `chgrp`s the finished file and logs the resulting
`owner:group mode`, so a lost setgid bit is self-healing and visible.

**Failure mode to recognise.** `jotta-cli status` stuck at

```
Files     : 0 (0bytes)
Status    : 1 file(s) (11.46MiB) have not been backed up
```

with **no** error in `~/.jottad/jottabackup.log`. The scan finds the file
(directory traversal needs only `x`, and `stat` succeeds) but the transfer never
starts, so `grep -i 'permission denied'` finds nothing - the read is never
attempted. Diagnose and repair:

```bash
stat -c '%A %U:%G' /mnt/ai_storage/backups/tthealth/*.dump.age

sudo chmod 2750 /mnt/ai_storage/backups/tthealth
sudo chgrp tt-ai-storage /mnt/ai_storage/backups/tthealth/*.dump.age
sudo chmod 0640          /mnt/ai_storage/backups/tthealth/*.dump.age
jotta-cli scan tthealth
```

Re-running the installer as root does the directory part and repairs existing
files, so it is an equally good fix.

### age keys - read before touching the keys

* Identity: `/home/mpegg-adm/.config/age/tthealth-backup.txt` (0600, not in git,
  never readable by `tt-backup`).
* **Escrow the identity offline now.** Without it every encrypted backup is
  permanently unreadable. It must also never enter `/mnt/ai_storage`: `jottad`
  would upload it alongside the backups it protects, defeating the encryption.
* Rotating the key means changing two things - the identity and
  `age/tthealth-recipient.txt`. Backups made before the rotation still require
  the previous identity.

### Validation performed (2026-10-03)

Run against the live database, writing to a throwaway directory:

* `backup-tthealth.sh` → exit 0, 534 MB DB → 12 MB `.dump.age`.
* Output decrypts with the identity and `pg_restore --list` reads it: 91 TOC
  entries, 16 health-schema tables, `Format: CUSTOM`, `Compression: gzip`.
* Wrong password → exit 5 and **no** leftover file (cleanup trap fired).
* **Post-install finding (same day).** `jotta-cli status` reported
  `1 file(s) (11.46MiB) have not been backed up` indefinitely, with **no** error in
  `~/.jottad/jottabackup.log`. Cause: the directory was created `0750` **without**
  the setgid bit, so the dump landed as `tt-backup:tt-backup 0640` and the uploader
  (`mpegg-adm` - a member of `tt-ai-storage`, not of `tt-backup`) could not read
  it, so the transfer never started. Reproduced and fixed: `0750` dir →
  `:writer-primary-group 640`; `2750` dir → `:tt-ai-storage 640`. The installer now
  sets the setgid bit and repairs existing files, and `backup-tthealth.sh`
  `chgrp`s the finished dump and logs its `owner:group mode`. See
  "Permissions are the upload contract".

### Follow-ups

1. **Mealie retrofit** - `tt-backup-mealie.service` still runs as `root`, writes
   *plaintext* tarballs and calls the misspelled `jolla-cli`. It should move onto
   the `tt-backup` account and be age-encrypted like this job.
2. **Gatekeepers** - `mpegg-adm` (and human `mpegg`) still hold
   `tthealth_dev1_owner` / `tt-dbadmin`. Dropping that is a separate decision:
   it is the current break-glass path.
3. **Log path split** - `/var/log/tt-backup-*.log` (flat, `su root adm`) vs
   `/var/log/tt-backup/*.log` (directory, `tt-backup`). The split is forced by
   the existing `tt-apps` logrotate glob; revisit if `tt-apps` is reworked.
4. **Off-host escrow check** - periodically confirm the age identity is still
   retrievable from the offline escrow, not only from this host.
5. **`jotta-cli` upgrade (cosmetic nag)** - every `jotta-cli` command prints
   `0.17.148769 -> 0.17.176206`. It is only a banner; backups work fine on the
   installed version. The banner's "use the packagemanger used to install
   jotta-cli" advice does **not** work here: the apt source was disabled during a
   release upgrade (`/etc/apt/sources.list.d/jotta-cli.list.distUpgrade` - note
   the `.distUpgrade` suffix), so `apt-cache policy jotta-cli` sees only
   `100 /var/lib/dpkg/status` and `apt install --only-upgrade` is a no-op. To
   actually take the update: re-enable the source
   (`sudo mv /etc/apt/sources.list.d/jotta-cli.list.distUpgrade /etc/apt/sources.list.d/jotta-cli.list`,
   then `sudo apt update && sudo apt install --only-upgrade jotta-cli`), and then
   **restart the daemon** - `jottad` is a *user* unit
   (`/usr/lib/systemd/user/jottad.service`) and keeps the old binary in memory
   until `systemctl --user restart jottad`. Schedule it for when someone can
   watch `jotta-cli status` recover.

