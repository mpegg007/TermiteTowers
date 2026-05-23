#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5e28ee5ef7fc536b6a2e7242e8ecab77ca41a098 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 17:21:49 %
#  %ccm_git_file_last_modified: 2026-05-23 17:21:48 %
#  %ccm_git_file_name: build_family_map.py %
#  %ccm_git_path: media/build_family_map.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 6997 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-23 Matthew Pegg  image tagging phase 1  % 
"""
build_family_map.py

Reads all .md sidecars under the PhotoArchive and groups image files into
families using union-find with two linking rules:

  1. Same ImageHash  → identical pixel content (copies, format conversions)
  2. Same canonical stem → same renamed file in different formats
       Canonical = matches  ^[A-Za-z]+_\d{14}_  (Owner_14digits_rest)
       Strip extension, compare stems exactly.
       Generic names like "party" are excluded from stem-matching.

Membership is transitive: A==B by hash, B==C by stem → all three are one family.

Usage:
    python build_family_map.py [<archive_root>]

Output: printed family report + families.json beside this script.
"""

import os
import sys
import re
import json

ARCHIVE_ROOT = r"C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"
CANONICAL_RE = re.compile(r'^[A-Za-z]+_\d{14}_')


# ── Union-Find ────────────────────────────────────────────────────────────────

class UF:
    def __init__(self):
        self._parent = {}

    def add(self, x):
        if x not in self._parent:
            self._parent[x] = x

    def find(self, x):
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra

    def stacks(self):
        groups = {}
        for x in self._parent:
            r = self.find(x)
            groups.setdefault(r, []).append(x)
        return list(groups.values())


# ── Sidecar parsing ───────────────────────────────────────────────────────────

def parse_sidecar(md_path):
    """Return (image_hash, file_name) from Identity section, or (None, None)."""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None, None

    h = re.search(r'\*\*ImageHash\*\*:\s*`([0-9a-f]+)`', content)
    n = re.search(r'\*\*FileName\*\*:\s*(.+)', content)
    image_hash = h.group(1) if h else None
    file_name  = n.group(1).strip() if n else None
    return image_hash, file_name


def canonical_stem(file_name):
    """Return stem if file_name is canonical, else None."""
    stem = os.path.splitext(file_name)[0] if file_name else ""
    return stem if CANONICAL_RE.match(stem) else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main(archive_root):
    # Collect all sidecars
    records = []  # list of {path, md_path, image_hash, file_name, stem}
    for dirpath, _, filenames in os.walk(archive_root):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            md_path    = os.path.join(dirpath, fname)
            image_path = md_path[:-3]  # strip .md
            image_hash, file_name = parse_sidecar(md_path)
            if not image_hash:
                continue
            stem = canonical_stem(file_name)
            records.append({
                "path":       image_path,
                "md_path":    md_path,
                "image_hash": image_hash,
                "file_name":  file_name or os.path.basename(image_path),
                "stem":       stem,
                "folder":     os.path.basename(dirpath),
            })

    print(f"Loaded {len(records)} sidecars from {archive_root}\n")

    # Build union-find keyed on image_path
    uf = UF()
    for r in records:
        uf.add(r["path"])

    # Index by hash and canonical stem
    by_hash = {}
    by_stem = {}
    for r in records:
        by_hash.setdefault(r["image_hash"], []).append(r["path"])
        if r["stem"]:
            by_stem.setdefault(r["stem"], []).append(r["path"])

    # Rule 1: same hash
    for paths in by_hash.values():
        for p in paths[1:]:
            uf.union(paths[0], p)

    # Rule 2: same canonical stem
    for paths in by_stem.values():
        for p in paths[1:]:
            uf.union(paths[0], p)

    # Build record lookup
    rec_by_path = {r["path"]: r for r in records}

    # Collect and sort stacks (largest first)
    raw_stacks = uf.stacks()
    stacks = []
    for members in raw_stacks:
        recs = [rec_by_path[p] for p in members if p in rec_by_path]
        FOLDER_ORDER = {"RAW_HDRi": 0, "TIFF_Archive": 1, "JPG_Share": 2, "JPG_Print": 3, "backup": 4}
        recs.sort(key=lambda r: (FOLDER_ORDER.get(r["folder"], 9), r["file_name"]))
        stacks.append(recs)
    stacks.sort(key=lambda f: -len(f))

    # ── Report ────────────────────────────────────────────────────────────────
    singletons  = [f for f in stacks if len(f) == 1]
    multi       = [f for f in stacks if len(f) > 1]

    print(f"Stacks: {len(multi)} multi-member, {len(singletons)} singletons\n")
    print("=" * 70)

    for i, stk in enumerate(multi, 1):
        hashes = {r["image_hash"] for r in stk}
        print(f"\nStack {i}  ({len(stk)} members, {len(hashes)} distinct hash(es))")
        print("-" * 70)
        prev_hash = None
        for r in stk:
            marker = "  " if r["image_hash"] == prev_hash else "* " if prev_hash else "  "
            rel = os.path.relpath(r["path"], archive_root)
            print(f"  {r['image_hash'][:8]}  [{r['folder']:<14}]  {rel}")
            prev_hash = r["image_hash"]

    if singletons:
        print(f"\n{'=' * 70}")
        print(f"Singletons ({len(singletons)}) — no related files found:")
        for stk in singletons:
            r = stk[0]
            rel = os.path.relpath(r["path"], archive_root)
            print(f"  {r['image_hash'][:8]}  [{r['folder']:<14}]  {rel}")

    # ── JSON output ───────────────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stacks.json")
    json_out = []
    for stk in stacks:
        json_out.append([{
            "path":       r["path"],
            "folder":     r["folder"],
            "file_name":  r["file_name"],
            "image_hash": r["image_hash"],
        } for r in stk])
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2)
    print(f"\nJSON written to {out_path}")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else ARCHIVE_ROOT
    main(root)
