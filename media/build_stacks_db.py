#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 18ddec9702ecb5d90a220ed71de4d2d9da6e4419 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 17:21:51 %
#  %ccm_git_file_last_modified: 2026-05-23 17:21:51 %
#  %ccm_git_file_name: build_stacks_db.py %
#  %ccm_git_path: media/build_stacks_db.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4943 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
build_stacks_db.py

Build image stacks using union-find on the images table.
Clears and repopulates stacks / stack_members.

Linking rules:
  1. Same image_hash  → identical pixel content
  2. Same canonical stem (Owner_14digits_rest, ignore extension) → same renamed file

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname

Usage:
    python build_stacks_db.py
"""

import os
import sys
import re
from pathlib import Path
import psycopg2

ENV_FILE     = Path(__file__).parent / ".env"
CANONICAL_RE = re.compile(r'^[A-Za-z]+_\d{14}_')

FOLDER_ORDER = {"RAW_HDRi": 0, "TIFF_Archive": 1, "JPG_Share": 2, "JPG_Print": 3, "backup": 4}

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

# ── Union-Find ────────────────────────────────────────────────────────────────

class UF:
    def __init__(self):
        self._p = {}

    def add(self, x):
        if x not in self._p:
            self._p[x] = x

    def find(self, x):
        while self._p[x] != x:
            self._p[x] = self._p[self._p[x]]
            x = self._p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._p[rb] = ra

    def groups(self):
        result = {}
        for x in self._p:
            result.setdefault(self.find(x), []).append(x)
        return list(result.values())

# ── Helpers ───────────────────────────────────────────────────────────────────

def canonical_stem(file_name):
    if not file_name:
        return None
    stem = os.path.splitext(file_name)[0]
    return stem if CANONICAL_RE.match(stem) else None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_env(ENV_FILE)
    conn = get_conn()
    cur  = conn.cursor()

    cur.execute("SELECT id, image_hash, file_name, folder, path FROM images")
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} images from DB")

    uf       = UF()
    by_hash  = {}
    by_stem  = {}
    meta     = {}  # id → {folder, path}

    for image_id, image_hash, file_name, folder, path in rows:
        uf.add(image_id)
        meta[image_id] = {"folder": folder, "path": path, "file_name": file_name}
        if image_hash:
            by_hash.setdefault(image_hash, []).append(image_id)
        stem = canonical_stem(file_name)
        if stem:
            by_stem.setdefault(stem, []).append(image_id)

    for ids in by_hash.values():
        for i in ids[1:]:
            uf.union(ids[0], i)

    for ids in by_stem.values():
        for i in ids[1:]:
            uf.union(ids[0], i)

    groups    = uf.groups()
    multi     = [g for g in groups if len(g) > 1]
    singleton = [g for g in groups if len(g) == 1]
    print(f"Stacks: {len(multi)} multi-member, {len(singleton)} singletons")

    # Repopulate
    cur.execute("DELETE FROM stack_members")
    cur.execute("DELETE FROM stacks")
    conn.commit()

    for group in sorted(groups, key=lambda g: -len(g)):
        cur.execute("INSERT INTO stacks DEFAULT VALUES RETURNING id")
        fid = cur.fetchone()[0]
        for image_id in group:
            cur.execute(
                "INSERT INTO stack_members (stack_id, image_id) VALUES (%s,%s)",
                (fid, image_id))

    conn.commit()

    # Print multi-member families
    print()
    for group in sorted(multi, key=lambda g: -len(g)):
        group_sorted = sorted(group, key=lambda i: (
            FOLDER_ORDER.get(meta[i]["folder"], 9), meta[i]["path"]))
        print(f"  Stack ({len(group)} members):")
        for image_id in group_sorted:
            m = meta[image_id]
            print(f"    [{m['folder']:<14}]  {m['path']}")
        print()

    cur.close()
    conn.close()
    print("Stack tables updated.")

if __name__ == "__main__":
    main()
