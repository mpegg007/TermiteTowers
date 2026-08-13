#!/usr/bin/env python3
"""Cleanup processor for water meter pipeline.

Implements a tiered retention policy to prevent unbounded image accumulation:

  Tier 1 — NEVER delete:
    - Manual corrections (odo_confidence == 1.0)
    - Transition-zone frames (preserve="transition" in notes)
    - Run anchors (run_position = "first" or "last" in notes)
    - Anomalies (status = "ANOMALY")
    - Failures (status = "FAIL")

  Tier 2 — Delete ALL non-protected odo crops (keep DB row):
    - Crops are disposable intermediate artifacts
    - Source images are archived on Jottacloud; crops can be regenerated

  Tier 3 — Delete source image (confidence ≥ PURGE_SOURCE_CONF_MIN):
    - Non-protected high-confidence frames whose source is already archived

  Tier 4 — Sweep:
    - Empty date subdirectories in pending/, scanned/, proc/
    - Debug images older than DEBUG_TTL_DAYS (default 7 days)

**Default is read-only (--dry-run).**  Pass ``--execute`` to actually delete.

Usage:
    # Report only (safe)
    .venv/bin/python scripts/water_meter/cleanup.py

    # Report with custom thresholds
    .venv/bin/python scripts/water_meter/cleanup.py --min-conf 0.85 --debug-ttl 14

    # Auto mode (cron-friendly, no confirmation)
    .venv/bin/python scripts/water_meter/cleanup.py --auto

    # Execute with confirmation
    .venv/bin/python scripts/water_meter/cleanup.py --execute --yes
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, init_db, get_session, _Session
from water_meter.core.common import (
    IMAGE_DIR, PENDING_DIR, SCANNED_DIR, PROC_DIR, DEBUG_DIR,
)

log = logging.getLogger("cleanup")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PURGE_SOURCE_CONF_MIN = 0.90    # minimum odo_confidence to delete source image
DEBUG_TTL_DAYS = 7              # delete debug images older than this


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_notes(notes_str: str | None) -> dict:
    """Parse JSON notes from a DB row. Returns empty dict on failure."""
    if not notes_str:
        return {}
    try:
        return json.loads(notes_str) if isinstance(notes_str, str) else notes_str
    except (json.JSONDecodeError, TypeError):
        return {}


def _is_protected(row: MeterReading) -> bool:
    """Return True if this row must NEVER have files deleted."""
    # Manual correction
    if row.odo_confidence == 1.0:
        return True

    # Anomaly or failure
    if row.status in ("ANOMALY", "FAIL"):
        return True

    # Transition-zone frame
    notes = _parse_notes(row.notes)
    if notes.get("preserve") == "transition":
        return True

    # Important image flagged by flag_important.py
    if notes.get("preserve") == "important":
        return True

    # Run anchor (first or last)
    if notes.get("run_position") in ("first", "last"):
        return True

    return False


def _find_file(base_dir: str, filename: str) -> Optional[str]:
    """Search recursively for filename within base_dir. Returns full path or None."""
    pattern = os.path.join(base_dir, "**", filename)
    matches = glob.glob(pattern, recursive=True)
    return matches[0] if matches else None


def _rm_empty_date_dirs(base_dir: str, dry_run: bool) -> int:
    """Remove empty YYYY-MM-DD subdirectories. Returns count removed."""
    removed = 0
    if not os.path.isdir(base_dir):
        return 0
    for entry in sorted(os.listdir(base_dir)):
        path = os.path.join(base_dir, entry)
        if not os.path.isdir(path):
            continue
        # Only touch YYYY-MM-DD date dirs
        if len(entry) != 10 or entry[4] != "-" or entry[7] != "-":
            continue
        try:
            contents = os.listdir(path)
        except PermissionError:
            continue
        if not contents:
            if not dry_run:
                try:
                    os.rmdir(path)
                    log.info("  Removed empty dir: %s", path)
                except OSError as e:
                    log.warning("  Failed to remove dir %s: %s", path, e)
            removed += 1
    return removed


def _rm_old_debug(dry_run: bool, ttl_days: int = DEBUG_TTL_DAYS) -> int:
    """Delete debug/*.jpg files older than ttl_days. Returns count removed."""
    removed = 0
    if not os.path.isdir(DEBUG_DIR):
        return 0
    cutoff = time.time() - (ttl_days * 86400)
    for fn in os.listdir(DEBUG_DIR):
        fp = os.path.join(DEBUG_DIR, fn)
        if not os.path.isfile(fp):
            continue
        try:
            mtime = os.path.getmtime(fp)
        except OSError:
            continue
        if mtime < cutoff:
            if not dry_run:
                try:
                    os.remove(fp)
                    log.debug("  Removed old debug: %s", fn)
                except OSError as e:
                    log.warning("  Failed to remove debug %s: %s", fn, e)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Tiered cleanup logic
# ---------------------------------------------------------------------------

def run_cleanup(
    min_source_conf: float = PURGE_SOURCE_CONF_MIN,
    debug_ttl_days: int = DEBUG_TTL_DAYS,
    dry_run: bool = True,
) -> dict:
    """Execute the full tiered cleanup pass.

    Returns stats dict.
    """
    stats = {
        "total_rows": 0,
        "protected": 0,
        "source_deleted": 0,
        "odo_crop_deleted": 0,
        "empty_dirs_removed": 0,
        "debug_deleted": 0,
        "dry_run": dry_run,
    }

    # --- Load all rows (keep session alive for attribute access) ---
    session = _Session()
    try:
        all_rows = (
            session.query(MeterReading)
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

        stats["total_rows"] = len(all_rows)
        if not all_rows:
            log.info("No rows in DB.")
            return stats

        log.info("Scanning %d rows...", len(all_rows))

        for row in all_rows:
            if _is_protected(row):
                stats["protected"] += 1
                continue

            confidence = row.odo_confidence or 0

            # Tier 2: delete ALL non-protected odo crops that have been decoded
            # Only delete crops where odo_confidence is set — crops without a
            # decode result still need to be processed by decode_odo first.
            # Source images are archived on Jottacloud and can regenerate crops.
            if row.odo_crop_file and row.odo_confidence is not None:
                crop_path = os.path.join(PROC_DIR, row.odo_crop_file)
                alt_path = os.path.join(PROC_DIR, os.path.basename(row.odo_crop_file))
                for cp in (crop_path, alt_path):
                    if os.path.isfile(cp):
                        if not dry_run:
                            try:
                                os.remove(cp)
                            except OSError as e:
                                log.warning("  Failed to delete odo crop %s: %s",
                                            cp, e)
                        stats["odo_crop_deleted"] += 1

            # Tier 3: delete source image for high-confidence non-protected frames
            if confidence >= min_source_conf and row.hub_x is not None:
                src_path = _find_file(SCANNED_DIR, row.image_name)
                if not src_path:
                    src_path = _find_file(PENDING_DIR, row.image_name)
                if not src_path:
                    src_path = os.path.join(IMAGE_DIR, row.image_name)

                if src_path and os.path.isfile(src_path):
                    if not dry_run:
                        try:
                            os.remove(src_path)
                            log.debug("  Deleted source: %s", src_path)
                        except OSError as e:
                            log.warning("  Failed to delete source %s: %s",
                                        src_path, e)
                    stats["source_deleted"] += 1
    finally:
        session.close()

    log.info("Protected: %d  Source deleted: %d  Odo crop deleted: %d",
             stats["protected"], stats["source_deleted"],
             stats["odo_crop_deleted"])

    # --- Sweep empty date directories ---
    for base_dir in (PENDING_DIR, SCANNED_DIR, PROC_DIR):
        removed = _rm_empty_date_dirs(base_dir, dry_run)
        stats["empty_dirs_removed"] += removed
        if removed:
            log.info("  Removed %d empty dirs from %s", removed,
                     os.path.basename(base_dir))

    # --- Sweep old debug images ---
    stats["debug_deleted"] = _rm_old_debug(dry_run, debug_ttl_days)
    if stats["debug_deleted"]:
        log.info("  Removed %d old debug files (>%d days)",
                 stats["debug_deleted"], debug_ttl_days)

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable cleanup report."""
    print(f"\n{'='*60}")
    print(f"Water Meter Cleanup Report")
    print(f"{'='*60}")
    print(f"Total DB rows:           {stats['total_rows']:>8}")
    print(f"Protected (never delete): {stats['protected']:>8}")
    print(f"\nFile deletions:")
    print(f"  Source images:         {stats['source_deleted']:>8}")
    print(f"  Odo crops:             {stats['odo_crop_deleted']:>8}")
    print(f"  Debug files:           {stats['debug_deleted']:>8}")
    print(f"\nDirectory cleanup:")
    print(f"  Empty dirs removed:    {stats['empty_dirs_removed']:>8}")

    if stats['dry_run']:
        print(f"\nDRY RUN — no files or directories were actually deleted.")
        print(f"Run with --execute to apply changes.")
    else:
        total = (stats['source_deleted'] + stats['odo_crop_deleted'] +
                 stats['debug_deleted'] + stats['empty_dirs_removed'])
        print(f"\n  Total items removed: {total}")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Quick pre-flight: estimate how many files would be deleted
# ---------------------------------------------------------------------------

def estimate_deletions(
    min_source_conf: float = PURGE_SOURCE_CONF_MIN,
) -> dict:
    """Quick estimate without loading all rows — just count candidates."""
    with get_session() as session:
        total = session.query(MeterReading).count()
        manual = session.query(MeterReading).filter(
            MeterReading.odo_confidence == 1.0).count()
        anomaly = session.query(MeterReading).filter(
            MeterReading.status == "ANOMALY").count()
        fail = session.query(MeterReading).filter(
            MeterReading.status == "FAIL").count()

        # High-confidence non-protected candidates for source deletion
        source_candidates = session.query(MeterReading).filter(
            MeterReading.odo_confidence >= min_source_conf,
            MeterReading.hub_x.isnot(None),
        ).count()

    # Count images on disk
    pending_count = sum(1 for _ in glob.glob(
        os.path.join(PENDING_DIR, "**", "water_meter_*.jpg"), recursive=True))
    scanned_count = sum(1 for _ in glob.glob(
        os.path.join(SCANNED_DIR, "**", "water_meter_*.jpg"), recursive=True))
    proc_count = sum(1 for _ in glob.glob(
        os.path.join(PROC_DIR, "**", "odo_*.jpg"), recursive=True))
    debug_count = len([f for f in os.listdir(DEBUG_DIR)
                       if os.path.isfile(os.path.join(DEBUG_DIR, f))]) \
        if os.path.isdir(DEBUG_DIR) else 0

    return {
        "db_total": total, "db_manual": manual, "db_anomaly": anomaly,
        "db_fail": fail, "db_source_candidates": source_candidates,
        "disk_pending_jpg": pending_count,
        "disk_scanned_jpg": scanned_count,
        "disk_proc_jpg": proc_count,
        "disk_debug_jpg": debug_count,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Water meter cleanup — tiered retention policy")
    p.add_argument("--min-conf", type=float, default=PURGE_SOURCE_CONF_MIN,
                   help=f"Min confidence for source deletion (default: {PURGE_SOURCE_CONF_MIN})")
    p.add_argument("--debug-ttl", type=int, default=DEBUG_TTL_DAYS,
                   help=f"Max age in days for debug images (default: {DEBUG_TTL_DAYS})")
    p.add_argument("--execute", action="store_true",
                   help="Actually delete files (DESTRUCTIVE)")
    p.add_argument("--auto", action="store_true",
                   help="Auto mode — execute without confirmation (for cron)")
    p.add_argument("--yes", "-y", action="store_true",
                   help="Skip confirmation prompt")
    p.add_argument("--estimate", action="store_true",
                   help="Quick estimate only — show DB + disk counts")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    # Quick estimate mode
    if args.estimate:
        est = estimate_deletions(args.min_conf)
        print(f"\n{'='*60}")
        print(f"Water Meter Storage Estimate")
        print(f"{'='*60}")
        print(f"DB rows:")
        print(f"  Total:                 {est['db_total']:>8}")
        print(f"  Manual corrections:    {est['db_manual']:>8}")
        print(f"  Anomalies:             {est['db_anomaly']:>8}")
        print(f"  Failures:              {est['db_fail']:>8}")
        print(f"  Source candidates:     {est['db_source_candidates']:>8}")
        print(f"\nDisk files:")
        print(f"  pending/*.jpg:         {est['disk_pending_jpg']:>8}")
        print(f"  scanned/*.jpg:         {est['disk_scanned_jpg']:>8}")
        print(f"  proc/odo_*.jpg:        {est['disk_proc_jpg']:>8}")
        print(f"  debug/*.jpg:           {est['disk_debug_jpg']:>8}")
        print(f"{'='*60}\n")
        return

    do_execute = args.execute or args.auto

    if do_execute:
        log.warning("EXECUTE mode — files WILL be deleted!")
        if not (args.yes or args.auto):
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    # Show pre-flight estimate before executing
    est = estimate_deletions(args.min_conf)
    log.info("Pre-flight: %d DB rows, %d pending jpg, %d scanned jpg, %d proc jpg, %d debug jpg",
             est['db_total'], est['disk_pending_jpg'], est['disk_scanned_jpg'],
             est['disk_proc_jpg'], est['disk_debug_jpg'])

    stats = run_cleanup(
        min_source_conf=args.min_conf,
        debug_ttl_days=args.debug_ttl,
        dry_run=not do_execute,
    )

    print_report(stats)

    if not do_execute:
        print("DRY RUN — no files were deleted.")
        print("Run with --execute or --auto to actually clean up.")


if __name__ == "__main__":
    main()