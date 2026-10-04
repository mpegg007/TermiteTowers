#!/usr/bin/env python3
"""Diagnostic: report odometer readings that violate monotonicity constraints.

Read-only — does NOT write to the DB.  Use this to assess decode quality
before and after template/hardware/anchor changes.

Typical run during experiments:
  .venv/bin/python scripts/water_meter/explore_monotonicity.py

The inline monotonicity bounds in decode_odo.py already correct violations
during processing; this script simply reports what's left afterward so you
can judge whether your latest changes helped or hurt.
"""
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("monotonicity")


def explore_violations() -> dict:
    """Return a stats dict summarising all monotonicity violations."""
    init_db()

    stats = {
        "total": 0,
        "flagged": 0,
        "backward": 0,
        "forward": 0,
        "deltas": [],
        "worst": [],  # (image_name, reading, expected_max, delta)
    }

    # --- Read manual anchors ---
    with get_session() as session:
        raw_manuals = (
            session.query(
                MeterReading.image_name,
                MeterReading.odo_reading,
                MeterReading.capture_ts,
            )
            .filter(MeterReading.odo_confidence == 1.0)
            .filter(MeterReading.odo_reading.isnot(None))
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

    if not raw_manuals:
        print("No manual correction anchors found — nothing to check.")
        return stats

    manual_readings: List[Tuple[float, object, str]] = [
        (float(r[1]), r[2], r[0]) for r in raw_manuals
    ]

    log.info("Found %d manual correction anchors", len(manual_readings))

    # Build running maximum per anchor
    anchor_max = 0.0
    anchor_by_name: Dict[str, float] = {}
    for reading, ts, name in manual_readings:
        if reading > anchor_max:
            anchor_max = reading
        anchor_by_name[name] = anchor_max

    # --- Scan all rows ---
    running_max = 0.0
    next_manual_index = 0
    next_manual_reading = manual_readings[0][0] if manual_readings else None

    with get_session() as session:
        all_rows = (
            session.query(MeterReading)
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

        stats["total"] = len(all_rows)

        for row in all_rows:
            if row.image_name in anchor_by_name:
                running_max = anchor_by_name[row.image_name]
                while (next_manual_index < len(manual_readings) and
                       manual_readings[next_manual_index][0] <= running_max):
                    next_manual_index += 1
                next_manual_reading = (
                    manual_readings[next_manual_index][0]
                    if next_manual_index < len(manual_readings) else None
                )
                continue

            if row.odo_reading is None:
                continue

            current = float(row.odo_reading)

            # Backward violation: reading went down
            backward = running_max > 0 and current < running_max - 0.01
            # Forward violation: reading exceeds next anchor
            forward = (next_manual_reading is not None and
                       current > next_manual_reading + 0.01)

            if not backward and not forward:
                continue

            stats["flagged"] += 1
            if backward:
                stats["backward"] += 1
                delta = running_max - current
            else:
                stats["forward"] += 1
                delta = current - next_manual_reading

            stats["deltas"].append(delta)
            stats["worst"].append((
                row.image_name or "?",
                round(current, 3),
                round(running_max, 3) if backward else round(next_manual_reading, 3),
                round(delta, 4),
                "backward" if backward else "forward",
            ))

    return stats


def print_report(stats: dict):
    """Print a human-readable summary."""
    total = stats["total"]
    flagged = stats["flagged"]
    rate = 100.0 * flagged / total if total else 0

    print(f"\n{'='*60}")
    print("Odometer Monotonicity Diagnostic Report")
    print(f"{'='*60}")
    print(f"Total readings:             {total:>8}")
    print(f"Violations:                 {flagged:>8}  ({rate:.1f}%)")
    print(f"  Backward (dropped):       {stats['backward']:>8}")
    print(f"  Forward (exceeded anchor):{stats['forward']:>8}")

    deltas = stats["deltas"]
    if deltas:
        deltas_sorted = sorted(deltas)
        print(f"\nViolation magnitude (cubic meters):")
        print(f"  Min:     {min(deltas):.4f}")
        print(f"  Median:  {deltas_sorted[len(deltas_sorted)//2]:.4f}")
        print(f"  Max:     {max(deltas):.4f}")
        print(f"  Mean:    {sum(deltas)/len(deltas):.4f}")

    # Top 10 worst offenders
    worst = sorted(stats["worst"], key=lambda x: x[3], reverse=True)[:10]
    if worst:
        print(f"\nTop 10 worst violations:")
        print(f"  {'Image':<40} {'Reading':>10} {'Expected':>10} {'Delta':>8} {'Dir'}")
        print(f"  {'-'*38}   {'-'*8}   {'-'*8}   {'-'*6}   {'-'*8}")
        for name, reading, expected, delta, direction in worst:
            dname = name if len(name) <= 38 else "..." + name[-35:]
            print(f"  {dname:<40} {reading:>10.3f} {expected:>10.3f} {delta:>8.4f} {direction}")

    print(f"{'='*60}\n")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    stats = explore_violations()
    print_report(stats)


if __name__ == "__main__":
    main()