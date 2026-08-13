#!/usr/bin/env python3
"""decode_odo.py — odometer digit reader for all 6 positions + DB writer.

Reads odometer crops from proc/YYYY-MM-DD/ and decodes all 6 digits
via template matching.  No monotonicity constraints — each crop is
decoded independently from its image only.

Writes results back to PostgreSQL water_meter.meter_readings table.

Usage:
    .venv/bin/python scripts/water_meter/decode_odo.py --crop proc/.../odo_xxx.jpg
    .venv/bin/python scripts/water_meter/decode_odo.py --batch --db-update
    .venv/bin/python scripts/water_meter/decode_odo.py --batch --db-update --force
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import (
    IMAGE_DIR, PROC_DIR, TEMPLATE_DIR,
    npos_from_fname, npos_distance,
    get_digit_slots,
    load_pos5_templates, load_static_templates,
    preprocess, match_pos5, match_static,
    DIGIT_SLOTS, REFERENCE_CROP_W, NUM_DIGITS, POS5_INDEX,
    MATCH_THRESHOLD, NPOS_WINDOW, TEMPLATE_DIGITS,
    match_with_ensemble, preprocess_clahe_otsu, preprocess_adaptive, refine_digit_slots, odo_stats,
)
from water_meter.core.db import (
    MeterReading, init_db, get_session,
    get_session as db_get_session,
)

log = logging.getLogger("decode_odo")

POS5_CONF_MIN = 0.55
STATIC_CONF_MIN = 0.40


def get_scaled_slots(crop_w: int) -> List[Tuple[int, int]]:
    s = crop_w / REFERENCE_CROP_W
    return [(max(0, int(a * s)), min(crop_w, int(b * s))) for a, b in DIGIT_SLOTS]


def load_pos_static_digit_templates(template_dir: str = None, pos: int = 0
                                    ) -> Dict[int, List[np.ndarray]]:
    if template_dir is None:
        template_dir = TEMPLATE_DIR
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


def match_static_digit(box: np.ndarray,
                       bank: Dict[int, List[np.ndarray]]) -> Tuple[Optional[int], float]:
    """Match a digit box against per-position templates.

    When only one digit template exists in the bank, uses a simple
    binarized match with a relaxed threshold — if there's only one
    possible digit, even a mediocre match is strong evidence.

    When 2+ digits exist, uses the full ensemble matcher with the
    standard confidence threshold for discrimination.
    """
    available_digits = [d for d, templates in bank.items() if templates]
    if not available_digits:
        return None, 0.0

    # ── Single-digit mode: only one possible digit ─────────────────
    if len(available_digits) == 1:
        only_digit = available_digits[0]
        templates = bank[only_digit]
        if not templates:
            return None, 0.0
        # Try all preprocessing paths on both query and template,
        # pick the best match.  Uses vertical sliding so digit roll
        # does not kill the match.
        best_s = -1.0
        q_paths = [
            preprocess(box),
            cv2.bitwise_not(preprocess_adaptive(box, 15, 4)),
        ]
        for q in q_paths:
            for t_img in templates:
                tp = preprocess(t_img)
                # Resize width to match query, preserve aspect ratio
                t_h_scaled = int(tp.shape[0] * (q.shape[1] / tp.shape[1]))
                tp_resized = cv2.resize(tp, (q.shape[1], t_h_scaled),
                                        interpolation=cv2.INTER_NEAREST)
                # Vertical sliding to find best vertical alignment
                q_padded = cv2.copyMakeBorder(
                    q,
                    int(q.shape[0] * 0.35),
                    int(q.shape[0] * 0.35),
                    0, 0, cv2.BORDER_REPLICATE,
                )
                result = cv2.matchTemplate(q_padded, tp_resized,
                                           cv2.TM_CCOEFF_NORMED)
                s = float(np.max(result))
                if s > best_s:
                    best_s = s
        # Boost: if there's no competition, normalize to [0.5, 1.0] range
        boosted = 0.5 + best_s * 0.5
        return only_digit, boosted

    # ── Multi-digit mode: ensemble + fallback ───────────────────────
    ordered_templates: List[Optional[np.ndarray]] = [None] * 10
    for d in range(10):
        tmpls = bank.get(d, [])
        ordered_templates[d] = tmpls[0] if tmpls else None

    d_ens, conf_ens, _scores = match_with_ensemble(box, ordered_templates)

    q = preprocess(box)
    best_d, best_s = None, -1.0
    for d, templates in bank.items():
        if not templates:
            continue
        for t in templates:
            tb = preprocess(t)
            # Resize width to match query, preserve aspect ratio for
            # height so vertical sliding works correctly.
            t_h_scaled = int(tb.shape[0] * (q.shape[1] / tb.shape[1]))
            tb_resized = cv2.resize(tb, (q.shape[1], t_h_scaled),
                                    interpolation=cv2.INTER_NEAREST)
            # Use vertical sliding via common._make_vertical_slide_query
            # and _vertical_slide_score (imported above as part of the
            # common module).
            q_padded = cv2.copyMakeBorder(
                q, int(q.shape[0] * 0.35), int(q.shape[0] * 0.35),
                0, 0, cv2.BORDER_REPLICATE,
            )
            result = cv2.matchTemplate(q_padded, tb_resized,
                                       cv2.TM_CCOEFF_NORMED)
            s = float(np.max(result))
            if s > best_s:
                best_s, best_d = s, d

    if d_ens is not None and conf_ens >= best_s:
        return d_ens, conf_ens
    if best_d is not None and best_s >= STATIC_CONF_MIN:
        return best_d, best_s
    return best_d, best_s


def process_crop(crop_path: str,
                 pos5_bank: Dict[Tuple[int, int], np.ndarray],
                 static_banks: List[Dict[int, List[np.ndarray]]],
                 debug: bool = False) -> dict:
    """Decode all 6 digits from a single odo crop.  No cross-frame state."""
    fname = os.path.basename(crop_path)
    img = cv2.imread(crop_path)
    if img is None:
        return {"crop_file": fname, "digits": None, "reading": None,
                "confidence": 0.0, "status": "FAIL",
                "pos_confs": [0.0] * 6, "pos_digits": [None] * 6,
                "pos5_source": "none"}

    h, w = img.shape[:2]
    npos = npos_from_fname(fname)
    slots = get_scaled_slots(w)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    slots = refine_digit_slots(gray, slots)

    pos_digits: List[Optional[int]] = [None] * 6
    pos_confs: List[float] = [0.0] * 6

    # pos0-4: individual digit template matching
    for pos in range(5):
        x0, x1 = slots[pos]
        if x1 - x0 < 10:
            continue
        box = gray[:, x0:x1]
        bank = static_banks[pos]
        if bank:
            digit, conf = match_static_digit(box, bank)
        else:
            digit, conf = None, 0.0
        pos_digits[pos] = digit
        pos_confs[pos] = round(conf, 4)

    # pos5: npos-constrained matching
    x0, x1 = slots[5]
    box5 = gray[:, x0:x1]
    d5, c5 = match_pos5(box5, npos, pos5_bank)
    pos5_source = "matched" if d5 is not None else "none"
    pos_digits[5] = d5
    pos_confs[5] = round(c5, 4)

    # Compose reading
    digits_str = "".join(str(d) if d is not None else "?" for d in pos_digits)
    reading = None
    if all(pos_digits[i] is not None for i in range(6)):
        integer_part = (pos_digits[0] * 10000 + pos_digits[1] * 1000 +
                        pos_digits[2] * 100 + pos_digits[3] * 10 + pos_digits[4])
        fractional_part = pos_digits[5] / 10.0 + (npos or 0) / 1000.0
        reading = integer_part + fractional_part

    valid_confs = [c for c in pos_confs if c > 0]
    overall_conf = round(sum(valid_confs) / len(valid_confs), 4) if valid_confs else 0.0

    return {
        "crop_file": fname,
        "digits": digits_str,
        "reading": reading,
        "confidence": overall_conf,
        "npos": npos,
        "pos_digits": pos_digits,
        "pos_confs": pos_confs,
        "pos5_digit": d5,
        "pos5_conf": round(c5, 4),
        "pos5_source": pos5_source,
        "status": "OK" if d5 is not None or any(d is not None for d in pos_digits[:5]) else "FAIL",
    }


# ---------------------------------------------------------------------------
# Batch processing: stateless, process each crop individually
# ---------------------------------------------------------------------------

def batch_process(files: List[str],
                  pos5_bank: Dict[Tuple[int, int], np.ndarray],
                  static_banks: List[Dict[int, List[np.ndarray]]],
                  db_update: bool = False,
                  skip_anomalies: bool = True,
                  debug: bool = False) -> List[dict]:
    """Process each odo crop independently. No monotonicity, no cross-frame state."""
    results: List[dict] = []
    if not files:
        return results

    # Pre-load anomaly names
    anomaly_names: set = set()
    with db_get_session() as session:
        if skip_anomalies:
            anomalous = (
                session.query(MeterReading.odo_crop_file)
                .filter(MeterReading.status == "ANOMALY")
                .all()
            )
            anomaly_names = {os.path.basename(row[0]) for row in anomalous if row[0]}

    total = len(files)
    skipped = 0
    for i, fp in enumerate(files):
        fname_basename = os.path.basename(fp)
        if skip_anomalies and fname_basename in anomaly_names:
            skipped += 1
            continue
        r = process_crop(fp, pos5_bank, static_banks, debug=debug)
        results.append(r)
        if (i + 1) % 2000 == 0 or (i + 1) == total:
            log.info("  [%d/%d] skipped=%d", i + 1, total, skipped)

    return results


def update_db_from_results(results: List[dict]) -> int:
    """Write decode results to DB. Returns number of updated rows."""
    updated = 0
    for r in results:
        crop_file = os.path.basename(r["crop_file"])
        if r["status"] == "FAIL":
            continue

        try:
            with db_get_session() as s:
                row = s.query(MeterReading).filter(
                    MeterReading.odo_crop_file.like(f"%/{crop_file}")
                ).first()
                if row is None:
                    row = s.query(MeterReading).filter(
                        MeterReading.odo_crop_file == crop_file
                    ).first()
                if row is None:
                    continue

                if r["digits"] is not None:
                    row.digits = r["digits"]
                    row.do_digits = r["digits"]
                if r["reading"] is not None:
                    row.odo_reading = float(r["reading"])
                    row.do_reading = float(r["reading"])
                row.odo_confidence = float(r["confidence"])
                row.do_confidence = float(r["confidence"])
                row.odo_pos5 = int(r["pos5_digit"]) if r["pos5_digit"] is not None else None
                row.do_pos5 = int(r["pos5_digit"]) if r["pos5_digit"] is not None else None
                row.odo_pos5_conf = float(r["pos5_conf"])
                row.do_pos5_conf = float(r["pos5_conf"])
                row.do_pos5_source = r.get("pos5_source", "matched")

                safe_confs = [float(c) for c in r.get("pos_confs", [])]
                safe_digits = [int(d) if d is not None else None for d in r.get("pos_digits", [])]
                conf_data = {
                    "pos_confs": safe_confs,
                    "pos_digits": safe_digits,
                    "pos5_source": r.get("pos5_source", "matched"),
                }

                # Store per-position detail as JSON in do_details
                row.do_details = json.dumps({
                    "pos_confs": safe_confs,
                    "pos_digits": safe_digits,
                    "pos5_source": r.get("pos5_source", "matched"),
                })

                # Merge with existing notes (preserve n00_anchor)
                existing = {}
                if row.notes:
                    try:
                        existing = json.loads(row.notes)
                    except (json.JSONDecodeError, TypeError):
                        existing = {}
                # Keep n00_anchor if present
                if "n00_anchor" in existing:
                    conf_data["n00_anchor"] = existing["n00_anchor"]
                existing.update(conf_data)
                row.notes = json.dumps(existing)
                updated += 1
        except Exception as e:
            log.warning("DB update failed for %s: %s", crop_file, e)

    return updated


def collect_crop_files(proc_dir: str = None) -> List[str]:
    if proc_dir is None:
        proc_dir = PROC_DIR
    pattern = os.path.join(proc_dir, "**", "odo_*.jpg")
    return sorted(glob.glob(pattern, recursive=True))


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Odometer decoder — reads all 6 digits + DB writer")
    p.add_argument("--crop", help="Path to single odometer crop")
    p.add_argument("--batch", action="store_true", help="Process all odo_*.jpg")
    p.add_argument("--db-update", action="store_true", help="Write results to DB")
    p.add_argument("--force", action="store_true", help="Process anomaly-flagged frames too")
    p.add_argument("--debug", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    pos5_bank = load_pos5_templates(TEMPLATE_DIR)
    static_banks = []
    for pos in range(5):
        bank = load_pos_static_digit_templates(TEMPLATE_DIR, pos)
        static_banks.append(bank)
        digits_present = sorted(d for d in range(10) if bank.get(d))
        log.info("  Pos%d: %s", pos, digits_present)

    if args.crop:
        r = process_crop(args.crop, pos5_bank, static_banks, debug=args.debug)
        print(f"  {r['crop_file']}: digits={r['digits']} conf={r['confidence']:.3f}")

    if args.batch:
        files = collect_crop_files()
        log.info("Processing %d crops...", len(files))
        results = batch_process(files, pos5_bank, static_banks,
                                skip_anomalies=not args.force, debug=args.debug)
        ok_count = sum(1 for r in results if r["status"] == "OK")
        print(f"\nBatch: {len(files)} crops processed, OK: {ok_count}")
        if args.db_update:
            updated = update_db_from_results(results)
            log.info("DB updated: %d rows", updated)


if __name__ == "__main__":
    main()