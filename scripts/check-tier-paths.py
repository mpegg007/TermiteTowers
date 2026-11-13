#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/check-tier-paths.py@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c259169d6e2008206b292a7c94eeacfce168d460 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: check-tier-paths.py %
#  %ccm_git_path: scripts/check-tier-paths.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 18914 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""check-tier-paths.py — enforce that a tier-named compose file only touches
that tier's host paths.

WHY THIS EXISTS
    The compose project name, container names and networks are already per tier
    (see plans/per-tier-secrets.md). Host bind mounts are NOT: every one is
    /mnt/ai_storage/<svc>/... with no tier segment. So if nextcloud-prd1.yml is
    created by copying the dev1 file and changing only `name:` and the env path,
    both tiers mount the SAME directory. A dev1 test that migrates a database or
    prunes files then operates on prd's bytes.

    This script turns "I hope I remembered to change the path" into a check that
    fails. It is the rule from plans/per-tier-secrets.md §3:

        In a file named *-<tier>.yml, every absolute path (bind-mount source,
        env_file, build context, secrets/configs file) must contain <tier> as a
        path component, or match an entry in a small reviewed allowlist.

CHECKS
    PATH_TIER   absolute path with no <tier> component, not allowlisted.
                The wrong-tier path — this is the accident this exists to stop.
    REL_ENV     env_file / secrets / configs `file:` given as a RELATIVE path.
                Relative env files live under infra/docker/env/, which
                .gitignore excludes, so a deployed tree (/srv/<tier>/tt, produced
                by rsync of tracked files only) has no such file and the service
                will not start. Also silently resolves to the wrong tier's file
                if the tree ever holds both.
    SHARED_RW   an allowlisted path whose allowlist mode is `must-ro` is mounted
                read-write. Covers the dev1-instance-has-write-access-to-the-
                photo-library case.

BASELINE RATCHET
    Today every host path is tier-less, so a hard check would be red immediately
    and stay red, which teaches everyone to ignore it. Instead the current
    violations are recorded in tier-path-baseline.txt: CI fails only on violations
    NOT in that file, and the baseline's line count is the visible work queue.
    As paths are migrated, re-run with --baseline-write so the file shrinks.
    When it is empty, add --strict to CI and delete the baseline.

USAGE
    scripts/check-tier-paths.py                     # check all, ratcheted
    scripts/check-tier-paths.py --baseline-write    # accept current state
    scripts/check-tier-paths.py --strict            # ignore baseline; fail on all
    scripts/check-tier-paths.py --json              # machine-readable
    scripts/check-tier-paths.py infra/docker/immich-dev1.yml   # subset (hook)

EXIT
    0  no violations outside the baseline
    1  at least one new violation
    2  usage or configuration error
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys

TIER_RE = re.compile(r"(?<![A-Za-z0-9])(dev\d+|uat\d+|prd\d*)(?![A-Za-z0-9])")

DEFAULT_COMPOSE_DIR = "infra/docker"
DEFAULT_ALLOWLIST = "infra/docker/tier-path-allowlist.conf"
DEFAULT_BASELINE = "infra/docker/tier-path-baseline.txt"

# Keys whose *items* are host paths.
PATH_LIST_KEYS = {"env_file", "volumes"}
# Keys whose *value* is a host path, when found inside the given parent key.
PATH_VALUE_KEYS = {
    "context": {"build"},      # build.context
    "file": {"secrets", "configs"},  # secrets.<n>.file
    "source": {"volumes"},     # long-form volumes[].source
}

CLASS_PATH_TIER = "PATH_TIER"
CLASS_REL_ENV = "REL_ENV"
CLASS_SHARED_RW = "SHARED_RW"

CLASS_ORDER = [CLASS_PATH_TIER, CLASS_REL_ENV, CLASS_SHARED_RW]

CLASS_HELP = {
    CLASS_PATH_TIER: "absolute path carries no tier segment",
    CLASS_REL_ENV: "relative env/secret path; absent from deployed trees",
    CLASS_SHARED_RW: "shared path mounted read-write; must be :ro",
}


# --------------------------------------------------------------------------
# input parsing
# --------------------------------------------------------------------------
def strip_comment(line: str) -> str:
    """Drop a '#' comment that starts the line or follows whitespace.

    Commented-out mounts are common in these files (snipeit carries a whole
    usage block of absolute paths), and they must not be reported.
    """
    for i, ch in enumerate(line):
        if ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def split_volume_spec(spec: str):
    """Return (host_path, read_only) for a short-form bind, else None.

    A spec with no ':' is a container path / anonymous volume, not a host bind,
    so it is not ours to check.
    """
    spec = unquote(spec)
    if not spec.startswith("/"):
        return None
    parts = spec.split(":")
    if len(parts) < 2:
        return None
    host = parts[0]
    mode = parts[2] if len(parts) >= 3 else ""
    read_only = "ro" in [m.strip() for m in mode.split(",")]
    return host, read_only


