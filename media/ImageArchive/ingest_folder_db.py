#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/ingest_folder_db.py:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 36d682bf9dd57f97f6e80ee8cdef6e39a270e2d5 %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
#  %ccm_git_file_name: ingest_folder_db.py %
#  %ccm_git_path: media/ImageArchive/ingest_folder_db.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 16786 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  track duplicate image locations, scrape from all files  % 
"""
ingest_folder_db.py

Walk a folder (recursively) and load every image directly into PostgreSQL —
no .md sidecar is created or required.  Designed for digital camera photos
where the SilverFast sidecar workflow doesn't apply.

Identity is the image hash.  If a file with the same hash is already in the
DB the canonical image record is reused, but tags are still diffed/merged and
the file's path + filename are recorded in image_locations so that meaningful
names (e.g. '660401_houseboat.tif') are never lost.

Usage:
    python ingest_folder_db.py <folder> --owner <Name>
    python ingest_folder_db.py <folder> --owner Matthew --folder RAW_HDRi
    python ingest_folder_db.py <folder> --owner Dianne --dry-run
    python ingest_folder_db.py <folder> --owner Owen --force   # re-process known hashes
    python ingest_folder_db.py <folder> --owner Matthew --limit 10

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname
"""

import argparse
import os
import re
import sys
from pathlib import Path
from datetime import datetime

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
import subprocess
import json

# ── Config ─────────────────────────────────────────────────────────────────────

EXIFTOOL = r"C:\Apps\exiftool-13.58_64\exiftool.exe"
EXIFTOOL = r"/home/mpegg-adm/apps/exiftool/exiftool"
ENV_FILE  = Path(__file__).parent.parent / ".env"

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png",
    ".tif", ".tiff",
    ".cr2", ".cr3",
    ".nef", ".nrw",
    ".arw", ".srf", ".sr2",
    ".orf",
    ".raf",
    ".rw2",
    ".dng",
    ".heic", ".heif",
}

# Tags that are never useful to store
SKIP_TAG_PATTERNS = re.compile(
    r"SourceFile|ThumbnailImage|PreviewImage|JpgFromRaw|OtherImage"
    r"|MakerNotes|PrintIM|FlashPix"
    r"|CanonCameraInfo|NikonCapture|PentaxModelID",
    re.IGNORECASE,
)

# ── Env / connection ────────────────────────────────────────────────────────────

def load_env(path: Path):
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def get_conn():
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        print("ERROR: PG_DSN not set. Add PG_DSN=postgres://... to media/.env")
        sys.exit(1)
    return psycopg2.connect(dsn)


# ── exiftool helpers ────────────────────────────────────────────────────────────

def run_et(*args):
    cmd = [EXIFTOOL] + list(args)
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    return r.stdout


def get_image_hash(filepath: str) -> str:
    raw = run_et("-ImageDataHash", "-s3", filepath)
    return raw.decode("utf-8", errors="replace").strip()


def get_all_tags(filepath: str) -> dict:
    raw = run_et("-j", "-a", "-G1", filepath)
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return data[0] if data else {}
    except (json.JSONDecodeError, IndexError):
        return {}


# ── Tag helpers ─────────────────────────────────────────────────────────────────

def flatten_tag_value(val) -> str:
    if isinstance(val, list):
        return "; ".join(str(v) for v in val)
    return str(val)


def should_skip_tag(key: str, val_str: str) -> bool:
    if SKIP_TAG_PATTERNS.search(key):
        return True
    if val_str.startswith("(Binary data"):
        return True
    return False


def build_tag_rows(all_tags: dict) -> dict[str, str]:
    """Return {tag_key: tag_value} for all storable tags."""
    rows = {}
    for key, val in all_tags.items():
        if key == "SourceFile":
            continue
        val_str = flatten_tag_value(val)
        if should_skip_tag(key, val_str):
            continue
        rows[key] = val_str
    return rows


# ── Metadata extraction ─────────────────────────────────────────────────────────

def get_file_type(all_tags: dict, filepath: str) -> str:
    """Use exiftool FileType tag, fall back to extension."""
    ft = all_tags.get("File:FileType") or all_tags.get("FileType")
    if ft:
        return str(ft).upper()
    return Path(filepath).suffix.lstrip(".").upper()


def get_file_date(all_tags: dict, filepath: str) -> str:
    """
    Return a date string we can store.  Preference order:
      EXIF DateTimeOriginal → CreateDate → FileModifyDate → file mtime
    Normalise EXIF colons: '2026:05:21 14:30:22' → '2026-05-21 14:30:22'
    """
    for key in (
        "EXIF:DateTimeOriginal", "ExifIFD:DateTimeOriginal",
        "EXIF:CreateDate", "ExifIFD:CreateDate",
        "XMP:CreateDate",
        "File:FileModifyDate",
    ):
        val = all_tags.get(key)
        if val:
            s = str(val)
            # Normalise '2026:05:21 14:30:22[-04:00]'
            s = re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', s)
            return s
    # Last resort: filesystem mtime
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


