"""Template management endpoints — list, extract, delete."""

import os
import re

from fastapi import APIRouter, HTTPException

from water_meter.core.common import PROC_DIR, TEMPLATE_DIR
from water_meter.core.db import MeterReading, get_session

router = APIRouter()


@router.get("/api/templates")
def api_templates():
    pos5, static = [], []
    p5pat, spat = re.compile(r"pos5_digit(\d+)_n(\d{2})\.png"), re.compile(r"pos(\d)_digit(\d+)(?:_\d+)?\.png")
    for fn in sorted(os.listdir(TEMPLATE_DIR)):
        m = p5pat.match(fn)
        if m: pos5.append({"filename": fn, "digit": int(m.group(1)), "npos": int(m.group(2))}); continue
        m = spat.match(fn)
        if m and int(m.group(1)) < 5: static.append({"filename": fn, "pos": int(m.group(1)), "digit": int(m.group(2))})
    missing_p5 = [{"digit": d, "npos": n} for d in range(10) for n in (0, 10, 20, 30, 70, 80, 90)
                   if not any(t["digit"] == d and t["npos"] == n for t in pos5)]
    missing_st = [{"pos": p, "digit": d} for p in range(5) for d in range(10)
                   if not any(t["pos"] == p and t["digit"] == d for t in static)]
    return {"pos5": pos5, "static": static, "missing_pos5": missing_p5, "missing_static": missing_st}


@router.post("/api/reading/{image_name}/extract_template/{pos}")
async def api_extract_template(image_name: str, pos: int):
    """Extract a digit box from this frame's odo crop and save as a template.

    The digit value is taken from the current `digits` field (which must
    be manually verified first via /correct).  For pos5, the template is
    saved with the current npos in its filename (e.g. pos5_digit7_n16.png).
    """
    import cv2
    from water_meter.core.common import (
        get_digit_slots, REFERENCE_CROP_W, DIGIT_SLOTS, PROC_DIR, TEMPLATE_DIR,
    )

    if pos < 0 or pos > 5:
        raise HTTPException(status_code=400, detail="pos must be 0-5")

    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404, detail="Row not found")
        if not row.odo_crop_file:
            raise HTTPException(status_code=404, detail="No odo crop available")
        if not row.digits or len(row.digits) != 6:
            raise HTTPException(status_code=400,
                                detail="Digits must be verified before extracting template")

        digit_val = int(row.digits[pos])
        crop_path = os.path.join(PROC_DIR, row.odo_crop_file)
        if not os.path.exists(crop_path):
            raise HTTPException(status_code=404, detail="Odo crop file not found")

        img = cv2.imread(crop_path)
        if img is None:
            raise HTTPException(status_code=500, detail="Failed to read odo crop")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, w = gray.shape[:2]
        slots = get_digit_slots(w)
        x0, x1 = slots[pos]
        box = gray[:, max(0, x0):min(w, x1)]

        if pos < 5:
            # Static digit: save as posN_digitD.png
            base = f"pos{pos}_digit{digit_val}"
            existing = sorted(
                f for f in os.listdir(TEMPLATE_DIR)
                if re.match(rf"pos{pos}_digit{digit_val}(?:_\d+)?\.png", f))
            next_idx = len(existing) + 1
            out_name = f"{base}_{next_idx:03d}.png" if existing else f"{base}.png"
        else:
            # pos5 drum digit: save with npos
            npos = row.npos or 0
            out_name = f"pos5_digit{digit_val}_n{npos:02d}.png"
            # Remove old template at this exact (digit, npos) if it exists
            for old in os.listdir(TEMPLATE_DIR):
                if re.match(rf"pos5_digit{digit_val}_n{npos:02d}\.png", old):
                    os.remove(os.path.join(TEMPLATE_DIR, old))

        out_path = os.path.join(TEMPLATE_DIR, out_name)
        cv2.imwrite(out_path, box)

        return {"status": "ok", "template": out_name,
                "pos": pos, "digit": digit_val,
                "npos": row.npos if pos == 5 else None}


@router.delete("/api/templates/{filename}")
def api_delete_template(filename: str):
    path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(path): os.remove(path)
    return {"deleted": filename}
