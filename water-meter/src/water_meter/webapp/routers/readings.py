"""Read-only endpoints for browsing readings and navigation."""

from datetime import datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, text

from water_meter.core.db import MeterReading, get_session

from ..utils import find_source_image, row_to_dict

router = APIRouter()

# Consecutive frames closer than this are treated as one "set" when grouping.
GROUP_GAP = timedelta(seconds=300)


@router.get("/api/readings")
def api_readings(
    page: int = Query(1, ge=1), per_page: int = Query(100, ge=1, le=1000),
    status: str = Query(""), min_conf: Optional[float] = Query(None),
    max_conf: Optional[float] = Query(None),
    npos_min: Optional[int] = Query(None), npos_max: Optional[int] = Query(None),
    order: str = Query("desc"), search: str = Query(""),
    flagged: int = Query(0), needs_review: int = Query(0),
    preserve: str = Query(""), run_position: str = Query(""),
    has_image: int = Query(0),
    grouped: int = Query(0),
    date: str = Query("", description="Filter to a single day YYYY-MM-DD"),
    spike: int = Query(0, description="Only rows >1.0 m³ above the day's median (requires date)"),
):
    with get_session() as s:
        q = s.query(MeterReading)
        if status: q = q.filter(MeterReading.status == status)
        if min_conf is not None: q = q.filter(MeterReading.odo_confidence >= min_conf)
        if max_conf is not None: q = q.filter(MeterReading.odo_confidence <= max_conf)
        if npos_min is not None: q = q.filter(MeterReading.npos >= npos_min)
        if npos_max is not None: q = q.filter(MeterReading.npos <= npos_max)
        if search: q = q.filter(MeterReading.image_name.like(f"%{search}%"))
        if date:
            try:
                day = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
            start = datetime.combine(day, time.min)
            end = datetime.combine(day + timedelta(days=1), time.min)
            q = q.filter(MeterReading.capture_ts >= start, MeterReading.capture_ts < end)
            if spike:
                # Only rows whose reading runs >1.0 m³ above the day's median.
                med = (
                    s.query(func.percentile_cont(0.5).within_group(MeterReading.odo_published.asc()))
                    .filter(MeterReading.capture_ts >= start, MeterReading.capture_ts < end,
                            MeterReading.odo_published.isnot(None))
                    .scalar_subquery()
                )
                q = q.filter(MeterReading.odo_published > (med + 1.0))
        if flagged: q = q.filter(MeterReading.notes.like('%"monotonicity_flag"%'))
        if needs_review: q = q.filter(
            (MeterReading.notes.like('%"needs_review"%')
             | (MeterReading.status == "FAIL")),
            MeterReading.odo_confidence < 1.0,
        )
        if preserve: q = q.filter(MeterReading.notes.like(f'%"preserve":"{preserve}"%'))
        if run_position: q = q.filter(MeterReading.notes.like(f'%"run_position":"{run_position}"%'))
        q = q.order_by(MeterReading.capture_ts.asc() if order == "asc" else MeterReading.capture_ts.desc())

        if grouped:
            # Collapse consecutive runs (frames <= GROUP_GAP apart) into the
            # FIRST frame of each set — so "needs review" shows one row per bad
            # stretch instead of every 15s frame.  Uses a LAG window over the
            # filtered set in chronological order.
            base = q.order_by(MeterReading.capture_ts.asc()).subquery()
            prev_ts = func.lag(base.c.capture_ts).over(order_by=base.c.capture_ts)
            starts = (
                s.query(base.c.image_name)
                .add_columns((base.c.capture_ts - prev_ts).label("gap"))
                .subquery()
            )
            q = (
                s.query(MeterReading)
                .join(starts, MeterReading.image_name == starts.c.image_name)
                .filter(or_(starts.c.gap.is_(None), starts.c.gap > GROUP_GAP))
                .order_by(MeterReading.capture_ts.asc())
            )

        # Fetch a generous window — the has_image filter runs client-side
        # in Python, so we need enough rows to fill the requested page
        # after filtering.
        fetch_limit = per_page * 3 if has_image else per_page
        rows = q.limit(fetch_limit).offset((page - 1) * per_page).all()
        rows_dicts = [row_to_dict(r) for r in rows]
        if has_image:
            rows_dicts = [r for r in rows_dicts if find_source_image(r["image_name"])]
        # Count is approximate when has_image filtering is active
        total = q.count()
    return {"page": page, "per_page": per_page, "total": total, "readings": rows_dicts}


