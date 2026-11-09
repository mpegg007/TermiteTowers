#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy/tt-deploy-record.sh@203 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0f6d4baacc7c95728b27da71d81e3918a68c67c6 %
#  %ccm_git_commit_id: a29b67ecbd66adfe92276731fcb2047f7064a4ab %
#  %ccm_git_commit_count: 203 %
#  %ccm_git_commit_date: 2026-11-09 14:06:35 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: promotion: manifest inventory, record generator, deploy archive/restore %
#  %ccm_git_modify_date: 2026-11-09 14:06:35 %
#  %ccm_git_file_last_modified: 2026-11-09 13:54:57 %
#  %ccm_git_file_name: tt-deploy-record.sh %
#  %ccm_git_path: scripts/deploy/tt-deploy-record.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4079 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# tt-deploy-record.sh — record what is actually live, AFTER a successful deploy.
#
# Usage:
#   tt-deploy-record.sh --run-area DIR [--state-dir DIR] [--commit SHA] [--dry-run]
#
# Writes two files into the state directory, OUTSIDE the run area:
#
#   .deployed-manifest   sorted "TYPE<TAB>VALUE<TAB>PATH" for every deployed file and link
#   .deployed-commit     the git commit the deploy came from (informational, for humans)
#
# Why outside the run area: inside, .deployed-manifest would be an untracked file, which
# violates the authorised-untracked invariant and would force that invariant to carve out
# an exception for the one file whose job is to describe exceptions. Outside, rsync
# --delete cannot reach it.
#
# Why the manifest records hashes rather than a commit id alone:
#   - it is the drift baseline tt-deploy-archive.sh diffs against
#   - it defines "authorised" content in the run area, so an unauthorised addition is
#     distinguishable from a legitimate delete
#   - it survives the run area being produced by something other than a checkout
#
# "Green means deployed" is a fact about a workflow run, not a property of the disk. With
# queued rather than cancelled concurrency, a green run for commit A can coexist with a
# queued run for commit B and a run area holding something else again. The manifest is
# the disk stating its own provenance.
#
# Exit codes: 0 ok, 1 precondition failure.

set -Eeuo pipefail

PROG="$(basename "$0")"

RUN_AREA=""
STATE_DIR=""
COMMIT="${GITHUB_SHA:-unknown}"
DRY_RUN=0

die() { printf '[ERROR] %s: %s\n' "$PROG" "$*" >&2; exit 1; }
info() { printf '[INFO]  %s: %s\n' "$PROG" "$*" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        --run-area)  RUN_AREA="${2-}"; shift 2 ;;
        --state-dir) STATE_DIR="${2-}"; shift 2 ;;
        --commit)    COMMIT="${2-}"; shift 2 ;;
        --dry-run)   DRY_RUN=1; shift ;;
        -h|--help)   sed -n '2,10p' "$0" >&2; exit 0 ;;
        *)           die "unknown argument: $1" ;;
    esac
done

[ -n "$RUN_AREA" ] || die "--run-area is required"
[ -d "$RUN_AREA" ] || die "run area does not exist: $RUN_AREA"
RUN_AREA="$(cd -- "$RUN_AREA" && pwd)"

if [ -z "$STATE_DIR" ]; then
    STATE_DIR="$(dirname -- "$RUN_AREA")"
fi
[ -d "$STATE_DIR" ] || die "state dir does not exist: $STATE_DIR"
[ -w "$STATE_DIR" ] || die "state dir is not writable: $STATE_DIR"
STATE_DIR="$(cd -- "$STATE_DIR" && pwd)"

MANIFEST="$STATE_DIR/.deployed-manifest"
COMMIT_FILE="$STATE_DIR/.deployed-commit"

# Same exclusion list as tt-deploy-archive.sh and the deploy's rsync flags.
excluded() {
    local rel="$1" comp
    local IFS=/
    for comp in $rel; do
        case "$comp" in
            .git|.env|.venv) return 0 ;;
        esac
    done
    return 1
}

build_manifest() {
    local root="$1" abs rel tgt
    while IFS= read -r -d '' abs; do
        rel="${abs#"$root"/}"
        excluded "$rel" && continue
        case "$rel" in
            *$'\t'*|*$'\n'*) die "path contains a tab or newline, which this format cannot express: $rel" ;;
        esac
        if [ -L "$abs" ]; then
            tgt="$(readlink -- "$abs")"
            printf 'L\t%s\t%s\n' "$tgt" "$rel"
        elif [ -f "$abs" ]; then
            printf 'F\t%s\t%s\n' "$(sha256sum -- "$abs" | cut -d' ' -f1)" "$rel"
        fi
    done < <(find "$root" -mindepth 1 \( -type f -o -type l \) -print0 | sort -z)
}

tmp_manifest="$(mktemp)"
tmp_commit="$(mktemp)"
trap 'rm -f -- "$tmp_manifest" "$tmp_commit"' EXIT

build_manifest "$RUN_AREA" > "$tmp_manifest"
printf '%s\n' "$COMMIT" > "$tmp_commit"

count="$(wc -l < "$tmp_manifest" | tr -d ' ')"
info "recorded ${count} path(s) from $RUN_AREA at commit ${COMMIT:0:12}"

if [ "$DRY_RUN" -eq 1 ]; then
    info "dry run — not written"
    exit 0
fi

# Atomic replace: a reader sees either the previous record or the new one, never a
# half-written manifest, which would make the next deploy's drift computation nonsense.
mv -f -- "$tmp_manifest" "$MANIFEST"
mv -f -- "$tmp_commit"   "$COMMIT_FILE"

info "wrote $MANIFEST and $COMMIT_FILE"
exit 0
