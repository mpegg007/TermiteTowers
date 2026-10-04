<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: media/ImageArchive/INGEST_V2_NOTES.md:149 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 50ca447980d112c46f2fe0d6b92f85cf8588f408 %
  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
  %ccm_git_commit_count: 149 %
  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: ita-v1 %
  %ccm_git_modify_date: 2026-06-19 14:49:00 %
  %ccm_git_file_last_modified: 2026-06-16 19:22:47 %
  %ccm_git_file_name: INGEST_V2_NOTES.md %
  %ccm_git_path: media/ImageArchive/INGEST_V2_NOTES.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 7544 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# ingest_folder_dbv2.py — v2 Schema Migration Notes

## Schema field mapping (v1 public → v2)

| v1 column | v2 location | Notes |
|---|---|---|
| `images.image_hash` | `v2.images.image_hash` | Direct — same ImageDataHash |
| `images.file_date` | `v2.images.capture_date` | Direct |
| `images.file_type` | `v2.images.format` | Direct (rename only) |
| `images.path` (dir part) | `v2.file_locations.base_path` | Split from full path |
| `images.file_name` | `v2.file_locations.filename` | Moved to file_locations |
| `images.file_bytes` | `v2.files.file_size` | Moved to files layer |
| `image_locations.path` | `v2.file_locations.base_path` | Consolidated |
| `image_locations.file_name` | `v2.file_locations.filename` | Consolidated |
| `image_locations.folder` | `v2.file_tags` (`Archive:Folder`) | Stored as tag — no column |
| `images.archive_owner` | `v2.file_tags` (`Archive:Owner`) | Stored as tag — no column |
| `images.sidecar_path` | _(dropped)_ | No sidecar concept in v2 |
| `image_tags.tag_key/value` | `v2.image_tags` via `v2.tag_master` | Normalised through tag_master |
| `tag_history.*` | `v2.tag_history` via trigger | Trigger-driven, policy-gated |
| _(new)_ | `v2.files.file_hash` | SHA-256 of raw file bytes |
| _(new)_ | `v2.images.width/height` | Extracted from EXIF |
| _(new)_ | `v2.images.camera_model` | EXIF:Make + EXIF:Model |
| _(new)_ | `v2.images.lens_info` | EXIF:LensModel / Composite:LensID |
| _(new)_ | `v2.images.orientation` | Derived from width vs height |
| _(new)_ | `v2.images.color_space` | EXIF:ColorSpace / ICC_Profile |
| _(new)_ | `v2.images.rating` | XMP:Rating (0-5) |
| _(new)_ | `v2.files.mime_type` | File:MIMEType |
| _(new)_ | `v2.files.bit_depth` | EXIF:BitsPerSample |
| _(new)_ | `v2.files.color_profile` | ICC_Profile:ProfileDescription |

---

## Missing functionality (due to schema changes)

### 1. `archive_owner` and `folder` — no direct columns in v2
`v1.images` stored `archive_owner` and `folder` as plain columns.  
**v2** has no equivalent columns; the script stores them as `Archive:Owner` and `Archive:Folder` file tags in `v2.file_tags`.  
Queries that filter on these values must now join through `v2.tag_master`.

**Recommendation:** If these are first-class query dimensions, add them as proper columns to `v2.files` or `v2.file_locations` and keep the tags as supplementary.

---

### 2. Tag history does not cover INSERT or DELETE
The `v2.fn_audit_tag_change` trigger fires on `AFTER UPDATE` only.  
Initial INSERTs and removals (DELETE) are **not logged** automatically.  
v1 manually inserted `added` / `removed` records into `tag_history`.

**Recommendation:** Add `AFTER INSERT` and `AFTER DELETE` triggers (or extend the existing function with `TG_OP` branching) so the full lifecycle is captured.

---

### 3. Tag history requires `tag_policies` rows to be seeded
The trigger checks `tag_policies.track_history` for each `(tag_id, target_type)` pair.  If no policy row exists, the `SELECT INTO` returns NULL and nothing is recorded.  
A freshly created schema logs **no history at all** until policies are populated.

**Recommendation:** Provide a seed script (or add a `DEFAULT true` fallback path in the trigger function) so history tracking works out of the box.