def scan_compose(path: str, tier: str):
    """Yield findings for one compose file."""
    findings = []
    stack = []  # (indent, key)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}")

    def parent_keys():
        return {key for _, key in stack}

    def add(line_no, cls, subject, read_only=None, extra=""):
        findings.append(
            {
                "file": path,
                "line": line_no,
                "class": cls,
                "subject": subject,
                "read_only": read_only,
                "extra": extra,
            }
        )

    for idx, raw in enumerate(lines, 1):
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()

        # Pop deeper-or-equal scopes before interpreting this line.
        while stack and stack[-1][0] >= indent:
            stack.pop()

        key_match = re.match(r"^([A-Za-z_][\w.\-]*):\s*(.*)$", body)
        item_match = re.match(r"^-\s*(.*)$", body)

        if key_match:
            key, value = key_match.group(1), unquote(key_match.group(2))
            parents = parent_keys()

            if value:
                # Inline value for a path-valued key. Route through the same
                # absolute/relative split the list form uses: a relative
                # secrets/configs `file:` is REL_ENV, not PATH_TIER.
                if key in PATH_VALUE_KEYS and PATH_VALUE_KEYS[key] & parents:
                    check_list_entry(idx, key, value, add)
                elif key in PATH_LIST_KEYS:
                    inline = value
                    if inline.startswith("[") and inline.endswith("]"):
                        inline = inline[1:-1]
                    for piece in inline.split(","):
                        piece = unquote(piece)
                        if piece:
                            check_list_entry(idx, key, piece, add)
            stack.append((indent, key))
            continue

        if item_match:
            value = item_match.group(1)
            if not value:
                # '- key: value' long form; the key line itself follows.
                continue
            # A bare 'key: value' inside a list item (long-form mounts).
            inner = re.match(r"^([A-Za-z_][\w.\-]*):\s+(.*)$", value)
            if inner:
                continue
            parents = parent_keys()
            governing = next(
                (k for _, k in reversed(stack) if k in PATH_LIST_KEYS), None
            )
            if governing is None:
                continue
            if governing == "volumes":
                parsed = split_volume_spec(value)
                if parsed is None:
                    continue
                host, read_only = parsed
                add(idx, CLASS_PATH_TIER, host, read_only)
            else:  # env_file
                check_list_entry(idx, governing, unquote(value), add)

    return findings


def check_list_entry(line_no, key, entry, add):
    if not entry:
        return
    if entry.startswith("/"):
        add(line_no, CLASS_PATH_TIER, entry)
    else:
        add(line_no, CLASS_REL_ENV, entry)


# --------------------------------------------------------------------------
# allowlist
# --------------------------------------------------------------------------
def load_allowlist(path: str):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for idx, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                raise SystemExit(f"{path}:{idx}: expected '<glob> | <mode> | <reason>'")
            glob, mode = parts[0], parts[1]
            reason = parts[2] if len(parts) >= 3 else ""
            if mode not in ("ok", "must-ro"):
                raise SystemExit(f"{path}:{idx}: mode must be 'ok' or 'must-ro', got {mode!r}")
            entries.append({"glob": glob, "mode": mode, "reason": reason})
    return entries


def allowlist_match(entries, host_path):
    for entry in entries:
        if fnmatch.fnmatchcase(host_path, entry["glob"]):
            return entry
    return None


def tier_component(path: str, tier: str) -> bool:
    return tier in [p for p in path.split("/") if p]


# --------------------------------------------------------------------------
# baseline
# --------------------------------------------------------------------------
def resolve_against(path, repo_root):
    """Makes a relative config path repo-relative when it does not exist as given."""
    if os.path.isabs(path) or os.path.exists(path):
        return path
    candidate = os.path.join(repo_root, path)
    return candidate if os.path.exists(candidate) else path


def fingerprint(finding, repo_root):
    rel = os.path.relpath(finding["file"], repo_root)
    return f"{rel}|{finding['class']}|{finding['subject']}"


def load_baseline(path):
    if not os.path.exists(path):
        print(
            f"warning: baseline {path} not found; treated as empty "
            f"(run --baseline-write to accept current state)",
            file=sys.stderr,
        )
        return set()
    entries = set()
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            entries.add(line)
    return entries


