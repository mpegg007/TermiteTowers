#!/usr/bin/env python3
"""
calc_needle_readings.py — combine visual odometer digits with needle tracking.

The digits field comes from decode_odo.py's visual odometer recognition.
It is the authoritative integer source.  This script:
1. Reads digits from visually-decoded frames.
2. Tracks needle wraps (npos 99→0) between visual reads for sub-revolution precision.
3. When consecutive visual reads disagree with needle tracking, trusts visual.
4. odo_published = visual_integer + needle_fraction (npos/1000).

By default runs incrementally — finds the last row with odo_needle already
computed and continues from there.  Use --from YYYYMMDD to recalculate from
a specific date.

Usage:
    .venv/bin/python scripts/water_meter/calc_needle_readings.py
    .venv/bin/python scripts/water_meter/calc_needle_readings.py --dry-run
    .venv/bin/python scripts/water_meter/calc_needle_readings.py --from 20260801
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("calc_needle")

# ── Plausibility guard ──────────────────────────────────────────────
# decode_odo sometimes misreads the odometer digits (e.g. "035495" when
# the true reading is 3540.x). calc_needle_readings must not follow those
# bad reads or the published value spikes wildly (3540 -> 3549 -> 3540).
# A residential meter never reads backwards and never advances faster
# than a few m³/hour, so we reject visual reads that go backwards or
# jump ahead beyond MAX_RATE_M3_PER_HOUR * elapsed hours, with a floor
# (MAX_SHORT_JUMP_M3) so tenths-wheel moves in short gaps are never
# rejected.  A tenths-wheel rollover is only +0.1 m³; the floor must not
# be much larger than that, or a single misread odometer frame (e.g.
# "035416" decoded as 3541.6 when the needle at npos 8 says ~3541.008)
# gets accepted as a +0.6 m³ jump and ratchets the whole line up, which
# then can never come back down (backward reads are rejected too).
MAX_RATE_M3_PER_HOUR = 2.0
MAX_SHORT_JUMP_M3 = 0.2


def _parse_reading(val: float) -> Tuple[int, int]:
    """Split a reading like 3541.131 into (integer, tenths)."""
    i = int(val)
    t = int(round((val - i) * 10)) % 10
    return i, t


def _load_rows(session, start_ts: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Load rows from capture_ts > start_ts (or all if None)."""
    q = session.query(MeterReading).order_by(MeterReading.capture_ts.asc())
    if start_ts is not None:
        q = q.filter(MeterReading.capture_ts > start_ts)
    rows = q.all()

    out = []
    for row in rows:
        visual_int = None
        visual_tenths = None
        if row.digits and len(row.digits) == 6:
            try:
                visual_int = int(row.digits[:5])
                visual_tenths = int(row.digits[5])
            except (ValueError, IndexError):
                pass

        dr_anchor = (row.dr_best is True and row.dr_pos5 is not None)

        out.append({
            "image_name": row.image_name,
            "npos": row.npos,
            "odo_manual": float(row.odo_manual) if row.odo_manual else None,
            "capture_ts": row.capture_ts,
            "visual_int": visual_int,
            "visual_tenths": visual_tenths,
            "dr_anchor": dr_anchor,
            "dr_pos5": row.dr_pos5,
        })

    return out


