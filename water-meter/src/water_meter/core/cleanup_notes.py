#!/usr/bin/env python3
"""Clean up review-related tags from meter_readings notes JSON.

When images are archived, cleaned up, or manually verified, the tags that
cause them to appear in "Needs Review" or "Flagged" views must be removed
so those views accurately reflect what still needs attention.

Removes the following keys from the notes JSON blob:
  - ``needs_review``
  - ``monotonicity_flag``
  - ``review_reason``
  - ``review_ts``
  - ``flagged_reason``

Preserves other keys (e.g. ``preserve``, ``source``, ``pos_confs``, etc.).

Target selection:
  - **all**: strip review tags from ALL rows (default)
  - **confirmed**: only rows with odo_confidence == 1.0 (manual corrections)
  - **clean**: only rows with clean_read == True
  - **archived**: only rows with clean_archive == True
  - **image**: a single image by name

**Default is dry-run.**  Pass ``--execute`` to write.

Usage:
    # Report what would be cleaned (all rows)
    .venv/bin/python scripts/water_meter/cleanup_notes.py

    # Clean only manually confirmed rows
    .venv/bin/python scripts/water_meter/cleanup_notes.py --target confirmed

    # Clean a single image
    .venv/bin/python scripts/water_meter/cleanup_notes.py --image water_meter_20260701_120000.jpg

    # Execute
    .venv/bin/python scripts/water_meter/cleanup_notes.py --execute --target all
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, init_db, get_session, _Session

log = logging.getLogger("cleanup_notes")

# ---------------------------------------------------------------------------
# Keys to strip from notes JSON
# ---------------------------------------------------------------------------
STRIP_KEYS: Set[str] = {
    "needs_review",
    "monotonicity_flag",
    "review_reason",
    "review_ts",
    "flagged_reason",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_notes(notes_str: str | None) -> tuple[str | None, bool]:
    """Parse notes, strip review keys, return (new_json_str, changed).

    Returns None for notes_str if nothing remains after stripping.
    """
    if not notes_str:
        return None, False

    try:
        data = json.loads(notes_str) if isinstance(notes_str, str) else notes_str
    except (json.JSONDecodeError, TypeError):
        return notes_str, False

    if not isinstance(data, dict):
        return notes_str, False

    changed = False
    for key in list(data.keys()):
        if key in STRIP_KEYS:
            del data[key]
            changed = True

    if not data:
        return None, changed

    return json.dumps(data), changed


def _get_target_rows(session, target: str, image_name: str | None) -> List[MeterReading]:
    """Return the rows to process based on target mode."""
    q = session.query(MeterReading)

    if target == "confirmed":
        q = q.filter(MeterReading.odo_confidence == 1.0)
    elif target == "clean":
        q = q.filter(MeterReading.clean_read == True)
    elif target == "archived":
        q = q.filter(MeterReading.clean_archive == True)
    elif target == "image" and image_name:
        row = session.get(MeterReading, image_name)
        return [row] if row else []
    # "all" — no additional filter

    return q.order_by(MeterReading.capture_ts.asc()).all()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_cleanup_notes(
    target: str = "all",
    image_name: str | None = None,
    dry_run: bool = True,
) -> dict:
    """Remove review-related tags from notes JSON.

    Returns stats dict.
    """
    stats = {
        "dry_run": dry_run,
        "target": target,
        "rows_scanned": 0,
        "rows_with_strippable_tags": 0,
        "rows_modified": 0,
        "images": [],
    }

    init_db()

    session = _Session()
    try:
        rows = _get_target_rows(session, target, image_name)
        stats["rows_scanned"] = len(rows)

        if not rows:
            log.info("No rows match target '%s'.", target)
            return stats

        modified = 0
        for row in rows:
            new_notes, changed = _clean_notes(row.notes)
            if changed:
                stats["rows_with_strippable_tags"] += 1
                log.debug("  %s: stripping review tags", row.image_name)
                if not dry_run:
                    row.notes = new_notes
                    modified += 1
                stats["images"].append(row.image_name)

        if not dry_run and modified:
            session.commit()
            stats["rows_modified"] = modified
            log.info("Modified %d rows.", modified)
        elif dry_run:
            stats["rows_modified"] = stats["rows_with_strippable_tags"]
            log.info(
                "Would modify %d rows (dry run).",
                stats["rows_with_strippable_tags"],
            )

    finally:
        session.close()

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable report."""
    print(f"\n{'='*60}")
    print(f"Water Meter — Notes Cleanup Report")
    print(f"{'='*60}")
    print(f"Target:                   {stats['target']}")
    print(f"Rows scanned:             {stats['rows_scanned']:>8}")
    print(f"Rows with review tags:    {stats['rows_with_strippable_tags']:>8}")
    print(f"Rows that would change:   {stats['rows_modified']:>8}")

    if stats["images"]:
        print(f"\n  First 20 affected images:")
        for img in stats["images"][:20]:
            print(f"    {img}")
        if len(stats["images"]) > 20:
            print(f"    ... and {len(stats['images']) - 20} more")

    if stats["dry_run"]:
        print(f"\nDRY RUN — no changes made to the database.")
        print(f"Run with --execute to apply changes.")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Clean up review-related tags from meter_readings notes JSON"
    )
    p.add_argument(
        "--target",
        choices=["all", "confirmed", "clean", "archived", "image"],
        default="all",
        help="Which rows to target (default: all)",
    )
    p.add_argument(
        "--image",
        metavar="FILENAME",
        help="Single image to clean (requires --target image)",
    )
    p.add_argument(
        "--execute", action="store_true",
        help="Write changes to the database (not a dry run)",
    )
    p.add_argument(
        "--auto", action="store_true",
        help="Auto mode — execute without confirmation (for cron)",
    )
    p.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.target == "image" and not args.image:
        log.error("--target image requires --image FILENAME")
        sys.exit(1)

    do_execute = args.execute or args.auto

    if do_execute:
        log.warning("EXECUTE mode — will modify DB notes!")
        if not (args.yes or args.auto):
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    stats = run_cleanup_notes(
        target=args.target,
        image_name=args.image,
        dry_run=not do_execute,
    )

    print_report(stats)


if __name__ == "__main__":
    main()