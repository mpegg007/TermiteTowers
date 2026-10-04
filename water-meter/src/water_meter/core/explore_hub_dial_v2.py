#!/usr/bin/env python3
"""DEBUG — Hub-based dial detection: hub center → scan bright rows above → find edges.

Algorithm:
 1. Find hub (blue dot) via distance-transform on closed red mask.
 2. Find left-side red marker blob (raw red, closest to horizon).
 3. Horizon = horizontal line through hub_y.
 4. Dial circle: radius = hub_x - left_edge, centered at hub.
 5. Inner ellipse: rx=0.90r, ry=0.75r (needle sweep zone boundary).
 6. Needle zone: red_raw pixels in annulus between inner ellipse and outer circle.
 7. Needle angle: centroid of zone pixels → line from hub through centroid to circle edge.
 8. Odometer box: from hub + dial_r proportions.

Output: ~/pictures/water_meter/templates/hub_dial_scan_*.jpg

Usage:
    .venv/bin/python scripts/water_meter/explore_hub_dial.py ~/pictures/water_meter/latest.jpg
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
    out_name = f"hub_dial_scan_{ts}.jpg"
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ── 1. red mask: raw (blob detection) + closed (hub detection) ──
    red_raw = cv2.bitwise_or(cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1),
                             cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2))
    red = cv2.morphologyEx(red_raw, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    dist = cv2.distanceTransform(red, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(dist)
    hub_x, hub_y = max_loc
    hub_r = int(dist[hub_y, hub_x])

    # ── 2. bright mask = dial face ──
    _, bright = cv2.threshold(blurred, BRIGHT_THRESH, 255, cv2.THRESH_BINARY)

    # ── 3. find scan row above needle/text area ──
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
        print("ERROR: no suitable scan row found", file=sys.stderr)
        sys.exit(1)

    bright_row = bright[scan_y, :].flatten()
    bright_idx = np.where(bright_row > 0)[0]
    left_edge = int(bright_idx[0])
    right_edge = int(bright_idx[-1])

    # ── 4. dial circle: centered at hub, bounded by both bright mask edges ──
    dial_cx = float(hub_x)
    dial_cy = float(hub_y)
    # Radius must not extend beyond left OR right bright mask tick
    dist_left  = hub_x - left_edge
    dist_right = right_edge - hub_x
    dial_r = min(dist_left, dist_right)
    if dial_r <= 0:
        dial_r = dist_left

    # ── 5. find left-side red marker blob (horizon anchor) ──
    hub_exclude_mask = np.zeros_like(red_raw)
    cv2.circle(hub_exclude_mask, (hub_x, hub_y), hub_r * 3, 255, -1)
    red_no_hub = cv2.bitwise_and(red_raw, cv2.bitwise_not(hub_exclude_mask))
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(red_no_hub)
    marker_cx = marker_cy = None
    marker_bbox = None
    marker_label = None
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
                    marker_label = lbl
        if marker_label is not None:
            marker_cx = int(centroids[marker_label][0])
            marker_cy = int(centroids[marker_label][1])
            sx = stats[marker_label, cv2.CC_STAT_LEFT]
            sy = stats[marker_label, cv2.CC_STAT_TOP]
            sw = stats[marker_label, cv2.CC_STAT_WIDTH]
            sh = stats[marker_label, cv2.CC_STAT_HEIGHT]
            # Make bbox square, centered on centroid
            side = max(int(sw), int(sh))
            bx = marker_cx - side // 2
            by = marker_cy - side // 2
            marker_bbox = (bx, by, side, side)
        else:
            marker_label = 1
            marker_cx = int(centroids[1][0])
            marker_cy = int(centroids[1][1])
            marker_bbox = (int(stats[1, cv2.CC_STAT_LEFT]), int(stats[1, cv2.CC_STAT_TOP]),
                           int(stats[1, cv2.CC_STAT_WIDTH]), int(stats[1, cv2.CC_STAT_HEIGHT]))

    # ── 6. inner ellipse: contain marker bbox, stay inside green circle ──
    if marker_bbox is not None:
        bx, by, bw, bh = marker_bbox
        h_dist = max(abs(bx - hub_x), abs(bx + bw - hub_x))
        v_dist = max(abs(by - hub_y), abs(by + bh - hub_y))
        # Sized to contain marker, but capped at 95% of dial_r so ellipse stays inside circle
        inner_rx = min(int(max(h_dist * 1.15, dial_r * 0.45)), int(dial_r * 0.95))
        inner_ry = min(int(max(v_dist * 1.15, dial_r * 0.40)), int(dial_r * 0.95))
    else:
        inner_rx = int(dial_r * 0.90)
        inner_ry = int(dial_r * 0.75)

    # ── 7. needle zone: red_raw pixels between inner ellipse and outer circle ──
    needle_zone_pixels = []
    for py in range(h):
        for px in range(w):
            if red_raw[py, px] > 0:
                dx = px - dial_cx
                dy = py - dial_cy
                r2 = dx*dx + dy*dy
                if r2 <= dial_r * dial_r:
                    e2 = (dx*dx)/(inner_rx*inner_rx) + (dy*dy)/(inner_ry*inner_ry)
                    if e2 > 1.0:
                        needle_zone_pixels.append((px, py))

    # DEBUG
    print(f"  Red blobs outside hub: {n_labels - 1}")
    for lbl in range(1, n_labels):
        cx = int(centroids[lbl][0]); cy = int(centroids[lbl][1])
        area = stats[lbl, cv2.CC_STAT_AREA]; side = "LEFT" if cx < hub_x else "RIGHT"
        dist = np.sqrt((cx - hub_x)**2 + (cy - hub_y)**2)
        print(f"    blob {lbl}: ({cx},{cy}) area={area} dist={dist:.0f} {side}")
    print(f"  Needle zone red pixels: {len(needle_zone_pixels)}")

    # ── 8. draw debug image ──
    dbg = img.copy()

    # hub
    cv2.circle(dbg, (hub_x, hub_y), hub_r, (255, 0, 0), 2)
    cv2.circle(dbg, (hub_x, hub_y), 8, (255, 0, 0), -1)
    cv2.putText(dbg, f"HUB ({hub_x},{hub_y}) r={hub_r}",
                (hub_x + 12, hub_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    # horizon line
    cv2.line(dbg, (0, hub_y), (w, hub_y), (255, 255, 0), 2)
    cv2.putText(dbg, f"center line y={hub_y}", (5, hub_y - 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1)

    # marker blob
    angle_deg = 0.0
    if marker_cx is not None and marker_cy is not None and marker_bbox is not None:
        bx, by, bw, bh = marker_bbox
        cv2.rectangle(dbg, (bx - 3, by - 3), (bx + bw + 3, by + bh + 3), (0, 0, 255), 2)
        blob_mask = (labels == marker_label).astype(np.uint8) * 255
        blob_color = np.zeros_like(dbg); blob_color[:] = (0, 0, 255)
        dbg = cv2.addWeighted(dbg, 1.0,
                              cv2.bitwise_and(blob_color, blob_color, mask=blob_mask), 0.4, 0)
        cv2.circle(dbg, (marker_cx, marker_cy), 6, (0, 0, 255), -1)
        cv2.circle(dbg, (marker_cx, marker_cy), 9, (0, 0, 255), 2)
        cv2.putText(dbg, f"RED2 ({marker_cx},{marker_cy}) area={stats[marker_label, cv2.CC_STAT_AREA]}",
                    (marker_cx + 10, marker_cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.line(dbg, (hub_x, hub_y), (marker_cx, marker_cy), (0, 165, 255), 2)
        dx_m = marker_cx - hub_x; dy_m = marker_cy - hub_y
        angle_deg = np.degrees(np.arctan2(dy_m, dx_m))
        mid_x = (hub_x + marker_cx) // 2; mid_y = (hub_y + marker_cy) // 2
        cv2.putText(dbg, f"{angle_deg:.1f} deg", (mid_x + 5, mid_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

    # odometer box
    odo_w = int(dial_r * 1.40); odo_h = int(dial_r * 0.32)
    odometer_x1 = hub_x - int(dial_r * 0.78); odometer_y1 = hub_y - int(dial_r * 0.64)
    odometer_x2 = odometer_x1 + odo_w; odometer_y2 = odometer_y1 + odo_h
    cv2.rectangle(dbg, (odometer_x1, odometer_y1), (odometer_x2, odometer_y2), (255, 0, 255), 2)
    cv2.putText(dbg, "ODOMETER", (odometer_x1, odometer_y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

    # scan row
    cv2.line(dbg, (0, scan_y), (w, scan_y), (0, 255, 255), 1)
    cv2.putText(dbg, f"scan row y={scan_y} (hub -{hub_y - scan_y})",
                (5, scan_y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

    # edge ticks
    cv2.line(dbg, (left_edge, scan_y - 20), (left_edge, scan_y + 20), (0, 255, 0), 2)
    cv2.putText(dbg, f"L={left_edge}", (left_edge - 25, scan_y - 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
    cv2.line(dbg, (right_edge, scan_y - 20), (right_edge, scan_y + 20), (0, 255, 0), 2)
    cv2.putText(dbg, f"R={right_edge}", (right_edge + 5, scan_y - 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

    # dial circle (green)
    if dial_r > 5 and dial_r < w:
        cv2.circle(dbg, (int(dial_cx), int(dial_cy)), dial_r, (0, 255, 0), 2)
        cv2.circle(dbg, (int(dial_cx), int(dial_cy)), 4, (0, 255, 0), -1)

    # inner ellipse (teal)
    cv2.ellipse(dbg, ((int(dial_cx), int(dial_cy)), (inner_rx * 2, inner_ry * 2), 0),
                (255, 191, 0), 2)
    cv2.putText(dbg, f"inner rx={inner_rx} ry={inner_ry}",
                (int(dial_cx) + 5, int(dial_cy) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 191, 0), 1)

    # needle zone pixels (cyan dots)
    for px, py in needle_zone_pixels:
        cv2.circle(dbg, (px, py), 1, (255, 255, 0), -1)

    # needle line: hub → centroid of cyan annulus pixels → circle edge
    if len(needle_zone_pixels) >= 3:
        nz_cx = sum(p[0] for p in needle_zone_pixels) / len(needle_zone_pixels)
        nz_cy = sum(p[1] for p in needle_zone_pixels) / len(needle_zone_pixels)
        nz_dx = nz_cx - hub_x; nz_dy = nz_cy - hub_y
        nz_angle = np.arctan2(nz_dy, nz_dx)
        tip_x = hub_x + int(dial_r * np.cos(nz_angle))
        tip_y = hub_y + int(dial_r * np.sin(nz_angle))
        cv2.line(dbg, (hub_x, hub_y), (tip_x, tip_y), (0, 255, 255), 2)  # bright cyan line
        cv2.circle(dbg, (tip_x, tip_y), 4, (0, 255, 255), -1)
        cv2.circle(dbg, (int(nz_cx), int(nz_cy)), 3, (0, 255, 255), 1)
        print(f"  Needle line: centroid=({int(nz_cx)},{int(nz_cy)}) tip=({tip_x},{tip_y}) angle={np.degrees(nz_angle):.0f} deg")

    cv2.putText(dbg, f"DIAL: ({int(dial_cx)},{int(dial_cy)})  r={dial_r}  (left-edge based)",
                (10, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.putText(dbg, f"L edge dist: {dial_r}px  R edge: {right_edge}",
                (10, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

    # brightness profile
    ph = 60
    profile = np.zeros((ph, w, 3), dtype=np.uint8)
    for x in range(w):
        yv = ph - int((bright_row[x] / 255.0) * (ph - 5))
        cv2.line(profile, (x, ph), (x, yv), (0, 255, 100), 1)
    cv2.line(profile, (hub_x, 0), (hub_x, ph), (255, 0, 0), 1)
    cv2.line(profile, (left_edge, 0), (left_edge, ph), (0, 255, 0), 1)
    cv2.line(profile, (right_edge, 0), (right_edge, ph), (0, 255, 0), 1)
    cv2.putText(profile, f"bright mask row y={scan_y}  (blue=hub, green=edges)",
                (10, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

    # ── odometer crop: extract the box region from original image ──
    crop_x1 = max(0, odometer_x1); crop_y1 = max(0, odometer_y1)
    crop_x2 = min(w, odometer_x2); crop_y2 = min(h, odometer_y2)
    odo_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
    crop_name = f"odo_crop_{ts}.jpg"
    crop_path = os.path.join(args.out_dir, crop_name)
    cv2.imwrite(crop_path, odo_crop)

    combined = np.vstack([dbg, profile])
    out_path = os.path.join(args.out_dir, out_name)
    cv2.imwrite(out_path, combined)
    print(f"ODOMETER CROP: {crop_path}")
    print(f"Saved: {out_path}")
    print(f"  Hub: ({hub_x}, {hub_y})  r={hub_r}")
    print(f"  Scan row: {scan_y}  (hub -{hub_y - scan_y})")
    print(f"  Edges: L={left_edge}  R={right_edge}  span={right_edge - left_edge}px")
    print(f"  Dial: cx={int(dial_cx)}  cy={int(dial_cy)}  r={dial_r}  (from L edge)")
    if marker_cx is not None:
        print(f"  Marker: ({marker_cx}, {marker_cy})")
    print(f"  Angle: {angle_deg:.1f} deg (hub→marker)")
    print(f"  Odometer box: ({odometer_x1},{odometer_y1})-({odometer_x2},{odometer_y2})")


if __name__ == "__main__":
    main()