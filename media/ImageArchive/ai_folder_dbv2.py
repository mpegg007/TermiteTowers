#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/ai_folder_dbv2.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d100ea3e312e58a4782faea1e0a38722c575e561 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-18 21:38:51 %
#  %ccm_git_file_name: ai_folder_dbv2.py %
#  %ccm_git_path: media/ImageArchive/ai_folder_dbv2.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 43823 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
ingest_folder_dbv2.py

Walk a folder (recursively) and load every image directly into PostgreSQL
using the v2 schema (init_v2_schema.sh).

Identity model:
  v2.images       is keyed on image_hash  (ImageDataHash — pixel content only,
                  format-agnostic; one row per unique image)
  v2.files        is keyed on file_hash   (SHA-256 of the raw file bytes;
                  one row per unique file encoding)
  v2.file_locations tracks every base_path+filename where a file was found

Usage:
    python ingest_folder_dbv2.py <folder>
    python ingest_folder_dbv2.py <folder> --dry-run
    python ingest_folder_dbv2.py <folder> --force
    python ingest_folder_dbv2.py <folder> --limit 10

Requires: pip install psycopg2-binary
Config:   media/.env  with  PG_DSN=postgres://user:pass@host:5432/dbname
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import base64
import psycopg2
from psycopg2.extras import execute_values

# ── Config ──────────────────────────────────────────────────────────────────────

PROMPT_FILE = str(Path.home() / "source/TermiteTowers/media/ImageArchive/prompts.txt")
EXIFTOOL = r"/home/mpegg-adm/apps/exiftool/exiftool"
ENV_FILE  = Path(__file__).parent.parent / ".env"
USER_OVERRIDE_MODEL = None

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png",
    ".tif", ".tiff",
    ".cr2", ".cr3",
    ".nef", ".nrw",
    ".arw", ".srf", ".sr2",
    ".orf", ".raf", ".rw2",
    ".dng",
    ".heic", ".heif",
}

SKIP_TAG_PATTERNS = re.compile(
    r"SourceFile|ThumbnailImage|PreviewImage|JpgFromRaw|OtherImage"
    r"|MakerNotes|PrintIM|FlashPix"
    r"|CanonCameraInfo|NikonCapture|PentaxModelID",
    re.IGNORECASE,
)

# ── Env / connection ─────────────────────────────────────────────────────────────

def load_env(path: Path):
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def get_conn():
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        print("ERROR: PG_DSN not set. Add PG_DSN=postgres://... to media/.env")
        sys.exit(1)
    return psycopg2.connect(dsn)


# ── exiftool helpers ─────────────────────────────────────────────────────────────

def run_et(*args) -> bytes:
    cmd = [EXIFTOOL] + list(args)
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    return r.stdout


def get_image_hash(filepath: str) -> str:
    """ImageDataHash — pixel-content hash, format-independent."""
    raw = run_et("-ImageDataHash", "-s3", filepath)
    return raw.decode("utf-8", errors="replace").strip()


# ------------------------------------------------------------
# 1. Read prompt blocks
# ------------------------------------------------------------
def _load_prompt_blocks():
    blocks = {}
    current = None
    section = None

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("=== model:"):
                model = line.split(":", 1)[1].strip().replace(" ===", "")
                current = {"prompt": [], "tags": [], "prkey": None}
                blocks[model] = current
                section = None
                continue

            if line.startswith("prkey:"):
                if current:
                    current["prkey"] = line.split(":", 1)[1].strip()
                continue

            if line.startswith("prompt:"):
                section = "prompt"
                continue

            if line.startswith("tags:"):
                section = "tags"
                continue

            if section == "prompt":
                current["prompt"].append(line)

            elif section == "tags":
                if line.strip():
                    current["tags"] = [t.strip() for t in line.split(",")]

    return blocks


PROMPT_BLOCKS = _load_prompt_blocks()


def route_model(filepath: str) -> str:
    """
    Decide which model to use for this image.
    Returns: "moondream", "llava-phi3", or "llava-next-34b"
    """

    # 1. If user explicitly requested a model → respect it
    if USER_OVERRIDE_MODEL:
        return USER_OVERRIDE_MODEL

    # 2. Stage 1: Moondream quick triage
    triage = run_moondream_triage(filepath)

    # triage is a dict:
    # {
    #   "scene_type": "church",
    #   "people_count": 1,
    #   "brightness": "dim",
    #   "objects": ["statue", "altar"]
    # }

    # 3. If Moondream fails → fallback to Phi3
    if not triage or "scene_type" not in triage:
        return "llava-phi3"

    people = triage.get("people_count", 0)
    scene  = triage.get("scene_type", "unknown")
    bright = triage.get("brightness", "normal")

    # 4. Simple scenes → Moondream is enough
    if people == 0 and scene in ("landscape", "street", "room"):
        return "moondream"

    # 5. Medium complexity → Phi3
    if people <= 1 and scene not in ("unknown", "complex"):
        return "llava-phi3"

    # 6. Low light + people → Phi3
    if bright in ("dark", "dim") and people <= 2:
        return "llava-phi3"

    # 7. Complex scenes → 34B
    if people > 2 or scene in ("church", "altar", "crowd", "complex"):
        return "llava-next-34b"

    # 8. Fallback
    return "llava-phi3"

