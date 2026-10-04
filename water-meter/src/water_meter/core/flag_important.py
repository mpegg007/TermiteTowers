#!/usr/bin/env python3
"""Flag important water meter images for long-term preservation.

Implements four strategies to identify keeper images that should survive
cleanup and archival:

  1. **Transition-zone frames** — one image per rollover event where npos
     crosses from >90 to <10.  These capture the odometer digit transition
     and are essential for manual verification.

  2. **Rotation stepping** — best image from each 10-npos rotation step
     between npos 95 and npos 5 (inclusive), chosen by composite quality
     score.  Covers the full rotation where the last digit is visible.

  3. **Best-per-hour (2 months)** — clearest image per hour over the
     trailing 60 days, biased toward high confidence + good contrast.

  4. **Best-per-day (1 year)** — clearest image per day over the trailing
     365 days, using the same composite quality score.

Each selected image has ``"preserve": "important"`` written into its
``notes`` JSON blob.  The ``cleanup.py`` and ``archive_images.py``
scripts already respect ``preserve`` tags.

**Default is dry-run.**  Pass ``--execute`` to write.

Usage:
    # Report what would be flagged
    .venv/bin/python scripts/water_meter/flag_important.py

    # Execute
    .venv/bin/python scripts/water_meter/flag_important.py --execute

    # Adjust time windows
    .venv/bin/python scripts/water_meter/flag_important.py --hour-window 90 --day-window 180
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from sqlalchemy import func

from water_meter.core.db import MeterReading, init_db, get_session, _Session

log = logging.getLogger("flag_important")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
HOUR_WINDOW_DAYS = 60         # trailing days for "best per hour" strategy
DAY_WINDOW_DAYS = 365         # trailing days for "best per day" strategy
N_POS_STEPS = [95, 85, 75, 65, 55, 45, 35, 25, 15, 5]  # rotation steps

# Composite quality score weights
WEIGHT_CONFIDENCE = 0.50
WEIGHT_IMG_CONTRAST = 0.25
WEIGHT_ODO_CONTRAST = 0.25

# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def _composite_score(row: MeterReading) -> float:
    """Compute a composite quality score [0, 1] for a row.

    Higher is better.  Penalises missing data and anomalies.
    """
    conf = row.odo_confidence or 0
    img_c = row.img_contrast or 0
    odo_c = row.odo_contrast or 0

    # Normalise contrast — typical range 0–100, cap at 100
    img_c_norm = min(img_c / 100.0, 1.0)
    odo_c_norm = min(odo_c / 100.0, 1.0)

    # Anomaly penalty
    penalty = 0.5 if row.status == "ANOMALY" else (0.0 if row.status == "OK" else 0.3)

    score = (
        WEIGHT_CONFIDENCE * conf
        + WEIGHT_IMG_CONTRAST * img_c_norm
        + WEIGHT_ODO_CONTRAST * odo_c_norm
    )
    # Apply penalty multiplicatively
    score *= (1.0 - penalty)
    return score


# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------

def _pick_best_in_bucket(
    rows: List[MeterReading],
) -> Optional[str]:
    """Return image_name of row with highest composite score, or None."""
    if not rows:
        return None
    best = max(rows, key=_composite_score)
    return best.image_name


def _flag_transitions(session) -> Set[str]:
    """Strategy 1: One frame per npos rollover (cross >90 → <10).

    Uses the same window-function logic as the /api/rollovers endpoint.
    Returns a set of image_names to flag.
    """
    flagged: Set[str] = set()
    subq = (
        session.query(
            MeterReading.image_name,
            MeterReading.npos,
            func.lag(MeterReading.npos)
            .over(order_by=MeterReading.capture_ts.asc())
            .label("prev_npos"),
        )
        .filter(MeterReading.status == "OK")
        .subquery()
    )
    rows = (
        session.query(MeterReading)
        .join(subq, MeterReading.image_name == subq.c.image_name)
        .filter(subq.c.prev_npos.isnot(None))
        .filter(subq.c.prev_npos > 90)
        .filter(MeterReading.npos >= 0)
        .filter(MeterReading.npos <= 3)
        .order_by(MeterReading.capture_ts.desc())
        .all()
    )
    for r in rows:
        flagged.add(r.image_name)
    log.info("  Transitions (rollovers): %d frames", len(flagged))
    return flagged


def _flag_rotation_steps(session) -> Set[str]:
    """Strategy 2: Best image from each npos step [95, 85, ..., 5].

    For each npos bucket (±2 tolerance), picks the highest composite score.
    """
    flagged: Set[str] = set()
    for target in N_POS_STEPS:
        # Bucket: npos in [target-2, target+2]
        bucket = (
            session.query(MeterReading)
            .filter(MeterReading.status == "OK")
            .filter(MeterReading.npos >= target - 2)
            .filter(MeterReading.npos <= target + 2)
            .order_by(MeterReading.capture_ts.desc())
            .all()
        )
        best = _pick_best_in_bucket(bucket)
        if best:
            flagged.add(best)
            log.debug("  Rotation step npos~%d: %s", target, best)
    log.info("  Rotation steps: %d frames", len(flagged))
    return flagged


def _flag_best_per_hour(session, window_days: int) -> Set[str]:
    """Strategy 3: Best image per clock-hour over the trailing window days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        session.query(MeterReading)
        .filter(MeterReading.capture_ts >= cutoff)
        .filter(MeterReading.status.in_(["OK", "ANOMALY"]))
        .order_by(MeterReading.capture_ts.asc())
        .all()
    )
    if not rows:
        log.info("  Best-per-hour: 0 frames (no data in window)")
        return set()

    # Bucket by (date, hour)
    buckets: Dict[Tuple[str, int], List[MeterReading]] = {}
    for r in rows:
        if r.capture_ts is None:
            continue
        key = (r.capture_ts.strftime("%Y-%m-%d"), r.capture_ts.hour)
        buckets.setdefault(key, []).append(r)

    flagged: Set[str] = set()
    for key, bucket in sorted(buckets.items()):
        best = _pick_best_in_bucket(bucket)
        if best:
            flagged.add(best)
    log.info("  Best-per-hour (%d days): %d frames from %d hour buckets",
             window_days, len(flagged), len(buckets))
    return flagged


