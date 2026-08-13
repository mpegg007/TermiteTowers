#!/usr/bin/env python3
"""Analyze horizon row to find outer segment-box edges with minimum streak lengths."""
import cv2, numpy as np

for label, path in [
    ("0720_054724", "/home/mpegg-adm/pictures/water_meter/water_meter_20260720_054724.jpg"),
    ("latest",      "/home/mpegg-adm/pictures/water_meter/latest.jpg"),
]:
    img = cv2.imread(path)
    if img is None: print(f"SKIP {label}"); continue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    red_raw = cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 100, 50]), np.array([10, 255, 255])),
                             cv2.inRange(hsv, np.array([170, 100, 50]), np.array([180, 255, 255])))
    red = cv2.morphologyEx(red_raw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    dist = cv2.distanceTransform(red, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(dist)
    hub_y, hub_x = max_loc[1], max_loc[0]
    hrow = blurred[hub_y, :]
    w = len(hrow)

    def outer_edge(row, start, step):
        """Find outer edge of segment box using minimum streak lengths.
        Pattern: dial bright(≥15) → dark gap(≥8) → segment box bright(≥15) → outer edge dark"""
        x, MIN_DARK, MIN_BRIGHT = start, 8, 15
        # Skip initial bright dial
        while 0 <= x < w and int(row[x]) > 90:
            x += step
        # Require dark gap of at least MIN_DARK pixels
        for _ in range(MIN_DARK):
            if not (0 <= x < w) or int(row[x]) >= 60:
                return None
            x += step
        # Require segment box of at least MIN_BRIGHT pixels
        for _ in range(MIN_BRIGHT):
            if not (0 <= x < w) or int(row[x]) <= 90:
                return None
            x += step
        # Find first dark pixel after segment box
        while 0 <= x < w:
            if int(row[x]) < 60:
                return x - step  # pixel just before this dark one
            x += step
        return None

    lo = outer_edge(hrow, hub_x, -1)
    ro = outer_edge(hrow, hub_x, +1)
    print(f"\n{label} hub=({hub_x},{hub_y})")
    if lo is not None:
        print(f"  LEFT outer={lo} dist={hub_x-lo}")
    else:
        print(f"  LEFT NOT FOUND")
    if ro is not None:
        print(f"  RIGHT outer={ro} dist={ro-hub_x}")
    else:
        print(f"  RIGHT NOT FOUND")
    if lo is not None and ro is not None:
        r = min(hub_x-lo, ro-hub_x)
        print(f"  dial_r = min({hub_x-lo}, {ro-hub_x}) = {r}")