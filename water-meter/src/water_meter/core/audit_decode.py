#!/usr/bin/env python3
"""Audit decode_meter.py on a 10% cross-section of water meter images.

Outputs:
  ~/pictures/water_meter/debug/     — debug overlay images
  ~/pictures/water_meter/audit_report.html  — clickable HTML report
"""

import glob, json, math, os, re, sys, time
from datetime import datetime
from html import escape

import cv2
import numpy as np

# Add project root to path for importing sibling modules
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

IMAGE_DIR = os.path.expanduser("~/pictures/water_meter")
DEBUG_DIR = os.path.join(IMAGE_DIR, "debug")
TEMPLATE_DIR = os.path.join(IMAGE_DIR, "templates")

# Reuse constants and functions from decode_meter.py
from water_meter.core.decode_meter import (
    detect_hub_and_dial, crop_odometer, draw_dial_scan, get_digit_slots,
    load_template_bank, match_digit,
)


def mean_brightness(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return int(gray.mean())


def std_brightness(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return int(gray.std())


def main():
    # Determine input directory and report name from env or CLI
    import argparse
    ap = argparse.ArgumentParser(description="Audit decode_meter.py on a set of water meter images")
    ap.add_argument("--input-dir", default=IMAGE_DIR, help=f"Directory with water_meter_*.jpg (default: {IMAGE_DIR})")
    ap.add_argument("--report", default="audit_report.html", help="Output report filename (default: audit_report.html)")
    ap.add_argument("--csv", nargs="?", const=None, help="Output CSV filename (default: same name as report with .csv)")
    ap.add_argument("--sample-pct", type=float, default=10.0, help="Sample percentage (default: 10, use 100 for all)")
    args = ap.parse_args()

    input_dir = args.input_dir
    report_name = args.report
    sample_pct = args.sample_pct / 100.0

    os.makedirs(DEBUG_DIR, exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, "water_meter_*.jpg")))
    if not files:
        print(f"No water_meter_*.jpg files found in {input_dir}"); sys.exit(1)

    total = len(files)
    sample_size = max(2, int(total * sample_pct))

    # Build sample indices
    step = max(1, (total - 2) // (sample_size - 2))
    indices = [0]
    for i in range(step, total - 1, step):
        if len(indices) < sample_size - 1:
            indices.append(i)
    indices.append(total - 1)
    indices.sort()

    print(f"Total images: {total}")
    print(f"Sample size: {len(indices)} (step={step})")
    print(f"First index: 0  ({os.path.basename(files[0])})")
    print(f"Last index:  {total-1}  ({os.path.basename(files[-1])})")

    bank = load_template_bank()

    rows = []
    ok = fail = 0

    for idx in indices:
        path = files[idx]
        fname = os.path.basename(path)
        print(f"\n[{idx}/{total}] {fname}")

        # Parse timestamp from filename
        m = re.match(r'water_meter_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', fname)
        ts_tag = f"{m.group(1)}{m.group(2)}{m.group(3)}_{m.group(4)}{m.group(5)}{m.group(6)}" if m else "unknown"

        img = cv2.imread(path)
        if img is None:
            rows.append((fname, idx, "ERROR", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""))
            fail += 1
            continue

        h, w = img.shape[:2]
        brightness = mean_brightness(img)
        contrast = std_brightness(img)

        lm = detect_hub_and_dial(img, debug=False)
        if lm is None:
            rows.append((fname, idx, brightness, contrast, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""))
            fail += 1
            continue

        # Metrics
        hub_x, hub_y = lm["hub_x"], lm["hub_y"]
        dial_r = lm["dial_r"]
        left_edge = lm["left_edge"]
        right_edge = lm["right_edge"]
        inner_rx = lm["inner_rx"]
        inner_ry = lm["inner_ry"]
        nz_pix = len(lm["needle_zone_pixels"])
        marker_cx = lm["marker_cx"] if lm["marker_cx"] is not None else -1
        marker_cy = lm["marker_cy"] if lm["marker_cy"] is not None else -1
        marker_bbox = lm["marker_bbox"]
        if marker_bbox is not None:
            mbx, mby, mbw, mbh = marker_bbox
            marker_extent = max(mbw, mbh)
        else:
            marker_extent = -1

        needle_deg = lm["needle_deg"]
        if needle_deg is not None:
            needle_str = f"{needle_deg:.2f}"
            npos = int(((needle_deg + 90) % 360) / 360 * 100) % 100
            npos_str = f"{npos:02d}"
        else:
            needle_str = "None"
            npos_str = ""

        # Horizon angle
        ha = lm["horizon_deg"]
        ha_str = f"{ha:.2f}" if ha is not None else "None"

        # Horizon row analysis (mean brightness of row)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        hrow = blurred[hub_y, :]
        hrow_mean = int(hrow.mean())
        hrow_std = int(hrow.std())

        # Odometry
        odo = crop_odometer(img, lm)
        if odo is not None:
            odo_h, odo_w = odo.shape[:2]
            odo_brightness = int(cv2.cvtColor(odo, cv2.COLOR_BGR2GRAY).mean())
            odo_contrast = int(cv2.cvtColor(odo, cv2.COLOR_BGR2GRAY).std())
        else:
            odo_h = odo_w = odo_brightness = odo_contrast = -1

        # Digit matching
        digits_str = ""
        if odo is not None:
            gray_odo = cv2.cvtColor(odo, cv2.COLOR_BGR2GRAY)
            slots = get_digit_slots(gray_odo.shape[1])
            for pos in range(6):
                x0, x1 = slots[pos]
                box = gray_odo[:, x0:x1]
                matched, conf = match_digit(box, pos, bank)
                d = str(matched) if matched is not None else "?"
                digits_str += d

        # Reading — no longer tracked per-frame; see decode_odo.py for digit decode
        reading = -1

        # Save debug image
        dbg_path = os.path.join(DEBUG_DIR, f"audit_{ts_tag}.jpg")
        dbg_rel = f"debug/audit_{ts_tag}.jpg"
        draw_dial_scan(img, lm, dbg_path)

        rows.append((
            fname, idx, brightness, contrast,
            hub_x, hub_y, dial_r,
            left_edge, right_edge,
            inner_rx, inner_ry,
            nz_pix, marker_cx, marker_cy, marker_extent,
            needle_str, npos_str, ha_str,
            hrow_mean, hrow_std,
            odo_w, odo_h, odo_brightness, odo_contrast,
            digits_str,
            f"{reading:.3f}" if reading > 0 else "N/A",
            dbg_rel,
            ts_tag,
        ))
        ok += 1

    # Write HTML report
    report_path = os.path.join(IMAGE_DIR, report_name)
    with open(report_path, "w") as f:
        f.write("""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body { font-family: monospace; font-size: 12px; margin: 20px; }
table { border-collapse: collapse; }
th, td { border: 1px solid #999; padding: 3px 6px; white-space: nowrap; }
th { background: #def; position: sticky; top: 0; }
tr:nth-child(even) { background: #f5f5f5; }
tr:hover { background: #ffd; }
a { text-decoration: none; color: #06c; }
a:hover { text-decoration: underline; }
.ok { color: #080; }
.fail { color: #c00; }
td { text-align: right; }
td.left { text-align: left; }
</style></head><body>
<h1>Water Meter Audit — 10% Sample</h1>
<p>Total: """ + str(total) + """ images, Sample: """ + str(len(rows)) + """ images</p>
<table>
<tr>
<th>Image</th><th>Idx</th><th>Bright</th><th>Contrast</th>
<th>HX</th><th>HY</th><th>dR</th>
<th>L</th><th>R</th>
<th>iRx</th><th>iRy</th>
<th>NZp</th><th>MX</th><th>MY</th><th>ME</th>
<th>Nd°</th><th>Np</th><th>HA°</th>
<th>HRm</th><th>HRs</th>
<th>oW</th><th>oH</th><th>oBr</th><th>oCn</th>
<th>Dig</th><th>Read</th>
<th>Debug</th>
</tr>
""")

        for r in rows:
            fname, idx, bright, contrast = r[0], r[1], r[2], r[3]
            hub_x, hub_y, dial_r = r[4], r[5], r[6]
            left_edge, right_edge = r[7], r[8]
            inner_rx, inner_ry = r[9], r[10]
            nz_pix = r[11]
            marker_cx, marker_cy, marker_extent = r[12], r[13], r[14]
            needle_str, npos_str, ha_str = r[15], r[16], r[17]
            hrow_mean, hrow_std = r[18], r[19]
            odo_w, odo_h, odo_bright, odo_contrast = r[20], r[21], r[22], r[23]
            digits_str = r[24]
            reading_str = r[25]
            dbg_rel = r[26]
            ts_tag = r[27]

            # Type-check each value for safe HTML display
            def v(x):
                if x is None or x == "" or x == -1 or x == "None":
                    return ""
                return str(x)

            # Clickable link to original image if served somewhere,
            # at least link to debug image
            debug_link = f'<a href="{escape(dbg_rel)}">debug</a>'
            orig_link = f'<a href="../images/{escape(ts_tag)}.jpg">img</a>' if False else ""

            f.write(f"""<tr>
<td class="left">{escape(fname)}</td>
<td>{idx}</td>
<td>{v(bright)}</td><td>{v(contrast)}</td>
<td>{v(hub_x)}</td><td>{v(hub_y)}</td><td>{v(dial_r)}</td>
<td>{v(left_edge)}</td><td>{v(right_edge)}</td>
<td>{v(inner_rx)}</td><td>{v(inner_ry)}</td>
<td>{v(nz_pix)}</td>
<td>{v(marker_cx)}</td><td>{v(marker_cy)}</td><td>{v(marker_extent)}</td>
<td class="left">{v(needle_str)}</td><td>{v(npos_str)}</td><td>{v(ha_str)}</td>
<td>{v(hrow_mean)}</td><td>{v(hrow_std)}</td>
<td>{v(odo_w)}</td><td>{v(odo_h)}</td><td>{v(odo_bright)}</td><td>{v(odo_contrast)}</td>
<td class="left">{v(digits_str)}</td>
<td class="left">{v(reading_str)}</td>
<td class="left">{debug_link}</td>
</tr>
""")

        f.write("</table>\n")
        f.write(f"<p>OK: {ok}  FAIL: {fail}</p>\n")
        f.write("</body></html>\n")

    print(f"\nDone: OK={ok}  FAIL={fail}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()