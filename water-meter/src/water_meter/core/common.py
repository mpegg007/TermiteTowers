#!/usr/bin/env python3
"""Shared constants, helpers, detection functions, and DB utilities for the water
meter pipeline.

Import this module instead of duplicating paths, detection logic, or template
loading across the pipeline stages.

Typical usage::

    from water_meter.core.common import (
        IMAGE_DIR, PROC_DIR, DEBUG_DIR, TEMPLATE_DIR,
        detect_hub_and_dial, crop_odometer, get_digit_slots,
        parse_filename_timestamp, npos_from_fname,
        load_pos5_templates, load_static_templates, preprocess,
        match_pos5, match_static,
        get_session, init_db, MeterReading, upsert_reading,
        get_last_processed_ts,
        image_stats, odo_stats,
        TEMPLATE_DIGITS,
    )
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from water_meter.core.db import (
    MeterReading, init_db, get_session, upsert_reading,
)

log = logging.getLogger("wm_common")

# ---------------------------------------------------------------------------
# Paths  (all overridable via WATER_METER_ROOT env var)
# ---------------------------------------------------------------------------
IMAGE_DIR = os.environ.get(
    "WATER_METER_ROOT",
    os.path.expanduser("~/pictures/water_meter"),
)
PENDING_DIR = os.path.join(IMAGE_DIR, "pending")
SCANNED_DIR = os.path.join(IMAGE_DIR, "scanned")
PROC_DIR = os.path.join(IMAGE_DIR, "proc")
DEBUG_DIR = os.path.join(IMAGE_DIR, "debug")
TEMPLATE_DIR = os.path.join(IMAGE_DIR, "templates")
KEEPERS_DIR = os.path.join(IMAGE_DIR, "keepers")

for _d in (TEMPLATE_DIR, DEBUG_DIR, PROC_DIR, SCANNED_DIR, KEEPERS_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------------
# Detection constants
# ---------------------------------------------------------------------------
RED_LOWER_1 = np.array([0, 100, 50])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 50])
RED_UPPER_2 = np.array([180, 255, 255])
BRIGHT_THRESH = 200
MIN_BRIGHT_FRAC = 0.30

# Odometer geometry
NUM_DIGITS = 6
TEMPLATE_DIGITS = list(range(10))  # [0..9]
REFERENCE_CROP_W = 558
DIGIT_SLOTS = [(24, 78), (119, 173), (197, 251), (289, 343), (368, 422), (432, 508)]
DIGIT_COLORS = [(0, 255, 0), (255, 0, 0), (255, 255, 0),
                (255, 0, 255), (0, 255, 255), (0, 165, 255)]

# Template matching
MATCH_THRESHOLD = 0.55
NPOS_WINDOW = 10
POS5_INDEX = 5

# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

FILENAME_RE = re.compile(
    r'water_meter_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})'
)

ODO_NPOS_RE = re.compile(r'_n(\d{2})\.jpg$')


def parse_filename_timestamp(fname: str) -> Optional[datetime]:
    """Extract capture timestamp from ``water_meter_YYYYMMDD_HHMMSS.jpg``."""
    m = FILENAME_RE.match(fname)
    if not m:
        return None
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)))


def timestamp_tag_from_fname(fname: str) -> str:
    """Return ``YYYYMMDD_HHMMSS`` tag from filename, or current time."""
    m = FILENAME_RE.match(fname)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}_{m.group(4)}{m.group(5)}{m.group(6)}"
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def npos_from_fname(fname: str) -> Optional[int]:
    """Extract needle position from ``odo_*_nNN.jpg`` filename."""
    m = ODO_NPOS_RE.search(fname)
    return int(m.group(1)) if m else None


def npos_distance(a: int, b: int) -> int:
    """Circular distance on npos (0-99)."""
    return min(abs(a - b), 100 - abs(a - b))


# ---------------------------------------------------------------------------
# Image statistics
# ---------------------------------------------------------------------------

def image_stats(img_bgr: np.ndarray):
    """Return (width, height, brightness, contrast) for a BGR image."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return {
        "width": img_bgr.shape[1],
        "height": img_bgr.shape[0],
        "brightness": int(gray.mean()),
        "contrast": int(gray.std()),
    }