@router.get("/api/reading/{image_name}")
def api_reading(image_name: str):
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None: raise HTTPException(status_code=404)
        return row_to_dict(row)


@router.get("/api/reading/{image_name}/adjacent")
def api_adjacent(image_name: str):
    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None: raise HTTPException(status_code=404)
        prev_d = next_d = None
        if row.capture_ts:
            prev_row = s.query(MeterReading).filter(MeterReading.capture_ts < row.capture_ts).order_by(MeterReading.capture_ts.desc()).first()
            next_row = s.query(MeterReading).filter(MeterReading.capture_ts > row.capture_ts).order_by(MeterReading.capture_ts.asc()).first()
            prev_d = row_to_dict(prev_row) if prev_row else None
            next_d = row_to_dict(next_row) if next_row else None
        rd = row_to_dict(row)
    return {"reading": rd, "prev": prev_d, "next": next_d}


@router.get("/api/navigate/{image_name:path}")
def api_navigate(image_name: str, dir: str = Query("next"),
                 by: str = Query("seq")):
    """Get next/prev image by seq (default), day, hour, or rotation.

    Returns {image_name, capture_ts, npos, digits, dr_best} or 404.
    """
    if by not in ("seq", "day", "hour", "rotation"):
        raise HTTPException(status_code=400, detail="by must be seq, day, hour, or rotation")
    if dir not in ("prev", "next"):
        raise HTTPException(status_code=400, detail="dir must be prev or next")

    with get_session() as s:
        row = s.get(MeterReading, image_name)
        if row is None or row.capture_ts is None:
            raise HTTPException(status_code=404)

        if by == "seq":
            if dir == "prev":
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts < row.capture_ts
                ).order_by(MeterReading.capture_ts.desc()).first()
            else:
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts > row.capture_ts
                ).order_by(MeterReading.capture_ts.asc()).first()

        elif by == "day":
            day_start = row.capture_ts.replace(hour=0, minute=0, second=0)
            if dir == "prev":
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts < day_start,
                    MeterReading.status == "OK",
                ).order_by(MeterReading.capture_ts.desc()).first()
            else:
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts >= (day_start + __import__('datetime').timedelta(days=1)),
                    MeterReading.status == "OK",
                ).order_by(MeterReading.capture_ts.asc()).first()

        elif by == "hour":
            hour_start = row.capture_ts.replace(minute=0, second=0)
            if dir == "prev":
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts < hour_start,
                    MeterReading.status == "OK",
                ).order_by(MeterReading.capture_ts.desc()).first()
            else:
                from datetime import timedelta
                target = s.query(MeterReading).filter(
                    MeterReading.capture_ts >= hour_start + timedelta(hours=1),
                    MeterReading.status == "OK",
                ).order_by(MeterReading.capture_ts.asc()).first()

        elif by == "rotation":
            if dir == "prev":
                target = s.query(MeterReading).filter(
                    MeterReading.dr_best == True,
                    MeterReading.dr_cycle < (row.dr_cycle or 999999),
                ).order_by(MeterReading.dr_cycle.desc()).first()
            else:
                target = s.query(MeterReading).filter(
                    MeterReading.dr_best == True,
                    MeterReading.dr_cycle > (row.dr_cycle or 0),
                ).order_by(MeterReading.dr_cycle.asc()).first()

        if target is None:
            raise HTTPException(status_code=404, detail="No more images in that direction")

        return {
            "image_name": target.image_name,
            "capture_ts": target.capture_ts.isoformat() if target.capture_ts else None,
            "npos": target.dm_npos or target.npos,
            "digits": target.do_digits or target.digits,
            "dr_best": target.dr_best,
            "dr_cycle": target.dr_cycle,
            "reading": target.cn_published or target.odo_published,
        }


