#!/usr/bin/env python3
"""tt-promote — inventory and validation for manifest-based promotion.

See docs/design/promotion-model.md. This tool deliberately covers only the parts that
need no credentials and touch no branches: it reads git objects and writes a text file.
Applying a promotion record is a separate concern.

Subcommands
-----------
  inventory  Build an app inventory from a git ref. Enumerates with `git ls-tree -r`,
             never the filesystem, so symlinked trees (wiki/infra reaches the env
             directory that holds live secrets) cannot leak into the inventory.
  validate   Check an inventory against the rules that make promotion deterministic.
  residual   Report source paths the inventory does not own — the inventory-staleness
             alarm. Not a per-promote checklist.

Inventory format
----------------
Plain text, one entry per line, leaf files only:

    # comment
    src/path/in/repo    ->  dst/path/on/target

Blank lines and comments are ignored. Order is preserved on read and normalised on
write. Text rather than YAML because the review question is "did this line change",
and a line diff answers it without a parser or indentation rules.
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

# Paths whose *presence* is behaviour: a workflow on the target branch fires on the next
# push, an installed unit runs, an enabled vhost listens, a logrotate file is picked up on
# the next rotation. Promoting one can redeploy, restart or expose something with no
# content change at all, so the record marks them for a second approval.
PRIVILEGED_PREFIXES = (
    ".github/workflows/",
    "infra/systemd/",
    "infra/nginx/sites-available/",
    "infra/logrotate/logrotate.d/",
)

EXIT_OK = 0
EXIT_ERRORS = 1
EXIT_USAGE = 2


class GitError(RuntimeError):
    pass


def git(repo_root: str, *args: str) -> bytes:
    """Run git in repo_root and return stdout, raising GitError with stderr on failure."""
    proc = subprocess.run(
        ["git", "-C", repo_root, *args],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )
    return proc.stdout


def ls_tree(repo_root: str, ref: str):
    """Yield (mode, type, sha, path) for every object under ref, recursively.

    `git ls-tree -r` returns blobs only, so directories cannot appear as entries. That
    is the mechanism behind the leaf-only rule rather than a convention layered on top.
    """
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


def blob_text(repo_root: str, sha: str) -> str:
    return git(repo_root, "cat-file", "blob", sha).decode(errors="replace")


# ── inventory model ──────────────────────────────────────────────────────────


@dataclass
class Entry:
    src: str
    dst: str
    line: int


@dataclass
class Inventory:
    path: str
    entries: list[Entry] = field(default_factory=list)

    def dsts(self) -> list[str]:
        return [e.dst for e in self.entries]

    def srcs(self) -> list[str]:
        return [e.src for e in self.entries]


def read_inventory(path: str) -> Inventory:
    inv = Inventory(path=path)
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "->" not in line:
                raise ValueError(f"{path}:{lineno}: no '->' separator: {line!r}")
            src, _, dst = line.partition("->")
            src, dst = src.strip(), dst.strip()
            if not src or not dst:
                raise ValueError(f"{path}:{lineno}: empty src or dst: {line!r}")
            inv.entries.append(Entry(src=src, dst=dst, line=lineno))
    return inv


def read_ignore(path: str | None) -> list[str]:
    """Ignore globs for the residual report. Simple suffix/prefix/substring matching.

    Deliberately not fnmatch: the goal is a short, explainable list ("everything under
    media/", "these three status docs"), not a pattern language nobody can audit.
    """
    if not path:
        return []
    patterns: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def matches_include(path: str, includes: list[str]) -> bool:
    """An app may be a SLICE of a tree, not all of it.

    The first promotion should be the smallest thing that proves the pipeline end to
    end. Promoting 99 paths including 13 privileged ones as the first exercise means a
    failure is ambiguous: was it the mechanism or one of the 99? Partitioning by
    deployment concern (docs, nginx, docker, hooks) makes each promotion reviewable and
    each failure attributable.
    """
    return not includes or any(path.startswith(prefix) for prefix in includes)


def is_ignored(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/") and path.startswith(pat):
            return True
        if pat.startswith("*") and path.endswith(pat[1:]):
            return True
        if pat == path:
            return True
    return False


# ── subcommands ──────────────────────────────────────────────────────────────


def cmd_inventory(args: argparse.Namespace) -> int:
    patterns = read_ignore(args.ignore)
    ref = args.ref or "HEAD"

    try:
        objects = list(ls_tree(args.repo_root, ref))
    except GitError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_USAGE

    prefix = args.dst_prefix or ""
    includes = args.include or []
    entries: list[Entry] = []
    skipped_symlink: list[tuple[str, str]] = []
    skipped_ignore = 0
    skipped_include = 0
    seen_src: set[str] = set()

    for mode, otype, sha, path in objects:
        if otype != "blob":
            continue
        if not matches_include(path, includes):
            skipped_include += 1
            continue
        if is_ignored(path, patterns):
            skipped_ignore += 1
            continue
        if mode == SYMLINK_MODE:
            target = blob_text(args.repo_root, sha).strip()
            skipped_symlink.append((path, target))
            continue
        entries.append(Entry(src=path, dst=prefix + path, line=0))
        seen_src.add(path)

    # --seed-ref exists because of a hole that is invisible until the first promotion:
    # an inventory generated from the source branch cannot own a path the source has
    # already deleted, so nothing can ever target that path for removal and it stays on
    # the target forever. The inventory is the PERSISTENT ownership record, so it is
    # seeded once from the target tier and thereafter only loses a line when someone
    # deliberately removes it.
    seeded = 0
    if args.seed_ref:
        try:
            seed_objects = list(ls_tree(args.repo_root, args.seed_ref))
        except GitError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return EXIT_USAGE
        for mode, otype, _sha, path in seed_objects:
            if otype != "blob" or mode == SYMLINK_MODE:
                continue
            if not matches_include(path, includes):
                continue
            if path in seen_src or is_ignored(path, patterns):
                continue
            entries.append(Entry(src=path, dst=prefix + path, line=0))
            seen_src.add(path)
            seeded += 1
        print(
            f"[INFO]  seeded {seeded} path(s) present on {args.seed_ref} but absent from {ref}",
            file=sys.stderr,
        )

    entries.sort(key=lambda e: e.dst)

    if args.show_skipped and (skipped_symlink or skipped_ignore or skipped_include):
        print(
            f"[INFO]  skipped {skipped_ignore} ignored, {skipped_include} outside the "
            f"include prefixes, {len(skipped_symlink)} symlink(s)",
            file=sys.stderr,
        )
        for path, target in skipped_symlink:
            kind = "ABSOLUTE" if target.startswith("/") else "relative"
            print(f"          symlink {kind}: {path} -> {target}", file=sys.stderr)

    seed_note = f", seeded from {args.seed_ref}" if args.seed_ref else ""
    body = [
        "# tt-hooks.skip-post-commit",
        "# ^ The CCM header is suppressed HERE DELIBERATELY. A header carrying branch,",
        "#   commit id and blob sha would be rewritten on every commit, so the file would",
        "#   show as changed even when no ownership line changed — which is the one",
        "#   property that makes a 500-line inventory reviewable. The marker is a comment",
        "#   so this file still parses as an inventory.",
        f"# tt-promote inventory — app={args.app}",
        f"# generated from {ref}{seed_note} ({len(entries)} leaf file(s))",
        "# src -> dst. Leaf paths only; no directories, no globs.",
        "#",
        "# This file is the PERSISTENT ownership record, not a snapshot of one branch.",
        "# A path listed here that no longer exists at the source is a DELETE candidate,",
        "# which is the only way the target ever loses a file. Removing a line means the",
        "# app no longer owns that path at all, and nothing will maintain or remove it.",
        "# Do not regenerate into this file without --seed-ref <target>.",
        "",
    ]
    body += [f"{e.src} -> {e.dst}" for e in entries]
    text = "\n".join(body) + "\n"

    if args.stdout:
        sys.stdout.write(text)
        return EXIT_OK

    if not args.out:
        print("[ERROR] either --out or --stdout is required", file=sys.stderr)
        return EXIT_USAGE

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"[INFO]  wrote {len(entries)} entries to {args.out}", file=sys.stderr)
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        inv = read_inventory(args.inventory)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_ERRORS

    errors: list[str] = []
    warnings: list[str] = []

    if not inv.entries:
        errors.append("inventory is empty")

    seen_dst: dict[str, int] = {}
    seen_dst_fold: dict[str, tuple[str, int]] = {}

    for e in inv.entries:
        where = f"{args.inventory}:{e.line}"

        # Leaf paths only: a glob or directory would make the entry unbounded, so the
        # manifest would stop determining what lands.
        bad = GLOB_CHARS & set(e.src + e.dst)
        if bad:
            errors.append(f"{where}: glob character(s) {''.join(sorted(bad))} in {e.src!r} -> {e.dst!r}")
        if e.src.endswith("/") or e.dst.endswith("/"):
            errors.append(f"{where}: directory entry, not a leaf file: {e.src!r} -> {e.dst!r}")
        if e.src.startswith("/") or e.dst.startswith("/"):
            errors.append(f"{where}: absolute path: {e.src!r} -> {e.dst!r}")
        if ".." in e.src.split("/") or ".." in e.dst.split("/"):
            errors.append(f"{where}: '..' in path: {e.src!r} -> {e.dst!r}")

        # One entry per destination: a record that names a destination twice can be
        # interpreted two ways depending on resolution order.
        if e.dst in seen_dst:
            errors.append(
                f"{where}: duplicate destination {e.dst!r} (first at line {seen_dst[e.dst]})"
            )
        else:
            seen_dst[e.dst] = e.line

        # Case collisions: a case-insensitive destination cannot represent both, and a
        # delete naming one could remove the other.
        fold = e.dst.lower()
        if fold in seen_dst_fold and seen_dst_fold[fold][0] != e.dst:
            errors.append(
                f"{where}: case collision {e.dst!r} vs {seen_dst_fold[fold][0]!r} "
                f"(line {seen_dst_fold[fold][1]})"
            )
        else:
            seen_dst_fold.setdefault(fold, (e.dst, e.line))

    # Cross-inventory uniqueness, when asked: two apps claiming one destination is a
    # collision that is checkable at rest, before any promote runs.
    if args.against:
        for other_path in args.against:
            try:
                other = read_inventory(other_path)
            except (OSError, ValueError) as exc:
                errors.append(f"could not read {other_path}: {exc}")
                continue
            for dst, line in seen_dst.items():
                for oe in other.entries:
                    if oe.dst == dst:
                        errors.append(
                            f"{args.inventory}:{line}: destination {dst!r} also claimed by "
                            f"{other_path}:{oe.line}"
                        )

    for w in warnings:
        print(f"[WARN]  {w}", file=sys.stderr)
    for err in errors:
        print(f"[ERROR] {err}", file=sys.stderr)

    if errors:
        print(f"[FAIL]  {len(errors)} problem(s) in {args.inventory}", file=sys.stderr)
        return EXIT_ERRORS

    print(
        f"[OK]    {args.inventory}: {len(inv.entries)} entries, "
        f"{len(set(inv.dsts()))} destination(s), no violations",
        file=sys.stderr,
    )
    return EXIT_OK


def cmd_residual(args: argparse.Namespace) -> int:
    try:
        inv = read_inventory(args.inventory)
        objects = list(ls_tree(args.repo_root, args.ref))
    except (OSError, ValueError, GitError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_ERRORS

    patterns = read_ignore(args.ignore)
    includes = args.include or []
    owned = {e.src for e in inv.entries}
    unowned = [
        path
        for mode, otype, _sha, path in objects
        if otype == "blob"
        and mode != SYMLINK_MODE
        and path not in owned
        and matches_include(path, includes)
        and not is_ignored(path, patterns)
    ]
    unowned.sort()

    print(
        f"[INFO]  {len(owned)} owned, {len(unowned)} unowned source path(s) at {args.ref}",
        file=sys.stderr,
    )
    for path in unowned:
        print(path)

    return EXIT_OK


# ── packages ─────────────────────────────────────────────────────────────────
# A package is the only artifact a human authors per promotion. See section 4.2 of
# docs/design/promotion-model.md. Nothing in this file generates one: generating it
# would put the machine back in the position of deciding what to promote, which is the
# thing the model exists to prevent.

PACKAGE_REQUIRED_HEADER = ("package", "app", "from", "to", "reason")


@dataclass
class PackageEntry:
    op: str                 # '+' copy/update, '-' delete
    src: str
    src_ref: str | None     # per-entry ref override, else the package's `from:`
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
                    raise ValueError(f"{path}:{lineno}: expected 'key: value' before the first entry: {line!r}")
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


def load_policy(repo_root: str, policy_dir: str | None, name: str, default: list[str]) -> list[str]:
    """Policy lives in files so forbidden paths and approval classes are diffs, not constants."""
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


def validate_package_entries(pkg: Package, deny: list[str], privileged: list[str]) -> list[str]:
    """Structural checks that need no git access.

    Deliberately runs BEFORE ref resolution. Otherwise a package with a glob and a bad
    branch reports only the branch, and you fix one thing at a time to discover the
    next — the failure ordering hides the real problems.
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
    """Resolve a package into a promote record.

    This is the only command that interprets a symbolic ref. Everything it emits is
    pinned to a commit and a blob, because a record that resolves at apply time makes
    the dry run meaningless and rollback impossible.
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
    seen_dst: dict[str, int] = {}

    for e in pkg.entries:
        where = f"{args.package}:{e.line}"

        bad = GLOB_CHARS & set(e.src + e.dst)
        if bad:
            errors.append(f"{where}: glob character(s) {''.join(sorted(bad))}: {e.src!r} -> {e.dst!r}")
        if e.src.endswith("/") or e.dst.endswith("/"):
            errors.append(f"{where}: directory entry, not a leaf file: {e.src!r} -> {e.dst!r}")
        if e.src.startswith("/") or e.dst.startswith("/"):
            errors.append(f"{where}: absolute path: {e.src!r} -> {e.dst!r}")
        if ".." in e.src.split("/") or ".." in e.dst.split("/"):
            errors.append(f"{where}: '..' in path: {e.src!r} -> {e.dst!r}")
        if is_ignored(e.dst, deny):
            errors.append(f"{where}: destination is on the deny list: {e.dst}")

        if e.dst in seen_dst:
            errors.append(f"{where}: duplicate destination {e.dst!r} (first at line {seen_dst[e.dst]})")
            continue
        seen_dst[e.dst] = e.line

        is_priv = is_privileged(e.dst, privileged)
        if is_priv and not e.approved:
            errors.append(f"{where}: privileged path requires an explicit '!': {e.dst}")
        if e.approved and not is_priv:
            errors.append(f"{where}: '!' on a non-privileged path: {e.dst}")

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
            print("[ERROR] package resolves to nothing, and --require-change was set", file=sys.stderr)
            return EXIT_ERRORS
        print("[WARN]  package resolves to nothing: target already matches", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"[INFO]  wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return EXIT_OK


def yaml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tree_map(repo_root: str, ref: str) -> dict[str, tuple[str, str]]:
    """path -> (mode, blob sha) for every blob in ref."""
    out: dict[str, tuple[str, str]] = {}
    for mode, otype, sha, path in ls_tree(repo_root, ref):
        if otype == "blob":
            out[path] = (mode, sha)
    return out


def is_privileged(path: str, privileged: list[str] | None = None) -> bool:
    prefixes = list(PRIVILEGED_PREFIXES) if privileged is None else privileged
    return any(path.startswith(p) for p in prefixes)


def cmd_record(args: argparse.Namespace) -> int:
    """Resolve an inventory against a source ref and emit a promote record.

    Every entry is pinned to a concrete commit and blob. `latest` is accepted as an input
    only in the sense that a branch name resolves here; the record stores the resolved
    SHA and never the name, because a record that resolves at apply time makes the dry
    run meaningless and rollback impossible.

    The record is a DELTA over the inventory: only entries whose destination blob differs
    from the target tree appear. That keeps the reviewed artifact small even when the
    inventory has hundreds of lines.
    """
    try:
        inv = read_inventory(args.inventory)
        source_commit = git(args.repo_root, "rev-parse", f"{args.source_ref}^{{commit}}").decode().strip()
        target_commit = git(args.repo_root, "rev-parse", f"{args.target_ref}^{{commit}}").decode().strip()
        src_tree = tree_map(args.repo_root, source_commit)
        dst_tree = tree_map(args.repo_root, target_commit)
    except (OSError, ValueError, GitError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_ERRORS

    copies: list[tuple[str, str, str]] = []  # (src, dst, blob)
    deletes: list[str] = []
    unchanged = 0
    absent = 0

    for e in inv.entries:
        src = src_tree.get(e.src)
        dst = dst_tree.get(e.dst)

        if src is not None and src[0] == SYMLINK_MODE:
            print(
                f"[ERROR] {args.inventory}:{e.line}: source is a symlink and is never "
                f"promotable: {e.src}",
                file=sys.stderr,
            )
            return EXIT_ERRORS

        if src is not None:
            if dst is None or dst[1] != src[1] or dst[0] != src[0]:
                copies.append((e.src, e.dst, src[1]))
            else:
                unchanged += 1
        else:
            # Owned, but gone from the source: the only way the target ever loses a file.
            # If the target does not have it either, there is simply nothing to do — but
            # it is counted, because a summary whose numbers do not reconcile sends the
            # next reader hunting a discrepancy that does not exist.
            if dst is not None:
                deletes.append(e.dst)
            else:
                absent += 1

    copies.sort(key=lambda t: t[1])
    deletes.sort()

    record_id = args.id or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{args.app}-to-{args.applies_to}"

    lines = [
        "record_version: 1",
        f"id: {yaml_str(record_id)}",
        f"app: {yaml_str(args.app)}",
        f"inventory: {yaml_str(args.inventory)}",
        f"source_ref: {yaml_str(args.source_ref)}",
        f"source_commit: {source_commit}",
        f"target_ref: {yaml_str(args.target_ref)}",
        f"target_commit: {target_commit}",
        f"applies_to: {yaml_str(args.applies_to)}",
        f"owned_paths: {len(inv.entries)}",
        f"unchanged: {unchanged}",
    ]

    if not copies and not deletes:
        lines.append("entries: []")
    else:
        lines.append("entries:")
        for src_path, dst_path, blob in copies:
            lines.append(f"  - op: copy")
            lines.append(f"    src: {yaml_str(src_path)}")
            lines.append(f"    dst: {yaml_str(dst_path)}")
            lines.append(f"    blob: {blob}")
            if is_privileged(dst_path):
                lines.append("    approval: required")
        for dst_path in deletes:
            lines.append("  - op: delete")
            lines.append(f"    dst: {yaml_str(dst_path)}")
            if is_privileged(dst_path):
                lines.append("    approval: required")

    text = "\n".join(lines) + "\n"

    n_priv = sum(
        1
        for _s, d, _b in copies
        if is_privileged(d)
    ) + sum(1 for d in deletes if is_privileged(d))

    total = len(copies) + len(deletes) + unchanged + absent
    if total != len(inv.entries):
        print(
            f"[ERROR] accounting does not reconcile: "
            f"{total} classified vs {len(inv.entries)} owned",
            file=sys.stderr,
        )
        return EXIT_ERRORS
    print(
        f"[INFO]  {len(copies)} copy, {len(deletes)} delete, {unchanged} unchanged, "
        f"{absent} absent from both = {len(inv.entries)} owned; {n_priv} privileged",
        file=sys.stderr,
    )
    print(f"[INFO]  source {args.source_ref} -> {source_commit[:12]}", file=sys.stderr)
    print(f"[INFO]  target {args.target_ref} -> {target_commit[:12]}", file=sys.stderr)

    if not copies and not deletes:
        if args.require_change:
            print("[ERROR] nothing to promote, and --require-change was set", file=sys.stderr)
            return EXIT_ERRORS
        print("[WARN]  nothing to promote: target already matches this inventory", file=sys.stderr)

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
        description="Inventory and validation for manifest-based promotion.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    inv = sub.add_parser("inventory", help="build an inventory from a git ref")
    inv.add_argument("--repo-root", required=True)
    inv.add_argument("--ref", default="HEAD")
    inv.add_argument("--app", required=True)
    inv.add_argument("--out", default=None)
    inv.add_argument("--stdout", action="store_true")
    inv.add_argument("--dst-prefix", default="")
    inv.add_argument("--ignore", default=None)
    inv.add_argument(
        "--include",
        nargs="+",
        default=None,
        help="only include paths under these prefixes, so an app can be a slice of the tree",
    )
    inv.add_argument(
        "--seed-ref",
        default=None,
        help="also list paths present at this ref, so ownership of source-deleted paths "
             "is retained and can become a delete (use the target branch, e.g. origin/prd)",
    )
    inv.add_argument("--show-skipped", action="store_true")
    inv.set_defaults(func=cmd_inventory)

    val = sub.add_parser("validate", help="check an inventory against the promotion rules")
    val.add_argument("--inventory", required=True)
    val.add_argument("--against", nargs="*", default=None)
    val.set_defaults(func=cmd_validate)

    res = sub.add_parser("residual", help="report source paths the inventory does not own")
    res.add_argument("--inventory", required=True)
    res.add_argument("--repo-root", required=True)
    res.add_argument("--ref", default="HEAD")
    res.add_argument("--ignore", default=None)
    res.add_argument("--include", nargs="+", default=None)
    res.set_defaults(func=cmd_residual)

    rec = sub.add_parser("record", help="resolve an inventory into a promote record")
    rec.add_argument("--repo-root", required=True)
    rec.add_argument("--inventory", required=True)
    rec.add_argument("--app", required=True)
    rec.add_argument("--source-ref", required=True, help="branch, tag or SHA to promote from")
    rec.add_argument("--target-ref", required=True, help="branch the record applies to")
    rec.add_argument("--applies-to", required=True, help="tier name recorded in the artifact")
    rec.add_argument("--out", default=None)
    rec.add_argument("--id", default=None)
    rec.add_argument("--require-change", action="store_true")
    rec.set_defaults(func=cmd_record)

    bld = sub.add_parser("build", help="resolve a package into a promote record")
    bld.add_argument("--repo-root", required=True)
    bld.add_argument("--package", required=True)
    bld.add_argument("--target-ref", default=None, help="defaults to the package's 'to:' value")
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
