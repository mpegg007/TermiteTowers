#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/generate_tag_master_excel_v2.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 8228afb6735397ff41f8ccae542a267a32cc4d8b %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-17 18:55:36 %
#  %ccm_git_file_name: generate_tag_master_excel_v2.py %
#  %ccm_git_path: media/ImageArchive/generate_tag_master_excel_v2.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 22017 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
generate_tag_master_excel_v2.py

Query all distinct tag_keys from v2.tag_master (and any new ones lurking in
v2.image_tags not yet formally catalogued) and produce an Excel workbook with
best-guess policy values for each tag.

v2 schema differences vs v1:
  - tag_master has NO propagatable / include_in_report / notes columns.
    Those behaviours are now expressed via v2.tag_policies rows.
  - canonical_key is stored as canonical_id (FK) in v2; the Excel still uses
    the human-readable text key — load_tag_master_v2.py resolves it to an ID.
  - One Excel row = one tag_master row + one tag_policies row (target_type=image).
    Additional target_type policies (file / stack / location) must be added
    directly in the database.

Output:  media/tag_master_v2_import.xlsx

Edit the file, then run load_tag_master_v2.py to upsert into v2.
"""

import os
import re

# Excel allows only characters: tab, LF, CR, and 0x20–0xFF
_illegal_xl_chars = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)

def clean_xl(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        return s
    return _illegal_xl_chars.sub("", s)

from pathlib import Path

from dotenv import load_dotenv
import psycopg2
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.environ["PG_DSN"]

# ── Tag classification rules ──────────────────────────────────────────────────
# Maps (track_history, write_to_exif, canonical_key, description)
# track_history  → v2.tag_policies.track_history
# write_to_exif  → v2.tag_policies.write_to_exif
# canonical_key  → resolved to v2.tag_master.canonical_id by the loader

SF     = "XMP-Silverfast:ScanFrames.PreviewArea.FrameList.ScanFrame.IPTC."
SF_O   = "XMP-Silverfast:OriginalScanFrame.PreviewArea.FrameList.ScanFrame.IPTC."
SF_SP  = "XMP-Silverfast:ScanFrames.PreviewArea.FrameList.ScanFrame.ScanParameter."
SF_OSP = "XMP-Silverfast:OriginalScanFrame.PreviewArea.FrameList.ScanFrame.ScanParameter."

# (track_history, write_to_exif, canonical_key, description)
EXACT_RULES: dict[str, tuple[bool, bool, str | None, str]] = {
    # ── Canonical fully-managed tags ─────────────────────────────────────────
    "IFD0:Artist":             (True,  True,  None, "Photographer / Creator"),
    "IFD0:Copyright":          (True,  True,  None, "Copyright notice"),
    "IFD0:ImageDescription":   (True,  True,  None, "Image description / caption"),
    "ExifIFD:UserComment":     (True,  True,  None, "User comment (freeform)"),
    "IPTC:Keywords":           (True,  True,  None, "Keywords"),
    "IPTC:Headline":           (True,  True,  None, "Headline"),
    "IPTC:ObjectName":         (True,  True,  None, "Object name / title"),
    "IPTC:By-lineTitle":       (True,  True,  None, "Photographer job title"),
    "IPTC:Credit":             (True,  True,  None, "Credit line"),
    "IPTC:Source":             (True,  True,  None, "Source"),
    "IPTC:City":               (True,  True,  None, "City"),
    "IPTC:Province-State":     (True,  True,  None, "Province / State"),
    "IPTC:Country-PrimaryLocationName": (True, True, None, "Country"),
    "IPTC:OriginalTransmissionReference": (True, True, None, "Job reference / OTR"),
    "IPTC:SpecialInstructions":(True,  True,  None, "Special instructions"),
    "IPTC:Writer-Editor":      (True,  True,  None, "Writer / editor credit"),
    "IPTC:DateCreated":        (True,  True,  None, "Date of original creation"),
    "IPTC:TimeCreated":        (True,  True,  None, "Time of original creation"),
    "XMP-xmp:Rating":          (True,  True,  None, "Star rating (1-5)"),
    "XMP-xmp:Label":           (True,  True,  None, "Color label"),
    "XMP-tts:Notes":           (True,  True,  None, "TT custom notes field"),
    "XMP-tts:ScanId":          (True,  True,  None, "TT scan session identifier"),
    "XMP-tts:Ver":             (False, False, None, "TT schema version (structural — do not propagate)"),

    # ── Canonical aliases ─────────────────────────────────────────────────────
    "IPTC:Caption-Abstract":   (True,  True,  "IFD0:ImageDescription",  "Caption (alias)"),
    "IPTC:By-line":            (True,  True,  "IFD0:Artist",            "By-line / author (alias)"),
    "IPTC:CopyrightNotice":    (True,  True,  "IFD0:Copyright",         "Copyright notice (alias)"),
    "XMP-dc:Creator":          (True,  True,  "IFD0:Artist",            "XMP creator (alias)"),
    "XMP-dc:Rights":           (True,  True,  "IFD0:Copyright",         "XMP rights (alias)"),
    "XMP-dc:Description":      (True,  True,  "IFD0:ImageDescription",  "XMP description (alias)"),
    "XMP-dc:Title":            (True,  True,  "IPTC:ObjectName",        "XMP title (alias)"),
    "XMP-dc:Subject":          (True,  True,  "IPTC:Keywords",          "XMP subject (alias)"),
    SF + "IPTCByline":         (True,  True,  "IFD0:Artist",            "SilverFast IPTC By-line (alias)"),
    SF + "IPTCCopyright":      (True,  True,  "IFD0:Copyright",         "SilverFast IPTC Copyright (alias)"),
    SF + "IPTCCaption":        (True,  True,  "IFD0:ImageDescription",  "SilverFast IPTC Caption (alias)"),
    SF + "IPTCKeywords":       (True,  True,  "IPTC:Keywords",          "SilverFast IPTC Keywords (alias)"),
    SF + "IPTCHeadline":       (True,  True,  "IPTC:Headline",          "SilverFast IPTC Headline (alias)"),
    SF + "IPTCObject":         (True,  True,  "IPTC:ObjectName",        "SilverFast IPTC Object name (alias)"),
    SF + "IPTCTitle":          (True,  True,  "IPTC:ObjectName",        "SilverFast IPTC Title (alias)"),
    SF + "IPTCCity":           (True,  True,  "IPTC:City",              "SilverFast IPTC City (alias)"),
    SF + "IPTCProvince":       (True,  True,  "IPTC:Province-State",    "SilverFast IPTC Province (alias)"),
    SF + "IPTCCountry":        (True,  True,  "IPTC:Country-PrimaryLocationName", "SilverFast IPTC Country (alias)"),
    SF + "IPTCCredits":        (True,  True,  "IPTC:Credit",            "SilverFast IPTC Credits (alias)"),
    SF + "IPTCOTR":            (True,  True,  "IPTC:OriginalTransmissionReference", "SilverFast IPTC OTR (alias)"),
    SF + "IPTCSource":         (True,  True,  "IPTC:Source",            "SilverFast IPTC Source (alias)"),
    SF + "IPTCSpecial":        (True,  True,  "IPTC:SpecialInstructions", "SilverFast IPTC Special Instr. (alias)"),
    SF + "IPTCWriter":         (True,  True,  "IPTC:Writer-Editor",     "SilverFast IPTC Writer (alias)"),
    SF + "IPTCDate":           (True,  True,  "IPTC:DateCreated",       "SilverFast IPTC Date (alias)"),
    SF + "IPTCTime":           (True,  True,  "IPTC:TimeCreated",       "SilverFast IPTC Time (alias)"),
    SF + "IPTCKeywordCount":   (False, False, None, "SilverFast keyword count — structural"),
    SF_O + "IPTCKeywordCount": (False, False, None, "SilverFast original keyword count — structural"),

    # ── Track history only (visible in reporting, not written back to EXIF) ───
    "IFD0:Make":               (True,  False, None, "Scanner/camera make"),
    "IFD0:Model":              (True,  False, None, "Scanner/camera model"),
    "IFD0:Software":           (True,  False, None, "Creating software"),
    "IFD0:BitsPerSample":      (True,  False, None, "Bit depth"),
    "IFD0:SamplesPerPixel":    (True,  False, None, "Colour channels"),
    "IFD0:PhotometricInterpretation": (True, False, None, "Pixel interpretation"),
    "IFD0:Orientation":        (True,  False, None, "Image orientation"),
    "XMP-Silverfast:HDRScan":  (True,  False, None, "SilverFast HDRi scan flag"),
    "XMP-Silverfast:Negative": (True,  False, None, "SilverFast negative/positive flag"),
    "ICC_Profile:ProfileDescription": (True, False, None, "Embedded colour profile name"),
    "ICC-header:PrimaryPlatform":     (True, False, None, "ICC profile platform"),
    "IPTC:CodedCharacterSet":  (True,  False, None, "IPTC character encoding"),

    # ── Stack namespace tags (always tracked, never written to EXIF) ──────────
    "Stack:Owner":             (True,  False, None, "Stack owner (ingest-time label)"),
    "Stack:Group":             (True,  False, None, "Stack group / event label"),
}

PREFIX_RULES: list[tuple[str, bool, bool, str | None, str]] = [
    # (prefix, track_history, write_to_exif, canonical_key, description)
    ("Stack:",          True,  False, None, "Stack namespace tag — tracked, not written to EXIF"),
    ("GPS:",            True,  True,  None, "GPS geolocation coordinates"),
    ("ExifIFD:",        True,  True,  None, "Exif IFD — camera capture data"),
    ("Composite:",      True,  False, None, "Computed composite — report only"),
    ("ExifTool:",       False, False, None, "ExifTool metadata — not stored in file"),
    ("File:",           False, False, None, "File container metadata — structural"),
    ("System:",         False, False, None, "Filesystem metadata — structural"),
    ("JFIF:",           False, False, None, "JPEG container field — structural"),
    ("Samsung:",        False, False, None, "Samsung camera-specific — structural"),
    ("ICC-header:",     False, False, None, "ICC colour profile header — structural"),
    ("ICC_Profile:",    False, False, None, "ICC colour profile matrix/data — structural"),
    ("IFD1:",           False, False, None, "Thumbnail IFD — structural"),
    ("IFD2:",           False, False, None, "Transparency mask IFD — structural"),
    ("IPTC:",           False, False, None, "IPTC technical/structural field"),
    ("IFD0:",           False, False, None, "IFD0 technical/structural field"),
    ("XMP-Silverfast:", False, False, None, "SilverFast scan parameter — structural"),
    ("XMP-sf:",         False, False, None, "SilverFast XMP field — structural"),
    ("XMP-x:",          False, False, None, "XMP toolkit field — structural"),
    ("XMP-xmp:",        False, False, None, "XMP basic field"),
    ("XMP-dc:",         False, False, None, "Dublin Core XMP field"),
    ("XMP-tts:",        False, False, None, "TT custom XMP field"),
    ("Archive:",        True,  False, None, "Archive namespace tag — tracked, not written to EXIF"),
]


def classify(tag_key: str) -> tuple[bool, bool, str | None, str, str]:
    """Return (track_history, write_to_exif, canonical_key, description, note)."""
    if tag_key in EXACT_RULES:
        th, we, canon, desc = EXACT_RULES[tag_key]
        return th, we, canon, desc, ""
    for prefix, th, we, canon, desc in PREFIX_RULES:
        if tag_key.startswith(prefix):
            return th, we, canon, f"{desc} ({tag_key})", ""
    return False, False, None, "", "UNCLASSIFIED — review manually"


def main():
    conn = psycopg2.connect(DSN)
    cur  = conn.cursor()

    # ── Fetch all known tags with usage stats from v2 ────────────────────────
    cur.execute("""
        WITH per_type_usage AS (
            SELECT
                th.tag_id,

                COUNT(DISTINCT th.image_id)    AS image_count,
                COUNT(DISTINCT th.file_id)     AS file_count,
                COUNT(DISTINCT th.stack_id)    AS stack_count,
                COUNT(DISTINCT th.location_id) AS location_count,

                COUNT(DISTINCT th.new_value) AS distinct_values
            FROM v2.tag_history th
            GROUP BY th.tag_id
        ),

        top_val AS (
            SELECT DISTINCT ON (tag_id)
                tag_id,
                new_value AS most_common_value
            FROM v2.tag_history
            WHERE new_value IS NOT NULL AND new_value <> ''
            GROUP BY tag_id, new_value
            ORDER BY tag_id, COUNT(*) DESC
        ),

        recent_image AS (
            SELECT DISTINCT ON (tag_id)
                tag_id,
                new_value AS last_image_value
            FROM v2.tag_history
            WHERE image_id IS NOT NULL AND new_value IS NOT NULL
            ORDER BY tag_id, recorded_at DESC
        ),

        recent_file AS (
            SELECT DISTINCT ON (tag_id)
                tag_id,
                new_value AS last_file_value
            FROM v2.tag_history
            WHERE file_id IS NOT NULL AND new_value IS NOT NULL
            ORDER BY tag_id, recorded_at DESC
        ),

        recent_stack AS (
            SELECT DISTINCT ON (tag_id)
                tag_id,
                new_value AS last_stack_value
            FROM v2.tag_history
            WHERE stack_id IS NOT NULL AND new_value IS NOT NULL
            ORDER BY tag_id, recorded_at DESC
        ),

        recent_location AS (
            SELECT DISTINCT ON (tag_id)
                tag_id,
                new_value AS last_location_value
            FROM v2.tag_history
            WHERE location_id IS NOT NULL AND new_value IS NOT NULL
            ORDER BY tag_id, recorded_at DESC
        ),

        existing_policies AS (
            SELECT
                tp.tag_id,
                tp.track_history,
                tp.write_to_exif
            FROM v2.tag_policies tp
            WHERE tp.target_type = 'image'
        ),

        tag_usage AS (
            SELECT
                tag_id,
                COALESCE(image_count,0)    AS image_count,
                COALESCE(file_count,0)     AS file_count,
                COALESCE(stack_count,0)    AS stack_count,
                COALESCE(location_count,0) AS location_count,
                COALESCE(distinct_values,0) AS distinct_values
            FROM per_type_usage
        )

        SELECT
            tm.tag_key,
            tm.canonical_id,
            canon_tm.tag_key AS canonical_key,
            tm.description,

            -- Per‑type usage
            tu.image_count,
            tu.file_count,
            tu.stack_count,
            tu.location_count,

            -- Global distinct values
            tu.distinct_values,

            -- Global most common value
            tv.most_common_value,

            -- Per‑type most recent values
            ri.last_image_value,
            rf.last_file_value,
            rs.last_stack_value,
            rl.last_location_value,

            -- Policy flags
            ep.track_history,
            ep.write_to_exif

        FROM v2.tag_master tm
        LEFT JOIN v2.tag_master canon_tm ON canon_tm.tag_id = tm.canonical_id
        LEFT JOIN tag_usage tu ON tu.tag_id = tm.tag_id
        LEFT JOIN top_val tv ON tv.tag_id = tm.tag_id

        LEFT JOIN recent_image    ri ON ri.tag_id = tm.tag_id
        LEFT JOIN recent_file     rf ON rf.tag_id = tm.tag_id
        LEFT JOIN recent_stack    rs ON rs.tag_id = tm.tag_id
        LEFT JOIN recent_location rl ON rl.tag_id = tm.tag_id

        LEFT JOIN existing_policies ep ON ep.tag_id = tm.tag_id

        ORDER BY tm.tag_key;

    """)
    rows = cur.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "tag_master"

    # ── Styles ────────────────────────────────────────────────────────────────
    FILLS = {
        "write":   PatternFill("solid", fgColor="C6EFCE"),  # green  — track + write to EXIF
        "track":   PatternFill("solid", fgColor="FFEB9C"),  # yellow — track only
        "alias":   PatternFill("solid", fgColor="DDEBF7"),  # blue   — alias
        "neither": PatternFill("solid", fgColor="FFCCCC"),  # red    — structural
    }
    hdr_font     = Font(bold=True, color="FFFFFF")
    hdr_fill     = PatternFill("solid", fgColor="2F5496")
    info_fill    = PatternFill("solid", fgColor="595959")
    policy_fill  = PatternFill("solid", fgColor="375623")   # dark green header
    thin         = Side(style="thin", color="AAAAAA")
    border       = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap         = Alignment(wrap_text=True, vertical="top")
    center       = Alignment(horizontal="center", vertical="top")

    # Editable columns (written by load_tag_master_v2.py)
    edit_headers = [
        "tag_key",
        "canonical_key",
        "description",
        "track_history",
        "write_to_exif",
        "target_type",
    ]
    edit_widths = [62, 62, 45, 14, 13, 13]


    # View-only stat columns (not read by loader)
    stat_headers = [
        "image_count",
        "file_count",
        "stack_count",
        "location_count",
        "distinct_values",
        "most_common_value",
        "last_image_value",
        "last_file_value",
        "last_stack_value",
        "last_location_value",
    ]
    stat_widths = [
        13,  # image_count
        13,  # file_count
        13,  # stack_count
        13,  # location_count
        15,  # distinct_values
        42,  # most_common_value
        42,  # last_image_value
        42,  # last_file_value
        42,  # last_stack_value
        42,  # last_location_value
    ]


    all_headers = edit_headers + stat_headers
    all_widths  = edit_widths  + stat_widths
    N_EDIT      = len(edit_headers)

    # Header row

    for col, (h, w) in enumerate(zip(all_headers, all_widths), 1):
        cell = ws.cell(row=1, column=col, value=clean_xl(h))

        if col <= N_EDIT:
            cell.fill = hdr_fill if col <= 3 else policy_fill
        else:
            cell.fill = info_fill
        cell.font      = hdr_font
        cell.alignment = center
        cell.border    = border
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"

    for row_i, (
        tag_key,
        canonical_id,
        canonical_key_db,
        description_db,

        # per‑type usage counts
        image_count,
        file_count,
        stack_count,
        location_count,

        # global distinct values
        distinct_values,

        # global most common value
        most_common,

        # per‑type most recent values
        last_image_value,
        last_file_value,
        last_stack_value,
        last_location_value,

        # policy flags
        db_track,
        db_write,
    ) in enumerate(rows, 2):


        # Classify via rules; DB values override if already set
        th_rule, we_rule, canon_rule, desc_rule, note = classify(tag_key)

        track_history = db_track if db_track is not None else th_rule
        write_to_exif = db_write if db_write is not None else we_rule
        canonical_key = canonical_key_db or canon_rule or ""
        description   = description_db or desc_rule or ""

        # Row colour
        if canonical_key:
            fill = FILLS["alias"]
        elif write_to_exif:
            fill = FILLS["write"]
        elif track_history:
            fill = FILLS["track"]
        else:
            fill = FILLS["neither"]

        if most_common and len(most_common) > 50:
            most_common = most_common[:47] + "..."

        values = [
            tag_key,
            canonical_key,
            description,
            "Y" if track_history else "N",
            "Y" if write_to_exif else "N",
            "image",  # default target_type

            image_count,
            file_count,
            stack_count,
            location_count,
            distinct_values,
            most_common or "",

            last_image_value or "",
            last_file_value or "",
            last_stack_value or "",
            last_location_value or "",
        ]

        for col, val in enumerate(values, 1):
            val = clean_xl(val)
            cell = ws.cell(row=row_i, column=col, value=val)
            cell.fill   = fill
            cell.border = border
            if col <= N_EDIT:
                cell.alignment = center if col in (4, 5, 6) else wrap
            else:
                cell.alignment = Alignment(wrap_text=False, vertical="top")

        ws.row_dimensions[row_i].height = 15

    # ── Legend sheet ──────────────────────────────────────────────────────────
    leg = wb.create_sheet("Legend")
    legend = [
        ("Colour",       "Meaning"),
        ("Green",        "track_history=Y AND write_to_exif=Y — tag value tracked and written back to EXIF on export"),
        ("Yellow",       "track_history=Y AND write_to_exif=N — tag tracked in DB for reporting; not written to EXIF"),
        ("Blue",         "Alias — canonical_key set; value is stored under the canonical tag; this tag is a duplicate source"),
        ("Red/Pink",     "track_history=N AND write_to_exif=N — structural/container tag; excluded from tracking"),
        ("",             ""),
        ("target_type",  "Policy applies to this entity type (image / file / stack / location).  Default is 'image'.  "
                         "For additional target_type policies on the same tag, add rows directly in v2.tag_policies."),
        ("",             ""),
        ("Grey headers", "image_count / distinct_values / most_common_value are VIEW-ONLY.  Not read by the loader."),
    ]
    leg.cell(row=1, column=1).font = Font(bold=True)
    leg.cell(row=1, column=2).font = Font(bold=True)
    for r, (a, b) in enumerate(legend, 1):
        leg.cell(row=r, column=1, value=clean_xl(a))
        leg.cell(row=r, column=2, value=clean_xl(b))
    leg.column_dimensions["A"].width = 14
    leg.column_dimensions["B"].width = 100

    out = Path(__file__).parent / "tag_master_v2_import.xlsx"
    wb.save(str(out))
    print(f"Written: {out}  ({len(rows)} tags)")


if __name__ == "__main__":
    main()
