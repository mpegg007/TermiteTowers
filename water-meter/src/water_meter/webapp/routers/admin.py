"""Write endpoints — manual correction, confirmation, status, reprocess, recalc."""

import glob
import json
import os
import re
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from water_meter.core import calc_needle_readings as calc_mod
from water_meter.core.common import PROC_DIR, TEMPLATE_DIR
from water_meter.core.db import MeterReading, get_session
from water_meter.core.decode_odo import (
    process_crop, load_pos5_templates, load_pos_static_digit_templates,
)

from ..utils import find_source_image, run_decode_meter

router = APIRouter()

# ── Recalc (calc_needle_readings) trigger — runs in a background thread so the
#    webapp stays responsive; poll /api/recalc/status for progress. ──────────
_recalc_state = {
    "running": False, "done": False, "from_date": None,
    "started_at": None, "finished_at": None, "result": None, "error": None,
}


def _run_recalc(from_date: str) -> None:
    _recalc_state["running"] = True
    _recalc_state["done"] = False
    _recalc_state["error"] = None
    try:
        total, updated = calc_mod.calc_needle_readings(dry_run=False, from_date=from_date)
        _recalc_state["result"] = {"total": total, "updated_needle": updated}
    except Exception as exc:  # pragma: no cover - defensive
        _recalc_state["error"] = str(exc)
    finally:
        _recalc_state["running"] = False
        _recalc_state["done"] = True
        _recalc_state["finished_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/api/recalc")
def api_recalc(from_date: str = Query("20260719", description="Recalc from YYYYMMDD")):
    if _recalc_state["running"]:
        return {"running": True, "message": "A recalc is already in progress"}
    if not re.match(r"^\d{8}$", from_date):
        raise HTTPException(status_code=400, detail="from_date must be YYYYMMDD")
    thread = threading.Thread(target=_run_recalc, args=(from_date,), daemon=True)
    thread.start()
    _recalc_state["from_date"] = from_date
    _recalc_state["started_at"] = datetime.now(timezone.utc).isoformat()
    return {"running": True, "from_date": from_date, "message": "Recalc started"}


@router.get("/api/recalc/status")
def api_recalc_status():
    return {
        "running": _recalc_state["running"],
        "done": _recalc_state["done"],
        "from_date": _recalc_state["from_date"],
        "started_at": _recalc_state["started_at"],
        "finished_at": _recalc_state["finished_at"],
        "result": _recalc_state["result"],
        "error": _recalc_state["error"],
    }


# ── Digits <-> reading reconciliation (rollover-aware) ──────────────────────
# The pos5 (tenths) odometer drum starts showing the NEXT digit slightly before
# the wheel engages.  At needle npos >= NPOS_ROLLOVER the digit you see is the
# "next" one, so the true tenths is one less.  This keeps manually-entered
# digits and readings consistent with the needle position.
NPOS_ROLLOVER = 85


def _normalize_digits(raw) -> str:
    """Normalize a digits string to exactly 6 chars (leading zeros)."""
    d = re.sub(r"[^0-9]", "", str(raw))
    if not d:
        raise HTTPException(status_code=400, detail="Invalid digits")
    if len(d) > 6:
        d = d[-6:]
    return d.zfill(6)


def _reading_from_digits(digits6: str, npos) -> float:
    """reading = integer + true_tenths/10 + npos/1000.

    At npos >= NPOS_ROLLOVER the drum is showing the NEXT tenths digit, so the
    true tenths is one less than the shown digit.
    """
    integer = int(digits6[:5])
    shown_tenths = int(digits6[5])
    true_tenths = (shown_tenths - 1) % 10 if (npos is not None and npos >= NPOS_ROLLOVER) else shown_tenths
    return integer + true_tenths / 10.0 + (npos or 0) / 1000.0


