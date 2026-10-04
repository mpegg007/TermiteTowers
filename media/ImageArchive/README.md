<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: media/ImageArchive/README.md:145 %
  %ccm_git_author: Matthew Pegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 909e3917f3de55ff12284535a33b9a1bc4a1cd74 %
  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
  %ccm_git_commit_count: 145 %
  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
  %ccm_git_commit_author: Matthew Pegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: adding readme %
  %ccm_git_modify_date: 2026-05-24 15:14:56 %
  %ccm_git_file_last_modified: 2026-05-24 15:14:56 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: media/ImageArchive/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 8111 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# ImageArchive

A pipeline for ingesting, cataloguing, tagging, and backing up scanned photo TIFFs from SilverFast.  
Primary store is a structured folder tree on external storage. PostgreSQL is the metadata DB.  
Every image file has a companion `.md` sidecar.

---

## Where Things Live

| Thing | Location |
|---|---|
| Archive root | `C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive` |
| DB | PostgreSQL `ttphoto_dev1` on `192.168.4.10` |
| DB owner account | `ttphoto_dev1_owner` (DDL via SSH peer auth) |
| DB app account | `ttphoto_dev1_app` (DML — used by all Python scripts via `PG_DSN` in `media/.env`) |
| Scripts | `media/ImageArchive/` |
| exiftool | `C:\Apps\exiftool-13.58_64\exiftool.exe` |
| jotta-cli | `C:\Program Files\Jottacloud\Update\Data\Current\jotta-cli.exe` |

---

## Archive Folder Structure

```
PhotoArchive/
  001_Matthew/
    RAW_HDRi/          ← raw HDR scans from SilverFast (.tif)
    TIFF_Archive/      ← processed/exported TIFFs
    JPG_Share/         ← web-res JPGs
    JPG_Print/         ← print-res JPGs
    Workfiles/         ← Photoshop / working files
  002_Dianne/
    ...
  003_Owen/
    ...
```

Person folders are created by `New-PhotoArchiveFolders.ps1`. Numbers are zero-padded and never reused.

### File Naming Convention

Every file in `RAW_HDRi` and `TIFF_Archive` must be **canonically named** before the pipeline will process it:

```
Owner_YYYYMMDDHHmmss_<original_scan_name>.tif
```

Example: `Matthew_20260521143022_20260521_0001.tif`

`Rename-ScanFiles.ps1` does the rename. Only canonically named files are picked up by `load_archive_db.py`, `build_stacks_db.py`, and `backup_hdri_jotta.py`.

---

## Database Schema

| Table | Purpose |
|---|---|
| `images` | One row per image: path, hash, file_name, folder, archive_owner, file_date, file_bytes |
| `image_tags` | All exiftool tags per image (tag_key / tag_value) |
| `tag_history` | Change log — records every tag add/change |
| `stacks` | A group of related image files (same scan, different formats) |
| `stack_members` | image_id → stack_id membership |
| `tag_master` | Controls which tags propagate and appear in reports; alias/canonical relationships |
| `file_backups` | Backup tracking: destination, remote_path, status, backed_up_at per image |
| `stack_tag_authority` | View — best authoritative tag value per stack member for propagation |

DDL lives in `init_schema.sh`. Run on the monolith as `mpegg-adm` (peer auth). New migrations are SCP'd then run via SSH — app account cannot CREATE TABLE.

---

## Sidecar Format (`.md`)

Every image file has `<filename>.tif.md` alongside it.

```markdown
## Identity
- ImageHash, FileName, FileDate, FileBytes, OriginalScanName, OriginalFileType

## Name History
| Timestamp | Path |

## Derived Files
| Timestamp | ImageHash | Path |

## Tag Snapshot — YYYY-MM-DD HH:MM      ← diff appended each time tags change
```diff
- old_tag: old_value
+ new_tag: new_value
```

## Current Tag State
```text
all current exiftool tags
```

## Backups
| Destination | Remote Path | Backed Up | Status |
```

The sidecar is the human-readable mirror of the DB. The DB is authoritative.

---

## Scripts

### Setup

| Script | What it does |
|---|---|
| `New-PhotoArchiveFolders.ps1` | Interactively creates numbered person folders with all standard subfolders |
| `init_schema.sh` | Creates all DB tables/views on the monolith (run once, or for fresh installs) |
| `setup_ttphoto_dev1.sh` | Full DB user/role setup |

### Ingestion Pipeline (run in order after scanning)

