<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: infra/backups/README.md % -->
<!-- %ccm_git_object_id: infra/backups/README.md@186 % -->
<!-- %ccm_git_commit_date: 2026-10-28 11:35:25 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: feat(backups): phase 3 - encrypt to per-tier keys % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-03 mpegg  backup scripts  -->
 <!-- %git_commit_history: unknown  unknown  unknown  -->
 <!-- %git_commit_history: 2026-02-07 mpegg  feb2026.1  -->
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
| `infra/backups/scripts/backup-tthealth-user.sh` | on-demand export + upload as a normal user (no sudo, no service account) |
| `infra/backups/scripts/install-tt-backup-tthealth.sh` | one-time root installer, also the deploy path |
| `infra/backups/sql/tt_backup-role.sql` | PostgreSQL role provisioning |
| `infra/backups/age/registry.json` | public registry: tiers, generations, public keys |
| `infra/backups/age/<tier>.recipient` | current age public key per tier (public - safe to commit) |
| `infra/backups/scripts/tt-keys.sh` | keyring tooling: init / list / status / verify / unlock |
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

Restore is two steps: the dump is encrypted to a per-tier DEK, and that DEK is
itself wrapped by the master identity. Never `tt-backup` - it can do neither.

```bash
# the generation comes from the filename: ...__health-2026Q4.dump.age
infra/backups/scripts/tt-keys.sh unlock health:2026Q4 --out /dev/shm/health.key
age --decrypt -i /dev/shm/health.key \
    /mnt/ai_storage/backups/tthealth/tthealth_dev1_YYYYmmdd_HHMMSS__health-2026Q4.dump.age \
  | pg_restore --clean --if-exists -h monolith -U tthealth_dev1_owner -d tthealth_dev1
shred -u /dev/shm/health.key
```

Dumps taken before the per-tier cutover carry no `__health-<gen>` suffix and are
generation `health/legacy` - unlock `health:legacy`, or use the old identity
file directly.

### On-demand export as a normal user (no sudo)

`backup-tthealth.sh` is root-installed and writes into a `tt-backup`-owned
directory, so a human cannot run it or extend it without privilege. For
"export this database right now" - before a migration, a restore rehearsal or a
risky schema change - use `scripts/backup-tthealth-user.sh`. It needs no sudo,
no systemd, no service account, no password and no change to `jottad`.

```bash
scripts/backup-tthealth-user.sh              # pg_dump | age -> local, then upload
scripts/backup-tthealth-user.sh --dry-run    # everything except the upload
scripts/backup-tthealth-user.sh --no-upload  # keep it local only
scripts/backup-tthealth-user.sh --keep 30 --remote tthealth-dev1
```

How it differs from the scheduled job:

| | `backup-tthealth.sh` (timer) | `backup-tthealth-user.sh` (on demand) |
| --- | --- | --- |
| Runs as | `tt-backup` service account | the invoking admin (`mpegg-adm`) |
| Scheduled | daily 03:30 + jitter | never - you run it |
| Auth | `tt_backup` role, password from pgpass | local socket + peer auth, no password |
| Local path | `/mnt/ai_storage/backups/tthealth` | `~/backups/tthealth` (`0700`, files `0600`) |
| Reaches Jotta via | `jottad` continuous backup | `jotta-cli archive` (one-shot put) |
| Cloud location | Jotta **Backups** area | Jotta **Archive** area |

* **Encryption is not optional.** It uses the `health` tier recipient
  (`age/health.recipient`), the same key as the scheduled job, so the restore
  procedure is identical - see above. `pg_dump` streams straight into `age`;
  plaintext never touches the disk. The filename carries `__health-<gen>`.
* **Peer auth.** The script defaults to `DB_HOST=/var/run/postgresql` and
  `DB_USER=$(id -un)`. `mpegg-adm` is a member of `tthealth_dev1_owner` and
  `pg_hba` trusts the local socket, so no credential is handled. Override with
  `DB_HOST=monolith DB_USER=tt_backup PGPASSFILE=~/.pgpass` for TCP.