---

### 4. `v2.file_locations` has no unique constraint on `(file_id, base_path)`
The schema defines only a primary key on `location_id`.  
The script must use a `SELECT … WHERE …` guard before each INSERT to avoid duplicate rows.  Concurrent runs could still produce duplicates.

**Recommendation:** Add `UNIQUE (file_id, base_path)` to `v2.file_locations` so the script can use `ON CONFLICT … DO UPDATE` atomically.

---

### 5. `sidecar_path` dropped
v1 recorded the path of the `.md` sidecar alongside the image.  v2 has no sidecar concept.  Sidecar data (XMP, IPTC notes) must either be stored as tags or handled by a separate table.

---

### 6. `--folder-name` argument not supported
v1 accepted `--folder-name` to override the folder column value.  
v2 derives `Archive:Folder` from `img_path.parent.name` with no override.

**Recommendation:** Add `--folder-name` back as an optional argument.

---

## Required enhancements

### A. `compression_ratio` not computed
`v2.files.compression_ratio NUMERIC(5,2)` is always NULL.  Computing it requires knowing the uncompressed (raw pixel) size, which is not directly available from `stat()`.  
Formula: `round(file_size / (width * height * channels * (bit_depth/8)), 2)`.  
This requires width, height, channel count, and bit depth — all available after exiftool runs, but channel count must be inferred from the colour model.

---

### B. `is_master` flag has no auto-detection
`v2.files.is_master` is always inserted as `false`.  
Heuristics to consider: highest resolution, RAW extension, or the first file seen for an `image_id`.

---

### C. `storage_volume` and `mount_point` not populated
`v2.file_locations.storage_volume` and `mount_point` are always NULL.  
These require detecting the mount point for the file's path (e.g. via `df -P <path>` or `/proc/mounts`).

---

### D. `is_corrupt` detection not implemented
`v2.files.is_corrupt` is always `false`.  
exiftool's stderr output contains corruption warnings (`Warning:`, `Error:`) that could be used to set this flag.

---

## Suggested improvements

### 1. Stack assignment (`--stack`)
Add an optional `--stack <name>` argument.  After ingesting images, look up or create a `v2.stacks` row by name, then insert a `v2.stack_members` row for each image_id processed.  This is the primary new concept in v2 with no v1 equivalent.

### 2. Initialise `v2.file_backups` rows
At the end of ingestion, INSERT a pending backup row in `v2.file_backups` for each new file_id against a configurable destination.  This seeds the backup tracking workflow.

### 3. Tag canonicalization via `canonical_id`
`v2.tag_master.canonical_id` supports aliasing (e.g. `EXIF:CreateDate` → canonical `DateTimeOriginal`).  The script currently stores tags verbatim.  A post-ingest canonicalization step could collapse aliases and normalise tag keys.

### 4. XMP Rating import to `v2.images.rating`
The script maps `XMP:Rating` to the `rating` column (already implemented).  Add `--default-rating <0-5>` as a CLI argument for collections that predate XMP rating tags.

### 5. Parallel ingestion
Wrap the per-file loop in `concurrent.futures.ThreadPoolExecutor` with a configurable `--workers N` argument.  exiftool and SHA-256 hashing are the main bottlenecks; each file can be hashed and exiftool-scanned independently before DB writes are batched.

### 6. exiftool batch mode
Replace per-file `exiftool` subprocess calls with a single invocation over the entire folder:  
```
exiftool -j -a -G1 -r <folder>
```  
This reduces subprocess overhead significantly for large collections.

### 7. Verification / re-sync mode
Add `--verify` to walk existing `v2.file_locations` rows, check `is_online`, update `last_verified_at`, and flag missing files as `is_online = false`.

### 8. `--volume` / `--mount` arguments
Allow the caller to pass `--volume <label>` and `--mount <path>` to populate `v2.file_locations.storage_volume` and `mount_point` explicitly (useful for removable media).

### 9. Migration utility (v1 → v2)
A separate `migrate_v1_to_v2.py` script that reads from the `public` schema and writes to `v2`, preserving tag history (`change_type`, `snapshot_ts`) by re-inserting into `v2.tag_history` manually (bypassing the trigger which only responds to live UPDATEs).
