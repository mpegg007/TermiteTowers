#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 799f8a7f34be32964adec5a869537732c285965e %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 17:21:55 %
#  %ccm_git_file_last_modified: 2026-05-23 17:21:55 %
#  %ccm_git_file_name: load_archive_db.py %
#  %ccm_git_path: media/load_archive_db.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 6917 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
load_archive_db.py

Parse all .md sidecars under PhotoArchive and load into PostgreSQL.
Run after scan_photoarchive.py to keep the DB in sync with sidecar state.

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname

Usage:
    python load_archive_db.py [<archive_root>]
"""

import os
import sys
import re
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

ARCHIVE_ROOT = r"C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"
ENV_FILE     = Path(__file__).parent / ".env"

# ── Connection ────────────────────────────────────────────────────────────────

def load_env(path):
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

# ── Sidecar parsing ───────────────────────────────────────────────────────────

def parse_sidecar(md_path):
    result = {
        "image_hash": None, "file_name": None, "file_type": None,
        "file_date":  None, "file_bytes": None, "scan_name": None,
        "current_tags": {},
        "history":      [],  # (snapshot_ts, change_type, tag_key, tag_value)
    }
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return result

    for field, key in [("ImageHash", "image_hash"), ("FileName", "file_name"),
                       ("OriginalFileType", "file_type"), ("FileDate", "file_date"),
                       ("OriginalScanName", "scan_name")]:
        m = re.search(rf'\*\*{field}\*\*:\s*`?([^`\n]+)`?', content)
        if m:
            result[key] = m.group(1).strip()

    m = re.search(r'\*\*FileBytes\*\*:\s*([\d,]+)', content)
    if m:
        result["file_bytes"] = int(m.group(1).replace(",", ""))

    m = re.search(r'## Current Tag State\n+```text\n(.*?)```', content, re.DOTALL)
    if m:
        for line in m.group(1).strip().splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                result["current_tags"][k.strip()] = v.strip()

    for snap in re.finditer(r'## Tag Snapshot — (.+?)\n+```diff\n(.*?)```', content, re.DOTALL):
        ts = snap.group(1).strip()
        for line in snap.group(2).strip().splitlines():
            if line and line[0] in ("+", "-") and ": " in line:
                change_type = line[0]
                k, _, v = line[1:].strip().partition(": ")
                result["history"].append((ts, change_type, k.strip(), v.strip()))

    return result

# ── Loader ────────────────────────────────────────────────────────────────────

def load_all(conn, archive_root):
    archive_root = Path(archive_root)
    cur = conn.cursor()

    md_files = sorted(
        Path(dirpath) / fname
        for dirpath, _, filenames in os.walk(archive_root)
        for fname in filenames
        if fname.endswith(".md")
    )
    print(f"Found {len(md_files)} sidecar(s)")

    loaded = skipped = errors = 0

    for md_path in md_files:
        image_path = Path(str(md_path)[:-3])
        if not image_path.exists():
            skipped += 1
            continue

        folder = image_path.parent.name
        parts  = image_path.relative_to(archive_root).parts
        owner  = re.sub(r'^\d+_', '', parts[0]) if parts else ""

        data = parse_sidecar(str(md_path))
        if not data["image_hash"]:
            skipped += 1
            continue

        try:
            cur.execute("""
                INSERT INTO images
                    (path, image_hash, file_name, file_type, folder,
                     archive_owner, file_date, file_bytes, scan_name, sidecar_path)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (path) DO UPDATE SET
                    image_hash    = EXCLUDED.image_hash,
                    file_name     = EXCLUDED.file_name,
                    file_type     = EXCLUDED.file_type,
                    folder        = EXCLUDED.folder,
                    archive_owner = EXCLUDED.archive_owner,
                    file_date     = EXCLUDED.file_date,
                    file_bytes    = EXCLUDED.file_bytes,
                    scan_name     = EXCLUDED.scan_name,
                    sidecar_path  = EXCLUDED.sidecar_path,
                    loaded_at     = NOW()
                RETURNING id
            """, (str(image_path), data["image_hash"], data["file_name"],
                  data["file_type"], folder, owner, data["file_date"],
                  data["file_bytes"], data["scan_name"], str(md_path)))
            image_id = cur.fetchone()[0]

            cur.execute("DELETE FROM image_tags WHERE image_id = %s", (image_id,))
            if data["current_tags"]:
                execute_values(cur,
                    "INSERT INTO image_tags (image_id, tag_key, tag_value) VALUES %s",
                    [(image_id, k, v) for k, v in data["current_tags"].items()])

            for ts, change_type, tag_key, tag_value in data["history"]:
                cur.execute("""
                    INSERT INTO tag_history
                        (image_id, snapshot_ts, change_type, tag_key, tag_value)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                """, (image_id, ts, change_type, tag_key, tag_value))

            loaded += 1

        except Exception as e:
            conn.rollback()
            print(f"  ERROR {md_path.name}: {e}")
            errors += 1
            continue

    conn.commit()
    cur.close()
    print(f"Done. Loaded: {loaded}, Skipped: {skipped}, Errors: {errors}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_env(ENV_FILE)
    root = sys.argv[1] if len(sys.argv) > 1 else ARCHIVE_ROOT

    print("Connecting to database...")
    conn = get_conn()

    print(f"Loading sidecars from {root}")
    load_all(conn, root)
    conn.close()

if __name__ == "__main__":
    main()