* **`--remote` is a folder.** `jotta-cli archive`'s `--remote` is the *full*
  destination including the filename (`--remote=folder/file`); passing only a
  folder name would upload a file called `folder`. The script appends the
  basename for you and verifies the result via `jotta-cli ls --json archive/<folder>`.
* Local retention is `--keep` days (default 7). Jotta's Archive has no rotation,
  so delete old exports in the web UI if you want the cloud copy pruned too.
* Exports land in Jotta's **Archive**, not the continuous-backup folder, so they
  do **not** appear in `jotta-cli status` - that output stays focused on the
  scheduled job.

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

### age keys - per tier, master-wrapped

Three classification tiers, one DEK each: **health** (the PHI database),
**mail** (the Thunderbird archive) and **general** (everything else). They are
deliberately separate so a compromise or a rotation of one cannot touch the
others.

| Object | Where | Secret? |
| --- | --- | --- |
| `<tier>.recipient` (public half) | `infra/backups/age/`, committed | no |
| `registry.json` (tier -> generation -> public key) | `infra/backups/age/`, committed | no |
| `keyring.tar.age` (every DEK, wrapped) | `/mnt/ai_storage/backups/tt-keys/` 0600, dir 0700 `mpegg-adm` | no - ciphertext |
| master identity | **off this host** (1Password) | **yes** |

* The keyring is ciphertext on purpose: `jottad` uploading it is required for
  disaster recovery, and it is useless without the master.
* Unwrapping needs the master identity, which is why `tt-backup` (and any
  service account) can never decrypt a backup. `scripts/install-tt-keys.sh
  --check` asserts both the DAC isolation and the Jotta coverage.
* `~/.config/age/tthealth-backup.txt` still matters: it is generation
  **`health/legacy`** and reads every dump and mail chunk made before the
  per-tier cutover. Keep it; it is not used for new backups.
* Inspect without any secret: `scripts/tt-keys.sh status` / `list`.
  Prove the whole chain (needs the master): `scripts/tt-keys.sh verify`.
  Unwrap one DEK for a restore: `scripts/tt-keys.sh unlock health:2026Q4`.
* Generation labels are `YYYYQn`. A rotation adds a generation and repoints
  `<tier>.recipient`; **old generations are never deleted while an artifact
  still needs them** (`retire_after` in the registry, `hold` for `legacy`).
  `rotate` / `rewrap` / `audit` / `prune` are not implemented yet (phase 5).

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


## Thunderbird mail archive (encrypted, per-year chunks, no sudo)

The Thunderbird profile holds a local copy of every IMAP mailbox. Once a message
is deleted from the server that copy is the *only* copy, so a dead disk loses
the history. `scripts/backup-mail.py` exports the mbox folders into compressed,
age-encrypted chunks grouped by year.

Mail is append-mostly, so the shape is the opposite of the DB job: instead of one
fresh dump per night, a **completed year is written once and never rewritten**.
The steady state uploads one new file per year - it does not re-upload every old
email on every run.

```bash
scripts/backup-mail.py --dry-run            # scan + show the plan, write nothing
scripts/backup-mail.py                      # seal every completed period
scripts/backup-mail.py --include-current    # also refresh the year in progress
scripts/backup-mail.py --only 2018          # (re)build one period
scripts/backup-mail.py --granularity month  # finer chunks (smaller risk window)
scripts/backup-mail.py --list               # what is archived
```

### Files

| Path (repo) | Purpose |
| --- | --- |
| `scripts/backup-mail.py` | the archive tool (stdlib Python; streams tar -> zstd -> age) |
| `scripts/install-tt-backup-mail-user.sh` | installs the **user** timer + archive dir; no sudo |
| `systemd/user/tt-backup-mail.{service,timer}` | daily 04:30 user units (`@REPO_DIR@` substituted on install) |

### What lands where

```
/mnt/ai_storage/backups/thunderbird/
  mail-2018.tar.zst.age        sealed year
  mail-2026.partial.tar.zst.age only with --include-current, rewritten as mail arrives
  state.json                   counts + sha256 per chunk, 0600
```

