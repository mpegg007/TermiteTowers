#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/backup-mail.py@186 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 668e16d98c9cb127ce0a0994b3acacbe90d3af05 %
#  %ccm_git_commit_id: 39d8262239b8cbb295886dbe654023e96f65ada9 %
#  %ccm_git_commit_count: 186 %
#  %ccm_git_commit_date: 2026-10-28 11:35:25 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 3 - encrypt to per-tier keys %
#  %ccm_git_modify_date: 2026-10-28 11:35:26 %
#  %ccm_git_file_last_modified: 2026-10-28 11:33:37 %
#  %ccm_git_file_name: backup-mail.py %
#  %ccm_git_path: infra/backups/scripts/backup-mail.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 27302 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""Archive Thunderbird mbox folders into immutable, encrypted, per-period chunks.

Why
---
IMAP leaves a local copy of mail in the Thunderbird profile, but that copy is
only as safe as the disk it sits on. Once a message is deleted from the server,
the profile mbox is the last copy. This exports those mboxes into compressed,
age-encrypted chunks grouped by year (default) or month, so a dead disk does not
take the archive with it.

Design
------
* Chunks are immutable: once `mail-2025.tar.zst.age` exists it is never
  rewritten unless the number of messages for that period actually changes
  (late-arriving mail carrying an old Date header). The steady state therefore
  uploads one new file per period - it does NOT re-upload every old email on
  every run.
* Only *completed* periods are sealed by default. The period still in progress
  is skipped unless --include-current is given (then it is written as
  `*.partial.*` and rewritten as mail arrives).
* Nothing new is left in plaintext: messages stream tar -> zstd -> age. (The
  source mboxes are already plaintext on the same disk; no plaintext spool is
  created, unlike a naive extract-to-temp approach.)
* Two passes: pass 1 counts messages per period (headers only), pass 2 streams
  the periods that need (re)building into their pipelines. A full scan of
  ~19 GB / 153k messages takes ~30 s.
* Restorable: each tar member is a real mbox fragment starting with a `From `
  line, named after the original folder path, so it opens in Thunderbird or any
  mbox reader. Members are prefixed with the period so extracting never
  overwrites a live profile folder:

      mail-2018.tar.zst.age
        └── 2018/ImapMail/outlook.office365.com/Sent

Usage
-----
    backup-mail.py --dry-run              # report the plan, write nothing
    backup-mail.py                        # seal every completed period
    backup-mail.py --include-current      # also refresh the in-progress period
    backup-mail.py --only 2018            # (re)build one period
    backup-mail.py --granularity month    # finer chunks, more files
    backup-mail.py --list                 # show what is archived

Restore one period (two steps - the chunk's DEK must be unwrapped first;
the generation to unlock is recorded against each chunk in state.json):
    infra/backups/scripts/tt-keys.sh unlock mail:2026Q4 --out /dev/shm/mail.key
    age -d -i /dev/shm/mail.key mail-2018.tar.zst.age | zstd -d | tar -tvf -
    age -d -i /dev/shm/mail.key mail-2018.tar.zst.age | zstd -d | tar -xf - -C /tmp/restore
    shred -u /dev/shm/mail.key
Chunks sealed before the per-tier cutover are generation "legacy" and still
need ~/.config/age/tthealth-backup.txt instead.

Exit codes: 0 ok (or nothing to do) | 2 bad environment | 3 bad arguments
            4 pipeline/write failure | 5 verification failure
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from collections import Counter
from datetime import date, datetime
from email.parser import BytesHeaderParser
from email.utils import parsedate_to_datetime
from pathlib import Path

VERSION = 1
APP = "backup-mail"

SEP = b"\nFrom "
BLANK = re.compile(rb"\r?\n\r?\n")
HEADER_PARSER = BytesHeaderParser()

# Files that live next to the mboxes but are not mail.
SKIP_SUFFIXES = (
    ".msf", ".dat", ".json", ".bak",
    ".sqlite", ".sqlite-wal", ".sqlite-shm", ".lock", ".tmp",
)
DEFAULT_EXCLUDE = ("Trash", "Junk", "Junk E-mail", "Deleted Items", "Spam")

