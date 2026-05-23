#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/scan_photoarchive.py:139 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 205415e0924affc676fd9277380b38a9e69e1041 %
#  %ccm_git_commit_id: 082ff38c260cbc5b6c247b8ea6097056d609d69a %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-05-23 16:09:44 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: image tagging phase 1 %
#  %ccm_git_modify_date: 2026-05-23 16:09:54 %
#  %ccm_git_file_last_modified: 2026-05-23 16:09:54 %
#  %ccm_git_file_name: scan_photoarchive.py %
#  %ccm_git_path: media/scan_photoarchive.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 2525 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
scan_photoarchive.py

Scan a PhotoArchive folder recursively and run extract_to_sidecar.py for every
image that either:
  - has no sidecar .md file yet, OR
  - has an image modify timestamp newer than the existing .md file

Usage:
    python scan_photoarchive.py [<archive_root>]

Defaults to ARCHIVE_ROOT below if no argument is supplied.
"""

import os
import sys
import subprocess
import datetime

ARCHIVE_ROOT = r"C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"
SIDECAR_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_to_sidecar.py")
IMAGE_EXTS = {".tif", ".tiff", ".jpg", ".jpeg"}


def needs_update(img_path):
    md_path = img_path + ".md"
    if not os.path.exists(md_path):
        return True, "no sidecar"
    img_mtime = os.path.getmtime(img_path)
    md_mtime  = os.path.getmtime(md_path)
    if img_mtime > md_mtime:
        delta = datetime.datetime.fromtimestamp(img_mtime) - datetime.datetime.fromtimestamp(md_mtime)
        return True, f"image newer by {delta}"
    return False, "up to date"


def main(archive_root):
    images = []
    for dirpath, _, filenames in os.walk(archive_root):
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() in IMAGE_EXTS:
                images.append(os.path.join(dirpath, fname))
    images.sort()

    total    = len(images)
    to_run   = []
    skipped  = 0

    print(f"Scanning {archive_root}")
    print(f"Found {total} image(s)\n")

    for img in images:
        update, reason = needs_update(img)
        rel = os.path.relpath(img, archive_root)
        if update:
            to_run.append((img, reason))
            print(f"  [QUEUE] {rel}  ({reason})")
        else:
            skipped += 1

    print(f"\n{len(to_run)} to process, {skipped} up to date\n{'='*60}")

    errors = []
    for i, (img, reason) in enumerate(to_run, 1):
        rel = os.path.relpath(img, archive_root)
        print(f"\n[{i}/{len(to_run)}] {rel}  ({reason})")
        result = subprocess.run(
            [sys.executable, SIDECAR_SCRIPT, img],
            capture_output=False
        )
        if result.returncode != 0:
            errors.append(img)

    print(f"\n{'='*60}")
    print(f"Done. Processed: {len(to_run)}, Skipped: {skipped}, Errors: {len(errors)}")
    if errors:
        print("\nFailed:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else ARCHIVE_ROOT
    main(root)
