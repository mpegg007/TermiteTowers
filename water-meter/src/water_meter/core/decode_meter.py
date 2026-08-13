#!/usr/bin/env python3
"""Unified water meter decoder — per-frame hub/dial detection + needle angle + odo crop.

Processes EVERY image independently (stateless). There is NO cross-frame state,
no accumulated revolution tracking, no baseline seeding, no drop detection.
Each frame writes its geometry, needle angle, and odometer crop to the DB.

Digit decoding (odometer wheel recognition) is handled as a separate stage by
``decode_odo.py``, which reads the saved crops from ``proc/YYYY-MM-DD/``.

Rev tracking (needle wrap-around across frames) is performed as a post-process
by querying DB rows ordered by ``capture_ts`` — NOT during live capture.

Features:
  --input-image  PATH      Image to process (default: ~/pictures/water_meter/latest.jpg)
  --dial-scan              Save debug overlay (hub, circle, ellipse, marker, needle, odo box)
  --odo-crop               Save odometer crop with digit boxes and vertical projection
  --debug                  Verbose console logging
  --batch-dir PATH         Process all water_meter_*.jpg files in directory
  --reprocess-mask GLOB    Only process files matching this fnmatch pattern (e.g. '20260701_*')
                           Implies --force (ignore last-processed timestamp).
  --force                  Process all files even if already in DB.
  --fast                   Use timestamp-based skip (faster, but can miss gap files)
  --no-move                Do NOT move processed source images to scanned/ (default: move them)

Output:
    ~/pictures/water_meter/proc/YYYY-MM-DD/          (odometer crops with needle position)
    ~/pictures/water_meter/debug/                    (debug overlays)
    ~/pictures/water_meter/scanned/YYYY-MM-DD/       (processed source images, moved by default; --no-move to disable)

Usage:
    .venv/bin/python scripts/water_meter/decode_meter.py --debug --dial-scan --odo-crop
    .venv/bin/python scripts/water_meter/decode_meter.py --batch-dir ~/pictures/water_meter/pending
    .venv/bin/python scripts/water_meter/decode_meter.py --batch-dir ~/pictures/water_meter/pending --reprocess-mask "20260701_*"
"""

import argparse
import fnmatch
import glob
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
import time

import cv2
import numpy as np

# Add project root so imports work when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    IMAGE_DIR, PENDING_DIR, SCANNED_DIR, PROC_DIR, DEBUG_DIR, TEMPLATE_DIR,
    detect_hub_and_dial, crop_odometer, get_digit_slots, get_odo_box_coords,
    parse_filename_timestamp, timestamp_tag_from_fname,
    image_stats, odo_stats,
    draw_dial_scan, draw_odo_crop,
    load_template_bank, save_template, match_digit,
    load_pos5_templates, load_static_templates,
    get_last_processed_ts,
)
from water_meter.core.db import (
    MeterReading, init_db, get_session, upsert_reading, _to_native,
)

log = logging.getLogger("decode_meter")

# ---------------------------------------------------------------------------
# Constants — local to this module (detection-specific)
# ---------------------------------------------------------------------------
# Skip files modified less than this many seconds ago — the capture script
# may still be writing them.  Water meter images are ~200 KB JPEGs captured
# minutes apart, so 30 seconds gives ample time for a write to complete.
MIN_FILE_AGE_SECONDS = 30
RED_LOWER_1 = np.array([0, 100, 50])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 50])
RED_UPPER_2 = np.array([180, 255, 255])
BRIGHT_THRESH = 200
MIN_BRIGHT_FRAC = 0.30

NUM_DIGITS = 6
REFERENCE_CROP_W = 558
DIGIT_SLOTS = [(24, 78), (119, 173), (197, 251), (289, 343), (368, 422), (432, 508)]
DIGIT_COLORS = [(0, 255, 0), (255, 0, 0), (255, 255, 0),
                (255, 0, 255), (0, 255, 255), (0, 165, 255)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_label_from_ts_tag(ts_tag: str) -> str:
    """Convert YYYYMMDD_HHMMSS to YYYY-MM-DD."""
    return f"{ts_tag[:4]}-{ts_tag[4:6]}-{ts_tag[6:8]}"


def _move_to_scanned(src_path: str, fname: str, cap_ts: datetime | None) -> str | None:
    """Move a processed source image from pending/ → scanned/YYYY-MM-DD/.

    Returns the destination path on success, None on failure.
    """
    date_label = cap_ts.strftime("%Y-%m-%d") if cap_ts else _date_label_from_ts_tag(
        timestamp_tag_from_fname(fname))
    dest_dir = os.path.join(SCANNED_DIR, date_label)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, fname)

    try:
        shutil.move(src_path, dest_path)
        return dest_path
    except OSError as e:
        log.warning("  Failed to move %s → scanned/: %s", fname, e)
        return None


