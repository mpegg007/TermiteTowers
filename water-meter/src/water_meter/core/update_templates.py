#!/usr/bin/env python3
"""Auto-update odometer digit templates from high-confidence reads.

Queries the DB for frames with high odo_confidence, extracts the digit boxes,
and saves new templates when they're better than existing ones or fill gaps
in the template bank.

Mode 1 — Fill gaps:
    Find positions/npos combos missing from the template bank and extract
    the best available crop for each.

Mode 2 — Refresh from high-conf reads:
    For any high-confidence read (odo_confidence >= threshold), compare
    its digit crop against the current best template.  If the crop is a
    significantly better match to the expected digit, replace the template.

Usage:
    # Fill missing pos5 templates
    .venv/bin/python scripts/water_meter/update_templates.py

    # Refresh all templates from high-confidence reads
    .venv/bin/python scripts/water_meter/update_templates.py --refresh --min-conf 0.85

    # Dry-run (show what would change)
    .venv/bin/python scripts/water_meter/update_templates.py --dry-run
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    IMAGE_DIR, PROC_DIR, TEMPLATE_DIR,
    npos_from_fname,
    get_digit_slots, extract_pos5_box,
    load_pos5_templates, load_static_templates,
    preprocess,
    POS5_INDEX, REFERENCE_CROP_W, DIGIT_SLOTS, NUM_DIGITS, TEMPLATE_DIGITS,
    MATCH_THRESHOLD,
)
from water_meter.core.db import MeterReading, init_db, get_session, _to_native

log = logging.getLogger("update_templates")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
DEFAULT_MIN_CONFIDENCE = 0.80   # must have at least this odo_confidence
TEMPLATE_IMPROVEMENT_GAP = 0.05 # replace only if new conf exceeds old by this much


# ---------------------------------------------------------------------------
# Template bank inventory
# ---------------------------------------------------------------------------

def inventory_templates() -> Dict[str, Set]:
    """Return what templates exist: {type: set_of_keys}."""
    pos5_existing: Set[Tuple[int, int]] = set()
    static_existing: Set[Tuple[int, int]] = set()

    pos5_pat = re.compile(r"pos5_digit(\d+)_n(\d{2})\.png")
    static_pat = re.compile(r"pos(\d)_digit(\d+)(?:_\d+)?\.png")

    for fn in os.listdir(TEMPLATE_DIR):
        m = pos5_pat.match(fn)
        if m:
            pos5_existing.add((int(m.group(1)), int(m.group(2))))
            continue
        m = static_pat.match(fn)
        if m:
            pos = int(m.group(1))
            digit = int(m.group(2))
            if pos < 5:
                static_existing.add((pos, digit))
            continue

    return {"pos5": pos5_existing, "static": static_existing}


def missing_pos5_templates() -> Set[Tuple[int, int]]:
    """Return (digit, npos) combos not yet in the template bank."""
    existing = inventory_templates()["pos5"]
    target_npos = {0, 10, 20, 30, 70, 80, 90}
    needed = set()
    for digit in TEMPLATE_DIGITS:
        for n in target_npos:
            if (digit, n) not in existing:
                needed.add((digit, n))
    return needed


def missing_static_templates() -> Set[Tuple[int, int]]:
    """Return (pos, digit) combos not yet in the template bank for pos0-4."""
    existing = inventory_templates()["static"]
    needed = set()
    for pos in range(5):
        for digit in TEMPLATE_DIGITS:
            if (pos, digit) not in existing:
                needed.add((pos, digit))
    return needed


# ---------------------------------------------------------------------------
# DB query helpers — return plain dicts to avoid detached session errors
# ---------------------------------------------------------------------------

def get_high_conf_rows(min_confidence: float = DEFAULT_MIN_CONFIDENCE
                       ) -> List[dict]:
    """Return rows with odo_confidence >= threshold as plain dicts."""
    with get_session() as session:
        rows = (
            session.query(
                MeterReading.image_name,
                MeterReading.odo_crop_file,
                MeterReading.odo_confidence,
                MeterReading.odo_pos5,
                MeterReading.odo_pos5_conf,
                MeterReading.npos,
                MeterReading.capture_ts,
                MeterReading.status,
                MeterReading.notes,
            )
            .filter(MeterReading.odo_confidence >= min_confidence)
            .filter(MeterReading.status == "OK")
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )
    return [
        {
            "image_name": r[0],
            "odo_crop_file": r[1],
            "odo_confidence": r[2],
            "odo_pos5": r[3],
            "odo_pos5_conf": r[4],
            "npos": r[5],
            "capture_ts": r[6],
            "status": r[7],
            "notes": r[8],
        }
        for r in rows
    ]


def get_odo_crop_for_row(row: dict) -> Optional[np.ndarray]:
    """Read the odo crop file for a given row dict. Returns BGR image or None."""
    cf = row.get("odo_crop_file")
    if not cf:
        return None
    path = os.path.join(PROC_DIR, cf)
    if not os.path.exists(path):
        return None
    return cv2.imread(path)


def extract_digit_boxes(odo_img: np.ndarray) -> list[Optional[np.ndarray]]:
    """Extract all 6 digit boxes as grayscale from an odo crop."""
    if odo_img is None:
        return [None] * 6
    h, w = odo_img.shape[:2]
    gray = cv2.cvtColor(odo_img, cv2.COLOR_BGR2GRAY)
    slots = get_digit_slots(w)
    boxes = []
    for x0, x1 in slots:
        if x1 - x0 >= 10 and x0 < w and x1 <= w:
            boxes.append(gray[:, x0:x1])
        else:
            boxes.append(None)
    return boxes


def parse_digits_from_row(row: dict) -> List[Optional[int]]:
    """Extract per-position digit values from the row's notes JSON."""
    notes = row.get("notes")
    if not notes:
        return [None] * 6
    try:
        data = json.loads(notes) if isinstance(notes, str) else notes
        pos_digits = data.get("pos_digits", [])
        while len(pos_digits) < 6:
            pos_digits.append(None)
        return pos_digits[:6]
    except (json.JSONDecodeError, TypeError):
        return [None] * 6


