#!/usr/bin/env python3
"""
Water Meter Pipeline Wrapper — runs the full sequence of jobs from image
ingestion through decoding, anchor review, flagging, archiving, cleanup,
and final reading extraction.

Pipeline order:
  1. decode_meter   — scan images, detect meter/needle, crop odo, store in DB
  2. decode_odo     — decode 6-digit odometer from saved crops
  3. calc_needle    — combine odo + npos → final_reading with monotonicity
  4. suggest_anchors — find high-quality anchor candidates (npos≈0, high conf)
  5. [user confirms anchors, re-runs calc_needle with anchors]
  6. flag_important  — mark important frames for preservation
  7. copy_keepers    — copy preserved source images to keepers/ before archiving
  8. archive_images  — zip & upload completed day folders to Jottacloud
  9. reupload_archives — retry any staging zips that failed to upload
  10. cleanup         — delete non-preserved crops, old debug, empty dirs
  11. extract_readings — output tiered CSV (hourly→8hourly→daily)

Usage:
    # Full pipeline (dry-run for archive/cleanup phases)
    .venv/bin/python scripts/water_meter/pipeline.py

    # Full pipeline with user anchor review
    .venv/bin/python scripts/water_meter/pipeline.py --interactive

    # Execute archive/cleanup (actually upload/delete)
    .venv/bin/python scripts/water_meter/pipeline.py --execute

    # Skip already-completed phases
    .venv/bin/python scripts/water_meter/pipeline.py --skip-decode --skip-anchors

    # Auto mode (cron-friendly, no prompts)
    .venv/bin/python scripts/water_meter/pipeline.py --auto
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project root & venv
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "src", "water_meter", "core")

# CLI tools referenced by archive / reupload
JOTTA_CLI = "/usr/bin/jotta-cli"

log = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# Tiered extraction windows (relative to "today")
# ---------------------------------------------------------------------------
# Month 1 (days 0–30):  hourly
# Months 2–3 (31–90):  8hourly
# Months 4–12 (91–365): daily
EXTRACTION_TIERS = [
    ("hourly",   1,  30),
    ("8hourly", 31,  90),
    ("daily",   91, 365),
]


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], label: str, exit_on_fail: bool = True,
         capture: bool = False) -> Tuple[int, str, str]:
    """Run a command, log output, return (exit_code, stdout, stderr)."""
    log.info("── %s ──", label)
    log.debug("  CMD: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=7200,  # 2h per phase — archive uploads can be slow
        )
    except subprocess.TimeoutExpired:
        log.error("  TIMEOUT: %s (7200s)", label)
        if exit_on_fail:
            sys.exit(1)
        return (124, "", "timeout after 7200s")

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        for line in stdout.splitlines()[-20:]:
            log.info("  | %s", line)
    if stderr:
        for line in stderr.splitlines()[-10:]:
            log.warning("  ! %s", line)

    if result.returncode != 0:
        log.error("  FAILED (exit %d): %s", result.returncode, label)
        if exit_on_fail:
            sys.exit(result.returncode)
    else:
        log.info("  ✓ %s complete", label)

    if capture:
        return (result.returncode, stdout, stderr)
    return (result.returncode, stdout, stderr)


# ---------------------------------------------------------------------------
# Phase 1 — Decode
# ---------------------------------------------------------------------------

def phase_decode(pending_dir: Optional[str] = None) -> None:
    """Run decode_meter, decode_odo, calc_needle in order."""
    from water_meter.core.common import PENDING_DIR

    batch_dir = pending_dir or PENDING_DIR

    # 1a. decode_meter — scan images
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "decode_meter.py"),
         "--batch-dir", batch_dir],
        "Phase 1a: decode_meter",
    )

    # 1b. decode_odo — decode digit crops
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "decode_odo.py"),
         "--batch", "--db-update" ],
        "Phase 1b: decode_odo",
    )

    # 1c. auto_anchor_n00 — store pos5 drum-digit matches at n00 frames
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "auto_anchor_n00.py")],
        "Phase 1c: auto_anchor_n00",
    )

    # 1d. calc_needle — combine visual digits + needle wraps → readings
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "calc_needle_readings.py")],
        "Phase 1d: calc_needle_readings",
    )

    # 1e. pick_rotation_anchors — flag single best frame per needle rotation cycle
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "pick_rotation_anchors.py")],
        "Phase 1e: pick_rotation_anchors",
    )


# ---------------------------------------------------------------------------
# Phase 2 — Anchor Review
# ---------------------------------------------------------------------------

def phase_anchors(interactive: bool = False) -> None:
    """Suggest anchor candidates, optionally let user review, then recalc."""
    # 2a. suggest_anchors — find candidates
    log.info("── Phase 2a: suggest_anchors (listing candidates) ──")
    cmd = [PYTHON, os.path.join(SCRIPTS_DIR, "suggest_anchors.py")]
    _run(cmd, "Phase 2a: suggest_anchors", exit_on_fail=False)

    # 2b. Interactive review (if requested)
    if interactive:
        log.info("── Phase 2b: anchor review ──")
        if not sys.stdin.isatty():
            log.warning("  stdin is not a TTY — skipping interactive review. "
                        "Use --approve with suggest_anchors.py manually.")
        else:
            resp = input("\n  Review anchor candidates interactively? [y/N] ")
            if resp.strip().lower() == "y":
                _run(
                    [PYTHON, os.path.join(SCRIPTS_DIR, "suggest_anchors.py"),
                     "--interactive"],
                    "Phase 2b: interactive review",
                    exit_on_fail=False,
                )

                resp2 = input("\n  Anchors approved. Recalculate odo_needle values? [y/N] ")
                if resp2.strip().lower() == "y":
                    _run(
                        [PYTHON, os.path.join(SCRIPTS_DIR, "calc_needle_readings.py")],
                        "Phase 2c: recalc_needle (with anchors)",
                    )
                else:
                    log.info("  Skipping recalculation. Run manually with: "
                             "calc_needle_readings.py")
            else:
                log.info("  Skipping interactive review.")
    else:
        log.info("  Non-interactive mode — anchor candidates listed above. "
                 "Review and approve manually, then re-run calc_needle_readings.")


# ---------------------------------------------------------------------------
# Phase 3 — Flag, Copy Keepers & Archive
# ---------------------------------------------------------------------------

def _copy_keepers(execute: bool = False) -> int:
    """Copy preserved/important source images from scanned/ to keepers/YYYY-MM-DD/.

    Query the DB for all rows where notes contain 'preserve' (set by
    flag_important.py and decode_odo.py).  For each, locate the source
    image in scanned/ and hard-link it into keepers/.  This keeps a
    local copy after archive_images.py removes the scanned/ folder.

    Returns count of images copied.
    """
    from water_meter.core.common import SCANNED_DIR, KEEPERS_DIR
    from water_meter.core.db import MeterReading, get_session

    log.info("── Phase 3b: copy keepers ──")
    os.makedirs(KEEPERS_DIR, exist_ok=True)

    copied = 0
    not_found = 0
    already_present = 0

    with get_session() as session:
        # Find all rows with preserve set in notes
        rows = session.query(MeterReading).filter(
            MeterReading.notes.like('%preserve%')
        ).all()

        log.info("  Found %d preserved rows in DB", len(rows))

        for row in rows:
            if not row.image_name:
                continue
            if not row.capture_ts:
                continue

            date_dir = row.capture_ts.strftime("%Y-%m-%d")
            src = os.path.join(SCANNED_DIR, date_dir, row.image_name)

            # Also try flat scanned/ (legacy)
            if not os.path.isfile(src):
                src = os.path.join(SCANNED_DIR, row.image_name)

            if not os.path.isfile(src):
                # Also try pending/
                from water_meter.core.common import PENDING_DIR
                pending_src = os.path.join(PENDING_DIR, date_dir, row.image_name)
                if os.path.isfile(pending_src):
                    src = pending_src
                else:
                    pending_flat = os.path.join(PENDING_DIR, row.image_name)
                    if os.path.isfile(pending_flat):
                        src = pending_flat
                    else:
                        not_found += 1
                        continue

            dest_dir = os.path.join(KEEPERS_DIR, date_dir)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, row.image_name)

            if os.path.isfile(dest):
                already_present += 1
                continue

            if execute:
                try:
                    # Use hard link when possible (same filesystem), copy as fallback
                    os.link(src, dest)
                except OSError:
                    shutil.copy2(src, dest)
            copied += 1

    log.info("  Copied: %d  Already present: %d  Not found: %d",
             copied, already_present, not_found)
    return copied


def phase_flag_and_archive(execute: bool = False) -> None:
    """Flag important frames, copy keepers, archive completed days, reupload failures."""
    # 3a. flag_keepers — mark first/last/best/important frames for preservation
    _run(
        [PYTHON, os.path.join(SCRIPTS_DIR, "flag_keepers.py")],
        "Phase 3a: flag_keepers",
    )

    # 3b. copy keepers — preserve important source images locally
    _copy_keepers(execute=execute)

    # 3c. archive_images
    archive_cmd = [PYTHON, os.path.join(SCRIPTS_DIR, "archive_images.py")]
    if execute:
        archive_cmd.append("--auto")
    _run(archive_cmd, "Phase 3c: archive_images")

    # 3d. reupload_archives
    reup_cmd = [PYTHON, os.path.join(SCRIPTS_DIR, "reupload_archives.py")]
    if execute:
        reup_cmd.append("--auto")
    _run(reup_cmd, "Phase 3d: reupload_archives")


# ---------------------------------------------------------------------------
# Phase 4 — Cleanup
# ---------------------------------------------------------------------------

def phase_cleanup(execute: bool = False) -> None:
    """Delete non-preserved crops, old debug files, empty dirs."""
    cmd = [PYTHON, os.path.join(SCRIPTS_DIR, "cleanup.py")]
    if execute:
        cmd.append("--auto")
    _run(cmd, "Phase 4: cleanup")


# ---------------------------------------------------------------------------
# Phase 5 — Extract Tiered Readings
# ---------------------------------------------------------------------------

def phase_extract(output_file: Optional[str] = None) -> None:
    """Extract readings with tiered density: hourly → 8hourly → daily."""
    today = datetime.now(timezone.utc).date()
    extract_script = os.path.join(SCRIPTS_DIR, "extract_readings.py")

    # Collect all outputs first (avoid interleaving with log lines)
    all_lines: List[str] = []
    header = "date,reading,source,npos,image_name"

    for strategy, day_start, day_end in EXTRACTION_TIERS:
        start_date = (today - timedelta(days=day_end)).isoformat()
        end_date = (today - timedelta(days=day_start - 1)).isoformat()

        log.info("── Phase 5: extract (%s) %s → %s ──",
                 strategy, start_date, end_date)

        cmd = [
            PYTHON, extract_script,
            "--strategy", strategy,
            "--start-date", start_date,
            "--end-date", end_date,
        ]
        exit_code, stdout, stderr = _run(
            cmd,
            f"extract {strategy} {start_date}..{end_date}",
            exit_on_fail=False,
            capture=True,
        )

        if exit_code != 0:
            log.warning("  Extraction tier '%s' failed — skipping.", strategy)
            continue

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line == header:
                continue  # skip duplicate headers
            all_lines.append(line)

    # Output
    if output_file and output_file != "-":
        with open(output_file, "w") as f:
            f.write(header + "\n")
            for line in all_lines:
                f.write(line + "\n")
        log.info("  Readings written to %s (%d rows)", output_file, len(all_lines))
    else:
        print(header)
        for line in all_lines:
            print(line)
        log.info("  %d reading rows on stdout", len(all_lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Water Meter Pipeline — full decode → extract wrapper"
    )
    p.add_argument(
        "--pending-dir",
        help="Override pending image directory (default from common.py)",
    )
    p.add_argument(
        "--interactive", action="store_true",
        help="Pause for interactive anchor review (requires display)",
    )
    p.add_argument(
        "--execute", action="store_true",
        help="Execute archive/cleanup (actually upload/delete). "
             "Default is dry-run for destructive phases.",
    )
    p.add_argument(
        "--auto", action="store_true",
        help="Auto mode — equivalent to --execute, no confirmation prompts",
    )
    p.add_argument(
        "--skip-decode", action="store_true",
        help="Skip Phase 1 (decode_meter + decode_odo + calc_needle)",
    )
    p.add_argument(
        "--skip-anchors", action="store_true",
        help="Skip Phase 2 (suggest/review anchors)",
    )
    p.add_argument(
        "--skip-archive", action="store_true",
        help="Skip Phase 3 (flag + archive + reupload)",
    )
    p.add_argument(
        "--skip-cleanup", action="store_true",
        help="Skip Phase 4 (cleanup)",
    )
    p.add_argument(
        "--skip-extract", action="store_true",
        help="Skip Phase 5 (extract readings CSV)",
    )
    p.add_argument(
        "--output", "-o", type=str, default="-",
        help="CSV output path (default: stdout)",
    )
    p.add_argument(
        "--debug", action="store_true",
        help="Verbose logging",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    execute_mode = args.execute or args.auto

    log.info("=" * 60)
    log.info("Water Meter Pipeline")
    log.info("  Execute mode: %s", "YES" if execute_mode else "DRY RUN")
    log.info("  Interactive:  %s", "YES" if args.interactive else "no")
    log.info("=" * 60)

    # ── Phase 1: Decode ──
    if not args.skip_decode:
        phase_decode(pending_dir=args.pending_dir)
    else:
        log.info("── Phase 1: SKIPPED (--skip-decode)")

    # ── Phase 2: Anchors ──
    if not args.skip_anchors:
        phase_anchors(interactive=args.interactive)
    else:
        log.info("── Phase 2: SKIPPED (--skip-anchors)")

    # ── Phase 3: Flag, Copy Keepers & Archive ──
    if not args.skip_archive:
        phase_flag_and_archive(execute=execute_mode)
    else:
        log.info("── Phase 3: SKIPPED (--skip-archive)")

    # ── Phase 4: Cleanup ──
    if not args.skip_cleanup:
        phase_cleanup(execute=execute_mode)
    else:
        log.info("── Phase 4: SKIPPED (--skip-cleanup)")

    # ── Phase 5: Extract ──
    if not args.skip_extract:
        phase_extract(output_file=args.output)
    else:
        log.info("── Phase 5: SKIPPED (--skip-extract)")

    log.info("=" * 60)
    log.info("Pipeline complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()