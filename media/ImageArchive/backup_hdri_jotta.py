#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: fca589bf18f9eaedf4c2007a9cbe86a8f36c5c87 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-24 13:04:12 %
#  %ccm_git_file_last_modified: 2026-05-24 13:04:12 %
#  %ccm_git_file_name: backup_hdri_jotta.py %
#  %ccm_git_path: media/ImageArchive/backup_hdri_jotta.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 11211 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
backup_hdri_jotta.py

Back up RAW_HDRi and TIFF_Archive image files to Jottacloud using jotta-cli.
Only files with canonical names (Owner_14digits_rest) are processed.
Upload status is tracked in the file_backups DB table and each image's .md sidecar.

Usage:
    python backup_hdri_jotta.py [--dry-run] [--force] [--owner NAME] [--limit N]

    --dry-run     Print eligible files and remote paths; do not upload
    --force       Re-upload files already marked as success in file_backups
    --owner NAME  Restrict to one archive owner token (e.g., Matthew)
    --limit N     Cap uploads at N files (useful for first test run)

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname
"""

import os
import re
import sys
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

ARCHIVE_ROOT   = r"C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"
ENV_FILE       = Path(__file__).parent.parent / ".env"
JOTTA_CLI      = r"C:\Program Files\Jottacloud\Update\Data\Current\jotta-cli.exe"
DESTINATION    = "jottacloud"

# Top-level folder name used as the remote root inside the Jottacloud device.
# If jotta-cli expects a device prefix, adjust to e.g. "Bosgame/PhotoArchive".
# Verify with:  jotta-cli.exe ls
REMOTE_ROOT    = "PhotoArchive"

TARGET_FOLDERS = ("RAW_HDRi", "TIFF_Archive")
CANONICAL_RE   = re.compile(r"^[A-Za-z]+_\d{14}_")

# ── Environment / connection ───────────────────────────────────────────────────

def check_schema(conn):
    """Verify file_backups table exists (DDL must be run on the server as owner)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'file_backups'
            )
        """)
        if not cur.fetchone()[0]:
            print("ERROR: file_backups table does not exist.")
            print("SSH to the monolith and run:")
            print("  psql -d ttphoto_dev1 -f add_file_backups.sql")
            sys.exit(1)


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


# ── Candidate selection ────────────────────────────────────────────────────────

def query_candidates(cur, force, owner_filter):
    """Return rows eligible for backup as list of tuples:
       (id, path, file_name, folder, image_hash, sidecar_path)
    """
    sql = """
        SELECT i.id, i.path, i.file_name, i.folder, i.image_hash, i.sidecar_path
        FROM   images i
        LEFT JOIN file_backups fb
               ON fb.image_id = i.id AND fb.destination = %s
        WHERE  i.folder  = ANY(%s)
          AND  i.file_name ~ %s
    """
    params = [DESTINATION, list(TARGET_FOLDERS), r"^[A-Za-z]+_\d{14}_"]

    if not force:
        sql += " AND (fb.status IS NULL OR fb.status != 'success')"

    if owner_filter:
        sql += " AND i.archive_owner ILIKE %s"
        params.append(owner_filter)

    sql += " ORDER BY i.folder, i.file_name"
    cur.execute(sql, params)
    return cur.fetchall()


# ── Remote path ────────────────────────────────────────────────────────────────

def build_remote_path(local_path):
    """Mirror the archive folder structure under REMOTE_ROOT."""
    try:
        rel = Path(local_path).relative_to(ARCHIVE_ROOT)
    except ValueError:
        rel = Path(local_path).name
    return f"{REMOTE_ROOT}/{str(rel).replace(os.sep, '/')}"


# ── Upload ─────────────────────────────────────────────────────────────────────

def jotta_upload(local_path, remote_path):
    """Call jotta-cli.exe archive. Returns (success: bool, error_msg: str)."""
    cmd = [JOTTA_CLI, "archive", local_path, f"--remote={remote_path}", "--nogui"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode == 0:
            return True, ""
        err = (result.stderr.decode("utf-8", errors="replace").strip()
               or result.stdout.decode("utf-8", errors="replace").strip())
        return False, err
    except FileNotFoundError:
        return False, f"jotta-cli not found at: {JOTTA_CLI}"
    except subprocess.TimeoutExpired:
        return False, "Upload timed out after 600s"


# ── DB record ──────────────────────────────────────────────────────────────────

def record_backup(cur, image_id, remote_path, backed_up_at, status, image_hash, error_msg):
    cur.execute("""
        INSERT INTO file_backups
            (image_id, destination, remote_path, backed_up_at, status, image_hash, error_msg)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (image_id, destination) DO UPDATE SET
            remote_path  = EXCLUDED.remote_path,
            backed_up_at = EXCLUDED.backed_up_at,
            status       = EXCLUDED.status,
            image_hash   = EXCLUDED.image_hash,
            error_msg    = EXCLUDED.error_msg
    """, (image_id, DESTINATION, remote_path, backed_up_at,
          status, image_hash, error_msg or None))


# ── Sidecar update ─────────────────────────────────────────────────────────────

def update_sidecar(sidecar_path, destination, remote_path, backed_up_at, status):
    """Add/replace the ## Backups section in the .md sidecar. Best-effort."""
    if not sidecar_path or not os.path.exists(sidecar_path):
        return
    try:
        with open(sidecar_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return

    # Parse any existing backup rows: destination → (remote_path, backed_up_at, status)
    backups = {}
    m = re.search(
        r"^## Backups\s*\n\|[^\n]+\|\n\|[-| ]+\|\n((?:\|[^\n]+\|\n)*)",
        content, re.MULTILINE,
    )
    if m:
        for row in re.finditer(
            r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
            m.group(1), re.MULTILINE,
        ):
            backups[row.group(1)] = (row.group(2), row.group(3), row.group(4))

    backups[destination] = (remote_path, backed_up_at, status)

    section = [
        "\n## Backups\n",
        "| Destination | Remote Path | Backed Up           | Status  |",
        "|-------------|-------------|---------------------|---------|",
    ]
    for dest in sorted(backups):
        rp, bat, st = backups[dest]
        section.append(f"| {dest:<11} | {rp} | {bat:<19} | {st:<7} |")
    section.append("")

    # Strip existing ## Backups section (to end of file) and append fresh
    stripped = re.sub(r"\n## Backups\b.*", "", content, flags=re.DOTALL).rstrip()
    new_content = stripped + "\n" + "\n".join(section)

    try:
        with open(sidecar_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        print(f"    [warn] sidecar write failed: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Back up RAW_HDRi and TIFF_Archive files to Jottacloud."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print candidates only; do not upload")
    parser.add_argument("--force", action="store_true",
                        help="Re-upload files already marked as success")
    parser.add_argument("--owner", metavar="NAME",
                        help="Restrict to one archive owner (e.g., Matthew)")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="Cap uploads at N files")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — pass without --dry-run to upload\n")

    load_env(ENV_FILE)
    conn = get_conn()
    check_schema(conn)
    cur  = conn.cursor()

    rows = query_candidates(cur, args.force, args.owner)

    total     = len(rows)
    processed = 0
    succeeded = 0
    failed    = 0
    missing   = 0

    owner_note = f"  (owner={args.owner})" if args.owner else ""
    limit_note = f"  limit={args.limit}" if args.limit else ""
    print(f"Eligible: {total}{owner_note}{limit_note}\n")

    for image_id, local_path, file_name, folder, image_hash, sidecar_path in rows:
        if args.limit and processed >= args.limit:
            break

        remote_path = build_remote_path(local_path)
        label       = f"[{folder:<14}]  {file_name}"

        if not os.path.exists(local_path):
            print(f"  MISSING    {label}")
            missing  += 1
            processed += 1
            continue

        if args.dry_run:
            print(f"  would upload  {label}")
            print(f"                → {remote_path}")
            processed += 1
            continue

        print(f"  uploading  {label}")
        print(f"             → {remote_path}")

        now_ts  = datetime.now(timezone.utc)
        success, error_msg = jotta_upload(local_path, remote_path)
        status  = "success" if success else "failed"
        ts_str  = now_ts.strftime("%Y-%m-%d %H:%M:%S")

        record_backup(cur, image_id, remote_path, now_ts, status, image_hash, error_msg)
        conn.commit()

        if success:
            update_sidecar(sidecar_path, DESTINATION, remote_path, ts_str, status)
            print(f"             \u2713 done")
            succeeded += 1
        else:
            print(f"             \u2717 {error_msg}")
            failed += 1

        processed += 1

    print()
    if args.dry_run:
        print(f"Would upload: {processed}  missing on disk: {missing}  total eligible: {total}")
    else:
        print(f"Uploaded: {succeeded}  failed: {failed}  "
              f"missing on disk: {missing}  processed: {processed}/{total}")
        if total > processed:
            print(f"  ({total - processed} not processed — limit reached)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
