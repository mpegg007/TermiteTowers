#!/usr/bin/env python3
"""Extract a clean per‑day reading dataset for analysis and export.

Outputs a minimal CSV:
    date,reading,source

Selection strategy:
  1. Start of day (00:00–00:02) — the single frame closest to midnight,
     with npos ≤ 10.  Falls back to "best of day" if all start‑of‑day
     frames have npos > 10.
  2. Best of day — the frame with the highest composite quality score
     (confidence × contrast × npos‑proximity).
  3. Per bucket: manual > needle > odo_raw — first bucket with data wins.

Output is written to stdout by default (pipe to a file if you want CSV
on disk).  The file is tiny (~1 KB per day) so a tempfile is overkill.

Usage:
    .venv/bin/python scripts/water_meter/extract_readings.py
    .venv/bin/python scripts/water_meter/extract_readings.py > readings.csv
    .venv/bin/python scripts/water_meter/extract_readings.py --start-date 2026-07-01 --end-date 2026-08-01
    .venv/bin/python scripts/water_meter/extract_readings.py --strategy best      # use best-of-day for all
    .venv/bin/python scripts/water_meter/extract_readings.py --strategy hourly    # best per clock hour
    .venv/bin/python scripts/water_meter/extract_readings.py --strategy 8hourly   # best per 8-hour block
    .venv/bin/python scripts/water_meter/extract_readings.py --strategy daily     # best per day (default)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session

log = logging.getLogger("extract_readings")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_best_reading(row: MeterReading) -> Tuple[Optional[float], str]:
    """Return the best available reading from a single row.

    Priority: manual > final > needle > odo_reading (scan)
    """
    if row.odo_manual is not None:
        return float(row.odo_manual), "manual"
    if row.odo_published is not None:
        return float(row.odo_published), "published"
    if row.odo_needle is not None:
        return float(row.odo_needle), "needle"
    if row.odo_reading is not None:
        return float(row.odo_reading), "odo_scan"
    return None, "none"


def _quality_score(row: MeterReading) -> float:
    """Score a row for "best of period" selection. Higher is better."""
    conf = row.odo_confidence or 0.0
    contrast = max(0, min((row.odo_contrast or 0) / 128.0, 1.0))
    # Needle near zero = unambiguous
    npos = row.npos
    if npos is not None:
        npos_score = 1.0 - abs(npos - 0) / 50.0  # closer to 0 is better, max penalty 50
        npos_score = max(0.0, npos_score)
    else:
        npos_score = 0.0
    # Build 0-1 score: confidence dominates, contrast and npos help tiebreak
    score = conf * 0.5 + contrast * 0.25 + npos_score * 0.25
    return score


# ---------------------------------------------------------------------------
# Strategy 1: Start-of-day (midnight±2 min, npos ≤ 10)
# ---------------------------------------------------------------------------

def _pick_start_of_day(day_rows: List[MeterReading]) -> Optional[MeterReading]:
    """Return the row closest to midnight with npos ≤ 10, or None."""
    midnight_candidates: List[MeterReading] = []
    for row in day_rows:
        if row.capture_ts is None:
            continue
        h = row.capture_ts.hour
        m = row.capture_ts.minute
        # Within 2 minutes of midnight (00:00 to 00:02)
        if h == 0 and m <= 2:
            if row.npos is not None and row.npos <= 10:
                midnight_candidates.append(row)
    if midnight_candidates:
        # Pick the one closest to midnight
        midnight_candidates.sort(key=lambda r: r.capture_ts.hour * 3600 +
                                            r.capture_ts.minute * 60 +
                                            r.capture_ts.second)
        return midnight_candidates[0]
    return None


# ---------------------------------------------------------------------------
# Strategy 2: Best of day (composite quality score)
# ---------------------------------------------------------------------------

def _pick_best_of_day(day_rows: List[MeterReading]) -> Optional[MeterReading]:
    """Pick the row with the highest composite quality score."""
    if not day_rows:
        return None
    best = None
    best_score = -1.0
    for row in day_rows:
        s = _quality_score(row)
        if s > best_score:
            best_score = s
            best = row
    return best


# ---------------------------------------------------------------------------
# Strategy 3: Best per hour
# ---------------------------------------------------------------------------

def _pick_best_per_hour(day_rows: List[MeterReading]) -> List[MeterReading]:
    """Pick the best row in each clock hour of the day."""
    buckets: Dict[int, List[MeterReading]] = {}
    for row in day_rows:
        if row.capture_ts is None:
            continue
        h = row.capture_ts.hour
        buckets.setdefault(h, []).append(row)

    result = []
    for h in sorted(buckets):
        best = _pick_best_of_day(buckets[h])
        if best:
            result.append(best)
    return result


# ---------------------------------------------------------------------------
# Strategy 4: Best per 8-hour block (00-07, 08-15, 16-23)
# ---------------------------------------------------------------------------

def _pick_best_per_8hour(day_rows: List[MeterReading]) -> List[MeterReading]:
    """Pick the best row in each 8-hour block of the day."""
    buckets: Dict[int, List[MeterReading]] = {}
    for row in day_rows:
        if row.capture_ts is None:
            continue
        block = row.capture_ts.hour // 8
        buckets.setdefault(block, []).append(row)

    result = []
    for b in sorted(buckets):
        best = _pick_best_of_day(buckets[b])
        if best:
            result.append(best)
    return result


# ---------------------------------------------------------------------------
# Data query
# ---------------------------------------------------------------------------

def _query_daily(start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> Dict[str, List[MeterReading]]:
    """Return {iso_date: [rows]} for the date range."""
    with get_session() as session:
        q = session.query(MeterReading).filter(
            MeterReading.status.in_(["OK", "ANOMALY"])
        ).order_by(MeterReading.capture_ts)

        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                q = q.filter(MeterReading.capture_ts >= start)
            except ValueError:
                log.error("Invalid start date: %s (expected YYYY-MM-DD)", start_date)
                sys.exit(1)

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                q = q.filter(MeterReading.capture_ts < end)
            except ValueError:
                log.error("Invalid end date: %s (expected YYYY-MM-DD)", end_date)
                sys.exit(1)

        rows: List[MeterReading] = q.all()

    # Group by date
    by_date: Dict[str, List[MeterReading]] = {}
    for row in rows:
        if row.capture_ts is None:
            continue
        d = row.capture_ts.strftime("%Y-%m-%d")
        by_date.setdefault(d, []).append(row)

    return by_date


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract(start_date=None, end_date=None, strategy="daily"):
    """Run extraction and print CSV to stdout."""
    by_date = _query_daily(start_date, end_date)
    if not by_date:
        log.warning("No data found")
        return

    dated_rows = sorted(by_date.items())
    total = 0

    print("date,reading,source,npos,image_name")

    for day_str, day_rows in dated_rows:
        if strategy in ("hourly", "8hourly"):
            if strategy == "hourly":
                picks = _pick_best_per_hour(day_rows)
                mode = "hourly"
            else:
                picks = _pick_best_per_8hour(day_rows)
                mode = "8hourly"
            for row in picks:
                best_val, source = _pick_best_reading(row)
                if best_val is not None:
                    print(f"{day_str},{best_val:.4f},{source}:{mode},{row.npos},{row.image_name}")
                    total += 1
            continue

        # strategy == "daily" or "best"
        row: Optional[MeterReading] = None
        mode = ""

        if strategy == "daily":
            # Prefer start-of-day, fall back to best-of-day
            sod = _pick_start_of_day(day_rows)
            if sod is not None:
                row = sod
                mode = "start_of_day"
            else:
                row = _pick_best_of_day(day_rows)
                mode = "best_of_day"
        else:
            # "best" — always use best-of-day
            row = _pick_best_of_day(day_rows)
            mode = "best_of_day"

        if row is None:
            continue

        best_val, source = _pick_best_reading(row)
        if best_val is not None:
            print(f"{day_str},{best_val:.4f},{source}:{mode},{row.npos},{row.image_name}")
            total += 1

    log.info("Extracted %d rows", total)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Extract per-day water meter readings")
    p.add_argument("--start-date", type=str, help="YYYY-MM-DD")
    p.add_argument("--end-date", type=str, help="YYYY-MM-DD")
    p.add_argument("--strategy", choices=["daily", "best", "hourly", "8hourly"], default="daily",
                   help="Selection strategy: daily (midnight+best), best (best-only), hourly (best per clock hour), 8hourly (best per 8h block)")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    extract(
        start_date=args.start_date,
        end_date=args.end_date,
        strategy=args.strategy,
    )


if __name__ == "__main__":
    main()