def _flag_best_per_day(session, window_days: int) -> Set[str]:
    """Strategy 4: Best image per calendar day over the trailing window days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        session.query(MeterReading)
        .filter(MeterReading.capture_ts >= cutoff)
        .filter(MeterReading.status.in_(["OK", "ANOMALY"]))
        .order_by(MeterReading.capture_ts.asc())
        .all()
    )
    if not rows:
        log.info("  Best-per-day: 0 frames (no data in window)")
        return set()

    buckets: Dict[str, List[MeterReading]] = {}
    for r in rows:
        if r.capture_ts is None:
            continue
        key = r.capture_ts.strftime("%Y-%m-%d")
        buckets.setdefault(key, []).append(r)

    flagged: Set[str] = set()
    for key, bucket in sorted(buckets.items()):
        best = _pick_best_in_bucket(bucket)
        if best:
            flagged.add(best)
    log.info("  Best-per-day (%d days): %d frames from %d day buckets",
             window_days, len(flagged), len(buckets))
    return flagged


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_flag(
    hour_window_days: int = HOUR_WINDOW_DAYS,
    day_window_days: int = DAY_WINDOW_DAYS,
    dry_run: bool = True,
) -> dict:
    """Run all four flagging strategies and collect the union of results.

    Returns stats dict with breakdowns per strategy.
    """
    stats = {
        "dry_run": dry_run,
        "transitions": 0,
        "rotation_steps": 0,
        "best_per_hour": 0,
        "best_per_day": 0,
        "total_unique": 0,
        "written": 0,
    }

    init_db()

    session = _Session()
    try:
        log.info("Strategy 1: Transition/rollover frames")
        transitions = _flag_transitions(session)

        log.info("Strategy 2: Rotation stepping (npos 95 → 5)")
        rotation = _flag_rotation_steps(session)

        log.info("Strategy 3: Best per hour (last %d days)", hour_window_days)
        per_hour = _flag_best_per_hour(session, hour_window_days)

        log.info("Strategy 4: Best per day (last %d days)", day_window_days)
        per_day = _flag_best_per_day(session, day_window_days)

        # Union of all strategies
        all_flagged = transitions | rotation | per_hour | per_day
        stats["transitions"] = len(transitions)
        stats["rotation_steps"] = len(rotation)
        stats["best_per_hour"] = len(per_hour)
        stats["best_per_day"] = len(per_day)
        stats["total_unique"] = len(all_flagged)

        log.info("Total unique images flagged for preservation: %d", len(all_flagged))

        if dry_run:
            log.info("Dry run — no DB changes made.")
            return stats

        # Write preserve: important into notes
        written = 0
        for image_name in all_flagged:
            row = session.get(MeterReading, image_name)
            if row is None:
                continue

            # Parse existing notes
            notes_data: dict = {}
            if row.notes:
                try:
                    notes_data = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
                except (json.JSONDecodeError, TypeError):
                    notes_data = {}

            # Only set preserve if not already set to something higher-priority
            if notes_data.get("preserve") not in ("transition", "manual"):
                notes_data["preserve"] = "important"
                row.notes = json.dumps(notes_data)
                written += 1

        session.commit()
        stats["written"] = written
        log.info("Wrote preserve:important to %d rows.", written)

    finally:
        session.close()

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable report."""
    print(f"\n{'='*60}")
    print(f"Water Meter — Important Image Flagging Report")
    print(f"{'='*60}")
    print(f"Transitions (rollovers):  {stats['transitions']:>8}")
    print(f"Rotation steps (95→5):    {stats['rotation_steps']:>8}")
    print(f"Best per hour (2 months): {stats['best_per_hour']:>8}")
    print(f"Best per day (1 year):    {stats['best_per_day']:>8}")
    print(f"{'─'*40}")
    print(f"Total unique flagged:     {stats['total_unique']:>8}")
    if not stats['dry_run']:
        print(f"Written to DB:            {stats['written']:>8}")
    print(f"{'='*60}")

    if stats['dry_run']:
        print("\nDRY RUN — no changes made to the database.")
        print("Run with --execute to write preserve:important tags.")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Flag important water meter images for preservation"
    )
    p.add_argument(
        "--execute", action="store_true",
        help="Write preserve:important tags to the database (not a dry run)",
    )
    p.add_argument(
        "--auto", action="store_true",
        help="Auto mode — execute without confirmation (for cron)",
    )
    p.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt",
    )
    p.add_argument(
        "--hour-window", type=int, default=HOUR_WINDOW_DAYS,
        metavar="DAYS",
        help=f"Trailing days for best-per-hour strategy (default: {HOUR_WINDOW_DAYS})",
    )
    p.add_argument(
        "--day-window", type=int, default=DAY_WINDOW_DAYS,
        metavar="DAYS",
        help=f"Trailing days for best-per-day strategy (default: {DAY_WINDOW_DAYS})",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    do_execute = args.execute or args.auto

    if do_execute:
        log.warning("EXECUTE mode — will write preserve:important tags to DB!")
        if not (args.yes or args.auto):
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    stats = run_flag(
        hour_window_days=args.hour_window,
        day_window_days=args.day_window,
        dry_run=not do_execute,
    )

    print_report(stats)


if __name__ == "__main__":
    main()