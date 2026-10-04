#!/usr/bin/env python3
"""Extract water meter reading using hub-based detection + digit template matching.

NEW METHOD — integrates the pipeline from explore_hub_dial.py and explore_odo.py:

 1. Hub (blue dot) via distance-transform on closed red mask
 2. Dial circle radius = hub_x - left_edge (bright mask scan)
 3. Left marker blob → horizon angle = needle angle
 4. Odometer crop via hub + dial_r proportions
 5. 6 digit slots via hardcoded structural positions (54px each)
 6. Template matching per digit (cv2.TM_CCOEFF_NORMED)
 7. Needle validates position-5 digit

Does NOT modify any existing script.

Output:
    ~/pictures/water_meter/readings_hub.csv      (per-frame readings)
    ~/pictures/water_meter/meter_state_hub.json   (persistent state)
    ~/pictures/water_meter/odometer_crops/        (archived crops)
    ~/pictures/water_meter/templates/             (digit templates)

Usage:
    .venv/bin/python scripts/water_meter/extract_reading.py
    .venv/bin/python scripts/water_meter/extract_reading.py --image <path> --debug
    .venv/bin/python scripts/water_meter/extract_reading.py --baseline 3533 --label 0,3,5,3,3,0
"""

import argparse, csv, json, os, re, sys
from datetime import datetime

import cv2
import numpy as np

# ---------------------------------------------------------------------------
IMAGE_DIR    = os.path.expanduser("~/pictures/water_meter")
CSV_PATH     = os.path.join(IMAGE_DIR, "readings_hub.csv")
STATE_PATH   = os.path.join(IMAGE_DIR, "meter_state_hub.json")
ARCHIVE_DIR  = os.path.join(IMAGE_DIR, "odometer_crops")
TEMPLATE_DIR = os.path.join(IMAGE_DIR, "templates")
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

RED_LOWER_1  = np.array([0, 100, 50]);  RED_UPPER_1  = np.array([10, 255, 255])
RED_LOWER_2  = np.array([170, 100, 50]); RED_UPPER_2  = np.array([180, 255, 255])
BRIGHT_THRESH  = 200
MIN_BRIGHT_FRAC = 0.30

NUM_DIGITS = 6
REFERENCE_CROP_W = 558
DIGIT_SLOTS = [(24, 78), (119, 173), (197, 251), (289, 343), (368, 422), (432, 508)]
# ---------------------------------------------------------------------------


