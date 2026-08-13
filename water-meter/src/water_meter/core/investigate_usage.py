#!/usr/bin/env python3
"""Investigate water usage anomalies — 08/01 spike and 7 AM patterns.

Connects directly to the water_meter PostgreSQL DB using the same
connection logic as db.py and the webapp /api/usage endpoint.
Uses odo_published (bucket 4 = COALESCE(odo_manual, odo_needle)) as the
authoritative reading and computes deltas the same way.

Usage:
    .venv/bin/python scripts/water_meter/investigate_usage.py
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, time

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("investigate_usage")

MAX_DAILY_DELTA_L = 20000  # cap: anything > 20 m³/day is a data artifact

# ── helpers ────────────────────────────────────────────────────────────────


def _load_all_published():
    """Return list of (capture_ts, odo_published, npos, reading, digits) sorted by time."""
    init_db()
    rows = []
    with get_session() as s:
        q = (
            s.query(
                MeterReading.capture_ts,
                MeterReading.odo_published,
                MeterReading.npos,
                MeterReading.reading,
                MeterReading.digits,
                MeterReading.status,
                MeterReading.image_name,
            )
            .filter(MeterReading.status == "OK")
            .filter(MeterReading.odo_published.isnot(None))
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )
        for ts, pub, npos, reading, digits, status, name in q:
            rows.append(
                {
                    "ts": ts,
                    "odo_published": float(pub),
                    "npos": npos,
                    "reading": float(reading) if reading is not None else None,
                    "digits": digits,
                    "image_name": name,
                }
            )
    return rows


def _daily_last(rows, start_dt=None, end_dt=None):
    """Chronologically LAST reading per day (same as /api/usage)."""
    out: dict = {}
    for r in rows:
        ts = r["ts"]
        if start_dt is not None and ts < start_dt:
            continue
        if end_dt is not None and ts >= end_dt:
            continue
        out[ts.strftime("%Y-%m-%d")] = r["odo_published"]
    return out


def _daily_deltas(daily_last_dict):
    """Compute day-over-day deltas from daily last readings."""
    sorted_dates = sorted(daily_last_dict.keys())
    deltas = []
    prev = None
    for d in sorted_dates:
        val = daily_last_dict[d]
        if prev is not None:
            delta_l = round((val - prev) * 1000, 1)
            deltas.append((d, delta_l, prev, val))
        prev = val
    return deltas


def _hourly_usage(rows, the_date):
    """Hourly usage for a specific day (by hour of capture_ts)."""
    start = datetime.combine(the_date, time(0, 0))
    end = start + timedelta(days=1)
    day_rows = [r for r in rows if start <= r["ts"] < end]

    # Find first and last reading per hour
    hour_first: dict = {}
    hour_last: dict = {}
    hour_all: dict = defaultdict(list)

    for r in day_rows:
        h = r["ts"].hour
        hour_all[h].append(r)
        if h not in hour_first:
            hour_first[h] = r
        hour_last[h] = r

    hourly = []
    prev_last = None
    for h in range(24):
        if h in hour_last:
            last_r = hour_last[h]
            usage_l = None
            if prev_last is not None and last_r["odo_published"] >= prev_last["odo_published"]:
                usage_l = round(
                    (last_r["odo_published"] - prev_last["odo_published"]) * 1000, 1
                )
            hourly.append(
                {
                    "hour": h,
                    "reading_m3": last_r["odo_published"],
                    "usage_l": usage_l,
                    "image_count": len(hour_all.get(h, [])),
                    "first_npos": hour_first[h]["npos"],
                    "last_npos": last_r["npos"],
                }
            )
            prev_last = last_r
        else:
            hourly.append(
                {"hour": h, "reading_m3": None, "usage_l": None, "image_count": 0}
            )
    return hourly


def _needle_wraps(npos_a, npos_b):
    """Count needle revolutions between two npos values (forward in time)."""
    if npos_a is None or npos_b is None:
        return None
    wraps = 0
    current = npos_a
    target = npos_b
    while target < current:
        wraps += 1
        target += 100
    return wraps


# ── investigation functions ────────────────────────────────────────────────


def investigate_aug1(rows):
    """Deep dive on 08/01 usage."""
    today = date.today()
    aug1 = date(2026, 8, 1)

    # Daily last readings for context
    daily_last = _daily_last(rows)
    deltas = _daily_deltas(daily_last)

    print("=" * 72)
    print("1. 08/01 DAILY USAGE INVESTIGATION")
    print("=" * 72)

    # Show daily deltas around Aug 1
    print("\nDaily usage (L) around Aug 1:")
    print(f"{'Date':<12} {'Usage (L)':>12} {'Reading (m³)':>15}")
    print("-" * 42)

    aug_dates = [(2026, 7, 28), (2026, 7, 29), (2026, 7, 30),
                 (2026, 7, 31), (2026, 8, 1), (2026, 8, 2), (2026, 8, 3)]
    aug_data = {}
    for d, delta_l, prev, val in deltas:
        aug_data[d] = (delta_l, val)
        if date.fromisoformat(d) in [date(*a) for a in aug_dates]:
            print(f"{d:<12} {delta_l:>12.1f} {val:>15.3f}")

    # Stats for all days in dataset
    all_deltas = [dl for _, dl, _, _ in deltas if dl is not None and dl >= 0 and dl <= MAX_DAILY_DELTA_L]
    if all_deltas:
        import statistics
        mean_l = statistics.mean(all_deltas)
        median_l = statistics.median(all_deltas)
        std_l = statistics.stdev(all_deltas) if len(all_deltas) > 1 else 0
        max_l = max(all_deltas)

        aug1_delta = aug_data.get("2026-08-01", (None, None))
        if aug1_delta[0] is not None:
            z_score = (aug1_delta[0] - mean_l) / std_l if std_l > 0 else 0
            print(f"\nAll-time daily stats ({len(all_deltas)} days):")
            print(f"  Mean:   {mean_l:.1f} L")
            print(f"  Median: {median_l:.1f} L")
            print(f"  StdDev: {std_l:.1f} L")
            print(f"  Max:    {max_l:.1f} L")
            print(f"\nAug 1: {aug1_delta[0]:.1f} L ({z_score:+.1f} sigma from mean)")

    # Hourly breakdown for Aug 1
    print(f"\n{'─' * 72}")
    print("Hourly breakdown for 08/01:")
    print(f"{'Hour':>5} {'Usage (L)':>10} {'Images':>8} {'First npos':>11} {'Last npos':>10} {'Reading':>12}")
    print("-" * 62)
    hourly = _hourly_usage(rows, aug1)
    for h in hourly:
        if h["image_count"] > 0:
            fnpos = h.get("first_npos", "?")
            lnpos = h.get("last_npos", "?")
            fnpos_str = str(fnpos) if fnpos is not None else "?"
            lnpos_str = str(lnpos) if lnpos is not None else "?"
            usage_str = f'{h["usage_l"]:.1f}' if h["usage_l"] is not None else "?"
            print(
                f'{h["hour"]:>5} {usage_str:>10} {h["image_count"]:>8} '
                f"{fnpos_str:>11} {lnpos_str:>10} {h['reading_m3']:>12.3f}"
            )
        elif h["usage_l"] is not None:
            # No images but inherited usage from previous hour's boundary
            pass

    # Needle-wrap authenticity check for Aug 1
    print(f"\n{'─' * 72}")
    print("Needle-wrap audit for 08/01 (checking for data artifacts):")
    aug1_start = datetime(2026, 8, 1)
    aug1_end = aug1_start + timedelta(days=1)
    aug1_rows = [r for r in rows if aug1_start <= r["ts"] < aug1_end]
    if len(aug1_rows) >= 2:
        prev_r = aug1_rows[0]
        for curr_r in aug1_rows[1:]:
            delta_m3 = curr_r["odo_published"] - prev_r["odo_published"]
            wraps = _needle_wraps(prev_r["npos"], curr_r["npos"])
            delta_l = delta_m3 * 1000
            if delta_l > 50:  # Flag any jump > 50 L
                expected_delta_m3_from_wraps = wraps / 100.0 if wraps is not None else None
                wrap_consistent = "✓" if expected_delta_m3_from_wraps is not None and abs(delta_m3 - expected_delta_m3_from_wraps) < 0.02 else "✗ MISMATCH"
                gap_min = (curr_r["ts"] - prev_r["ts"]).total_seconds() / 60
                print(
                    f"  {prev_r['ts'].strftime('%H:%M:%S')} → {curr_r['ts'].strftime('%H:%M:%S')}: "
                    f"Δ={delta_l:.0f}L  npos {prev_r['npos']}→{curr_r['npos']} ({wraps} wraps)  "
                    f"gap={gap_min:.0f}min  {wrap_consistent}"
                )
            prev_r = curr_r


def investigate_7am(rows):
    """Compare 7 AM usage across all days."""
    print("\n\n" + "=" * 72)
    print("2. 7 AM USAGE COMPARISON")
    print("=" * 72)

    # For each day, find last reading before 7 AM and first reading at/after 7 AM
    # Group by date
    by_date = defaultdict(list)
    for r in rows:
        d = r["ts"].date()
        by_date[d].append(r)

    seven_am_deltas = []
    for d in sorted(by_date.keys()):
        day_rows = by_date[d]
        t7 = datetime.combine(d, time(7, 0))

        before = [r for r in day_rows if r["ts"] < t7]
        after = [r for r in day_rows if r["ts"] >= t7]

        if before and after:
            last_before = before[-1]
            first_after = after[0]
            delta_l = (first_after["odo_published"] - last_before["odo_published"]) * 1000
            wraps = _needle_wraps(last_before["npos"], first_after["npos"])
            gap_min = (first_after["ts"] - last_before["ts"]).total_seconds() / 60
            seven_am_deltas.append(
                {
                    "date": d,
                    "delta_l": delta_l,
                    "before_ts": last_before["ts"],
                    "after_ts": first_after["ts"],
                    "before_npos": last_before["npos"],
                    "after_npos": first_after["npos"],
                    "wraps": wraps,
                    "gap_min": gap_min,
                    "before_reading": last_before["odo_published"],
                    "after_reading": first_after["odo_published"],
                }
            )

    if not seven_am_deltas:
        print("\n  No 7 AM boundary data found.")
        return

    # Today's 7 AM delta
    today = date.today()
    today_delta = next((d for d in seven_am_deltas if d["date"] == today), None)

    # Stats
    valid_deltas = [d["delta_l"] for d in seven_am_deltas if 0 <= d["delta_l"] <= MAX_DAILY_DELTA_L]
    if valid_deltas:
        import statistics
        mean_7 = statistics.mean(valid_deltas)
        median_7 = statistics.median(valid_deltas)
        std_7 = statistics.stdev(valid_deltas) if len(valid_deltas) > 1 else 0
        min_7 = min(valid_deltas)
        max_7 = max(valid_deltas)

        print(f"\n7 AM boundary stats ({len(valid_deltas)} days):")
        print(f"  Mean:   {mean_7:.1f} L")
        print(f"  Median: {median_7:.1f} L")
        print(f"  StdDev: {std_7:.1f} L")
        print(f"  Min:    {min_7:.1f} L")
        print(f"  Max:    {max_7:.1f} L")

        if today_delta:
            z = (today_delta["delta_l"] - mean_7) / std_7 if std_7 > 0 else 0
            print(f"\n  Today (2026-08-03) 7 AM delta: {today_delta['delta_l']:.1f} L ({z:+.1f} sigma)")
            print(f"    Before: {today_delta['before_ts'].strftime('%H:%M:%S')} "
                  f"reading={today_delta['before_reading']:.3f} npos={today_delta['before_npos']}")
            print(f"    After:  {today_delta['after_ts'].strftime('%H:%M:%S')} "
                  f"reading={today_delta['after_reading']:.3f} npos={today_delta['after_npos']}")
            print(f"    Gap: {today_delta['gap_min']:.0f} min  Wraps: {today_delta['wraps']}")

    # Show all 7 AM deltas
    print(f"\nAll 7 AM deltas (last {min(14, len(seven_am_deltas))} days):")
    print(f"{'Date':<12} {'Delta (L)':>10} {'Gap(min)':>9} {'npos before':>12} {'npos after':>11} {'Wraps':>6}")
    print("-" * 66)
    for d in seven_am_deltas[-14:]:
        marker = " ← TODAY" if d["date"] == today else ""
        print(
            f'{d["date"]} {d["delta_l"]:>10.1f} {d["gap_min"]:>9.0f} '
            f'{d["before_npos"]:>12} {d["after_npos"]:>11} {d["wraps"]:>6}{marker}'
        )

    # Check for suspicious 100L and 1000L multiples
    suspicious = []
    for d in seven_am_deltas:
        if d["delta_l"] > 0:
            if abs(d["delta_l"] - 100) < 5:
                suspicious.append((d["date"], d["delta_l"], "~100 L (1 rev)"))
            elif abs(d["delta_l"] - 200) < 5:
                suspicious.append((d["date"], d["delta_l"], "~200 L (2 rev)"))
            elif abs(d["delta_l"] - 300) < 5:
                suspicious.append((d["date"], d["delta_l"], "~300 L (3 rev)"))
            elif abs(d["delta_l"] - 1000) < 10:
                suspicious.append((d["date"], d["delta_l"], "~1000 L (integer jump)"))

    if suspicious:
        print(f"\nSuspicious near-multiples of 100L or 1000L:")
        for d, val, note in suspicious:
            print(f"  {d}: {val:.1f} L — {note}")


def investigate_daily_multiples(rows):
    """Check daily deltas for suspicious multiples of 100L and 1000L."""
    print("\n\n" + "=" * 72)
    print("3. SUSPICIOUS DAILY-DELTA PATTERNS (multiples of 100L / 1000L)")
    print("=" * 72)

    daily_last = _daily_last(rows)
    deltas = _daily_deltas(daily_last)

    suspects_100 = []
    suspects_1000 = []
    for d, delta_l, prev, val in deltas:
        if delta_l is None or delta_l <= 0 or delta_l > MAX_DAILY_DELTA_L:
            continue
        rem_100 = delta_l % 100
        if rem_100 < 5 or rem_100 > 95:
            if 90 <= delta_l <= 110:
                suspects_100.append((d, delta_l, "~100 L (1 rev)"))
            elif 190 <= delta_l <= 210:
                suspects_100.append((d, delta_l, "~200 L (2 rev)"))
            elif 290 <= delta_l <= 310:
                suspects_100.append((d, delta_l, "~300 L (3 rev)"))
            elif 390 <= delta_l <= 410:
                suspects_100.append((d, delta_l, "~400 L (4 rev)"))
            elif 490 <= delta_l <= 510:
                suspects_100.append((d, delta_l, "~500 L (5 rev)"))
        if abs(delta_l - 1000) < 10:
            suspects_1000.append((d, delta_l, "~1000 L (integer jump)"))

    if suspects_100:
        print("\nDays with usage near multiples of 100 L (possible revolution artifacts):")
        for d, val, note in suspects_100:
            print(f"  {d}: {val:.1f} L — {note}")
    else:
        print("\nNo suspect 100 L multiple patterns found.")

    if suspects_1000:
        print("\nDays with usage near 1000 L (possible integer-jump artifacts):")
        for d, val, note in suspects_1000:
            print(f"  {d}: {val:.1f} L — {note}")
    else:
        print("\nNo suspect 1000 L patterns found.")


# ── main ───────────────────────────────────────────────────────────────────


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("Loading all published readings from DB...")
    rows = _load_all_published()
    log.info("Loaded %d readings", len(rows))

    if not rows:
        print("No data found.")
        return

    investigate_aug1(rows)
    investigate_7am(rows)
    investigate_daily_multiples(rows)

    print("\n" + "=" * 72)
    print("Done.")


if __name__ == "__main__":
    main()