REPO_DIR = Path(__file__).resolve().parents[3]
AGE_DIR = REPO_DIR / "infra" / "backups" / "age"
REGISTRY = AGE_DIR / "registry.json"
# Mail is its own classification tier: a personal-mail archive must never share
# a key with the PHI database (see infra/backups/README.md, "Per-tier keys").
DEFAULT_TIER = "mail"
DEFAULT_RECIPIENT = AGE_DIR / f"{DEFAULT_TIER}.recipient"
DEFAULT_OUT = Path("/mnt/ai_storage/backups/thunderbird")


def log(level: str, msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level:<5}] {msg}", flush=True)


class Fail(Exception):
    """Fatal condition carrying an exit code."""

    def __init__(self, msg: str, code: int = 4) -> None:
        super().__init__(msg)
        self.code = code


# --------------------------------------------------------------------------
# profile / source discovery
# --------------------------------------------------------------------------
def find_profile(explicit: str | None) -> Path:
    if explicit:
        prof = Path(explicit).expanduser()
        if not prof.is_dir():
            raise Fail(f"profile directory not found: {prof}", 3)
        return prof

    home = Path.home()
    # (profiles.ini path, directory its relative profile paths resolve against)
    candidates = [
        (home / "snap/thunderbird/current/.config/thunderbird/profiles.ini",
         home / "snap/thunderbird/current/.config/thunderbird"),
        (home / ".thunderbird/profiles.ini", home / ".thunderbird"),
        (home / ".mozilla-thunderbird/profiles.ini", home / ".mozilla-thunderbird"),
        (home / ".var/app/org.mozilla.Thunderbird/.thunderbird/profiles.ini",
         home / ".var/app/org.mozilla.Thunderbird/.thunderbird"),
    ]

    found: list[Path] = []
    for ini_path, base in candidates:
        if not ini_path.is_file():
            continue
        parser = configparser.ConfigParser()
        try:
            with open(ini_path, encoding="utf-8", errors="replace") as fh:
                parser.read_string(fh.read(), source=str(ini_path))
        except (OSError, configparser.Error):
            continue
        for section in parser.sections():
            if not section.startswith("Profile"):
                continue
            raw = parser.get(section, "Path", fallback="").strip()
            if not raw:
                continue
            relative = parser.get(section, "IsRelative", fallback="1").strip() in (
                "1", "true", "yes")
            prof = (base / raw) if relative else Path(raw).expanduser()
            if prof.is_dir():
                found.append(prof)

    # Prefer a profile that actually contains mail.
    for prof in found:
        if (prof / "ImapMail").is_dir() or (prof / "Mail").is_dir():
            return prof
    if found:
        return found[0]
    raise Fail("no Thunderbird profile found - pass --profile PATH", 2)


def is_mbox(path: Path) -> bool:
    """An mbox always starts with a 'From ' separator line."""
    try:
        with open(path, "rb") as fh:
            return fh.read(5) == b"From "
    except OSError:
        return False


def find_sources(root: Path, exclude: set[str]) -> list[Path]:
    """Every mbox under a Mail/ or ImapMail/ tree (descends into *.sbd/)."""
    sources: list[Path] = []
    if not root.is_dir():
        return sources
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(SKIP_SUFFIXES) or path.name.startswith("."):
            continue
        try:
            if path.name in exclude or path.stat().st_size == 0:
                continue
        except OSError:
            continue
        sources.append(path)
    return sources


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def iter_messages(path: Path, chunk_size: int = 1 << 20):
    """Yield each message's exact bytes, starting with its b'From ' line.

    Messages are delimited by '\\nFrom ' (body lines beginning with 'From ' are
    escaped as '>From ' in mbox, so this only matches real boundaries). The
    separator's leading newline stays with the *following* message, so
    concatenating the yielded bytes - with a '\\n' appended to each - reproduces
    the original file byte for byte.
    """
    with open(path, "rb") as fh:
        buf = b""
        first = True
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            buf += block
            if first:
                first = False
                if not buf.startswith(b"From "):
                    cut = buf.find(SEP)
                    if cut < 0:
                        buf = b""
                        continue
                    buf = buf[cut + 1:]
            start = 0
            while True:
                idx = buf.find(SEP, start)
                if idx < 0:
                    break
                yield buf[start:idx]
                start = idx + 1
            buf = buf[start:]
        if buf:
            yield buf


