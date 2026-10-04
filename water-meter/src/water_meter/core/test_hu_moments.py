#!/usr/bin/env python3
"""POC: Hu Moments + Grid Density vs current ensemble on water_meter_20260806_081316.jpg

Loads the single odo crop, extracts all 6 digit boxes, compares four matching
methods side-by-side, and prints a per-position report with scores.

Usage:
    .venv/bin/python scripts/water_meter/test_hu_moments.py
"""

from __future__ import annotations

import os, sys, re
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    PROC_DIR, TEMPLATE_DIR,
    DIGIT_SLOTS, REFERENCE_CROP_W, TEMPLATE_DIGITS, NPOS_WINDOW,
    get_digit_slots, refine_digit_slots,
    load_pos5_templates,
    match_with_ensemble,
)

# ── Config ──────────────────────────────────────────────────────────
CROP_FILE = "2026-08-06/odo_20260806_081316_n31.jpg"
GROUND_TRUTH = [0, 3, 5, 4, 1, 1]               # 035411
NPOS = 31

GRID_ROWS = 4
GRID_COLS = 4
BORDER_STRIP = 2
TOP_BOTTOM_MARGIN = 0.15

# ── Template loading ────────────────────────────────────────────────

def load_pos_static(template_dir: str, pos: int) -> dict[int, list[np.ndarray]]:
    bank: dict[int, list[np.ndarray]] = {d: [] for d in TEMPLATE_DIGITS}
    pat = re.compile(rf"pos{pos}_digit(\d+)(?:_\w+)?\.png")
    for fn in os.listdir(template_dir):
        m = pat.match(fn)
        if not m:
            continue
        d = int(m.group(1))
        img = cv2.imread(os.path.join(template_dir, fn), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            bank[d].append(img)
    return bank


# ── Structural preprocessing ────────────────────────────────────────

def preprocess_structural(box: np.ndarray) -> np.ndarray:
    """Binarize + border strip + morphology. Returns white-digit-on-black binary."""
    if len(box.shape) == 3:
        gray = cv2.cvtColor(box, cv2.COLOR_BGR2GRAY)
    else:
        gray = box.copy()
    gray = cv2.equalizeHist(gray)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = thresh.shape

    # Mask rolling-drum edge noise
    margin_h = max(1, int(h * TOP_BOTTOM_MARGIN))
    thresh[0:margin_h, :] = 0
    thresh[h - margin_h:h, :] = 0
    thresh[0:BORDER_STRIP, :] = 0
    thresh[h - BORDER_STRIP:h, :] = 0
    thresh[:, 0:BORDER_STRIP] = 0
    thresh[:, w - BORDER_STRIP:w] = 0

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    return thresh


# ── Hu Moments matching ─────────────────────────────────────────────

def extract_hu_moments(binary: np.ndarray) -> np.ndarray:
    moments = cv2.moments(binary)
    hu = cv2.HuMoments(moments).flatten()
    result = np.zeros(7, dtype=np.float64)
    for i in range(7):
        if hu[i] != 0:
            result[i] = -1.0 * np.sign(hu[i]) * np.log10(abs(hu[i]))
    return result


def match_hu(query_box: np.ndarray,
             templates: dict[int, list[np.ndarray]]) -> tuple[int | None, float, dict[int, float]]:
    if query_box is None or query_box.size == 0:
        return None, 0.0, {}

    q_bin = preprocess_structural(query_box)
    q_contours, _ = cv2.findContours(q_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    q_hu = extract_hu_moments(q_bin)

    scores: dict[int, float] = {}
    for digit, tmpl_list in templates.items():
        if not tmpl_list:
            continue
        best = -1.0
        for tmpl in tmpl_list:
            t_bin = preprocess_structural(tmpl)

            # contour-based matchShapes
            t_contours, _ = cv2.findContours(t_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if q_contours and t_contours:
                dist = cv2.matchShapes(q_contours[0], t_contours[0], cv2.CONTOURS_MATCH_I1, 0.0)
                sim1 = 1.0 / (1.0 + max(0.0, dist))
            else:
                sim1 = 0.0

            # I3 metric on Hu vectors
            t_hu = extract_hu_moments(t_bin)
            denom = np.abs(q_hu) + np.abs(t_hu)
            mask = denom > 1e-10
            if mask.any():
                i3 = np.sum(np.abs(1.0 / q_hu[mask] - 1.0 / t_hu[mask]))
                sim2 = 1.0 / (1.0 + i3)
            else:
                sim2 = 0.0

            combined = 0.5 * sim1 + 0.5 * sim2
            if combined > best:
                best = combined
        scores[digit] = best

    if not scores:
        return None, 0.0, {}
    best_d = max(scores, key=scores.get)
    return best_d, float(scores[best_d]), {d: float(s) for d, s in scores.items()}


# ── Grid Density matching ───────────────────────────────────────────

def grid_density(binary: np.ndarray, rows: int = GRID_ROWS, cols: int = GRID_COLS
                 ) -> np.ndarray:
    h, w = binary.shape
    zh, zw = h // rows, w // cols
    feat = np.zeros(rows * cols, dtype=np.float64)
    idx = 0
    for r in range(rows):
        y0 = r * zh
        y1 = (r + 1) * zh if r < rows - 1 else h
        for c in range(cols):
            x0 = c * zw
            x1 = (c + 1) * zw if c < cols - 1 else w
            zone = binary[y0:y1, x0:x1]
            feat[idx] = np.count_nonzero(zone) / max(1, zone.size)
            idx += 1
    return feat


def match_grid(query_box: np.ndarray,
               templates: dict[int, list[np.ndarray]]) -> tuple[int | None, float, dict[int, float]]:
    if query_box is None or query_box.size == 0:
        return None, 0.0, {}

    q_bin = preprocess_structural(query_box)
    q_vec = grid_density(q_bin)

    scores: dict[int, float] = {}
    for digit, tmpl_list in templates.items():
        if not tmpl_list:
            continue
        best = -1.0
        for tmpl in tmpl_list:
            t_bin = preprocess_structural(tmpl)
            t_vec = grid_density(t_bin)
            corr = np.corrcoef(q_vec, t_vec)[0, 1]
            if np.isnan(corr):
                corr = 0.0
            score = max(0.0, min(1.0, (corr + 1.0) / 2.0))
            if score > best:
                best = score
        scores[digit] = best

    if not scores:
        return None, 0.0, {}
    best_d = max(scores, key=scores.get)
    return best_d, float(scores[best_d]), {d: float(s) for d, s in scores.items()}


def match_hu_grid(query_box, templates, hu_w=0.60, grid_w=0.40):
    _, _, hu_s = match_hu(query_box, templates)
    _, _, gr_s = match_grid(query_box, templates)
    combined = {}
    for d in set(hu_s) | set(gr_s):
        combined[d] = hu_w * hu_s.get(d, 0) + grid_w * gr_s.get(d, 0)
    if not combined:
        return None, 0.0, {}
    best_d = max(combined, key=combined.get)
    return best_d, float(combined[best_d]), {"hu": hu_s.get(best_d, 0),
                                               "grid": gr_s.get(best_d, 0),
                                               "combined": float(combined[best_d])}


# ── pos5 helpers ────────────────────────────────────────────────────

def pos5_to_static(pos5_bank: dict, npos: int) -> dict[int, list[np.ndarray]]:
    bank: dict[int, list[np.ndarray]] = {d: [] for d in range(10)}
    if npos is None:
        return bank
    for (d, tn), img in pos5_bank.items():
        if min(abs(npos - tn), 100 - abs(npos - tn)) <= NPOS_WINDOW:
            bank[d].append(img)
    return bank


def match_pos5_raw(box: np.ndarray, npos: int,
                   bank: dict) -> tuple[int | None, float]:
    """Current pos5: raw grayscale TM_CCOEFF_NORMED."""
    if npos is None:
        return None, 0.0
    best_d, best_s = None, -1.0
    for (d, tn), t in bank.items():
        if min(abs(npos - tn), 100 - abs(npos - tn)) > NPOS_WINDOW:
            continue
        tr = cv2.resize(t, (box.shape[1], box.shape[0]),
                        interpolation=cv2.INTER_NEAREST) if box.shape != t.shape else t
        s = cv2.matchTemplate(box, tr, cv2.TM_CCOEFF_NORMED)[0][0]
        if s > best_s:
            best_s, best_d = s, d
    return best_d, best_s


# ── Main ────────────────────────────────────────────────────────────

def main():
    crop_path = os.path.join(PROC_DIR, CROP_FILE)
    if not os.path.exists(crop_path):
        print(f"ERROR: crop not found: {crop_path}")
        sys.exit(1)

    img = cv2.imread(crop_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    slots = get_digit_slots(w)
    slots = refine_digit_slots(gray, slots)

    # Load all templates
    pos5_bank = load_pos5_templates(TEMPLATE_DIR)
    static_banks = [load_pos_static(TEMPLATE_DIR, p) for p in range(5)]

    print()
    print("=" * 90)
    print("  POC: Hu Moments + Grid Density on water_meter_20260806_081316.jpg")
    print("  Ground truth: 035411  (odo_published=3541.131, npos=31)")
    print("=" * 90)
    print(f"  {'Pos':<6} {'GT':>3}  {'Current Ensemble':<22} {'Hu Moments':<22} {'Grid Density':<22} {'Hu+Grid':<22}")
    print(f"  {'─' * 83}")

    ok_cur = ok_hu = ok_grid = ok_comb = 0
    total = 6

    for pos in range(6):
        x0, x1 = slots[pos]
        box = gray[:, x0:x1]
        gt = GROUND_TRUTH[pos]

        if pos < 5:
            bank = static_banks[pos]
            ordered = [bank.get(d, [None])[0] if bank.get(d) else None for d in range(10)]

            d_cur, c_cur, _ = match_with_ensemble(box, ordered)
            d_hu,  c_hu,  _ = match_hu(box, bank)
            d_gr,  c_gr,  _ = match_grid(box, bank)
            d_cb,  c_cb,  _ = match_hu_grid(box, bank)
        else:
            bank = pos5_bank
            d_cur, c_cur = match_pos5_raw(box, NPOS, bank)
            static_bank = pos5_to_static(bank, NPOS)
            d_hu,  c_hu,  _ = match_hu(box, static_bank)
            d_gr,  c_gr,  _ = match_grid(box, static_bank)
            d_cb,  c_cb,  _ = match_hu_grid(box, static_bank)

        def fmt(d, c, gt):
            mark = "✓" if d == gt else "✗"
            return f"{d if d is not None else '?'}({c:.3f}) {mark}"

        cur_s = fmt(d_cur, c_cur, gt)
        hu_s  = fmt(d_hu,  c_hu,  gt)
        gr_s  = fmt(d_gr,  c_gr,  gt)
        cb_s  = fmt(d_cb,  c_cb,  gt)

        print(f"  pos{pos:<4} {gt:>3}  {cur_s:<22} {hu_s:<22} {gr_s:<22} {cb_s:<22}")

        if d_cur == gt: ok_cur  += 1
        if d_hu  == gt: ok_hu   += 1
        if d_gr  == gt: ok_grid += 1
        if d_cb  == gt: ok_comb += 1

    print(f"  {'─' * 83}")
    print(f"  {'TOTAL':<6} {'':>3}  {ok_cur}/{total} {'correct':<16} {ok_hu}/{total} {'correct':<16} {ok_grid}/{total} {'correct':<16} {ok_comb}/{total} correct")
    print()

    # Show per-digit score breakdown for a position that's interesting
    print("  ── Per-digit score breakdown for pos4 (expected=1) ──")
    x0, x1 = slots[4]
    box4 = gray[:, x0:x1]
    bank4 = static_banks[4]
    _, _, hu_all = match_hu(box4, bank4)
    _, _, gr_all = match_grid(box4, bank4)

    print(f"  {'Digit':<8} {'Hu Score':>10} {'Grid Score':>12}")
    print(f"  {'─' * 32}")
    for d in sorted(set(hu_all) | set(gr_all)):
        hs = hu_all.get(d, 0)
        gs = gr_all.get(d, 0)
        marker = " ← GT" if d == 1 else ""
        print(f"  {d:<8} {hs:>10.4f} {gs:>12.4f}{marker}")

    # Show pos5 breakdown
    print()
    print("  ── Per-digit score breakdown for pos5 (expected=1) ──")
    x0, x1 = slots[5]
    box5 = gray[:, x0:x1]
    sb5 = pos5_to_static(pos5_bank, NPOS)
    _, _, hu5_all = match_hu(box5, sb5)
    _, _, gr5_all = match_grid(box5, sb5)

    print(f"  {'Digit':<8} {'Hu Score':>10} {'Grid Score':>12}")
    print(f"  {'─' * 32}")
    for d in sorted(set(hu5_all) | set(gr5_all)):
        hs = hu5_all.get(d, 0)
        gs = gr5_all.get(d, 0)
        marker = " ← GT" if d == 1 else ""
        print(f"  {d:<8} {hs:>10.4f} {gs:>12.4f}{marker}")

    print()


if __name__ == "__main__":
    main()