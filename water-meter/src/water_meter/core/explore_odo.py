#!/usr/bin/env python3
"""Odometer box exploration — vertical line analysis to find 6-digit boundaries.

Uses Sobel X edge detection on the crop to find structural elements:
thick black bars, cog wheels, digit windows. Maps them to 6 digit slots
and draws colored boxes around each.

Output: ~/pictures/water_meter/templates/odo_scan_*.jpg
        ~/pictures/water_meter/templates/odo_crop_*.jpg

Usage:
    .venv/bin/python scripts/water_meter/explore_odo.py ~/pictures/water_meter/latest.jpg
"""

import argparse, os, sys
from datetime import datetime
import cv2
import numpy as np

OUT = os.path.expanduser("~/pictures/water_meter/templates")
RED_LOWER_1 = np.array([0, 100, 50]); RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 50]); RED_UPPER_2 = np.array([180, 255, 255])
BRIGHT_THRESH = 200
MIN_BRIGHT_FRAC = 0.30

DIGIT_COLORS = [
    (0, 255, 0),     # 1 green
    (255, 0, 0),     # 2 red
    (255, 255, 0),   # 3 cyan
    (255, 0, 255),   # 4 magenta
    (0, 255, 255),   # 5 yellow
    (0, 165, 255),   # 6 orange
]