# ---------------------------------------------------------------------------
# Process single image
# ---------------------------------------------------------------------------

def process_image(img_path: str, args) -> dict | None:
    """Process a single image frame — stateless, no cross-frame references.

    Returns {"npos": npos, "needle_deg": needle_deg, "moved_to": path} on
    success, None on failure.
    """
    img = cv2.imread(img_path)
    if img is None:
        log.error("cannot read %s", img_path)
        return None

    fname = os.path.basename(img_path)
    ts_tag = timestamp_tag_from_fname(fname)
    cap_ts = parse_filename_timestamp(fname)

    log.debug("[%s] %s", cap_ts or "unknown", fname)

    # Image-level stats
    stats = image_stats(img)

    # Detection
    lm = detect_hub_and_dial(img, debug=args.debug)
    if lm is None:
        log.info("  FAIL: %s — hub/dial detect failed", fname)
        _write_fail(fname, cap_ts, stats, "hub/dial detect failed")
        return None

    log.debug("  hub=(%d,%d)  dial_r=%d", lm["hub_x"], lm["hub_y"], lm["dial_r"])

    # Needle angle — per-frame measurement
    needle_deg = lm.get("needle_deg")
    if needle_deg is None:
        needle_deg = lm.get("horizon_deg", 0)
    if needle_deg is None:
        needle_deg = 0.0
    if needle_deg < 0:
        needle_deg += 360.0
    npos = int(((needle_deg + 90) % 360) / 360 * 100) % 100

    log.debug("  needle=%.1f°  npos=%d  nz_pix=%d",
              needle_deg, npos, len(lm["needle_zone_pixels"]))

    # Odometer crop — save to proc/YYYY-MM-DD/
    odo = crop_odometer(img, lm)
    if odo is None:
        log.info("  FAIL: %s — odo crop failed", fname)
        _write_fail(fname, cap_ts, stats, "odo crop failed")
        return None

    npos = int(((needle_deg + 90) % 360) / 360 * 100) % 100
    odo_crop_basename = f"odo_{ts_tag}_n{npos:02d}.jpg"
    date_label = _date_label_from_ts_tag(ts_tag)
    proc_date_dir = os.path.join(PROC_DIR, date_label)
    os.makedirs(proc_date_dir, exist_ok=True)
    cv2.imwrite(os.path.join(proc_date_dir, odo_crop_basename), odo)
    # Store path relative to PROC_DIR so lookups work cross-platform
    odo_crop_rel = os.path.join(date_label, odo_crop_basename)

    # --- Debug outputs ---
    if args.dial_scan:
        scan_path = os.path.join(DEBUG_DIR, f"hub_dial_scan_{ts_tag}.jpg")
        draw_dial_scan(img, lm, scan_path)
        log.debug("  dial-scan: %s", scan_path)

    if args.odo_crop:
        odo_path = os.path.join(DEBUG_DIR, f"odo_crop_{ts_tag}.jpg")
        vproj_path = os.path.join(DEBUG_DIR, f"odo_vproj_{ts_tag}.jpg") if args.dial_scan else None
        draw_odo_crop(odo, odo_path, vproj_path)
        log.debug("  odo-crop: %s", odo_path)

    # --- Odo stats ---
    odo_st = odo_stats(odo)

    # --- Write to DB (upsert on image_name) ---
    try:
        ox1, oy1, odo_w, odo_h = get_odo_box_coords(lm)
        odo_brightness = odo_st["odo_brightness"]
        odo_contrast = odo_st["odo_contrast"]

        # marker_extent
        me = -1
        if lm["marker_bbox"] is not None:
            _, _, mbw, mbh = lm["marker_bbox"]
            me = max(mbw, mbh)

        # Horizon row stats
        gray_cv = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray_cv, (9, 9), 0)
        hrow_vals = blurred[lm["hub_y"], :]
        hrow_mean = int(hrow_vals.mean())
        hrow_std = int(hrow_vals.std())

        with get_session() as session:
            upsert_reading(session, {
                "image_name": fname,
                "capture_ts": cap_ts,
                "processed_ts": datetime.now(tz=timezone.utc),
                "status": "OK",
                "hub_x": lm["hub_x"],
                "hub_y": lm["hub_y"],
                "hub_r": lm["hub_r"],
                "dial_r": lm["dial_r"],
                "dial_ry": lm["dial_ry"],
                "left_edge": lm["left_edge"],
                "right_edge": lm["right_edge"],
                "inner_rx": lm["inner_rx"],
                "inner_ry": lm["inner_ry"],
                "nz_pix": len(lm["needle_zone_pixels"]),
                "marker_cx": lm.get("marker_cx", -1) or -1,
                "marker_cy": lm.get("marker_cy", -1) or -1,
                "marker_extent": me,
                "needle_deg": needle_deg,
                "npos": npos,
                "horizon_deg": lm["horizon_deg"],
                "hrow_mean": hrow_mean,
                "hrow_std": hrow_std,
                "img_brightness": stats["brightness"],
                "img_contrast": stats["contrast"],
                "odo_x1": ox1,
                "odo_y1": oy1,
                "odo_w": odo_st["odo_width"],
                "odo_h": odo_st["odo_height"],
                "odo_brightness": odo_brightness,
                "odo_contrast": odo_contrast,
                "img_width": stats["width"],
                "img_height": stats["height"],
                "odo_crop_file": odo_crop_rel,
                "odo_width": odo_st["odo_width"],
                "odo_height": odo_st["odo_height"],
                "odo_mean": odo_st["odo_mean"],
                "odo_std": odo_st["odo_std"],
                "odo_sobel_mean": odo_st["odo_sobel_mean"],
                "odo_sobel_std": odo_st["odo_sobel_std"],
                "odo_hist_entropy": odo_st["odo_hist_entropy"],
                "clean_read": False,
                "clean_archive": False,
                # ── dm_ prefixed copies ──
                "dm_status": "OK",
                "dm_hub_x": lm["hub_x"],
                "dm_hub_y": lm["hub_y"],
                "dm_hub_r": lm["hub_r"],
                "dm_dial_r": lm["dial_r"],
                "dm_dial_ry": lm["dial_ry"],
                "dm_left_edge": lm["left_edge"],
                "dm_right_edge": lm["right_edge"],
                "dm_inner_rx": lm["inner_rx"],
                "dm_inner_ry": lm["inner_ry"],
                "dm_nz_pix": len(lm["needle_zone_pixels"]),
                "dm_marker_cx": lm.get("marker_cx", -1) or -1,
                "dm_marker_cy": lm.get("marker_cy", -1) or -1,
                "dm_marker_extent": me,
                "dm_needle_deg": needle_deg,
                "dm_npos": npos,
                "dm_horizon_deg": lm["horizon_deg"],
                "dm_hrow_mean": hrow_mean,
                "dm_hrow_std": hrow_std,
                "dm_img_brightness": stats["brightness"],
                "dm_img_contrast": stats["contrast"],
                "dm_img_width": stats["width"],
                "dm_img_height": stats["height"],
                "dm_odo_x1": ox1,
                "dm_odo_y1": oy1,
                "dm_odo_w": odo_st["odo_width"],
                "dm_odo_h": odo_st["odo_height"],
                "dm_odo_crop_file": odo_crop_rel,
                "dm_odo_brightness": odo_brightness,
                "dm_odo_contrast": odo_contrast,
                "dm_odo_mean": odo_st["odo_mean"],
                "dm_odo_std": odo_st["odo_std"],
                "dm_odo_sobel_mean": odo_st["odo_sobel_mean"],
                "dm_odo_sobel_std": odo_st["odo_sobel_std"],
                "dm_odo_hist_entropy": odo_st["odo_hist_entropy"],
            })
    except Exception as e:
        log.error("  DB ERROR: %s", e)
        return None

    # --- Move source image to scanned/ if requested ---
    moved_to = None
    if not args.no_move and not img_path.startswith(SCANNED_DIR):
        moved_to = _move_to_scanned(img_path, fname, cap_ts)

    return {"npos": npos, "needle_deg": needle_deg, "moved_to": moved_to}


