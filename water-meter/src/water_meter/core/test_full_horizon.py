#!/usr/bin/env python3
"""Dump full horizon row (all 1280 px) grouped into dark/mid/bright runs."""
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
    print(f"Image: {label}  hub=({hub_x},{hub_y})  w={w}")
    print(f"Horizon row: min={int(hrow.min())} max={int(hrow.max())}")

    # Find runs of dark (<60) and bright (>90)
    cur_state = "DARK" if hrow[0] < 60 else ("BRIGHT" if hrow[0] > 90 else "MID")
    run_start = 0
    runs = []
    for x in range(1, w):
        v = hrow[x]
        state = "DARK" if v < 60 else ("BRIGHT" if v > 90 else "MID")
        if state != cur_state:
            if x - run_start >= 3:  # only report runs >= 3px
                avg = int(np.mean(hrow[run_start:x]))
                runs.append((run_start, x - 1, cur_state, avg))
            cur_state = state
            run_start = x
    # Last run
    if w - run_start >= 3:
        avg = int(np.mean(hrow[run_start:w]))
        runs.append((run_start, w - 1, cur_state, avg))

    print(f"\nRuns (≥3px):")
    print(f"{'x_from':>5} {'x_to':>5} {'len':>5} {'state':>6} {'avg_val':>7}")
    print(f"{'-'*35}")
    for xf, xt, st, avg in runs:
        length = xt - xf + 1
        marker = " *** HUB" if xf <= hub_x <= xt else ""
        print(f"{xf:>5} {xt:>5} {length:>5} {st:>6} {avg:>7}{marker}")