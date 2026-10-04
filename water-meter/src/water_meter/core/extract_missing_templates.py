#!/usr/bin/env python3
"""Extract missing digit templates from frames with confirmed odo_published values.

Uses odo_published as ground truth. For each position (0-4), extracts digit
boxes and saves as posN_digitD.png templates if they're missing from the bank.

Usage:
    .venv/bin/python scripts/water_meter/extract_missing_templates.py
"""

import glob, os, sys, cv2
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/
from water_meter.core.common import TEMPLATE_DIR, DIGIT_SLOTS, REFERENCE_CROP_W, PROC_DIR
from water_meter.core.db import MeterReading, get_session, init_db

def main():
    init_db()
    saved = 0
    
    with get_session() as s:
        rows = s.query(MeterReading).filter(
            MeterReading.odo_published.isnot(None),
            MeterReading.status == 'OK',
            MeterReading.capture_ts >= '2026-08-03'
        ).order_by(MeterReading.capture_ts.desc()).limit(2000).all()
        
        for row in rows:
            if saved >= 50:
                break
            
            val = float(row.odo_published)
            integer_part = int(val)
            tenths = int(round((val - integer_part) * 10)) % 10
            digit_str = f"{integer_part:05d}{tenths}"
            expected = [int(c) for c in digit_str]
            
            # Find odo crop
            if not row.odo_crop_file:
                continue
            # odo_crop_file is stored as e.g. "2026-08-04/odo_...jpg" relative to PROC_DIR
            crop_path = os.path.join(PROC_DIR, row.odo_crop_file)
            if not os.path.exists(crop_path):
                continue
            
            img = cv2.imread(crop_path)
            if img is None or img.size == 0:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, w = gray.shape[:2]
            s_ratio = w / REFERENCE_CROP_W
            
            # Check each position 0-4
            for pos in range(5):
                digit_val = expected[pos]
                base = f"pos{pos}_digit{digit_val}"
                legacy = os.path.join(TEMPLATE_DIR, f"{base}.png")
                existing = glob.glob(os.path.join(TEMPLATE_DIR, f"{base}_*.png"))
                
                if os.path.exists(legacy) or len(existing) >= 3:
                    continue  # already have this template
                
                x0 = max(0, int(DIGIT_SLOTS[pos][0] * s_ratio))
                x1 = min(w, int(DIGIT_SLOTS[pos][1] * s_ratio))
                if x1 - x0 < 10:
                    continue
                box = gray[:, x0:x1]
                
                if existing:
                    next_idx = len(existing) + 1
                    out_name = f"{base}_{next_idx:03d}.png"
                else:
                    out_name = f"{base}.png"
                
                out_path = os.path.join(TEMPLATE_DIR, out_name)
                cv2.imwrite(out_path, box)
                saved += 1
                print(f"  Saved {out_name} (pos={pos} digit={digit_val} from {os.path.basename(crop_path)})")
        
        print(f"\nSaved {saved} new templates")
        s.commit()

if __name__ == "__main__":
    main()