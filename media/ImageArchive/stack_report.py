#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/stack_report.py:145 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 60793fa90491311c2c236f1af92f8be8443357a2 %
#  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
#  %ccm_git_commit_count: 145 %
#  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: adding readme %
#  %ccm_git_modify_date: 2026-05-24 15:15:30 %
#  %ccm_git_file_last_modified: 2026-05-24 15:15:30 %
#  %ccm_git_file_name: stack_report.py %
#  %ccm_git_path: media/ImageArchive/stack_report.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 17862 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % 
# %git_commit_history: 2026-05-23 Matthew Pegg  image tags  % 
"""
stack_report.py

Generate a stack report from the DB for a given stack_id.

Usage:
    python stack_report.py <stack_id> [--out <file.md>]
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.environ["PG_DSN"]

CANONICAL_RE = re.compile(r'^([A-Za-z]+_\d{14}_)')


def fmt_size(n):
    return f"{n:,}" if n else "—"


def clean_date(raw):
    """Convert '2026:05:22 21:14:53-04:00' -> '2026-05-22 21:14:53'"""
    if not raw:
        return "—"
    s = str(raw)
    s = re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', s)
    s = re.sub(r'[+-]\d{2}:\d{2}$', '', s).strip()
    return s


def main():
    if len(sys.argv) < 2:
        print("Usage: stack_report.py <stack_id> [--out <file.md>]")
        sys.exit(1)
    stack_id = int(sys.argv[1])

    out_path = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    conn = psycopg2.connect(DSN)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id FROM stacks WHERE id = %s", (stack_id,))
    if not cur.fetchone():
        print(f"No stack with id={stack_id}")
        sys.exit(1)

    # Members — canonical folders first, then backup
    cur.execute("""
        SELECT i.id, i.path, i.file_name, i.folder, i.file_type,
               i.image_hash, i.file_bytes, i.file_date, i.archive_owner, i.scan_name
        FROM stack_members sm
        JOIN images i ON i.id = sm.image_id
        WHERE sm.stack_id = %s
        ORDER BY
            CASE i.folder
                WHEN 'RAW_HDRi'     THEN 1
                WHEN 'TIFF_Archive' THEN 2
                WHEN 'JPG_Print'    THEN 3
                ELSE 4
            END,
            i.file_date DESC NULLS LAST
    """, (stack_id,))
    members = list(cur.fetchall())
    member_index = {row["id"]: i for i, row in enumerate(members, 1)}

    hdri_ids = {r["id"] for r in members if "HDRi" in (r["file_type"] or "")}
    hdr_ids  = {r["id"] for r in members if r["id"] not in hdri_ids}

    # Does tag_master have any include_in_report tags?
    cur.execute("SELECT COUNT(*) AS n FROM tag_master WHERE include_in_report = true")
    report_tags_defined = cur.fetchone()["n"] > 0

    # Divergent tags — behaviour depends on whether tag_master is populated:
    #   populated → only include_in_report canonical tags + their aliases, hybrid conflict logic
    #   empty     → fall back to all divergent tags across stack
    divergent_sections = []   # list of (canonical_key, description, [row_dicts])

    if report_tags_defined:
        # Per-stack: fetch all values for include_in_report tags and their aliases
        cur.execute("""
            SELECT
                COALESCE(tm.canonical_key, tm.tag_key) AS canonical_key,
                tm.tag_key                             AS source_tag_key,
                i.id, i.file_name, i.folder, i.file_type,
                it.tag_value, it.changed_at,
                tmcanon.description
            FROM image_tags it
            JOIN stack_members sm ON sm.image_id = it.image_id
            JOIN images i         ON i.id = it.image_id
            JOIN tag_master tm    ON tm.tag_key = it.tag_key
            JOIN tag_master tmcanon ON tmcanon.tag_key = COALESCE(tm.canonical_key, tm.tag_key)
            WHERE sm.stack_id = %s
              AND it.tag_value IS NOT NULL AND it.tag_value <> ''
              AND tmcanon.include_in_report = true
            ORDER BY canonical_key,
                CASE i.folder WHEN 'RAW_HDRi' THEN 1 WHEN 'TIFF_Archive' THEN 2
                               WHEN 'JPG_Print' THEN 3 ELSE 4 END,
                i.file_date DESC NULLS LAST
        """, (stack_id,))
        raw = cur.fetchall()

        # Group: canonical_key → image_id → list of {source_tag_key, tag_value, changed_at}
        from collections import defaultdict
        by_canon = defaultdict(lambda: defaultdict(list))
        descriptions = {}
        for r in raw:
            by_canon[r["canonical_key"]][r["id"]].append(r)
            descriptions[r["canonical_key"]] = r["description"]

        for canonical_key in sorted(by_canon):
            per_member = by_canon[canonical_key]
            # Collect all distinct values across members (collapsed to canonical)
            all_vals = {entry["tag_value"]
                        for entries in per_member.values()
                        for entry in entries}

            # Build display rows
            display_rows = []
            for img_id, entries in per_member.items():
                # Separate canonical vs alias entries for this member
                canon_entries = [e for e in entries if e["source_tag_key"] == canonical_key]
                alias_entries = [e for e in entries if e["source_tag_key"] != canonical_key]

                canon_val = canon_entries[0]["tag_value"] if canon_entries else None
                alias_entries_by_key = {}
                for e in alias_entries:
                    alias_entries_by_key.setdefault(e["source_tag_key"], e)

                # Check for alias/canonical conflict on same image
                conflicts = {ak: ae for ak, ae in alias_entries_by_key.items()
                             if canon_val is not None and ae["tag_value"] != canon_val}

                # Primary row (canonical or alias-only)
                primary = canon_entries[0] if canon_entries else alias_entries[0]
                alias_note = "" if canon_entries else f" *(via `{primary['source_tag_key']}`)*"
                display_rows.append({
                    "img_id": img_id,
                    "entry": primary,
                    "alias_note": alias_note,
                    "conflict": False,
                })
                # Conflict rows
                for ak, ae in conflicts.items():
                    display_rows.append({
                        "img_id": img_id,
                        "entry": ae,
                        "alias_note": f" *(alias `{ak}`)*",
                        "conflict": True,
                    })

            # Only include in report if values actually diverge across members
            # OR if any member has a conflict
            has_conflict = any(dr["conflict"] for dr in display_rows)
            has_divergence = len(all_vals) > 1
            if has_divergence or has_conflict:
                divergent_sections.append((canonical_key, descriptions.get(canonical_key), display_rows))
    else:
        # Fallback: all tags with distinct values > 1
        cur.execute("""
            SELECT it.tag_key
            FROM image_tags it
            JOIN stack_members sm ON sm.image_id = it.image_id
            WHERE sm.stack_id = %s
              AND it.tag_value IS NOT NULL AND it.tag_value <> ''
            GROUP BY it.tag_key
            HAVING COUNT(DISTINCT it.tag_value) > 1
            ORDER BY it.tag_key
        """, (stack_id,))
        fallback_keys = [r["tag_key"] for r in cur.fetchall()]

        if fallback_keys:
            cur.execute("""
                SELECT i.id, i.file_name, i.folder, i.file_type,
                       it.tag_key, it.tag_value, it.changed_at
                FROM image_tags it
                JOIN stack_members sm ON sm.image_id = it.image_id
                JOIN images i ON i.id = it.image_id
                WHERE sm.stack_id = %s AND it.tag_key = ANY(%s)
                ORDER BY it.tag_key,
                    CASE i.folder WHEN 'RAW_HDRi' THEN 1 WHEN 'TIFF_Archive' THEN 2
                                   WHEN 'JPG_Print' THEN 3 ELSE 4 END,
                    i.file_date DESC NULLS LAST
            """, (stack_id, fallback_keys))
            fb_data = {}
            for r in cur.fetchall():
                fb_data.setdefault(r["tag_key"], []).append(r)
            for tag_key in fallback_keys:
                rows = fb_data.get(tag_key, [])
                display_rows = [{"img_id": r["id"], "entry": r,
                                 "alias_note": "", "conflict": False} for r in rows]
                divergent_sections.append((tag_key, None, display_rows))

    # Propagatable tags
    cur.execute("SELECT tag_key FROM tag_master WHERE propagatable = TRUE AND canonical_key IS NULL ORDER BY tag_key")
    prop_keys = [r["tag_key"] for r in cur.fetchall()]

    prop_authority = {}
    if prop_keys:
        cur.execute("""
            SELECT tag_key, tag_value, source_tag_key, source_image_id, source_path
            FROM stack_tag_authority
            WHERE stack_id = %s
            ORDER BY tag_key
        """, (stack_id,))
        for r in cur.fetchall():
            prop_authority[r["tag_key"]] = r

    # Current tag values on non-HDRi members for each propagatable key
    target_current = {}
    if prop_keys and hdr_ids:
        cur.execute("""
            SELECT it.tag_key, it.image_id, it.tag_value
            FROM image_tags it
            WHERE it.image_id = ANY(%s) AND it.tag_key = ANY(%s)
        """, (list(hdr_ids), prop_keys))
        for r in cur.fetchall():
            target_current.setdefault(r["tag_key"], {})[r["image_id"]] = r["tag_value"]

    conn.close()

    # ── Header fields ─────────────────────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    stems, owners, scan_names = set(), set(), set()
    for row in members:
        m = CANONICAL_RE.match(row["file_name"] or "")
        if m:
            stems.add(m.group(1))
            owners.add(m.group(1).split("_")[0])
        if row["scan_name"]:
            scan_names.add(row["scan_name"])

    stem      = stems.pop()      if len(stems)      == 1 else (", ".join(sorted(stems))      or "—")
    owner     = owners.pop()     if len(owners)     == 1 else (", ".join(sorted(owners))     or "unknown")
    scan_name = scan_names.pop() if len(scan_names) == 1 else (", ".join(sorted(scan_names)) or "—")

    # ── Hash groups ───────────────────────────────────────────────────────────
    hash_groups = {}
    for row in members:
        h = row["image_hash"] or "none"
        hash_groups.setdefault(h, []).append(row)

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append("# TT Stack Report\n")
    lines.append(f"> Generated: {now} (from DB)")
    lines.append(f"> Stack ID: {stack_id}")
    lines.append(f"> Archive Owner: {owner}")
    lines.append(f"> Canonical Stem: `{stem}`")
    lines.append(f"> Scan Session: `{scan_name}`")
    lines.append("")
    lines.append("---\n")

    # ── Members ───────────────────────────────────────────────────────────────
    lines.append(f"## Members ({len(members)})\n")
    lines.append("| # | id | Folder | File Name | Type | Hash | Size | FileDate |")
    lines.append("|---|-----|--------|-----------|------|------|------|----------|")
    for i, row in enumerate(members, 1):
        is_hdri  = row["id"] in hdri_ids
        type_col = f"**{row['file_type']}** ⚠" if is_hdri else (row["file_type"] or "—")
        h        = row["image_hash"] or "—"
        hash_col = f"`{h[:8]}`" if h != "—" else "—"
        lines.append(
            f"| {i} | {row['id']} | {row['folder']} | {row['file_name']} "
            f"| {type_col} | {hash_col} | {fmt_size(row['file_bytes'])} B "
            f"| {clean_date(row['file_date'])} |"
        )
    lines.append("")
    lines.append("> ⚠ HDRi — never receives propagated tags.")
    lines.append("")
    lines.append("---\n")

    # ── Stack Structure ───────────────────────────────────────────────────────
    lines.append("## Stack Structure\n")
    lines.append(f"{len(hash_groups)} distinct pixel payload(s):\n")
    lines.append("| Hash | Type(s) | Members |")
    lines.append("|------|---------|---------|")
    for h, rows in sorted(hash_groups.items(), key=lambda kv: -len(kv[1])):
        types   = " / ".join(sorted({r["file_type"] or "?" for r in rows}))
        mnums   = ", ".join(f"#{member_index[r['id']]} {r['folder']}" for r in rows)
        lines.append(f"| `{h[:8]}` | {types} | {mnums} |")
    lines.append("")
    lines.append("---\n")

    # ── Divergent Tags ────────────────────────────────────────────────────────
    lines.append("## Divergent Tags\n")
    if not report_tags_defined:
        lines.append("> `tag_master` has no `include_in_report` tags — showing all divergent tags as fallback.\n")
    if divergent_sections:
        lines.append(f"> {len(divergent_sections)} tag(s) with differing values or alias/canonical conflicts.\n")
        for canonical_key, description, display_rows in divergent_sections:
            heading = f"`{canonical_key}`"
            if description:
                heading += f" — {description}"
            lines.append(f"### {heading}\n")
            lines.append("| # | Folder | Value | Source Tag | Tag Last Changed |")
            lines.append("|---|--------|-------|------------|-----------------|")
            for dr in display_rows:
                r   = dr["entry"]
                mn  = member_index[r["id"]]
                ca  = str(r["changed_at"])[:19] if r["changed_at"] else "—"
                val = f"`{r['tag_value']}`"
                src = dr["alias_note"] or ""
                conflict_flag = " ⚠ alias/canonical conflict" if dr["conflict"] else ""
                lines.append(f"| #{mn} | {r['folder']} | {val}{conflict_flag} | {src} | {ca} |")
            lines.append("")
    else:
        lines.append("_No divergent tags found for configured report tags._\n")
    lines.append("---\n")

    # ── Propagation Plan ─────────────────────────────────────────────────────
    lines.append("## Propagation Plan\n")

    if not prop_keys:
        lines.append("_`tag_master` has no propagatable tags defined yet._\n")
        lines.append("Example — to define propagatable tags:\n")
        lines.append("```sql")
        lines.append("INSERT INTO tag_master (tag_key, propagatable) VALUES")
        lines.append("    ('IFD0:Artist', true),")
        lines.append("    ('IFD0:Copyright', true),")
        lines.append("    ('IFD0:ImageDescription', true);")
        lines.append("-- Alias example:")
        lines.append("INSERT INTO tag_master (tag_key, canonical_key) VALUES")
        lines.append("    ('XMP-Silverfast:ScanFrames.PreviewArea.FrameList.ScanFrame.IPTC.IPTCCopyright', 'IFD0:Copyright');")
        lines.append("```")
    else:
        targets = [r for r in members if r["id"] in hdr_ids]

        if not prop_authority:
            lines.append("_No authority values found for any propagatable tag in this stack._\n")
        else:
            lines.append(
                "> Authority = most-recent non-empty value in the stack. "
                "HDRi members may be authority **sources** but are never **targets**.\n"
            )
            hdr_headers = " | ".join(f"→ #{member_index[t['id']]} {t['folder']}" for t in targets)
            hdr_seps    = " | ".join("---" for _ in targets)
            lines.append(f"| Tag | Authority Value | Source | {hdr_headers} |")
            lines.append(f"|-----|----------------|--------|{hdr_seps}|")

            for tag_key, auth in sorted(prop_authority.items()):
                src_name     = Path(auth["source_path"]).name if auth["source_path"] else "—"
                val          = auth["tag_value"] or "—"
                src_tag      = auth["source_tag_key"] or tag_key
                alias_note   = f" *(via `{src_tag}`)*" if src_tag != tag_key else ""
                cells = []
                for t in targets:
                    cur_val = target_current.get(tag_key, {}).get(t["id"])
                    if cur_val is None:
                        cells.append("absent — **would write**")
                    elif cur_val == val:
                        cells.append("✓ matches")
                    else:
                        cells.append(f"`{cur_val}` — **would overwrite**")
                lines.append(f"| `{tag_key}`{alias_note} | `{val}` | {src_name} | " + " | ".join(cells) + " |")

        no_auth = [k for k in prop_keys if k not in prop_authority]
        if no_auth:
            lines.append("")
            lines.append("### No authority found\n")
            lines.append("_No member in this stack has a value for these — nothing to propagate:_\n")
            for k in no_auth:
                lines.append(f"- `{k}`")

    lines.append("")
    output = "\n".join(lines)

    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