def _digits_from_reading(reading: float, npos) -> str:
    """Inverse of _reading_from_digits: reading -> 6-char digits string.

    Works in thousandths to avoid float boundary issues (e.g. 3542.7 stored as
    3542.69999... must still give tenths 7).
    """
    integer = int(reading)
    thousandths = int(round((reading - integer) * 1000))
    true_tenths = (thousandths // 100) % 10
    shown_tenths = (true_tenths + 1) % 10 if (npos is not None and npos >= NPOS_ROLLOVER) else true_tenths
    return f"{integer:05d}{shown_tenths}"


@router.post("/api/reading/{image_name}/correct")
async def api_correct(image_name: str, request: Request):
    data = await request.json()
    corrected_reading = data.get("reading")
    corrected_digits = data.get("digits")
    if corrected_reading is None and corrected_digits is None:
        raise HTTPException(status_code=400, detail="reading or digits required")
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None: raise HTTPException(status_code=404)
        npos = row.npos
        if corrected_reading is not None:
            try:
                val = float(corrected_reading)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Invalid reading value")
            # Derive the (rollover-aware) digits from the reading.
            digits_str = _digits_from_reading(val, npos)
            row.digits = digits_str
            row.do_digits = digits_str
            corrected_digits = digits_str
            row.reading = val
            row.odo_reading = val
            row.odo_published = val
            row.odo_manual = val
            row.cn_manual = val
            row.cn_published = val
            row.do_reading = val
        else:  # only digits provided — compute the reading from digits + needle
            digits_str = _normalize_digits(corrected_digits)
            val = _reading_from_digits(digits_str, npos)
            row.digits = digits_str
            row.do_digits = digits_str
            corrected_digits = digits_str
            row.reading = val
            row.odo_reading = val
            row.odo_published = val
            row.odo_manual = val
            row.cn_manual = val
            row.cn_published = val
            row.do_reading = val
        row.odo_confidence = 1.0
        row.do_confidence = 1.0
        notes_data = {}
        if row.notes:
            try: notes_data = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
            except (json.JSONDecodeError, TypeError): notes_data = {}
        notes_data.pop("needs_review", None)
        notes_data.pop("monotonicity_flag", None)
        notes_data.pop("calc_reject", None)
        notes_data["source"] = "manual"
        notes_data["corrected_at"] = datetime.now(timezone.utc).isoformat()
        # Parse digits string into pos_digits array so update_templates can use it.
        # Only set confidence to 1.0 for positions that were actually changed —
        # preserve existing confidence for positions that matched correctly.
        if corrected_digits and len(corrected_digits) == 6:
            parsed = [int(c) if c.isdigit() else None for c in corrected_digits]
            old_pos_confs = notes_data.get("pos_confs", [0.0] * 6)
            old_pos_digits = notes_data.get("pos_digits", [None] * 6)
            new_confs = []
            for pi in range(6):
                if (pi < len(old_pos_digits) and old_pos_digits[pi] is not None
                        and old_pos_digits[pi] == parsed[pi]):
                    # This position was already correct — keep old confidence
                    new_confs.append(old_pos_confs[pi] if pi < len(old_pos_confs) else 0.0)
                else:
                    # This position was corrected — mark as verified
                    new_confs.append(1.0)
            notes_data["pos_digits"] = parsed
            notes_data["pos_confs"] = new_confs
        row.notes = json.dumps(notes_data)
        s.commit()
    return {"status": "ok", "image_name": image_name}


@router.post("/api/reading/{image_name}/confirm")
def api_confirm(image_name: str):
    """Mark the current auto-decoded reading as trusted (confidence=1.0).

    Unlike /correct, this doesn't change the reading value — it just
    promotes the existing auto decode to manual-trust level.
    """
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404, detail="Reading not found")
        row.odo_confidence = 1.0
        notes_data = {}
        if row.notes:
            try:
                notes_data = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
            except (json.JSONDecodeError, TypeError):
                notes_data = {}
        notes_data["source"] = "confirmed"
        notes_data["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        row.notes = json.dumps(notes_data)
        s.commit()
    return {"status": "ok", "image_name": image_name}


@router.post("/api/reading/{image_name}/status")
async def api_set_status(image_name: str, request: Request):
    """Change the status of a reading (e.g. ANOMALY → OK, or vice versa)."""
    data = await request.json()
    new_status = data.get("status")
    if new_status not in ("OK", "ANOMALY", "FAIL"):
        raise HTTPException(status_code=400, detail="status must be OK, ANOMALY, or FAIL")
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None:
            raise HTTPException(status_code=404)
        row.status = new_status
        # Update notes to track the change
        notes_data = {}
        if row.notes:
            try:
                notes_data = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
            except (json.JSONDecodeError, TypeError):
                notes_data = {}
        notes_data["status_changed_by"] = "webapp"
        notes_data["status_changed_at"] = datetime.now(timezone.utc).isoformat()
        row.notes = json.dumps(notes_data)
        s.commit()
    return {"status": "ok", "image_name": image_name, "new_status": new_status}


@router.post("/api/reprocess/{image_name}")
async def api_reprocess(image_name: str):
    """Re-run decode_meter + decode_odo on a single image and refresh DB."""
    src_path = find_source_image(image_name)
    if not src_path:
        raise HTTPException(status_code=404, detail="Source image not found")

    # Step 1: decode_meter (dial scan + odo crop)
    result = run_decode_meter(
        ["--input-image", src_path, "--dial-scan", "--odo-crop", "--no-move"])
    if result.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=f"decode_meter failed: {result.stderr[:200]}")

    # Step 2: decode_odo on the newly generated crop (run directly in-process)
    m = re.match(r"water_meter_(\d{8}_\d{6})", image_name)
    ts_tag = m.group(1) if m else ""
    crops = sorted(glob.glob(
        os.path.join(PROC_DIR, "**", f"odo_{ts_tag}_*.jpg"), recursive=True))
    if crops:
        crop_path = crops[-1]
        pos5_bank = load_pos5_templates(TEMPLATE_DIR)
        static_banks = []
        for p in range(5):
            static_banks.append(load_pos_static_digit_templates(TEMPLATE_DIR, p))

        r = process_crop(crop_path, pos5_bank, static_banks, debug=False)

        # Update DB row with decode results
        with get_session() as s:
            row = s.get(MeterReading, image_name)
            if row:
                new_crop_rel = os.path.relpath(crops[-1], PROC_DIR)
                row.odo_crop_file = new_crop_rel
                row.status = "OK"
                if r["digits"] is not None:
                    row.digits = r["digits"]
                if r["reading"] is not None:
                    row.odo_reading = float(r["reading"])
                row.odo_confidence = float(r["confidence"])
                row.odo_pos5 = int(r["pos5_digit"]) if r["pos5_digit"] is not None else None
                row.odo_pos5_conf = float(r["pos5_conf"])

                # Preserve n00_anchor in notes
                existing_notes = {}
                if row.notes:
                    try:
                        existing_notes = json.loads(row.notes) if isinstance(row.notes, str) else row.notes
                    except (json.JSONDecodeError, TypeError):
                        existing_notes = {}
                n00_preserved = existing_notes.get("n00_anchor", None)

                conf_data = {
                    "pos_confs": [float(c) for c in r.get("pos_confs", [])],
                    "pos_digits": [int(d) if d is not None else None for d in r.get("pos_digits", [])],
                    "pos5_source": r.get("pos5_source", "matched"),
                }
                if n00_preserved:
                    conf_data["n00_anchor"] = n00_preserved
                row.notes = json.dumps(conf_data)
                s.commit()

    return {"status": "ok", "image_name": image_name,
            "crop_generated": bool(crops),
            "debug_images": ["hub_dial_scan", "odo_crop"]}
