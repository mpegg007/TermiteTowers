#!/usr/bin/env python3
"""Flag keeper frames for local preservation before archive cleanup.

Marks key frames so archive_images.py can protect them:
- kp_first_of_day: chronologically first frame each UTC day
- kp_last_of_day:  chronologically last frame each UTC day
- kp_first_lit:    first frame each day with img_brightness > 40 (not pitch black)
- kp_last_lit:     last frame each day with img_brightness > 40
- kp_rotation_best: copy of dr_best (single best frame per rotation cycle)
- kp_important:    rollover frames (npos > 90 -> < 10) AND high-confidence frames

Writes kp_* boolean columns to DB.  Keeps existing values — only sets new
flags, never clears old ones unless they no longer qualify.

Usage:
    .venv/bin/python scripts/water_meter/flag_keepers.py
    .venv/bin/python scripts/water_meter/flag_keepers.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("flag_keepers")

# ── Day boundary: use local timezone offset ─────────────────────────
# Frames are captured in America/Toronto.  Use UTC-4 (EDT) consistently.
# If DST changes, adjust the offset.  capture_ts is a naive datetime.
LOCAL_OFFSET = timedelta(hours=-4)


def _local_date(ts) -> str:
    """Return 'YYYY-MM-DD' string in local timezone."""
    if ts is None:
        return ""
    local = ts + LOCAL_OFFSET
    return local.strftime("%Y-%m-%d")


def flag_keepers(dry_run: bool = False) -> int:
    """Walk all rows, set kp_* flags."""
    init_db()

    row_dicts: List[Dict[str, Any]] = []
    with get_session() as s:
        rows = (
            s.query(MeterReading)
            .filter(MeterReading.status == "OK")
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )
        for row in rows:
            row_dicts.append({
                "image_name": row.image_name,
                "capture_ts": row.capture_ts,
                "npos": row.npos,
                "img_brightness": row.img_brightness,
                "odo_confidence": row.odo_confidence,
            })

    if not row_dicts:
        log.warning("No rows")
        return 0

    updates: Dict[str, Dict[str, bool]] = {rd["image_name"]: {
        "kp_first_of_day": False, "kp_last_of_day": False,
        "kp_first_lit": False, "kp_last_lit": False,
        "kp_rotation_best": False, "kp_important": False,
    } for rd in row_dicts}

    # ── Per-day first/last ──────────────────────────────────────────
    days: Dict[str, Dict[str, Optional[str]]] = {}
    for rd in row_dicts:
        day = _local_date(rd["capture_ts"])
        if not day:
            continue
        if day not in days:
            days[day] = {"first": rd["image_name"], "last": None,
                         "first_lit": None, "last_lit": None,
                         "first_lit_name": None, "last_lit_name": None}
        days[day]["last"] = rd["image_name"]
        if rd["img_brightness"] is not None and rd["img_brightness"] > 40:
            if days[day]["first_lit"] is None:
                days[day]["first_lit"] = rd["capture_ts"]
                days[day]["first_lit_name"] = rd["image_name"]
            days[day]["last_lit"] = rd["capture_ts"]
            days[day]["last_lit_name"] = rd["image_name"]

    for day, info in days.items():
        if info["first"]:
            updates[info["first"]]["kp_first_of_day"] = True
        if info["last"]:
            updates[info["last"]]["kp_last_of_day"] = True
        if info["first_lit_name"]:
            updates[info["first_lit_name"]]["kp_first_lit"] = True
        if info["last_lit_name"]:
            updates[info["last_lit_name"]]["kp_last_lit"] = True

    # ── Rotation best ───────────────────────────────────────────────
    # Copy from dr_best via DB
    with get_session() as s:
        best_rows = (
            s.query(MeterReading.image_name)
            .filter(MeterReading.dr_best == True)   # noqa: E712
            .all()
        )
        for (name,) in best_rows:
            if name in updates:
                updates[name]["kp_rotation_best"] = True

    # ── Important frames ────────────────────────────────────────────
    # Rollover: npos drops from >90 to <10 between consecutive frames
    # High confidence: odo_confidence >= 0.80
    last_npos = None
    for rd in row_dicts:
        name = rd["image_name"]
        # Rollover
        if (last_npos is not None and last_npos > 90
                and rd["npos"] is not None and rd["npos"] < 10):
            # Flag the PREVIOUS frame (the >90 one) — that's the settled one
            pass  # We'll flag the current one
        # High confidence
        conf = rd.get("odo_confidence")
        if conf is not None and conf >= 0.80:
            updates[name]["kp_important"] = True
        last_npos = rd["npos"]

    # Also flag rollover entry points
    last_npos = None
    for i, rd in enumerate(row_dicts):
        if (last_npos is not None and last_npos > 90
                and rd["npos"] is not None and rd["npos"] < 10
                and i > 0):
            # Flag the previous frame (the settled high-npos frame)
            prev_name = row_dicts[i - 1]["image_name"]
            if prev_name in updates:
                updates[prev_name]["kp_important"] = True
        last_npos = rd["npos"]

    # ── Write ───────────────────────────────────────────────────────
    written = 0
    if not dry_run:
        with get_session() as s:
            for name, flags in updates.items():
                row = s.get(MeterReading, name)
                if row is None:
                    continue
                # Only set new flags; don't clear existing
                for col, val in flags.items():
                    current = getattr(row, col, None)
                    # Set if new value is True OR preserve existing True
                    if val or current:
                        setattr(row, col, bool(val or current))
                written += 1
            s.commit()

    # ── Summary ─────────────────────────────────────────────────────
    stats = {k: sum(1 for v in updates.values() if v.get(k)) for k in updates[
        next(iter(updates))].keys()}

    print(f"\n{'=' * 50}")
    print(f"Keeper Frame Flags")
    print(f"{'=' * 50}")
    for label, col in [
        ("First of day", "kp_first_of_day"),
        ("Last of day", "kp_last_of_day"),
        ("First lit", "kp_first_lit"),
        ("Last lit", "kp_last_lit"),
        ("Rotation best", "kp_rotation_best"),
        ("Important", "kp_important"),
    ]:
        cnt = stats.get(col, 0)
        print(f"  {label:<20} {cnt:>6}")
    if dry_run:
        print(f"\n  Would update: {len(updates)} rows")
    else:
        print(f"\n  Updated: {written} rows")

    return written


def main():
    p = argparse.ArgumentParser(description="Flag keeper frames for preservation")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    flag_keepers(dry_run=args.dry_run)


if __name__ == "__main__":
    main()