def write_baseline(path, findings, repo_root):
    lines = sorted({fingerprint(f, repo_root) for f in findings})
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            "# tier-path-baseline.txt — known, accepted tier-path violations.\n"
            "#\n"
            "# Generated by scripts/check-tier-paths.py --baseline-write.\n"
            "# Format: <compose file>|<class>|<path>\n"
            "#\n"
            "# This file is the work queue, not a permission slip. Every line is a\n"
            "# host path a tier-named compose file touches without naming that tier.\n"
            "# Migrate the path, then re-run --baseline-write so the list shrinks.\n"
            "# When this file is empty, switch CI to --strict and delete it.\n"
            f"#\n# {len(lines)} entr{'y' if len(lines) == 1 else 'ies'}.\n"
        )
        for line in lines:
            fh.write(line + "\n")
    return len(lines)


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------
def evaluate(finding, allowlist):
    """Return None if acceptable, else (class, reason).

    The returned class can differ from the one the scanner assigned: a path the
    allowlist shares but demands read-only is reported as SHARED_RW, because the
    defect is the mount mode, not the missing tier segment.
    """
    if finding["class"] == CLASS_REL_ENV:
        return CLASS_REL_ENV, CLASS_HELP[CLASS_REL_ENV]

    subject = finding["subject"]
    tier = finding.get("tier", "")

    if tier and tier_component(subject, tier):
        return None

    match = allowlist_match(allowlist, subject)
    if match:
        if match["mode"] == "must-ro" and not finding.get("read_only"):
            return (
                CLASS_SHARED_RW,
                f"shared by design ({match['reason']}) but mounted read-write; "
                f"must be ':ro'",
            )
        return None

    return CLASS_PATH_TIER, CLASS_HELP[CLASS_PATH_TIER]


def main(argv):
    ap = argparse.ArgumentParser(
        description="Enforce tier separation of host paths in compose files.",
    )
    ap.add_argument("files", nargs="*", help="specific compose files to check")
    ap.add_argument("--compose-dir", default=DEFAULT_COMPOSE_DIR)
    ap.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--baseline-write", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo_root = args.repo_root or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # Resolve config paths against the repo root, not the caller's CWD. Run from
    # a subdirectory, a bare relative default silently resolves to nothing: the
    # allowlist would come back empty (so every shared path is reported) and the
    # baseline would be missing (so all known debt looks new). Fail loudly for an
    # explicitly named allowlist, fall back quietly for a missing baseline.
    allowlist_path = resolve_against(args.allowlist, repo_root)
    baseline_path = resolve_against(args.baseline, repo_root)

    allowlist = load_allowlist(allowlist_path)

    if args.files:
        candidates = args.files
    else:
        compose_dir = os.path.join(repo_root, args.compose_dir)
        if not os.path.isdir(compose_dir):
            raise SystemExit(f"compose dir not found: {compose_dir}")
        candidates = [
            os.path.join(compose_dir, name)
            for name in sorted(os.listdir(compose_dir))
            if name.endswith((".yml", ".yaml"))
        ]

    findings = []
    untiered = []
    for path in candidates:
        name = os.path.basename(path)
        tiers = TIER_RE.findall(name)
        if not tiers:
            untiered.append(name)
            continue
        tier = tiers[0]
        for finding in scan_compose(path, tier):
            finding["tier"] = tier
            verdict = evaluate(finding, allowlist)
            if verdict:
                finding["class"], finding["reason"] = verdict
                findings.append(finding)

    if args.baseline_write:
        count = write_baseline(baseline_path, findings, repo_root)
        print(f"baseline written: {baseline_path} ({count} entries)")
        return 0

    baseline = set() if args.strict else load_baseline(baseline_path)
    new = [f for f in findings if fingerprint(f, repo_root) not in baseline]
    accepted = len(findings) - len(new)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not new,
                    "new": [
                        {
                            "file": os.path.relpath(f["file"], repo_root),
                            "line": f["line"],
                            "class": f["class"],
                            "path": f["subject"],
                            "reason": f["reason"],
                        }
                        for f in new
                    ],
                    "new_count": len(new),
                    "baselined_count": accepted,
                    "untiered_files": untiered,
                },
                indent=2,
            )
        )
        return 1 if new else 0

    if new:
        by_file = {}
        for f in new:
            by_file.setdefault(os.path.relpath(f["file"], repo_root), []).append(f)
        for relpath in sorted(by_file):
            print(relpath)
            for f in sorted(by_file[relpath], key=lambda x: (x["line"], x["subject"])):
                print(f"  {f['line']:>4}  [{f['class']}] {f['subject']}")
                print(f"        {f['reason']}")
        print()

    if untiered and not args.quiet:
        print(
            "note: skipped files with no tier token in the name "
            f"({len(untiered)}): {', '.join(untiered)}",
            file=sys.stderr,
        )
        print()

    if new:
        counts = {}
        for f in new:
            counts[f["class"]] = counts.get(f["class"], 0) + 1
        summary = ", ".join(
            f"{cls}={counts[cls]}" for cls in CLASS_ORDER if cls in counts
        )
        print(f"FAIL: {len(new)} new tier-path violation(s) ({summary})")
        if accepted:
            print(f"      {accepted} pre-existing violation(s) accepted by baseline")
        return 1

    if not args.quiet:
        print(
            f"OK: no new tier-path violations "
            f"({accepted} pre-existing accepted by baseline)"
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - surface as usage error, not traceback
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