def find_vlines(crop_img):
    """Find vertical edge columns in a grayscale odometer crop."""
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    abs_x = np.abs(sobel_x)
    vproj = np.sum(abs_x, axis=0)
    if vproj.max() == 0:
        return vproj, []
    vproj_thresh = vproj.max() * 0.25
    strong_vcols = np.where(vproj > vproj_thresh)[0]
    edge_lines = []
    if len(strong_vcols) > 0:
        groups = []
        current = [strong_vcols[0]]
        for i in range(1, len(strong_vcols)):
            if strong_vcols[i] - strong_vcols[i - 1] <= 3:
                current.append(strong_vcols[i])
            else:
                groups.append(current)
                current = [strong_vcols[i]]
        groups.append(current)
        for g in groups:
            edge_lines.append(int(np.mean(g)))
    return vproj, edge_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--out-dir", default=OUT)
    args = parser.parse_args()
    p = os.path.expanduser(args.image)
    img = cv2.imread(p)
    if img is None:
        print(f"ERROR: cannot read {p}", file=sys.stderr); sys.exit(1)
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h_img, w_img = img.shape[:2]
    gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray_full, (9, 9), 0)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ── landmark detection ──
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
    for offset in range(0, h_img, 2):
        test_y = hub_y - offset
        if test_y < 5:
            break
        row = bright[test_y, :]
        if row[0] > 0 or row[-1] > 0:
            continue
        if np.count_nonzero(row) / w_img >= MIN_BRIGHT_FRAC:
            scan_y = test_y
            break
    if scan_y is None:
        for y in range(hub_y - 1, 0, -1):
            if np.count_nonzero(bright[y, :]) > 50:
                scan_y = y
                break
    if scan_y is None:
        print("ERROR: no suitable scan row found", file=sys.stderr)
        sys.exit(1)

    bright_row = bright[scan_y, :].flatten()
    bright_idx = np.where(bright_row > 0)[0]
    left_edge = int(bright_idx[0])
    dial_r = hub_x - left_edge
    dial_cx = float(hub_x); dial_cy = float(hub_y)

    # marker
    hub_exclude_mask = np.zeros_like(red_raw)
    cv2.circle(hub_exclude_mask, (hub_x, hub_y), hub_r * 3, 255, -1)
    red_no_hub = cv2.bitwise_and(red_raw, cv2.bitwise_not(hub_exclude_mask))
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(red_no_hub)
    marker_cx = marker_cy = None
    if n_labels > 1:
        best_dy = float('inf')
        for lbl in range(1, n_labels):
            cx = int(centroids[lbl][0]); cy = int(centroids[lbl][1])
            area = stats[lbl, cv2.CC_STAT_AREA]
            if cx < hub_x and area > 500:
                dy = abs(cy - hub_y)
                if dy < best_dy:
                    best_dy = dy
                    marker_cx = cx; marker_cy = cy
    angle_deg = 0.0
    if marker_cx is not None:
        angle_deg = np.degrees(np.arctan2(marker_cy - hub_y, marker_cx - hub_x))

    # ── odometer box ──
    odo_w = int(dial_r * 1.40)
    odo_h = int(dial_r * 0.32)
    odo_x1 = hub_x - int(dial_r * 0.78)
    odo_y1 = hub_y - int(dial_r * 0.64)
    odo_x2 = odo_x1 + odo_w
    odo_y2 = odo_y1 + odo_h

    # ── extract crop ──
    crop_x1 = max(0, odo_x1); crop_y1 = max(0, odo_y1)
    crop_x2 = min(w_img, odo_x2); crop_y2 = min(h_img, odo_y2)
    odo_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
    crop_h, crop_w = odo_crop.shape[:2]

    # ── vertical line analysis ──
    vproj, edge_lines = find_vlines(odo_crop)
    print(f"  Edge lines in crop: {edge_lines}")

    # ── define 6 digit boxes (equal width, bar-separated) ──
    # Pattern from vertical edge analysis:
    #   d1: start=24  end=24+54=78     gap → bar(91,118)
    #   d2: start=119 end=119+54=173   gap → cog/bar(204,229)
    #   d3: start=197 end=197+54=251   gap → bar(262,288)
    #   d4: start=289 end=289+54=343   gap → bar(343,365)
    #   d5: start=368 end=368+54=422   gap → bar(432,486)
    #   d6: start=432 (bar start)  end=507 (last edge)

    # Detect thick bars
    thick_bar_starts = []
    thick_bar_ends = []
    for i in range(len(edge_lines) - 1):
        gap = edge_lines[i + 1] - edge_lines[i]
        if gap > 20:
            thick_bar_starts.append(edge_lines[i])
            thick_bar_ends.append(edge_lines[i + 1])

    digit_w = 54
    d1_s = edge_lines[0] if edge_lines else 24
    d1_e = d1_s + digit_w

    d2_s = 119
    d2_e = d2_s + digit_w

    d3_s = 197
    d3_e = d3_s + digit_w

    d4_s = 289
    d4_e = d4_s + digit_w

    d5_s = 368
    d5_e = d5_s + digit_w

    d6_s = 432 if edge_lines and edge_lines[-1] > 432 else 432
    d6_e = edge_lines[-1] if edge_lines else 507

    digit_boxes = [
        (d1_s, d1_e),
        (d2_s, d2_e),
        (d3_s, d3_e),
        (d4_s, d4_e),
        (d5_s, d5_e),
        (d6_s, d6_e),
    ]

    # ── draw debug image on crop ──
    dbg_crop = odo_crop.copy()
    for idx, (dx1, dx2) in enumerate(digit_boxes):
        color = DIGIT_COLORS[idx]
        cv2.rectangle(dbg_crop, (int(dx1), 2), (int(dx2), crop_h - 3), color, 2)
        cx = (dx1 + dx2) / 2
        cv2.putText(dbg_crop, f"{idx + 1}", (int(cx) - 8, crop_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Also draw edge lines and thick bars on crop
    for ex in edge_lines:
        cv2.line(dbg_crop, (ex, 0), (ex, crop_h - 1), (0, 255, 0), 1)
    for sx, ex in zip(thick_bar_starts, thick_bar_ends):
        cv2.rectangle(dbg_crop, (sx, 0), (ex, crop_h - 1), (255, 255, 255), 1)

    # ── save crop with boxes ──
    crop_name = f"odo_crop_{ts}.jpg"
    crop_path = os.path.join(args.out_dir, crop_name)
    cv2.imwrite(crop_path, dbg_crop)

    # ── vproj debug ──
    proj_h = 60
    proj_img = np.zeros((proj_h, crop_w, 3), dtype=np.uint8)
    vpmax = vproj.max() or 1
    for x in range(crop_w):
        yh = proj_h - int((vproj[x] / vpmax) * (proj_h - 2))
        cv2.line(proj_img, (x, proj_h), (x, yh), (0, 255, 255), 1)
    for ex in edge_lines:
        cv2.line(proj_img, (ex, 0), (ex, proj_h), (0, 255, 0), 1)
    vproj_name = f"odo_vproj_{ts}.jpg"
    cv2.imwrite(os.path.join(args.out_dir, vproj_name),
                np.vstack([dbg_crop, proj_img]))

    print(f"ODOMETER CROP: {crop_path}")
    print(f"VPROJ: {args.out_dir}/{vproj_name}")
    print(f"  Crop size: {crop_w}x{crop_h}")
    print(f"  Thick bar pairs: {list(zip(thick_bar_starts, thick_bar_ends))}")
    print(f"  Digit boxes (crop coords):")
    for idx, (dx1, dx2) in enumerate(digit_boxes):
        print(f"    Digit {idx + 1}: {int(dx1)}–{int(dx2)}  ({int(dx2 - dx1)}px)")
    print(f"  Hub: ({hub_x}, {hub_y})  Dial: r={dial_r}  Angle: {angle_deg:.1f} deg")


if __name__ == "__main__":
    main()