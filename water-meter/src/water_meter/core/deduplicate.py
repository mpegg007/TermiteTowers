#!/usr/bin/env python3
"""Deduplicate water meter frames — identify runs of identical readings, tag
run groups in the DB, and report which middle frames are eligible for deletion.

A "run" is a contiguous sequence of frames (ordered by capture_ts) where ALL of:
  - needle_deg is within NEEDLE_DEG_TOLERANCE (±1.0°)
  - odo_reading is identical (no consumption)
  - npos is within NPOS_TOLERANCE (±2)

Frames in a run are classified as:
  - "first"  — bookend anchor (preserved)
  - "last"   — bookend anchor (preserved)
  - "middle" — eligible for deletion IF all conditions below are met
  - "transition" — transition-zone frame (NEVER deleted, even if middle)

A middle frame is eligible for deletion when:
  - NOT a manual correction (odo_confidence != 1.0)
  - NOT in transition zone (preserve != "transition" in notes)
  - NOT an anomaly (status != "ANOMALY")
  - NOT a FAIL
  - odo_confidence >= 0.85 (high confidence — DB row is sufficient)
  - The DB row has valid geometry (hub_x, needle_deg are not null)

Eligible middle frames have their source image and odo crop deleted.
Their DB rows remain as evidence.

Usage:
    # Dry run — report only
    .venv/bin/python scripts/water_meter/deduplicate.py

    # Dry run with custom tolerances
    .venv/bin/python scripts/water_meter/deduplicate.py --needle-tol 0.5 --npos-tol 1

    # Execute — tag DB + delete eligible files
    .venv/bin/python scripts/water_meter/deduplicate.py --execute --yes
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, init_db, get_session
from water_meter.core.common import (
    IMAGE_DIR, PENDING_DIR, SCANNED_DIR, PROC_DIR,
)

log = logging.getLogger("deduplicate")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
NEEDLE_DEG_TOLERANCE = 1.0    # ± degrees for "same needle position"
NPOS_TOLERANCE = 2            # ± npos units for "same position"
PURGE_CONF_MIN = 0.85         # minimum confidence for safe deletion


# ---------------------------------------------------------------------------
# Run detection
# ---------------------------------------------------------------------------

def _values_same(
    needle_deg_a: float | None, needle_deg_b: float | None,
    odo_reading_a: float | None, odo_reading_b: float | None,
    npos_a: int | None, npos_b: int | None,
    needle_tol: float = NEEDLE_DEG_TOLERANCE,
    npos_tol: int = NPOS_TOLERANCE,
) -> bool:
    """Return True if two frames have effectively identical readings."""
    if needle_deg_a is None or needle_deg_b is None:
        return False
    if odo_reading_a is None or odo_reading_b is None:
        return False
    if abs(needle_deg_a - needle_deg_b) > needle_tol:
        return False
    if odo_reading_a != odo_reading_b:
        return False
    if npos_a is not None and npos_b is not None:
        if abs(npos_a - npos_b) > npos_tol:
            return False
    return True


def _is_transition_preserved(notes_str: str | None) -> bool:
    """Check if a DB row's notes contain preserve='transition'."""
    if not notes_str:
        return False
    try:
        nd = json.loads(notes_str) if isinstance(notes_str, str) else notes_str
        return nd.get("preserve") == "transition"
    except (json.JSONDecodeError, TypeError):
        return False