# ------------------------------------------------------------
# 2. Select model → PR## → prompt
# ------------------------------------------------------------
def select_model(filepath: str) -> str:
    return route_model(filepath)


def get_pr_key(model: str) -> str:
    return PROMPT_BLOCKS[model]["prkey"]


def get_prompt(model: str) -> str:
    return "\n".join(PROMPT_BLOCKS[model]["prompt"]).strip()


def get_tags(model: str):
    return PROMPT_BLOCKS[model]["tags"]

def run_moondream_triage(filepath: str) -> dict:
    """
    Run Moondream triage using the PR01 strict JSON prompt.
    Returns a dict with keys:
      scene_type, indoor_outdoor, people_count, brightness, objects
    Returns {} on failure.
    """

    model = "moondream"
    pr_key = get_pr_key(model)
    prompt = get_prompt(model)

    # Base64 encode image
    try:
        with open(filepath, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return {}

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }

    # Call Ollama
    proc = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", json.dumps(payload)],
        capture_output=True
    )

    try:
        data = json.loads(proc.stdout.decode("utf-8"))
        raw = data.get("response", "").strip()
    except Exception:
        return {}

    # Parse the JSON Moondream returns
    try:
        triage = json.loads(raw)
        if isinstance(triage, dict):
            return triage
        return {}
    except Exception:
        return {}

def db_has_pr(cur, image_hash: str, pr_key: str) -> bool:
    # 1. Find image_id
    cur.execute("SELECT image_id FROM v2.images WHERE image_hash = %s", (image_hash,))
    row = cur.fetchone()
    if not row:
        return False
    image_id = row[0]

    # 2. Find tag_id for aaAI:PR##
    tag_key = f"aaAI:{pr_key}PromptResponse"
    cur.execute("SELECT tag_id FROM v2.tag_master WHERE tag_key = %s", (tag_key,))
    row = cur.fetchone()
    if not row:
        return False
    tag_id = row[0]

    # 3. Check image_tags
    cur.execute(
        "SELECT 1 FROM v2.image_tags WHERE image_id = %s AND tag_id = %s",
        (image_id, tag_id)
    )
    if cur.fetchone():
        return True

    # 4. Check file_tags
    cur.execute(
        "SELECT 1 FROM v2.file_tags WHERE image_id = %s AND tag_id = %s",
        (image_id, tag_id)
    )
    if cur.fetchone():
        return True

    return False

# ------------------------------------------------------------
# 3. Call Ollama
# ------------------------------------------------------------
def ollama_generate(url, model, prompt, img_bytes):
    import subprocess, json, base64

    # Encode image
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [b64],
    }

    # Build curl command
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        url,
        "-H", "Content-Type: application/json",
        "-d", "@-",          # <‑‑ read POST body from stdin
    ]

    # Launch curl
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Write JSON to stdin
    proc.stdin.write(json.dumps(payload).encode("utf-8"))
    proc.stdin.close()

    # Read output
    out = proc.stdout.read().decode("utf-8")
    err = proc.stderr.read().decode("utf-8")

    if err.strip():
        raise RuntimeError(err)

    return out

# ------------------------------------------------------------
# 4. AI version of get_all_tags()
# ------------------------------------------------------------
def ai_get_all_tags(filepath: str) -> dict:
    model = select_model(filepath)
    pr_key = get_pr_key(model)
    prompt = get_prompt(model)
    response = run_ollama(filepath, model, prompt)

    return {
        f"aaAI:{pr_key}ModelID": model,
        f"aaAI:{pr_key}PromptKey": pr_key,
        f"aaAI:{pr_key}PromptResponse": response
    }


# ------------------------------------------------------------
# 5. Optional: wrapper to replace ExifTool
# ------------------------------------------------------------
def get_all_tags(filepath: str, cur=None) -> dict:
    # compute image hash
    image_hash = get_image_hash(filepath)

    # determine which PR## this image would use
    model = select_model(filepath)
    pr_key = get_pr_key(model)

    # check DB
    if db_has_pr(cur, image_hash, pr_key):
        return {}   # crawler will skip

    # otherwise generate AI tags
    return ai_get_all_tags(filepath)

# ── File hash ────────────────────────────────────────────────────────────────────