def detect_hub_and_dial(img):
    """Return dict with hub, dial, marker info."""
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
        return None
    bright_idx = np.where(bright[scan_y, :].flatten() > 0)[0]
    left_edge = int(bright_idx[0])
    dial_r = hub_x - left_edge

    # marker blob
    hub_exclude = np.zeros_like(red_raw)
    cv2.circle(hub_exclude, (hub_x, hub_y), hub_r * 3, 255, -1)
    red_no_hub = cv2.bitwise_and(red_raw, cv2.bitwise_not(hub_exclude))
    n_labels, _, stats, centroids = cv2.connectedComponentsWithStats(red_no_hub)
    marker_cx = marker_cy = None
    marker_bbox = None
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
                    sx = int(stats[lbl, cv2.CC_STAT_LEFT])
                    sy = int(stats[lbl, cv2.CC_STAT_TOP])
                    sw = int(stats[lbl, cv2.CC_STAT_WIDTH])
                    sh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
                    # Make bounding box square, centered on centroid
                    side = max(sw, sh)
                    bx = cx - side // 2
                    by = cy - side // 2
                    marker_bbox = (bx, by, side, side)
    angle_deg = 0.0
    if marker_cx is not None:
        angle_deg = np.degrees(np.arctan2(marker_cy - hub_y, marker_cx - hub_x))

    # Enforce minimum dial radius: marker is near the left edge; radius must be >= distance to marker + margin.
    if marker_cx is not None:
        min_dial_r = (hub_x - marker_cx) + 30
        dial_r = max(dial_r, min_dial_r)

    # Needle zone: red_raw pixels in annulus between inner ellipse and outer circle.
    # The inner ellipse MUST enclose the marker blob's square bounding box so that
    # its red pixels don't bleed into the needle detection zone.
    if marker_bbox is not None:
        bx, by, bw, bh = marker_bbox
        h_dist = max(abs(bx - hub_x), abs(bx + bw - hub_x))
        v_dist = max(abs(by - hub_y), abs(by + bh - hub_y))
        inner_rx = int(max(h_dist * 1.15, dial_r * 0.45))
        inner_ry = int(max(v_dist * 1.15, dial_r * 0.40))
    else:
        inner_rx = int(dial_r * 0.90)
        inner_ry = int(dial_r * 0.75)
    needle_zone_pixels = []
    for py in range(h):
        for px in range(w):
            if red_raw[py, px] > 0:
                dx = px - hub_x
                dy = py - hub_y
                r2 = dx*dx + dy*dy
                if r2 <= dial_r * dial_r:
                    e2 = (dx*dx)/(inner_rx*inner_rx) + (dy*dy)/(inner_ry*inner_ry)
                    if e2 > 1.0:
                        needle_zone_pixels.append((px, py))

    # Compute needle angle from FARTHEST red pixel in annulus (needle tip).
    # The centroid is biased when the needle and marker are on opposite sides.
    needle_deg = None
    if len(needle_zone_pixels) >= 3:
        farthest = max(needle_zone_pixels,
                       key=lambda p: (p[0] - hub_x)**2 + (p[1] - hub_y)**2)
        tip_x, tip_y = farthest
        needle_deg = np.degrees(np.arctan2(tip_y - hub_y, tip_x - hub_x))

    return {"hub_x": hub_x, "hub_y": hub_y, "hub_r": hub_r,
            "dial_r": dial_r, "left_edge": left_edge,
            "marker_cx": marker_cx, "marker_cy": marker_cy,
            "angle_deg": angle_deg,
            "needle_deg": needle_deg,
            "needle_zone_pixels": len(needle_zone_pixels)}


def crop_odometer(img, lm):
    """Crop odometer region using hub-based proportions."""
    hi, wi = img.shape[:2]
    dr = lm["dial_r"]
    odo_w = int(dr * 1.40); odo_h = int(dr * 0.32)
    x1 = max(0, lm["hub_x"] - int(dr * 0.78))
    y1 = max(0, lm["hub_y"] - int(dr * 0.64))
    x2 = min(wi, x1 + odo_w); y2 = min(hi, y1 + odo_h)
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def get_digit_slots(crop_w):
    """Scale digit slot positions to the current crop width."""
    scale = crop_w / REFERENCE_CROP_W
    return [(max(0, int(s * scale)), min(crop_w, int(e * scale)))
            for s, e in DIGIT_SLOTS]


# ── template bank ──

def load_template_bank():
    bank = {}
    for fn in os.listdir(TEMPLATE_DIR):
        m = re.match(r"pos(\d)_digit(\d+)\.png", fn)
        if m:
            pos, d = int(m.group(1)), int(m.group(2))
            t = cv2.imread(os.path.join(TEMPLATE_DIR, fn), cv2.IMREAD_GRAYSCALE)
            if t is not None:
                bank[(pos, d)] = t
    return bank


def save_template(pos, val, gray_img):
    cv2.imwrite(os.path.join(TEMPLATE_DIR, f"pos{pos}_digit{val}.png"), gray_img)


def match_digit(box_gray, pos, bank):
    candidates = {d: t for (p, d), t in bank.items() if p == pos}
    if not candidates:
        return None, 0.0
    best_d, best_s = None, -1.0
    for d, t in candidates.items():
        if box_gray.shape != t.shape:
            t = cv2.resize(t, (box_gray.shape[1], box_gray.shape[0]),
                           interpolation=cv2.INTER_CUBIC)
        s = cv2.matchTemplate(box_gray, t, cv2.TM_CCOEFF_NORMED)[0][0]
        if s > best_s:
            best_s, best_d = s, d
    return (best_d, best_s)