def find_identical_runs(
    needle_tol: float = NEEDLE_DEG_TOLERANCE,
    npos_tol: int = NPOS_TOLERANCE,
) -> Tuple[List[List[MeterReading]], int, int]:
    """Scan all rows ordered by capture_ts and group into identical-reading runs.

    Returns (runs, total_rows, rows_in_runs).
    A "run" has 2+ consecutive frames with the same reading.
    """
    with get_session() as session:
        all_rows = (
            session.query(MeterReading)
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

    total = len(all_rows)
    if total < 2:
        return [], total, 0

    runs: List[List[MeterReading]] = []
    current_run: List[MeterReading] = [all_rows[0]]

    for i in range(1, total):
        prev = current_run[-1]
        curr = all_rows[i]

        if _values_same(
            prev.needle_deg, curr.needle_deg,
            prev.odo_reading, curr.odo_reading,
            prev.npos, curr.npos,
            needle_tol, npos_tol,
        ):
            current_run.append(curr)
        else:
            if len(current_run) >= 2:
                runs.append(current_run)
            current_run = [curr]

    # Don't forget the final run
    if len(current_run) >= 2:
        runs.append(current_run)

    rows_in_runs = sum(len(r) for r in runs)
    return runs, total, rows_in_runs


def classify_run_positions(
    run: List[MeterReading],
) -> Dict[str, MeterReading]:
    """Classify each row in a run as first/middle/last.

    Returns {image_name: position} mapping.
    Also returns the set of middle-row image_names eligible for deletion.
    """
    n = len(run)
    if n < 2:
        return {}, set()

    positions: Dict[str, str] = {}  # image_name → position
    eligible_for_delete: Set[str] = set()

    for i, row in enumerate(run):
        if i == 0:
            positions[row.image_name] = "first"
        elif i == n - 1:
            positions[row.image_name] = "last"
        else:
            positions[row.image_name] = "middle"

    # Determine which middle frames are eligible for deletion
    for row in run:
        if positions.get(row.image_name) != "middle":
            continue

        # Never delete manual corrections
        if row.odo_confidence == 1.0:
            continue

        # Never delete anomalies or failures
        if row.status in ("ANOMALY", "FAIL"):
            continue

        # Never delete transition-zone frames
        if _is_transition_preserved(row.notes):
            continue

        # Require high confidence and valid geometry
        if (row.odo_confidence is not None and
                row.odo_confidence >= PURGE_CONF_MIN and
                row.hub_x is not None and
                row.needle_deg is not None):
            eligible_for_delete.add(row.image_name)

    return positions, eligible_for_delete


# ---------------------------------------------------------------------------
# File location helpers
# ---------------------------------------------------------------------------

def _find_source_image(image_name: str) -> Optional[str]:
    """Search for the source image in pending/ or scanned/ subdirectories."""
    for base_dir in (PENDING_DIR, SCANNED_DIR):
        pattern = os.path.join(base_dir, "**", image_name)
        import glob
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    # Also try flat IMAGE_DIR
    direct = os.path.join(IMAGE_DIR, image_name)
    if os.path.exists(direct):
        return direct

    return None


def _find_odo_crop(odo_crop_file: str) -> Optional[str]:
    """Find an odo crop in proc/ (handles both flat and date-subdir paths)."""
    # Try direct — handles "YYYY-MM-DD/basename" relative paths
    full = os.path.join(PROC_DIR, odo_crop_file)
    if os.path.exists(full):
        return full

    # Try flat (legacy)
    alt = os.path.join(PROC_DIR, os.path.basename(odo_crop_file))
    if os.path.exists(alt):
        return alt

    return None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_dedupe(
    needle_tol: float = NEEDLE_DEG_TOLERANCE,
    npos_tol: int = NPOS_TOLERANCE,
    dry_run: bool = True,
) -> dict:
    """Run deduplication: tag runs in DB, optionally delete eligible files.

    Returns stats dict.
    """
    runs, total, rows_in_runs = find_identical_runs(needle_tol, npos_tol)

    stats = {
        "total_rows": total,
        "total_runs": len(runs),
        "rows_in_runs": rows_in_runs,
        "rows_tagged_first": 0,
        "rows_tagged_last": 0,
        "rows_tagged_middle": 0,
        "eligible_for_delete": 0,
        "source_deleted": 0,
        "odo_deleted": 0,
        "dry_run": dry_run,
    }

    if not runs:
        log.info("No identical-reading runs found.")
        return stats

    log.info("Found %d runs covering %d / %d rows (%.1f%%)",
             len(runs), rows_in_runs, total,
             100 * rows_in_runs / total if total else 0)

    # Process each run
    run_id_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_")
    updated = 0

    for run_idx, run in enumerate(runs):
        run_id = f"{run_id_prefix}{run_idx:06d}_{uuid.uuid4().hex[:8]}"
        positions, eligible = classify_run_positions(run)

        # Tag positions in DB
        if not dry_run:
            with get_session() as session:
                for row in run:
                    db_row = session.get(MeterReading, row.image_name)
                    if db_row is None:
                        continue

                    # Merge run info into notes JSON
                    notes_data = {}
                    if db_row.notes:
                        try:
                            notes_data = json.loads(db_row.notes) if isinstance(db_row.notes, str) else db_row.notes
                        except (json.JSONDecodeError, TypeError):
                            notes_data = {}

                    position = positions.get(row.image_name, "unknown")
                    notes_data["run_id"] = run_id
                    notes_data["run_position"] = position

                    db_row.notes = json.dumps(notes_data)
                    updated += 1

                session.commit()

        # Count positions
        for row in run:
            pos = positions.get(row.image_name)
            if pos == "first":
                stats["rows_tagged_first"] += 1
            elif pos == "last":
                stats["rows_tagged_last"] += 1
            elif pos == "middle":
                stats["rows_tagged_middle"] += 1

        # Delete eligible middle frames' files
        for image_name in eligible:
            stats["eligible_for_delete"] += 1

            if dry_run:
                continue

            # Delete source image
            src_path = _find_source_image(image_name)
            if src_path and os.path.exists(src_path):
                try:
                    os.remove(src_path)
                    stats["source_deleted"] += 1
                    log.debug("  Deleted source: %s", src_path)
                except OSError as e:
                    log.warning("  Failed to delete source %s: %s", image_name, e)

            # Delete odo crop
            with get_session() as s:
                db_row = s.get(MeterReading, image_name)
                if db_row and db_row.odo_crop_file:
                    crop_path = _find_odo_crop(db_row.odo_crop_file)
                    if crop_path and os.path.exists(crop_path):
                        try:
                            os.remove(crop_path)
                            stats["odo_deleted"] += 1
                            log.debug("  Deleted odo crop: %s", crop_path)
                        except OSError as e:
                            log.warning("  Failed to delete odo crop %s: %s",
                                        db_row.odo_crop_file, e)

    if not dry_run:
        log.info("Tagged %d DB rows", updated)

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable deduplication report."""
    print(f"\n{'='*60}")
    print(f"Water Meter Deduplication Report")
    print(f"{'='*60}")
    print(f"Total DB rows:           {stats['total_rows']:>8}")
    print(f"Identical-reading runs:  {stats['total_runs']:>8}")
    print(f"Rows in runs:            {stats['rows_in_runs']:>8}  "
          f"({100*stats['rows_in_runs']/stats['total_rows']:.1f}%)"
          if stats['total_rows'] else "")
    print(f"\nRun positions:")
    print(f"  First (anchors):       {stats['rows_tagged_first']:>8}")
    print(f"  Last (anchors):        {stats['rows_tagged_last']:>8}")
    print(f"  Middle (redundant):    {stats['rows_tagged_middle']:>8}")
    print(f"\nEligible for deletion:   {stats['eligible_for_delete']:>8}")

    if not stats['dry_run']:
        print(f"\nDeleted:")
        print(f"  Source images:         {stats['source_deleted']:>8}")
        print(f"  Odo crops:             {stats['odo_deleted']:>8}")
    else:
        print(f"\nDRY RUN — no files deleted, no DB changes made.")
        print(f"Run with --execute to apply changes.")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Deduplicate water meter frames — find identical-reading runs")
    p.add_argument("--needle-tol", type=float, default=NEEDLE_DEG_TOLERANCE,
                   help=f"Needle angle tolerance in degrees (default: {NEEDLE_DEG_TOLERANCE})")
    p.add_argument("--npos-tol", type=int, default=NPOS_TOLERANCE,
                   help=f"npos tolerance (default: {NPOS_TOLERANCE})")
    p.add_argument("--execute", action="store_true",
                   help="Actually tag DB and delete eligible files")
    p.add_argument("--yes", "-y", action="store_true",
                   help="Skip confirmation prompt (with --execute)")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    dry_run = not args.execute

    if args.execute:
        log.warning("EXECUTE mode — will tag DB rows and delete eligible files!")
        if not args.yes:
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    stats = execute_dedupe(
        needle_tol=args.needle_tol,
        npos_tol=args.npos_tol,
        dry_run=dry_run,
    )

    print_report(stats)


if __name__ == "__main__":
    main()