def _write_fail(fname: str, cap_ts: datetime | None, stats: dict, reason: str):
    """Write a FAIL row to the DB."""
    try:
        with get_session() as session:
            upsert_reading(session, {
                "image_name": fname,
                "capture_ts": cap_ts,
                "processed_ts": datetime.now(tz=timezone.utc),
                "status": "FAIL",
                "fail_reason": reason,
                "img_brightness": stats["brightness"],
                "img_contrast": stats["contrast"],
                "img_width": stats["width"],
                "img_height": stats["height"],
                "clean_read": False,
                "clean_archive": False,
            })
    except Exception:
        pass  # Don't let DB errors cascade


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def collect_files(batch_dir: str, reprocess_mask: str | None,
                  force: bool, fast: bool = False) -> list[str]:
    """Return sorted list of image paths to process.

    Default (gap-safe): loads all known ``image_name`` values from the DB into
    a set and processes any file **not** in that set.  This catches files missed
    during a previous run regardless of timestamp ordering.

    ``--fast`` mode: uses ``MAX(capture_ts)`` for faster DB lookup (one query
    instead of loading all names), but can miss files from a gap.
    """
    # Recursive — capture stores files in date subdirectories (pending/YYYY-MM-DD/)
    pattern = os.path.join(batch_dir, "**", "water_meter_*.jpg")
    all_files = sorted(glob.glob(pattern, recursive=True))

    if not all_files:
        return []

    # Guard: skip files still being written by the capture script
    now = time.time()
    stale_cutoff = now - MIN_FILE_AGE_SECONDS
    skipped_recent = 0
    aged_files = []
    for fp in all_files:
        try:
            mtime = os.path.getmtime(fp)
        except OSError:
            aged_files.append(fp)
            continue
        if mtime < stale_cutoff:
            aged_files.append(fp)
        else:
            skipped_recent += 1
    if skipped_recent:
        log.info("Skipping %d files still being written (modified < %ds ago)",
                 skipped_recent, MIN_FILE_AGE_SECONDS)
    all_files = aged_files

    if not all_files:
        return []

    # If force or reprocess mask, process everything (mask filters later)
    if force or reprocess_mask:
        if reprocess_mask:
            all_files = [f for f in all_files
                         if fnmatch.fnmatch(os.path.basename(f), f"water_meter_{reprocess_mask}.jpg")]
        return all_files

    # ── Determine already-processed names ──
    if fast:
        # Timestamp-based: skip files older than MAX(capture_ts)
        try:
            from water_meter.core.common import get_last_processed_ts
            with get_session() as session:
                last_ts = get_last_processed_ts(session)
        except Exception:
            last_ts = None

        if last_ts is None:
            log.info("No prior DB entries — processing all %d files", len(all_files))
            return all_files

        log.info("Last processed capture_ts: %s (fast mode)", last_ts)
        new_files = []
        for fp in all_files:
            fname = os.path.basename(fp)
            ts = parse_filename_timestamp(fname)
            if ts is not None and ts > last_ts:
                new_files.append(fp)
            elif ts is None:
                new_files.append(fp)
    else:
        # Gap-safe: bulk-load all known image_name values
        try:
            from water_meter.core.common import MeterReading
            with get_session() as session:
                known = {row[0] for row in session.query(MeterReading.image_name).all()}
        except Exception:
            known = set()

        log.info("DB has %d known image names (gap-safe mode)", len(known))
        new_files = [fp for fp in all_files if os.path.basename(fp) not in known]

    log.info("Skipping %d already-processed files, %d new",
             len(all_files) - len(new_files), len(new_files))
    return new_files


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Unified water meter decoder — per-frame stateless")
    ap.add_argument("--input-image",
                    help="Image to process (default: ~/pictures/water_meter/latest.jpg)")
    ap.add_argument("--dial-scan", action="store_true",
                    help="Save debug dial overlay")
    ap.add_argument("--odo-crop", action="store_true",
                    help="Save odometer crop with digit boxes")
    ap.add_argument("--debug", action="store_true",
                    help="Verbose logging")
    ap.add_argument("--batch-dir",
                    help="Process all water_meter_*.jpg files in directory")
    ap.add_argument("--reprocess-mask",
                    help="fnmatch pattern for filenames to reprocess "
                         "(e.g. '20260701_*'). Implies --force.")
    ap.add_argument("--force", action="store_true",
                    help="Process all files even if already in DB")
    ap.add_argument("--fast", action="store_true",
                    help="Use timestamp-based skip (faster, but can miss gap files)")
    ap.add_argument("--no-move", action="store_true",
                    help="Do NOT move processed source images to scanned/ (default: move them)")
    return ap.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    # Batch mode
    if args.batch_dir:
        files = collect_files(args.batch_dir, args.reprocess_mask, args.force, args.fast)
        if not files:
            log.info("No water_meter_*.jpg files to process in %s", args.batch_dir)
            return

        log.info("Batch mode: %d images", len(files))
        succ = fail = 0
        for i, fp in enumerate(files):
            result = process_image(fp, args)
            if result:
                succ += 1
            else:
                fail += 1
            if (i + 1) % 500 == 0:
                log.info("  [%d/%d] ok=%d fail=%d", i + 1, len(files), succ, fail)
            elif args.debug and (i + 1) % 50 == 0:
                log.debug("  [%d/%d] ok=%d fail=%d", i + 1, len(files), succ, fail)

        log.info("Done: %d ok, %d fail", succ, fail)
        return

    # Single image
    img_path = args.input_image or os.path.join(IMAGE_DIR, "latest.jpg")
    if not os.path.exists(img_path):
        log.error("%s not found", img_path)
        sys.exit(1)

    result = process_image(img_path, args)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()