#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0a7b51f29992413dae952118f45b3257c316979a %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-24 13:04:36 %
#  %ccm_git_file_last_modified: 2026-05-24 13:04:36 %
#  %ccm_git_file_name: stack_compare_excel.py %
#  %ccm_git_path: media/ImageArchive/stack_compare_excel.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10255 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
stack_compare_excel.py

Generate an Excel comparison grid for a stack:
  - Rows  = tag keys (all tags present across any member)
  - Columns = one per image in the stack (sorted by file_date, then file_name)
  - Cells = tag value for that image/tag combination

Colour coding:
  Row background:
    green  — all members that have this tag agree on the value
    orange — values differ across members (divergent)
    white  — only one member has this tag (unique / no comparison)

  Tag key cell (col A) gets an additional left-border colour from tag_master:
    dark green  — propagatable
    gold border — include_in_report only
    (no border) — not in tag_master

Usage:
    python media/stack_compare_excel.py <stack_id> [--out <file.xlsx>]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.environ["PG_DSN"]

# ── Styles ────────────────────────────────────────────────────────────────────
FILL_HDR      = PatternFill("solid", fgColor="1F3864")   # dark navy
FILL_AGREE    = PatternFill("solid", fgColor="E2EFDA")   # light green
FILL_DIVERGE  = PatternFill("solid", fgColor="FCE4D6")   # light orange
FILL_UNIQUE   = PatternFill("solid", fgColor="FFFFFF")   # white
FILL_TAG_PROP = PatternFill("solid", fgColor="C6EFCE")   # green tint for tag key
FILL_TAG_RPT  = PatternFill("solid", fgColor="FFEB9C")   # yellow tint for tag key

FONT_HDR  = Font(bold=True, color="FFFFFF", size=9)
FONT_SUBH = Font(bold=True, size=8)
FONT_CELL = Font(size=8)
FONT_TAGK = Font(bold=True, size=8)

ALIGN_WRAP   = Alignment(wrap_text=True, vertical="top")
ALIGN_CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)

thin  = Side(style="thin",   color="AAAAAA")
thick = Side(style="medium", color="2F5496")
BORDER_THIN  = Border(left=thin, right=thin, top=thin, bottom=thin)
BORDER_THICK = Border(left=thick, right=thin, top=thin, bottom=thin)


def fetch_stack(stack_id):
    conn = psycopg2.connect(DSN)
    cur  = conn.cursor()

    # Members
    cur.execute("""
        SELECT i.id, i.file_name, i.path, i.file_date, i.file_type, i.image_hash
        FROM stack_members sm
        JOIN images i ON i.id = sm.image_id
        WHERE sm.stack_id = %s
        ORDER BY i.file_date, i.file_name
    """, (stack_id,))
    members = cur.fetchall()
    if not members:
        conn.close()
        return None, None, None

    image_ids = [m[0] for m in members]

    # All tags for these images
    cur.execute("""
        SELECT image_id, tag_key, tag_value
        FROM image_tags
        WHERE image_id = ANY(%s)
        ORDER BY tag_key, image_id
    """, (image_ids,))
    tag_rows = cur.fetchall()

    # tag_master lookup
    cur.execute("SELECT tag_key, propagatable, include_in_report FROM tag_master")
    tm = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    conn.close()
    return members, tag_rows, tm


def build_grid(members, tag_rows):
    """Return sorted tag_keys list and dict {tag_key: {image_id: value}}."""
    grid = {}
    for image_id, tag_key, tag_value in tag_rows:
        grid.setdefault(tag_key, {})[image_id] = tag_value

    # Sort: tag_master propagatable/report first, then alphabetical by namespace
    def sort_key(tk):
        ns = tk.split(":")[0]
        ORDER = ["IFD0", "ExifIFD", "IPTC", "XMP-dc", "XMP-xmp", "XMP-tts",
                 "XMP-Silverfast", "GPS", "ICC_Profile", "ICC-header",
                 "IFD1", "IFD2", "JFIF", "Samsung", "File", "System",
                 "ExifTool", "Composite"]
        ns_rank = ORDER.index(ns) if ns in ORDER else len(ORDER)
        return (ns_rank, tk)

    tag_keys = sorted(grid.keys(), key=sort_key)
    return tag_keys, grid


def row_status(values_for_tag, image_ids):
    """Return 'agree' | 'diverge' | 'unique'."""
    present = [values_for_tag.get(iid) for iid in image_ids if iid in values_for_tag]
    if len(present) <= 1:
        return "unique"
    return "agree" if len(set(present)) == 1 else "diverge"