def normalize_date_for_pg(date_str: str) -> str:
    """Strip timezone suffix that PostgreSQL rejects for TIMESTAMP (non-TZ) columns."""
    # Keep as-is; the DB column is TIMESTAMPTZ so any ISO 8601 form is fine.
    return date_str


# ── DB operations ───────────────────────────────────────────────────────────────

def check_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT to_regclass('public.images'),
                   to_regclass('public.image_tags'),
                   to_regclass('public.tag_history'),
                   to_regclass('public.image_locations')
        """)
        row = cur.fetchone()
    missing = [name for name, exists in zip(
        ("images", "image_tags", "tag_history", "image_locations"), row
    ) if exists is None]
    if missing:
        print(f"ERROR: Missing tables: {', '.join(missing)}")
        if "image_locations" in missing:
            print("  -> Run: scp add_image_locations.sql server:/tmp/ then psql -d ttphoto_dev1 -f /tmp/add_image_locations.sql")
        else:
            print("  -> Run init_schema.sh on the server first.")
        sys.exit(1)


def find_image_id_by_hash(cur, image_hash: str) -> int | None:
    """Return the image_id for a known hash, or None if not yet in DB."""
    cur.execute("SELECT id FROM images WHERE image_hash = %s LIMIT 1", (image_hash,))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_location(cur, image_id: int, path: str, file_name: str, folder: str | None):
    """Record (or refresh) a path where this image hash was found."""
    cur.execute("""
        INSERT INTO image_locations (image_id, path, file_name, folder)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (image_id, path) DO UPDATE SET
            file_name = EXCLUDED.file_name,
            folder    = EXCLUDED.folder,
            found_at  = NOW()
    """, (image_id, path, file_name, folder))


def upsert_image(cur, *, path, image_hash, file_name, file_type,
                 folder, archive_owner, file_date, file_bytes) -> int:
    cur.execute("""
        INSERT INTO images
            (path, image_hash, file_name, file_type, folder,
             archive_owner, file_date, file_bytes, sidecar_path)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NULL)
        ON CONFLICT (path) DO UPDATE SET
            image_hash    = EXCLUDED.image_hash,
            file_name     = EXCLUDED.file_name,
            file_type     = EXCLUDED.file_type,
            folder        = EXCLUDED.folder,
            archive_owner = EXCLUDED.archive_owner,
            file_date     = EXCLUDED.file_date,
            file_bytes    = EXCLUDED.file_bytes,
            loaded_at     = NOW()
        RETURNING id
    """, (path, image_hash, file_name, file_type, folder,
          archive_owner, file_date, file_bytes))
    return cur.fetchone()[0]


def sync_tags(cur, image_id: int, new_tags: dict, file_date: str,
              file_modify_ts: str | None = None):
    """Diff image_tags vs new_tags; record history for adds/changes/removals.

    snapshot_ts  = file_date  (capture date: DateTimeOriginal / CreateDate)
    recorded_at  = file_modify_ts (File:FileModifyDate — best proxy for when
                   tags were last written to disk; None for old rows)
    """
    cur.execute(
        "SELECT tag_key, tag_value FROM image_tags WHERE image_id = %s",
        (image_id,)
    )
    old_tags = {r[0]: r[1] for r in cur.fetchall()}

    added   = {k: v for k, v in new_tags.items() if k not in old_tags}
    changed = {k: v for k, v in new_tags.items()
               if k in old_tags and old_tags[k] != v}
    removed = {k for k in old_tags if k not in new_tags}

    ts  = normalize_date_for_pg(file_date)
    rts = normalize_date_for_pg(file_modify_ts) if file_modify_ts else None

    if added:
        execute_values(cur,
            "INSERT INTO image_tags (image_id, tag_key, tag_value, changed_at)"
            " VALUES %s ON CONFLICT DO NOTHING",
            [(image_id, k, v, ts) for k, v in added.items()])
        execute_values(cur,
            "INSERT INTO tag_history"
            " (image_id, snapshot_ts, change_type, tag_key, tag_value, recorded_at)"
            " VALUES %s ON CONFLICT DO NOTHING",
            [(image_id, ts, "added", k, v, rts) for k, v in added.items()])

    for k, v in changed.items():
        cur.execute(
            "UPDATE image_tags SET tag_value = %s, changed_at = %s"
            " WHERE image_id = %s AND tag_key = %s",
            (v, ts, image_id, k))
        cur.execute(
            "INSERT INTO tag_history"
            " (image_id, snapshot_ts, change_type, tag_key, tag_value, recorded_at)"
            " VALUES (%s,%s,'changed_from',%s,%s,%s) ON CONFLICT DO NOTHING",
            (image_id, ts, k, old_tags[k], rts))
        cur.execute(
            "INSERT INTO tag_history"
            " (image_id, snapshot_ts, change_type, tag_key, tag_value, recorded_at)"
            " VALUES (%s,%s,'changed_to',%s,%s,%s) ON CONFLICT DO NOTHING",
            (image_id, ts, k, v, rts))

    for k in removed:
        cur.execute(
            "DELETE FROM image_tags WHERE image_id = %s AND tag_key = %s",
            (image_id, k))
        cur.execute(
            "INSERT INTO tag_history"
            " (image_id, snapshot_ts, change_type, tag_key, tag_value, recorded_at)"
            " VALUES (%s,%s,'removed',%s,%s,%s) ON CONFLICT DO NOTHING",
            (image_id, ts, k, old_tags[k], rts))

    return len(added), len(changed), len(removed)


# ── File collection ─────────────────────────────────────────────────────────────

def collect_images(folder: Path) -> list[Path]:
    result = []
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if Path(fname).suffix.lower() in IMAGE_EXTS:
                result.append(Path(dirpath) / fname)
    return sorted(result)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest a folder of images into the DB (no sidecar).")
    parser.add_argument("folder", help="Folder to walk (recursively)")
    parser.add_argument("--owner", required=True, help="archive_owner value (e.g. Matthew)")
    parser.add_argument("--folder-name", default=None,
                        help="folder column value; defaults to the immediate parent directory name of each file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done but make no DB changes")
    parser.add_argument("--force", action="store_true",
                        help="Re-process files whose hash is already in the DB")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N files (0 = no limit)")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        sys.exit(1)

    load_env(ENV_FILE)

    if args.dry_run:
        print("[DRY RUN] No changes will be written.\n")

    conn = get_conn()
    check_schema(conn)

    images = collect_images(folder)
    print(f"Found {len(images)} image(s) in {folder}\n")

    processed = skipped = errors = 0
    cur = conn.cursor()

    for img_path in images:
        if args.limit and processed >= args.limit:
            print(f"\nLimit of {args.limit} reached.")
            break

        rel = img_path.relative_to(folder) if img_path.is_relative_to(folder) else img_path
        print(f"  {rel} ", end="", flush=True)

        try:
            image_hash = get_image_hash(str(img_path))
            if not image_hash:
                print("✗ hash failed")
                errors += 1
                continue

            all_tags      = get_all_tags(str(img_path))
            tag_rows      = build_tag_rows(all_tags)
            file_type     = get_file_type(all_tags, str(img_path))
            file_date     = get_file_date(all_tags, str(img_path))
            file_modify_ts = all_tags.get("File:FileModifyDate") or all_tags.get("FileModifyDate")
            file_bytes    = img_path.stat().st_size
            file_name     = img_path.name
            folder_col    = args.folder_name or img_path.parent.name

            if args.dry_run:
                existing_id = find_image_id_by_hash(cur, image_hash)
                label = "(known hash) " if existing_id else ""
                print(f"{label}→ {file_type}  {len(tag_rows)} tags  {file_bytes:,}B  {file_date}")
                processed += 1
                continue

            existing_id = find_image_id_by_hash(cur, image_hash)

            if existing_id and not args.force:
                # Known hash: merge tags and record this location
                added, changed, removed = sync_tags(
                    cur, existing_id, tag_rows, file_date, file_modify_ts)
                upsert_location(cur, existing_id, str(img_path), file_name, folder_col)
                conn.commit()

                tag_parts = []
                if added:   tag_parts.append(f"+{added}")
                if changed: tag_parts.append(f"~{changed}")
                if removed: tag_parts.append(f"-{removed}")
                tag_summary = ' '.join(tag_parts) or 'no change'
                print(f"(known hash) tags: {tag_summary}  loc: recorded")
                skipped += 1
                continue

            image_id = upsert_image(
                cur,
                path=str(img_path),
                image_hash=image_hash,
                file_name=file_name,
                file_type=file_type,
                folder=folder_col,
                archive_owner=args.owner,
                file_date=file_date,
                file_bytes=file_bytes,
            )
            added, changed, removed = sync_tags(
                cur, image_id, tag_rows, file_date, file_modify_ts)
            upsert_location(cur, image_id, str(img_path), file_name, folder_col)
            conn.commit()

            parts = []
            if added:   parts.append(f"+{added}")
            if changed: parts.append(f"~{changed}")
            if removed: parts.append(f"-{removed}")
            print(f"✓  tags: {' '.join(parts) or 'no change'}")
            processed += 1

        except Exception as exc:
            conn.rollback()
            print(f"✗ {exc}")
            errors += 1

    cur.close()
    conn.close()

    print(f"\nDone.  new={processed}  known_hash_merged={skipped}  errors={errors}")


if __name__ == "__main__":
    main()
