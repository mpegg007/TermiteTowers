#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 38528bd0a2df477cfa386af8b0dc5ed0c125c606 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 18:20:38 %
#  %ccm_git_file_last_modified: 2026-05-23 18:20:38 %
#  %ccm_git_file_name: extract_to_sidecar.py %
#  %ccm_git_path: media/extract_to_sidecar.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 11615 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-23 Matthew Pegg  image tagging phase 1  % 
﻿#!/usr/bin/env python3
"""
extract_to_sidecar.py

Extract all metadata from a TIFF to a Markdown sidecar (.md).
Tracks name history, tag snapshots over time, and derived file hashes.

Usage:
    python extract_to_sidecar.py <file.tif>
"""

import subprocess, json, sys, os, re, datetime
from urllib.parse import unquote
import xml.etree.ElementTree as ET

EXIFTOOL = r"C:\Apps\exiftool-13.58_64\exiftool.exe"

BLOB_TAGS = [
    "XMP-Silverfast:ScanFrames",
    "XMP-Silverfast:OriginalScanFrame",
]

# Blob dot-path substrings to exclude. Any path containing one of these is dropped.
BLOB_IGNORE = [
    ".PreviewArea.Draw_Mask",
    ".PreviewArea.Preview_Rotation_Data.",
    ".PreviewArea.WorkflowPilot_Data.",
    ".PreviewArea.GeneralDialogList.",
    ".PreviewArea.InputProfileName",
    ".PreviewArea.Maximum_ISRD_Offset",
    ".ScanFrame.FilterList.",       # entire filter/processing pipeline
    ".ScanFrame.FilterDialogList.", # filter panel window geometry
    ".ScanFrame.FilterBlackList.",  # disabled filter list
    ".ScanFrame.ProcessList.",      # processing step history
    ".ScanFrame.VerticalScrollbarPosition",
]

# ScanParameter fields to keep; all other ScanParameter fields are excluded.
SCANPARAM_KEEP = {"Directory", "InputFilename", "Name"}


def run_et(*args):
    cmd = [EXIFTOOL] + list(args)
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout, r.stderr


def get_all_tags(filepath):
    raw, _ = run_et("-j", "-a", "-G1", filepath)
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return data[0] if data else {}
    except (json.JSONDecodeError, IndexError):
        return {}


def get_image_hash(filepath):
    raw, _ = run_et("-ImageDataHash", "-s3", filepath)
    return raw.decode("utf-8", errors="replace").strip()


def get_blob(filepath, tag):
    raw, _ = run_et("-b", f"-{tag}", filepath)
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace").strip()
    if not text.startswith("<"):
        text = unquote(text).strip()
    return text if text.startswith("<") else None


def fix_xml_tags(xml_str):
    xml_str = re.sub(r'<([A-Za-z][A-Za-z0-9 ]*)>',
                     lambda m: f'<{m.group(1).replace(" ", "_")}>', xml_str)
    xml_str = re.sub(r'</([A-Za-z][A-Za-z0-9 ]*)>',
                     lambda m: f'</{m.group(1).replace(" ", "_")}>', xml_str)
    return xml_str


def walk_element(element, prefix):
    path = f"{prefix}.{element.tag}"
    children = list(element)
    if not children:
        text = unquote((element.text or "").strip())
        if text:
            yield path, text
    else:
        for child in children:
            yield from walk_element(child, path)


def parse_blob(blob_tag, xml_str):
    results = []
    xml_clean = re.sub(r'<!DOCTYPE[^>]*>', '', xml_str)
    xml_clean = fix_xml_tags(xml_clean)
    def _keep(path):
        if ".ScanParameter." in path:
            return path.rsplit(".", 1)[-1] in SCANPARAM_KEEP
        return not any(pat in path for pat in BLOB_IGNORE)

    try:
        root = ET.fromstring(xml_clean)
        for path, val in walk_element(root, blob_tag):
            if _keep(path):
                results.append((path, val))
    except ET.ParseError:
        for m in re.finditer(r'<([A-Za-z0-9_]+)>([^<]+)</\1>', xml_str):
            val = unquote(m.group(2).strip())
            path = f"{blob_tag}.{m.group(1)}"
            if val and _keep(path):
                results.append((path, val))
    return results


