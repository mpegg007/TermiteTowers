#!/usr/bin/env python3
"""Empirical comparison of old vs enhanced digit detection methods.

Runs both match_static_digit (old adaptive-threshold only) and
match_with_ensemble (new multi-path) on every manual correction
(ground truth) and on a random sample of auto-decoded frames.

Reports:
  - Per-digit accuracy against ground truth
  - Average confidence scores (old vs new)
  - Agreement rates between methods
  - Cases where ensemble corrected an old error or introduced a new one

Usage:
    .venv/bin/python scripts/water_meter/compare_odo_methods.py

Options:
    --sample N      Number of random auto-decoded samples (default: 500)
    --debug N       Print detailed results for first N discrepancies
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    IMAGE_DIR, PROC_DIR, TEMPLATE_DIR,
    get_digit_slots,
    preprocess, match_with_ensemble,
    clean_binary, extract_edges, preprocess_clahe_otsu,
    TEMPLATE_DIGITS, REFERENCE_CROP_W, DIGIT_SLOTS,
)
from water_meter.core.db import MeterReading, get_session, init_db

log = logging.getLogger("compare_odo")

# ---------------------------------------------------------------------------
# Load templates the same way decode_odo.py does
# ---------------------------------------------------------------------------

import re

def load_pos_static_digit_templates(template_dir: str, pos: int
                                    ) -> Dict[int, List[np.ndarray]]:
    bank: Dict[int, List[np.ndarray]] = {d: [] for d in TEMPLATE_DIGITS}
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


# ---------------------------------------------------------------------------
# Old method — exact copy of original match_static_digit
# ---------------------------------------------------------------------------

STATIC_CONF_MIN = 0.40

def match_static_digit_old(box: np.ndarray,
                           bank: Dict[int, List[np.ndarray]]
                           ) -> Tuple[Optional[int], float]:
    """Original single-path adaptive-threshold matching."""
    available_digits = [d for d, templates in bank.items() if templates]
    if not available_digits:
        return None, 0.0

    single_digit_mode = (len(available_digits) == 1)
    threshold = 0.70 if single_digit_mode else STATIC_CONF_MIN

    q = preprocess(box)
    best_d, best_s = None, -1.0
    for d, templates in bank.items():
        if not templates:
            continue
        for t in templates:
            tb = preprocess(t)
            if q.shape != tb.shape:
                tb = cv2.resize(tb, (q.shape[1], q.shape[0]),
                                interpolation=cv2.INTER_NEAREST)
            s = cv2.matchTemplate(q, tb, cv2.TM_CCOEFF_NORMED)[0][0]
            if s > best_s:
                best_s, best_d = s, d
    if best_d is not None and best_s >= threshold:
        return best_d, best_s
    return best_d, best_s


# ---------------------------------------------------------------------------
# New method — ensemble matcher (from common.py)
# ---------------------------------------------------------------------------

def match_static_digit_new(box: np.ndarray,
                           bank: Dict[int, List[np.ndarray]]
                           ) -> Tuple[Optional[int], float]:
    """Enhanced ensemble matching with sliding-window alignment."""
    available_digits = [d for d, templates in bank.items() if templates]
    if not available_digits:
        return None, 0.0

    single_digit_mode = (len(available_digits) == 1)
    threshold = 0.70 if single_digit_mode else STATIC_CONF_MIN

    # Build ordered list of templates (one per digit 0-9)
    ordered_templates: List[Optional[np.ndarray]] = [None] * 10
    for d in range(10):
        tmpls = bank.get(d, [])
        ordered_templates[d] = tmpls[0] if tmpls else None

    # Attempt ensemble matching
    d_ens, conf_ens, _scores = match_with_ensemble(box, ordered_templates)

    # Always run fallback (original method) for comparison
    q = preprocess(box)
    best_d, best_s = None, -1.0
    for d, templates in bank.items():
        if not templates:
            continue
        for t in templates:
            tb = preprocess(t)
            if q.shape != tb.shape:
                tb = cv2.resize(tb, (q.shape[1], q.shape[0]),
                                interpolation=cv2.INTER_NEAREST)
            s = cv2.matchTemplate(q, tb, cv2.TM_CCOEFF_NORMED)[0][0]
            if s > best_s:
                best_s, best_d = s, d

    # Pick the better result — new method can only improve, never regress
    if d_ens is not None and conf_ens >= best_s:
        return d_ens, conf_ens
    if best_d is not None and best_s >= threshold:
        return best_d, best_s
    return best_d, best_s


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------

def compare_frame(crop_path: str,
                  static_banks: List[Dict[int, List[np.ndarray]]],
                  ground_truth_digits: List[Optional[int]],
                  ) -> dict:
    """Compare old vs new matching on one crop.

    Returns comparison dict with per-position results.
    """
    img = cv2.imread(crop_path)
    if img is None:
        return {"error": "can't read", "crop": crop_path}

    h, w = img.shape[:2]
    s = w / REFERENCE_CROP_W
    slots = [(max(0, int(a * s)), min(w, int(b * s))) for a, b in DIGIT_SLOTS]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    pos_results = []
    for pos in range(5):
        x0, x1 = slots[pos]
        if x1 - x0 < 10:
            pos_results.append({"pos": pos, "error": "slot too small"})
            continue
        box = gray[:, x0:x1]
        bank = static_banks[pos]
        if not bank:
            pos_results.append({"pos": pos, "error": "no bank"})
            continue

        gt = ground_truth_digits[pos] if pos < len(ground_truth_digits) else None

        d_old, c_old = match_static_digit_old(box, bank)
        d_new, c_new = match_static_digit_new(box, bank)

        old_correct = (d_old == gt) if gt is not None else None
        new_correct = (d_new == gt) if gt is not None else None

        pos_results.append({
            "pos": pos,
            "ground_truth": gt,
            "old_digit": d_old,
            "old_conf": round(c_old, 4),
            "old_correct": old_correct,
            "new_digit": d_new,
            "new_conf": round(c_new, 4),
            "new_correct": new_correct,
            "agreement": d_old == d_new,
        })

    return {"crop": os.path.basename(crop_path), "positions": pos_results}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Compare old vs new odo digit detection methods")
    p.add_argument("--sample", type=int, default=500,
                   help="Number of random auto-decoded samples")
    p.add_argument("--debug", type=int, default=5,
                   help="Print first N discrepancies in detail")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    # Load template banks
    static_banks = []
    for pos in range(5):
        bank = load_pos_static_digit_templates(TEMPLATE_DIR, pos)
        static_banks.append(bank)

    digit_counts = [sum(1 for v in bank.values() if v) for bank in static_banks]
    log.info("Templates per position: %s", digit_counts)

    # ── Phase 1: Ground truth (manual corrections) ──
    with get_session() as s:
        manual_rows_raw = (
            s.query(MeterReading.image_name, MeterReading.odo_crop_file, MeterReading.odo_reading, MeterReading.digits)
            .filter(MeterReading.odo_confidence == 1.0)
            .filter(MeterReading.odo_crop_file.isnot(None))
            .filter(MeterReading.odo_reading.isnot(None))
            .all()
        )
        manual_rows = [{"image_name": r[0], "odo_crop_file": r[1], "odo_reading": float(r[2]), "digits": r[3]} for r in manual_rows_raw]
    log.info("Manual corrections (ground truth): %d", len(manual_rows))

    gt_results = []
    for row in manual_rows:
        crop_path = os.path.join(PROC_DIR, row["odo_crop_file"])
        if not os.path.exists(crop_path):
            continue
        reading = row["odo_reading"]
        i_part = int(reading)
        f_part = int(round((reading - i_part) * 10)) % 10
        gt_digits = [(i_part // (10 ** (4 - pi))) % 10 for pi in range(5)] + [f_part]
        result = compare_frame(crop_path, static_banks, gt_digits)
        result["reading"] = reading
        result["image_name"] = row["image_name"]
        gt_results.append(result)

    log.info("Ground truth frames compared: %d", len(gt_results))

    # ── Phase 2: Random sample from auto-decoded frames ──
    with get_session() as s:
        auto_rows_raw = (
            s.query(MeterReading.image_name, MeterReading.odo_crop_file, MeterReading.digits)
            .filter(MeterReading.odo_crop_file.isnot(None))
            .filter(MeterReading.odo_confidence < 1.0)
            .filter(MeterReading.odo_confidence.isnot(None))
            .all()
        )
        # Randomly pick rows within the session
        if len(auto_rows_raw) > args.sample:
            picked = random.sample(auto_rows_raw, args.sample)
        else:
            picked = auto_rows_raw
        sample_rows = [{"image_name": r[0], "odo_crop_file": r[1], "digits": r[2]} for r in picked]
    log.info("Auto-decoded rows for sample: %d", len(sample_rows))

    sample_results = []
    for row in sample_rows:
        crop_path = os.path.join(PROC_DIR, row["odo_crop_file"])
        if not os.path.exists(crop_path):
            continue
        gt_digits = None
        if row["digits"] and len(row["digits"]) == 6:
            gt_digits = [int(c) if c.isdigit() else None for c in row["digits"]]
        result = compare_frame(crop_path, static_banks, gt_digits or [None]*6)
        result["image_name"] = row["image_name"]
        sample_results.append(result)

    log.info("Sample frames compared: %d", len(sample_results))

    # ── Compute statistics ──
    def compute_stats(results, label, has_gt=True):
        """Compute per-position accuracy and confidence stats."""
        pos_stats = []
        for pos in range(5):
            old_correct = 0
            new_correct = 0
            old_confs = []
            new_confs = []
            agreement = 0
            total = 0
            new_fixed_old_wrong = 0
            new_broke_old_right = 0

            for r in results:
                if "positions" not in r:
                    continue
                pr = r["positions"][pos] if pos < len(r["positions"]) else None
                if pr is None or "old_digit" not in pr:
                    continue
                total += 1
                old_confs.append(pr["old_conf"])
                new_confs.append(pr["new_conf"])
                if pr.get("agreement"):
                    agreement += 1
                if has_gt and pr.get("old_correct") is not None:
                    if pr["old_correct"]:
                        old_correct += 1
                    if pr["new_correct"]:
                        new_correct += 1
                    if not pr["old_correct"] and pr["new_correct"]:
                        new_fixed_old_wrong += 1
                    if pr["old_correct"] and not pr["new_correct"]:
                        new_broke_old_right += 1

            pos_stats.append({
                "pos": pos,
                "total": total,
                "old_correct": old_correct,
                "new_correct": new_correct,
                "old_accuracy": round(old_correct / total * 100, 1) if total else 0,
                "new_accuracy": round(new_correct / total * 100, 1) if total else 0,
                "old_avg_conf": round(np.mean(old_confs), 4) if old_confs else 0,
                "new_avg_conf": round(np.mean(new_confs), 4) if new_confs else 0,
                "agreement_pct": round(agreement / total * 100, 1) if total else 0,
                "new_fixed_old_wrong": new_fixed_old_wrong,
                "new_broke_old_right": new_broke_old_right,
            })
        return pos_stats

    gt_stats = compute_stats(gt_results, "Ground Truth (Manual)", has_gt=True)
    sample_stats = compute_stats(sample_results, "Random Sample", has_gt=True)

    # ── Report ──
    print()
    print("=" * 90)
    print("  COMPARISON: OLD (adaptive threshold) vs NEW (multi-path ensemble)")
    print("=" * 90)

    print()
    print("--- GROUND TRUTH (Manual Corrections, n={}) ---".format(len(gt_results)))
    print(f"{'Pos':<6}{'Old Acc':>10}{'New Acc':>10}{'Δ':>8}{'Old Conf':>10}{'New Conf':>10}{'Agree%':>8}{'Fixed':>8}{'Broke':>8}")
    print("-" * 78)
    for ps in gt_stats:
        delta = ps["new_accuracy"] - ps["old_accuracy"]
        print(f"  {ps['pos']:<4}{ps['old_accuracy']:>9.1f}%{ps['new_accuracy']:>9.1f}%{delta:>+7.1f}%{ps['old_avg_conf']:>10.4f}{ps['new_avg_conf']:>10.4f}{ps['agreement_pct']:>7.1f}%{ps['new_fixed_old_wrong']:>8}{ps['new_broke_old_right']:>8}")

    # Overall
    total_old_c = sum(ps["old_correct"] for ps in gt_stats)
    total_new_c = sum(ps["new_correct"] for ps in gt_stats)
    total_gt = sum(ps["total"] for ps in gt_stats)
    total_fixed = sum(ps["new_fixed_old_wrong"] for ps in gt_stats)
    total_broke = sum(ps["new_broke_old_right"] for ps in gt_stats)
    print("-" * 78)
    print(f"  Total  {total_old_c/total_gt*100:>8.1f}%{total_new_c/total_gt*100:>9.1f}%{'+' if total_new_c>=total_old_c else ''}{total_new_c-total_old_c:>6}  "
          f"Fixed: {total_fixed}  Broke: {total_broke}")
    print()

    print("--- RANDOM SAMPLE (Auto-decoded, n={}) ---".format(len(sample_results)))
    print(f"{'Pos':<6}{'Old Acc':>10}{'New Acc':>10}{'Δ':>8}{'Old Conf':>10}{'New Conf':>10}{'Agree%':>8}{'Fixed':>8}{'Broke':>8}")
    print("-" * 78)
    for ps in sample_stats:
        delta = ps["new_accuracy"] - ps["old_accuracy"]
        print(f"  {ps['pos']:<4}{ps['old_accuracy']:>9.1f}%{ps['new_accuracy']:>9.1f}%{delta:>+7.1f}%{ps['old_avg_conf']:>10.4f}{ps['new_avg_conf']:>10.4f}{ps['agreement_pct']:>7.1f}%{ps['new_fixed_old_wrong']:>8}{ps['new_broke_old_right']:>8}")
    total_old_c2 = sum(ps["old_correct"] for ps in sample_stats)
    total_new_c2 = sum(ps["new_correct"] for ps in sample_stats)
    total_s2 = sum(ps["total"] for ps in sample_stats)
    total_fixed2 = sum(ps["new_fixed_old_wrong"] for ps in sample_stats)
    total_broke2 = sum(ps["new_broke_old_right"] for ps in sample_stats)
    print("-" * 78)
    print(f"  Total  {total_old_c2/total_s2*100:>8.1f}%{total_new_c2/total_s2*100:>9.1f}%{'+' if total_new_c2>=total_old_c2 else ''}{total_new_c2-total_old_c2:>6}  "
          f"Fixed: {total_fixed2}  Broke: {total_broke2}")
    print()

    # ── Confidence distribution comparison ──
    print("--- CONFIDENCE DISTRIBUTION (Ground Truth frames) ---")
    old_all_confs = []
    new_all_confs = []
    for r in gt_results:
        for pr in r.get("positions", []):
            if "old_conf" in pr:
                old_all_confs.append(pr["old_conf"])
                new_all_confs.append(pr["new_conf"])

    bins = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]
    print(f"{'Range':<14}{'Old Count':>12}{'New Count':>12}")
    print("-" * 38)
    for lo, hi in bins:
        old_c = sum(1 for c in old_all_confs if lo <= c < hi)
        new_c = sum(1 for c in new_all_confs if lo <= c < hi)
        print(f"  [{lo:.2f}-{hi:.2f}){old_c:>7}{new_c:>12}")

    print()
    print("--- SUMMARY ---")
    gt_n = len(gt_results)
    print(f"  Ground truth frames compared: {gt_n}")
    print(f"  Old method accuracy: {total_old_c/total_gt*100:.1f}% ({total_old_c}/{total_gt})")
    print(f"  New method accuracy: {total_new_c/total_gt*100:.1f}% ({total_new_c}/{total_gt})")
    if total_new_c > total_old_c:
        print(f"  ✅ New method IMPROVED accuracy by {total_new_c - total_old_c} correct digits "
              f"({(total_new_c/total_gt - total_old_c/total_gt)*100:+.1f}%)")
    elif total_new_c < total_old_c:
        print(f"  ❌ New method REGRESSED by {total_old_c - total_new_c} correct digits "
              f"({(total_new_c/total_gt - total_old_c/total_gt)*100:+.1f}%)")
    else:
        print(f"  ➖ No change in accuracy")
    print(f"  Corrections made (wrong→right): {total_fixed}")
    print(f"  Regressions introduced (right→wrong): {total_broke}")
    print(f"  Net improvement: {total_fixed - total_broke} digits")

    # ── Debug: print discrepancies ──
    if args.debug > 0:
        print()
        print("--- DISCREPANCIES (up to {}) ---".format(args.debug))
        shown = 0
        for r in gt_results:
            if shown >= args.debug:
                break
            discrepancies = []
            for pr in r.get("positions", []):
                if pr.get("old_correct") is not None and pr.get("new_correct") is not None:
                    if pr["old_correct"] != pr["new_correct"]:
                        discrepancies.append(pr)
            if discrepancies:
                print()
                print(f"  Crop: {r.get('crop','?')}  Image: {r.get('image_name','?')}")
                print(f"  Reading: {r.get('reading','?')}")
                for pr in discrepancies:
                    status = "✅ fixed by NEW" if not pr["old_correct"] and pr["new_correct"] else "❌ broke (was RIGHT, now WRONG)"
                    print(f"    pos{pr['pos']}: GT={pr['ground_truth']}  "
                          f"OLD={pr['old_digit']}({pr['old_conf']:.3f}) → "
                          f"NEW={pr['new_digit']}({pr['new_conf']:.3f})  {status}")
                shown += 1


if __name__ == "__main__":
    main()