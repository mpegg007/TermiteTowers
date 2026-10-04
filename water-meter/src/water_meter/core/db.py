#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: AnalAcres %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/water_meter/db.py:42 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c3bf346f360fd91484ee2580e803ede7c7f0ca16 %
#  %ccm_git_commit_id: a414d7a53797f49ecad674b85a680efe8adad6d9 %
#  %ccm_git_commit_count: 42 %
#  %ccm_git_commit_date: 2026-07-26 13:05:51 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: meter dial decode %
#  %ccm_git_modify_date: 2026-07-26 13:05:52 %
#  %ccm_git_file_last_modified: 2026-07-26 09:38:24 %
#  %ccm_git_file_name: db.py %
#  %ccm_git_path: scripts/water_meter/db.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5561 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""Database model and session for water meter readings (PostgreSQL).

Mirrors the full schema of the original SQLite model.  Connects to
ttdb_dev1 on the local PG cluster via peer auth as mpegg-adm.
The table lives in the ``water_meter`` schema.
"""

import os
import json
from datetime import datetime
from contextlib import contextmanager

import numpy as np

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, create_engine,
    BigInteger
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# Connection — local socket, peer auth, schema-locked
# ---------------------------------------------------------------------------
DB_DSN = os.environ.get("WATER_METER_DB_DSN", "postgresql:///ttdb_dev1")
DB_SCHEMA = "water_meter"

_engine = create_engine(DB_DSN, echo=False, connect_args={"options": f"-csearch_path={DB_SCHEMA}"})
_Session = sessionmaker(bind=_engine)

Base = declarative_base()

# Tell SQLAlchemy to default to our schema
Base.metadata.schema = DB_SCHEMA


class MeterReading(Base):
    """One row per water meter image processed by decode_meter.py."""

    __tablename__ = "meter_readings"
    __table_args__ = {"schema": DB_SCHEMA}

    # --- Primary key: image filename (upsert key) ---
    image_name = Column(String(128), primary_key=True)

    # --- Capture metadata ---
    capture_ts     = Column(DateTime, nullable=True)
    processed_ts   = Column(DateTime, default=datetime.utcnow)

    # --- Overall status ---
    status         = Column(String(16), default="OK")   # OK / FAIL
    fail_reason    = Column(Text, nullable=True)

    # --- Hub & dial geometry ---
    hub_x          = Column(Integer)
    hub_y          = Column(Integer)
    hub_r          = Column(Integer)
    dial_r         = Column(Integer)
    dial_ry        = Column(Integer)
    left_edge      = Column(Integer)
    right_edge     = Column(Integer)

    # --- Inner ellipse ---
    inner_rx       = Column(Integer)
    inner_ry       = Column(Integer)

    # --- Needle zone & marker ---
    nz_pix         = Column(Integer)
    marker_cx      = Column(Integer)
    marker_cy      = Column(Integer)
    marker_extent  = Column(Integer)
    needle_deg     = Column(Float)
    npos           = Column(Integer)          # 0-99
    horizon_deg    = Column(Float)

    # --- Horizon row stats ---
    hrow_mean      = Column(Integer)
    hrow_std       = Column(Integer)

    # --- Image brightness ---
    img_brightness = Column(Integer)
    img_contrast   = Column(Integer)

    # --- Odometer crop ---
    odo_x1         = Column(Integer)
    odo_y1         = Column(Integer)
    odo_w          = Column(Integer)
    odo_h          = Column(Integer)
    odo_brightness = Column(Integer)
    odo_contrast   = Column(Integer)

    # --- Digit results ---
    digits         = Column(String(12))       # e.g. "35330?" or "000000"
    reading        = Column(Float)
    accumulated_revs = Column(Float)

    # --- Image dimensions ---
    img_width      = Column(Integer)
    img_height     = Column(Integer)

    # --- Odometer crop metadata ---
    odo_crop_file  = Column(String(128))      # basename of odo crop saved to proc/
    odo_width      = Column(Integer)
    odo_height     = Column(Integer)

    # --- Odometer analysis (for future digit scanning) ---
    odo_mean       = Column(Integer)           # mean pixel value of odo gray crop
    odo_std        = Column(Integer)           # std dev of odo gray crop
    odo_sobel_mean = Column(Integer)           # mean of vertical Sobel magnitude
    odo_sobel_std  = Column(Integer)           # std dev of vertical Sobel magnitude
    odo_hist_entropy = Column(Float)           # Shannon entropy of odo histogram

    # --- Odometer decoding results ---
    odo_reading    = Column(Float)              # bucket 1: decoded reading from OCR (image scan)
    odo_confidence = Column(Float)              # overall confidence of odo decode
    odo_pos5       = Column(Integer)            # decoded pos5 digit
    odo_pos5_conf  = Column(Float)              # confidence of pos5 match

    # --- 4-bucket reading architecture ---
    odo_scan       = Column(Float)              # bucket 1: raw OCR / template match result
    odo_needle     = Column(Float)              # bucket 2: needle-crossing continuity calc
    odo_manual     = Column(Float)              # bucket 3: human-verified manual input
    odo_published  = Column(Float)              # bucket 4: authoritative published value

    # --- Pipeline state ---
    clean_read     = Column(Boolean, default=False)
    clean_archive  = Column(Boolean, default=False)
    notes          = Column(Text, nullable=True)

    # ── dm_ columns (decode_meter — dial detection + odo crop) ─────
    dm_status           = Column(String(16), nullable=True)
    dm_fail_reason      = Column(Text, nullable=True)
    dm_hub_x            = Column(Integer, nullable=True)
    dm_hub_y            = Column(Integer, nullable=True)
    dm_hub_r            = Column(Integer, nullable=True)
    dm_dial_r           = Column(Integer, nullable=True)
    dm_dial_ry          = Column(Integer, nullable=True)
    dm_left_edge        = Column(Integer, nullable=True)
    dm_right_edge       = Column(Integer, nullable=True)
    dm_inner_rx         = Column(Integer, nullable=True)
    dm_inner_ry         = Column(Integer, nullable=True)
    dm_nz_pix           = Column(Integer, nullable=True)
    dm_marker_cx        = Column(Integer, nullable=True)
    dm_marker_cy        = Column(Integer, nullable=True)
    dm_marker_extent    = Column(Integer, nullable=True)
    dm_needle_deg       = Column(Float, nullable=True)
    dm_npos             = Column(Integer, nullable=True)
    dm_horizon_deg      = Column(Float, nullable=True)
    dm_hrow_mean        = Column(Integer, nullable=True)
    dm_hrow_std         = Column(Integer, nullable=True)
    dm_img_brightness   = Column(Integer, nullable=True)
    dm_img_contrast     = Column(Integer, nullable=True)
    dm_img_width        = Column(Integer, nullable=True)
    dm_img_height       = Column(Integer, nullable=True)
    dm_odo_x1           = Column(Integer, nullable=True)
    dm_odo_y1           = Column(Integer, nullable=True)
    dm_odo_w            = Column(Integer, nullable=True)
    dm_odo_h            = Column(Integer, nullable=True)
    dm_odo_crop_file    = Column(String(128), nullable=True)
    dm_odo_brightness   = Column(Integer, nullable=True)
    dm_odo_contrast     = Column(Integer, nullable=True)
    dm_odo_mean         = Column(Integer, nullable=True)
    dm_odo_std          = Column(Integer, nullable=True)
    dm_odo_sobel_mean   = Column(Integer, nullable=True)
    dm_odo_sobel_std    = Column(Integer, nullable=True)
    dm_odo_hist_entropy = Column(Float, nullable=True)

    # ── do_ columns (decode_odo — digit recognition) ────────────────
    do_digits       = Column(String(12), nullable=True)
    do_reading      = Column(Float, nullable=True)
    do_confidence   = Column(Float, nullable=True)
    do_pos5         = Column(Integer, nullable=True)
    do_pos5_conf    = Column(Float, nullable=True)
    do_pos5_source  = Column(String(8), nullable=True)
    do_details      = Column(Text, nullable=True)   # JSON: per-position scores, sources

    # ── dr_ columns (rotation anchor picker) ───────────────────────
    dr_cycle    = Column(Integer, nullable=True)
    dr_zone     = Column(String(8), nullable=True)
    dr_enter    = Column(Integer, nullable=True)
    dr_exit     = Column(Integer, nullable=True)
    dr_flutter  = Column(Boolean, nullable=True)
    dr_best     = Column(Boolean, nullable=True)
    dr_score    = Column(Float, nullable=True)
    dr_pos5     = Column(Integer, nullable=True)

    # ── cn_ columns (calc_needle_readings) ──────────────────────────
    cn_needle          = Column(Float, nullable=True)
    cn_published       = Column(Float, nullable=True)
    cn_manual          = Column(Float, nullable=True)
    cn_visual_trusted  = Column(Boolean, nullable=True)

    # ── kp_ columns (keeper flags for archive protection) ───────────
    kp_first_of_day  = Column(Boolean, nullable=True)
    kp_last_of_day   = Column(Boolean, nullable=True)
    kp_first_lit     = Column(Boolean, nullable=True)
    kp_last_lit      = Column(Boolean, nullable=True)
    kp_rotation_best = Column(Boolean, nullable=True)
    kp_important     = Column(Boolean, nullable=True)

    def __repr__(self):
        return f"<MeterReading({self.image_name}, {self.status}, reading={self.reading})>"


def init_db():
    """Create tables if they don't exist. Safe to call repeatedly."""
    Base.metadata.create_all(_engine)


@contextmanager
def get_session():
    """Context manager yielding a SQLAlchemy Session."""
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _to_native(v):
    """Convert numpy types to native Python types for psycopg2 compatibility."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    return v


def upsert_reading(session: Session, row_data: dict) -> MeterReading:
    """Insert or update a MeterReading row keyed on image_name.

    ``row_data`` keys correspond to column names.  ``image_name`` is required.
    Returns the persisted MeterReading instance.
    """
    image_name = row_data.pop("image_name")
    # Convert numpy types to native Python types
    row_data = {k: _to_native(v) for k, v in row_data.items()}
    existing = session.get(MeterReading, image_name)
    if existing:
        for k, v in row_data.items():
            setattr(existing, k, v)
        reading = existing
    else:
        reading = MeterReading(image_name=image_name, **row_data)
        session.add(reading)
    session.flush()
    return reading
