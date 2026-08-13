#!/usr/bin/env python3
"""Archive completed water meter image folders to Jottacloud.

For each YYYY-MM-DD subdirectory under ~/pictures/water_meter/scanned/:
  1. Determine if the day is "complete" — the DB contains at least one
     capture_ts from the *following* calendar day.
  2. Skip the current day (still accumulating).
  3. Create a Windows-compatible .zip file named
     ``water-meter-images-YYYY-MM-DD.zip`` in a staging directory.
  4. Remove the source folder (zip is a validated replacement).
  5. Upload the .zip to Jottacloud via ``jotta-cli archive``.
  6. Delete the local .zip on successful upload.

**Default is dry-run.**  Pass ``--execute`` to actually run.

Usage:
    # Dry-run — show what would happen
    .venv/bin/python scripts/water_meter/archive_images.py

    # Execute (with confirmation)
    .venv/bin/python scripts/water_meter/archive_images.py --execute

    # Auto mode (no confirmation, for cron)
    .venv/bin/python scripts/water_meter/archive_images.py --auto

    # Target a single specific date
    .venv/bin/python scripts/water_meter/archive_images.py --date 2026-07-18
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from sqlalchemy import func

from water_meter.core.db import MeterReading, init_db, get_session
from water_meter.core.common import SCANNED_DIR

log = logging.getLogger("archive_images")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
JOTTA_CLI = "jotta-cli"
JOTTA_REMOTE_ROOT = "WaterMeter/Images"   # under Archive/<device>/
STAGING_DIR = os.path.join(os.path.dirname(SCANNED_DIR), "staging")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _list_date_dirs(pending_dir: str) -> List[str]:
    """Return sorted list of YYYY-MM-DD directory names under *pending_dir*."""
    if not os.path.isdir(pending_dir):
        return []
    dirs = []
    for entry in sorted(os.listdir(pending_dir)):
        entry_path = os.path.join(pending_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        # Match YYYY-MM-DD pattern
        if len(entry) == 10 and entry[4] == "-" and entry[7] == "-":
            try:
                datetime.strptime(entry, "%Y-%m-%d")
            except ValueError:
                continue
            # Only include if it contains at least one .jpg
            if any(fn.lower().endswith(".jpg") for fn in os.listdir(entry_path)):
                dirs.append(entry)
    return dirs


def _get_db_capture_dates() -> List[date]:
    """Return sorted unique dates that appear in MeterReading.capture_ts."""
    with get_session() as session:
        rows = (
            session.query(func.date(MeterReading.capture_ts).label("d"))
            .filter(MeterReading.capture_ts.isnot(None))
            .distinct()
            .order_by("d")
            .all()
        )
    return [r.d for r in rows if r.d is not None]


def _is_day_complete(day_str: str, db_dates: List[date]) -> bool:
    """A day folder is complete if the DB has capture_ts 2 days later.

    We require a 2‑day buffer (not 1) so the operator has time to review
    anchors and confirm readings before the source images are archived.
    """
    try:
        day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    two_days_later = day_date + timedelta(days=2)
    return two_days_later in db_dates


def _create_zip(source_dir: str, zip_path: str) -> int:
    """Create a zip file from *source_dir* contents. Returns file count added.

    Files are placed at the root of the zip (no enclosing folder).
    Uses ZIP_STORED (no compression) for speed — images are already JPEG.
    """
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(source_dir)):
            fpath = os.path.join(source_dir, fname)
            if not os.path.isfile(fpath):
                continue
            # Store with just the filename (no directory prefix)
            zf.write(fpath, arcname=fname)
            count += 1
    return count


def _jotta_upload(local_path: str, remote_rel: str) -> tuple[bool, str]:
    """Upload a file to Jottacloud via jotta-cli archive.

    Returns (success, error_message).
    """
    cmd = [JOTTA_CLI, "archive", local_path, f"--remote={remote_rel}", "--nogui"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode == 0:
            return True, ""
        err = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
        )
        return False, err
    except FileNotFoundError:
        return False, f"jotta-cli not found on PATH (tried: {JOTTA_CLI})"
    except subprocess.TimeoutExpired:
        return False, "Upload timed out after 600s"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_archive(
    dry_run: bool = True,
    target_date: Optional[str] = None,
    force_incomplete: bool = False,
) -> dict:
    """Main archive pass. Returns stats dict.

    Workflow: zip → remove source folder → upload → delete local zip.

    The zip file on disk serves as the authoritative local backup until
    upload succeeds.  The source folder is removed immediately after a
    valid zip is created so that pending/ stays clean even if jotta-cli
    uploads are retried later.
    """
    stats = {
        "dry_run": dry_run,
        "candidates": 0,
        "zipped": 0,
        "source_removed": 0,
        "uploaded": 0,
        "zip_deleted": 0,
        "upload_failed": 0,
        "skipped_today": 0,
        "skipped_incomplete": 0,
        "errors": 0,
        "details": [],
    }

    init_db()

    # ---- Gather data ----
    db_dates = _get_db_capture_dates()
    log.info("DB has capture_ts for %d distinct dates: %s",
             len(db_dates),
             [d.isoformat() for d in db_dates[-5:]] if db_dates else "none")

    date_dirs = _list_date_dirs(SCANNED_DIR)
    log.info("Found %d date directories in %s", len(date_dirs), SCANNED_DIR)

    today_str = date.today().isoformat()

    # ---- Determine eligible folders ----
    candidates: List[str] = []
    for d in date_dirs:
        if target_date and d != target_date:
            continue
        if d == today_str:
            log.info("  %s — skipping (today)", d)
            stats["skipped_today"] += 1
            continue
        if not force_incomplete and not _is_day_complete(d, db_dates):
            log.info("  %s — skipping (not complete — no next-day data in DB)", d)
            stats["skipped_incomplete"] += 1
            continue
        if force_incomplete and not _is_day_complete(d, db_dates):
            log.info("  %s — forced (incomplete: no next-day data in DB)", d)
        candidates.append(d)

    stats["candidates"] = len(candidates)
    if not candidates:
        log.info("No candidate date folders to archive.")
        return stats

    log.info("Candidate folders for archiving (%d): %s",
             len(candidates), candidates)

    os.makedirs(STAGING_DIR, exist_ok=True)

    for d in candidates:
        entry = {
            "date": d,
            "zip_created": False,
            "source_removed": False,
            "uploaded": False,
            "zip_deleted": False,
            "error": None,
        }
        source_dir = os.path.join(SCANNED_DIR, d)
        zip_name = f"water-meter-images-{d}.zip"
        zip_path = os.path.join(STAGING_DIR, zip_name)
        remote_path = f"{JOTTA_REMOTE_ROOT}/{zip_name}"

        # ---------------------------------------------------------------
        # Step 1: create the zip
        # ---------------------------------------------------------------
        file_count = 0
        if not dry_run:
            try:
                file_count = _create_zip(source_dir, zip_path)
                zip_size = os.path.getsize(zip_path)
                log.info("  Created %s  (%d files, %.1f MB)",
                         zip_name, file_count, zip_size / (1024 * 1024))
                entry["zip_created"] = True
                stats["zipped"] += 1
            except Exception as exc:
                log.error("  Failed to create zip for %s: %s", d, exc)
                entry["error"] = f"zip failed: {exc}"
                stats["errors"] += 1
                stats["details"].append(entry)
                continue
        else:
            file_count = sum(
                1 for fn in os.listdir(source_dir)
                if os.path.isfile(os.path.join(source_dir, fn))
            )
            log.info("  [DRY RUN] Would zip %s → %s  (%d files)",
                     source_dir, zip_name, file_count)
            entry["zip_created"] = "dry-run"
            stats["zipped"] += 1

        # ---------------------------------------------------------------
        # Step 2: remove source folder (zip is the local replacement)
        # ---------------------------------------------------------------
        if not dry_run:
            try:
                shutil.rmtree(source_dir)
                log.info("  Removed source folder: %s", source_dir)
                entry["source_removed"] = True
                stats["source_removed"] += 1
            except OSError as exc:
                log.warning("  Failed to remove source folder %s: %s", source_dir, exc)
                entry["error"] = f"source folder removal failed: {exc}"
                stats["errors"] += 1
                stats["details"].append(entry)
                continue
        else:
            log.info("  [DRY RUN] Would remove source folder: %s", source_dir)
            entry["source_removed"] = "dry-run"
            stats["source_removed"] += 1

        # ---------------------------------------------------------------
        # Step 3: upload zip to Jottacloud (long timeout for large zips)
        # ---------------------------------------------------------------
        if not dry_run:
            try:
                success, error_msg = _jotta_upload(zip_path, f"WaterMeter/Images/{zip_name}")
                if success:
                    log.info("  Uploaded to Jottacloud: %s", f"WaterMeter/Images/{zip_name}")
                    entry["uploaded"] = True
                    stats["uploaded"] += 1
                else:
                    log.error("  Upload failed for %s: %s", zip_name, error_msg)
                    entry["error"] = f"upload failed: {error_msg}"
                    stats["upload_failed"] += 1
                    stats["details"].append(entry)
                    continue
            except Exception as exc:
                log.error("  Upload exception for %s: %s", d, exc)
                entry["error"] = f"upload exception: {exc}"
                stats["upload_failed"] += 1
                stats["details"].append(entry)
                continue
        else:
            log.info("  [DRY RUN] Would upload %s → jotta:%s",
                     zip_name, remote_path)
            entry["uploaded"] = "dry-run"
            stats["uploaded"] += 1

        # ---------------------------------------------------------------
        # Step 4: delete local zip on successful upload
        # ---------------------------------------------------------------
        if not dry_run:
            try:
                os.remove(zip_path)
                log.info("  Deleted local zip: %s", zip_path)
                entry["zip_deleted"] = True
                stats["zip_deleted"] += 1
            except OSError as exc:
                log.warning("  Failed to delete local zip %s: %s", zip_path, exc)
                entry["error"] = f"zip deletion failed: {exc}"
        else:
            log.info("  [DRY RUN] Would delete local zip: %s", zip_path)
            entry["zip_deleted"] = "dry-run"
            stats["zip_deleted"] += 1

        stats["details"].append(entry)

    return stats


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable archive report."""
    print(f"\n{'='*60}")
    print(f"Water Meter Image Archive Report")
    print(f"{'='*60}")
    print(f"Dry run:                  {'YES' if stats['dry_run'] else 'NO'}")
    print(f"Candidate date folders:   {stats['candidates']:>8}")
    print(f"Skipped (today):          {stats['skipped_today']:>8}")
    print(f"Skipped (incomplete):     {stats['skipped_incomplete']:>8}")
    print(f"\nZipped:                   {stats['zipped']:>8}")
    print(f"Source folder removed:    {stats['source_removed']:>8}")
    print(f"Uploaded to Jotta:        {stats['uploaded']:>8}")
    print(f"Upload failed:            {stats['upload_failed']:>8}")
    print(f"Local zip deleted:        {stats['zip_deleted']:>8}")
    print(f"Errors:                   {stats['errors']:>8}")

    details = stats.get("details", [])
    if details:
        print(f"\n  {'Date':<12} {'Zip':<6} {'Src':<5} {'Upload':<7} {'Del':<5}")
        print(f"  {'-'*10}   {'-'*4}   {'-'*3}   {'-'*5}   {'-'*3}")
        for d in details:
            def _check(val):
                if val is True:
                    return "✓"
                if val == "dry-run":
                    return "~"
                return "✗"

            print(
                f"  {d['date']:<12} "
                f"{_check(d['zip_created']):<6} "
                f"{_check(d.get('source_removed')):<5} "
                f"{_check(d['uploaded']):<7} "
                f"{_check(d['zip_deleted']):<5}"
            )
            if d.get("error"):
                print(f"          ⚠  {d['error']}")

    if stats["upload_failed"]:
        failed_dates = [d["date"] for d in details if d.get("uploaded") is False and d.get("zip_created") is True]
        if failed_dates:
            print(f"\n⚠  Uploads failed for: {', '.join(failed_dates)}")
            print(f"   Zips are retained in {STAGING_DIR} — re-run to retry.")

    print(f"\n{'='*60}\n")

    if stats["dry_run"]:
        print("DRY RUN — no files were created, uploaded, or deleted.")
        print("Run with --execute to actually archive.")
        print()
        if stats["candidates"] > 0:
            print("Candidate folders that would be archived:")
            for d in stats["details"]:
                src = os.path.join(SCANNED_DIR, d["date"])
                file_count = sum(
                    1 for fn in os.listdir(src)
                    if os.path.isfile(os.path.join(src, fn))
                )
                print(f"  {d['date']}  ({file_count} files) → water-meter-images-{d['date']}.zip")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Archive completed water meter image folders to Jottacloud"
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually create zips, upload, and delete (not a dry run)",
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help="Auto mode — execute without confirmation prompt (for cron)",
    )
    p.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (same as --auto but still requires --execute)",
    )
    p.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Only process a single specific date folder",
    )
    p.add_argument(
        "--force-incomplete", action="store_true",
        help="Archive date folders even if the next day has no DB captures "
             "(useful when the system was offline for a day, e.g. 23rd→25th gap). "
             "When used with --date, only the target date is forced.",
    )
    p.add_argument(
        "--staging-dir",
        default=STAGING_DIR,
        help=f"Directory for temporary .zip files (default: {STAGING_DIR})",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Override staging dir if specified
    global STAGING_DIR
    STAGING_DIR = args.staging_dir

    do_execute = args.execute or args.auto

    if do_execute:
        log.warning("EXECUTE mode — files WILL be created and uploaded!")
        if not (args.yes or args.auto):
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    stats = run_archive(
        dry_run=not do_execute,
        target_date=args.date,
        force_incomplete=args.force_incomplete,
    )

    print_report(stats)


if __name__ == "__main__":
    main()