#!/usr/bin/env python3
"""find_markers.py — Locate water meter landmarks without template matching.

Strategy (no templates — works with camera shift):
  1. White dial face  →  grayscale + threshold → largest bright contour → minEnclosingCircle
  2. NEPTUNE text     →  template match the "NEPTUNE" word as secondary anchor
  3. Needle pivot     →  tick-mark line intersection (radial lines converge at pivot)
  4. Needle angle     →  HSV red mask → largest contour centroid → angle from pivot
  5. Odometer ROI     →  known relative offset from dial center → edge projection refinement

Usage:
    .venv/bin/python scripts/water_meter/find_markers.py --file ~/pictures/water_meter/latest.jpg
    .venv/bin/python scripts/water_meter/find_markers.py --file ~/pictures/water_meter/latest.jpg --debug
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

# --- white dial face detection ---
DIAL_BRIGHT_THRESHOLD = 220     # grayscale threshold — only very bright white (dial face)
DIAL_BLUR_KERNEL = (9, 9)       # Gaussian blur kernel size
DIAL_MIN_AREA_FRAC = 0.005      # minimum contour area as fraction of image area
DIAL_MAX_RADIUS_FRAC = 0.45     # reject circles larger than 45% of image min dimension
DIAL_CIRCLE_FIT_MIN_POINTS = 8  # minimum contour points to attempt circle fit

# --- NEPTUNE text detection ---
NEPTUNE_TEMPLATE_PATH = os.path.expanduser(
    "~/pictures/water_meter/templates/neptune_text_template.png"
)
NEPTUNE_MATCH_MIN = 0.4

# --- needle pivot detection via tick-mark line intersection ---
PIVOT_LINE_THRESHOLD = 40       # HoughLinesP vote threshold
PIVOT_LINE_MIN_LENGTH = 20      # minimum line segment length (pixels)
PIVOT_LINE_MAX_GAP = 5          # maximum gap in a line segment
PIVOT_RADIAL_MIN_ANGLE = 15     # exclude near-horizontal (likely odometer edges)
PIVOT_RADIAL_MAX_ANGLE = 165    # exclude near-horizontal
PIVOT_MIN_RADIAL_LINES = 3      # minimum number of radial lines required

# --- needle angle detection ---
RED_LOWER_1 = np.array([0, 100, 50])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 50])
RED_UPPER_2 = np.array([180, 255, 255])
NEEDLE_MIN_AREA = 10

# --- odometer ROI ---
KNOWN_DIAL_RADIUS = 165.0
ODO_OFFSET_DX = -60
ODO_OFFSET_DY = -170
ODO_WIDTH = 330
ODO_HEIGHT = 55

# --- debug output ---
DEFAULT_DEBUG_DIR = os.path.expanduser("~/pictures/water_meter/templates")

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def find_markers(
    image: Union[str, np.ndarray],
    *,
    debug: bool = False,
    debug_dir: str = DEFAULT_DEBUG_DIR,
) -> dict:
    """Detect water meter landmarks in *image*.

    Parameters
    ----------
    image : str or np.ndarray
        Either a file path or an in-memory BGR image array.
    debug : bool
        If True, writes intermediate debug images to *debug_dir*.
    debug_dir : str
        Directory for debug output images.

    Returns
    -------
    dict with keys: dial_center, neptune_text, needle_pivot, needle_angle,
    odometer_roi, alignment_score, diagnostics.
    """
    if isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image}")
    else:
        img = image

    if img is None or img.size == 0:
        raise ValueError("Empty image")

    ih, iw = img.shape[:2]
    img_area = ih * iw
    min_dial_area = DIAL_MIN_AREA_FRAC * img_area
    max_dial_radius = DIAL_MAX_RADIUS_FRAC * min(ih, iw)

    diag: Dict[str, Any] = {}

    if debug:
        os.makedirs(debug_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"markers_{ts}"

    debug_img = img.copy() if debug else None

    # 1. find white dial face
    dial_result = _find_dial_face(
        img, min_dial_area, max_dial_radius, diag, debug, debug_dir,
        prefix if debug else "", debug_img,
    )

    # 2. NEPTUNE text
    neptune_result = _find_neptune_text(
        img, dial_result, debug, debug_dir,
        prefix if debug else "", debug_img,
    )

    # 3. needle pivot (tick-mark intersection)
    pivot_result = _find_needle_pivot(
        img, dial_result, diag, debug, debug_dir,
        prefix if debug else "", debug_img,
    )

    # 4. needle angle
    angle_result = _find_needle_angle(
        img, pivot_result, dial_result, diag, debug, debug_dir,
        prefix if debug else "", debug_img,
    )

    # 5. odometer ROI
    odo_result = _find_odometer_roi(
        img, dial_result, diag, debug, debug_dir,
        prefix if debug else "", debug_img,
    )

    # alignment score
    scores = [
        dial_result[3] if dial_result else 0.0,
        neptune_result[4] if neptune_result else 0.0,
        pivot_result[2] if pivot_result else 0.0,
        angle_result[1] if angle_result else 0.0,
        odo_result[4] if odo_result else 0.0,
    ]
    alignment_score = (
        sum(scores) / max(len(scores), 1) if any(s > 0 for s in scores) else 0.0
    )

    result = {
        "dial_center": dial_result,
        "neptune_text": neptune_result,
        "needle_pivot": pivot_result,
        "needle_angle": angle_result,
        "odometer_roi": odo_result,
        "alignment_score": round(alignment_score, 4),
        "diagnostics": diag,
    }

    if debug and debug_img is not None:
        out_path = os.path.join(debug_dir, f"{prefix}_debug_final.jpg")
        cv2.imwrite(out_path, debug_img)
        print(f"[DEBUG] final composite → {out_path}", file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# Stage 1 — white dial face
# ---------------------------------------------------------------------------


def _find_dial_face(
    img, min_area, max_radius, diag, debug, debug_dir, prefix, debug_img,
):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, DIAL_BLUR_KERNEL, 0)
    _, thresh = cv2.threshold(blurred, DIAL_BRIGHT_THRESHOLD, 255, cv2.THRESH_BINARY)
    bright_pixels = int(cv2.countNonZero(thresh))
    diag["bright_pixels_found"] = bright_pixels

    if debug:
        cv2.imwrite(os.path.join(debug_dir, f"{prefix}_debug_01_bright_mask.jpg"), thresh)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    diag["bright_contours"] = len(contours)
    diag["contours_considered"] = []

    debug_contours = img.copy() if debug else None

    if not contours:
        diag["dial_used"] = "none (no contours)"
        return None

    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for idx, ct in enumerate(sorted_contours):
        area = cv2.contourArea(ct)
        n_pts = len(ct)
        (cx, cy), radius = cv2.minEnclosingCircle(ct)
        radius = float(radius)

        rejected = None
        if area < min_area:
            rejected = f"area {int(area)} < min {int(min_area)}"
        elif n_pts < DIAL_CIRCLE_FIT_MIN_POINTS:
            rejected = f"points {n_pts} < min {DIAL_CIRCLE_FIT_MIN_POINTS}"
        elif radius > max_radius:
            rejected = f"radius {int(radius)} > max {int(max_radius)}"

        entry = {"rank": idx, "area": int(area), "radius": int(radius), "points": n_pts}
        if rejected:
            entry["rejected_reason"] = rejected
        else:
            entry["rejected_reason"] = None
        diag["contours_considered"].append(entry)

        if rejected is None:
            circle_area = np.pi * radius * radius
            fill_ratio = min(area / circle_area, 1.0) if circle_area > 0 else 0.0
            confidence = round(fill_ratio, 4)
            cx, cy = float(cx), float(cy)
            diag["dial_used"] = "bright_contour_fit"
            diag["dial_fill_ratio"] = fill_ratio

            if debug_img is not None:
                cv2.circle(debug_img, (int(cx), int(cy)), int(radius), (0, 255, 0), 2)
                cv2.circle(debug_img, (int(cx), int(cy)), 4, (0, 255, 0), -1)
                cv2.putText(debug_img, f"dial r={int(radius)} c={confidence:.2f}",
                            (int(cx) + 10, int(cy) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            return (cx, cy, radius, confidence)

    diag["dial_used"] = "none (all contours rejected)"
    diag["dial_fill_ratio"] = 0.0
    return None


# ---------------------------------------------------------------------------
# Stage 2 — NEPTUNE text
# ---------------------------------------------------------------------------


def _find_neptune_text(img, dial_result, debug, debug_dir, prefix, debug_img):
    if not os.path.exists(NEPTUNE_TEMPLATE_PATH):
        return None
    neptune_tmpl = cv2.imread(NEPTUNE_TEMPLATE_PATH)
    if neptune_tmpl is None:
        return None
    th, tw = neptune_tmpl.shape[:2]
    ih, iw = img.shape[:2]

    if dial_result is not None:
        dial_cx, dial_cy, dial_r, _ = dial_result
        half = int(dial_r * 1.2)
        x1 = max(0, int(dial_cx) - half)
        y1 = max(0, int(dial_cy) - half)
        x2 = min(iw, int(dial_cx) + half)
        y2 = min(ih, int(dial_cy) + half)
        search_roi = img[y1:y2, x1:x2] if x2 > x1 and y2 > y1 else img
        offset_x, offset_y = x1, y1
    else:
        search_roi = img
        offset_x, offset_y = 0, 0

    result = cv2.matchTemplate(search_roi, neptune_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < NEPTUNE_MATCH_MIN:
        return None

    nx = offset_x + max_loc[0]
    ny = offset_y + max_loc[1]
    confidence = round(float(max_val), 4)
    return (nx, ny, tw, th, confidence)


# ---------------------------------------------------------------------------
# Stage 3 — needle pivot (tick-mark line intersection)
# ---------------------------------------------------------------------------


def _find_needle_pivot(img, dial_result, diag, debug, debug_dir, prefix, debug_img):
    """Find pivot by detecting tick-mark line segments and computing their intersection."""
    if dial_result is None:
        diag["pivot_used"] = "no dial center"
        return None

    dial_cx, dial_cy, dial_r, _ = dial_result
    ih, iw = img.shape[:2]

    # Circular mask for dial face
    mask = np.zeros((ih, iw), dtype=np.uint8)
    cv2.circle(mask, (int(dial_cx), int(dial_cy)), int(dial_r * 0.90), 255, -1)

    # Edges within the dial mask
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges_all = cv2.Canny(blurred, 60, 150)
    edges = cv2.bitwise_and(edges_all, edges_all, mask=mask)

    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,
        threshold=PIVOT_LINE_THRESHOLD,
        minLineLength=PIVOT_LINE_MIN_LENGTH,
        maxLineGap=PIVOT_LINE_MAX_GAP,
    )

    diag["pivot_lines_found"] = 0 if lines is None else len(lines)

    if debug:
        pivot_dbg = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        if lines is not None:
            for seg in lines:
                x1, y1, x2, y2 = int(seg[0]), int(seg[1]), int(seg[2]), int(seg[3])
                cv2.line(pivot_dbg, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.imwrite(os.path.join(debug_dir, f"{prefix}_debug_04_pivot_lines.jpg"), pivot_dbg)

    if lines is None or len(lines) < PIVOT_MIN_RADIAL_LINES:
        diag["pivot_used"] = f"lines found: {0 if lines is None else len(lines)} (need {PIVOT_MIN_RADIAL_LINES})"
        return None

    # Filter to radial lines
    radial_lines = []
    for seg in lines:
        x1, y1, x2, y2 = int(seg[0]), int(seg[1]), int(seg[2]), int(seg[3])
        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        if PIVOT_RADIAL_MIN_ANGLE <= angle <= PIVOT_RADIAL_MAX_ANGLE:
            radial_lines.append((x1, y1, x2, y2))

    diag["pivot_radial_lines"] = len(radial_lines)

    if len(radial_lines) < PIVOT_MIN_RADIAL_LINES:
        diag["pivot_used"] = f"radial lines: {len(radial_lines)} (need {PIVOT_MIN_RADIAL_LINES})"
        return None

    # Compute all pairwise intersections
    intersections = []
    for i in range(len(radial_lines)):
        for j in range(i + 1, len(radial_lines)):
            pt = _line_intersection(*(radial_lines[i]), *(radial_lines[j]))
            if pt is not None:
                intersections.append(pt)

    diag["pivot_intersections"] = len(intersections)

    if len(intersections) < 2:
        diag["pivot_used"] = f"intersections: {len(intersections)}"
        return None

    # Cluster: take median intersection, reject outliers
    pts = np.array(intersections, dtype=np.float32)
    median_pt = np.median(pts, axis=0)
    distances = np.linalg.norm(pts - median_pt, axis=1)
    dist_median = float(np.median(distances))
    if dist_median < 1.0:
        dist_median = 20.0
    inliers = pts[distances < dist_median * 3.0]

    if len(inliers) < 2:
        px, py = float(median_pt[0]), float(median_pt[1])
        confidence = 0.3
    else:
        cluster_center = np.mean(inliers, axis=0)
        cluster_std = float(np.std(inliers, axis=0).mean()) if len(inliers) > 1 else 50.0
        confidence = round(min(1.0, max(0.1, 1.0 - cluster_std / 30.0)), 4)
        px, py = float(cluster_center[0]), float(cluster_center[1])

    diag["pivot_used"] = (
        f"tick-intersect ({int(px)}, {int(py)}) "
        f"radial={len(radial_lines)} intersections={len(intersections)} inliers={len(inliers)}"
    )
    diag["pivot_confidence"] = confidence

    if debug_img is not None:
        cv2.circle(debug_img, (int(px), int(py)), 5, (255, 0, 0), -1)
        cv2.drawMarker(debug_img, (int(px), int(py)), (255, 0, 0),
                       markerType=cv2.MARKER_CROSS, markerSize=12, thickness=2)
        cv2.putText(debug_img, f"pivot tick {confidence:.2f}",
                    (int(px) + 10, int(py) + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        for x1, y1, x2, y2 in radial_lines:
            cv2.line(debug_img, (x1, y1), (x2, y2), (255, 100, 100), 1)

    return (px, py, confidence)


def _line_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    return (px, py)


# ---------------------------------------------------------------------------
# Stage 4 — needle angle
# ---------------------------------------------------------------------------


def _find_needle_angle(img, pivot_result, dial_result, diag, debug, debug_dir, prefix, debug_img):
    ih, iw = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_or(
        cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1),
        cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2),
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    if debug:
        red_dbg = img.copy()
        red_dbg[mask > 0] = (0, 255, 255)
        cv2.imwrite(os.path.join(debug_dir, f"{prefix}_debug_05_red_mask.jpg"), red_dbg)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        diag["needle_angle_used"] = "no red contours"
        return None

    largest = max(contours, key=cv2.contourArea)
    needle_area = cv2.contourArea(largest)
    if needle_area < NEEDLE_MIN_AREA:
        diag["needle_angle_used"] = f"red contour area {int(needle_area)} too small"
        return None

    M = cv2.moments(largest)
    if M["m00"] == 0:
        diag["needle_angle_used"] = "moment m00=0"
        return None

    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]

    if pivot_result is not None:
        origin_x, origin_y = pivot_result[0], pivot_result[1]
        diag["needle_origin_used"] = "pivot"
    elif dial_result is not None:
        origin_x, origin_y = dial_result[0], dial_result[1]
        diag["needle_origin_used"] = "dial_center"
    else:
        origin_x, origin_y = iw / 2.0, ih / 2.0
        diag["needle_origin_used"] = "image_center"

    deg = float(np.degrees(np.arctan2(cx - origin_x, -(cy - origin_y))))
    if deg < 0:
        deg += 360.0
    confidence = round(min(needle_area / 500.0, 1.0), 4)
    diag["needle_area"] = int(needle_area)
    diag["needle_centroid"] = (int(cx), int(cy))
    diag["needle_angle_used"] = f"origin={diag['needle_origin_used']} angle={deg:.1f}"

    if debug_img is not None:
        cv2.line(debug_img, (int(origin_x), int(origin_y)), (int(cx), int(cy)), (0, 0, 255), 2)
        cv2.circle(debug_img, (int(cx), int(cy)), 6, (0, 0, 255), -1)

    return (deg, confidence)


# ---------------------------------------------------------------------------
# Stage 5 — odometer ROI
# ---------------------------------------------------------------------------


def _find_odometer_roi(img, dial_result, diag, debug, debug_dir, prefix, debug_img):
    if dial_result is None:
        diag["odometer_used"] = "no dial center"
        return None

    dial_cx, dial_cy, dial_r, _ = dial_result
    ih, iw = img.shape[:2]
    scale = dial_r / KNOWN_DIAL_RADIUS if KNOWN_DIAL_RADIUS > 0 else 1.0

    ox = max(0, int(dial_cx + ODO_OFFSET_DX * scale))
    oy = max(0, int(dial_cy + ODO_OFFSET_DY * scale))
    ow = min(max(10, int(ODO_WIDTH * scale)), iw - ox)
    oh = min(max(5, int(ODO_HEIGHT * scale)), ih - oy)

    if ow <= 0 or oh <= 0:
        diag["odometer_used"] = "ROI OOB"
        return None

    roi = img[oy:oy + oh, ox:ox + ow]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    h_proj = np.sum(edges, axis=1)
    diag["odometer_h_proj_max"] = int(h_proj.max()) if h_proj.size > 0 else 0

    if debug:
        odo_dbg = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        max_val = max(h_proj.max(), 1)
        for row_idx, val in enumerate(h_proj):
            bar_len = min(int(val / max_val * ow), ow - 1)
            if bar_len > 0:
                cv2.line(odo_dbg, (0, row_idx), (bar_len, row_idx), (0, 255, 0), 1)
        cv2.imwrite(os.path.join(debug_dir, f"{prefix}_debug_06_odometer_roi.jpg"), odo_dbg)

    if h_proj.max() == 0:
        diag["odometer_edge_active_rows"] = 0
        diag["odometer_used"] = "geometry_only"
        confidence = 0.1
    else:
        threshold = h_proj.max() * 0.2
        active_rows = np.where(h_proj > threshold)[0]
        diag["odometer_edge_active_rows"] = int(len(active_rows))
        if len(active_rows) >= 2:
            top = int(active_rows[0])
            bottom = int(active_rows[-1])
            oy = oy + top
            oh = max(10, bottom - top)
            confidence = min(round(float(len(active_rows)) / float(oh), 4) if oh > 0 else 0.1, 1.0)
            diag["odometer_used"] = "edge_projection_refined"
        else:
            confidence = 0.2
            diag["odometer_used"] = "geometry_only"

    if debug_img is not None:
        cv2.rectangle(debug_img, (ox, oy), (ox + ow, oy + oh), (255, 255, 0), 2)

    return (ox, oy, ow, oh, confidence)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Locate water meter landmarks.")
    parser.add_argument("--file", required=True, help="Path to water meter image.")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-dir", default=DEFAULT_DEBUG_DIR)
    args = parser.parse_args(argv)

    image_path = os.path.expanduser(args.file)
    if not os.path.exists(image_path):
        print(f"ERROR: not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = find_markers(image_path, debug=args.debug, debug_dir=args.debug_dir)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()