def period_of(raw: bytes, granularity: str) -> str:
    """Year ('2025') or year-month ('2025-10') for a message, from its headers."""
    match = BLANK.search(raw)
    head = raw if match is None else raw[: match.start()]
    fmt = "%Y" if granularity == "year" else "%Y-%m"
    try:
        msg = HEADER_PARSER.parsebytes(head)
    except Exception:
        return "undated"

    value = msg.get("Date")
    if value:
        try:
            return parsedate_to_datetime(value).strftime(fmt)
        except Exception:
            pass
    # Sent items and some Exchange copies carry no Date: fall back to Received.
    for received in reversed(msg.get_all("Received") or []):
        try:
            return parsedate_to_datetime(received.rsplit(";", 1)[-1].strip()).strftime(fmt)
        except Exception:
            continue
    return "undated"


def period_end(period: str) -> date | None:
    """Last day of a period, or None when it cannot be determined."""
    try:
        if re.fullmatch(r"\d{4}", period):
            return date(int(period), 12, 31)
        if re.fullmatch(r"\d{4}-\d{2}", period):
            year, month = int(period[:4]), int(period[5:])
            if month == 12:
                return date(year, 12, 31)
            return date.fromordinal(date(year, month + 1, 1).toordinal() - 1)
    except ValueError:
        return None
    return None


def is_complete(period: str, today: date) -> bool:
    """True once the period has finished, i.e. it can be sealed for good."""
    end = period_end(period)
    return end is not None and end < today


# --------------------------------------------------------------------------
# encrypted chunk pipeline: tar -> zstd -> age
# --------------------------------------------------------------------------
class ChunkWriter:
    """Streams tar members into zstd into age, producing one chunk file."""

    def __init__(self, final: Path, recipient: Path, threads: int = 0) -> None:
        self.final = final
        self.tmp: Path | None = final.with_name(final.name + ".part")
        self.members = 0
        self.bytes = 0
        final.parent.mkdir(parents=True, exist_ok=True)
        if self.tmp.exists():
            self.tmp.unlink()
        self.enc = subprocess.Popen(
            ["age", "--encrypt", "--recipients-file", str(recipient),
             "--output", str(self.tmp)],
            stdin=subprocess.PIPE,
        )
        self.zst = subprocess.Popen(
            ["zstd", "-q", f"-T{threads}", "-c"],
            stdin=subprocess.PIPE, stdout=self.enc.stdin,
        )
        self.tar = tarfile.open(fileobj=self.zst.stdin, mode="w|")

    def add(self, name: str, data: bytes, mtime: float) -> None:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mtime = int(mtime)
        info.mode = 0o600
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        self.tar.addfile(info, io.BytesIO(data))
        self.members += 1
        self.bytes += len(data)

    def finish(self) -> Path:
        self.tar.close()
        self.zst.stdin.close()
        if self.zst.wait() != 0:
            self._abort("zstd failed")
        self.enc.stdin.close()
        if self.enc.wait() != 0:
            self._abort("age failed")
        if not self.tmp or not self.tmp.is_file() or self.tmp.stat().st_size == 0:
            self._abort("age produced no output")
        with open(self.tmp, "rb") as fh:
            if fh.read(21) != b"age-encryption.org/v1":
                self._abort("output is not an age file")
        os.chmod(self.tmp, 0o600)
        os.replace(self.tmp, self.final)
        self.tmp = None
        return self.final

    def _abort(self, why: str) -> None:
        if self.tmp and self.tmp.exists():
            self.tmp.unlink()
        raise Fail(f"{why} for {self.final.name}", 4)


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"version": VERSION, "periods": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot read state {path}: {exc}", 2)
    state.setdefault("periods", {})
    return state


