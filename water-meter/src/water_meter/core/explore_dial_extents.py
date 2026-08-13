#!/usr/bin/env python3
"""Measure vertical vs horizontal dial face extents from the bright mask."""
import cv2, numpy as np, os, sys

# Add project root so imports work from any subdirectory
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

img = cv2.imread(os.path.expanduser("~/pictures/water_meter/latest.jpg"))
h, w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (9, 9), 0)

# Hub
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
red_raw = cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 100, 50]), np.array([10, 255, 255])),
                         cv2.inRange(hsv, np.array([170, 100, 50]), np.array([180, 255, 255])))
red = cv2.morphologyEx(red_raw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
dist = cv2.distanceTransform(red, cv2.DIST_L2, 5)
_, _, _, max_loc = cv2.minMaxLoc(dist)
hub_x, hub_y = max_loc

# Bright mask
_, bright = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)

# Left/right edges from segment boxes
from water_meter.core.decode_meter import find_segment_box_edges
horizon_row = blurred[hub_y, :]
left_edge, right_edge = find_segment_box_edges(horizon_row, hub_x, w)
dial_r = hub_x - left_edge
print(f"Hub: ({hub_x}, {hub_y})")
print(f"Left edge: {left_edge}  Right edge: {right_edge}")
print(f"dial_r (horizontal): {dial_r}")
print(f"odo crop box: x={hub_x - int(0.78*dial_r)} y={hub_y - int(0.64*dial_r)} "
      f"w={int(1.40*dial_r)} h={int(0.32*dial_r)}")

# Scan vertical extents across the dial face area
top_vals = []
bot_vals = []
for cx in range(max(0, hub_x - dial_r), min(w, hub_x + dial_r)):
    col = bright[:, cx]
    bp = np.where(col > 0)[0]
    if len(bp) > 0:
        top_vals.append(bp[0])
        bot_vals.append(bp[-1])

if top_vals and bot_vals:
    top_all = min(top_vals)
    bot_all = max(bot_vals)
    print(f"\nBright mask across dial face (x={hub_x-dial_r} to {hub_x+dial_r}):")
    print(f"  topmost bright = {top_all}  (hub_y - top = {hub_y - top_all})")
    print(f"  bottommost bright = {bot_all}  (bot - hub_y = {bot_all - hub_y})")
    print(f"  vertical half-extent ≈ {(bot_all - top_all) // 2}")
    print(f"\n  Horizontal half-extent (dial_r) = {dial_r}")
    print(f"  Ratio horizontal:vertical = {dial_r}:{(bot_all - top_all)//2}")