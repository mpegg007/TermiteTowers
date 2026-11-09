#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/promote/tt-promote.py@213 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: fe37504d7474f225301aa28dc9b81384c90c603d %
#  %ccm_git_commit_id: 9c7d1423abce1097a5227b45ff32bd3357facf0a %
#  %ccm_git_commit_count: 213 %
#  %ccm_git_commit_date: 2026-11-09 14:55:21 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: promote: two artifacts only — manifest and record; inventory removed (D20) %
#  %ccm_git_modify_date: 2026-11-09 14:55:22 %
#  %ccm_git_file_last_modified: 2026-11-09 14:55:08 %
#  %ccm_git_file_name: tt-promote.py %
#  %ccm_git_path: scripts/promote/tt-promote.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 17081 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""tt-promote — build a pinned promotion record from a hand-authored manifest.

Two artifacts, and only two: a **manifest** you write, and a **record** it resolves to.
See docs/design/promotion-model.md.

There is deliberately no inventory. A committed list of everything an app owns has no
consumer in this flow — `build` reads a manifest and nothing else. The two questions an
inventory used to answer are queries over two refs:

    git diff --diff-filter=D origin/prd...dev1    # what should be deleted
    git diff --name-status origin/prd...dev1      # what changed at all

If a build or packaging step needs a file list, that is an input to that step, and it is
expressed as a manifest like any other selection. Until such a step exists, there is
nothing for an inventory to do.

Manifest format
---------------
Header keys, then one entry per line:

    package:  2026-11-09-docs
    app:      internal-docs
    from:     dev1
    to:       uat1
    reason:   why this selection exists

    + docs/design/promotion-model.md          # copy or update, identity mapping
    + wiki/ports.md -> docs/ports.md          # remapped destination
    + infra/docker/x.yml@7c77ce9              # pinned to its own commit
    - memory-bank/host-deploy-runbook.md      # delete, file only

`from:` is the ONLY place a symbolic ref is allowed. `build` resolves it once, and the
record carries the commit — a record that resolved at apply time would make the dry run
meaningless and rollback impossible.

Size is a style choice. A two-hundred-entry manifest that changes one file produces a
one-file commit on the target, because the apply writes each blob and an identical blob
produces no diff.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

GLOB_CHARS = set("*?[")
SYMLINK_MODE = "120000"

# Fallback only. policy/privileged.txt is authoritative when present, so that changing
# what requires approval is a reviewable diff rather than an edit to this file.
PRIVILEGED_PREFIXES = (
    ".github/workflows/",
    "infra/systemd/",
    "infra/nginx/sites-available/",
    "infra/logrotate/logrotate.d/",
)

PACKAGE_REQUIRED_HEADER = ("package", "app", "from", "to", "reason")

EXIT_OK = 0
EXIT_ERRORS = 1
EXIT_USAGE = 2


class GitError(RuntimeError):
    pass


def git(repo_root: str, *args: str) -> bytes:
    """Run git in repo_root and return stdout, raising GitError with stderr on failure."""
    proc = subprocess.run(["git", "-C", repo_root, *args], capture_output=True)
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )
    return proc.stdout


def ls_tree(repo_root: str, ref: str):
    """Yield (mode, type, sha, path) for every blob under ref, recursively."""
    out = git(repo_root, "ls-tree", "-r", "-z", "--full-tree", ref)
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        parts = meta.split(b" ")
        if len(parts) != 3:
            continue
        mode, otype, sha = (p.decode() for p in parts)
        yield mode, otype, sha, path.decode()


def tree_map(repo_root: str, ref: str) -> dict[str, tuple[str, str]]:
    """path -> (mode, blob sha) for every blob in ref."""
    out: dict[str, tuple[str, str]] = {}
    for mode, otype, sha, path in ls_tree(repo_root, ref):
        if otype == "blob":
            out[path] = (mode, sha)
    return out


# ── manifest model ───────────────────────────────────────────────────────────


@dataclass
class PackageEntry:
    op: str                 # '+' copy/update, '-' delete
    src: str
    src_ref: str | None     # per-entry ref override, else the manifest's `from:`
    dst: str
    approved: bool          # the human typed '!' on a privileged path
    line: int


@dataclass
class Package:
    path: str
    header: dict[str, str] = field(default_factory=dict)
    entries: list[PackageEntry] = field(default_factory=list)


def read_package(path: str) -> Package:
    pkg = Package(path=path)
    in_entries = False
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if not in_entries and line[0] not in "+-":
                key, sep, value = line.partition(":")
                if not sep:
                    raise ValueError(
                        f"{path}:{lineno}: expected 'key: value' before the first entry: {line!r}"
                    )
                pkg.header[key.strip().lower()] = value.strip()
                continue

            in_entries = True
            op = line[0]
            rest = line[1:].strip()
            approved = False
            if rest.startswith("!"):
                approved = True
                rest = rest[1:].strip()
            if not rest:
                raise ValueError(f"{path}:{lineno}: empty entry")

            if "->" in rest:
                left, _, right = rest.partition("->")
                src, dst = left.strip(), right.strip()
            else:
                src = dst = rest
            if not src or not dst:
                raise ValueError(f"{path}:{lineno}: empty src or dst: {line!r}")

            src_ref = None
            if "@" in src:
                src, _, src_ref = src.rpartition("@")
                src = src.strip()
                src_ref = src_ref.strip() or None
                if not src:
                    raise ValueError(f"{path}:{lineno}: empty path before '@': {line!r}")

            pkg.entries.append(
                PackageEntry(op=op, src=src, src_ref=src_ref, dst=dst, approved=approved, line=lineno)
            )
    return pkg


