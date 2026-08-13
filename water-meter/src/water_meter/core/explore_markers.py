#!/usr/bin/env python3
"""
explore_markers.py — Generate debug images showing ALL candidate detections for each
landmark. No decisions, no downstream extraction — just labeled visualizations.

Outputs: ~/pictures/water_meter/templates/explore_*.jpg

Usage:
    .venv/bin/python scripts/water_meter/explore_markers.py ~/pictures/water_meter/latest.jpg
    .venv/bin/python scripts/water_meter/explore_markers.py ~/pictures/water_meter/water_meter_20260719_093806.jpg
"""

import argparse, os, sys
from datetime import datetime
import cv2
import numpy as np

OUT = os.path.expanduser("~/pictures/water_meter/templates")
RED_LOWER_1 = np.array([0, 100, 50]); RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 50]); RED_UPPER_2 = np.array([180, 255, 255])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Path to water meter image")
    parser.add_argument("--out-dir", default=OUT)
    args = parser.parse_args()
    path = os.path.expanduser(args.image)
    img = cv2.imread(path)
    if img is None:
        print(f"ERROR: cannot read {path}", file=sys.stderr); sys.exit(1)
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pfx = f"explore_{ts}"
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ========== DIAL: bright threshold + circle fit ==========
    for level, t in [("low", 180), ("mid", 210), ("high", 230), ("vhigh", 245)]:
        dbg = img.copy()
        _, mask = cv2.threshold(cv2.GaussianBlur(gray, (9, 9), 0), t, 255, cv2.THRESH_BINARY)
        dbg[mask > 0] = (dbg[mask > 0] * 0.5 + np.array([0, 255, 255]) * 0.5).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            ct = max(contours, key=cv2.contourArea)
            (cx, cy), r = cv2.minEnclosingCircle(ct); cx, cy, r = int(cx), int(cy), int(r)
            area = cv2.contourArea(ct)
            cv2.circle(dbg, (cx, cy), r, (0, 255, 0), 2)
            cv2.circle(dbg, (cx, cy), 4, (0, 255, 0), -1)
            cv2.putText(dbg, f"thresh={t}  r={r}  area={int(area)}  fill={area/(np.pi*r*r):.2f}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(dbg, f"thresh={t}  NO CONTOURS", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_dial_bright_{level}.jpg"), dbg)

    # ========== DIAL: HoughCircles on blurred gray ==========
    for label, p1, p2, min_r, max_r in [
        ("strict", 100, 50, 50, 250), ("medium", 80, 40, 30, 300),
        ("loose", 60, 30, 20, 350), ("very_loose", 50, 20, 10, 400)]:
        dbg = img.copy()
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.0, minDist=30,
                                   param1=p1, param2=p2, minRadius=min_r, maxRadius=max_r)
        if circles is not None:
            for (cx, cy, r) in np.round(circles[0, :]).astype(int):
                cv2.circle(dbg, (cx, cy), r, (0, 255, 0), 2)
                cv2.circle(dbg, (cx, cy), 3, (0, 255, 0), -1)
                cv2.putText(dbg, f"r={r}", (cx + 3, cy - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
            cv2.putText(dbg, f"HoughCircles {label} p1={p1} p2={p2} r=[{min_r},{max_r}] found={len(circles[0])}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        else:
            cv2.putText(dbg, f"HoughCircles {label}  NONE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_dial_hough_{label}.jpg"), dbg)

    # ========== DIAL: HoughCircles on Canny edges ==========
    for label, cl, ch in [("edges_lo", 30, 120), ("edges_mid", 50, 150), ("edges_hi", 80, 200)]:
        dbg = img.copy()
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), cl, ch)
        circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, dp=1.0, minDist=30,
                                   param1=60, param2=30, minRadius=50, maxRadius=250)
        if circles is not None:
            for (cx, cy, r) in np.round(circles[0, :]).astype(int):
                cv2.circle(dbg, (cx, cy), r, (0, 255, 0), 2)
                cv2.circle(dbg, (cx, cy), 3, (0, 255, 0), -1)
            cv2.putText(dbg, f"Edge Hough {label} found={len(circles[0])}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        else:
            cv2.putText(dbg, f"Edge Hough {label}  NONE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_dial_edge_circle_{label}.jpg"), dbg)

    # ========== RED NEEDLE: 3 approaches to find hub center ==========
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1),
                              cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2))
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    red_dbg = img.copy()
    red_dbg[red_mask > 0] = (0, 255, 255)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        ct = max(contours, key=cv2.contourArea)
        M = cv2.moments(ct)
        if M["m00"] > 0:
            # ---- APPROACH A: raw centroid (WRONG — falls on shaft) ----
            cx_raw = int(M["m10"] / M["m00"]);  cy_raw = int(M["m01"] / M["m00"])
            cv2.circle(red_dbg, (cx_raw, cy_raw), 10, (0, 0, 255), 2)
            cv2.putText(red_dbg, f"A:centroid (shaft) ({cx_raw},{cy_raw})",
                        (cx_raw + 12, cy_raw - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # ---- APPROACH B: distance transform peak = thickest part = hub ----
            dist = cv2.distanceTransform(red_mask, cv2.DIST_L2, 5)
            _, max_val, _, max_loc = cv2.minMaxLoc(dist)
            cx_dt, cy_dt = max_loc; hub_r = int(dist[cy_dt, cx_dt])
            cv2.circle(red_dbg, (cx_dt, cy_dt), hub_r, (255, 0, 0), 2)
            cv2.circle(red_dbg, (cx_dt, cy_dt), 6, (255, 0, 0), -1)
            cv2.putText(red_dbg, f"B:dist-transform hub ({cx_dt},{cy_dt}) r={hub_r}",
                        (cx_dt + 12, cy_dt), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

            # ---- APPROACH C: minAreaRect — axis-aligned center of the hub ---
            rect = cv2.minAreaRect(ct)
            # rect = ((center_x, center_y), (width, height), angle)
            rcx, rcy = int(rect[0][0]), int(rect[0][1])
            box = cv2.boxPoints(rect); box = np.intp(box)
            cv2.drawContours(red_dbg, [box], 0, (0, 255, 0), 1)
            # The wider dimension is the hub; the narrower is the shaft.
            # The side of the rect opposite the tip is closer to the hub.
            rw, rh = rect[1]
            if rw > rh:
                shaft_dir = np.array([np.cos(np.radians(rect[2])), np.sin(np.radians(rect[2]))])
                hub_center = np.array([rcx, rcy]) + shaft_dir * rw / 2
            else:
                shaft_dir = np.array([-np.sin(np.radians(rect[2])), np.cos(np.radians(rect[2]))])
                hub_center = np.array([rcx, rcy]) + shaft_dir * rh / 2
            cv2.circle(red_dbg, (int(hub_center[0]), int(hub_center[1])), 8, (0, 255, 0), -1)
            cv2.putText(red_dbg, f"C:rect hub ({int(hub_center[0])},{int(hub_center[1])})",
                        (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    else:
        cv2.putText(red_dbg, "NO RED CONTOUR", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_red_needle.jpg"), red_dbg)

    # ========== HoughLinesP on edges ==========
    for label, cl, ch, thresh, min_len in [
        ("strict", 80, 200, 60, 30), ("medium", 60, 180, 40, 20), ("loose", 40, 150, 25, 15)]:
        dbg = img.copy()
        ed = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), cl, ch)
        lines = cv2.HoughLinesP(ed, 1, np.pi / 180, thresh, minLineLength=min_len, maxLineGap=10)
        if lines is not None:
            for seg in lines:
                x1, y1, x2, y2 = int(seg[0]), int(seg[1]), int(seg[2]), int(seg[3])
                angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                color = (255, 255, 0) if angle < 5 or angle > 175 else \
                        (0, 255, 0) if 80 < angle < 100 else (0, 0, 255)
                cv2.line(dbg, (x1, y1), (x2, y2), color, 1)
            cv2.putText(dbg, f"Lines {label} found={len(lines)} (cyan=horiz green=vert red=diag)",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        else:
            cv2.putText(dbg, f"Lines {label}  NONE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_lines_{label}.jpg"), dbg)

    # ========== Shi-Tomasi corners ==========
    for label, q, n in [("tight", 0.1, 200), ("mid", 0.05, 400), ("loose", 0.02, 600)]:
        dbg = img.copy()
        c = cv2.goodFeaturesToTrack(gray, maxCorners=n, qualityLevel=q, minDistance=5)
        if c is not None:
            for pt in np.intp(c):
                x, y = pt.ravel(); cv2.circle(dbg, (x, y), 2, (0, 255, 0), -1)
            cv2.putText(dbg, f"Shi-Tomasi {label} q={q} found={len(c)}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(dbg, f"Shi-Tomasi {label}  NONE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_corners_{label}.jpg"), dbg)

    # ========== Contour hierarchy (concentric features) ==========
    dbg = img.copy()
    ed = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, hierarchy = cv2.findContours(ed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is not None:
        h = hierarchy[0]
        for i, (ct, hi) in enumerate(zip(contours, h)):
            if cv2.contourArea(ct) > 500 and hi[3] >= 0:
                (cx, cy), r = cv2.minEnclosingCircle(ct)
                cv2.circle(dbg, (int(cx), int(cy)), int(r), (0, 255, 0), 1)
        cv2.putText(dbg, "Contour tree: nested (concentric) features in green",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_contour_tree.jpg"), dbg)

    # ========== DIAL: morphological close + open before threshold ==========
    for label, t, it in [("t180_close2", 180, 2), ("t200_close2", 200, 2), ("t220_close3", 220, 3)]:
        dbg = img.copy()
        _, mask = cv2.threshold(cv2.GaussianBlur(gray, (9, 9), 0), t, 255, cv2.THRESH_BINARY)
        se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, se, iterations=it),
                                cv2.MORPH_OPEN, se, iterations=1)
        dbg[mask > 0] = (dbg[mask > 0] * 0.5 + np.array([0, 255, 255]) * 0.5).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            ct = max(contours, key=cv2.contourArea)
            (cx, cy), r = cv2.minEnclosingCircle(ct); cx, cy, r = int(cx), int(cy), int(r)
            cv2.circle(dbg, (cx, cy), r, (0, 255, 0), 2)
            cv2.circle(dbg, (cx, cy), 4, (0, 255, 0), -1)
            cv2.putText(dbg, f"morph t={t} close={it}  r={r}  area={int(cv2.contourArea(ct))}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.imwrite(os.path.join(args.out_dir, f"{pfx}_dial_morph_{label}.jpg"), dbg)

    print(f"Generated {pfx}_*.jpg → {args.out_dir}")
    print("  dial_bright_[low,mid,high,vhigh], dial_hough_[strict..very_loose]")
    print("  dial_edge_circle_[edges_lo,edges_mid,edges_hi]")
    print("  red_needle (A:centroid B:dist-transform C:minAreaRect hub)")
    print("  lines_[strict,medium,loose], corners_[tight,mid,loose]")
    print("  contour_tree, dial_morph_[t180,t200,t220]")


if __name__ == "__main__":
    main()