| Step | Script | Notes |
|---|---|---|
| 1 | `Rename-ScanFiles.ps1` | Renames raw scan output to canonical `Owner_14digits_originalname.tif` |
| 2 | `scan_photoarchive.py` | Walks archive, calls `extract_to_sidecar.py` for any image with no sidecar or a newer mtime |
| 3 | `extract_to_sidecar.py` | Runs exiftool on a single file, writes/updates the `.md` sidecar (name history, tag snapshots, current state) |
| 4 | `load_archive_db.py` | Parses all `.md` sidecars, upserts into `images` + `image_tags` + `tag_history` |

`scan_photoarchive.py` is the normal entry point — it calls `extract_to_sidecar.py` per file. Call `extract_to_sidecar.py` directly to re-process a single file.

### Stack Building

| Script | What it does |
|---|---|
| `build_stacks_db.py` | Rebuilds `stacks` / `stack_members` from DB using union-find on ImageHash + canonical stem |
| `build_stack_map.py` | File-based version (no DB) — outputs `stacks.json`; useful for inspection without a DB connection |

Stacks group related files: same hash = identical pixels; same canonical stem = same scan in different formats.

### Tag Management

| Script | What it does |
|---|---|
| `generate_tag_master_excel.py` | Queries all distinct `tag_key` values from DB, produces `tag_master_import.xlsx` pre-classified with best-guess propagatable/include_in_report flags |
| `load_tag_master.py` | Imports the reviewed Excel into `tag_master` table |
| `propagate_tags.py` | For each stack, finds the authoritative value of each propagatable tag and writes it to members that are missing it or have a different value. Never touches HDRi masters. |

`propagate_tags.py --apply` writes; without `--apply` it dry-runs.

### Reporting

| Script | What it does |
|---|---|
| `stack_report.py <stack_id>` | Prints / writes a `.md` report for one stack: members, file sizes, divergent tags |
| `stack_compare_excel.py` | Excel comparison across multiple stacks |

### Backup

| Script | What it does |
|---|---|
| `backup_hdri_jotta.py` | Backs up canonically-named files in `RAW_HDRi` and `TIFF_Archive` to Jottacloud via `jotta-cli archive`. Records status in `file_backups` table and sidecar `## Backups` section. |
| `add_file_backups.sql` | Migration to create `file_backups` table. SCP to server, run via SSH as `mpegg-adm`. |

```
python backup_hdri_jotta.py --dry-run          # preview
python backup_hdri_jotta.py --limit 1          # test one file
python backup_hdri_jotta.py                    # full run
python backup_hdri_jotta.py --force            # re-upload already-backed-up files
python backup_hdri_jotta.py --owner Dianne     # one person only
```

Jottacloud remote path: `Archive/<device>/PhotoArchive/<NNN_Owner>/<folder>/<filename>`  
`REMOTE_ROOT` at the top of the script controls the prefix.

---

## Typical Workflow After a Scan Session

```
1.  SilverFast scan  →  RAW_HDRi/20260521_0001.tif  (raw output, not yet canonical)

2.  Rename-ScanFiles.ps1
      RAW_HDRi/20260521_0001.tif
      → RAW_HDRi/Dianne_20260521143022_20260521_0001.tif

3.  scan_photoarchive.py
      → extract_to_sidecar.py per new/changed file
      → Dianne_20260521143022_20260521_0001.tif.md  created/updated

4.  load_archive_db.py
      → images + image_tags + tag_history rows upserted

5.  build_stacks_db.py
      → stacks / stack_members rebuilt

6.  propagate_tags.py --apply
      → propagatable tags written to non-HDRi stack members

7.  backup_hdri_jotta.py
      → new files uploaded to Jottacloud
      → file_backups row inserted, sidecar ## Backups updated
```

---

## Current State (2026-05-24)

| Item | Status |
|---|---|
| People | Matthew (001), Dianne (002), Owen (003) |
| Canonical files | ~100 across RAW_HDRi + TIFF_Archive |
| Sidecars | Generated for all scanned files |
| DB loaded | Yes |
| Stacks built | Yes |
| tag_master | Populated from Excel import |
| Propagation | Configured, applied |
| Jottacloud backup | In progress — first batch running |

---

## Dependencies

```
pip install psycopg2-binary openpyxl python-dotenv
```

`media/.env`:
```
PG_DSN=postgres://ttphoto_dev1_app:<password>@192.168.4.10:5432/ttphoto_dev1
```

---

## Adding a New Person

```powershell
# Creates e.g. 004_Susan/ with RAW_HDRi, TIFF_Archive, JPG_Share, JPG_Print, Workfiles
.\New-PhotoArchiveFolders.ps1
```

## DB Migrations

Never run DDL from Windows with the app account — it will fail.  
SCP the `.sql` file to the server, then:

```bash
ssh mpegg-adm@192.168.4.10 "psql -d ttphoto_dev1 -f /tmp/migration.sql"
```