def make_sheet(ws, stack_id, members, tag_keys, grid, tm):
    image_ids   = [m[0] for m in members]
    file_names  = [m[1] for m in members]
    file_dates  = [m[3] for m in members]
    file_types  = [m[4] for m in members]

    n_images = len(image_ids)

    # ── Row 1: stack title ────────────────────────────────────────────────────
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=1+n_images)
    cell = ws.cell(row=1, column=1,
                   value=f"Stack {stack_id}  —  {n_images} member(s)")
    cell.font      = FONT_HDR
    cell.fill      = FILL_HDR
    cell.alignment = ALIGN_CENTER

    # ── Row 2: column headers (file names) ───────────────────────────────────
    ws.cell(row=2, column=1, value="Tag Key").font = FONT_SUBH
    ws.cell(row=2, column=1).fill      = PatternFill("solid", fgColor="D9D9D9")
    ws.cell(row=2, column=1).alignment = ALIGN_CENTER
    ws.cell(row=2, column=1).border    = BORDER_THIN

    for col_i, (fname, ftype) in enumerate(zip(file_names, file_types), 2):
        label = fname
        c = ws.cell(row=2, column=col_i, value=label)
        c.font      = FONT_SUBH
        c.fill      = FILL_HDR
        c.alignment = ALIGN_CENTER
        c.border    = BORDER_THIN

    # ── Row 3: file dates ─────────────────────────────────────────────────────
    ws.cell(row=3, column=1, value="File Date").font = Font(italic=True, size=8)
    ws.cell(row=3, column=1).fill      = PatternFill("solid", fgColor="D9D9D9")
    ws.cell(row=3, column=1).alignment = ALIGN_CENTER
    ws.cell(row=3, column=1).border    = BORDER_THIN

    for col_i, fdate in enumerate(file_dates, 2):
        c = ws.cell(row=3, column=col_i, value=fdate or "")
        c.font      = Font(italic=True, size=8, color="CCCCCC")
        c.fill      = FILL_HDR
        c.alignment = ALIGN_CENTER
        c.border    = BORDER_THIN

    # ── Data rows ─────────────────────────────────────────────────────────────
    for row_i, tag_key in enumerate(tag_keys, 4):
        values_for_tag = grid.get(tag_key, {})
        status = row_status(values_for_tag, image_ids)
        fill   = {"agree": FILL_AGREE, "diverge": FILL_DIVERGE,
                  "unique": FILL_UNIQUE}[status]

        # Tag key cell
        prop_info = tm.get(tag_key)
        if prop_info:
            prop, rpt = prop_info
            key_fill = FILL_TAG_PROP if prop else FILL_TAG_RPT
        else:
            key_fill = fill

        c = ws.cell(row=row_i, column=1, value=tag_key)
        c.font      = FONT_TAGK
        c.fill      = key_fill
        c.alignment = ALIGN_WRAP
        c.border    = BORDER_THICK if prop_info else BORDER_THIN

        # Value cells
        for col_i, iid in enumerate(image_ids, 2):
            val = values_for_tag.get(iid, "")
            c = ws.cell(row=row_i, column=col_i, value=val)
            c.font      = FONT_CELL
            c.fill      = fill
            c.alignment = ALIGN_WRAP
            c.border    = BORDER_THIN

    # ── Column widths ─────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 55
    for col_i in range(2, 2 + n_images):
        ws.column_dimensions[get_column_letter(col_i)].width = 28

    ws.freeze_panes = "B4"
    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 30
    ws.row_dimensions[3].height = 14


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print("Usage: python stack_compare_excel.py <stack_id> [--out <file.xlsx>]")
        sys.exit(1)

    stack_id = int(args[0])

    out_path = None
    if "--out" in args:
        out_path = Path(args[args.index("--out") + 1])
    else:
        out_path = Path(__file__).parent / f"stack_{stack_id}_compare.xlsx"

    members, tag_rows, tm = fetch_stack(stack_id)
    if members is None:
        print(f"No stack with id={stack_id}")
        sys.exit(1)

    tag_keys, grid = build_grid(members, tag_rows)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Stack {stack_id}"

    make_sheet(ws, stack_id, members, tag_keys, grid, tm)

    # ── Legend sheet ──────────────────────────────────────────────────────────
    leg = wb.create_sheet("Legend")
    legend = [
        ("Row colour",   "Meaning"),
        ("Light green",  "All members that have this tag agree on the value"),
        ("Light orange", "Values differ across members (divergent)"),
        ("White",        "Only one member has this tag"),
        ("", ""),
        ("Tag key cell colour", "Meaning"),
        ("Green tint",   "Tag is propagatable (from tag_master)"),
        ("Yellow tint",  "Tag is include_in_report only (from tag_master)"),
        ("Row fill",     "Not in tag_master — inherits row colour"),
    ]
    for r, (a, b) in enumerate(legend, 1):
        leg.cell(row=r, column=1, value=a).font = Font(bold=(r in (1, 6)))
        leg.cell(row=r, column=2, value=b)
    leg.column_dimensions["A"].width = 22
    leg.column_dimensions["B"].width = 60

    wb.save(str(out_path))
    print(f"Written: {out_path}")
    print(f"  {len(members)} images, {len(tag_keys)} tags, "
          f"{sum(1 for tk in tag_keys if row_status(grid[tk], [m[0] for m in members])=='diverge')} divergent rows")


if __name__ == "__main__":
    main()
