#!/usr/bin/env python3
"""Extract pos5 digit templates at every 10th npos position.

Phase 1 — Extract n00 seeds per revolution:
    Scans all odo crops chronologically, tracks needle crossings (n99→n00).
    Saves the best n00 image from each revolution as:
        templates/pos5_UNKNOWN_n00_R<rev>.png
    You rename to:  pos5_digit<N>_n00.png  (N = 0-9)

Phase 2 — Fill n10, n20, ..., n90:
    Uses n00 seeds + needle-crossing tracking to digit ALL revolutions.
    For each revolution, saves the BEST crop at each target npos
    (n00, n10, n20, n30, n40, n50, n60, n70, n80, n90).
    Skip n40-n60 (transition zone where 2 digits visible).
    Result: ~70 templates total (7 per digit × 10 digits).

Usage:
    .venv/bin/python scripts/water_meter/extract_n00_seeds.py              # Phase 1
    .venv/bin/python scripts/water_meter/extract_n00_seeds.py --propagate  # Phase 2
    .venv/bin/python scripts/water_meter/extract_n00_seeds.py --find-missing  # after renaming
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("extract_n00_seeds")

IMAGE_DIR = os.path.expanduser("~/pictures/water_meter")
PROC_DIR = os.path.join(IMAGE_DIR, "proc")
TEMPLATE_DIR = os.path.join(IMAGE_DIR, "templates")

NUM_DIGITS = 6
POS5_INDEX = 5
REFERENCE_CROP_W = 558
POS5_REF_START = 432
POS5_REF_END = 508

# Target npos positions to sample (every 10th, skip transition zone)
TARGET_NPOS = [0, 10, 20, 30, 70, 80, 90]
NPOS_TOLERANCE = 4  # Accept within ±4 of target (e.g. n06-n14 for n10)


def get_scaled_pos5(crop_w: int) -> Tuple[int, int]:
    s = crop_w / REFERENCE_CROP_W
    x0 = max(0, int(POS5_REF_START * s))
    x1 = min(crop_w, int(POS5_REF_END * s))
    return (x0, x1)


def extract_pos5_box(odo_path: str) -> Optional[np.ndarray]:
    img = cv2.imread(odo_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x0, x1 = get_scaled_pos5(w)
    return gray[:, x0:x1]


def npos_from_filename(fname: str) -> Optional[int]:
    m = re.search(r'_n(\d{2})\.jpg$', fname)
    if m:
        return int(m.group(1))
    return None


def npos_distance(a: int, b: int) -> int:
    """Circular distance on npos (0-99)."""
    return min(abs(a - b), 100 - abs(a - b))


# ---------------------------------------------------------------------------
# Phase 1: extract one n00 per revolution
# ---------------------------------------------------------------------------

def phase1_extract_n00(args: argparse.Namespace) -> None:
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(PROC_DIR, "odo_*.jpg")))
    log.info("Scanning %d odo crops for crossings...", len(files))

    rev_count = 0
    in_n00 = False
    best_for_rev: Optional[Tuple[int, np.ndarray, str]] = None
    saved = 0

    for fp in files:
        fname = os.path.basename(fp)
        npos = npos_from_filename(fname)
        if npos is None:
            continue
        is_n00 = npos <= 2 or npos >= 98

        if not in_n00 and is_n00:
            in_n00 = True
            best_for_rev = None

        if in_n00 and not is_n00:
            in_n00 = False
            if best_for_rev is not None:
                n, box, src = best_for_rev
                out = f"pos5_UNKNOWN_n00_R{rev_count+1:03d}.png"
                p = os.path.join(TEMPLATE_DIR, out)
                if not os.path.exists(p):
                    cv2.imwrite(p, box)
                    saved += 1
                    if args.debug:
                        log.debug("  R%03d: %s <- %s (n%d)", rev_count+1, out, src, n)
                rev_count += 1

        if in_n00:
            dist = min(npos, 100 - npos)
            if best_for_rev is None or dist < min(best_for_rev[0], 100 - best_for_rev[0]):
                box = extract_pos5_box(fp)
                if box is not None:
                    best_for_rev = (npos, box, fname)

    if in_n00 and best_for_rev is not None:
        n, box, src = best_for_rev
        out = f"pos5_UNKNOWN_n00_R{rev_count+1:03d}.png"
        p = os.path.join(TEMPLATE_DIR, out)
        if not os.path.exists(p):
            cv2.imwrite(p, box)
            saved += 1

    print(f"\nSaved {saved} n00 candidates from {rev_count} revolutions")
    print("Rename to pos5_digit<N>_n00.png, then run --propagate")


# ---------------------------------------------------------------------------
# Phase 2: fill n10-n90 using n00 seeds + geometry tracking
# ---------------------------------------------------------------------------

def load_n00_templates() -> Dict[int, np.ndarray]:
    templates = {}
    for fn in sorted(os.listdir(TEMPLATE_DIR)):
        m = re.match(r"pos5_digit(\d+)_n00\.png", fn)
        if not m:
            continue
        d = int(m.group(1))
        img = cv2.imread(os.path.join(TEMPLATE_DIR, fn), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            templates[d] = img
    return templates


def propagate(args: argparse.Namespace) -> int:
    """Walk all odo crops, track digit via needle crossings, save best per target npos."""
    seeds = load_n00_templates()
    if not seeds:
        print("ERROR: No pos5_digit<N>_n00.png found", file=sys.stderr)
        sys.exit(1)

    log.info("Loaded %d n00 seeds: %s", len(seeds), sorted(seeds.keys()))
    files = sorted(glob.glob(os.path.join(PROC_DIR, "odo_*.jpg")))
    log.info("Processing %d crops...", len(files))

    # Track what we need to save per (digit, target_npos)
    # best[(digit, target)] = (npos, box_image, fname, dist_from_target)
    best: Dict[Tuple[int, int], Tuple[int, np.ndarray, str, int]] = {}

    current_digit: Optional[int] = None
    last_npos: Optional[int] = None

    for fp in files:
        fname = os.path.basename(fp)
        npos = npos_from_filename(fname)
        if npos is None:
            continue

        # Track needle crossing (geometry only, no matching needed)
        if last_npos is not None and last_npos > 90 and npos < 10:
            if current_digit is not None:
                current_digit = (current_digit + 1) % 10
        last_npos = npos

        box = extract_pos5_box(fp)
        if box is None:
            continue

        # Bootstrap current_digit from n00 match only when at n00
        # Use binarized matching for robustness against lighting
        if npos <= 2 or npos >= 98:
            # Binarize query
            q_blur = cv2.GaussianBlur(box, (3, 3), 0)
            q_bin = cv2.adaptiveThreshold(q_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 15, 4)
            for digit, tmpl in seeds.items():
                t_blur = cv2.GaussianBlur(tmpl, (3, 3), 0)
                t_bin = cv2.adaptiveThreshold(t_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 15, 4)
                if q_bin.shape != t_bin.shape:
                    t_bin = cv2.resize(t_bin, (q_bin.shape[1], q_bin.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)
                score = cv2.matchTemplate(q_bin, t_bin, cv2.TM_CCOEFF_NORMED)[0][0]
                if score >= 0.60:
                    current_digit = digit
                    if args.debug:
                        log.debug("  BOOTSTRAP: digit=%d at n%s (score=%.2f)",
                                  digit, fname[-6:-4], score)
                    break

        if current_digit is None:
            continue

        # Check if this npos is near any target we need
        for target in TARGET_NPOS:
            dist = npos_distance(npos, target)
            if dist <= NPOS_TOLERANCE:
                key = (current_digit, target)
                if key not in best or dist < best[key][3]:
                    best[key] = (npos, box, fname, dist)

    # Save results
    saved = 0
    existing = 0
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

    for (digit, target), (npos, box, src, dist) in sorted(best.items()):
        out = f"pos5_digit{digit}_n{target:02d}.png"
        path = os.path.join(TEMPLATE_DIR, out)
        if os.path.exists(path):
            existing += 1
            continue
        cv2.imwrite(path, box)
        saved += 1
        if args.debug:
            log.debug("  %s <- %s (n%d, dist=%d)", out, src, npos, dist)

    print(f"\nPropagation: {saved} new + {existing} existing = {saved+existing} total")
    print(f"Saved n00 seeds preserved: {len(seeds)}")
    total = len(glob.glob(os.path.join(TEMPLATE_DIR, "pos5_digit*_n*.png")))
    print(f"Total pos5 templates: {total}")
    return saved


# ---------------------------------------------------------------------------
# Find missing n00 seeds
# ---------------------------------------------------------------------------

def find_missing(args: argparse.Namespace) -> None:
    """Use n00 seeds + crossings to predict digit for unlabelled revolutions."""
    seeds = load_n00_templates()
    if not seeds:
        print("ERROR: No pos5_digit<N>_n00.png found", file=sys.stderr)
        sys.exit(1)

    known = set(seeds.keys())
    missing = sorted(set(range(10)) - known)
    log.info("Missing: %s", missing)
    if not missing:
        print("All digits 0-9 labelled")
        return

    files = sorted(glob.glob(os.path.join(PROC_DIR, "odo_*.jpg")))
    rev_info: Dict[int, dict] = {}
    rev = 0
    in_n00 = False
    best_rev: Optional[Tuple[int, np.ndarray, str]] = None
    current_digit: Optional[int] = None
    last_npos: Optional[int] = None

    for fp in files:
        fname = os.path.basename(fp)
        npos = npos_from_filename(fname)
        if npos is None:
            continue
        is_n00 = npos <= 2 or npos >= 98

        if last_npos is not None and last_npos > 90 and npos < 10:
            if current_digit is not None:
                current_digit = (current_digit + 1) % 10
        last_npos = npos

        if not in_n00 and is_n00:
            in_n00 = True
            best_rev = None

        if in_n00 and not is_n00:
            in_n00 = False
            if best_rev is not None:
                rev += 1
                rev_info[rev] = {'npos': best_rev[0], 'box': best_rev[1],
                                 'fname': best_rev[2], 'digit': current_digit}

        if in_n00:
            dist = min(npos, 100 - npos)
            if best_rev is None or dist < min(best_rev[0], 100 - best_rev[0]):
                box = extract_pos5_box(fp)
                if box is not None:
                    best_rev = (npos, box, fname)

        # Match at n00 to set digit
        if is_n00:
            box = extract_pos5_box(fp)
            if box is not None:
                for d, t in seeds.items():
                    tt = t
                    if box.shape != t.shape:
                        tt = cv2.resize(t, (box.shape[1], box.shape[0]),
                                        interpolation=cv2.INTER_CUBIC)
                    s = cv2.matchTemplate(box, tt, cv2.TM_CCOEFF_NORMED)[0][0]
                    if s >= 0.70:
                        current_digit = d
                        break

    if in_n00 and best_rev is not None:
        rev += 1
        rev_info[rev] = {'npos': best_rev[0], 'box': best_rev[1],
                         'fname': best_rev[2], 'digit': current_digit}

    found = 0
    for md in missing:
        for r, info in sorted(rev_info.items()):
            if info.get('digit') == md:
                out = f"pos5_UNKNOWN_n00_R{r:03d}.png"
                p = os.path.join(TEMPLATE_DIR, out)
                if not os.path.exists(p):
                    cv2.imwrite(p, info['box'])
                    found += 1
                    print(f"  {out} <- {info['fname']} (digit {md})")
                break

    if found == 0 and missing:
        # Fallback: save all unlabeled revs
        for r, info in sorted(rev_info.items()):
            if info.get('digit') is not None:
                continue
            out = f"pos5_UNKNOWN_n00_R{r:03d}.png"
            p = os.path.join(TEMPLATE_DIR, out)
            if not os.path.exists(p):
                cv2.imwrite(p, info['box'])
                found += 1
                print(f"  {out} <- {info['fname']} (unlabeled)")

    print(f"\nSaved {found} candidates")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="n00 seed extraction & propagation")
    p.add_argument("--propagate", action="store_true",
                    help="Fill n10-n90 using seeds + geometry tracking")
    p.add_argument("--find-missing", action="store_true",
                    help="Find missing n00 seeds")
    p.add_argument("--debug", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%H:%M:%S")

    if args.propagate:
        propagate(args)
    elif args.find_missing:
        find_missing(args)
    else:
        phase1_extract_n00(args)


if __name__ == "__main__":
    main()