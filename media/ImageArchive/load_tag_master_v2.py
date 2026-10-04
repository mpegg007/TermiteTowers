#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/load_tag_master_v2.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0ca729ed1eeb88e2e729f391b1b13fb992420913 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-16 20:46:59 %
#  %ccm_git_file_name: load_tag_master_v2.py %
#  %ccm_git_path: media/ImageArchive/load_tag_master_v2.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 7241 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
load_tag_master_v2.py

Read media/tag_master_v2_import.xlsx and upsert rows into v2.tag_master
and v2.tag_policies.

v2 schema differences:
  - tag_master has (tag_id, tag_key, canonical_id, description).
    There is NO propagatable / include_in_report / notes column.
  - canonical_id is a FK to tag_master.tag_id.  The Excel uses a human-readable
    canonical_key (text); this script resolves it to a tag_id.
  - Behavioural flags (track_history, write_to_exif) are stored in tag_policies,
    one row per (tag_id, target_type) pair.

Load order:
  Pass 1 — insert all canonical tags (canonical_key blank) into tag_master.
  Pass 2 — insert alias tags, setting canonical_id.
  Pass 3 — upsert tag_policies rows (track_history / write_to_exif / target_type).

Rows where track_history=N AND write_to_exif=N AND canonical_key is blank are
still loaded into tag_master (they need to exist for FK integrity), but a
tag_policies row is written with both flags=false so triggers skip them.

Usage:
    python load_tag_master_v2.py [--dry-run]
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
import openpyxl

load_dotenv(Path(__file__).parent.parent / ".env")
DSN  = os.environ["PG_DSN"]
XLSX = Path(__file__).parent / "tag_master_v2_import.xlsx"

DRY_RUN = "--dry-run" in sys.argv

VALID_TARGET_TYPES = {"image", "file", "stack", "location"}


def read_rows() -> list[dict]:
    if not XLSX.exists():
        print(f"ERROR: {XLSX} not found.  Run generate_tag_master_excel_v2.py first.")
        sys.exit(1)

    wb = openpyxl.load_workbook(str(XLSX), read_only=True, data_only=True)
    ws = wb["tag_master"]

    rows: list[dict] = []
    headers = None
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = [str(c).strip() if c else "" for c in r]
            continue

        row = dict(zip(headers, r))

        tag_key       = (row.get("tag_key")       or "").strip()
        canonical_key = (row.get("canonical_key") or "").strip() or None
        description   = (row.get("description")   or "").strip() or None
        track_history = (row.get("track_history") or "N").strip().upper() == "Y"
        write_to_exif = (row.get("write_to_exif") or "N").strip().upper() == "Y"
        target_type   = (row.get("target_type")   or "image").strip().lower()

        if not tag_key:
            continue
        if target_type not in VALID_TARGET_TYPES:
            print(f"WARNING: Unknown target_type '{target_type}' for {tag_key!r}, defaulting to 'image'")
            target_type = "image"

        rows.append(dict(
            tag_key=tag_key,
            canonical_key=canonical_key,
            description=description,
            track_history=track_history,
            write_to_exif=write_to_exif,
            target_type=target_type,
        ))

    wb.close()
    return rows


# ── SQL ───────────────────────────────────────────────────────────────────────

TAG_MASTER_CANONICAL_SQL = """
INSERT INTO v2.tag_master (tag_key, description)
VALUES (%(tag_key)s, %(description)s)
ON CONFLICT (tag_key) DO UPDATE
    SET description = COALESCE(EXCLUDED.description, v2.tag_master.description)
RETURNING tag_id
"""

TAG_MASTER_ALIAS_SQL = """
UPDATE v2.tag_master
SET canonical_id = (SELECT tag_id FROM v2.tag_master WHERE tag_key = %(canonical_key)s),
    description  = COALESCE(%(description)s, description)
WHERE tag_key = %(tag_key)s
"""

TAG_POLICY_SQL = """
INSERT INTO v2.tag_policies (tag_id, target_type, track_history, write_to_exif)
VALUES (%(tag_id)s, %(target_type)s, %(track_history)s, %(write_to_exif)s)
ON CONFLICT (tag_id, target_type) DO UPDATE
    SET track_history = EXCLUDED.track_history,
        write_to_exif = EXCLUDED.write_to_exif
"""


def main():
    rows       = read_rows()
    canonicals = [r for r in rows if r["canonical_key"] is None]
    aliases    = [r for r in rows if r["canonical_key"] is not None]

    print(f"Rows: {len(canonicals)} canonical  {len(aliases)} aliases  ({len(rows)} total)")

    if DRY_RUN:
        print("-- DRY RUN: no changes written --")
        for r in rows:
            print(
                f"  {r['tag_key']:60s}"
                f"  track={'Y' if r['track_history'] else 'N'}"
                f"  exif={'Y' if r['write_to_exif'] else 'N'}"
                f"  target={r['target_type']}"
                f"  canon={r['canonical_key'] or ''}"
            )
        return

    conn = psycopg2.connect(DSN)
    cur  = conn.cursor()

    # ── Pass 1: canonical tags → get/create tag_id ────────────────────────────
    tag_id_map: dict[str, int] = {}

    for r in canonicals:
        cur.execute(TAG_MASTER_CANONICAL_SQL, r)
        row = cur.fetchone()
        tag_id_map[r["tag_key"]] = row[0]

    # ── Pass 2: alias tags — must already exist or be in canonicals ───────────
    for r in aliases:
        # Ensure the alias row exists in tag_master first
        cur.execute(
            "INSERT INTO v2.tag_master (tag_key, description)"
            " VALUES (%(tag_key)s, %(description)s)"
            " ON CONFLICT (tag_key) DO UPDATE"
            " SET description = COALESCE(EXCLUDED.description, v2.tag_master.description)"
            " RETURNING tag_id",
            r,
        )
        tag_id_map[r["tag_key"]] = cur.fetchone()[0]

    # Flush so all tag_master rows exist before resolving canonical_ids
    conn.commit()

    for r in aliases:
        # Check the canonical target exists
        cur.execute(
            "SELECT tag_id FROM v2.tag_master WHERE tag_key = %s",
            (r["canonical_key"],),
        )
        canon_row = cur.fetchone()
        if canon_row is None:
            print(f"WARNING: canonical_key {r['canonical_key']!r} not found for {r['tag_key']!r} — skipping alias link")
        else:
            cur.execute(TAG_MASTER_ALIAS_SQL, r)

    conn.commit()

    # ── Pass 3: tag_policies ──────────────────────────────────────────────────
    # Reload full tag_id_map from DB to catch any pre-existing tags
    cur.execute("SELECT tag_key, tag_id FROM v2.tag_master")
    for key, tid in cur.fetchall():
        tag_id_map[key] = tid

    policy_count = 0
    for r in rows:
        tid = tag_id_map.get(r["tag_key"])
        if tid is None:
            print(f"WARNING: tag_id not found for {r['tag_key']!r} — skipping policy")
            continue
        cur.execute(TAG_POLICY_SQL, {
            "tag_id":       tid,
            "target_type":  r["target_type"],
            "track_history": r["track_history"],
            "write_to_exif": r["write_to_exif"],
        })
        policy_count += 1

    conn.commit()
    conn.close()

    print(
        f"Done.  {len(canonicals)} canonical + {len(aliases)} alias"
        f" tag_master rows upserted.  {policy_count} tag_policies rows upserted."
    )


if __name__ == "__main__":
    main()
