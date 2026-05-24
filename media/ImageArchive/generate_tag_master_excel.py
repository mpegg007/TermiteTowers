#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/generate_tag_master_excel.py:145 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a6e73f41e66d80745779d6b65e921f21c0f65c4b %
#  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
#  %ccm_git_commit_count: 145 %
#  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: adding readme %
#  %ccm_git_modify_date: 2026-05-24 15:15:13 %
#  %ccm_git_file_last_modified: 2026-05-24 15:15:12 %
#  %ccm_git_file_name: generate_tag_master_excel.py %
#  %ccm_git_path: media/ImageArchive/generate_tag_master_excel.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 13638 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % 
"""
generate_tag_master_excel.py

Query all distinct tag_keys from image_tags and produce an Excel workbook
with best-guess values for tag_master columns:
  - propagatable      (Y/N)
  - include_in_report (Y/N)  — never Y if propagatable=N (rule enforced in output)
  - canonical_key     — if this tag is an alias of another
  - description       — human label
  - notes

Output: media/tag_master_import.xlsx

Edit the file, then run load_tag_master.py to INSERT into the DB.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.environ["PG_DSN"]

# ── Tag classification rules ──────────────────────────────────────────────────
# (tag_key, propagatable, include_in_report, canonical_key, description)
# Order matters: first match wins.

SF = "XMP-Silverfast:ScanFrames.PreviewArea.FrameList.ScanFrame.IPTC."
SF_ORIG = "XMP-Silverfast:OriginalScanFrame.PreviewArea.FrameList.ScanFrame.IPTC."
SF_SP   = "XMP-Silverfast:ScanFrames.PreviewArea.FrameList.ScanFrame.ScanParameter."
SF_OSP  = "XMP-Silverfast:OriginalScanFrame.PreviewArea.FrameList.ScanFrame.ScanParameter."

EXACT_RULES = {
    # ── Canonical propagatable tags ───────────────────────────────────────────
    "IFD0:Artist":             (True,  True,  None, "Photographer / Creator"),
    "IFD0:Copyright":          (True,  True,  None, "Copyright notice"),
    "IFD0:ImageDescription":   (True,  True,  None, "Image description / caption"),
    "ExifIFD:UserComment":     (True,  True,  None, "User comment (freeform)"),
    "IPTC:Keywords":           (True,  True,  None, "Keywords"),
    "IPTC:Headline":           (True,  True,  None, "Headline"),
    "IPTC:ObjectName":         (True,  True,  None, "Object name / title"),
    "IPTC:Caption-Abstract":   (True,  True,  "IFD0:ImageDescription", "Caption (alias of ImageDescription)"),
    "IPTC:By-line":            (True,  True,  "IFD0:Artist",           "By-line / author (alias of Artist)"),
    "IPTC:CopyrightNotice":    (True,  True,  "IFD0:Copyright",        "Copyright notice (alias of Copyright)"),
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
    "XMP-dc:Creator":          (True,  True,  "IFD0:Artist",           "XMP creator (alias of Artist)"),
    "XMP-dc:Rights":           (True,  True,  "IFD0:Copyright",        "XMP rights (alias of Copyright)"),
    "XMP-dc:Description":      (True,  True,  "IFD0:ImageDescription", "XMP description (alias of ImageDescription)"),
    "XMP-dc:Title":            (True,  True,  "IPTC:ObjectName",       "XMP title (alias of ObjectName)"),
    "XMP-dc:Subject":          (True,  True,  "IPTC:Keywords",         "XMP subject (alias of Keywords)"),
    "XMP-xmp:Rating":          (True,  True,  None, "Star rating (1-5)"),
    "XMP-xmp:Label":           (True,  True,  None, "Color label"),
    "XMP-tts:Notes":           (True,  True,  None, "TT custom notes field"),
    "XMP-tts:ScanId":          (True,  True,  None, "TT scan session identifier"),
    "XMP-tts:Ver":             (False, False, None, "TT schema version (do not propagate)"),

    # ── SilverFast IPTC aliases ───────────────────────────────────────────────
    SF + "IPTCByline":         (True,  True,  "IFD0:Artist",           "SilverFast IPTC By-line (alias of Artist)"),
    SF + "IPTCCopyright":      (True,  True,  "IFD0:Copyright",        "SilverFast IPTC Copyright (alias of Copyright)"),
    SF + "IPTCCaption":        (True,  True,  "IFD0:ImageDescription", "SilverFast IPTC Caption (alias of ImageDescription)"),
    SF + "IPTCKeywords":       (True,  True,  "IPTC:Keywords",         "SilverFast IPTC Keywords (alias of Keywords)"),
    SF + "IPTCHeadline":       (True,  True,  "IPTC:Headline",         "SilverFast IPTC Headline (alias of Headline)"),
    SF + "IPTCObject":         (True,  True,  "IPTC:ObjectName",       "SilverFast IPTC Object name (alias of ObjectName)"),
    SF + "IPTCTitle":          (True,  True,  "IPTC:ObjectName",       "SilverFast IPTC Title (alias of ObjectName)"),
    SF + "IPTCCity":           (True,  True,  "IPTC:City",             "SilverFast IPTC City (alias of City)"),
    SF + "IPTCProvince":       (True,  True,  "IPTC:Province-State",   "SilverFast IPTC Province (alias of Province-State)"),
    SF + "IPTCCountry":        (True,  True,  "IPTC:Country-PrimaryLocationName", "SilverFast IPTC Country (alias)"),
    SF + "IPTCCredits":        (True,  True,  "IPTC:Credit",           "SilverFast IPTC Credits (alias of Credit)"),
    SF + "IPTCOTR":            (True,  True,  "IPTC:OriginalTransmissionReference", "SilverFast IPTC OTR (alias)"),
    SF + "IPTCSource":         (True,  True,  "IPTC:Source",           "SilverFast IPTC Source (alias of Source)"),
    SF + "IPTCSpecial":        (True,  True,  "IPTC:SpecialInstructions", "SilverFast IPTC Special Instr. (alias)"),
    SF + "IPTCWriter":         (True,  True,  "IPTC:Writer-Editor",    "SilverFast IPTC Writer (alias of Writer-Editor)"),
    SF + "IPTCDate":           (True,  True,  "IPTC:DateCreated",      "SilverFast IPTC Date (alias of DateCreated)"),
    SF + "IPTCTime":           (True,  True,  "IPTC:TimeCreated",      "SilverFast IPTC Time (alias of TimeCreated)"),
    SF + "IPTCKeywordCount":   (False, False, None, "SilverFast keyword count — not useful"),

    SF_ORIG + "IPTCKeywordCount": (False, False, None, "SilverFast original keyword count — not useful"),

    # ── Report-only (interesting but not propagated) ──────────────────────────
    "IFD0:Make":               (False, True,  None, "Scanner/camera make"),
    "IFD0:Model":              (False, True,  None, "Scanner/camera model"),
    "IFD0:Software":           (False, True,  None, "Creating software"),
    "IFD0:BitsPerSample":      (False, True,  None, "Bit depth"),
    "IFD0:SamplesPerPixel":    (False, True,  None, "Colour channels"),
    "IFD0:PhotometricInterpretation": (False, True, None, "Pixel interpretation (RGB/greyscale)"),
    "IFD0:Orientation":        (False, True,  None, "Image orientation"),
    "XMP-Silverfast:HDRScan":  (False, True,  None, "SilverFast HDRi scan flag"),
    "XMP-Silverfast:Negative": (False, True,  None, "SilverFast negative/positive flag"),
    "ICC_Profile:ProfileDescription": (False, True, None, "Embedded colour profile name"),
    "ICC-header:PrimaryPlatform":     (False, True, None, "ICC profile platform (Apple/MS)"),
    "ICC-header:ProfileCMMType":      (False, True, None, "ICC CMM type"),
    "IPTC:CodedCharacterSet":  (False, True,  None, "IPTC character encoding"),
}

# Prefix rules for everything not matched by exact rules
PREFIX_RULES = [
    # (prefix, propagatable, include_in_report, canonical_key, description_template)
    ("Composite:",      False, False, None, "Computed composite — not stored in file"),
    ("ExifTool:",       False, False, None, "ExifTool metadata — not in image"),
    ("File:",           False, False, None, "File container metadata"),
    ("System:",         False, False, None, "Filesystem metadata"),
    ("JFIF:",           False, False, None, "JPEG container field"),
    ("Samsung:",        False, False, None, "Samsung camera-specific"),
    ("ICC-header:",     False, False, None, "ICC colour profile header"),
    ("ICC_Profile:",    False, False, None, "ICC colour profile matrix/data"),
    ("IFD1:",           False, False, None, "Thumbnail IFD — not propagated"),
    ("IFD2:",           False, False, None, "Transparency mask IFD — not propagated"),
    ("GPS:",            False, False, None, "GPS coordinates (scan — likely absent)"),
    ("ExifIFD:",        False, False, None, "Exif IFD — camera exposure/capture data"),
    ("IPTC:",           False, False, None, "IPTC technical field"),
    ("IFD0:",           False, False, None, "IFD0 technical field"),
    ("XMP-Silverfast:", False, False, None, "SilverFast scan parameter"),
    ("XMP-sf:",         False, False, None, "SilverFast XMP field"),
    ("XMP-x:",          False, False, None, "XMP toolkit field"),
    ("XMP-xmp:",        False, False, None, "XMP basic field"),
    ("XMP-dc:",         False, False, None, "Dublin Core XMP field"),
    ("XMP-tts:",        False, False, None, "TT custom XMP field"),
]


def classify(tag_key):
    if tag_key in EXACT_RULES:
        prop, report, canon, desc = EXACT_RULES[tag_key]
        return prop, report, canon, desc, ""
    for prefix, prop, report, canon, desc in PREFIX_RULES:
        if tag_key.startswith(prefix):
            return prop, report, canon, f"{desc} ({tag_key})", ""
    return False, False, None, "", "UNCLASSIFIED — review manually"


def main():
    conn = psycopg2.connect(DSN)
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT tag_key FROM image_tags ORDER BY tag_key")
    tag_keys = [r[0] for r in cur.fetchall()]
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "tag_master"

    # ── Styles ────────────────────────────────────────────────────────────────
    FILLS = {
        "propagate": PatternFill("solid", fgColor="C6EFCE"),   # green
        "report":    PatternFill("solid", fgColor="FFEB9C"),   # yellow
        "neither":   PatternFill("solid", fgColor="FFCCCC"),   # red/pink
        "alias":     PatternFill("solid", fgColor="DDEBF7"),   # blue
    }
    hdr_font  = Font(bold=True, color="FFFFFF")
    hdr_fill  = PatternFill("solid", fgColor="2F5496")
    thin      = Side(style="thin", color="AAAAAA")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap      = Alignment(wrap_text=True, vertical="top")
    center    = Alignment(horizontal="center", vertical="top")

    headers = ["tag_key", "propagatable", "include_in_report",
               "canonical_key", "description", "notes"]
    col_widths = [60, 14, 18, 62, 45, 30]

    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font  = hdr_font
        cell.fill  = hdr_fill
        cell.alignment = center
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"

    for row_i, tag_key in enumerate(tag_keys, 2):
        prop, report, canon, desc, notes = classify(tag_key)

        # Enforce: include_in_report can only be Y if propagatable is Y
        # EXCEPT for report-only tags explicitly marked
        # (already handled in EXACT_RULES; prefix defaults both to False)

        if canon:
            fill = FILLS["alias"]
        elif prop:
            fill = FILLS["propagate"]
        elif report:
            fill = FILLS["report"]
        else:
            fill = FILLS["neither"]

        values = [tag_key, "Y" if prop else "N", "Y" if report else "N",
                  canon or "", desc, notes]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_i, column=col, value=val)
            cell.fill      = fill
            cell.border    = border
            cell.alignment = wrap
            if col in (2, 3):
                cell.alignment = center

        ws.row_dimensions[row_i].height = 15

    # ── Legend sheet ──────────────────────────────────────────────────────────
    leg = wb.create_sheet("Legend")
    legend = [
        ("Colour", "Meaning"),
        ("Green",  "Canonical propagatable tag — value propagated to non-HDRi members"),
        ("Blue",   "Alias — value propagated as canonical_key; source tag itself is not the target"),
        ("Yellow", "Report-only — shown in divergent tag report but NOT propagated"),
        ("Red/Pink", "Neither — technical/structural, excluded from report and propagation"),
    ]
    for r, (a, b) in enumerate(legend, 1):
        leg.cell(row=r, column=1, value=a).font = Font(bold=(r==1))
        leg.cell(row=r, column=2, value=b)
    leg.column_dimensions["A"].width = 12
    leg.column_dimensions["B"].width = 80

    out = Path(__file__).parent / "tag_master_import.xlsx"
    wb.save(str(out))
    print(f"Written: {out}  ({len(tag_keys)} tags)")


if __name__ == "__main__":
    main()
