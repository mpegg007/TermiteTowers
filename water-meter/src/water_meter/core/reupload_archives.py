#!/usr/bin/env python3
"""Re-upload staging zip files that failed or were never uploaded to Jottacloud.

Jottacloud's ``jotta-cli archive`` queues a job with the ``jottad`` daemon and
exits immediately — the daemon handles the actual upload in the background.
This script polls ``jotta-cli list uploads --json`` to track progress and
know when each file has completed.

Features:
  - Smart skip: compares local file size against Jottacloud remote size.
    Matching size → already uploaded → skip.
  - Duplicate detection: if a zip is already in the upload queue, waits for
    the daemon to finish it rather than queuing a second copy.
  - Progress polling: polls the daemon's upload queue every 10s, showing
    bytes remaining and estimated speed.
  - Generous timeout: 8 hours per file (configurable) — zips are hundreds of MB
    and connection quality varies widely.
  - Read-only by default (--dry-run).  Pass --execute to actually upload.
  - Never deletes local zips unless you pass --clean AND the upload verifies.

Usage:
    # Dry-run — list what would happen
    .venv/bin/python scripts/water_meter/reupload_archives.py

    # Execute uploads
    .venv/bin/python scripts/water_meter/reupload_archives.py --execute

    # Execute and delete local zips after verified upload
    .venv/bin/python scripts/water_meter/reupload_archives.py --execute --clean

    # Force re-upload even if remote size matches (e.g. after corruption)
    .venv/bin/python scripts/water_meter/reupload_archives.py --execute --force

    # Custom timeout per file (seconds)
    .venv/bin/python scripts/water_meter/reupload_archives.py --execute --timeout 28800
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.core.common import IMAGE_DIR, SCANNED_DIR

log = logging.getLogger("reupload_archives")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
JOTTA_CLI = "jotta-cli"
JOTTA_REMOTE_ROOT = "WaterMeter/Images"
STAGING_DIR = os.path.join(os.path.dirname(SCANNED_DIR), "staging")
PER_FILE_TIMEOUT = 28800  # 8 hours for large zips on slow connections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _list_local_zips() -> List[str]:
    """Return sorted list of zip paths in staging/."""
    if not os.path.isdir(STAGING_DIR):
        log.error("Staging directory not found: %s", STAGING_DIR)
        return []
    zips = sorted(
        os.path.join(STAGING_DIR, f)
        for f in os.listdir(STAGING_DIR)
        if f.startswith("water-meter-images-") and f.endswith(".zip")
    )
    if not zips:
        log.info("No zip files in %s", STAGING_DIR)
    return zips


def _fetch_remote_files() -> Dict[str, dict]:
    """Query Jottacloud for existing files in the archive folder.

    Returns {filename: {"Size": int, "Checksum": str}}.
    Returns empty dict on any failure (connection, auth, etc.).
    """
    cmd = [JOTTA_CLI, "ls", "--json", f"Archive/{JOTTA_REMOTE_ROOT}"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        if result.returncode != 0:
            log.warning("jotta-cli ls failed: %s", result.stderr.strip())
            return {}
        data = json.loads(result.stdout)
    except FileNotFoundError:
        log.error("jotta-cli not found on PATH (tried: %s)", JOTTA_CLI)
        return {}
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        log.warning("Failed to query Jottacloud: %s", e)
        return {}

    remote: Dict[str, dict] = {}
    for f in data.get("Files", []):
        name = f.get("Name")
        if name and name.startswith("water-meter-images-"):
            remote[name] = {"Size": f.get("Size", 0), "Checksum": f.get("Checksum", "")}
    return remote


def _get_upload_queue() -> List[dict]:
    """Return the current upload queue from the jottad daemon."""
    cmd = [JOTTA_CLI, "list", "uploads", "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
        if result.returncode != 0:
            log.warning("jotta-cli list uploads failed: %s", result.stderr.strip())
            return []
        return json.loads(result.stdout)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning("Failed to read upload queue: %s", e)
        return []


def _queue_upload(local_path: str, remote_rel: str) -> Optional[str]:
    """Queue a file for upload with jottad. Returns upload ID if queued, None on error.

    Uses devnull for stdin and pipes stdout/stderr to avoid subprocess deadlock
    with large output buffers.  Timeout is generous (120s) because the archive
    command may take a while to hand off to the daemon for large zips.
    """
    cmd = [JOTTA_CLI, "archive", local_path, f"--remote={remote_rel}", "--nogui"]
    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            text=True,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            log.error("  Failed to queue upload: %s", stderr or stdout or "unknown error")
            return None
        # jotta-cli archive returns no output on success. We'll look it up
        # in the queue by filename.
        return _find_upload_id(remote_rel)
    except subprocess.TimeoutExpired:
        log.error("  Timeout queuing upload (120s) — daemon may be hung")
        return None
    except FileNotFoundError:
        log.error("  jotta-cli not found on PATH")
        return None


def _find_upload_id(remote_rel: str) -> Optional[str]:
    """Find the upload ID for a given remote path in the queue."""
    # Give jottad a moment to register the job
    for attempt in range(3):
        queue = _get_upload_queue()
        for entry in queue:
            if f"/archive/{remote_rel}" in entry.get("Remote", ""):
                return entry.get("Id")
        if attempt < 2:
            time.sleep(2)
    return None


def _poll_upload(upload_id: str, local_size: int, timeout: int) -> bool:
    """Poll the daemon until the upload completes or times out.

    Prints progress every 10s. Returns True on completion, False on timeout/error.
    """
    start = time.time()
    last_remaining = local_size
    while True:
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            log.error("  TIMEOUT after %s — upload did not complete", _human_duration(elapsed))
            return False

        queue = _get_upload_queue()
        entry = _find_entry_by_id(queue, upload_id)
        if entry is None:
            # Upload ID vanished — could be completed and pruned from queue,
            # or could be an error. Check if remote file exists.
            log.info("  Upload ID %s no longer in queue", upload_id)
            return True  # assume completed if vanished

        total_bytes = entry.get("Total", {}).get("Bytes", local_size)
        remaining_bytes = entry.get("Remaining", {}).get("Bytes", 0)
        completed_ts = entry.get("CompletedTimeMs")
        has_error = bool(entry.get("Errors"))

        if completed_ts:
            if has_error:
                log.error("  Daemon reports upload error for %s", upload_id)
                return False
            elapsed = int(time.time() - start)
            transferred = total_bytes - remaining_bytes if remaining_bytes else total_bytes
            log.info("  ✓ Daemon reports upload complete in %s (%s transferred)",
                     _human_duration(elapsed), _human_size(transferred))
            return True

        # Progress heartbeat
        transferred = total_bytes - remaining_bytes
        pct = 100.0 * transferred / total_bytes if total_bytes > 0 else 0
        delta = transferred - (local_size - last_remaining)
        bps = delta / 10.0 if elapsed > 0 else 0
        last_remaining = remaining_bytes

        log.info("    … %s/%s (%.0f%%, %s) — %ds elapsed",
                 _human_size(transferred), _human_size(total_bytes),
                 pct, _human_speed(bps), elapsed)

        time.sleep(10)


def _find_entry_by_id(queue: List[dict], upload_id: str) -> Optional[dict]:
    """Find an upload entry by ID."""
    for e in queue:
        if e.get("Id") == upload_id:
            return e
    return None


def _find_entry_by_remote(queue: List[dict], remote_rel: str) -> Optional[dict]:
    """Find an upload entry matching a remote path."""
    target = f"/archive/{remote_rel}"
    for e in queue:
        if e.get("Remote") == target:
            return e
    return None


def _verify_remote_file(zip_name: str, local_size: int) -> bool:
    """Check that the remote file exists with the expected size."""
    remote = _fetch_remote_files()
    info = remote.get(zip_name)
    if info is None:
        return False
    return info["Size"] == local_size


def _human_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ("KB", "MB", "GB", "TB"):
        size_bytes /= 1024
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} PB"


def _human_speed(bytes_per_second: float) -> str:
    """Format transfer speed."""
    if bytes_per_second < 1:
        return "—"
    if bytes_per_second < 1024:
        return f"{bytes_per_second:.0f} B/s"
    kbps = bytes_per_second / 1024
    if kbps < 1024:
        return f"{kbps:.0f} KB/s"
    return f"{kbps / 1024:.1f} MB/s"


def _human_duration(seconds: int) -> str:
    """Format seconds into hh:mm:ss."""
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _jottad_alive() -> bool:
    """Return True if jottad daemon is reachable."""
    cmd = [JOTTA_CLI, "ls", "--json", f"Archive/{JOTTA_REMOTE_ROOT}"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "Could not connect to jottad" in stderr:
                log.error("jottad daemon is not running.")
                log.error("  Expected socket: unix:///run/user/1000/jottad/jottad.socket")
                log.error("  Start jottad with: jottad &")
                return False
            log.warning("jotta-cli ls failed: %s", stderr)
            return False
        return True
    except FileNotFoundError:
        log.error("jotta-cli not found on PATH (tried: %s)", JOTTA_CLI)
        return False
    except subprocess.TimeoutExpired:
        log.error("jotta-cli ls timed out — jottad may be hung")
        return False


def run_reupload(
    dry_run: bool = True,
    force: bool = False,
    clean: bool = False,
    timeout: int = PER_FILE_TIMEOUT,
) -> dict:
    """Main re-upload pass. Returns stats dict."""
    stats = {
        "dry_run": dry_run,
        "total": 0,
        "skipped": 0,
        "uploaded": 0,
        "failed": 0,
        "cleaned": 0,
        "errors": [],
    }

    local_zips = _list_local_zips()
    if not local_zips:
        return stats

    # Pre-flight: jottad must be running for any upload flow
    if not _jottad_alive():
        log.error("Aborted — jottad daemon is required for uploads.")
        stats["errors"].append("jottad daemon not reachable")
        return stats

    stats["total"] = len(local_zips)

    # Fetch remote state
    remote_files = _fetch_remote_files()
    log.info("  Found %d water-meter-images-*.zip files on Jottacloud",
             len(remote_files))

    # Fetch current upload queue — important for duplicate detection
    current_queue = _get_upload_queue()
    queue_by_remote: Dict[str, dict] = {}
    for e in current_queue:
        remote = e.get("Remote", "")
        if "/archive/WaterMeter/Images/" in remote:
            zip_name = os.path.basename(remote)
            queue_by_remote[zip_name] = e

    print()
    for i, local_path in enumerate(local_zips):
        zip_name = os.path.basename(local_path)
        try:
            local_size = os.path.getsize(local_path)
        except OSError as e:
            log.error("  Cannot stat %s: %s", zip_name, e)
            stats["errors"].append(f"{zip_name}: stat failed")
            continue

        remote_info = remote_files.get(zip_name)
        remote_rel = f"{JOTTA_REMOTE_ROOT}/{zip_name}"

        # --- Already on Jottacloud? ---
        if remote_info and remote_info["Size"] == local_size and not force:
            log.info("[%d/%d] SKIP  %s — already on Jotta (%s, size match)",
                     i + 1, len(local_zips), zip_name, _human_size(local_size))
            stats["skipped"] += 1
            if clean and not dry_run:
                try:
                    os.remove(local_path)
                    log.info("        Removed local zip: %s", zip_name)
                    stats["cleaned"] += 1
                except OSError as e:
                    log.warning("        Failed to remove %s: %s", zip_name, e)
            continue

        # --- Partial remote: wrong size → re-upload ---
        if remote_info:
            log.warning("[%d/%d] PARTIAL %s — remote %s ≠ local %s → re-uploading",
                        i + 1, len(local_zips), zip_name,
                        _human_size(remote_info["Size"]), _human_size(local_size))

        # --- Already in daemon queue? ---
        existing_queue_entry = queue_by_remote.get(zip_name)
        if existing_queue_entry and existing_queue_entry.get("CompletedTimeMs") is None:
            upload_id = existing_queue_entry["Id"]
            remaining = existing_queue_entry.get("Remaining", {}).get("Bytes", local_size)
            log.info("[%d/%d] QUEUED %s — already in daemon queue (id=%s, %s remaining)",
                     i + 1, len(local_zips), zip_name, upload_id,
                     _human_size(remaining))
            if dry_run:
                log.info("  [DRY RUN] Would wait for daemon to complete")
                continue

            log.info("  Waiting for daemon to finish …")
            if _poll_upload(upload_id, local_size, timeout):
                stats["uploaded"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{zip_name}: daemon upload failed/timed out")
                continue
        elif dry_run:
            log.info("[%d/%d] QUEUE %s — would upload to Jottacloud (%s)",
                     i + 1, len(local_zips), zip_name, _human_size(local_size))
            continue
        else:
            # --- Queue new upload ---
            upload_id = _queue_upload(local_path, remote_rel)
            if upload_id is None:
                log.error("[%d/%d] FAILED %s — could not queue upload",
                          i + 1, len(local_zips), zip_name)
                stats["failed"] += 1
                stats["errors"].append(f"{zip_name}: queue failed")
                continue

            log.info("[%d/%d] QUEUED %s (id=%s) — polling daemon …",
                     i + 1, len(local_zips), zip_name, upload_id)

            if _poll_upload(upload_id, local_size, timeout):
                stats["uploaded"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{zip_name}: upload failed/timed out")
                continue

        # --- Post-upload verify ---
        log.info("  Verifying remote presence …")
        verified = _verify_remote_file(zip_name, local_size)
        if verified:
            log.info("  ✓ Verified on Jottacloud (size match)")
        else:
            log.warning("  ⚠ Could not verify %s on Jottacloud — will NOT delete local zip",
                        zip_name)
            stats["errors"].append(f"{zip_name}: post-upload verification failed")
            continue

        # --- Clean up local zip if requested ---
        if clean:
            try:
                os.remove(local_path)
                log.info("  Removed local zip: %s", zip_name)
                stats["cleaned"] += 1
            except OSError as e:
                log.warning("  Failed to remove %s: %s", zip_name, e)

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(stats: dict):
    """Print a human-readable upload report."""
    print(f"\n{'='*60}")
    print("Staging Re-Upload Report")
    print(f"{'='*60}")
    print(f"Dry run:                  {'YES' if stats['dry_run'] else 'NO'}")
    print(f"Total zip files:          {stats['total']:>8}")
    print(f"Skipped (already there):  {stats['skipped']:>8}")
    print(f"Uploaded:                 {stats['uploaded']:>8}")
    print(f"Failed:                   {stats['failed']:>8}")
    print(f"Cleaned (local deleted):  {stats['cleaned']:>8}")

    errors = stats.get("errors", [])
    if errors:
        print(f"\n⚠  {len(errors)} error(s):")
        for e in errors:
            print(f"    {e}")

    if stats["dry_run"]:
        print(f"\nDRY RUN — no files were uploaded or deleted.")
        print(f"Run with --execute to actually upload.")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Re-upload staging zip files to Jottacloud (failed uploads)"
    )
    p.add_argument(
        "--execute", action="store_true",
        help="Actually upload files (not a dry run)",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Re-upload even if remote size matches (e.g. after corruption)",
    )
    p.add_argument(
        "--clean", action="store_true",
        help="Delete local zip after verified upload",
    )
    p.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt",
    )
    p.add_argument(
        "--auto", action="store_true",
        help="Auto mode — execute without confirmation prompt (for cron/pipeline)",
    )
    p.add_argument(
        "--timeout", type=int, default=PER_FILE_TIMEOUT,
        help=f"Per-file upload timeout in seconds (default: {PER_FILE_TIMEOUT}, 8 hours)",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    do_execute = args.execute or args.auto

    if do_execute:
        log.warning("EXECUTE mode — files WILL be uploaded to Jottacloud!")
        if not (args.yes or args.auto):
            response = input("\n⚠  Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                print("   Aborted.")
                sys.exit(0)

    stats = run_reupload(
        dry_run=not do_execute,
        force=args.force,
        clean=args.clean,
        timeout=args.timeout,
    )

    print_report(stats)


if __name__ == "__main__":
    main()