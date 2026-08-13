#!/usr/bin/env python3
"""Detect needle rotation cycles and flag the single best frame per cycle.

Scans all rows chronologically by capture_ts.  A rotation cycle's "settled zone"
begins when npos enters 85-10 (drum fully visible).  It ends when npos passes
into the 30-70 mid-zone (drum rotating).  Within each settled zone, the frame
with best image quality (sharpness + ideal exposure + closest to npos 0) is
marked ``dr_best = True``.

Writes ``dr_cycle``, ``dr_zone``, ``dr_enter``, ``dr_exit``, ``dr_flutter``,
``dr_best``, ``dr_score``, and ``dr_pos5`` to DB.

Usage:
    .venv/bin/python scripts/water_meter/pick_rotation_anchors.py
    .venv/bin/python scripts/water_meter/pick_rotation_anchors.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("pick_rotation")

# ── Cycle zone thresholds ──────────────────────────────────────────
SETTLED_MIN = 85
SETTLED_MAX = 10
MID_MIN = 30
MID_MAX = 70

# ── Quality scoring weights ────────────────────────────────────────
W_SHARPNESS = 0.30
W_EXPOSURE  = 0.25
W_NPOS      = 0.45


def _exposure_score(brightness: Optional[int]) -> float:
    if brightness is None:
        return 0.5
    low, high = 120, 180
    if low <= brightness <= high:
        return 1.0
    if brightness < low:
        return max(0.0, brightness / low)
    return max(0.0, (255 - brightness) / (255 - high))


def _npos_score(npos: Optional[int]) -> float:
    if npos is None:
        return 0.0
    dist = npos if npos <= 50 else 100 - npos
    return max(0.0, 1.0 - dist / 50.0)


def _quality_score(rd: Dict[str, Any]) -> float:
    sobel = rd.get("odo_sobel_mean") or 0
    sharpness = min(1.0, sobel / 80.0)
    exposure = _exposure_score(rd.get("odo_brightness"))
    npos_prox = _npos_score(rd.get("npos"))
    return (W_SHARPNESS * sharpness +
            W_EXPOSURE * exposure +
            W_NPOS * npos_prox)


def pick_rotation_anchors(dry_run: bool = False) -> int:
    init_db()

    row_dicts: List[Dict[str, Any]] = []
    with get_session() as s:
        rows = (
            s.query(MeterReading)
            .filter(MeterReading.status == "OK")
            .filter(MeterReading.npos.isnot(None))
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )
        for row in rows:
            row_dicts.append({
                "image_name": row.image_name,
                "npos": row.npos,
                "odo_sobel_mean": row.odo_sobel_mean,
                "odo_brightness": row.odo_brightness,
                "digits": row.digits,
            })

    if not row_dicts:
        log.warning("No rows found")
        return 0

    log.info("Scanning %d rows for rotation cycles", len(row_dicts))

    cycle_id = 0
    in_settled = False
    cycle_candidates: List[int] = []
    flutter_detected = False
    last_npos: Optional[int] = None
    total_cycles = 0

    updates: Dict[str, Dict[str, Any]] = {}

    for i, rd in enumerate(row_dicts):
        npos = rd["npos"]

        # ── Detect flutter ──
        if in_settled and last_npos is not None and npos is not None:
            if npos - last_npos < -5:
                flutter_detected = True

        # ── Entering settled zone ──
        if not in_settled:
            if npos is not None and (npos >= SETTLED_MIN or npos <= SETTLED_MAX):
                in_settled = True
                cycle_id += 1
                cycle_candidates = [i]
                flutter_detected = False
        else:
            # Already settled
            if npos is not None and (npos >= SETTLED_MIN or npos <= SETTLED_MAX):
                cycle_candidates.append(i)
            elif npos is not None and MID_MIN <= npos <= MID_MAX:
                # Exiting settled zone — pick best
                if cycle_candidates:
                    best_idx = max(cycle_candidates,
                                   key=lambda idx: _quality_score(row_dicts[idx]))
                    total_cycles += 1
                    enter_npos = (row_dicts[cycle_candidates[0]]["npos"]
                                  if cycle_candidates else None)
                    for ci in cycle_candidates:
                        r_ci = row_dicts[ci]
                        sc = _quality_score(r_ci)
                        updates[r_ci["image_name"]] = {
                            "dr_cycle": cycle_id,
                            "dr_zone": "settled",
                            "dr_enter": enter_npos,
                            "dr_exit": npos,
                            "dr_flutter": flutter_detected,
                            "dr_best": (ci == best_idx),
                            "dr_score": round(sc, 4),
                            "dr_pos5": (int(r_ci["digits"][5])
                                        if r_ci.get("digits") and len(r_ci["digits"]) == 6
                                        else None),
                        }
                in_settled = False
                cycle_candidates = []
                flutter_detected = False
            elif npos is not None:
                # npos 11-29: ambiguous, keep in settled
                cycle_candidates.append(i)

        last_npos = npos

    # ── Handle still-open cycle ──
    if in_settled and cycle_candidates:
        best_idx = max(cycle_candidates,
                       key=lambda idx: _quality_score(row_dicts[idx]))
        total_cycles += 1
        enter_npos = (row_dicts[cycle_candidates[0]]["npos"]
                      if cycle_candidates else None)
        for ci in cycle_candidates:
            r_ci = row_dicts[ci]
            sc = _quality_score(r_ci)
            updates[r_ci["image_name"]] = {
                "dr_cycle": cycle_id,
                "dr_zone": "settled",
                "dr_enter": enter_npos,
                "dr_exit": None,
                "dr_flutter": flutter_detected,
                "dr_best": (ci == best_idx),
                "dr_score": round(sc, 4),
                "dr_pos5": (int(r_ci["digits"][5])
                            if r_ci.get("digits") and len(r_ci["digits"]) == 6
                            else None),
            }

    # ── Defaults for non-settled rows ──
    for rd in row_dicts:
        name = rd["image_name"]
        if name not in updates:
            updates[name] = {
                "dr_cycle": None, "dr_zone": "transit",
                "dr_enter": None, "dr_exit": None,
                "dr_flutter": None, "dr_best": False,
                "dr_score": None, "dr_pos5": None,
            }

    # ── Write ───────────────────────────────────────────────────────
    if not dry_run:
        with get_session() as s:
            for name, vals in updates.items():
                row = s.get(MeterReading, name)
                if row is None:
                    continue
                for k, v in vals.items():
                    setattr(row, k, v)
            s.commit()

    # ── Summary ─────────────────────────────────────────────────────
    best_count = sum(1 for v in updates.values() if v.get("dr_best"))
    flutter_count = sum(1 for v in updates.values() if v.get("dr_flutter"))

    print(f"\n{'=' * 60}")
    print(f"Rotation Anchor Results")
    print(f"{'=' * 60}")
    print(f"  Total rows scanned:     {len(row_dicts)}")
    print(f"  Rotation cycles found:  {total_cycles}")
    print(f"  Best anchors selected:  {best_count}")
    print(f"  Flutter cycles:         {flutter_count}")
    if dry_run:
        print(f"  Would write:            {len(updates)} rows")
    else:
        print(f"  Written to DB:          {len(updates)} rows")

    best_rows = [(n, v) for n, v in updates.items() if v.get("dr_best")]
    if best_rows[:10]:
        print(f"\n  Top 10 anchor frames:")
        print(f"  {'Image':<50} {'Cycle':>5} {'npos':>4} {'Score':>8} {'p5':>3}")
        print(f"  {'─' * 72}")
        for name, vals in sorted(best_rows,
                                 key=lambda x: x[1].get("dr_cycle") or 0)[:10]:
            r_rd = next((r for r in row_dicts if r["image_name"] == name), None)
            rpos = r_rd["npos"] if r_rd else "?"
            print(f"  {name:<50} {vals['dr_cycle']:>5} {str(rpos):>4} "
                  f"{vals['dr_score'] or 0:>8.4f} {str(vals.get('dr_pos5','?')):>3}")

    return len(updates)


def main():
    p = argparse.ArgumentParser(
        description="Pick single best frame per needle rotation cycle")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    pick_rotation_anchors(dry_run=args.dry_run)


if __name__ == "__main__":
    main()