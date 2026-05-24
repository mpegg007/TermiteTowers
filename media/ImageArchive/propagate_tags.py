#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 1d03aecda227674166acd9c1d56b3e603277de75 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-24 13:04:29 %
#  %ccm_git_file_last_modified: 2026-05-24 13:04:29 %
#  %ccm_git_file_name: propagate_tags.py %
#  %ccm_git_path: media/ImageArchive/propagate_tags.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 6831 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
"""
propagate_tags.py

For each image stack, find the authoritative value for each propagatable tag
(most recently-dated source member), then write it to all non-HDRi stack
members that are missing or have a different value.

After writing, runs extract_to_sidecar.py on changed files to update .md sidecars.

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname

Usage:
    python propagate_tags.py [--apply] [--stack <id>]

    --apply       Write tags to image files (default: dry-run, print only)
    --stack N     Process only stack with id N

To add propagatable tags:
    INSERT INTO propagatable_tags (tag_key, tag_group, notes)
    VALUES ('EXIF:GPSLatitude', 'geo', NULL);
"""

import os
import sys
import subprocess
from pathlib import Path
import psycopg2

ENV_FILE       = Path(__file__).parent.parent / ".env"
SIDECAR_SCRIPT = Path(__file__).parent / "extract_to_sidecar.py"
EXIFTOOL       = os.environ.get("EXIFTOOL", r"C:\Apps\exiftool-13.58_64\exiftool.exe")

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

# ── Propagation logic ─────────────────────────────────────────────────────────

def write_tags(image_path, tags, apply):
    """Write {tag_key: value} to image via exiftool. Returns True on success."""
    if not tags:
        return False
    args = [EXIFTOOL, "-overwrite_original"]
    for key, val in tags.items():
        args.append(f"-{key}={val}")
    args.append(image_path)
    if not apply:
        return True  # dry-run always succeeds
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        print(f"    exiftool error: {result.stderr.decode('utf-8','replace').strip()}")
    return result.returncode == 0

def update_sidecar(image_path):
    subprocess.run([sys.executable, str(SIDECAR_SCRIPT), image_path],
                   capture_output=True)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    apply        = "--apply" in sys.argv
    stack_filter = None
    if "--stack" in sys.argv:
        idx = sys.argv.index("--stack")
        try:
            stack_filter = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("ERROR: --stack requires an integer id")
            sys.exit(1)

    mode_label = "[APPLY]" if apply else "[DRY  ]"
    if not apply:
        print("DRY RUN — pass --apply to actually write tags\n")

    load_env(ENV_FILE)
    conn = get_conn()
    cur  = conn.cursor()

    # Check propagatable tags
    cur.execute("SELECT tag_key FROM tag_master WHERE propagatable = TRUE ORDER BY tag_key")
    prop_rows = cur.fetchall()
    if not prop_rows:
        print("No propagatable tags defined.")
        print("Add rows to tag_master, e.g.:")
        print("  INSERT INTO tag_master (tag_key, propagatable)")
        print("  VALUES ('IFD0:Artist', true), ('IFD0:Copyright', true);")
        sys.exit(0)
    print(f"Propagatable tags: {', '.join(r[0] for r in prop_rows)}\n")

    # Get stacks
    if stack_filter:
        cur.execute("SELECT id FROM stacks WHERE id = %s", (stack_filter,))
    else:
        cur.execute("SELECT id FROM stacks ORDER BY id")
    stack_ids = [row[0] for row in cur.fetchall()]

    total_files_changed = 0
    total_tags_written  = 0

    for sid in stack_ids:
        # Authority: best value per canonical tag across the whole stack
        cur.execute("""
            SELECT tag_key, tag_value, source_tag_key, source_path
            FROM stack_tag_authority
            WHERE stack_id = %s
        """, (sid,))
        authority = {row[0]: (row[1], row[2], row[3]) for row in cur.fetchall()}
        if not authority:
            continue

        # Members with their current tags
        cur.execute("""
            SELECT i.id, i.path, i.file_type,
                   COALESCE(json_object_agg(it.tag_key, it.tag_value)
                             FILTER (WHERE it.tag_key IS NOT NULL), '{}')
            FROM stack_members sm
            JOIN images i ON i.id = sm.image_id
            LEFT JOIN image_tags it ON it.image_id = i.id
            WHERE sm.stack_id = %s
            GROUP BY i.id, i.path, i.file_type
        """, (sid,))
        members = cur.fetchall()

        stack_changed = False
        for image_id, path, file_type, current_tags in members:
            if not os.path.exists(path):
                continue
            if file_type and "HDRi" in file_type:
                continue  # never touch HDRi masters

            to_write = {}
            for tag_key, (auth_val, source_tag_key, source_path) in authority.items():
                if path == source_path:
                    continue  # this IS the source
                current_val = (current_tags or {}).get(tag_key, "")
                if current_val != auth_val:
                    to_write[tag_key] = auth_val
                    print(f"  {mode_label} {os.path.basename(path)}")
                    print(f"    {tag_key}: {current_val!r} → {auth_val!r}")
                    alias_note = f" (via alias {source_tag_key})" if source_tag_key != tag_key else ""
                    print(f"    (from {os.path.basename(source_path)}{alias_note})")

            if to_write:
                success = write_tags(path, to_write, apply)
                if success:
                    total_tags_written += len(to_write)
                    stack_changed = True
                    if apply:
                        update_sidecar(path)
                        print(f"    \u2192 sidecar updated")

        if stack_changed:
            total_files_changed += 1
            print()

    summary = "Applied" if apply else "Would apply"
    print(f"{summary}: {total_tags_written} tag write(s) across {total_files_changed} file(s)")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
