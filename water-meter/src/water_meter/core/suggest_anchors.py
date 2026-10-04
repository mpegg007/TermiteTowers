#!/usr/bin/env python3
"""Mark rows needing manual review based on n00 pos5 template disagreement.

Instead of the old span-based discrepancy logic (which flagged frames
where odo_needle disagreed with odo_manual in the broken pipeline),
this script:

1. Finds n00_anchor rows where the template-matched pos5 digit disagrees
   with the needle-tracked ones digit by more than 1 (indicating the
   needle counter may have missed wraps).
2. Only flags rows whose source image is confirmed to exist on disk
   (checked across keepers/, scanned/, pending/).
3. Prefers recent frames — only flags rows from the last 7 days.

Usage:
    .venv/bin/python scripts/water_meter/suggest_anchors.py
    .venv/bin/python scripts/water_meter/suggest_anchors.py --dry-run
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("suggest_anchors")

IMAGE_DIR = os.path.expanduser("~/pictures/water_meter")
SOURCE_DIRS = ["keepers", "scanned", "pending"]


def image_exists_on_disk(image_name: str) -> bool:
    """Check if a source image file exists in any of the source directories."""
    for base in SOURCE_DIRS:
        for root, _dirs, files in os.walk(os.path.join(IMAGE_DIR, base)):
            if image_name in files:
                return True
    return False


def suggest_new_anchors(dry_run: bool = False) -> int:
    """Find n00 frames where pos5 template disagrees with needle integer.

    Disagreement by >1 digit means the needle counter likely missed wraps.
    These frames are the best candidates for manual anchor verification.
    """
    init_db()

    # Only consider the last 7 days (older images may be archived)
    cutoff = datetime.utcnow() - timedelta(days=7)

    candidates = []
    with get_session() as s:
        rows = (
            s.query(MeterReading)
            .filter(MeterReading.status == "OK")
            .filter(MeterReading.notes.like('%"pos5_digit"%'))
            .filter(MeterReading.odo_manual.is_(None))  # not already corrected
            .filter(MeterReading.capture_ts >= cutoff)
            .order_by(MeterReading.capture_ts.desc())
            .all()
        )

        for row in rows:
            try:
                notes = json.loads(row.notes) if isinstance(row.notes, str) else (row.notes or {})
            except (json.JSONDecodeError, TypeError):
                continue

            anchor = notes.get("n00_anchor", {})
            pos5_digit = anchor.get("pos5_digit")
            if pos5_digit is None:
                continue

            # Needle-tracked ones digit
            if row.odo_needle is None:
                continue
            needle_ones = int(row.odo_needle) % 10

            # Disagreement by exactly 1 is common template confusion — skip
            diff = abs(pos5_digit - needle_ones)
            if diff <= 1:
                continue

            # Check image exists
            if not image_exists_on_disk(row.image_name):
                continue

            candidates.append({
                "image_name": row.image_name,
                "capture_ts": row.capture_ts,
                "npos": row.npos,
                "odo_needle": row.odo_needle,
                "pos5_digit": pos5_digit,
                "pos5_conf": anchor.get("pos5_confidence", 0),
                "needle_ones": needle_ones,
                "diff": diff,
            })

    # Sort by capture_ts descending (most recent first)
    candidates.sort(key=lambda x: x["capture_ts"], reverse=True)

    # Only mark top 10 (avoid flag flood)
    marked = 0
    for c in candidates[:10]:
        if not dry_run:
            with get_session() as s:
                row = s.get(MeterReading, c["image_name"])
                if row is None:
                    continue
                try:
                    notes = json.loads(row.notes) if isinstance(row.notes, str) else (row.notes or {})
                except (json.JSONDecodeError, TypeError):
                    notes = {}
                notes["needs_review"] = f"pos5_mismatch:d{needle_ones}→{c['pos5_digit']}"
                row.notes = json.dumps(notes)
                s.commit()
            marked += 1

    # Print summary
    print(f"\n{'=' * 72}")
    print(f"Review Suggestions (pos5 template vs needle integer mismatch)")
    print(f"{'=' * 72}")
    print(f"  Candidates (diff > 1):   {len(candidates)}")
    print(f"  Marked for review:       {marked}")

    if candidates:
        print(f"\n  Top candidates:")
        print(f"  {'Timestamp':<20} {'npos':>4} {'needle':>10} {'p5':>3} {'diff':>4} {'conf':>8} {'img'}")
        print(f"  {'─' * 80}")
        for c in candidates[:10]:
            print(f"  {c['capture_ts'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"{c['npos']:>4} {c['odo_needle']:>10.3f} {c['pos5_digit']:>3} "
                  f"{c['diff']:>4} {c['pos5_conf']:>8.3f} {c['image_name'][:40]}")

    return marked


def main():
    import argparse
    p = argparse.ArgumentParser(description="Suggest manual review candidates via n00 pos5 mismatch")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    suggest_new_anchors(dry_run=args.dry_run)


if __name__ == "__main__":
    main()