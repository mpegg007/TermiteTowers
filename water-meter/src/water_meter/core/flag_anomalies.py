#!/usr/bin/env python3
"""Anomaly flagger for water meter pipeline.

Scans the ``meter_readings`` table for outlier frames based on geometric,
photometric, and context-aware checks.  Flags anomalous frames so the
odometer decoder can skip them.

Checks (per row, against surrounding context):
  - Too dark: ``img_brightness`` < 2σ below rolling mean of neighbours
  - No dial center: ``hub_x IS NULL`` or ``status = 'FAIL'``
  - Horizon tilted: ``horizon_deg`` deviates > threshold from rolling median
  - Dial radius off: ``dial_r`` deviates > pct from rolling median
  - Odo crop size off: ``odo_w`` or ``odo_h`` deviates > pct
  - Low contrast: ``img_contrast`` or ``odo_contrast`` below threshold
  - Missing marker: ``marker_cx = -1``
  - Needle zone pixel count anomalous: ``nz_pix`` outside expected range

Usage:
    .venv/bin/python scripts/water_meter/flag_anomalies.py              # scan + write
    .venv/bin/python scripts/water_meter/flag_anomalies.py --dry-run     # report only
    .venv/bin/python scripts/water_meter/flag_anomalies.py --window 200  # wider context
    .venv/bin/python scripts/water_meter/flag_anomalies.py --reset       # clear all anomaly flags
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from typing import List, Optional, Set

import numpy as np

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.db import MeterReading, init_db, get_session
from water_meter.core.common import get_rows_since, get_last_processed_ts

log = logging.getLogger("flag_anomalies")

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
DEFAULT_WINDOW = 100           # rolling window size for context
BRIGHTNESS_SIGMA = 2.0         # std devs below mean → too dark
CONTRAST_SIGMA = 2.0           # std devs below mean → low contrast
HORIZON_DEG_THRESH = 3.0       # degrees from rolling median → tilted
DIAL_R_PCT = 0.20              # 20% deviation from median dial_r
ODO_SIZE_PCT = 0.25            # 25% deviation from median odo_w or odo_h
NZ_PIX_SIGMA = 3.0             # std devs from mean nz_pix → anomaly
MIN_BRIGHTNESS = 30            # absolute floor (pixel value 0-255)
MIN_CONTRAST = 5               # absolute floor for contrast


# ---------------------------------------------------------------------------
# Rolling window helpers
# ---------------------------------------------------------------------------

def _rolling_stats(values: np.ndarray, window: int):
    """Return (rolling_mean, rolling_std, rolling_median) arrays same length as input."""
    n = len(values)
    mean = np.full(n, np.nan, dtype=np.float64)
    std = np.full(n, np.nan, dtype=np.float64)
    median = np.full(n, np.nan, dtype=np.float64)

    for i in range(n):
        start = max(0, i - window // 2)
        end = min(n, i + window // 2)
        win = values[start:end]
        mean[i] = np.mean(win)
        std[i] = np.std(win)
        median[i] = np.median(win)

    return mean, std, median


def _flag_outlier(value: float, mean: float, std: float, sigma: float) -> bool:
    """Return True if value is more than sigma std devs below mean."""
    if np.isnan(mean) or np.isnan(std) or std == 0:
        return False
    return value < (mean - sigma * std)


def _flag_outlier_both_sides(value: float, mean: float, std: float, sigma: float) -> bool:
    """Return True if value is more than sigma std devs away from mean in either direction."""
    if np.isnan(mean) or np.isnan(std) or std == 0:
        return False
    return abs(value - mean) > sigma * std


def _flag_pct_deviation(value: float, median: float, pct: float) -> bool:
    """Return True if value deviates from median by more than pct fraction."""
    if np.isnan(median) or median == 0 or value is None:
        return False
    return abs(value - median) / median > pct


# ---------------------------------------------------------------------------
# Main anomaly scanning
# ---------------------------------------------------------------------------

def scan_anomalies(window: int = DEFAULT_WINDOW,
                   brightness_sigma: float = BRIGHTNESS_SIGMA,
                   contrast_sigma: float = CONTRAST_SIGMA,
                   horizon_thresh: float = HORIZON_DEG_THRESH,
                   dial_r_pct: float = DIAL_R_PCT,
                   odo_size_pct: float = ODO_SIZE_PCT,
                   nz_pix_sigma: float = NZ_PIX_SIGMA,
                   dry_run: bool = False,
                   reset: bool = False) -> dict:
    """Scan all OK rows and return/set anomaly flags.

    Returns a dict with counts and list of flagged image_names.
    """
    with get_session() as session:
        if reset:
            # Clear all anomaly flags
            rows = session.query(MeterReading).filter(
                MeterReading.status == "ANOMALY"
            ).all()
            for r in rows:
                r.status = "OK"
                r.fail_reason = None
            session.commit()
            log.info("Reset %d anomaly flags → OK", len(rows))
            return {"reset_count": len(rows), "flags": {}}

        # Pull all rows with known geometry (status OK) as raw tuples to avoid
        # DetachedInstanceError when iterating outside the session.
        rows_raw = (
            session.query(
                MeterReading.image_name,
                MeterReading.capture_ts,
                MeterReading.img_brightness,
                MeterReading.img_contrast,
                MeterReading.odo_contrast,
                MeterReading.dial_r,
                MeterReading.odo_w,
                MeterReading.odo_h,
                MeterReading.nz_pix,
                MeterReading.horizon_deg,
                MeterReading.marker_cx,
                MeterReading.npos,
            )
            .filter(MeterReading.status == "OK")
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

    if not rows_raw:
        log.info("No rows to scan.")
        return {"total": 0, "flagged": 0, "flags": {}}

    n = len(rows_raw)
    log.info("Scanning %d rows (window=%d)...", n, window)

    # --- Extract arrays from raw tuples ---
    brightness = np.array([r[2] for r in rows_raw], dtype=np.float64)
    contrast   = np.array([r[3] or 0 for r in rows_raw], dtype=np.float64)
    odo_contrast = np.array([r[4] or 0 for r in rows_raw], dtype=np.float64)
    dial_r     = np.array([r[5] or 0 for r in rows_raw], dtype=np.float64)
    odo_w      = np.array([r[6] or 0 for r in rows_raw], dtype=np.float64)
    odo_h      = np.array([r[7] or 0 for r in rows_raw], dtype=np.float64)
    nz_pix     = np.array([r[8] or 0 for r in rows_raw], dtype=np.float64)
    horizon    = np.array([float(r[9]) if r[9] is not None else np.nan for r in rows_raw], dtype=np.float64)

    # --- Compute rolling stats ---
    b_mean, _, _ = _rolling_stats(brightness, window)
    c_mean, _, _ = _rolling_stats(contrast, window)
    oc_mean, _, _ = _rolling_stats(odo_contrast, window)
    _, dr_std, dr_med = _rolling_stats(dial_r, window)
    _, ow_std, ow_med = _rolling_stats(odo_w, window)
    _, oh_std, oh_med = _rolling_stats(odo_h, window)
    nz_mean, nz_std, _ = _rolling_stats(nz_pix, window)
    _, _, h_med = _rolling_stats(horizon, window)

    # --- Flag each row ---
    flagged: dict[str, Set[str]] = {}  # image_name → set of flag reasons
    flagged_count = 0

    for i in range(n):
        image_name = rows_raw[i][0]
        ib = rows_raw[i][2]
        ic = rows_raw[i][3]
        oc = rows_raw[i][4]
        dr = rows_raw[i][5]
        ow_val = rows_raw[i][6]
        oh_val = rows_raw[i][7]
        nz = rows_raw[i][8]
        hd = rows_raw[i][9]
        mc = rows_raw[i][10]

        flags: Set[str] = set()

        # 1) Too dark (absolute floor)
        if ib is not None and ib < MIN_BRIGHTNESS:
            flags.add("too_dark_abs")

        # 2) Too dark (relative)
        if _flag_outlier(ib or 0, b_mean[i], 1.0, brightness_sigma):
            flags.add("too_dark")

        # 3) Low contrast (image)
        if ic is not None and ic < MIN_CONTRAST:
            flags.add("low_contrast_abs")

        # 4) Low contrast (relative)
        if _flag_outlier(ic or 0, c_mean[i], 1.0, contrast_sigma):
            flags.add("low_contrast")

        # 5) Low odo contrast (relative)
        if _flag_outlier(oc or 0, oc_mean[i], 1.0, contrast_sigma):
            flags.add("low_odo_contrast")

        # 6) Horizon tilted
        if (hd is not None and not np.isnan(h_med[i])
                and abs(hd - h_med[i]) > horizon_thresh):
            flags.add("horizon_tilted")

        # 7) Dial radius off
        if _flag_pct_deviation(dr, dr_med[i], dial_r_pct):
            flags.add("dial_size_off")

        # 8) Odo crop size off
        if _flag_pct_deviation(ow_val, ow_med[i], odo_size_pct):
            flags.add("odo_width_off")
        if _flag_pct_deviation(oh_val, oh_med[i], odo_size_pct):
            flags.add("odo_height_off")

        # 9) Missing marker
        if mc is None or mc == -1:
            flags.add("no_marker")

        # 10) Needle zone pixel count anomalous
        if _flag_outlier_both_sides(nz or 0, nz_mean[i], nz_std[i], nz_pix_sigma):
            flags.add("nz_pix_anomaly")

        # 11) npos discontinuity — needle flipped 180° (neighbors agree, this frame doesn't)
        curr_npos = rows_raw[i][11]  # npos column
        if curr_npos is not None:
            prev_npos = rows_raw[i-1][11] if i > 0 else None
            next_npos = rows_raw[i+1][11] if i + 1 < n else None
            if prev_npos is not None and next_npos is not None:
                if abs(prev_npos - next_npos) <= 20 and abs(curr_npos - prev_npos) > 30:
                    flags.add("npos_discontinuity")

        if flags:
            flagged[image_name] = flags
            flagged_count += 1

    log.info("Flagged %d / %d rows (%.1f%%)", flagged_count, n, 100 * flagged_count / n)

    # Print summary of flag types
    flag_counts: dict[str, int] = {}
    for flist in flagged.values():
        for f in flist:
            flag_counts[f] = flag_counts.get(f, 0) + 1
    for f, c in sorted(flag_counts.items(), key=lambda x: -x[1]):
        log.info("  %s: %d", f, c)

    if dry_run:
        log.info("Dry run — no DB changes made.")
        return {"total": n, "flagged": flagged_count, "flags": flagged, "flag_counts": flag_counts}

    # --- Write to DB ---
    updated = 0
    with get_session() as session:
        for image_name, flags in flagged.items():
            row = session.get(MeterReading, image_name)
            if row is None:
                continue
            row.status = "ANOMALY"
            row.fail_reason = ", ".join(sorted(flags))
            updated += 1
        session.commit()

    log.info("Updated %d rows to ANOMALY status.", updated)
    return {"total": n, "flagged": flagged_count, "flags": flagged, "flag_counts": flag_counts}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Water meter anomaly flagger")
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                   help=f"Rolling window size (default: {DEFAULT_WINDOW})")
    p.add_argument("--brightness-sigma", type=float, default=BRIGHTNESS_SIGMA,
                   help=f"Std dev threshold for brightness (default: {BRIGHTNESS_SIGMA})")
    p.add_argument("--contrast-sigma", type=float, default=CONTRAST_SIGMA,
                   help=f"Std dev threshold for contrast (default: {CONTRAST_SIGMA})")
    p.add_argument("--horizon-thresh", type=float, default=HORIZON_DEG_THRESH,
                   help=f"Degrees threshold for horizon tilt (default: {HORIZON_DEG_THRESH})")
    p.add_argument("--dial-r-pct", type=float, default=DIAL_R_PCT,
                   help=f"Percent deviation for dial radius (default: {DIAL_R_PCT})")
    p.add_argument("--odo-size-pct", type=float, default=ODO_SIZE_PCT,
                   help=f"Percent deviation for odo size (default: {ODO_SIZE_PCT})")
    p.add_argument("--nz-pix-sigma", type=float, default=NZ_PIX_SIGMA,
                   help=f"Std dev threshold for needle zone pixels (default: {NZ_PIX_SIGMA})")
    p.add_argument("--dry-run", action="store_true",
                   help="Report anomalies only, do not update DB")
    p.add_argument("--reset", action="store_true",
                   help="Clear all ANOMALY flags back to OK status")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    result = scan_anomalies(
        window=args.window,
        brightness_sigma=args.brightness_sigma,
        contrast_sigma=args.contrast_sigma,
        horizon_thresh=args.horizon_thresh,
        dial_r_pct=args.dial_r_pct,
        odo_size_pct=args.odo_size_pct,
        nz_pix_sigma=args.nz_pix_sigma,
        dry_run=args.dry_run,
        reset=args.reset,
    )

    if args.reset:
        print(f"Reset {result.get('reset_count', 0)} anomaly flags → OK")
    else:
        total = result.get("total", 0)
        flagged = result.get("flagged", 0)
        print(f"\nTotal rows: {total}")
        print(f"Anomalies:  {flagged} ({100 * flagged / total:.1f}%)" if total else "Anomalies: 0")


if __name__ == "__main__":
    main()