* **Excluded by default:** `Trash`, `Junk`, `Junk E-mail`, `Deleted Items`,
  `Spam` (`--exclude` overrides). Non-mail artefacts (`.msf`, `.sqlite*`, `.dat`)
  and anything that is not an mbox are always skipped.
* **Inside the chunk:** one tar member per folder-period, named after the
  original path and prefixed with the period, so extracting never overwrites a
  live profile folder. Each member is a real mbox fragment (starts with a `From `
  line) and opens in Thunderbird or any mbox reader:

  ```
  2018/ImapMail/outlook.office365.com/Sent
  2018/ImapMail/127.0.0.1/Labels.sbd/mpegg007@gmail.com
  2018/ImapMail/127.0.0.1/Labels.sbd/mpegg007@gmail.com.part2
  ```

  A fragment larger than `--fragment-cap` MB (default 64) is split into numbered
  `partN` members rather than buffered in memory; concatenate them in order when
  restoring by hand.
* **Rebuild rule:** a sealed chunk is rewritten only when its message count
  actually changes (late-arriving mail carrying an old `Date:` header). New mail
  in the current year never touches an older year.
* **No plaintext spool:** messages stream straight into `tar | zstd | age`. The
  source mboxes are already plaintext on the same disk; the tool never writes a
  second plaintext copy.
* **Encryption:** the `mail` tier (`age/mail.recipient`), deliberately separate
  from the PHI database's key. Each chunk records the generation it was sealed
  with in `state.json`, so a rotation never leaves a chunk unattributable.
  Override with `--tier` / `--recipient`.

### Restore

```bash
infra/backups/scripts/tt-keys.sh unlock mail:2026Q4 --out /dev/shm/mail.key
age -d -i /dev/shm/mail.key \
    /mnt/ai_storage/backups/thunderbird/mail-2018.tar.zst.age \
  | zstd -d | tar -tvf -              # inspect
age -d -i /dev/shm/mail.key \
    /mnt/ai_storage/backups/thunderbird/mail-2018.tar.zst.age \
  | zstd -d | tar -xf - -C /tmp/mail-restore
shred -u /dev/shm/mail.key
```

`--list` shows the tier/generation recorded for each chunk. Chunks sealed before
the cutover show `pre-tier/legacy` and need `~/.config/age/tthealth-backup.txt`.

Each extracted file is an mbox for that folder/year. To bring one back into a
live profile, copy the messages into the corresponding local folder rather than
overwriting the live mbox.

### Schedule + Jotta (both without root)

```bash
scripts/install-tt-backup-mail-user.sh          # dir + user units + timer
scripts/backup-mail.py                          # first full archive
jotta-cli add /mnt/ai_storage/backups/thunderbird
jotta-cli scan
```

`jottad` already runs as `mpegg-adm` (a user unit), so a **user** timer and a
folder added to the continuous backup is all that is needed - no system unit, no
sudo, no service account.

### Gotchas

* **Snap revisions.** Thunderbird here is the snap build, so the profile lives
  under `~/snap/thunderbird/<revision>/.config/thunderbird/<profile>/` and
  `current/` follows the active revision. An older revision's tree can hold mail
  the current one no longer has; archive it too:

  ```bash
  scripts/backup-mail.py --extra-root ~/snap/thunderbird/1274/.config/thunderbird/<profile>/ImapMail
  ```

  Members then land under `extra-ImapMail-<hash>/`. That old tree is also ~7.8 GB
  of duplicate profile and is worth pruning once archived.
* **Gmail views.** `[Gmail]/All Mail`, `All Mail` and `Labels/...` are different
  views of the same messages, so the archive is deliberately larger than the sum
  of distinct messages. No de-duplication is done - dropping a copy could look
  like losing mail.
* **1969/1970 chunks** exist because some messages carry a bogus epoch `Date:`.
  They are tiny; the `undated` chunk holds mail with no usable date at all.
* `jotta-cli status` reports the folder like any other continuous backup; a chunk
  appears once `jottad` scans and uploads it.
