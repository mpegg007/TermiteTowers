"""Debug overlay and decode-debug endpoints.

All of these shell out to the decode_meter CLI (via the app venv) to
regenerate crops when needed, then draw debug overlays with OpenCV.
"""

import glob
import json
import os
import re
import shutil

from fastapi import APIRouter, HTTPException

from water_meter.core.common import (
    IMAGE_DIR, PROC_DIR, DEBUG_DIR, TEMPLATE_DIR,
    get_digit_slots, refine_digit_slots, DIGIT_COLORS,
    NPOS_WINDOW,
)
from water_meter.core.db import MeterReading, get_session

from ..utils import find_source_image, run_decode_meter

router = APIRouter()


def _regenerate_odo_crop(image_name: str, row_data: dict) -> None:
    """If the odo crop is missing, regenerate it via decode_meter and update the row."""
    crop_path = os.path.join(PROC_DIR, row_data.get("odo_crop_file", ""))
    if os.path.exists(crop_path):
        return

    src_path = find_source_image(image_name)
    if not src_path:
        raise HTTPException(status_code=404, detail="Odo crop not found and no source image available")

    tmp_dir = os.path.join(IMAGE_DIR, "web_debug_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, image_name)
    shutil.copy2(src_path, tmp_path)
    try:
        result = run_decode_meter(["--input-image", tmp_path, "--odo-crop", "--no-move"])
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"decode_meter.py failed: {result.stderr[:200]}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    m = re.match(r"water_meter_(\d{8}_\d{6})", image_name)
    ts_tag = m.group(1) if m else ""
    crops = sorted(glob.glob(
        os.path.join(PROC_DIR, "**", f"odo_{ts_tag}_*.jpg"), recursive=True))
    if not crops:
        raise HTTPException(status_code=500, detail="decode_meter.py ran but produced no odo crop")
    new_crop_rel = os.path.relpath(crops[-1], PROC_DIR)
    with get_session() as s:
        update_row = s.get(MeterReading, image_name)
        if update_row:
            update_row.odo_crop_file = new_crop_rel
            s.commit()
    row_data["odo_crop_file"] = new_crop_rel


@router.post("/api/debug_image/{image_name}")
async def api_debug_image(image_name: str):
    """Generate debug overlay by shelling out to decode_meter.py --dial-scan."""
    src_path = find_source_image(image_name)
    if not src_path:
        raise HTTPException(status_code=404, detail="Source image not found")

    # decode_meter.py writes to debug/hub_dial_scan_{ts_tag}.jpg
    m = re.match(r"water_meter_(\d{8}_\d{6})", image_name)
    ts_tag = m.group(1) if m else image_name.rsplit(".", 1)[0]
    out_name = f"hub_dial_scan_{ts_tag}.jpg"
    out_path = os.path.join(DEBUG_DIR, out_name)

    if os.path.exists(out_path):
        return {"debug_image": out_name, "cached": True}

    # Copy source image to a temp location so decode_meter can find it
    tmp_dir = os.path.join(IMAGE_DIR, "web_debug_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, image_name)
    shutil.copy2(src_path, tmp_path)

    try:
        result = run_decode_meter(["--input-image", tmp_path, "--dial-scan"])
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"decode_meter.py failed: {result.stderr[:200]}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if os.path.exists(out_path):
        return {"debug_image": out_name, "cached": False}
    raise HTTPException(status_code=500, detail="decode_meter.py did not produce output")


@router.post("/api/debug_odo/{image_name}")
async def api_debug_odo(image_name: str):
    """Generate odo debug image — digit slots, per-digit conf, edge projection."""
    import cv2
    import numpy as np
    from water_meter.core.common import (
        REFERENCE_CROP_W, DIGIT_SLOTS,
    )

    # Extract all row data inside the session (prevents detached instance errors)
    row_data = {}
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404, detail="Row not found")
        if not row.odo_crop_file:
            raise HTTPException(status_code=404, detail="No odo crop available")
        row_data = {
            "odo_crop_file": row.odo_crop_file,
            "digits": row.digits,
            "odo_reading": row.odo_reading,
            "odo_confidence": row.odo_confidence,
            "odo_pos5": row.odo_pos5,
            "status": row.status,
            "needle_deg": row.needle_deg,
            "notes_raw": row.notes,
        }

    _regenerate_odo_crop(image_name, row_data)
    crop_path = os.path.join(PROC_DIR, row_data["odo_crop_file"])

    # Output path — replace / with _ to keep a flat filename
    safe_name = row_data['odo_crop_file'].replace('/', '_')
    out_name = f"odo_debug_{safe_name}"
    out_path = os.path.join(DEBUG_DIR, out_name)

    if os.path.exists(out_path):
        return {"debug_image": out_name, "cached": True}

    # Parse notes
    notes_data = {}
    if row_data.get("notes_raw"):
        try:
            notes_data = json.loads(row_data["notes_raw"]) if isinstance(row_data["notes_raw"], str) else row_data["notes_raw"]
        except (json.JSONDecodeError, TypeError):
            pass

    # Load crop and build debug overlay
    img = cv2.imread(crop_path)
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to read odo crop")
    crop_h, crop_w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Slot boundaries ---
    original_slots = get_digit_slots(crop_w)
    refined_slots = refine_digit_slots(gray, original_slots)

    # --- Edge projection (Sobel X) ---
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    vproj = np.sum(np.abs(sobel_x), axis=0)
    vmax = vproj.max() or 1

    # Build a taller canvas: crop on top, edge projection + annotations below
    proj_h = 50
    info_h = 70
    total_h = crop_h + proj_h + info_h
    canvas = np.zeros((total_h, crop_w, 3), dtype=np.uint8)
    canvas[:crop_h, :] = img

    # Draw digit slots on the crop area
    for idx, (x1, x2) in enumerate(original_slots):
        cv2.rectangle(canvas, (x1, 2), (x2, crop_h - 3),
                      DIGIT_COLORS[idx], 2)
        cx = (x1 + x2) // 2
        cv2.putText(canvas, f"d{idx}", (cx - 10, crop_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, DIGIT_COLORS[idx], 1)

    # Draw refined slots as thin outlines when they differ
    for idx, (x1, x2) in enumerate(refined_slots):
        if x1 != original_slots[idx][0] or x2 != original_slots[idx][1]:
            col = tuple(min(255, c + 80) for c in DIGIT_COLORS[idx])
            cv2.rectangle(canvas, (x1, 2), (x2, crop_h - 3), col, 1)

    # --- Edge projection bar ---
    y0 = crop_h
    for x in range(crop_w):
        yh = int((vproj[x] / vmax) * (proj_h - 2))
        cv2.line(canvas, (x, y0 + proj_h), (x, y0 + proj_h - yh),
                 (0, 255, 255), 1)

    # Mark edge peaks on projection
    edge_peaks = []
    strong = np.where(vproj > vmax * 0.25)[0]
    if len(strong) > 0:
        groups = []
        cur = [strong[0]]
        for i in range(1, len(strong)):
            if strong[i] - strong[i - 1] <= 3:
                cur.append(strong[i])
            else:
                groups.append(int(np.mean(cur)))
                cur = [strong[i]]
        groups.append(int(np.mean(cur)))
        edge_peaks = groups
    for ex in edge_peaks:
        cv2.circle(canvas, (ex, y0 + proj_h // 2), 3, (0, 255, 0), -1)

    # --- Info bar: per-digit confidences + reading ---
    info_y = crop_h + proj_h
    pos_confs = notes_data.get("pos_confs", [])
    pos_digits_list = notes_data.get("pos_digits", [])

    # Per-digit conf text
    conf_parts = []
    for pi in range(6):
        d = pos_digits_list[pi] if pi < len(pos_digits_list) else None
        c = pos_confs[pi] if pi < len(pos_confs) else 0
        ds = str(d) if d is not None else "?"
        conf_parts.append(f"[{pi}]:{ds}({c:.2f})")
    conf_text = "  ".join(conf_parts)
    cv2.putText(canvas, conf_text, (8, info_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1)

    # Reading line
    digits_str = row_data.get("digits") or "?"
    reading_val = row_data.get("odo_reading")
    reading_text = f"Digits: {digits_str}  Reading: {reading_val if reading_val else 'N/A'}  Conf: {row_data.get('odo_confidence') or 'N/A'}"
    cv2.putText(canvas, reading_text, (8, info_y + 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # Pos5 source
    pos5_source = notes_data.get("pos5_source", "?")
    status_text = f"Status: {row_data.get('status','?')}  Pos5: {row_data.get('odo_pos5')}@{pos5_source}  Needle: {row_data.get('needle_deg')}"
    cv2.putText(canvas, status_text, (8, info_y + 62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1)

    cv2.imwrite(out_path, canvas)
    return {"debug_image": out_name, "cached": False}


@router.post("/api/decode_debug/{image_name}")
async def api_decode_debug(image_name: str):
    """Full decode debug — returns per-candidate score matrix + composite image.

    Runs the full decode_odo pipeline on this frame's odo crop but captures
    ALL candidate scores for every digit position, including templates that
    were NOT chosen.  Returns JSON with the score matrix and saves a
    composite debug image to DEBUG_DIR.
    """
    import cv2
    from water_meter.core.common import (
        debug_decode_crop, REFERENCE_CROP_W, DIGIT_SLOTS,
    )
    from water_meter.core.decode_odo import (
        load_pos5_templates, load_pos_static_digit_templates,
    )

    # Extract all row data inside the session
    row_data = {}
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404, detail="Row not found")
        if not row.odo_crop_file:
            raise HTTPException(status_code=404, detail="No odo crop available")
        row_data = {
            "odo_crop_file": row.odo_crop_file,
            "digits": row.digits,
            "odo_reading": row.odo_reading,
            "odo_confidence": row.odo_confidence,
            "status": row.status,
        }

    _regenerate_odo_crop(image_name, row_data)
    crop_path = os.path.join(PROC_DIR, row_data["odo_crop_file"])

    # Load template banks
    pos5_bank = load_pos5_templates(TEMPLATE_DIR)
    static_banks = []
    for p in range(5):
        static_banks.append(load_pos_static_digit_templates(TEMPLATE_DIR, p))

    # Run full decode debug
    result = debug_decode_crop(crop_path, pos5_bank, static_banks)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Strip large base64 images from positions if response would be too heavy
    # The composite debug image already has them visually
    light_positions = []
    for p in result.get("positions", []):
        lp = {
            "position": p["position"],
            "slot": p.get("slot"),
            "chosen": p.get("chosen"),
            "npos": p.get("npos"),
            "pos5_source": p.get("pos5_source"),
        }
        if p["position"] == 5:
            # pos5: list of candidates
            lp["candidates"] = [
                {"digit": c.get("digit"), "npos": c.get("npos"),
                 "score": c.get("score")}
                for c in p.get("candidates", [])[:10]
            ]
        else:
            # static: dict of digit -> scores
            candidates_dict = {}
            for d_str, cdata in p.get("candidates", {}).items():
                candidates_dict[d_str] = {
                    "scores": cdata.get("scores", {}),
                }
            lp["candidates"] = candidates_dict
        light_positions.append(lp)

    return {
        "image_name": image_name,
        "digits": result.get("digits"),
        "reading": result.get("reading"),
        "confidence": result.get("confidence"),
        "npos": result.get("npos"),
        "positions": light_positions,
        "debug_image": result.get("debug_image"),
        "db_digits": row_data.get("digits"),
        "db_reading": row_data.get("odo_reading"),
        "db_confidence": row_data.get("odo_confidence"),
    }


@router.post("/api/pos5_bw_debug/{image_name}")
async def api_pos5_bw_debug(image_name: str):
    """Generate a B&W comparison image for pos5 digit.

    Extracts the pos5 digit box from the odo crop, binarizes it strictly
    (Otsu, no grey), and compares it side-by-side with all pos5 templates
    within NPOS_WINDOW — also binarized.  Shows raw NCC score per template.
    """
    import cv2
    import numpy as np
    from water_meter.core.common import (
        MATCH_THRESHOLD, load_pos5_templates,
    )

    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404, detail="Row not found")
        if not row.odo_crop_file:
            raise HTTPException(status_code=404, detail="No odo crop available")
        odo_crop_file = row.odo_crop_file
        npos = row.npos
        db_digits = row.digits

    crop_path = os.path.join(PROC_DIR, odo_crop_file)
    if not os.path.exists(crop_path):
        raise HTTPException(status_code=404, detail="Odo crop not found")

    img = cv2.imread(crop_path)
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to read odo crop")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    w = gray.shape[1]
    slots = get_digit_slots(w)
    slots = refine_digit_slots(gray, slots)
    x0, x1 = slots[5]
    box5 = gray[:, x0:x1]

    def to_bw(g):
        """Otsu binarize — digit strokes = white (255), background = black (0).
        No equalizeHist; the digit is already dark-on-light with good contrast."""
        blur = cv2.GaussianBlur(g, (5, 5), 0)
        _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return bw

    q_bw = to_bw(box5)

    pos5_bank = load_pos5_templates(TEMPLATE_DIR)

    # Gather templates within NPOS_WINDOW
    candidates = []
    for (d, tn), t in sorted(pos5_bank.items(), key=lambda kv: kv[0]):
        dist = min(abs(npos - tn), 100 - abs(npos - tn)) if npos is not None else 999
        if dist > NPOS_WINDOW:
            continue
        tr = cv2.resize(t, (box5.shape[1], box5.shape[0]))
        t_bw = to_bw(tr)
        s_ncc = float(cv2.matchTemplate(q_bw, t_bw, cv2.TM_CCOEFF_NORMED)[0][0])
        xor_px = int(np.count_nonzero(np.bitwise_xor(q_bw, t_bw)))
        xor_score = 1.0 - xor_px / q_bw.size
        candidates.append({
            "digit": d, "npos": tn, "dist": dist,
            "bw_ncc": round(s_ncc, 4),
            "xor_score": round(xor_score, 4), "xor_px": xor_px,
        })

    # Sort by best NCC
    candidates.sort(key=lambda c: c["bw_ncc"], reverse=True)

    # Build composite comparison image
    panel_w = box5.shape[1] + 10
    panel_h = box5.shape[0] + 40
    n_panels = len(candidates) + 1  # +1 for query
    canvas_w = n_panels * panel_w
    canvas_h = panel_h
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    # Draw query first
    qx = 0
    canvas[0:box5.shape[0], qx:qx + box5.shape[1]] = q_bw
    cv2.putText(canvas, "QUERY", (qx + 2, panel_h - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, 255, 1)

    # Draw each candidate
    for ci, cand in enumerate(candidates):
        cx = (ci + 1) * panel_w
        # Re-create the template BW
        for (d, tn), t in pos5_bank.items():
            if d == cand["digit"] and tn == cand["npos"]:
                tr = cv2.resize(t, (box5.shape[1], box5.shape[0]))
                t_bw = to_bw(tr)
                canvas[0:box5.shape[0], cx:cx + box5.shape[1]] = t_bw
                winner = ci == 0
                color = 255 if winner else 180
                label = f"d{d}n{tn:02d} NCC={cand['bw_ncc']:.3f}"
                if winner:
                    label += " BEST"
                cv2.putText(canvas, label, (cx + 2, panel_h - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.30, color, 1)
                break

    # Save
    safe_name = image_name.rsplit(".", 1)[0]
    out_name = f"pos5_bw_debug_{safe_name}.png"
    out_path = os.path.join(DEBUG_DIR, out_name)
    cv2.imwrite(out_path, canvas)

    return {
        "debug_image": out_name,
        "npos": npos,
        "db_digits": db_digits,
        "slot": [x0, x1],
        "candidates": candidates,
        "total_pixels": box5.size,
    }
