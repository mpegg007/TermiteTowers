"""Stats, usage, and rollover endpoints (aggregation queries)."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func

from water_meter.core.db import MeterReading, get_session

from ..utils import row_to_dict

router = APIRouter()


def _hourly_buckets(s, day):
    """Chronologically-ordered per-hour buckets for a single calendar date.

    Returns dict hour -> {first, last, count, first_image, last_image}.
    Only OK rows with odo_published are considered (same rules as the
    daily/hourly usage figures).
    """
    from datetime import datetime, time, timedelta
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    rows = (
        s.query(MeterReading.capture_ts, MeterReading.image_name, MeterReading.odo_published)
        .filter(MeterReading.capture_ts >= start, MeterReading.capture_ts < end)
        .filter(MeterReading.status == "OK")
        .filter(MeterReading.odo_published.isnot(None))
        .order_by(MeterReading.capture_ts.asc())
        .all()
    )
    buckets: dict = {}
    for ts, img, reading in rows:
        h = ts.hour
        val = float(reading)
        b = buckets.get(h)
        if b is None:
            buckets[h] = {"first": val, "last": val, "count": 1,
                          "first_image": img, "last_image": img}
        else:
            b["last"] = val
            b["count"] += 1
            b["last_image"] = img
    return buckets


def _hourly_usage(buckets):
    """Turn hour buckets into a 24-entry list with usage deltas.

    usage_l for hour h = last(h) - last(h-1); the first active hour of the
    day has no prior baseline so usage_l is None.  Non-monotonic deltas
    (data artifacts) report None rather than negative usage.
    """
    out = []
    prev_last = None
    for h in range(24):
        b = buckets.get(h)
        if b is None:
            out.append({
                "hour": h, "reading_m3": None, "usage_l": None,
                "image_count": 0, "first_image": None, "last_image": None,
            })
            continue
        usage_l = None
        if prev_last is not None and b["last"] >= prev_last:
            usage_l = round((b["last"] - prev_last) * 1000, 1)
        out.append({
            "hour": h,
            "reading_m3": b["last"],
            "usage_l": usage_l,
            "image_count": b["count"],
            "first_image": b["first_image"],
            "last_image": b["last_image"],
        })
        prev_last = b["last"]
    return out


@router.get("/api/stats")
def api_stats():
    with get_session() as s:
        def _cnt(filt=None):
            q = s.query(func.count(MeterReading.image_name))
            return q.filter(filt).scalar() if filt is not None else q.scalar()
        total = _cnt()
        ok_c = _cnt(MeterReading.status == "OK")
        anomaly_c = _cnt(MeterReading.status == "ANOMALY")
        fail_c = _cnt(MeterReading.status == "FAIL")
        has_odo = _cnt(MeterReading.odo_confidence.isnot(None))
        high_conf = _cnt(MeterReading.odo_confidence >= 0.80) if has_odo else 0
        manual = _cnt(MeterReading.odo_confidence == 1.0)
        latest_row = s.query(MeterReading).filter(MeterReading.odo_reading.isnot(None)).order_by(MeterReading.capture_ts.desc()).first()
        latest_reading = float(latest_row.odo_reading) if latest_row is not None and latest_row.odo_reading is not None else None
        latest_ts = latest_row.capture_ts.isoformat() if latest_row is not None and latest_row.capture_ts is not None else None
        avg_conf = s.query(func.avg(MeterReading.odo_confidence)).filter(MeterReading.odo_confidence.isnot(None)).scalar()
    return {
        "total": total, "ok": ok_c, "anomaly": anomaly_c, "fail": fail_c,
        "has_odo_reading": has_odo, "high_confidence": high_conf, "manual_corrected": manual,
        "latest_reading": latest_reading,
        "latest_ts": latest_ts,
        "avg_confidence": round(float(avg_conf), 4) if avg_conf else None,
    }


@router.get("/api/usage")
def api_usage():
    """Return daily/hourly usage statistics in litres.

    Uses odo_published (bucket 4) — the authoritative reading that is
    COALESCE(odo_manual, odo_needle).  Computes inter-period deltas
    from the *last* chronological reading in each period, not min/max.

    Returns:
        daily_30: [{date, reading_m3, usage_l}] — last 30 days
        last_month_usage_l: total litres used last calendar month
        this_month_usage_l: total litres used so far this calendar month
        hourly_today: [{hour, reading_m3, usage_l, image_count}] — all 24 hours
    """
    from datetime import date, timedelta

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    with get_session() as s:
        # ── Helper: chronologically LAST reading per day ──
        def _daily_last(start_dt, end_dt=None):
            q = (
                s.query(MeterReading.capture_ts, MeterReading.odo_published)
                .filter(MeterReading.capture_ts >= start_dt)
                .filter(MeterReading.status == "OK")
                .filter(MeterReading.odo_published.isnot(None))
                .order_by(MeterReading.capture_ts.asc())
            )
            if end_dt is not None:
                q = q.filter(MeterReading.capture_ts < end_dt)
            rows = q.all()
            out: dict = {}
            for ts, reading in rows:
                out[ts.strftime("%Y-%m-%d")] = float(reading)
            return out

        # ── Daily usage (last 30 days) ──
        # Pad with one extra day of history for proper first-day delta
        lookahead = thirty_days_ago - timedelta(days=1)
        daily_last = _daily_last(lookahead)
        MAX_DAILY_DELTA_L = 20000  # cap: anything > 20 m³/day is a data artifact
        daily_30 = []
        prev_reading = None
        for d in sorted(daily_last.keys()):
            reading = daily_last[d]
            usage_l = None
            if prev_reading is not None and reading is not None and prev_reading is not None:
                delta = reading - prev_reading
                delta_l = delta * 1000
                if 0 <= delta_l <= MAX_DAILY_DELTA_L:
                    usage_l = round(delta_l, 1)
            daily_30.append({
                "date": d,
                "reading_m3": reading,
                "usage_l": usage_l,
            })
            prev_reading = reading
        # Trim the extra day we added for baseline
        if daily_30 and daily_30[0]["date"] < thirty_days_ago.isoformat():
            daily_30 = daily_30[1:]

        # ── Last month total ──
        # Sum day-over-day deltas within the calendar month, capped at
        # MAX_DAILY_DELTA_L to exclude needle-integer-jump artifacts.
        first_of_this_month = today.replace(day=1)
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        lm_baseline = _daily_last(last_month_start - timedelta(days=1), first_of_this_month)
        last_month_usage_l = None
        if len(lm_baseline) >= 2:
            sorted_keys = sorted(lm_baseline.keys())
            total_l = 0.0
            prev = lm_baseline[sorted_keys[0]]
            for d in sorted_keys[1:]:
                val = lm_baseline[d]
                if val is not None and prev is not None:
                    delta_l = (val - prev) * 1000
                    if 0 <= delta_l <= MAX_DAILY_DELTA_L:
                        total_l += delta_l
                prev = val
            if total_l > 0:
                last_month_usage_l = round(total_l, 1)

        # ── This month total ──
        tm_baseline = _daily_last(first_of_this_month - timedelta(days=1))
        this_month_usage_l = None
        if len(tm_baseline) >= 2:
            sorted_keys = sorted(tm_baseline.keys())
            total_l = 0.0
            prev = tm_baseline[sorted_keys[0]]
            for d in sorted_keys[1:]:
                val = tm_baseline[d]
                if val is not None and prev is not None:
                    delta_l = (val - prev) * 1000
                    if 0 <= delta_l <= MAX_DAILY_DELTA_L:
                        total_l += delta_l
                prev = val
            if total_l > 0:
                this_month_usage_l = round(total_l, 1)

        # ── Today's hourly usage ──
        today_buckets = _hourly_buckets(s, today)
        hourly_today = _hourly_usage(today_buckets)
        today_first = (today_buckets[min(today_buckets)]["first_image"]
                       if today_buckets else None)
        today_last = (today_buckets[max(today_buckets)]["last_image"]
                      if today_buckets else None)

    return {
        "daily_30": daily_30,
        "last_month_usage_l": last_month_usage_l,
        "this_month_usage_l": this_month_usage_l,
        "hourly_today": hourly_today,
        "first_image": today_first,
        "last_image": today_last,
    }


@router.get("/api/usage/hourly")
def api_usage_hourly(date: str = Query(..., description="Date YYYY-MM-DD")):
    """Per-hour usage + first/last image for a single date.

    Used by the Usage page when a daily bar is clicked so the lower
    hourly chart reflects the selected date instead of always "today".
    """
    from datetime import datetime, timedelta
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    with get_session() as s:
        buckets = _hourly_buckets(s, day)
        hourly = _hourly_usage(buckets)
        first_image = (buckets[min(buckets)]["first_image"] if buckets else None)
        last_image = (buckets[max(buckets)]["last_image"] if buckets else None)
    return {
        "date": date,
        "first_image": first_image,
        "last_image": last_image,
        "hourly": hourly,
    }


@router.get("/api/rollovers")
def api_rollovers(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=1000),
):
    """Return one frame per needle rollover (npos crosses from >90 to <10).

    These are the best frames for manual verification — the odometer digits
    are fully settled and the needle position makes reading unambiguous.
    """
    with get_session() as s:
        # Window function: previous npos for each row
        subq = (
            s.query(
                MeterReading.image_name,
                MeterReading.npos,
                func.lag(MeterReading.npos)
                .over(order_by=MeterReading.capture_ts.asc())
                .label("prev_npos"),
            )
            .filter(MeterReading.status == "OK")
            .subquery()
        )
        q = (
            s.query(MeterReading)
            .join(subq, MeterReading.image_name == subq.c.image_name)
            .filter(subq.c.prev_npos.isnot(None))
            .filter(subq.c.prev_npos > 90)
            .filter(MeterReading.npos >= 0)
            .filter(MeterReading.npos <= 3)
            .order_by(MeterReading.capture_ts.desc())
        )
        total = q.count()
        row_objs = q.limit(per_page).offset((page - 1) * per_page).all()
        rows_dicts = [row_to_dict(r) for r in row_objs]
    return {"page": page, "per_page": per_page, "total": total, "readings": rows_dicts}