def odo_stats(odo_bgr: np.ndarray):
    """Return odometer textural stats: mean, std, Sobel, entropy."""
    gray = cv2.cvtColor(odo_bgr, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_mag = np.abs(sobel_x)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_norm = hist / hist.sum()
    hist_nz = hist_norm[hist_norm > 0]
    entropy = float(-(hist_nz * np.log2(hist_nz)).sum())
    return {
        "odo_mean": int(gray.mean()),
        "odo_std": int(gray.std()),
        "odo_sobel_mean": int(sobel_mag.mean()),
        "odo_sobel_std": int(sobel_mag.std()),
        "odo_hist_entropy": entropy,
        "odo_brightness": int(gray.mean()),
        "odo_contrast": int(gray.std()),
        "odo_width": odo_bgr.shape[1],
        "odo_height": odo_bgr.shape[0],
    }


# ---------------------------------------------------------------------------
# Detection: hub + dial + needle + marker
# ---------------------------------------------------------------------------

def find_segment_box_edges(horizon_row, hub_x, w):
    """Find the outer edges of the segment-box ring on both sides of the hub.

    Scans the full horizon row and identifies BRIGHT runs (>90).  The hub sits
    inside the main dial BRIGHT region.  The segment boxes are additional BRIGHT
    runs beyond the main dial, separated by dark gaps.

    Returns (left_edge, right_edge) or falls back to (50, w-50).
    """
    runs = []  # [(x_from, x_to, 'B'|'D'|'M')...]
    cur = 0
    while cur < w:
        v = int(horizon_row[cur])
        st = 'B' if v > 90 else ('D' if v < 60 else 'M')
        end = cur
        while end < w and ((int(horizon_row[end]) > 90 and st == 'B')
                           or (int(horizon_row[end]) < 60 and st == 'D')
                           or (60 <= int(horizon_row[end]) <= 90 and st == 'M')):
            end += 1
        if end - cur >= 2:
            runs.append((cur, end - 1, st))
        cur = end

    # Find BRIGHT run containing hub (the main dial)
    for xf, xt, st in runs:
        if st == 'B' and xf <= hub_x <= xt:
            break  # dial_run not needed beyond existence check

    # Find the outermost BRIGHT runs that are NOT the main dial face.
    left_edge = 50
    right_edge = w - 50

    for xf, xt, st in runs:
        wbox = xt - xf + 1
        if st == 'B' and not (xf <= hub_x <= xt) and 10 <= wbox <= 120:
            if xf < hub_x:
                left_edge = xf
                break

    for xf, xt, st in runs:
        wbox = xt - xf + 1
        if st == 'B' and not (xf <= hub_x <= xt) and 10 <= wbox <= 120:
            if xf > hub_x:
                right_edge = xt
                break

    return left_edge, right_edge


def detect_hub_and_dial(img, debug=False):
    """Full detection pipeline for a water meter frame.

    Returns a dict with hub, dial, marker, needle geometry, or None on failure.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    red_raw = cv2.bitwise_or(cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1),
                             cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2))
    red = cv2.morphologyEx(red_raw, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    dist = cv2.distanceTransform(red, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(dist)
    hub_x, hub_y = max_loc
    hub_r = int(dist[hub_y, hub_x])

    _, bright = cv2.threshold(blurred, BRIGHT_THRESH, 255, cv2.THRESH_BINARY)
    scan_y = None
    for offset in range(0, h, 2):
        test_y = hub_y - offset
        if test_y < 5:
            break
        row = bright[test_y, :]
        if row[0] > 0 or row[-1] > 0:
            continue
        if np.count_nonzero(row) / w >= MIN_BRIGHT_FRAC:
            scan_y = test_y
            break
    if scan_y is None:
        for y in range(hub_y - 1, 0, -1):
            if np.count_nonzero(bright[y, :]) > 50:
                scan_y = y
                break
    if scan_y is None:
        if debug:
            log.debug("  FAIL: no scan row")
        return None

    dial_cx = float(hub_x)
    dial_cy = float(hub_y)
    horizon_row = blurred[hub_y, :]

    left_edge, right_edge = find_segment_box_edges(horizon_row, hub_x, w)

    dial_r = hub_x - left_edge
    if dial_r <= 0:
        dial_r = 50

    # Vertical half-extent
    top_bright = h
    bot_bright = 0
    for cx in range(max(0, hub_x - dial_r), min(w, hub_x + dial_r)):
        col = bright[:, cx]
        bp = np.where(col > 0)[0]
        if len(bp) > 0:
            if bp[0] < top_bright:
                top_bright = bp[0]
            if bp[-1] > bot_bright:
                bot_bright = bp[-1]
    v_half = max((bot_bright - top_bright) // 2, 1)
    dial_ry = min(v_half, dial_r)

    if debug:
        log.debug("  scan_y=%s  L=%s  R=%s  dial_r=%s  dial_ry=%s",
                  scan_y, left_edge, right_edge, dial_r, dial_ry)

    # Marker blob
    hub_exclude = np.zeros_like(red_raw)
    cv2.circle(hub_exclude, (hub_x, hub_y), hub_r * 3, 255, -1)
    red_no_hub = cv2.bitwise_and(red_raw, cv2.bitwise_not(hub_exclude))
    n_labels, _, stats, centroids = cv2.connectedComponentsWithStats(red_no_hub)
    marker_cx = marker_cy = None
    marker_bbox = None
    if n_labels > 1:
        best_dy = float('inf')
        for lbl in range(1, n_labels):
            cx = int(centroids[lbl][0])
            cy = int(centroids[lbl][1])
            area = stats[lbl, cv2.CC_STAT_AREA]
            if cx < hub_x and area > 500:
                dy = abs(cy - hub_y)
                if dy < best_dy:
                    best_dy = dy
                    marker_cx = cx
                    marker_cy = cy
                    sx = int(stats[lbl, cv2.CC_STAT_LEFT])
                    sy = int(stats[lbl, cv2.CC_STAT_TOP])
                    sw = int(stats[lbl, cv2.CC_STAT_WIDTH])
                    sh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
                    side = max(sw, sh)
                    marker_bbox = (marker_cx - side // 2, marker_cy - side // 2, side, side)

    angle_deg = 0.0
    if marker_cx is not None:
        angle_deg = np.degrees(np.arctan2(marker_cy - hub_y, marker_cx - hub_x))
    if debug:
        log.debug("  marker=(%s,%s)  horizon_angle=%.1f°", marker_cx, marker_cy, angle_deg)

    # Inner ellipse
    if marker_bbox is not None:
        bx, by, bw, bh = marker_bbox
        hd = max(abs(bx - hub_x), abs(bx + bw - hub_x))
        vd = max(abs(by - hub_y), abs(by + bh - hub_y))
        inner_rx = min(int(max(hd * 1.15, dial_r * 0.45)), int(dial_r * 0.95))
        inner_ry = min(int(max(vd * 1.15, dial_r * 0.40)), int(dial_r * 0.95))
    else:
        inner_rx = int(dial_r * 0.90)
        inner_ry = int(dial_r * 0.75)

    # Needle zone
    needle_zone_pixels = []
    for py in range(h):
        for px in range(w):
            if red_raw[py, px] > 0:
                dx = px - hub_x
                dy = py - hub_y
                r2 = dx * dx + dy * dy
                if r2 <= dial_r * dial_r:
                    e2 = (dx * dx) / (inner_rx * inner_rx) + (dy * dy) / (inner_ry * inner_ry)
                    if e2 > 1.0:
                        needle_zone_pixels.append((px, py))

    needle_deg = None
    if len(needle_zone_pixels) >= 3:
        nz_cx = sum(p[0] for p in needle_zone_pixels) / len(needle_zone_pixels)
        nz_cy = sum(p[1] for p in needle_zone_pixels) / len(needle_zone_pixels)
        needle_deg = np.degrees(np.arctan2(nz_cy - hub_y, nz_cx - hub_x))
    if debug:
        log.debug("  needle=%s  nz_pix=%s  inner_r=(%s,%s)",
                  needle_deg, len(needle_zone_pixels), inner_rx, inner_ry)

    return {
        "hub_x": hub_x, "hub_y": hub_y, "hub_r": hub_r,
        "dial_r": dial_r, "dial_ry": dial_ry,
        "dial_cx": dial_cx, "dial_cy": dial_cy,
        "left_edge": left_edge, "right_edge": right_edge,
        "marker_cx": marker_cx, "marker_cy": marker_cy,
        "marker_bbox": marker_bbox,
        "horizon_deg": angle_deg,
        "needle_deg": needle_deg,
        "needle_zone_pixels": needle_zone_pixels,
        "inner_rx": inner_rx, "inner_ry": inner_ry,
        "bright": bright, "scan_y": scan_y,
    }


# ---------------------------------------------------------------------------
# Odometer crop helpers
# ---------------------------------------------------------------------------

def crop_odometer(img, lm):
    """Crop the odometer region from a full frame using landmark dict."""
    hi, wi = img.shape[:2]
    dr = lm["dial_r"]
    ow = int(dr * 1.40)
    oh = int(dr * 0.32)
    x1 = max(0, lm["hub_x"] - int(dr * 0.78))
    y1 = max(0, lm["hub_y"] - int(dr * 0.64) + int(oh * 0.20))
    x2 = min(wi, x1 + ow)
    y2 = min(hi, y1 + oh)
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def get_odo_box_coords(lm):
    """Return (x1, y1, w, h) pixel coordinates of the odo crop box."""
    dr = lm["dial_r"]
    oh = int(dr * 0.32)
    x1 = lm["hub_x"] - int(dr * 0.78)
    y1 = lm["hub_y"] - int(dr * 0.64) + int(oh * 0.20)
    return x1, y1, int(dr * 1.40), oh


def get_digit_slots(crop_w):
    """Return scaled digit slot intervals for a crop of given width."""
    s = crop_w / REFERENCE_CROP_W
    return [(max(0, int(a * s)), min(crop_w, int(b * s))) for a, b in DIGIT_SLOTS]


def extract_pos5_box(odo_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Extract the pos5 (rightmost) digit box as grayscale."""
    if odo_bgr is None:
        return None
    h, w = odo_bgr.shape[:2]
    slots = get_digit_slots(w)
    x0, x1 = slots[POS5_INDEX]
    gray = cv2.cvtColor(odo_bgr, cv2.COLOR_BGR2GRAY)
    return gray[:, x0:x1]


# ---------------------------------------------------------------------------
# Preprocessing for template matching
# ---------------------------------------------------------------------------

def preprocess(img: np.ndarray) -> np.ndarray:
    """Binarize with adaptive threshold for template matching."""
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 15, 4)


# ---------------------------------------------------------------------------
# Enhanced preprocessing - multi-path, lighting-robust digit detection
# ---------------------------------------------------------------------------

# Sliding-window alignment range (pixels) for sub-slot digit alignment
SLIDE_RANGE = 4

# Morphological kernel for cleaning binarized digits
_morph_kernel_init = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

# Minimum connected-component area to retain after binarization cleanup
MIN_COMPONENT_AREA = 12