def save_state(path: Path, state: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def chunk_name(period: str, today: date) -> str:
    partial = period != "undated" and not is_complete(period, today)
    return f"mail-{period}{'.partial' if partial else ''}.tar.zst.age"


def generation_of(tier: str, recipient: Path) -> str:
    """Current generation label for a tier.

    The public registry is authoritative when present; the fallback parses the
    recipient file's own header ("... | generation: 2026Q4 | ..."), which is how
    an installed-only layout works. There is no default generation: a chunk that
    cannot name the key it needs is not restorable, so this fails instead.
    """
    if REGISTRY.is_file():
        try:
            with open(REGISTRY, encoding="utf-8") as fh:
                current = json.load(fh).get("tiers", {}).get(tier, {}).get("current")
            if current:
                return str(current)
        except (OSError, json.JSONDecodeError):
            pass
    try:
        with open(recipient, encoding="utf-8") as fh:
            for line in fh:
                if not line.lstrip().startswith("#") or "generation:" not in line:
                    continue
                fields = {}
                for field in line.split("|"):
                    key, _, value = field.partition(":")
                    fields[key.strip("# ").strip()] = value.strip()
                gen = fields.get("generation", "")
                if not gen:
                    continue
                # The header names its own tier: refuse to hand back a
                # generation belonging to a different classification.
                header_tier = fields.get("tier", "")
                if header_tier and header_tier != tier:
                    raise Fail(f"{recipient} belongs to tier '{header_tier}', "
                               f"not '{tier}'", 3)
                return gen
    except OSError:
        pass
    raise Fail(f"cannot determine the {tier} generation from {REGISTRY} "
               f"or {recipient}", 3)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog=APP,
        description="Archive Thunderbird mail into encrypted per-period chunks.",
        epilog="restore: infra/backups/scripts/tt-keys.sh unlock mail:2026Q4 "
               "--out /dev/shm/mail.key, then age -d -i /dev/shm/mail.key CHUNK "
               "| zstd -d | tar -xf - -C /tmp/restore",
    )
    ap.add_argument("--profile", help="Thunderbird profile directory (auto-detected)")
    ap.add_argument("--extra-root", action="append", default=[], metavar="PATH",
                    help="additional Mail/ or ImapMail/ tree to archive, e.g. an old "
                         "snap revision's profile (repeatable)")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"output directory (default: {DEFAULT_OUT})")
    ap.add_argument("--tier", default=DEFAULT_TIER,
                    help=f"encryption tier, selects <tier>.recipient and the "
                         f"generation recorded per chunk (default: {DEFAULT_TIER})")
    ap.add_argument("--recipient", default="",
                    help="override the recipient file (default: <tier>.recipient)")
    ap.add_argument("--granularity", choices=("year", "month"), default="year",
                    help="chunk size (default: year)")
    ap.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDE),
                    help="comma-separated folder names to skip (default: %(default)s)")
    ap.add_argument("--include-current", action="store_true",
                    help="also (re)build the period still in progress, as *.partial")
    ap.add_argument("--only", metavar="PERIOD",
                    help="build just this period, e.g. 2018 or 2026-10")
    ap.add_argument("--max-periods", type=int, default=48,
                    help="cap chunks built per run (default: 48)")
    ap.add_argument("--fragment-cap", type=int, default=64, metavar="MB",
                    help="max size of one mbox fragment before it is split into "
                         "numbered parts (default: 64)")
    ap.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
    ap.add_argument("--list", action="store_true", help="list archived periods and exit")
    ap.add_argument("--scan", action="store_true",
                    help="run 'jotta-cli scan' on the output folder afterwards")
    return ap.parse_args(argv)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    args = parse_args(argv)
    os.umask(0o077)          # state, chunks and temporary *.part stay private
    out_dir = Path(args.out).expanduser()
    state_path = out_dir / "state.json"
    recipient = (Path(args.recipient).expanduser() if args.recipient
                 else AGE_DIR / f"{args.tier}.recipient")

    state = load_state(state_path)

    if args.list:
        periods = state.get("periods", {})
        if not periods:
            log("INFO", f"nothing archived yet in {out_dir}")
            return 0
        total = sum(p.get("bytes", 0) for p in periods.values())
        log("INFO", f"{len(periods)} period(s) in {out_dir}: "
                    f"{total / 1e9:.2f} GB encrypted, "
                    f"{sum(p.get('messages', 0) for p in periods.values())} messages")
        for key in sorted(periods):
            entry = periods[key]
            # Pre-cutover chunks carry no tier: they were all sealed with the
            # single legacy identity, so name that rather than print "?".
            log("INFO", f"  {key:<10} {entry.get('messages', 0):>7} msgs  "
                        f"{entry.get('bytes', 0) / 1e6:>9.1f} MB  "
                        f"{entry.get('tier', 'pre-tier')}/"
                        f"{entry.get('generation', 'legacy'):<9} "
                        f"{entry.get('chunk', '')}")
        return 0

    for tool in ("age", "zstd"):
        if shutil.which(tool) is None:
            raise Fail(f"{tool} not found in PATH", 2)

    profile = find_profile(args.profile)
    exclude = {name.strip() for name in args.exclude.split(",") if name.strip()}

    # (member-name prefix, absolute path) for every mbox we intend to archive
    sources: list[tuple[str, Path]] = []
    for path in find_sources(profile / "ImapMail", exclude) + \
            find_sources(profile / "Mail", exclude):
        if is_mbox(path):
            sources.append((str(path.relative_to(profile)), path))
    for extra in args.extra_root:
        extra_root = Path(extra).expanduser()
        if not extra_root.is_dir():
            raise Fail(f"--extra-root not a directory: {extra_root}", 3)
        # Stable, unambiguous prefix even when two trees share a basename
        # (e.g. the same profile under two snap revisions).
        digest = hashlib.sha1(str(extra_root.resolve()).encode()).hexdigest()[:8]
        label = f"extra-{extra_root.name}-{digest}"
        for path in find_sources(extra_root, exclude):
            if is_mbox(path):
                sources.append((f"{label}/{path.relative_to(extra_root)}", path))

    if not sources:
        raise Fail(f"no mbox files found under {profile}", 2)

    log("INFO", f"profile : {profile}")
    log("INFO", f"sources : {len(sources)} mbox files, "
                f"{sum(p.stat().st_size for _, p in sources) / 1e9:.2f} GB")
    log("INFO", f"output  : {out_dir}  (granularity: {args.granularity})")

    # --- pass 1: count messages per period (headers only) -----------------
    started = time.time()
    counts: Counter[str] = Counter()
    for _rel, path in sources:
        for raw in iter_messages(path):
            counts[period_of(raw, args.granularity)] += 1
    log("INFO", f"pass 1  : {sum(counts.values())} messages in {len(counts)} period(s), "
                f"{time.time() - started:.1f}s")

    today = date.today()
    known = state.get("periods", {})
    build: list[str] = []
    for period in sorted(counts):
        if args.only and period != args.only:
            continue
        # --only always wins: it may target the period still in progress.
        if not args.only and not args.include_current \
                and period != "undated" and not is_complete(period, today):
            continue
        entry = known.get(period) or {}
        chunk = out_dir / entry["chunk"] if entry.get("chunk") else None
        # A sealed chunk is rebuilt only when its message count actually moved,
        # and never when the name drifted (partial -> sealed at a period boundary).
        unchanged = (chunk is not None and chunk.is_file()
                     and chunk.name == chunk_name(period, today)
                     and entry.get("messages") == counts[period])
        if not unchanged:
            build.append(period)

    log("INFO", f"plan    : {len(build)} to build, {len(counts) - len(build)} up to date")
    for period in build[: args.max_periods]:
        log("INFO", f"  build {period:<10} {counts[period]:>7} msgs"
                    f"{'  (rebuild)' if period in known else ''}")
    if len(build) > args.max_periods:
        log("INFO", f"  ... {len(build) - args.max_periods} deferred to the next run "
                    f"(--max-periods {args.max_periods})")

    if args.dry_run:
        log("INFO", "dry-run : nothing written")
        return 0
    if not build:
        log("INFO", "nothing to do")
        return 0
    if not recipient.is_file():
        raise Fail(f"age recipient file missing: {recipient} "
                   f"(run infra/backups/scripts/tt-keys.sh init)", 2)
    generation = generation_of(args.tier, recipient)
    log("INFO", f"tier    : {args.tier}/{generation}  ({recipient.name})")

    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)

    # --- pass 2: stream each due period into its own pipeline -------------
    due = build[: args.max_periods]
    frag_cap = max(1, args.fragment_cap) * 1024 * 1024
    # Many chunks in flight share the cores; a lone chunk takes all of them.
    zstd_threads = 0 if len(due) <= 2 else 1
    writers: dict[str, ChunkWriter] = {}
    try:
        for period in due:
            writers[period] = ChunkWriter(
                out_dir / chunk_name(period, today), recipient, zstd_threads)

        for rel, path in sources:
            mtime = path.stat().st_mtime
            # One tar member per (period, folder): a real mbox fragment holding
            # every message of that folder for that period. Buffered per source
            # file only, and split into numbered parts once it exceeds the cap,
            # so memory stays bounded without ever spilling plaintext to disk.
            buffers: dict[str, bytearray] = {}
            parts: dict[str, int] = {}
            for raw in iter_messages(path):
                period = period_of(raw, args.granularity)
                writer = writers.get(period)
                if writer is None:
                    continue          # not due yet; picked up by a later run
                if not raw.endswith(b"\n"):
                    raw += b"\n"
                buf = buffers.setdefault(period, bytearray())
                buf += raw
                if len(buf) >= frag_cap:
                    index = parts.get(period, 0) + 1
                    parts[period] = index
                    name = f"{period}/{rel}" + ("" if index == 1 else f".part{index}")
                    writer.add(name, bytes(buf), mtime)
                    buffers[period] = bytearray()
            for period, buf in buffers.items():
                if not buf:
                    continue
                index = parts.get(period, 0) + 1
                name = f"{period}/{rel}" + ("" if index == 1 else f".part{index}")
                writers[period].add(name, bytes(buf), mtime)

        for period, writer in writers.items():
            final = writer.finish()
            entry = {
                "chunk": str(final.relative_to(out_dir)),
                "tier": args.tier,
                "generation": generation,
                "messages": counts[period],
                "members": writer.members,
                "mail_bytes": writer.bytes,
                "bytes": final.stat().st_size,
                "sha256": sha256_of(final),
                "written": datetime.now().isoformat(timespec="seconds"),
            }
            state.setdefault("periods", {})[period] = entry
            log("INFO", f"wrote   : {entry['chunk']}  {writer.members} member(s), "
                        f"{writer.bytes / 1e6:.1f} MB mail -> "
                        f"{entry['bytes'] / 1e6:.1f} MB encrypted")
    except BaseException:
        for writer in writers.values():
            if writer.tmp and writer.tmp.exists():
                writer.tmp.unlink()
        raise
    finally:
        state["version"] = VERSION
        state["granularity"] = args.granularity
        state["generated"] = datetime.now().isoformat(timespec="seconds")
        save_state(state_path, state)

    if args.scan and shutil.which("jotta-cli"):
        subprocess.run(["jotta-cli", "scan"], check=False)

    log("INFO", f"done    : {len(due)} chunk(s) in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fail as exc:
        log("ERROR", str(exc))
        sys.exit(exc.code)
    except KeyboardInterrupt:
        log("ERROR", "interrupted")
        sys.exit(130)
