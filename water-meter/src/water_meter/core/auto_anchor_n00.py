#!/usr/bin/env python3
"""Store pos5 drum-digit readings at n00 frames for integer verification.

At n00 positions (npos 98-2), the drum digit is fully settled. This script
template-matches the pos5 digit and stores ONLY the digit in DB notes.
It does NOT track integer independently — that's the needle tracker's job.

calc_needle_readings.py will use these anchors to verify that the
needle-crossing-tracked integer has the correct ones digit. If not,
the integer gets snapped to the nearest value that matches.

Usage:
    .venv/bin/python scripts/water_meter/auto_anchor_n00.py           # scan all
    .venv/bin/python scripts/water_meter/auto_anchor_n00.py --dry-run  # preview
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    PROC_DIR, TEMPLATE_DIR,
    npos_from_fname,
    get_digit_slots,
    load_pos5_templates,
    DIGIT_SLOTS, REFERENCE_CROP_W, POS5_INDEX,
    TEMPLATE_DIGITS,
)
from water_meter.core.db import MeterReading, init_db, get_session

log = logging.getLogger("auto_anchor_n00")

N00_NPOS_SET = {98, 99, 0, 1, 2}
POS5_CONF_THRESHOLD = 0.55


def binarize(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 15, 4)


def _match(query: np.ndarray, template: np.ndarray) -> float:
    if query.shape != template.shape:
        template = cv2.resize(template, (query.shape[1], query.shape[0]),
                              interpolation=cv2.INTER_NEAREST)
    return float(cv2.matchTemplate(query, template, cv2.TM_CCOEFF_NORMED)[0][0])


def match_digit_ensemble(box: np.ndarray,
                         bank: Dict[int, List[np.ndarray]]
                         ) -> Tuple[Optional[int], float, float]:
    """Match a digit box against per-digit template bank.

    Returns (best_digit, best_score, second_best_score).
    """
    scores: Dict[int, float] = {}
    for digit, tmpls in bank.items():
        best = -1.0
        for t in tmpls:
            s_raw = _match(box, t)
            s_bin = _match(binarize(box), binarize(t))
            best = max(best, s_raw, s_bin)
        if best > -1.0:
            scores[digit] = best

    if not scores:
        return None, 0.0, 0.0

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_digit, best_score = sorted_scores[0]
    second_best = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
    return best_digit, best_score, second_best


def get_scaled_slots(crop_w: int) -> List[Tuple[int, int]]:
    s = crop_w / REFERENCE_CROP_W
    return [(max(0, int(a * s)), min(crop_w, int(b * s))) for a, b in DIGIT_SLOTS]


def find_n00_digits(dry_run: bool = False) -> int:
    """Scan all n00-region frames, match pos5 digit via templates.

    Stores ONLY the pos5_digit in DB notes — no integer tracking.
    """
    init_db()

    # Load only n00 pos5 templates
    pos5_bank: Dict[int, List[np.ndarray]] = {d: [] for d in TEMPLATE_DIGITS}
    for (digit, npos), template in load_pos5_templates(TEMPLATE_DIR).items():
        if npos in N00_NPOS_SET:
            pos5_bank[digit].append(template)

    total_files = sum(len(v) for v in pos5_bank.values())
    n_digits = sum(1 for v in pos5_bank.values() if v)
    log.info("Pos5 n00 templates: %d digits (%d files)", n_digits, total_files)
    if not any(pos5_bank.values()):
        log.warning("No pos5 n00 templates — run extract_n00_seeds.py first")
        return 0

    # Collect n00 crops with DB info
    n00_entries = []
    with get_session() as s:
        rows = (
            s.query(MeterReading.image_name, MeterReading.odo_crop_file,
                    MeterReading.capture_ts, MeterReading.npos, MeterReading.notes)
            .filter(MeterReading.status == "OK")
            .filter(MeterReading.odo_crop_file.isnot(None))
            .filter(MeterReading.capture_ts.isnot(None))
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )
        for row in rows:
            fname = os.path.basename(row.odo_crop_file) if row.odo_crop_file else ""
            npos = npos_from_fname(fname)
            if npos is None or npos not in N00_NPOS_SET:
                continue
            n00_entries.append({
                "image_name": row.image_name,
                "crop_fname": fname,
                "capture_ts": row.capture_ts,
                "npos": npos,
                "notes": row.notes,
            })

    log.info("Found %d n00-region frames", len(n00_entries))

    all_crops = {os.path.basename(f): f for f in
                 glob.glob(os.path.join(PROC_DIR, "**", "odo_*.jpg"), recursive=True)}

    written = 0
    scanned = 0
    results: List[dict] = []

    for entry in n00_entries:
        fname = entry["crop_fname"]
        fp = all_crops.get(fname)
        if fp is None:
            continue

        scanned += 1

        # Extract pos5 slot
        img = cv2.imread(fp)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, w = gray.shape[:2]
        slots = get_scaled_slots(w)
        x0, x1 = slots[POS5_INDEX]
        if x1 - x0 < 10 or x1 > w:
            continue
        box5 = gray[:, x0:x1]

        d5, d5_conf, d5_second = match_digit_ensemble(box5, pos5_bank)
        if d5 is None or d5_conf < POS5_CONF_THRESHOLD:
            continue

        gap = d5_conf - d5_second

        anchor_data = {
            "n00_anchor": {
                "pos5_digit": d5,
                "pos5_confidence": round(d5_conf, 4),
                "pos5_gap": round(gap, 4),
                "npos": entry["npos"],
                "source_crop": fname,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            }
        }

        results.append({
            "fname": fname,
            "pos5_digit": d5,
            "conf": round(d5_conf, 4),
            "gap": round(gap, 4),
            "npos": entry["npos"],
        })

        if not dry_run:
            with get_session() as s:
                row = s.get(MeterReading, entry["image_name"])
                if row is None:
                    continue
                existing = {}
                if row.notes:
                    try:
                        existing = (json.loads(row.notes)
                                    if isinstance(row.notes, str) else row.notes)
                    except (json.JSONDecodeError, TypeError):
                        existing = {}
                existing.update(anchor_data)
                existing.pop("needs_review", None)
                row.notes = json.dumps(existing)
                s.commit()
                written += 1

        if scanned % 1000 == 0:
            log.info("  Scanned: %d, Written: %d", scanned, written)

    print(f"\n{'=' * 72}")
    print(f"n00 Pos5 Anchor Results")
    print(f"{'=' * 72}")
    print(f"  n00 frames found:    {len(n00_entries)}")
    print(f"  Scanned:             {scanned}")
    print(f"  Pos5 matched:        {len(results)}")
    if dry_run:
        print(f"  Would write:         {len(results)}")
    else:
        print(f"  Written to DB:       {written}")

    if results:
        print(f"\n  Last 20:")
        print(f"  {'Crop':<45} {'npos':>4} {'p5':>3} {'conf':>8} {'gap':>8}")
        print(f"  {'─' * 72}")
        for a in results[-20:]:
            print(f"  {a['fname']:<45} {a['npos']:>4} {a['pos5_digit']:>3} "
                  f"{a['conf']:>8.4f} {a['gap']:>8.4f}")

    return len(results)


def main():
    p = argparse.ArgumentParser(
        description="Store pos5 drum-digit match results at n00 frames")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("=== n00 Pos5 Anchor ===")
    total = find_n00_digits(dry_run=args.dry_run)
    if args.dry_run:
        print(f"\nDRY RUN — {total} entries would be written.")
    else:
        print(f"\nTotal: {total} entries written.")
    log.info("=== Done ===")


if __name__ == "__main__":
    main()