# ---------------------------------------------------------------------------
# Fill missing templates
# ---------------------------------------------------------------------------

def fill_missing_pos5(high_conf_rows: List[dict], dry_run: bool = False) -> int:
    """Find and fill missing pos5 templates from high-confidence reads."""
    missing = missing_pos5_templates()
    if not missing:
        log.info("All pos5 templates present — nothing to fill.")
        return 0

    log.info("Missing pos5 templates: %d", len(missing))
    for d, n in sorted(missing):
        log.info("  digit=%d npos=%d", d, n)

    missing_by_digit: Dict[int, list] = {d: [] for d in TEMPLATE_DIGITS}
    for d, n in missing:
        missing_by_digit[d].append(n)

    saved = 0
    for row in high_conf_rows:
        odo = get_odo_crop_for_row(row)
        if odo is None:
            continue

        npos = npos_from_fname(row.get("odo_crop_file") or "")
        pos_digits = parse_digits_from_row(row)

        digit_val = pos_digits[POS5_INDEX] if len(pos_digits) > POS5_INDEX else None
        if digit_val is None:
            digit_val = row.get("odo_pos5")

        if digit_val is None or npos is None:
            continue

        if (digit_val, npos) not in missing:
            for target_npos in list(missing_by_digit.get(digit_val, [])):
                if abs(npos - target_npos) <= 5:
                    box = extract_pos5_box(odo)
                    if box is not None:
                        out = f"pos5_digit{digit_val}_n{target_npos:02d}.png"
                        path = os.path.join(TEMPLATE_DIR, out)
                        if not os.path.exists(path):
                            if not dry_run:
                                cv2.imwrite(path, box)
                            log.info("  ✓ Saved %s (from %s, npos=%d)",
                                     out, row.get("odo_crop_file"), npos)
                            saved += 1
                            missing.discard((digit_val, target_npos))
                            missing_by_digit[digit_val].remove(target_npos)
                        break

        if not missing:
            break

    if missing:
        log.info("Still missing after scan: %d", len(missing))
        for d, n in sorted(missing):
            log.info("  digit=%d npos=%d", d, n)

    return saved