def compute_file_hash(filepath: str) -> str:
    """SHA-256 of the raw file bytes (distinct from ImageDataHash)."""
    h = hashlib.sha256()
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Tag helpers ──────────────────────────────────────────────────────────────────

def flatten_tag_value(val) -> str:
    if isinstance(val, list):
        return "; ".join(str(v) for v in val)
    return str(val)


def should_skip_tag(key: str, val_str: str) -> bool:
    if SKIP_TAG_PATTERNS.search(key):
        return True
    if val_str.startswith("(Binary data"):
        return True
    return False


def build_tag_rows(all_tags: dict) -> dict[str, str]:
    """Return {tag_key: tag_value} for all storable tags."""
    rows: dict[str, str] = {}
    for key, val in all_tags.items():
        if key == "SourceFile":
            continue
        val_str = flatten_tag_value(val)
        if should_skip_tag(key, val_str):
            continue
        rows[key] = val_str
    return rows


# ── Metadata extraction ──────────────────────────────────────────────────────────

def _norm_exif_date(s: str) -> str:
    """Normalise EXIF date separators: '2026:05:21 14:30:22' → '2026-05-21 14:30:22'."""
    return re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', s)


def get_file_type(all_tags: dict, filepath: str) -> str:
    ft = all_tags.get("File:FileType") or all_tags.get("FileType")
    if ft:
        return str(ft).upper()
    return Path(filepath).suffix.lstrip(".").upper()


def get_capture_date(all_tags: dict, filepath: str) -> str:
    for key in (
        "EXIF:DateTimeOriginal", "ExifIFD:DateTimeOriginal",
        "EXIF:CreateDate",      "ExifIFD:CreateDate",
        "XMP:CreateDate",
        "File:FileModifyDate",
    ):
        val = all_tags.get(key)
        if val:
            return _norm_exif_date(str(val))
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


def get_dimensions(all_tags: dict) -> tuple[int | None, int | None]:
    w = None
    for key in ("EXIF:ImageWidth", "EXIF:ExifImageWidth", "File:ImageWidth", "ImageWidth"):
        raw = all_tags.get(key)
        if raw is not None:
            try:
                w = int(str(raw).split()[0])
                break
            except (ValueError, IndexError):
                continue
    h = None
    for key in ("EXIF:ImageHeight", "EXIF:ExifImageHeight", "File:ImageHeight", "ImageHeight"):
        raw = all_tags.get(key)
        if raw is not None:
            try:
                h = int(str(raw).split()[0])
                break
            except (ValueError, IndexError):
                continue
    return w, h


