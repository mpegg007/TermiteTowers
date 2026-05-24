#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/load_tag_master.py:145 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d099e65a4bbc2b8df28912f8c430a3d1100a73b7 %
#  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
#  %ccm_git_commit_count: 145 %
#  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: adding readme %
#  %ccm_git_modify_date: 2026-05-24 15:15:19 %
#  %ccm_git_file_last_modified: 2026-05-24 15:15:19 %
#  %ccm_git_file_name: load_tag_master.py %
#  %ccm_git_path: media/ImageArchive/load_tag_master.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 3315 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % 
"""
load_tag_master.py

Read media/tag_master_import.xlsx and INSERT rows into tag_master.

Only rows where include_in_report=Y or propagatable=Y are loaded
(red / excluded rows are skipped — they add no value to the table).

Two-pass insert: canonical rows first (no canonical_key), then aliases,
so the FK constraint is satisfied.

Usage:
    python media/load_tag_master.py [--dry-run]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import openpyxl

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.environ["PG_DSN"]
XLSX = Path(__file__).parent / "tag_master_import.xlsx"

DRY_RUN = "--dry-run" in sys.argv


def read_rows():
    wb = openpyxl.load_workbook(str(XLSX), read_only=True, data_only=True)
    ws = wb["tag_master"]
    rows = []
    headers = None
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = [str(c).strip() if c else "" for c in r]
            continue
        row = dict(zip(headers, r))
        tag_key      = (row.get("tag_key") or "").strip()
        propagatable = (row.get("propagatable") or "N").strip().upper() == "Y"
        in_report    = (row.get("include_in_report") or "N").strip().upper() == "Y"
        canonical    = (row.get("canonical_key") or "").strip() or None
        description  = (row.get("description") or "").strip() or None
        notes        = (row.get("notes") or "").strip() or None

        if not tag_key:
            continue
        # Skip red rows — neither propagatable nor in report
        if not propagatable and not in_report:
            continue

        rows.append(dict(
            tag_key=tag_key,
            propagatable=propagatable,
            include_in_report=in_report,
            canonical_key=canonical,
            description=description,
            notes=notes,
        ))
    wb.close()
    return rows


INSERT_SQL = """
INSERT INTO tag_master (tag_key, propagatable, include_in_report, canonical_key, description, notes)
VALUES (%(tag_key)s, %(propagatable)s, %(include_in_report)s, %(canonical_key)s, %(description)s, %(notes)s)
ON CONFLICT (tag_key) DO UPDATE
    SET propagatable       = EXCLUDED.propagatable,
        include_in_report  = EXCLUDED.include_in_report,
        canonical_key      = EXCLUDED.canonical_key,
        description        = EXCLUDED.description,
        notes              = EXCLUDED.notes
"""


def main():
    rows = read_rows()
    canonicals = [r for r in rows if r["canonical_key"] is None]
    aliases    = [r for r in rows if r["canonical_key"] is not None]

    print(f"Rows to load: {len(canonicals)} canonical, {len(aliases)} aliases  ({len(rows)} total)")
    if DRY_RUN:
        print("-- DRY RUN: no changes written --")
        for r in rows:
            print(f"  {r['tag_key']:60s}  prop={str(r['propagatable'])[0]}  report={str(r['include_in_report'])[0]}"
                  f"  canon={r['canonical_key'] or ''}")
        return

    conn = psycopg2.connect(DSN)
    cur  = conn.cursor()

    for r in canonicals:
        cur.execute(INSERT_SQL, r)
    for r in aliases:
        cur.execute(INSERT_SQL, r)

    conn.commit()
    conn.close()
    print(f"Done. {len(rows)} rows upserted into tag_master.")


if __name__ == "__main__":
    main()