# ── state persistence ──

def load_state():
    defaults = {"digits": [None] * NUM_DIGITS, "last_ts": None,
                "last_reading": None, "last_angle": None,
                "accumulated_revs": 0.0, "baseline_units": 0}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                d = json.load(f)
            for k in defaults:
                if k in d:
                    defaults[k] = d[k]
        except:
            pass
    return defaults


def save_state(s):
    with open(STATE_PATH, "w") as f:
        json.dump(s, f, indent=2, default=str)


def append_csv(ts_str, reading):
    exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["timestamp", "reading"])
        w.writerow([ts_str, f"{reading:.3f}"])


def archive_crop(img, prefix="odo_hub"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(os.path.join(ARCHIVE_DIR, f"{prefix}_{ts}.jpg"), img)


# ── main ──

def main():
    ap = argparse.ArgumentParser(description="Extract water meter reading (hub-based method)")
    ap.add_argument("--image", help="Path to a specific image (default: latest.jpg)")
    ap.add_argument("--debug", action="store_true", help="Save debug crops")
    ap.add_argument("--baseline", type=float, help="Baseline integer reading for seeding state")
    ap.add_argument("--label", help="Comma-separated 6 digits for baseline image, e.g. 0,3,5,3,3,0")
    ap.add_argument("--reset", action="store_true", help="Reset persistent state")
    args = ap.parse_args()

    if args.reset and os.path.exists(STATE_PATH):
        os.remove(STATE_PATH)

    state = load_state()
    now = datetime.now()
    img_path = args.image or os.path.join(IMAGE_DIR, "latest.jpg")

    if not os.path.exists(img_path):
        print(f"ERROR: {img_path} not found", file=sys.stderr)
        sys.exit(1)

    img = cv2.imread(img_path)
    if img is None:
        print(f"ERROR: cannot read {img_path}", file=sys.stderr)
        sys.exit(1)

    # Parse capture timestamp from filename (water_meter_YYYYMMDD_HHMMSS.jpg)
    fname = os.path.basename(img_path)
    m = re.match(r'water_meter_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', fname)
    if m:
        img_ts = f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"
    else:
        img_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # ── baseline seeding ──
    if args.baseline is not None and args.label is not None:
        digits = [int(x.strip()) for x in args.label.split(",")]
        state["digits"] = digits
        state["last_reading"] = float(int(args.baseline))
        state["last_ts"] = now.isoformat()
        state["baseline_units"] = int(args.baseline)
        save_state(state)
        print(f"BASELINE: {int(args.baseline)} digits={digits}")

        lm = detect_hub_and_dial(img)
        if lm is None:
            print("ERROR: hub/dial detection failed", file=sys.stderr)
            sys.exit(1)
        odo = crop_odometer(img, lm)
        if odo is None:
            print("ERROR: odo crop failed", file=sys.stderr)
            sys.exit(1)
        gray = cv2.cvtColor(odo, cv2.COLOR_BGR2GRAY)
        slots = get_digit_slots(gray.shape[1])
        for pos in range(NUM_DIGITS):
            x0, x1 = slots[pos]
            x0, x1 = max(0, x0), min(gray.shape[1], x1)
            tp = os.path.join(TEMPLATE_DIR, f"pos{pos}_digit{digits[pos]}.png")
            if not os.path.exists(tp):
                save_template(pos, digits[pos], gray[:, x0:x1])
                print(f"  template: pos{pos}_digit{digits[pos]}.png")
        return

    # ── hub + dial detection ──
    lm = detect_hub_and_dial(img)
    if lm is None:
        print("ERROR: hub/dial detection failed", file=sys.stderr)
        sys.exit(1)

    print(f"[{now:%Y-%m-%d %H:%M:%S}] {os.path.basename(img_path)}")
    print(f"  hub=({lm['hub_x']},{lm['hub_y']})  hub_r={lm['hub_r']}  dial_r={lm['dial_r']}")

    # needle angle → fractional reading
    # Use annulus needle_deg (cyan pixels) if available; fall back to marker angle
    needle_deg = lm.get("needle_deg")
    if needle_deg is None:
        needle_deg = lm["angle_deg"]  # fallback to marker (always ~178°)
    nz_pixels = lm.get("needle_zone_pixels", 0)
    if needle_deg < 0:
        needle_deg += 360.0
    # Dial convention: 0° = UP (.000), 90° = RIGHT (.025), 180° = DOWN (.050), 270° = LEFT (.075)
    # arctan2 gives 0° = RIGHT, so add 90° offset and mod 360
    needle_dec = ((needle_deg + 90.0) % 360.0 / 360.0) * 0.1

    prev_angle = state.get("last_angle")
    if prev_angle is not None:
        disp = needle_deg - prev_angle
        if disp < -180:
            disp += 360.0
        elif disp > 180:
            disp -= 360.0
        state["accumulated_revs"] = state.get("accumulated_revs", 0.0) + disp / 360.0
    pos5_from_needle = (state.get("baseline_units", 0) + int(state["accumulated_revs"])) % 10

    print(f"  needle={needle_deg:.1f}°  dec={needle_dec:.3f}  nz_pix={nz_pixels}  revs={state['accumulated_revs']:.2f}  pos5_pred={pos5_from_needle}")

    # odometer crop
    odo = crop_odometer(img, lm)
    if odo is None:
        print("ERROR: odo crop failed", file=sys.stderr)
        sys.exit(1)
    archive_crop(odo)
    if args.debug:
        cv2.imwrite(os.path.join(IMAGE_DIR, "debug_hub_odometer.jpg"), odo)

    gray = cv2.cvtColor(odo, cv2.COLOR_BGR2GRAY)
    slots = get_digit_slots(gray.shape[1])
    bank = load_template_bank()
    digits = [None] * NUM_DIGITS
    last_digits = state["digits"]

    for pos in range(NUM_DIGITS):
        x0, x1 = slots[pos]
        x0, x1 = max(0, x0), min(gray.shape[1], x1)
        box = gray[:, x0:x1]
        matched, conf = match_digit(box, pos, bank)

        ld = last_digits[pos] if last_digits and last_digits[pos] is not None else None
        if matched is not None and ld is not None:
            if matched < ld and not (ld == 9 and matched == 0):
                matched = ld
        if matched is None:
            matched = ld if ld is not None else 0
        if pos == 5 and ld is not None and pos5_from_needle != ld:
            matched = pos5_from_needle

        digits[pos] = matched
        print(f"  digit[{pos}]={matched}  conf={conf:.3f}")

        # auto-save high-confidence templates
        if conf > 0.85 and matched is not None and (pos, matched) not in bank:
            save_template(pos, matched, box.copy())
            bank[(pos, matched)] = box.copy()
        if pos == 5 and matched is not None and (pos, matched) not in bank:
            save_template(pos, matched, box.copy())
            bank[(pos, matched)] = box.copy()

    # compute reading
    white = sum(digits[i] * (10 ** (NUM_DIGITS - 2 - i))
                for i in range(NUM_DIGITS - 1) if digits[i] is not None)
    black = digits[5] if digits[5] is not None else 0
    reading = float(white) + black * 0.1 + needle_dec

    if state["last_reading"] is not None and reading < state["last_reading"] - 0.1:
        print(f"  WARN: drop ({reading:.3f} < {state['last_reading']:.3f}) — held")
        reading = state["last_reading"]

    print(f"  READING: {reading:.3f}")
    state["digits"] = digits
    state["last_ts"] = now.isoformat()
    state["last_reading"] = reading
    state["last_angle"] = needle_deg
    save_state(state)
    append_csv(img_ts, reading)


if __name__ == "__main__":
    main()