#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy/tt-deploy-restore.sh@203 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 08b8ea69763973289d482208d1ac74e03d8cf6b7 %
#  %ccm_git_commit_id: a29b67ecbd66adfe92276731fcb2047f7064a4ab %
#  %ccm_git_commit_count: 203 %
#  %ccm_git_commit_date: 2026-11-09 14:06:35 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: promotion: manifest inventory, record generator, deploy archive/restore %
#  %ccm_git_modify_date: 2026-11-09 14:06:35 %
#  %ccm_git_file_last_modified: 2026-11-09 13:55:05 %
#  %ccm_git_file_name: tt-deploy-restore.sh %
#  %ccm_git_path: scripts/deploy/tt-deploy-restore.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 5811 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# tt-deploy-restore.sh — put archived bytes back into a run area.
#
# Usage:
#   tt-deploy-restore.sh --list  [--state-dir DIR]
#   tt-deploy-restore.sh --latest [--state-dir DIR] [--dry-run] [PATH...]
#   tt-deploy-restore.sh --archive ID [--state-dir DIR] [--dry-run] [PATH...]
#
# An archive with no scripted, exercised restore is not a recovery path — it is
# archaeology to be performed under pressure. This is the other half of
# tt-deploy-archive.sh, and it exists so the archive is a capability rather than a hoard.
#
# Every payload is verified against the hash recorded at archive time BEFORE it is
# written. A mismatch aborts rather than restoring bytes that are not what the archive
# claims to hold.
#
# Restore does not touch the run area's other files and does not run the deploy. A
# subsequent deploy will overwrite whatever was restored, matching the target branch.
# That is expected: restore recovers bytes, it does not hold a deployment back. To keep
# restored bytes live, the change must reach the target branch.
#
# Exit codes: 0 ok, 1 usage or verification failure.

set -Eeuo pipefail

PROG="$(basename "$0")"

STATE_DIR=""
ARCHIVE_ID=""
LIST=0
DRY_RUN=0
PATHS=()

die()  { printf '[ERROR] %s: %s\n' "$PROG" "$*" >&2; exit 1; }
info() { printf '[INFO]  %s: %s\n' "$PROG" "$*" >&2; }
warn() { printf '[WARN]  %s: %s\n' "$PROG" "$*" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        --state-dir) STATE_DIR="${2-}"; shift 2 ;;
        --archive)   ARCHIVE_ID="${2-}"; shift 2 ;;
        --latest)    ARCHIVE_ID="latest"; shift ;;
        --list)      LIST=1; shift ;;
        --dry-run)   DRY_RUN=1; shift ;;
        -h|--help)   sed -n '2,20p' "$0" >&2; exit 0 ;;
        --)          shift; while [ $# -gt 0 ]; do PATHS+=("$1"); shift; done ;;
        -*)          die "unknown argument: $1" ;;
        *)           PATHS+=("$1"); shift ;;
    esac
done

[ -n "$STATE_DIR" ] || die "--state-dir is required (the /srv/<tier> directory)"
[ -d "$STATE_DIR" ] || die "state dir does not exist: $STATE_DIR"
ARCHIVE_ROOT="$STATE_DIR/archive"

# ── list ──────────────────────────────────────────────────────────────────────
if [ "$LIST" -eq 1 ]; then
    if [ ! -d "$ARCHIVE_ROOT" ]; then
        info "no archives under $ARCHIVE_ROOT"
        exit 0
    fi
    found=0
    for d in "$ARCHIVE_ROOT"/*/; do
        [ -d "$d" ] || continue
        found=1
        id="$(basename -- "$d")"
        n="$(wc -l < "$d/paths.txt" 2>/dev/null | tr -d ' ' || echo 0)"
        base="$(grep -m1 '^baseline_commit=' "$d/meta.env" 2>/dev/null | cut -d= -f2 || true)"
        printf '%-34s %4s path(s)  baseline=%s\n' "$id" "${n:-0}" "${base:-unknown}"
    done
    [ "$found" -eq 1 ] || info "no archives under $ARCHIVE_ROOT"
    exit 0
fi

[ -n "$ARCHIVE_ID" ] || die "one of --list, --archive ID or --latest is required"

if [ "$ARCHIVE_ID" = "latest" ]; then
    ARCHIVE_ID="$(ls -1 "$ARCHIVE_ROOT" 2>/dev/null | sort | tail -n1 || true)"
    [ -n "$ARCHIVE_ID" ] || die "no archives under $ARCHIVE_ROOT"
fi

ARCHIVE_DIR="$ARCHIVE_ROOT/$ARCHIVE_ID"
[ -d "$ARCHIVE_DIR" ] || die "archive not found: $ARCHIVE_DIR"

MANIFEST="$ARCHIVE_DIR/archive-manifest.tsv"
PATHS_FILE="$ARCHIVE_DIR/paths.txt"
[ -f "$MANIFEST" ]   || die "archive is missing archive-manifest.tsv: $ARCHIVE_DIR"
[ -f "$PATHS_FILE" ] || die "archive is missing paths.txt: $ARCHIVE_DIR"

run_area="$(grep -m1 '^run_area=' "$ARCHIVE_DIR/meta.env" 2>/dev/null | cut -d= -f2- || true)"
[ -n "$run_area" ] || die "archive is missing run_area in meta.env: $ARCHIVE_DIR"
[ -d "$run_area" ] || die "recorded run area does not exist: $run_area"

info "archive  : $ARCHIVE_ID"
info "run area : $run_area"

# ── selection ─────────────────────────────────────────────────────────────────
if [ "${#PATHS[@]}" -gt 0 ]; then
    selected="$(mktemp)"
    trap 'rm -f -- "$selected"' EXIT
    for p in "${PATHS[@]}"; do
        grep -Fx -- "$p" "$PATHS_FILE" >> "$selected" || die "path is not in this archive: $p"
    done
else
    selected="$PATHS_FILE"
fi

# ── verify then restore ───────────────────────────────────────────────────────
restored=0
while IFS= read -r path; do
    [ -n "$path" ] || continue

    src="$ARCHIVE_DIR/files/$path"
    [ -e "$src" ] || [ -L "$src" ] || die "archive is missing payload for $path"

    expected="$(awk -F'\t' -v p="$path" '$3 == p { print $1 "\t" $2; exit }' "$MANIFEST")"
    [ -n "$expected" ] || die "no recorded hash for $path"
    exp_type="${expected%%$'\t'*}"
    exp_val="${expected#*$'\t'}"

    if [ -L "$src" ]; then
        got_type="L"; got_val="$(readlink -- "$src")"
    else
        got_type="F"; got_val="$(sha256sum -- "$src" | cut -d' ' -f1)"
    fi

    [ "$got_type" = "$exp_type" ] || die "type mismatch for $path: expected $exp_type, found $got_type"
    [ "$got_val"  = "$exp_val"  ] || die "hash mismatch for $path: payload does not match its recorded hash"

    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  would restore %s\n' "$path"
    else
        mkdir -p -- "$run_area/$(dirname -- "$path")"
        cp -a -- "$src" "$run_area/$path"
        printf '  restored %s\n' "$path"
    fi
    restored=$(( restored + 1 ))
done < "$selected"

if [ "$DRY_RUN" -eq 1 ]; then
    info "verified ${restored} path(s); dry run, nothing written"
else
    info "verified and restored ${restored} path(s)"
fi
[ "$restored" -gt 0 ] || warn "no paths matched"
exit 0