# ── policy ───────────────────────────────────────────────────────────────────


def load_policy(repo_root: str, policy_dir: str | None, name: str, default: list[str]) -> list[str]:
    """Policy lives in files so forbidden paths and approval classes are reviewable diffs."""
    directory = policy_dir or os.path.join(repo_root, "promote", "policy")
    path = os.path.join(directory, name)
    if not os.path.exists(path):
        print(f"[WARN]  no policy file at {path} — using the built-in default", file=sys.stderr)
        return list(default)
    values: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line and not line.startswith("#"):
                values.append(line)
    return values


def is_ignored(path: str, patterns: list[str]) -> bool:
    """exact path, trailing '/' for a prefix, leading '*' for a suffix."""
    for pat in patterns:
        if pat.endswith("/") and path.startswith(pat):
            return True
        if pat.startswith("*") and path.endswith(pat[1:]):
            return True
        if pat == path:
            return True
    return False


def is_privileged(path: str, privileged: list[str] | None = None) -> bool:
    prefixes = list(PRIVILEGED_PREFIXES) if privileged is None else privileged
    return any(path.startswith(p) for p in prefixes)


def yaml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ── build ────────────────────────────────────────────────────────────────────


def validate_package_entries(pkg: Package, deny: list[str], privileged: list[str]) -> list[str]:
    """Structural checks that need no git access.

    Deliberately runs BEFORE ref resolution. Otherwise a manifest with a glob and a bad
    branch reports only the branch, and the real problems stay hidden behind a missing
    revision — one fix, one rerun, one discovery at a time.
    """
    errors: list[str] = []
    seen_dst: dict[str, int] = {}
    for e in pkg.entries:
        where = f"{pkg.path}:{e.line}"

        bad = GLOB_CHARS & set(e.src + e.dst)
        if bad:
            errors.append(f"{where}: glob character(s) {''.join(sorted(bad))}: {e.src!r} -> {e.dst!r}")
        if e.src.endswith("/") or e.dst.endswith("/"):
            errors.append(f"{where}: directory entry, not a leaf file: {e.src!r} -> {e.dst!r}")
        if e.src.startswith("/") or e.dst.startswith("/"):
            errors.append(f"{where}: absolute path: {e.src!r} -> {e.dst!r}")
        if ".." in e.src.split("/") or ".." in e.dst.split("/"):
            errors.append(f"{where}: '..' in path: {e.src!r} -> {e.dst!r}")
        if is_ignored(e.dst, deny) or is_ignored(e.src, deny):
            errors.append(f"{where}: path is on the deny list: {e.dst}")

        if e.dst in seen_dst:
            errors.append(
                f"{where}: duplicate destination {e.dst!r} (first at line {seen_dst[e.dst]})"
            )
        else:
            seen_dst[e.dst] = e.line

        is_priv = is_privileged(e.dst, privileged)
        if is_priv and not e.approved:
            errors.append(f"{where}: privileged path requires an explicit '!': {e.dst}")
        if e.approved and not is_priv:
            errors.append(f"{where}: '!' on a non-privileged path: {e.dst}")

    return errors