def get_file_type(all_tags):
    for k, v in all_tags.items():
        if "HDRScan" in k:
            return "HDRi" if str(v) == "Yes" else "HDR"
    return "TIFF"


def get_scan_name(all_tags, blob_lines):
    for key, val in blob_lines:
        if key.endswith(".ScanParameter.Name"):
            return val
    stem = all_tags.get("System:FileName", "")
    return os.path.splitext(stem)[0] if stem else ""


def parse_existing_sidecar(sidecar_path):
    result = {"image_hash": "", "scan_name": "", "file_type": "",
              "name_history": [], "derived": [], "last_tags": []}
    if not os.path.exists(sidecar_path):
        return result
    with open(sidecar_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'\*\*ImageHash\*\*:\s*`?([0-9a-f]+)`?', content)
    if m: result["image_hash"] = m.group(1)
    m = re.search(r'\*\*OriginalScanName\*\*:\s*(.+)', content)
    if m: result["scan_name"] = m.group(1).strip()
    m = re.search(r'\*\*OriginalFileType\*\*:\s*(.+)', content)
    if m: result["file_type"] = m.group(1).strip()
    for m in re.finditer(r'^\|\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*\|\s*([^|]+?)\s*\|$', content, re.MULTILINE):
        ts, val = m.group(1).strip(), m.group(2).strip()
        if re.match(r'[0-9a-f]{32}', val):
            continue  # derived row handled below
        result["name_history"].append((ts, val))
    for m in re.finditer(r'^\|\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*\|\s*([0-9a-f]{32})\s*\|\s*(.+?)\s*\|$', content, re.MULTILINE):
        result["derived"].append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    m = re.search(r'## Current Tag State\n+```text\n(.*?)```', content, re.DOTALL)
    if m:
        result["last_tags"] = [l for l in m.group(1).strip().splitlines() if l.strip()]
    else:
        # fallback: old format — last text block
        blocks = re.findall(r'```text\n(.*?)```', content, re.DOTALL)
        if blocks:
            result["last_tags"] = [l for l in blocks[-1].strip().splitlines() if l.strip()]
    return result


def parse_existing_snapshots(sidecar_path):
    if not os.path.exists(sidecar_path):
        return []
    with open(sidecar_path, "r", encoding="utf-8") as f:
        content = f.read()
    snapshots = []
    for m in re.finditer(r'## Tag Snapshot — (.+?)\n```(text|diff)\n(.*?)```', content, re.DOTALL):
        ts    = m.group(1).strip()
        fence = m.group(2).strip()
        tags  = [l for l in m.group(3).strip().splitlines() if l.strip()]
        snapshots.append((ts, tags, fence))
    return snapshots


