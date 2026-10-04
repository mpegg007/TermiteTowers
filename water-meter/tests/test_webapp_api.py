"""Smoke tests for the water meter webapp.

DB-dependent endpoints are skipped when PostgreSQL (ttdb_dev1) is unreachable,
so this suite is safe to run on a fresh checkout without local infra.
"""

import pytest

from fastapi.testclient import TestClient

from water_meter.webapp.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _db_available() -> bool:
    try:
        from sqlalchemy import text
        from water_meter.core.db import get_session
        with get_session() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def test_spa_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Water Meter" in resp.text or "water" in resp.text.lower()


def test_templates_endpoint(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"pos5", "static", "missing_pos5", "missing_static"}


@pytest.mark.skipif(not _db_available(), reason="PostgreSQL ttdb_dev1 not reachable")
def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body and "latest_reading" in body


@pytest.mark.skipif(not _db_available(), reason="PostgreSQL ttdb_dev1 not reachable")
def test_readings_endpoint(client):
    resp = client.get("/api/readings", params={"per_page": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "readings" in body and "total" in body


@pytest.mark.skipif(not _db_available(), reason="PostgreSQL ttdb_dev1 not reachable")
def test_navigate_by_reading(client):
    # first: value below all readings -> earliest row
    resp = client.get("/api/navigate_by_reading", params={"value": 1.0, "mode": "first"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["image_name"] and body["mode"] == "first"

    # last: a value definitely in range
    resp2 = client.get("/api/navigate_by_reading", params={"value": 3539.9, "mode": "last"})
    assert resp2.status_code == 200
    assert resp2.json()["image_name"]

    # invalid mode -> 400
    resp3 = client.get("/api/navigate_by_reading", params={"value": 1.0, "mode": "bogus"})
    assert resp3.status_code == 400


# ── Rollover-aware digits <-> reading reconciliation (pure, no DB) ──────────
from water_meter.webapp.routers.admin import (  # noqa: E402
    _normalize_digits, _reading_from_digits, _digits_from_reading,
)


def test_normalize_digits():
    assert _normalize_digits("35427") == "035427"
    assert _normalize_digits("035427") == "035427"
    assert _normalize_digits("354270") == "354270"


def test_reading_from_digits_rollover():
    # digits "035427" (3542.7) at npos 98 (>=85) -> drum shows NEXT digit,
    # true tenths = 6 -> 3542.698
    assert abs(_reading_from_digits("035427", 98) - 3542.698) < 1e-9
    # same digits at low npos -> 3542.710
    assert abs(_reading_from_digits("035427", 10) - 3542.710) < 1e-9


def test_digits_from_reading_rollover():
    assert _digits_from_reading(3542.698, 98) == "035427"
    assert _digits_from_reading(3542.710, 10) == "035427"
    assert _digits_from_reading(3542.0, 0) == "035420"


def test_roundtrip_consistency():
    for npos in (0, 45, 85, 98):
        reading = _reading_from_digits("035427", npos)
        assert _digits_from_reading(reading, npos) == "035427"