def fill_missing_static(high_conf_rows: List[dict], dry_run: bool = False) -> int:
    """Find and fill missing static (pos0-4) templates."""
    missing = missing_static_templates()
    if not missing:
        log.info("All static templates present — nothing to fill.")
        return 0

    log.info("Missing static templates: %d", len(missing))
    for pos, d in sorted(missing):
        log.info("  pos=%d digit=%d", pos, d)

    saved = 0
    for row in high_conf_rows:
        odo = get_odo_crop_for_row(row)
        if odo is None:
            continue

        pos_digits = parse_digits_from_row(row)
        boxes = extract_digit_boxes(odo)

        for pos in range(5):
            digit_val = pos_digits[pos] if len(pos_digits) > pos else None
            if digit_val is None:
                continue

            box = boxes[pos]
            if box is None:
                continue

            base = f"pos{pos}_digit{digit_val}"
            existing = sorted(glob.glob(os.path.join(TEMPLATE_DIR, f"{base}_*.png")))

            # If this is a NEW digit (not in templates at all), save it always
            if (pos, digit_val) in missing:
                # Migrate legacy single-file name if it exists
                legacy = os.path.join(TEMPLATE_DIR, f"{base}.png")
                if os.path.exists(legacy) and not existing:
                    os.rename(legacy, os.path.join(TEMPLATE_DIR, f"{base}_001.png"))
                    existing = [os.path.join(TEMPLATE_DIR, f"{base}_001.png")]
                next_idx = len(existing) + 1
                out = f"{base}_{next_idx:03d}.png"
                path = os.path.join(TEMPLATE_DIR, out)
                if not dry_run:
                    cv2.imwrite(path, box)
                log.info("  ✓ Saved %s (from %s)", out, row.get("odo_crop_file"))
                saved += 1
                missing.discard((pos, digit_val))

            # If the digit already exists, add more examples (up to 5 total)
            elif len(existing) < 5:
                next_idx = len(existing) + 1
                out = f"{base}_{next_idx:03d}.png"
                path = os.path.join(TEMPLATE_DIR, out)
                if not dry_run:
                    cv2.imwrite(path, box)
                log.info("  + Added %s (from %s)", out, row.get("odo_crop_file"))
                saved += 1
                break  # one additional example per row is enough

        if not missing:
            break

    if missing:
        log.info("Still missing after scan: %d", len(missing))

    return saved


# ---------------------------------------------------------------------------
# Refresh: replace templates with better matches
# ---------------------------------------------------------------------------