def build_md(image_hash, scan_name, file_type, file_name, file_date, file_bytes, name_history, derived, snapshots, current_tag_lines):
    lines = ["# TT Image Record\n",
             "## Identity\n",
             f"- **ImageHash**: `{image_hash}`",
             f"- **FileName**: {file_name}",
             f"- **FileDate**: {file_date}",
             f"- **FileBytes**: {file_bytes:,}",
             f"- **OriginalScanName**: {scan_name}",
             f"- **OriginalFileType**: {file_type}",
             "",
             "## Name History\n",
             "| Timestamp           | Path |",
             "|---------------------|------|"]
    for ts, path in name_history:
        lines.append(f"| {ts} | {path} |")
    lines += ["",
              "## Derived Files\n",
              "| Timestamp           | ImageHash                        | Path |",
              "|---------------------|----------------------------------|------|"]
    for ts, h, path in derived:
        lines.append(f"| {ts} | {h} | {path} |")
    lines.append("")
    for ts, snap_lines, fence in snapshots:
        lines.append(f"## Tag Snapshot — {ts}\n")
        lines.append(f"```{fence}")
        lines.extend(snap_lines)
        lines.append("```")
        lines.append("")
    if snapshots:
        lines.append("")
    lines.append("## Current Tag State\n")
    lines.append("```text")
    lines.extend(current_tag_lines)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main(filepath):
    filepath = os.path.abspath(filepath)
    sidecar  = filepath + ".md"
    now_ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{'='*60}")
    print(f"Source : {os.path.basename(filepath)}")
    print(f"Sidecar: {os.path.basename(sidecar)}")

    print("\n  Getting image hash...")
    image_hash = get_image_hash(filepath)
    print(f"  Hash: {image_hash}")

    print("\n  Reading all tags...")
    all_tags = get_all_tags(filepath)
    print(f"  Found {len(all_tags)} tags")

    tag_lines = []
    for key, val in all_tags.items():
        if key == "SourceFile" or key in BLOB_TAGS:
            continue
        val_str = "; ".join(str(v) for v in val) if isinstance(val, list) else str(val)
        if val_str.startswith("(Binary data"):
            continue
        if "MaskList" in key:
            m = re.search(r'<!--\s*File created on\s+([^-]+)-->', val_str)
            val_str = f"File created on {m.group(1).strip()}" if m else "(empty)"
        tag_lines.append(f"{key}: {val_str}")

    all_blob_lines = []
    for blob_tag in BLOB_TAGS:
        if blob_tag not in all_tags:
            continue
        xml_str = get_blob(filepath, blob_tag)
        if not xml_str:
            continue
        print(f"\n  Parsing blob: {blob_tag} ({len(xml_str)} chars)...")
        blob_lines = parse_blob(blob_tag, xml_str)
        print(f"  Extracted {len(blob_lines)} fields")
        for key, val in blob_lines:
            tag_lines.append(f"{key}: {val}")
        all_blob_lines.extend(blob_lines)

    tag_lines.sort()

    file_type = get_file_type(all_tags)
    scan_name = get_scan_name(all_tags, all_blob_lines)

    existing  = parse_existing_sidecar(sidecar)
    final_hash = existing["image_hash"] or image_hash
    final_scan = existing["scan_name"] or scan_name

    name_history = existing["name_history"]
    if not name_history or name_history[-1][1] != filepath:
        name_history.append((now_ts, filepath))

    derived   = existing["derived"]
    snapshots = parse_existing_snapshots(sidecar)

    prev_tags = existing["last_tags"]
    is_new = not prev_tags
    if not is_new and set(prev_tags) != set(tag_lines):
        prev_map = {line.partition(": ")[0]: line for line in prev_tags}
        curr_map = {line.partition(": ")[0]: line for line in tag_lines}
        diff_lines = []
        for k in sorted(set(prev_map) | set(curr_map)):
            if k in prev_map and k not in curr_map:
                diff_lines.append(f"- {prev_map[k]}")
            elif k not in prev_map and k in curr_map:
                diff_lines.append(f"+ {curr_map[k]}")
            elif prev_map[k] != curr_map[k]:
                diff_lines.append(f"- {prev_map[k]}")
                diff_lines.append(f"+ {curr_map[k]}")
        snapshots.append((now_ts, diff_lines, "diff"))
        print(f"\n  Tags changed — appending diff snapshot ({len(diff_lines)} changed lines)")
    elif is_new:
        print(f"\n  New file — writing Current Tag State (no snapshot)")
    else:
        print(f"\n  Tags unchanged — no new snapshot")

    def _parse_dt(s):
        try:
            return datetime.datetime.fromisoformat(s.replace(':', '-', 2))
        except Exception:
            return datetime.datetime.min
    create_dt = _parse_dt(str(all_tags.get("System:FileCreateDate", "")))
    modify_dt = _parse_dt(str(all_tags.get("System:FileModifyDate", "")))
    file_date = str(all_tags.get("System:FileCreateDate" if create_dt >= modify_dt else "System:FileModifyDate", ""))
    file_bytes = os.path.getsize(filepath)

    md = build_md(final_hash, final_scan, file_type, os.path.basename(filepath), file_date, file_bytes, name_history, derived, snapshots, tag_lines)
    with open(sidecar, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"  Snapshots: {len(snapshots)}, Name history: {len(name_history)} entries")
    print(f"\nDone: {sidecar}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
