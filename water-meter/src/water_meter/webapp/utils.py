"""Shared helpers for the water meter webapp.

Extracted from the original single-file app.py so routers stay small.
"""

import glob
import json
import os
import subprocess
import sys
from typing import Optional

from water_meter.core.common import (
    IMAGE_DIR, PENDING_DIR, SCANNED_DIR, KEEPERS_DIR,
)
from water_meter.core.db import MeterReading


def find_source_image(image_name: str) -> Optional[str]:
    """Search keepers/, scanned/, pending/, and flat IMAGE_DIR."""
    for base in (KEEPERS_DIR, SCANNED_DIR, PENDING_DIR):
        pattern = os.path.join(base, "**", image_name)
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    # Flat IMAGE_DIR fallback
    direct = os.path.join(IMAGE_DIR, image_name)
    if os.path.exists(direct):
        return direct
    return None


def run_decode_meter(extra_args, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run the decode_meter CLI as a module using the app's own interpreter.

    The webapp runs inside the water-meter venv, so ``sys.executable`` is the
    interpreter with ``water_meter`` installed — no absolute repo paths needed.
    """
    return subprocess.run(
        [sys.executable, "-m", "water_meter.core.decode_meter", *extra_args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def row_to_dict(row: MeterReading) -> dict:
    """Serialize a MeterReading row for JSON API responses."""
    pos_confs = []
    pos_digits_raw = []
    if row.notes:
        try:
            nd = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
            pos_confs = nd.get("pos_confs", [])
            pos_digits_raw = nd.get("pos_digits", [])
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "image_name": row.image_name,
        "capture_ts": row.capture_ts.isoformat() if row.capture_ts else None,
        "clean_read": row.clean_read, "clean_archive": row.clean_archive,
        "notes": row.notes,
        # ── dm_ (decode_meter) ──────────────────────────────────
        "dm_status": row.dm_status,
        "dm_fail_reason": row.dm_fail_reason,
        "dm_hub_x": row.dm_hub_x, "dm_hub_y": row.dm_hub_y, "dm_hub_r": row.dm_hub_r,
        "dm_dial_r": row.dm_dial_r, "dm_dial_ry": row.dm_dial_ry,
        "dm_left_edge": row.dm_left_edge, "dm_right_edge": row.dm_right_edge,
        "dm_inner_rx": row.dm_inner_rx, "dm_inner_ry": row.dm_inner_ry,
        "dm_nz_pix": row.dm_nz_pix,
        "dm_marker_cx": row.dm_marker_cx, "dm_marker_cy": row.dm_marker_cy,
        "dm_marker_extent": row.dm_marker_extent,
        "dm_needle_deg": row.dm_needle_deg, "dm_npos": row.dm_npos,
        "dm_horizon_deg": row.dm_horizon_deg,
        "dm_hrow_mean": row.dm_hrow_mean, "dm_hrow_std": row.dm_hrow_std,
        "dm_img_brightness": row.dm_img_brightness, "dm_img_contrast": row.dm_img_contrast,
        "dm_img_width": row.dm_img_width, "dm_img_height": row.dm_img_height,
        "dm_odo_x1": row.dm_odo_x1, "dm_odo_y1": row.dm_odo_y1,
        "dm_odo_w": row.dm_odo_w, "dm_odo_h": row.dm_odo_h,
        "dm_odo_crop_file": row.dm_odo_crop_file,
        "dm_odo_brightness": row.dm_odo_brightness, "dm_odo_contrast": row.dm_odo_contrast,
        "dm_odo_mean": row.dm_odo_mean, "dm_odo_std": row.dm_odo_std,
        "dm_odo_sobel_mean": row.dm_odo_sobel_mean, "dm_odo_sobel_std": row.dm_odo_sobel_std,
        "dm_odo_hist_entropy": row.dm_odo_hist_entropy,
        # ── do_ (decode_odo) ───────────────────────────────────
        "do_digits": row.do_digits,
        "do_reading": row.do_reading,
        "do_confidence": row.do_confidence,
        "do_pos5": row.do_pos5, "do_pos5_conf": row.do_pos5_conf,
        "do_pos5_source": row.do_pos5_source,
        "do_details": row.do_details,
        # ── dr_ (rotation anchors) ──────────────────────────────
        "dr_cycle": row.dr_cycle, "dr_zone": row.dr_zone,
        "dr_enter": row.dr_enter, "dr_exit": row.dr_exit,
        "dr_flutter": row.dr_flutter, "dr_best": row.dr_best,
        "dr_score": row.dr_score, "dr_pos5": row.dr_pos5,
        # ── cn_ (calc_needle) ───────────────────────────────────
        "cn_needle": row.cn_needle, "cn_published": row.cn_published,
        "cn_manual": row.cn_manual, "cn_visual_trusted": row.cn_visual_trusted,
        # ── kp_ (keeper flags) ──────────────────────────────────
        "kp_first_of_day": row.kp_first_of_day,
        "kp_last_of_day": row.kp_last_of_day,
        "kp_first_lit": row.kp_first_lit,
        "kp_last_lit": row.kp_last_lit,
        "kp_rotation_best": row.kp_rotation_best,
        "kp_important": row.kp_important,
        # ── Legacy aliases (for JS backward compat) ───────────
        "status": row.dm_status or row.status,
        "digits": row.do_digits or row.digits,
        "odo_reading": row.do_reading or row.odo_reading,
        "odo_confidence": row.do_confidence or row.odo_confidence,
        "odo_pos5": row.do_pos5 or row.odo_pos5,
        "odo_pos5_conf": row.do_pos5_conf or row.odo_pos5_conf,
        "npos": row.dm_npos or row.npos,
        "needle_deg": row.dm_needle_deg or row.needle_deg,
        "hub_x": row.dm_hub_x or row.hub_x,
        "hub_y": row.dm_hub_y or row.hub_y,
        "hub_r": row.dm_hub_r or row.hub_r,
        "dial_r": row.dm_dial_r or row.dial_r,
        "dial_ry": row.dm_dial_ry or row.dial_ry,
        "img_brightness": row.dm_img_brightness or row.img_brightness,
        "img_contrast": row.dm_img_contrast or row.img_contrast,
        "odo_brightness": row.dm_odo_brightness or row.odo_brightness,
        "odo_contrast": row.dm_odo_contrast or row.odo_contrast,
        "horizon_deg": row.dm_horizon_deg or row.horizon_deg,
        "hrow_mean": row.dm_hrow_mean or row.hrow_mean,
        "hrow_std": row.dm_hrow_std or row.hrow_std,
        "fail_reason": row.dm_fail_reason or row.fail_reason,
        "odo_needle": row.cn_needle or row.odo_needle,
        "odo_published": row.cn_published or row.odo_published,
        "odo_manual": row.cn_manual or row.odo_manual,
        # ── Legacy (no direct replacement) ──────────────────────
        "reading": row.reading,
        "accumulated_revs": row.accumulated_revs,
        "odo_scan": row.odo_scan,
        "odo_crop_file": row.odo_crop_file,
    }