def refresh_templates(high_conf_rows: List[dict],
                      min_confidence: float = DEFAULT_MIN_CONFIDENCE,
                      dry_run: bool = False) -> int:
    """Replace existing templates if a high-conf crop is a better match.

    Scans ALL high-confidence rows first, tracks the BEST candidate per
    template (by self-other gap), then writes each template only once
    at the end.  This guarantees the best crop wins, not just the last
    qualifying row.
    """
    pos5_bank = load_pos5_templates(TEMPLATE_DIR)
    static_banks = []
    for pos in range(5):
        from water_meter.core.decode_odo import load_pos_static_digit_templates
        bank = load_pos_static_digit_templates(TEMPLATE_DIR, pos)
        static_banks.append(bank)

    # Track best candidate per template: (pos_or_key) -> (gap, self, other, box, info)
    best_static_candidate: Dict[Tuple[int, int], Tuple[float, float, float, np.ndarray, str]] = {}
    best_pos5_candidate: Dict[Tuple[int, int], Tuple[float, float, float, np.ndarray, str]] = {}

    scanned = 0
    for row in high_conf_rows:
        odo = get_odo_crop_for_row(row)
        if odo is None:
            continue

        npos = npos_from_fname(row.get("odo_crop_file") or "")
        pos_digits = parse_digits_from_row(row)
        boxes = extract_digit_boxes(odo)
        scanned += 1

        # pos0-4 — evaluate candidates
        for pos in range(5):
            digit_val = pos_digits[pos] if len(pos_digits) > pos else None
            if digit_val is None or boxes[pos] is None:
                continue

            bank = static_banks[pos]
            existing_templates = bank.get(digit_val, [])
            if not existing_templates:
                continue

            q = preprocess(boxes[pos])
            best_existing_self = 0.0
            for t in existing_templates:
                tp = preprocess(t)
                if q.shape != tp.shape:
                    tp = cv2.resize(tp, (q.shape[1], q.shape[0]),
                                    interpolation=cv2.INTER_NEAREST)
                s = cv2.matchTemplate(q, tp, cv2.TM_CCOEFF_NORMED)[0][0]
                if s > best_existing_self:
                    best_existing_self = s

            best_other = 0.0
            for other_d in TEMPLATE_DIGITS:
                if other_d == digit_val:
                    continue
                for t in bank.get(other_d, []):
                    tp = preprocess(t)
                    if q.shape != tp.shape:
                        tp = cv2.resize(tp, (q.shape[1], q.shape[0]),
                                        interpolation=cv2.INTER_NEAREST)
                    s = cv2.matchTemplate(q, tp, cv2.TM_CCOEFF_NORMED)[0][0]
                    if s > best_other:
                        best_other = s

            gap = best_existing_self - best_other
            if gap > TEMPLATE_IMPROVEMENT_GAP and best_existing_self > 0.6:
                key = (pos, digit_val)
                prev = best_static_candidate.get(key)
                if prev is None or gap > prev[0]:
                    best_static_candidate[key] = (gap, best_existing_self, best_other,
                                                   boxes[pos].copy(),
                                                   row.get("odo_crop_file", "?"))

        # pos5 — evaluate candidates
        digit_val = pos_digits[POS5_INDEX] if len(pos_digits) > POS5_INDEX else None
        if digit_val is not None and npos is not None and boxes[POS5_INDEX] is not None:
            key = (digit_val, npos)
            if key in pos5_bank:
                q = preprocess(boxes[POS5_INDEX])
                t = pos5_bank[key]
                tp = preprocess(t)
                if q.shape != tp.shape:
                    tp = cv2.resize(tp, (q.shape[1], q.shape[0]),
                                    interpolation=cv2.INTER_NEAREST)
                s = cv2.matchTemplate(q, tp, cv2.TM_CCOEFF_NORMED)[0][0]

                best_other = 0.0
                for other_key, other_t in pos5_bank.items():
                    if other_key[0] == digit_val:
                        continue
                    if abs(other_key[1] - npos) > 10:
                        continue
                    otp = preprocess(other_t)
                    if q.shape != otp.shape:
                        otp = cv2.resize(otp, (q.shape[1], q.shape[0]),
                                         interpolation=cv2.INTER_NEAREST)
                    os_ = cv2.matchTemplate(q, otp, cv2.TM_CCOEFF_NORMED)[0][0]
                    if os_ > best_other:
                        best_other = os_

                gap = s - best_other
                if gap > TEMPLATE_IMPROVEMENT_GAP and s > 0.6:
                    prev = best_pos5_candidate.get(key)
                    if prev is None or gap > prev[0]:
                        best_pos5_candidate[key] = (gap, s, best_other,
                                                     boxes[POS5_INDEX].copy(),
                                                     row.get("odo_crop_file", "?"))

    # Write the best candidate for each template
    replaced = 0
    for (pos, digit_val), (gap, self_conf, other_conf, box, src) in sorted(best_static_candidate.items()):
        out = f"pos{pos}_digit{digit_val}.png"
        path = os.path.join(TEMPLATE_DIR, out)
        if not dry_run:
            cv2.imwrite(path, box)
        log.info("  ↻ Replaced %s (gap=%.3f, self=%.3f, other=%.3f, from %s)",
                 out, gap, self_conf, other_conf, src)
        replaced += 1

    for (digit_val, npos), (gap, self_conf, other_conf, box, src) in sorted(best_pos5_candidate.items()):
        out = f"pos5_digit{digit_val}_n{npos:02d}.png"
        path = os.path.join(TEMPLATE_DIR, out)
        if not dry_run:
            cv2.imwrite(path, box)
        log.info("  ↻ Replaced %s (gap=%.3f, self=%.3f, other=%.3f, from %s)",
                 out, gap, self_conf, other_conf, src)
        replaced += 1

    log.info("Scanned %d rows, wrote %d improved templates", scanned, replaced)
    return replaced


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Auto-update odometer digit templates from high-confidence reads")
    p.add_argument("--min-conf", type=float, default=DEFAULT_MIN_CONFIDENCE,
                   help=f"Minimum odo_confidence (default: {DEFAULT_MIN_CONFIDENCE})")
    p.add_argument("--refresh", action="store_true",
                   help="Also refresh/replace existing templates with better ones")
    p.add_argument("--dry-run", action="store_true",
                   help="Report what would change, don't write files")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    inv = inventory_templates()
    log.info("Template bank inventory:")
    log.info("  Pos5 (digit@npos): %d", len(inv["pos5"]))
    log.info("  Static (pos,digit): %d", len(inv["static"]))

    missing_p5 = missing_pos5_templates()
    missing_st = missing_static_templates()
    log.info("Missing pos5: %d, static: %d", len(missing_p5), len(missing_st))

    if not missing_p5 and not missing_st and not args.refresh:
        log.info("Template bank is complete. Use --refresh to improve existing.")
        return

    rows = get_high_conf_rows(args.min_conf)
    log.info("High-confidence rows (≥%.2f): %d", args.min_conf, len(rows))

    if not rows:
        log.warning("No high-confidence rows found. Cannot update templates.")
        return

    saved = 0
    replaced = 0

    if missing_p5:
        saved += fill_missing_pos5(rows, dry_run=args.dry_run)

    if missing_st:
        saved += fill_missing_static(rows, dry_run=args.dry_run)

    if args.refresh:
        replaced = refresh_templates(rows, args.min_conf, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\nDRY RUN — no files written.")
        print(f"Would save: {saved} new templates")
        print(f"Would refresh: {replaced} existing templates")
    else:
        print(f"\nSaved: {saved} new templates")
        print(f"Refreshed: {replaced} existing templates")


if __name__ == "__main__":
    main()