def _seed_from_db(session, before_ts: datetime) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Seed (last_int, last_tenths, last_npos) from the last reading before before_ts."""
    seed_row = (
        session.query(MeterReading)
        .filter(MeterReading.capture_ts < before_ts)
        .filter(MeterReading.odo_published.isnot(None))
        .order_by(MeterReading.capture_ts.desc())
        .first()
    )
    if seed_row and seed_row.odo_published is not None:
        vi, vt = _parse_reading(float(seed_row.odo_published))
        log.info("Seeded from %s: integer=%d tenths=%d npos=%s",
                 seed_row.image_name, vi, vt, seed_row.npos)
        return vi, vt, seed_row.npos
    return None, None, None


def calc_needle_readings(dry_run: bool = False,
                         from_date: Optional[str] = None) -> Tuple[int, int]:
    """Walk rows chronologically, compute odo_needle/odo_published.

    Default: incremental (continues from last computed row).
    --from YYYYMMDD: recalculate from that date onwards, seeded from prior data.
    """
    init_db()

    with get_session() as s:
        if from_date:
            if not re.match(r"^\d{8}$", from_date):
                log.error("--from must be YYYYMMDD format, got '%s'", from_date)
                return 0, 0
            window_start = datetime(
                int(from_date[:4]), int(from_date[4:6]), int(from_date[6:8]))
            all_rows = _load_rows_from(s, window_start)
            last_vi, last_vt, last_npos = _seed_from_db(s, window_start)
        else:
            # Incremental
            last_done = (
                s.query(MeterReading)
                .filter(MeterReading.odo_needle.isnot(None))
                .order_by(MeterReading.capture_ts.desc())
                .first()
            )
            if last_done is None:
                all_rows = _load_rows(s)
                log.info("No prior odo_needle — full calc (%d rows)", len(all_rows))
                last_vi, last_vt, last_npos = None, None, None
            else:
                last_ts = last_done.capture_ts
                all_rows = _load_rows(s, start_ts=last_ts)
                log.info("Incremental from %s — %d new rows",
                         last_ts.strftime("%Y-%m-%d %H:%M") if last_ts else "?",
                         len(all_rows))
                if not all_rows:
                    log.info("No new rows — nothing to do")
                    return 0, 0
                if last_done.odo_published is not None:
                    last_vi, last_vt = _parse_reading(float(last_done.odo_published))
                    last_npos = last_done.npos
                    log.info("Seeded: integer=%d tenths=%d npos=%s",
                             last_vi, last_vt, last_npos)
                else:
                    last_vi, last_vt, last_npos = None, None, None

    if not all_rows:
        return 0, 0

    # ── Forward propagation ───────────────────────────────────────────
    visual_written = 0
    propagated = 0
    false_drops = 0
    duplicates = 0
    rejected_visual = 0
    last_wrap_ts = None
    last_state_ts = None
    last_published = None

    updates: Dict[str, float] = {}
    rejects: Dict[str, str] = {}

    def _last_value() -> Optional[float]:
        if last_vi is None:
            return None
        return last_vi + (last_vt if last_vt is not None else 0) / 10.0

    def _plausible_jump(new_val: float, prev_val: Optional[float],
                        gap_seconds: Optional[float]) -> bool:
        """True if a visually-decoded jump is physically possible for a meter.

        Rejects backwards moves and jumps beyond MAX_RATE_M3_PER_HOUR, with a
        floor so tenths-wheel increments inside short gaps are never rejected.
        """
        if prev_val is None:
            return True
        delta = new_val - prev_val
        if delta < -0.001:
            return False  # a meter can never read backwards
        if gap_seconds is None or gap_seconds <= 0:
            gap_seconds = 15.0
        max_delta = max(MAX_SHORT_JUMP_M3,
                        MAX_RATE_M3_PER_HOUR * (gap_seconds / 3600.0))
        return delta <= max_delta

    for row in all_rows:
        npos = row["npos"]
        if npos is None:
            # Dark / failed frame — no needle info.  Carry the last known
            # value forward until a valid frame appears.
            if last_published is not None:
                updates[row["image_name"]] = last_published
                propagated += 1
            continue

        # Skip consecutive identical npos (no new needle info) — UNLESS the
        # row carries a manual reading or rotation anchor that must be honored.
        if last_npos is not None and npos == last_npos:
            if (row["odo_manual"] is None
                    and not (row["dr_anchor"] and row["dr_pos5"] is not None)):
                duplicates += 1
                if last_vi is not None and last_vt is not None:
                    updates[row["image_name"]] = last_vi + last_vt / 10.0 + npos / 1000.0
                continue

        # Needle wrap
        now_ts = row["capture_ts"]
        if (last_npos is not None and last_npos > 85 and npos < 10
                and last_vi is not None):
            if (last_wrap_ts is None
                    or (now_ts - last_wrap_ts).total_seconds() > 300):
                last_vt = (last_vt + 1) % 10
                if last_vt == 0:
                    last_vi += 1
                last_wrap_ts = now_ts
                last_state_ts = now_ts
        elif last_npos is not None and npos < last_npos - 50:
            false_drops += 1

        gap_seconds = ((now_ts - last_state_ts).total_seconds()
                       if last_state_ts is not None else None)

        pinned_value = None

        # 1. Manual reading: GROUND TRUTH (user-confirmed) — highest authority.
        #    odo_manual is never overwritten by calc; it pins the published
        #    value exactly for that frame and seeds the propagation from it.
        if row["odo_manual"] is not None:
            val = row["odo_manual"]
            last_vi = int(val)
            last_vt = int(round((val - last_vi) * 10)) % 10
            last_state_ts = now_ts
            pinned_value = float(val)

        # 2. Rotation anchor: trusted tenths (user-confirmed rollover)
        elif row["dr_anchor"] and row["dr_pos5"] is not None:
            anchor_tenths = row["dr_pos5"]
            if last_vt is not None and last_vt != anchor_tenths:
                log.info("  Anchor @ %s: tenths %d → %d",
                         row["image_name"], last_vt, anchor_tenths)
            last_vt = anchor_tenths
            # Integer only from visual if plausible — anchors pin the tenths,
            # they don't justify a wild odometer jump.
            if row["visual_int"] is not None and row["visual_int"] != 3532:
                cand = row["visual_int"] + (row["visual_tenths"] or 0) / 10.0
                if _plausible_jump(cand, _last_value(), gap_seconds):
                    if last_vi != row["visual_int"]:
                        last_vi = row["visual_int"]
                elif last_vi is None:
                    last_vi = row["visual_int"]
            last_state_ts = now_ts

        # 3. Visual read reset — guarded against implausible jumps
        elif row["visual_int"] is not None and row["visual_int"] != 3532:
            cand = row["visual_int"] + (row["visual_tenths"] or 0) / 10.0
            prev = _last_value()
            if _plausible_jump(cand, prev, gap_seconds):
                last_vi = row["visual_int"]
                if row["visual_tenths"] is not None:
                    last_vt = row["visual_tenths"]
                visual_written += 1
                last_state_ts = now_ts
            else:
                rejected_visual += 1
                reason = (f"visual {cand:.3f} vs {prev:.3f}"
                          if prev is not None else f"visual {cand:.3f}")
                rejects[row["image_name"]] = reason

        if last_vi is not None:
            safe_tenths = last_vt if last_vt is not None else 0
            if pinned_value is not None:
                updates[row["image_name"]] = pinned_value
            else:
                updates[row["image_name"]] = last_vi + safe_tenths / 10.0 + npos / 1000.0
            last_published = updates[row["image_name"]]
            propagated += 1

        last_npos = npos

    log.info("Forward: %d visual resets, %d propagated, %d false drops, %d duplicates, %d rejected visual",
             visual_written, propagated - visual_written, false_drops, duplicates, rejected_visual)
    if rejects:
        log.warning("Rejected %d implausible visual reads (auto-corrected by propagation)",
                    len(rejects))

    if propagated > 0 and all_rows:
        final_name = all_rows[-1]["image_name"]
        if final_name in updates:
            log.info("Final reading: %.3f m³", updates[final_name])

    # ── Write ─────────────────────────────────────────────────────────
    updated_needle = 0
    updated_published = 0
    # Track which rows had their own visual read (not just propagated)
    visual_trusted_names = set()
    for r in all_rows:
        if r["visual_int"] is not None and r["visual_int"] != 3532:
            visual_trusted_names.add(r["image_name"])

    def _clear_flag(notes_raw, key):
        if not notes_raw:
            return notes_raw
        try:
            notes = json.loads(notes_raw) if isinstance(notes_raw, str) else notes_raw
        except (json.JSONDecodeError, TypeError):
            return notes_raw
        if not isinstance(notes, dict) or key not in notes:
            return notes_raw
        notes.pop(key, None)
        return json.dumps(notes)

    if not dry_run:
        with get_session() as s:
            for name, val in updates.items():
                row = s.get(MeterReading, name)
                if not row:
                    continue
                if row.odo_needle != val:
                    row.odo_needle = val
                    updated_needle += 1
                if row.odo_published != val:
                    row.odo_published = val
                    updated_published += 1
                if row.odo_reading is None or abs(row.odo_reading - val) > 0.1:
                    row.odo_reading = val
                    row.reading = val
                # ── cn_ prefixed copies ──
                row.cn_needle = val
                row.cn_published = val
                row.cn_visual_trusted = (name in visual_trusted_names)
                if row.odo_manual is not None:
                    row.cn_manual = float(row.odo_manual)
                # The guard auto-fixes rejected reads via propagation, so a row
                # that now has a value no longer needs manual review — clear any
                # stale calc_reject marker left by earlier runs.
                if "calc_reject" in (row.notes or ""):
                    row.notes = _clear_flag(row.notes, "calc_reject")
            s.commit()
        log.info("Wrote %d odo_needle, %d odo_published",
                 updated_needle, updated_published)
    else:
        updated_needle = len(updates)

    return len(all_rows), updated_needle


def _load_rows_from(session, window_start: datetime) -> List[Dict[str, Any]]:
    """Load rows with capture_ts >= window_start."""
    rows = (
        session.query(MeterReading)
        .filter(MeterReading.capture_ts >= window_start)
        .order_by(MeterReading.capture_ts.asc())
        .all()
    )
    out = []
    for row in rows:
        visual_int = None
        visual_tenths = None
        if row.digits and len(row.digits) == 6:
            try:
                visual_int = int(row.digits[:5])
                visual_tenths = int(row.digits[5])
            except (ValueError, IndexError):
                pass
        dr_anchor = (row.dr_best is True and row.dr_pos5 is not None)
        out.append({
            "image_name": row.image_name,
            "npos": row.npos,
            "odo_manual": float(row.odo_manual) if row.odo_manual else None,
            "capture_ts": row.capture_ts,
            "visual_int": visual_int,
            "visual_tenths": visual_tenths,
            "dr_anchor": dr_anchor,
            "dr_pos5": row.dr_pos5,
        })
    return out


def main():
    p = argparse.ArgumentParser(
        description="Calc needle readings — visual digits + needle wraps")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--from", dest="from_date", metavar="YYYYMMDD",
                   help="Recalculate from this date instead of incremental")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    total, updated = calc_needle_readings(dry_run=args.dry_run,
                                          from_date=args.from_date)
    print(f"\nTotal rows: {total}  Updated odo_needle: {updated}")


if __name__ == "__main__":
    main()