#!/usr/bin/env python3
"""Dump horizon row grayscale values to understand the segment-box pattern."""
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

    print(f"\n{'='*70}")
    print(f"Image: {label}  hub=({hub_x},{hub_y})")
    print(f"Horizon row grayscale: min={int(hrow.min())} max={int(hrow.max())}")
    print()

    # Print LEFT side: every pixel from hub_x down to 0, mark transitions
    print("--- LEFT side (hub → 0) ---")
    last_category = "BRIGHT" if hrow[hub_x] > 90 else ("DARK" if hrow[hub_x] < 60 else "MID")
    for x in range(hub_x, max(hub_x - 200, 0), -1):
        v = int(hrow[x])
        cat = "BRIGHT" if v > 90 else ("DARK" if v < 60 else "MID")
        marker = " <--" if cat != last_category else ""
        if marker or x % 50 == 0:
            print(f"  x={x:4d} val={v:3d} {cat}{marker}")
        last_category = cat

    print()
    print("--- RIGHT side (hub → w) ---")
    last_category = "BRIGHT" if hrow[hub_x] > 90 else ("DARK" if hrow[hub_x] < 60 else "MID")
    for x in range(hub_x, min(hub_x + 200, w)):
        v = int(hrow[x])
        cat = "BRIGHT" if v > 90 else ("DARK" if v < 60 else "MID")
        marker = " <--" if cat != last_category else ""
        if marker or x % 50 == 0:
            print(f"  x={x:4d} val={v:3d} {cat}{marker}")
        last_category = cat