def cmd_build(args: argparse.Namespace) -> int:
    """Resolve a manifest into a promote record.

    The only command that interprets a symbolic ref. Everything it emits is pinned to a
    commit and a blob.
    """
    try:
        pkg = read_package(args.package)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_ERRORS

    missing = [k for k in PACKAGE_REQUIRED_HEADER if not pkg.header.get(k)]
    if missing:
        print(f"[ERROR] {args.package}: missing header key(s): {', '.join(missing)}", file=sys.stderr)
        return EXIT_ERRORS
    if not pkg.entries:
        print(f"[ERROR] {args.package}: no entries", file=sys.stderr)
        return EXIT_ERRORS

    deny = load_policy(args.repo_root, args.policy_dir, "deny.txt", [])
    privileged = load_policy(args.repo_root, args.policy_dir, "privileged.txt", list(PRIVILEGED_PREFIXES))

    structural = validate_package_entries(pkg, deny, privileged)
    if structural:
        for err in structural:
            print(f"[ERROR] {err}", file=sys.stderr)
        print(f"[FAIL]  {len(structural)} problem(s) in {args.package}; nothing emitted", file=sys.stderr)
        return EXIT_ERRORS

    source_ref = pkg.header["from"]
    target_ref = args.target_ref or pkg.header["to"]

    try:
        source_commit = git(args.repo_root, "rev-parse", f"{source_ref}^{{commit}}").decode().strip()
        target_commit = git(args.repo_root, "rev-parse", f"{target_ref}^{{commit}}").decode().strip()
        src_tree = tree_map(args.repo_root, source_commit)
        dst_tree = tree_map(args.repo_root, target_commit)
    except GitError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        print(f"[ERROR] cannot resolve from={source_ref!r} or to={target_ref!r}", file=sys.stderr)
        return EXIT_ERRORS

    tree_cache: dict[str, dict[str, tuple[str, str]]] = {source_commit: src_tree}

    errors: list[str] = []
    copies: list[tuple[PackageEntry, str]] = []
    deletes: list[str] = []
    noops = 0

    for e in pkg.entries:
        where = f"{args.package}:{e.line}"

        if e.op == "-":
            if e.dst in dst_tree:
                deletes.append(e.dst)
            else:
                noops += 1
            continue

        entry_commit = source_commit
        entry_ref = source_ref
        if e.src_ref:
            try:
                entry_commit = git(args.repo_root, "rev-parse", f"{e.src_ref}^{{commit}}").decode().strip()
            except GitError:
                errors.append(f"{where}: cannot resolve ref {e.src_ref!r}")
                continue
            entry_ref = e.src_ref
        if entry_commit not in tree_cache:
            tree_cache[entry_commit] = tree_map(args.repo_root, entry_commit)
        tree = tree_cache[entry_commit]

        src = tree.get(e.src)
        if src is None:
            errors.append(f"{where}: source path absent at {entry_ref}: {e.src}")
            continue
        if src[0] == SYMLINK_MODE:
            errors.append(f"{where}: source is a symlink and is never promotable: {e.src}")
            continue

        dst = dst_tree.get(e.dst)
        if dst is not None and dst[0] == src[0] and dst[1] == src[1]:
            noops += 1
            continue
        copies.append((e, src[1]))

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        print(f"[FAIL]  {len(errors)} problem(s); nothing emitted", file=sys.stderr)
        return EXIT_ERRORS

    with open(args.package, "rb") as fh:
        package_sha = hashlib.sha256(fh.read()).hexdigest()

    record_id = args.id or (
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{pkg.header['package']}"
    )

    lines = [
        "record_version: 1",
        f"id: {yaml_str(record_id)}",
        f"package: {yaml_str(pkg.header['package'])}",
        f"package_sha: {package_sha}",
        f"package_path: {yaml_str(os.path.relpath(args.package, args.repo_root))}",
        f"app: {yaml_str(pkg.header['app'])}",
        f"reason: {yaml_str(pkg.header['reason'])}",
        f"source_ref: {yaml_str(source_ref)}",
        f"source_commit: {source_commit}",
        f"target_ref: {yaml_str(target_ref)}",
        f"target_commit: {target_commit}",
        f"applies_to: {yaml_str(pkg.header['to'])}",
        f"selected: {len(pkg.entries)}",
        f"unchanged: {noops}",
    ]

    if not copies and not deletes:
        lines.append("entries: []")
    else:
        lines.append("entries:")
        for e, blob in copies:
            lines.append("  - op: copy")
            lines.append(f"    src: {yaml_str(e.src)}")
            lines.append(f"    dst: {yaml_str(e.dst)}")
            lines.append(f"    blob: {blob}")
            if e.src_ref:
                lines.append(f"    src_ref: {yaml_str(e.src_ref)}")
            if is_privileged(e.dst, privileged):
                lines.append("    approval: required")
        for dst in deletes:
            lines.append("  - op: delete")
            lines.append(f"    dst: {yaml_str(dst)}")
            if is_privileged(dst, privileged):
                lines.append("    approval: required")

    text = "\n".join(lines) + "\n"

    print(
        f"[INFO]  {len(copies)} copy, {len(deletes)} delete, {noops} no-op "
        f"of {len(pkg.entries)} selected",
        file=sys.stderr,
    )
    print(f"[INFO]  from {source_ref} -> {source_commit[:12]}", file=sys.stderr)
    print(f"[INFO]  to   {target_ref} -> {target_commit[:12]}", file=sys.stderr)
    print(f"[INFO]  package_sha {package_sha[:16]}", file=sys.stderr)

    if not copies and not deletes:
        if args.require_change:
            print("[ERROR] manifest resolves to nothing, and --require-change was set", file=sys.stderr)
            return EXIT_ERRORS
        print("[WARN]  manifest resolves to nothing: target already matches", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"[INFO]  wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return EXIT_OK


# ── cli ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tt-promote",
        description="Build a pinned promotion record from a hand-authored manifest.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    bld = sub.add_parser("build", help="resolve a manifest into a promote record")
    bld.add_argument("--repo-root", required=True)
    bld.add_argument("--package", required=True, help="the manifest file")
    bld.add_argument("--target-ref", default=None, help="defaults to the manifest's 'to:' value")
    bld.add_argument("--policy-dir", default=None)
    bld.add_argument("--out", default=None)
    bld.add_argument("--id", default=None)
    bld.add_argument("--require-change", action="store_true")
    bld.set_defaults(func=cmd_build)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