# Weight factors for ensembling binary + edge + raw NCC scores
BINARY_WEIGHT = 0.40
EDGE_WEIGHT = 0.35
RAW_NCC_WEIGHT = 0.25


def preprocess_clahe_otsu(img: np.ndarray) -> np.ndarray:
    """CLAHE equalization + Otsu global threshold.

    Normalizes local contrast via CLAHE then applies a global Otsu threshold.
    Stable under both dim and overexposed conditions where adaptive
    thresholding may fail.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    try:
        eq = clahe.apply(img)
    except cv2.error:
        eq = img
    blur = cv2.GaussianBlur(eq, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def preprocess_adaptive(img: np.ndarray, block_size: int = 15,
                        c_val: int = 4) -> np.ndarray:
    """Adaptive Gaussian threshold - the original preprocessing path."""
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, block_size, c_val)


def clean_binary(binary: np.ndarray) -> np.ndarray:
    """Morphological cleanup of a binarized digit image.

    - Closing to heal broken strokes from dim lighting
    - Remove small connected components (salt-and-pepper noise)
    - Opening to separate barely-touching digit edges
    """
    kernel = _morph_kernel_init
    # Close to fill gaps in strokes
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    # Remove small noise components
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        cv2.bitwise_not(closed), connectivity=8)
    mask = np.ones_like(closed, dtype=np.uint8) * 255
    for lbl in range(1, n_labels):
        if stats[lbl, cv2.CC_STAT_AREA] < MIN_COMPONENT_AREA:
            mask[labels == lbl] = 0
    cleaned = cv2.bitwise_and(closed, mask)
    # Open to separate touching digits
    opened = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    return opened


def extract_edges(img: np.ndarray) -> np.ndarray:
    """Extract edge map via Sobel X gradient magnitude.

    Edges are far more lighting-invariant than binary pixel values.
    Returns a thresholded binary edge mask.
    """
    sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    abs_x = np.abs(sobel_x)
    abs_x = (abs_x / (abs_x.max() or 1.0) * 255).astype(np.uint8)
    _, edges = cv2.threshold(abs_x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return edges


# Vertical-slide margin: extra pixels added above & below the query box so
# that cv2.matchTemplate can slide the (taller, aspect-ratio-preserved)
# template vertically to find the best alignment.  Odometer digits roll up
# and down inside their slots; without this margin the match is a rigid 1:1
# comparison that fails on every frame where the digit has rolled even one
# pixel off centre.
VERT_SLIDE_FRAC = 0.35   # extra margin as fraction of query height


def _make_vertical_slide_query(query: np.ndarray,
                                template: np.ndarray) -> np.ndarray:
    """Pad *query* vertically so that *template* (aspect-ratio scaled to
    match query width) can slide up/down inside it.  Returns the padded
    query image with edge-replicate padding."""
    qh, qw = query.shape
    th, tw = template.shape
    # Scale template so width matches query, preserving aspect ratio
    t_h_scaled = int(th * (qw / tw))
    # Vertical padding: at least enough so template can slide, plus a margin
    vert_pad = max(
        int(qh * VERT_SLIDE_FRAC),
        t_h_scaled - qh + 2,   # +2 so there's always room to slide
    )
    return cv2.copyMakeBorder(
        query, vert_pad, vert_pad, 0, 0, cv2.BORDER_REPLICATE,
    )


def _vertical_slide_score(query_padded: np.ndarray,
                           template: np.ndarray) -> float:
    """Run cv2.matchTemplate on vertically-padded query with the template
    (which should already be width-scaled to query width but retain its
    natural aspect-ratio height).  Returns the *best* NCC score across all
    vertical positions."""
    result = cv2.matchTemplate(
        query_padded, template, cv2.TM_CCOEFF_NORMED,
    )
    return float(np.max(result))


def match_template_sliding(query: np.ndarray, template: np.ndarray,
                           slide_range: int = None) -> Tuple[float, int]:
    """Match template against query with sliding-window alignment.

    Slides the template +/- slide_range pixels horizontally *and*
    vertically within the query and returns the best score and x-offset.
    Vertical sliding uses VERT_SLIDE_FRAC margin so odometer digits that
    have rolled within their slot are still matched correctly.

    Args:
        query: Preprocessed query image (binary or edge map).
        template: Preprocessed template image.
        slide_range: Maximum horizontal slide in pixels (defaults to SLIDE_RANGE).

    Returns:
        (best_score, best_offset_x)
    """
    if slide_range is None:
        slide_range = SLIDE_RANGE
    qh, qw = query.shape
    th, tw = template.shape

    # ── When template is at least as wide as query: use vertical sliding ──
    if tw >= qw:
        t_resized = template
        if qw != tw or qh != th:
            # Resize width to match query, preserve aspect ratio for height
            t_h_scaled = int(th * (qw / tw))
            t_resized = cv2.resize(template, (qw, t_h_scaled),
                                   interpolation=cv2.INTER_NEAREST)
        query_padded = _make_vertical_slide_query(query, template)
        score = _vertical_slide_score(query_padded, t_resized)
        return score, 0

    # ── Template narrower than query: horizontal + vertical sliding ──
    best_score = -1.0
    best_offset = 0
    for offset in range(-slide_range, slide_range + 1):
        x0 = max(0, (qw - tw) // 2 + offset)
        x1 = x0 + tw
        if x1 > qw:
            x1 = qw
            x0 = x1 - tw
        if x0 < 0:
            x0 = 0
            x1 = tw
        sub = query[:, x0:x1]
        t_resized = template
        if sub.shape != t_resized.shape:
            t_h_scaled = int(th * (sub.shape[1] / tw))
            t_resized = cv2.resize(template, (sub.shape[1], t_h_scaled),
                                   interpolation=cv2.INTER_NEAREST)
        sub_padded = _make_vertical_slide_query(sub, template)
        s = _vertical_slide_score(sub_padded, t_resized)
        if s > best_score:
            best_score = float(s)
            best_offset = offset
    return best_score, best_offset


def match_with_ensemble(
    query_box: np.ndarray,
    templates: List[np.ndarray],
) -> Tuple[Optional[int], float, Dict[str, float]]:
    """Multi-path ensembled digit matching for lighting robustness.

    Combines four complementary match paths via weighted voting:
      1. Binary (adaptive threshold) - moderate lighting
      2. CLAHE + Otsu binary - extreme lighting (glare/dim)
      3. Edge-map (Sobel X) - lighting-invariant structural match
      4. Raw grayscale NCC - bypasses binarization entirely

    Args:
        query_box: Grayscale image of the digit box (raw, unpreprocessed).
        templates: List of raw (unpreprocessed) template images for digits 0-9.

    Returns:
        (digit, confidence, path_scores_dict)
    """
    if query_box is None or query_box.size == 0 or not templates:
        return None, 0.0, {}

    # Prepare query representations
    query_binary = preprocess(query_box)
    query_binary = clean_binary(query_binary)
    query_clahe = preprocess_clahe_otsu(query_box)
    query_clahe = clean_binary(query_clahe)
    query_edges = extract_edges(query_box)
    best_digit = None
    best_ensemble_score = -1.0
    scores_detail: Dict[str, float] = {}

    for digit, tmpl in enumerate(templates):
        if tmpl is None:
            continue

        # Path 1: Binary (adaptive threshold)
        tmpl_binary = preprocess(tmpl)
        tmpl_binary = clean_binary(tmpl_binary)
        score_binary, _ = match_template_sliding(query_binary, tmpl_binary)

        # Path 2: CLAHE + Otsu binary
        tmpl_clahe = preprocess_clahe_otsu(tmpl)
        tmpl_clahe = clean_binary(tmpl_clahe)
        score_clahe, _ = match_template_sliding(query_clahe, tmpl_clahe)

        # Path 3: Edge map
        tmpl_edges = extract_edges(tmpl)
        score_edges, _ = match_template_sliding(query_edges, tmpl_edges)

        # Path 4: Raw grayscale NCC via vertical-sliding matchTemplate
        # (replaces the old rigid pixel-dot-product which failed when the
        # digit was even one pixel off centre).
        t_h_scaled_raw = int(tmpl.shape[0] * (query_box.shape[1] / tmpl.shape[1]))
        tmpl_raw_resized = cv2.resize(tmpl, (query_box.shape[1], t_h_scaled_raw),
                                      interpolation=cv2.INTER_NEAREST)
        query_padded_raw = _make_vertical_slide_query(query_box, tmpl)
        score_raw = _vertical_slide_score(query_padded_raw, tmpl_raw_resized)
        score_raw = max(0.0, float(score_raw))

        # Weighted ensemble - blend CLAHE into binary portion when available
        bin_score = max(0.0, float(score_binary))
        clahe_score = max(0.0, float(score_clahe))
        edge_score = max(0.0, float(score_edges))
        ensemble = (BINARY_WEIGHT * 0.5 * bin_score +
                    BINARY_WEIGHT * 0.5 * clahe_score +
                    EDGE_WEIGHT * edge_score +
                    RAW_NCC_WEIGHT * score_raw)

        if ensemble > best_ensemble_score:
            best_ensemble_score = float(ensemble)
            best_digit = digit
            scores_detail = {
                "binary": float(score_binary),
                "clahe_otsu": float(score_clahe),
                "edges": float(score_edges),
                "raw_ncc": float(score_raw),
                "ensemble": float(ensemble),
            }

    return best_digit, best_ensemble_score, scores_detail


def match_with_ensemble_all(
    query_box: np.ndarray,
    templates: List[np.ndarray],
) -> Dict[int, Dict[str, float]]:
    """Like match_with_ensemble but returns scores for ALL digit candidates.

    Returns:
        Dict mapping digit -> {"binary": ..., "clahe_otsu": ..., "edges": ..., "raw_ncc": ..., "ensemble": ...}
        Only includes digits with non-None templates.
    """
    if query_box is None or query_box.size == 0 or not templates:
        return {}

    # Prepare query representations
    query_binary = preprocess(query_box)
    query_binary = clean_binary(query_binary)
    query_clahe = preprocess_clahe_otsu(query_box)
    query_clahe = clean_binary(query_clahe)
    query_edges = extract_edges(query_box)
    all_scores: Dict[int, Dict[str, float]] = {}

    for digit, tmpl in enumerate(templates):
        if tmpl is None:
            continue

        tmpl_binary = preprocess(tmpl)
        tmpl_binary = clean_binary(tmpl_binary)
        score_binary, _ = match_template_sliding(query_binary, tmpl_binary)

        tmpl_clahe = preprocess_clahe_otsu(tmpl)
        tmpl_clahe = clean_binary(tmpl_clahe)
        score_clahe, _ = match_template_sliding(query_clahe, tmpl_clahe)

        tmpl_edges = extract_edges(tmpl)
        score_edges, _ = match_template_sliding(query_edges, tmpl_edges)

        # Path 4: Raw grayscale NCC via vertical-sliding matchTemplate
        t_h_scaled_raw = int(tmpl.shape[0] * (query_box.shape[1] / tmpl.shape[1]))
        tmpl_raw_resized = cv2.resize(tmpl, (query_box.shape[1], t_h_scaled_raw),
                                      interpolation=cv2.INTER_NEAREST)
        query_padded_raw = _make_vertical_slide_query(query_box, tmpl)
        score_raw = _vertical_slide_score(query_padded_raw, tmpl_raw_resized)
        score_raw = max(0.0, float(score_raw))

        bin_score = max(0.0, float(score_binary))
        clahe_score = max(0.0, float(score_clahe))
        edge_score = max(0.0, float(score_edges))
        ensemble = (BINARY_WEIGHT * 0.5 * bin_score +
                    BINARY_WEIGHT * 0.5 * clahe_score +
                    EDGE_WEIGHT * edge_score +
                    RAW_NCC_WEIGHT * score_raw)

        all_scores[digit] = {
            "binary": float(score_binary),
            "clahe_otsu": float(score_clahe),
            "edges": float(score_edges),
            "raw_ncc": float(score_raw),
            "ensemble": float(ensemble),
        }

    return all_scores


def adaptive_threshold_from_stats(
    stats_dict: Dict[str, float],
    base_threshold: float = 0.40,
) -> float:
    """Adjust confidence threshold based on image quality statistics.

    Uses odo_stats() output to raise/lower the confidence floor:
    - High contrast + high entropy: lower threshold (clean image)
    - Low contrast + low entropy: raise threshold (degraded image)
    - Glare (brightness > 200): raise threshold
    - Very dim (brightness < 40): raise threshold

    Args:
        stats_dict: Output of odo_stats().
        base_threshold: Default minimum confidence.

    Returns:
        Adjusted threshold in [0.25, 0.80].
    """
    contrast = float(stats_dict.get("odo_contrast", 50))
    brightness = float(stats_dict.get("odo_brightness", 128))
    entropy = float(stats_dict.get("odo_hist_entropy", 5.0))

    adjustment = 0.0

    # Good contrast (> 60): lower threshold
    if contrast > 60:
        adjustment -= 0.05
    # Excellent contrast (> 80): lower more
    if contrast > 80:
        adjustment -= 0.05

    # High entropy (> 6.0): lower threshold (rich texture)
    if entropy > 6.0:
        adjustment -= 0.03

    # Low contrast (< 30): raise threshold
    if contrast < 30:
        adjustment += 0.10

    # Low entropy (< 4.0): raise threshold (flat image)
    if entropy < 4.0:
        adjustment += 0.08

    # Glare (brightness > 200): raise threshold
    if brightness > 200:
        adjustment += 0.08

    # Very dim (brightness < 40): raise threshold
    if brightness < 40:
        adjustment += 0.10

    adjusted = base_threshold + adjustment
    return max(0.25, min(0.80, adjusted))


# ---------------------------------------------------------------------------
# Dynamic digit boundary refinement via vertical Sobel projection
# ---------------------------------------------------------------------------

def refine_digit_slots(
    gray: np.ndarray,
    slots: List[Tuple[int, int]],
    peak_threshold_frac: float = 0.25,
    max_shift: int = 5,
) -> List[Tuple[int, int]]:
    """Refine digit slot boundaries using vertical Sobel edge projection.

    Sobel X projection highlights vertical edges between digit windows
    (bars/cogs) that are stable across lighting conditions.  Each slot's
    boundaries are nudged toward the nearest detected edge peak, up to
    max_shift pixels.  This corrects for sub-pixel drift without rewiring
    the fixed slot layout.

    Args:
        gray: Grayscale odometer crop image.
        slots: List of (x0, x1) slot boundaries.
        peak_threshold_frac: Fraction of max projection for peak detection.
        max_shift: Maximum pixels a boundary can be shifted.

    Returns:
        Refined list of (x0, x1) slot boundaries.
    """
    h, w = gray.shape
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    vproj = np.sum(np.abs(sobel_x), axis=0)
    vmax = vproj.max()
    if vmax is None or vmax == 0:
        return slots

    # Detect strong edge peaks (digit separators)
    threshold_val = vmax * peak_threshold_frac
    strong = np.where(vproj > threshold_val)[0]
    edge_peaks: List[int] = []
    if len(strong) > 0:
        groups = []
        cur = [strong[0]]
        for i in range(1, len(strong)):
            if strong[i] - strong[i - 1] <= 3:
                cur.append(strong[i])
            else:
                groups.append(int(np.mean(cur)))
                cur = [strong[i]]
        groups.append(int(np.mean(cur)))
        edge_peaks = groups

    if not edge_peaks:
        return slots

    refined: List[Tuple[int, int]] = []
    for x0, x1 in slots:
        # Nudge left boundary toward nearest left edge peak
        new_x0 = x0
        left_candidates = [p for p in edge_peaks if abs(p - x0) <= max_shift]
        if left_candidates:
            new_x0 = min(left_candidates, key=lambda p: abs(p - x0))

        # Nudge right boundary toward nearest right edge peak
        new_x1 = x1
        right_candidates = [p for p in edge_peaks if abs(p - x1) <= max_shift]
        if right_candidates:
            new_x1 = min(right_candidates, key=lambda p: abs(p - x1))

        # Don't collapse a slot below minimum usable width.
        # 12 px matches process_crop's "< 10" skip guard with a
        # small safety margin.  Tighter than 12 and pos0 can get
        # squeezed off the left edge when the Sobel edge projection
        # picks up the odometer window border instead of digit edges.
        if new_x1 - new_x0 >= 12:
            refined.append((new_x0, new_x1))
        else:
            refined.append((x0, x1))

    return refined


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_pos5_templates(template_dir: str = None) -> Dict[Tuple[int, int], np.ndarray]:
    """Load ``pos5_digitD_nNN.png`` templates.

    Returns ``{(digit: int, npos: int): grayscale_image}``.
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    bank: Dict[Tuple[int, int], np.ndarray] = {}
    pat = re.compile(r"pos5_digit(\d+)_n(\d{2})\.png")
    for fn in os.listdir(template_dir):
        m = pat.match(fn)
        if not m:
            continue
        d, n = int(m.group(1)), int(m.group(2))
        img = cv2.imread(os.path.join(template_dir, fn), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            bank[(d, n)] = img
    return bank


def load_static_templates(template_dir: str = None) -> List[Optional[np.ndarray]]:
    """Load ``pos<N>_digit_avg.png`` for positions 0-4.

    Returns list of 5 grayscale images (or None if missing).
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    templates: List[Optional[np.ndarray]] = []
    for pos in range(5):
        path = os.path.join(template_dir, f"pos{pos}_digit_avg.png")
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        templates.append(img)
    return templates


# Legacy template bank (used by audit_decode.py v1 style)
def load_template_bank():
    """Load saved digit templates from TEMPLATE_DIR.

    Legacy format: ``pos<N>_digit<D>.png``.
    Used by audit_decode.py for v1-style digit matching.
    """
    bank = {}
    for fn in os.listdir(TEMPLATE_DIR):
        m = re.match(r"pos(\d)_digit(\d+)\.png", fn)
        if m:
            pos, d = int(m.group(1)), int(m.group(2))
            t = cv2.imread(os.path.join(TEMPLATE_DIR, fn), cv2.IMREAD_GRAYSCALE)
            if t is not None:
                bank[(pos, d)] = t
    return bank


def save_template(pos, val, gray_img, clock_pos=None):
    """Save digit template (legacy format)."""
    if pos == 5 and clock_pos is not None:
        fname = f"pos{pos}_digit{val}_clock{clock_pos}.png"
    else:
        fname = f"pos{pos}_digit{val}.png"
    cv2.imwrite(os.path.join(TEMPLATE_DIR, fname), gray_img)


# ---------------------------------------------------------------------------
# Template matching
# ---------------------------------------------------------------------------

def match_pos5(box: np.ndarray, npos: int,
               bank: Dict[Tuple[int, int], np.ndarray]) -> Tuple[Optional[int], float]:
    """Match pos5 box against templates near this npos.

    Uses aspect-ratio-preserving vertical sliding — the pos5 drum digit
    rolls up/down, so a rigid 1:1 comparison fails when the digit has
    moved even one pixel off centre.

    When no template is within NPOS_WINDOW of the needle position
    (template coverage gap in the 40-60 range), progressively expands
    the window up to 3× so one of the adjacent digit states is matched.
    """
    if npos is None:
        return None, 0.0

    for scale in (1, 2, 3):
        window = NPOS_WINDOW * scale
        best_d, best_s = None, -1.0
        for (d, tn), t in bank.items():
            dist = min(abs(npos - tn), 100 - abs(npos - tn))
            if dist > window:
                continue
            # Resize template width to match box, preserving aspect ratio
            t_h_scaled = int(t.shape[0] * (box.shape[1] / t.shape[1]))
            t_resized = cv2.resize(t, (box.shape[1], t_h_scaled),
                                   interpolation=cv2.INTER_NEAREST)
            query_padded = _make_vertical_slide_query(box, t)
            s = _vertical_slide_score(query_padded, t_resized)
            if s > best_s:
                best_s, best_d = s, d
        if best_d is not None and best_s >= MATCH_THRESHOLD:
            return best_d, best_s
        # If a match was found but below threshold, still return it on
        # the expanded pass — better than nothing.
        if best_d is not None:
            return best_d, best_s
    return best_d, best_s


def match_pos5_all(box: np.ndarray, npos: int,
                   bank: Dict[Tuple[int, int], np.ndarray]) -> List[Dict]:
    """Like match_pos5 but returns all candidate scores for debugging.

    Returns:
        List of {"digit": int, "npos": int, "score": float, "scores_by_path": {...}} sorted best-to-worst.
    """
    if npos is None:
        return []

    # Preprocess query for all paths
    box_adaptive = preprocess(box)
    box_otsu_global = cv2.GaussianBlur(box, (3, 3), 0)
    _, box_otsu_global = cv2.threshold(box_otsu_global, 0, 255,
                                        cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    candidates = []
    for (d, tn), t in bank.items():
        dist = min(abs(npos - tn), 100 - abs(npos - tn))
        if dist > NPOS_WINDOW:
            continue

        # Path 1: raw grayscale — vertical sliding to handle digit roll
        t_h_scaled = int(t.shape[0] * (box.shape[1] / t.shape[1]))
        t_raw = cv2.resize(t, (box.shape[1], t_h_scaled),
                           interpolation=cv2.INTER_NEAREST)
        query_padded_raw = _make_vertical_slide_query(box, t)
        s_raw = _vertical_slide_score(query_padded_raw, t_raw)

        # Path 2: adaptive threshold — vertical sliding
        t_adaptive = cv2.resize(t, (box.shape[1], t_h_scaled),
                                interpolation=cv2.INTER_NEAREST)
        t_adaptive = preprocess(t_adaptive)
        query_padded_ad = _make_vertical_slide_query(box_adaptive, t)
        s_adaptive = _vertical_slide_score(query_padded_ad, t_adaptive)

        # Path 3: global Otsu — vertical sliding
        bl = cv2.GaussianBlur(t_raw, (3, 3), 0)
        _, t_otsu = cv2.threshold(bl, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        query_padded_ot = _make_vertical_slide_query(box_otsu_global, t)
        s_otsu = _vertical_slide_score(query_padded_ot, t_otsu)

        # Best score across all paths
        best_score = max(s_raw, s_adaptive, s_otsu)

        candidates.append({
            "digit": d,
            "npos": tn,
            "score": best_score,
            "scores_by_path": {
                "raw": s_raw,
                "adaptive": s_adaptive,
                "otsu": s_otsu,
            },
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def match_static(box: np.ndarray, template: np.ndarray) -> Tuple[Optional[str], float]:
    """Match a static digit box against its composite template.

    Uses vertical sliding so minor digit roll does not kill the match.
    """
    if template is None:
        return None, 0.0
    q = preprocess(box)
    tp = preprocess(template)
    t_h_scaled = int(tp.shape[0] * (q.shape[1] / tp.shape[1]))
    t_resized = cv2.resize(tp, (q.shape[1], t_h_scaled),
                           interpolation=cv2.INTER_NEAREST)
    query_padded = _make_vertical_slide_query(q, template)
    s = _vertical_slide_score(query_padded, t_resized)
    return "avg", s


def match_digit(box_gray, pos, bank):
    """Match a digit box against legacy templates for a given position.

    Uses vertical sliding so minor digit roll does not kill the match.
    """
    cand = {d: t for (p, d), t in bank.items() if p == pos}
    if not cand:
        return None, 0.0
    bd, bs = None, -1.0
    for d, t in cand.items():
        t_h_scaled = int(t.shape[0] * (box_gray.shape[1] / t.shape[1]))
        t_resized = cv2.resize(t, (box_gray.shape[1], t_h_scaled),
                               interpolation=cv2.INTER_CUBIC)
        query_padded = _make_vertical_slide_query(box_gray, t)
        s = _vertical_slide_score(query_padded, t_resized)
        if s > bs:
            bs, bd = s, d
    return (bd, bs)


# ---------------------------------------------------------------------------
# DB query helpers
# ---------------------------------------------------------------------------

def get_last_processed_ts(session: Session) -> Optional[datetime]:
    """Return the most recent capture_ts in meter_readings, or None."""
    return session.query(func.max(MeterReading.capture_ts)).scalar()


def get_row_by_image_name(session: Session, image_name: str) -> Optional[MeterReading]:
    """Look up a single row by primary key (image_name)."""
    return session.get(MeterReading, image_name)


def get_rows_since(session: Session, since_ts: datetime,
                   status: Optional[str] = None) -> List[MeterReading]:
    """Return rows with capture_ts > since_ts, ordered chronologically."""
    q = session.query(MeterReading).filter(MeterReading.capture_ts > since_ts)
    if status:
        q = q.filter(MeterReading.status == status)
    return q.order_by(MeterReading.capture_ts.asc()).all()


# ---------------------------------------------------------------------------
# Debug drawing
# ---------------------------------------------------------------------------

def draw_dial_scan(img, lm, out_path):
    """Save a debug overlay showing hub, dial circle, marker, needle, odo box."""
    h, w = img.shape[:2]
    dbg = img.copy()

    cv2.circle(dbg, (lm["hub_x"], lm["hub_y"]), lm["hub_r"], (255, 0, 0), 2)
    cv2.circle(dbg, (lm["hub_x"], lm["hub_y"]), 8, (255, 0, 0), -1)
    cv2.line(dbg, (0, lm["hub_y"]), (w, lm["hub_y"]), (255, 255, 0), 2)

    if lm["marker_cx"] is not None and lm["marker_bbox"] is not None:
        bx, by, bw, bh = lm["marker_bbox"]
        cv2.rectangle(dbg, (bx - 3, by - 3), (bx + bw + 3, by + bh + 3), (0, 0, 255), 2)
        cv2.line(dbg, (lm["hub_x"], lm["hub_y"]),
                 (lm["marker_cx"], lm["marker_cy"]), (0, 165, 255), 2)

    cv2.circle(dbg, (int(lm["dial_cx"]), int(lm["dial_cy"])), lm["dial_r"], (0, 255, 0), 2)
    cv2.ellipse(dbg,
                (int(lm["dial_cx"]), int(lm["dial_cy"])),
                (lm["inner_rx"], lm["inner_ry"]), 0, 0, 360,
                (255, 191, 0), 2)

    for px, py in lm["needle_zone_pixels"]:
        cv2.circle(dbg, (px, py), 1, (255, 255, 0), -1)

    if len(lm["needle_zone_pixels"]) >= 3:
        nd = lm.get("needle_deg")
        if nd is not None:
            nr = np.radians(nd)
            tx = int(lm["hub_x"] + lm["dial_r"] * np.cos(nr))
            ty = int(lm["hub_y"] + lm["dial_r"] * np.sin(nr))
            cv2.line(dbg, (lm["hub_x"], lm["hub_y"]), (tx, ty), (0, 255, 255), 2)
            cv2.circle(dbg, (tx, ty), 4, (0, 255, 255), -1)

    # Odo crop box
    dr = lm["dial_r"]
    oh = int(dr * 0.32)
    ox1 = lm["hub_x"] - int(dr * 0.78)
    oy1 = lm["hub_y"] - int(dr * 0.64) + int(oh * 0.20)
    ox2 = ox1 + int(dr * 1.40)
    oy2 = oy1 + oh
    cv2.rectangle(dbg, (ox1, oy1), (ox2, oy2), (255, 0, 255), 2)

    # Anchor points
    cv2.circle(dbg, (lm["left_edge"], lm["hub_y"]), 6, (0, 255, 0), -1)
    cv2.putText(dbg, f"L={lm['left_edge']}", (lm["left_edge"] - 40, lm["hub_y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
    cv2.circle(dbg, (lm["right_edge"], lm["hub_y"]), 6, (0, 255, 0), -1)
    cv2.putText(dbg, f"R={lm['right_edge']}", (lm["right_edge"] + 5, lm["hub_y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

    cv2.imwrite(out_path, dbg)
    return out_path


def draw_odo_crop(crop_img, out_path, vproj_path=None):
    """Save odo crop with digit slots and vertical Sobel projection."""
    crop_h, crop_w = crop_img.shape[:2]
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    vproj = np.sum(np.abs(sobel_x), axis=0)

    dbg = crop_img.copy()
    slots = get_digit_slots(crop_w)
    for idx, (x1, x2) in enumerate(slots):
        cv2.rectangle(dbg, (max(0, x1), 2), (min(crop_w, x2), crop_h - 3),
                      DIGIT_COLORS[idx], 2)

    edge_lines = []
    vmax = vproj.max() or 1
    strong = np.where(vproj > vmax * 0.25)[0]
    if len(strong) > 0:
        groups = []
        cur = [strong[0]]
        for i in range(1, len(strong)):
            if strong[i] - strong[i - 1] <= 3:
                cur.append(strong[i])
            else:
                groups.append(cur)
                cur = [strong[i]]
        groups.append(cur)
        edge_lines = [int(np.mean(g)) for g in groups]

    for ex in edge_lines:
        cv2.line(dbg, (ex, 0), (ex, crop_h - 1), (0, 255, 0), 1)

    cv2.imwrite(out_path, dbg)

    if vproj_path:
        ph = 60
        proj_img = np.zeros((ph, crop_w, 3), dtype=np.uint8)
        for x in range(crop_w):
            yh = ph - int((vproj[x] / vmax) * (ph - 2))
            cv2.line(proj_img, (x, ph), (x, yh), (0, 255, 255), 1)
        for ex in edge_lines:
            cv2.line(proj_img, (ex, 0), (ex, ph), (0, 255, 0), 1)
        cv2.imwrite(vproj_path, np.vstack([dbg, proj_img]))
    return out_path


# ---------------------------------------------------------------------------
# Full decode debug — exposes all per-candidate match scores
# ---------------------------------------------------------------------------

def _img_to_base64_png(img: np.ndarray) -> Optional[str]:
    """Encode a grayscale or BGR image as base64 PNG data URL."""
    if img is None or img.size == 0:
        return None
    success, encoded = cv2.imencode(".png", img)
    if not success:
        return None
    b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _native(val):
    """Convert numpy scalar to Python native type for JSON serialization."""
    import numpy as np
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val


def debug_decode_crop(
    crop_path: str,
    pos5_bank: Dict[Tuple[int, int], np.ndarray],
    static_banks: List[Dict[int, List[np.ndarray]]],
) -> dict:
    """Full decode of a single odo crop with ALL per-candidate match scores.

    Returns a dict with "positions[i]" entries containing:
      - query_image_base64: the raw digit box
      - query_preprocessed_base64: the preprocessed (adaptive threshold) version
      - chosen: {"digit": int, "confidence": float}
      - candidates: {digit: {"scores": {"ensemble": ..., "binary": ..., ...}, "template_base64": ...}}

    Also saves a composite debug image to DEBUG_DIR.
    """
    fname = os.path.basename(crop_path)
    img = cv2.imread(crop_path)
    if img is None:
        return {"crop_file": fname, "error": "Failed to read crop image"}

    h, w = img.shape[:2]
    npos = npos_from_fname(fname)
    slots = get_digit_slots(w)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    slots = refine_digit_slots(gray, slots)

    positions = []
    pos_digits: List[Optional[int]] = [None] * 6
    pos_confs: List[float] = [0.0] * 6

    # ── pos0-4: static digit matching ──────────────────────────────
    for pos in range(5):
        x0, x1 = slots[pos]
        pos_data: dict = {
            "position": pos,
            "slot": [x0, x1],
            "chosen": None,
            "candidates": {},
            "query_image_base64": None,
            "query_preprocessed_base64": None,
        }

        if x1 - x0 < 10:
            positions.append(pos_data)
            continue

        box = gray[:, x0:x1]
        pos_data["query_image_base64"] = _img_to_base64_png(box)
        pos_data["query_preprocessed_base64"] = _img_to_base64_png(preprocess(box))

        bank = static_banks[pos]
        if not bank:
            positions.append(pos_data)
            continue

        available_digits = sorted(d for d, templates in bank.items() if templates)

        if len(available_digits) == 1:
            # Single-digit mode
            only_digit = available_digits[0]
            templates = bank[only_digit]
            best_s = -1.0
            q_paths = [
                preprocess(box),
                cv2.bitwise_not(preprocess_adaptive(box, 15, 4)),
            ]
            for q in q_paths:
                for t_img in templates:
                    tp = preprocess(t_img)
                    if q.shape != tp.shape:
                        tp = cv2.resize(tp, (q.shape[1], q.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)
                    s = cv2.matchTemplate(q, tp, cv2.TM_CCOEFF_NORMED)[0][0]
                    if s > best_s:
                        best_s = s
            boosted = float(0.5 + best_s * 0.5)
            pos_data["chosen"] = {"digit": only_digit, "confidence": round(boosted, 4)}
            pos_data["candidates"][str(only_digit)] = {
                "scores": {"ensemble": round(boosted, 4)},
                "template_base64": _img_to_base64_png(bank[only_digit][0]),
            }
            pos_digits[pos] = only_digit
            pos_confs[pos] = round(boosted, 4)
        else:
            # Multi-digit mode: ensemble matching
            ordered_templates: List[Optional[np.ndarray]] = [None] * 10
            for d in range(10):
                tmpls = bank.get(d, [])
                ordered_templates[d] = tmpls[0] if tmpls else None

            # Get full scores for all candidates
            all_scores = match_with_ensemble_all(box, ordered_templates)

            # Determine winner
            best_d = None
            best_c = -1.0
            for d, scores in all_scores.items():
                if scores["ensemble"] > best_c:
                    best_c = scores["ensemble"]
                    best_d = d

            # Also try simple adaptive threshold fallback (from match_static_digit)
            q = preprocess(box)
            for d, templates in bank.items():
                if not templates:
                    continue
                for t in templates:
                    tb = preprocess(t)
                    if q.shape != tb.shape:
                        tb = cv2.resize(tb, (q.shape[1], q.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)
                    s = cv2.matchTemplate(q, tb, cv2.TM_CCOEFF_NORMED)[0][0]
                    # Add fallback score if not already present
                    ds = all_scores.get(d)
                    if ds is None:
                        all_scores[d] = {"ensemble": float(s), "fallback_binary": float(s)}
                    else:
                        ds["fallback_binary"] = float(s)

            if best_d is not None:
                pos_data["chosen"] = {"digit": best_d, "confidence": round(best_c, 4)}
                pos_digits[pos] = best_d
                pos_confs[pos] = round(best_c, 4)

            # Build candidate entries
            for d in sorted(all_scores.keys()):
                tmpls = bank.get(d, [])
                tmpl_b64 = _img_to_base64_png(tmpls[0]) if tmpls else None
                pos_data["candidates"][str(d)] = {
                    "scores": all_scores[d],
                    "template_base64": tmpl_b64,
                }

        positions.append(pos_data)

    # ── pos5: npos-constrained matching ─────────────────────────────
    x0, x1 = slots[5]
    box5 = gray[:, x0:x1]
    candidates5 = match_pos5_all(box5, npos, pos5_bank)

    chosen5 = None
    if candidates5:
        best = candidates5[0]
        chosen5 = {"digit": best["digit"], "confidence": round(best["score"], 4)}
        pos_digits[5] = best["digit"]
        pos_confs[5] = round(best["score"], 4)
        if best["score"] < MATCH_THRESHOLD:
            chosen5["below_threshold"] = True

    # Add template images to pos5 candidates
    for c in candidates5:
        t_key = (c["digit"], c["npos"])
        tmpl_img = pos5_bank.get(t_key)
        c["template_base64"] = _img_to_base64_png(tmpl_img)

    pos5_data = {
        "position": 5,
        "slot": [x0, x1],
        "chosen": chosen5,
        "candidates": candidates5,
        "query_image_base64": _img_to_base64_png(box5),
        "query_preprocessed_base64": _img_to_base64_png(preprocess(box5)),
        "npos": npos,
        "pos5_source": "matched" if candidates5 else "none",
    }
    positions.append(pos5_data)

    # ── Compose reading ─────────────────────────────────────────────
    digits_str = "".join(str(d) if d is not None else "?" for d in pos_digits)
    reading = None
    if all(pos_digits[i] is not None for i in range(6)):
        integer_part = (pos_digits[0] * 10000 + pos_digits[1] * 1000 +
                        pos_digits[2] * 100 + pos_digits[3] * 10 + pos_digits[4])
        fractional_part = pos_digits[5] / 10.0 + (npos or 0) / 1000.0
        reading = round(integer_part + fractional_part, 3)

    valid_confs = [c for c in pos_confs if c > 0]
    overall_conf = round(sum(valid_confs) / len(valid_confs), 4) if valid_confs else 0.0

    # ── Generate composite debug image ──────────────────────────────
    debug_img_path = _draw_decode_debug_image(img, gray, slots, positions, npos, digits_str, reading, overall_conf, fname)

    return {
        "crop_file": fname,
        "digits": digits_str,
        "reading": reading,
        "confidence": overall_conf,
        "npos": npos,
        "positions": positions,
        "pos_digits": pos_digits,
        "pos_confs": pos_confs,
        "status": "OK",
        "debug_image": debug_img_path,
    }


def _draw_decode_debug_image(
    img_bgr: np.ndarray,
    gray: np.ndarray,
    slots: List[Tuple[int, int]],
    positions: List[dict],
    npos: Optional[int],
    digits_str: str,
    reading: Optional[float],
    confidence: float,
    fname: str,
) -> str:
    """Draw a composite debug image showing all digit positions with candidate comparison.

    Layout:
      - Top section: full odo crop with colored slot rectangles
      - For each position (0-5): a panel row showing:
        * Query digit box (left)
        * Each template candidate side-by-side with scores underneath

    Returns path to saved debug image.
    """
    crop_h, crop_w = img_bgr.shape[:2]

    # Calculate required canvas size
    panel_h = 140  # height per position panel
    header_h = 50
    total_h = crop_h + header_h + 6 * panel_h + 20
    # Expand width to fit all candidates if needed (max 10 digits x 50px)
    candidate_width = max(crop_w, 10 * 55 + 120)

    canvas = np.zeros((total_h, candidate_width, 3), dtype=np.uint8)
    canvas[:] = (20, 20, 20)  # dark background

    # ── Draw crop at top ─────────────────────────────────────────────
    canvas[:crop_h, :crop_w] = img_bgr
    # Slot rectangles
    for idx, (x0, x1) in enumerate(slots):
        color = DIGIT_COLORS[idx]
        cv2.rectangle(canvas, (x0, 2), (x1, crop_h - 3), color, 2)
        cx = (x0 + x1) // 2
        cv2.putText(canvas, f"pos{idx}", (cx - 15, crop_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1)

    # Info line under crop
    info_y = crop_h + 5
    info_text = f"Digits: {digits_str}  Reading: {reading if reading else 'N/A'}  Conf: {confidence:.3f}  npos: {npos}"
    cv2.putText(canvas, info_text, (8, info_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # ── Per-position panels ──────────────────────────────────────────
    panel_y = crop_h + header_h

    for pos_data in positions:
        pos = pos_data["position"]
        color = DIGIT_COLORS[pos]
        chosen = pos_data.get("chosen")

        # Position label
        cv2.putText(canvas, f"pos{pos}", (8, panel_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, 2)

        # Draw query box on left
        query_x = 8
        query_y = panel_y + 24
        query_img = None

        if pos_data.get("query_image_base64"):
            b64_data = pos_data["query_image_base64"]
            if b64_data.startswith("data:"):
                b64_data = b64_data.split(",", 1)[1]
            try:
                raw = base64.b64decode(b64_data)
                arr = np.frombuffer(raw, np.uint8)
                query_img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
            except Exception:
                pass

        if query_img is not None:
            qh, qw = query_img.shape
            # Scale to fit panel height
            scale = (panel_h - 30) / max(qh, 1)
            disp_w = max(30, int(qw * scale))
            disp_h = max(20, int(qh * scale))
            if query_img.shape[0] > 0 and query_img.shape[1] > 0:
                disp = cv2.resize(query_img, (disp_w, disp_h))
                if len(disp.shape) == 2:
                    disp = cv2.cvtColor(disp, cv2.COLOR_GRAY2BGR)
                canvas[query_y:query_y + disp_h, query_x:query_x + disp_w] = disp
            cv2.putText(canvas, "query", (query_x, query_y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        # Draw candidates
        cand_x = query_x + 75

        if pos == 5:
            # pos5: candidates list with npos labels
            candidates = pos_data.get("candidates", [])
            for ci, cand in enumerate(candidates[:10]):  # max 10 shown
                c_x = cand_x + ci * 55
                c_y = query_y
                digit = cand.get("digit")
                score = cand.get("score", 0)
                is_winner = (chosen and chosen.get("digit") == digit)

                # Draw template image
                tmpl_b64 = cand.get("template_base64")
                if tmpl_b64 and tmpl_b64.startswith("data:"):
                    try:
                        raw = base64.b64decode(tmpl_b64.split(",", 1)[1])
                        arr = np.frombuffer(raw, np.uint8)
                        tmpl_img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
                        if tmpl_img is not None and tmpl_img.size > 0:
                            scale = (panel_h - 55) / max(tmpl_img.shape[0], 1)
                            th = max(15, int(tmpl_img.shape[0] * scale))
                            tw = max(20, int(tmpl_img.shape[1] * scale))
                            disp_t = cv2.resize(tmpl_img, (tw, th))
                            if len(disp_t.shape) == 2:
                                disp_t = cv2.cvtColor(disp_t, cv2.COLOR_GRAY2BGR)
                            canvas[c_y:c_y + th, c_x:c_x + tw] = disp_t
                    except Exception:
                        pass

                # Border for winner
                if is_winner:
                    cv2.rectangle(canvas, (c_x - 2, c_y - 2),
                                  (c_x + 48, c_y + panel_h - 45),
                                  (0, 255, 0), 2)

                # Score label
                fmt_d = str(digit)
                if cand.get("npos") is not None:
                    fmt_d += f"@n{cand['npos']:02d}"
                score_color = (0, 255, 0) if score >= 0.55 else (255, 200, 0) if score >= 0.40 else (255, 100, 100)
                cv2.putText(canvas, fmt_d, (c_x, c_y + panel_h - 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.30, (200, 200, 200), 1)
                cv2.putText(canvas, f"{score:.3f}", (c_x, c_y + panel_h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.30, score_color, 1)
        else:
            # Static digits: candidates dict
            candidates = pos_data.get("candidates", {})
            # Sort by ensemble score descending
            sorted_cands = sorted(
                candidates.items(),
                key=lambda kv: kv[1].get("scores", {}).get("ensemble", 0),
                reverse=True,
            )
            for ci, (digit_str, cand_data) in enumerate(sorted_cands[:10]):
                c_x = cand_x + ci * 55
                c_y = query_y
                digit = int(digit_str)
                scores = cand_data.get("scores", {})
                ensemble_s = scores.get("ensemble", 0)
                is_winner = (chosen and chosen.get("digit") == digit)

                # Draw template image
                tmpl_b64 = cand_data.get("template_base64")
                if tmpl_b64 and tmpl_b64.startswith("data:"):
                    try:
                        raw = base64.b64decode(tmpl_b64.split(",", 1)[1])
                        arr = np.frombuffer(raw, np.uint8)
                        tmpl_img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
                        if tmpl_img is not None and tmpl_img.size > 0:
                            scale = (panel_h - 55) / max(tmpl_img.shape[0], 1)
                            th = max(15, int(tmpl_img.shape[0] * scale))
                            tw = max(20, int(tmpl_img.shape[1] * scale))
                            disp_t = cv2.resize(tmpl_img, (tw, th))
                            if len(disp_t.shape) == 2:
                                disp_t = cv2.cvtColor(disp_t, cv2.COLOR_GRAY2BGR)
                            canvas[c_y:c_y + th, c_x:c_x + tw] = disp_t
                    except Exception:
                        pass

                # Border for winner
                if is_winner:
                    cv2.rectangle(canvas, (c_x - 2, c_y - 2),
                                  (c_x + 48, c_y + panel_h - 45),
                                  (0, 255, 0), 2)

                # Detail scores
                binary_s = scores.get("binary", 0)
                clahe_s = scores.get("clahe_otsu", 0)
                edges_s = scores.get("edges", 0)
                raw_s = scores.get("raw_ncc", 0)

                score_color = (0, 255, 0) if ensemble_s >= 0.55 else (255, 200, 0) if ensemble_s >= 0.40 else (255, 100, 100)
                cv2.putText(canvas, str(digit), (c_x, c_y + panel_h - 48),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                # Multi-line scores in small font
                lines = [
                    f"ens:{ensemble_s:.2f}",
                    f"bi:{binary_s:.2f} cl:{clahe_s:.2f}",
                    f"ed:{edges_s:.2f} ra:{raw_s:.2f}",
                ]
                for li, line in enumerate(lines):
                    cv2.putText(canvas, line, (c_x, c_y + panel_h - 32 + li * 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                score_color if li == 0 else (160, 160, 160), 1)

        panel_y += panel_h

    # ── Save ─────────────────────────────────────────────────────────
    safe_name = fname.replace("/", "_").replace("\\", "_")
    out_name = f"decode_debug_{safe_name}"
    out_path = os.path.join(DEBUG_DIR, out_name)
    cv2.imwrite(out_path, canvas)
    log.info("Saved decode debug image: %s", out_path)
    return out_name