def get_orientation(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return "unknown"
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def get_camera_model(all_tags: dict) -> str | None:
    model = (all_tags.get("EXIF:Model")
             or all_tags.get("IFD0:Model")
             or all_tags.get("Model"))
    make  = (all_tags.get("EXIF:Make")
             or all_tags.get("IFD0:Make")
             or all_tags.get("Make"))
    if not model:
        return None
    s = str(model).strip()
    if make:
        make_s = str(make).strip()
        if not s.lower().startswith(make_s.lower()):
            s = f"{make_s} {s}"
    return s


def get_lens_info(all_tags: dict) -> str | None:
    for key in ("EXIF:LensModel", "ExifIFD:LensModel", "XMP:Lens",
                "Composite:LensID", "EXIF:LensInfo"):
        val = all_tags.get(key)
        if val:
            return str(val).strip()
    return None


def get_color_space(all_tags: dict) -> str | None:
    for key in ("EXIF:ColorSpace", "ICC_Profile:ColorSpaceData",
                "ICC_Profile:ProfileConnectionSpace"):
        val = all_tags.get(key)
        if val:
            return str(val).strip()
    return None


def get_mime_type(all_tags: dict) -> str | None:
    val = all_tags.get("File:MIMEType") or all_tags.get("MIMEType")
    return str(val).strip() if val else None


def get_bit_depth(all_tags: dict) -> int | None:
    for key in ("EXIF:BitsPerSample", "File:BitsPerSample", "PNG:BitDepth"):
        val = all_tags.get(key)
        if val is not None:
            try:
                return int(str(val).split()[0])
            except (ValueError, IndexError):
                continue
    return None


def get_color_profile(all_tags: dict) -> str | None:
    for key in ("ICC_Profile:ProfileDescription", "ICC-header:ProfileDescription"):
        val = all_tags.get(key)
        if val:
            return str(val).strip()
    return None


def get_exif_rating(all_tags: dict) -> int | None:
    """Map XMP:Rating (0-5) to the v2.images.rating column."""
    for key in ("XMP:Rating", "XMP-xmp:Rating", "MicrosoftPhoto:Rating"):
        val = all_tags.get(key)
        if val is not None:
            try:
                r = int(str(val))
                if 0 <= r <= 5:
                    return r
            except (ValueError, TypeError):
                continue
    return None


# ── Filesystem / compression helpers ────────────────────────────────────────────

def get_mount_info(filepath: str) -> tuple[str | None, str | None]:
    """Return (storage_volume, mount_point) for the file's filesystem."""
    try:
        result = subprocess.run(
            ["df", "-P", filepath],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                # df -P: Filesystem 1024-blocks Used Available Capacity Mounted-on
                storage_volume = parts[0] if parts else None
                mount_point    = parts[5] if len(parts) > 5 else None
                return storage_volume, mount_point
    except Exception:
        pass
    return None, None


def _get_channel_count(all_tags: dict) -> int | None:
    """Infer number of colour channels from EXIF tags."""
    for key in ("EXIF:SamplesPerPixel", "File:ColorComponents", "ColorComponents"):
        val = all_tags.get(key)
        if val is not None:
            try:
                return int(str(val).split()[0])
            except (ValueError, IndexError):
                continue
    cs = str(all_tags.get("EXIF:ColorSpace") or all_tags.get("File:ColorSpace", "")).lower()
    if "rgb" in cs:
        return 3
    if "cmyk" in cs:
        return 4
    if "gray" in cs or "grey" in cs:
        return 1
    pi = str(all_tags.get("EXIF:PhotometricInterpretation", "")).lower()
    if "rgb" in pi:
        return 3
    if "cmyk" in pi:
        return 4
    if "gray" in pi or "min" in pi:
        return 1
    return None


def compute_compression_ratio(
    file_size: int,
    width: int | None,
    height: int | None,
    bit_depth: int | None,
    all_tags: dict,
) -> float | None:
    """
    Ratio of actual file size to uncompressed pixel data size.
    < 1.0 means the file is smaller than raw; ~1.0 is near-lossless.
    NUMERIC(5,2) range supported: 0.01 .. 999.99.
    """
    if not (file_size and width and height and bit_depth):
        return None
    channels = _get_channel_count(all_tags)
    if channels is None:
        return None
    raw_size = width * height * channels * (bit_depth / 8)
    if raw_size <= 0:
        return None
    return min(round(file_size / raw_size, 2), 999.99)


# ── Tag master (normalised) cache ────────────────────────────────────────────────

_tag_id_cache: dict[str, int] = {}
_policy_tag_keys: set[str] = set()   # tag_keys that had ≥1 policy row at prime time
_existing_tag_keys: set[str] = set() # all tag_keys in tag_master at prime time (incl. no-policy)


def get_or_create_tag_id(cur, tag_key: str) -> int:
    if tag_key in _tag_id_cache:
        return _tag_id_cache[tag_key]
    # ON CONFLICT DO UPDATE with a no-op ensures RETURNING always fires
    cur.execute(
        "INSERT INTO v2.tag_master (tag_key)"
        " VALUES (%s)"
        " ON CONFLICT (tag_key) DO UPDATE SET tag_key = EXCLUDED.tag_key"
        " RETURNING tag_id, canonical_id",
        (tag_key,),
    )
    row = cur.fetchone()
    tag_id, canonical_id = row
    # Follow canonical alias so aliased tags deduplicate to the same row
    effective_id: int = canonical_id if canonical_id is not None else tag_id
    _tag_id_cache[tag_key] = effective_id
    # New tag: create a default file-level policy so it qualifies for storage.
    # ON CONFLICT DO NOTHING is safe for aliases and concurrent runs.
    cur.execute(
        "INSERT INTO v2.tag_policies (tag_id, target_type, track_history, write_to_exif)"
        " VALUES (%s, 'file', true, false)"
        " ON CONFLICT (tag_id, target_type) DO NOTHING",
        (effective_id,),
    )
    return effective_id


def prime_tag_cache(cur):
    """Reload tag_master and tag_policies into the local caches.

    _policy_tag_keys  — keys that have ≥1 tag_policies row at prime time.
                        These are stored in image_tags (formally classified).
    _existing_tag_keys — all keys in tag_master at prime time (with or without
                        a policy).  Keys absent from both sets are brand-new and
                        will receive a default policy via get_or_create_tag_id.

    Tags in tag_master but WITHOUT a policy are skipped — not stored.
    Clears all collections first so it is safe to call after a rollback.
    """
    _tag_id_cache.clear()
    _policy_tag_keys.clear()
    _existing_tag_keys.clear()
    cur.execute("SELECT tag_key, tag_id, canonical_id FROM v2.tag_master")
    for key, tid, canonical_id in cur.fetchall():
        effective_id = canonical_id if canonical_id is not None else tid
        _tag_id_cache[key] = effective_id
        _existing_tag_keys.add(key)
    cur.execute(
        "SELECT DISTINCT tm.tag_key"
        " FROM v2.tag_master tm"
        " JOIN v2.tag_policies tp ON tp.tag_id = tm.tag_id"
    )
    for (key,) in cur.fetchall():
        _policy_tag_keys.add(key)


# ── Schema check ─────────────────────────────────────────────────────────────────

def check_schema(conn):
    required = (
        "v2.images", "v2.files", "v2.file_locations",
        "v2.tag_master", "v2.image_tags", "v2.file_tags",
    )
    with conn.cursor() as cur:
        placeholders = ", ".join(["to_regclass(%s)"] * len(required))
        cur.execute(f"SELECT {placeholders}", list(required))
        row = cur.fetchone()
    missing = [name for name, exists in zip(required, row) if exists is None]
    if missing:
        print(f"ERROR: Missing tables: {', '.join(missing)}")
        print("  -> Run init_v2_schema.sh on the server first.")
        sys.exit(1)


# ── Image upsert (canonical, keyed on image_hash) ───────────────────────────────

def find_image_id(cur, image_hash: str) -> int | None:
    cur.execute("SELECT image_id FROM v2.images WHERE image_hash = %s", (image_hash,))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_image(cur, *, image_hash, width, height, fmt, capture_date,
                 camera_model, lens_info, orientation, color_space,
                 rating) -> int:
    cur.execute(
        """
        INSERT INTO v2.images
            (image_hash, width, height, format, capture_date,
             camera_model, lens_info, orientation, color_space, rating)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (image_hash) DO UPDATE SET
            width        = COALESCE(EXCLUDED.width,        v2.images.width),
            height       = COALESCE(EXCLUDED.height,       v2.images.height),
            format       = COALESCE(EXCLUDED.format,       v2.images.format),
            capture_date = COALESCE(EXCLUDED.capture_date, v2.images.capture_date),
            camera_model = COALESCE(EXCLUDED.camera_model, v2.images.camera_model),
            lens_info    = COALESCE(EXCLUDED.lens_info,    v2.images.lens_info),
            orientation  = COALESCE(EXCLUDED.orientation,  v2.images.orientation),
            color_space  = COALESCE(EXCLUDED.color_space,  v2.images.color_space),
            rating       = CASE WHEN EXCLUDED.rating > 0 THEN EXCLUDED.rating
                                ELSE v2.images.rating END
        RETURNING image_id
        """,
        (image_hash, width, height, fmt, capture_date,
         camera_model, lens_info, orientation, color_space, rating or 0),
    )
    return cur.fetchone()[0]


# ── File upsert (keyed on file_hash) ────────────────────────────────────────────

def find_file_id(cur, file_hash: str) -> int | None:
    cur.execute("SELECT file_id FROM v2.files WHERE file_hash = %s", (file_hash,))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_file(cur, *, image_id, file_hash, file_size, mime_type,
                bit_depth, color_profile, compression_ratio=None) -> int:
    cur.execute(
        """
        INSERT INTO v2.files
            (image_id, file_hash, file_size, mime_type,
             bit_depth, color_profile, compression_ratio, is_master, is_corrupt)
        VALUES (%s,%s,%s,%s,%s,%s,%s, false, false)
        ON CONFLICT (file_hash) DO UPDATE SET
            image_id          = EXCLUDED.image_id,
            file_size         = COALESCE(EXCLUDED.file_size,         v2.files.file_size),
            mime_type         = COALESCE(EXCLUDED.mime_type,         v2.files.mime_type),
            bit_depth         = COALESCE(EXCLUDED.bit_depth,         v2.files.bit_depth),
            color_profile     = COALESCE(EXCLUDED.color_profile,     v2.files.color_profile),
            compression_ratio = COALESCE(EXCLUDED.compression_ratio, v2.files.compression_ratio)
        RETURNING file_id
        """,
        (image_id, file_hash, file_size, mime_type, bit_depth, color_profile, compression_ratio),
    )
    return cur.fetchone()[0]


# ── Location upsert ──────────────────────────────────────────────────────────────

def upsert_location(cur, *, file_id, base_path, filename,
                    storage_volume=None, mount_point=None) -> int:
    cur.execute(
        """
        INSERT INTO v2.file_locations
            (file_id, base_path, filename, storage_volume, mount_point,
             is_online, last_verified_at)
        VALUES (%s,%s,%s,%s,%s, true, NOW())
        ON CONFLICT (file_id, base_path) DO UPDATE SET
            filename         = EXCLUDED.filename,
            storage_volume   = COALESCE(EXCLUDED.storage_volume, v2.file_locations.storage_volume),
            mount_point      = COALESCE(EXCLUDED.mount_point,    v2.file_locations.mount_point),
            is_online        = true,
            last_verified_at = NOW()
        RETURNING location_id
        """,
        (file_id, base_path, filename, storage_volume, mount_point),
    )
    return cur.fetchone()[0]


# ── Tag sync helpers ─────────────────────────────────────────────────────────────

def _read_entity_tags(cur, table: str, id_col: str, entity_id: int) -> dict[str, str]:
    """Return {tag_key: tag_value} for a given entity."""
    cur.execute(
        f"SELECT tm.tag_key, et.tag_value"
        f" FROM {table} et"
        f" JOIN v2.tag_master tm ON tm.tag_id = et.tag_id"
        f" WHERE et.{id_col} = %s",
        (entity_id,),
    )
    return {r[0]: r[1] for r in cur.fetchall()}


def _sync_tags(cur, table: str, id_col: str, entity_id: int,
               new_tags: dict[str, str]) -> tuple[int, int, int]:
    """
    Diff and apply tag changes for any *_tags table.
    The UPDATE trigger (fn_audit_tag_change) handles history per tag_policies.
    Returns (added, changed, removed).
    """
    old_tags = _read_entity_tags(cur, table, id_col, entity_id)

    added   = {k: v for k, v in new_tags.items() if k not in old_tags}
    changed = {k: v for k, v in new_tags.items()
               if k in old_tags and old_tags[k] != v}
    removed = {k for k in old_tags if k not in new_tags}

    if added:
        rows = []
        for key, val in added.items():
            tid = get_or_create_tag_id(cur, key)
            rows.append((entity_id, tid, val))
        execute_values(
            cur,
            f"INSERT INTO {table} ({id_col}, tag_id, tag_value)"
            f" VALUES %s ON CONFLICT DO NOTHING",
            rows,
        )

    for key, val in changed.items():
        tid = get_or_create_tag_id(cur, key)
        cur.execute(
            f"UPDATE {table} SET tag_value = %s"
            f" WHERE {id_col} = %s AND tag_id = %s",
            (val, entity_id, tid),
        )

    for key in removed:
        tid = _tag_id_cache.get(key)
        if tid is None:
            cur.execute("SELECT tag_id FROM v2.tag_master WHERE tag_key = %s", (key,))
            row = cur.fetchone()
            if row:
                tid = row[0]
                _tag_id_cache[key] = tid
        if tid:
            cur.execute(
                f"DELETE FROM {table} WHERE {id_col} = %s AND tag_id = %s",
                (entity_id, tid),
            )

    return len(added), len(changed), len(removed)


def sync_image_tags(cur, image_id: int, tag_rows: dict[str, str]) -> tuple[int, int, int]:
    return _sync_tags(cur, "v2.image_tags", "image_id", image_id, tag_rows)


def sync_file_tags(cur, file_id: int, tag_rows: dict[str, str]) -> tuple[int, int, int]:
    """Store tags in file_tags — used for auto-created (unclassified) tag keys."""
    return _sync_tags(cur, "v2.file_tags", "file_id", file_id, tag_rows)


# ── Stack helpers ────────────────────────────────────────────────────────────────

def parse_stack_tags(extra_args: list[str]) -> dict[str, str]:
    """
    Extract --ingest-stack-KEY=VALUE arguments from the unparsed CLI remainder.

    Keys are stored in tag_master as  Stack:Title  (the 'Stack:' namespace plus
    the title-cased key from the CLI, e.g. --ingest-stack-owner → Stack:Owner).
    Values are kept verbatim.
    """
    stack_tags: dict[str, str] = {}
    for arg in extra_args:
        m = re.match(r'^--ingest-stack-([a-zA-Z0-9_-]+)=(.*)$', arg)
        if m:
            raw_key = m.group(1)
            tag_key = "Stack:" + raw_key.title()   # owner→Owner, my-group→My-Group
            stack_tags[tag_key] = m.group(2)
        elif arg.startswith("--ingest-stack-"):
            print(f"WARNING: Ignoring malformed stack arg (expected --ingest-stack-KEY=VALUE): {arg}")
    return stack_tags


def find_or_create_stack(cur, stack_tags: dict[str, str]) -> tuple[int, bool]:
    """
    Find a v2.stacks row whose Stack:* tags match exactly the supplied key/value
    pairs.  Tags added by other processes under different namespaces are ignored
    in the comparison — only Stack:* tags are counted in the totals check.
    Creates a new stack if no exact match is found.

    Returns (stack_id, created).
    """
    tag_count = len(stack_tags)
    keys   = list(stack_tags.keys())
    values = list(stack_tags.values())

    cur.execute(
        """
        WITH provided AS (
            SELECT unnest(%s::text[]) AS tag_key,
                   unnest(%s::text[]) AS tag_value
        ),
        matches AS (
            SELECT st.stack_id, COUNT(*) AS matched
            FROM v2.stack_tags st
            JOIN v2.tag_master tm ON tm.tag_id = st.tag_id
            JOIN provided p ON p.tag_key = tm.tag_key AND p.tag_value = st.tag_value
            GROUP BY st.stack_id
        ),
        stack_totals AS (
            -- Count only Stack:* namespace tags so other-process tags are invisible
            SELECT st.stack_id, COUNT(*) AS total
            FROM v2.stack_tags st
            JOIN v2.tag_master tm ON tm.tag_id = st.tag_id
            WHERE tm.tag_key LIKE 'Stack:%%'
            GROUP BY st.stack_id
        )
        SELECT m.stack_id
        FROM matches m
        JOIN stack_totals t ON t.stack_id = m.stack_id
        WHERE m.matched = %s AND t.total = %s
        LIMIT 1
        """,
        (keys, values, tag_count, tag_count),
    )
    row = cur.fetchone()
    if row:
        return row[0], False

    # Create new stack; human-readable name strips the Stack: prefix
    stack_name = " | ".join(
        f"{k.split(':', 1)[1].lower()}={v}" for k, v in stack_tags.items()
    )
    cur.execute(
        "INSERT INTO v2.stacks (stack_name) VALUES (%s) RETURNING stack_id",
        (stack_name,),
    )
    stack_id: int = cur.fetchone()[0]

    for key, val in stack_tags.items():
        tid = get_or_create_tag_id(cur, key)
        cur.execute(
            "INSERT INTO v2.stack_tags (stack_id, tag_id, tag_value)"
            " VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (stack_id, tid, val),
        )

    return stack_id, True


def add_to_stack(cur, stack_id: int, image_id: int):
    cur.execute(
        "INSERT INTO v2.stack_members (stack_id, image_id)"
        " VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (stack_id, image_id),
    )


# ── File collection ──────────────────────────────────────────────────────────────

def collect_images(folder: Path) -> list[Path]:
    result = []
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if Path(fname).suffix.lower() in IMAGE_EXTS:
                result.append(Path(dirpath) / fname)
    return sorted(result)


# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ingest a folder of images into the v2 PostgreSQL schema.")
    parser.add_argument("folder", help="Folder to walk (recursively)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done but make no DB changes")
    parser.add_argument("--force", action="store_true",
                        help="Re-process files whose file_hash is already in the DB")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N files (0 = no limit)")
    # Collect any --ingest-stack-KEY=VALUE args from the remainder
    args, extra_args = parser.parse_known_args()
    stack_tags = parse_stack_tags(extra_args)

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        sys.exit(1)

    load_env(ENV_FILE)

    if args.dry_run:
        print("[DRY RUN] No changes will be written.\n")
    if stack_tags:
        print(f"Stack tags requested: {stack_tags}")

    conn = get_conn()
    check_schema(conn)

    images = collect_images(folder)
    print(f"Found {len(images)} image(s) in {folder}\n")

    processed = skipped = errors = 0

    with conn.cursor() as cur:
        prime_tag_cache(cur)

        # ── Resolve or create stack ───────────────────────────────────────
        stack_id: int | None = None
        if stack_tags and not args.dry_run:
            stack_id, created = find_or_create_stack(cur, stack_tags)
            conn.commit()
            verb = "Created" if created else "Found"
            print(f"{verb} stack id={stack_id}  {stack_tags}\n")
        elif stack_tags and args.dry_run:
            print(f"[DRY RUN] Would resolve stack with tags: {stack_tags}\n")

        for img_path in images:
            if args.limit and processed >= args.limit:
                print(f"\nLimit of {args.limit} reached.")
                break

            rel = (img_path.relative_to(folder)
                   if img_path.is_relative_to(folder) else img_path)
            print(f"  {rel} ", end="", flush=True)

            try:
                # ── Hashes ───────────────────────────────────────────────
                image_hash = get_image_hash(str(img_path))
                if not image_hash:
                    print("✗ image_hash failed")
                    errors += 1
                    continue

                file_hash = compute_file_hash(str(img_path))

                # ── Metadata ─────────────────────────────────────────────
                all_tags = get_all_tags(str(img_path), cur)
                tag_rows     = build_tag_rows(all_tags)
                fmt          = get_file_type(all_tags, str(img_path))
                capture_date = get_capture_date(all_tags, str(img_path))
                width, height = get_dimensions(all_tags)
                orientation  = get_orientation(width, height)
                camera_model = get_camera_model(all_tags)
                lens_info    = get_lens_info(all_tags)
                color_space  = get_color_space(all_tags)
                mime_type    = get_mime_type(all_tags)
                bit_depth    = get_bit_depth(all_tags)
                color_profile= get_color_profile(all_tags)
                rating       = get_exif_rating(all_tags)
                file_size    = img_path.stat().st_size
                base_path    = str(img_path.parent)
                filename     = img_path.name
                storage_volume, mount_point = get_mount_info(str(img_path))
                compression_ratio = compute_compression_ratio(
                    file_size, width, height, bit_depth, all_tags)

                if args.dry_run:
                    known_img  = find_image_id(cur, image_hash)
                    known_file = find_file_id(cur, file_hash)
                    labels = []
                    if known_img:  labels.append("known_image")
                    if known_file: labels.append("known_file")
                    prefix = f"({','.join(labels)}) " if labels else ""
                    policy_count  = sum(1 for k in tag_rows if k in _policy_tag_keys)
                    new_count     = sum(1 for k in tag_rows
                                       if k not in _policy_tag_keys
                                       and k not in _existing_tag_keys)
                    skipped_count = len(tag_rows) - policy_count - new_count
                    skip_note = f" skipped(no-policy):{skipped_count}" if skipped_count else ""
                    print(f"{prefix}→ {fmt}  {width}x{height}  "
                          f"img_tags:{policy_count} file_tags:{new_count}{skip_note}  "
                          f"{file_size:,}B  {capture_date}")
                    processed += 1
                    continue

                # ── Skip already-known file unless --force ────────────────
                existing_file_id = find_file_id(cur, file_hash)
                if existing_file_id and not args.force:
                    upsert_location(cur, file_id=existing_file_id,
                                    base_path=base_path, filename=filename,
                                    storage_volume=storage_volume,
                                    mount_point=mount_point)
                    if stack_id is not None:
                        # image_hash already computed above — no extra DB lookup needed
                        existing_image_id = find_image_id(cur, image_hash)
                        if existing_image_id:
                            add_to_stack(cur, stack_id, existing_image_id)
                    conn.commit()
                    print("(known file_hash) loc: refreshed")
                    skipped += 1
                    continue

                # ── Canonical image record ────────────────────────────────
                image_id = upsert_image(
                    cur,
                    image_hash=image_hash,
                    width=width,
                    height=height,
                    fmt=fmt,
                    capture_date=capture_date,
                    camera_model=camera_model,
                    lens_info=lens_info,
                    orientation=orientation,
                    color_space=color_space,
                    rating=rating,
                )

                # ── File record ───────────────────────────────────────────
                file_id = upsert_file(
                    cur,
                    image_id=image_id,
                    file_hash=file_hash,
                    file_size=file_size,
                    mime_type=mime_type,
                    bit_depth=bit_depth,
                    color_profile=color_profile,
                    compression_ratio=compression_ratio,
                )

                # ── Location ──────────────────────────────────────────────
                upsert_location(cur, file_id=file_id,
                                base_path=base_path, filename=filename,
                                storage_volume=storage_volume,
                                mount_point=mount_point)

                # ── Tags: policy-gated routing ────────────────────────────────
                # policy_tags  — had a policy at startup  → image_tags
                # new_tags     — unknown at startup        → get_or_create_tag_id
                #                creates tag_master + default file-level policy
                #                                          → file_tags (staging)
                # no-policy    — in tag_master but no policy → skipped (not stored)
                policy_tags = {k: v for k, v in tag_rows.items()
                               if k in _policy_tag_keys}
                new_tags    = {k: v for k, v in tag_rows.items()
                               if k not in _policy_tag_keys
                               and k not in _existing_tag_keys}

                i_add, i_chg, i_rem = sync_image_tags(cur, image_id, policy_tags)
                if new_tags:
                    sync_file_tags(cur, file_id, new_tags)

                # ── Stack membership ──────────────────────────────────────
                if stack_id is not None:
                    add_to_stack(cur, stack_id, image_id)

                conn.commit()

                parts = []
                if i_add: parts.append(f"+{i_add}")
                if i_chg: parts.append(f"~{i_chg}")
                if i_rem: parts.append(f"-{i_rem}")
                new_label = f"  file_tags:+{len(new_tags)}" if new_tags else ""
                print(f"✓  img_tags: {' '.join(parts) or 'no change'}{new_label}")
                processed += 1

            except Exception as exc:
                conn.rollback()
                # Cache may contain tag_ids from the rolled-back transaction;
                # re-prime from DB so the next file starts from a clean state.
                _tag_id_cache.clear()
                _policy_tag_keys.clear()
                _existing_tag_keys.clear()
                prime_tag_cache(cur)
                print(f"✗ {exc}")
                errors += 1

    conn.close()
    print(f"\nDone.  new={processed}  known_hash_merged={skipped}  errors={errors}")


if __name__ == "__main__":
    main()