@router.get("/api/navigate_by_reading")
def api_navigate_by_reading(
    value: float = Query(...),
    mode: str = Query("first"),
):
    """Jump to a reading near a target meter value (used for manual corrections).

    Searches the chronological series of published readings (odo_published,
    falling back to odo_reading when null):

      mode="first" — the reading immediately BEFORE the first reading whose
          value exceeds ``value``.  (First value > target, back up 1 row.)
          This is the last reading at-or-below ``value`` before the crossing.

      mode="last"  — the reading immediately AFTER the last reading at-or-below
          ``value``.  (Last time the value was seen, forward 1 row.)
          This is the first reading that exceeds ``value`` after the value run.

    Returns the same navigation payload as /api/navigate/{image_name}.
    """
    if mode not in ("first", "last"):
        raise HTTPException(status_code=400, detail="mode must be first or last")

    # Boundary search done in SQL via a row_number window — avoids loading all
    # rows into Python, which would slow down as the table grows (~5.7k rows/day).
    value_col = "COALESCE(odo_published, odo_reading)"
    with get_session() as s:
        if mode == "first":
            row = s.execute(text(f"""
                WITH v AS (
                    SELECT image_name, capture_ts, npos, digits, dm_npos, do_digits,
                           dr_best, dr_cycle, cn_published, odo_published,
                           {value_col} AS val,
                           ROW_NUMBER() OVER (ORDER BY capture_ts ASC) AS rn
                    FROM water_meter.meter_readings
                    WHERE capture_ts IS NOT NULL
                      AND (odo_published IS NOT NULL OR odo_reading IS NOT NULL)
                ),
                cross_ AS (
                    SELECT rn FROM v WHERE val > :value ORDER BY rn ASC LIMIT 1
                )
                SELECT v.* FROM v, cross_
                WHERE v.rn = GREATEST(cross_.rn - 1, 1)
            """), {"value": value}).mappings().first()
            if row is None:
                raise HTTPException(status_code=404, detail=f"No reading above {value}")
        else:  # "last"
            row = s.execute(text(f"""
                WITH v AS (
                    SELECT image_name, capture_ts, npos, digits, dm_npos, do_digits,
                           dr_best, dr_cycle, cn_published, odo_published,
                           {value_col} AS val,
                           ROW_NUMBER() OVER (ORDER BY capture_ts ASC) AS rn
                    FROM water_meter.meter_readings
                    WHERE capture_ts IS NOT NULL
                      AND (odo_published IS NOT NULL OR odo_reading IS NOT NULL)
                ),
                last_ AS (
                    SELECT MAX(rn) AS rn FROM v WHERE val <= :value
                )
                SELECT v.* FROM v, last_
                WHERE last_.rn IS NOT NULL
                  AND v.rn = LEAST(last_.rn + 1, (SELECT MAX(rn) FROM v))
            """), {"value": value}).mappings().first()
            if row is None:
                raise HTTPException(status_code=404, detail=f"No reading at or below {value}")

        result = {
            "image_name": row["image_name"],
            "capture_ts": row["capture_ts"].isoformat() if row["capture_ts"] else None,
            "npos": row["dm_npos"] if row["dm_npos"] is not None else row["npos"],
            "digits": row["do_digits"] if row["do_digits"] is not None else row["digits"],
            "dr_best": row["dr_best"],
            "dr_cycle": row["dr_cycle"],
            "reading": row["cn_published"] if row["cn_published"] is not None else row["odo_published"],
        }

    return {**result, "mode": mode, "target_value": value}


@router.get("/api/needs_review_daily")
def api_needs_review_daily():
    """Per-day reading summary to spot spike days (value-based, not flag-based).

    For every day, the published-reading min/max/median across ALL frames.  A
    day is flagged as a spike when its max reading is more than 1.0 m³ above
    that day's median — a stretch of readings running well above the normal
    line for the day.  Clicking a spike day drills into those frames.
    """
    with get_session() as s:
        rows = (
            s.query(MeterReading.capture_ts, MeterReading.odo_published)
            .filter(MeterReading.capture_ts.isnot(None))
            .filter(MeterReading.odo_published.isnot(None))
            .order_by(MeterReading.capture_ts.asc())
            .all()
        )

    days = {}
    for ts, pub in rows:
        d = ts.date()
        days.setdefault(d, {"date": d.isoformat(), "vals": []})["vals"].append(float(pub))

    out = []
    for d in sorted(days):
        vals = sorted(days[d]["vals"])
        med = vals[len(vals) // 2]
        out.append({
            "date": d.isoformat(),
            "n": len(vals),
            "min": vals[0],
            "max": vals[-1],
            "median": med,
            "spike": vals[-1] - med > 1.0,
        })
    return {"days": out}
