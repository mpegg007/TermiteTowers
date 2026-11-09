#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy/tt-deploy-archive.sh@203 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 344deb64079f783491edd4b0413b36d6ccd5bda2 %
#  %ccm_git_commit_id: a29b67ecbd66adfe92276731fcb2047f7064a4ab %
#  %ccm_git_commit_count: 203 %
#  %ccm_git_commit_date: 2026-11-09 14:06:35 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: promotion: manifest inventory, record generator, deploy archive/restore %
#  %ccm_git_modify_date: 2026-11-09 14:06:35 %
#  %ccm_git_file_last_modified: 2026-11-09 14:03:07 %
#  %ccm_git_file_name: tt-deploy-archive.sh %
#  %ccm_git_path: scripts/deploy/tt-deploy-archive.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 9723 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# tt-deploy-archive.sh — capture run-area drift BEFORE a deploy overwrites or purges it.
#
# Usage:
#   tt-deploy-archive.sh --run-area DIR [--state-dir DIR] [--dry-run] [--allow-bootstrap]
#
# Runs immediately before `rsync -a --delete`. The deploy makes the run area identical
# to the incoming tree, so two classes of bytes are destroyed by it:
#
#   ADDED     present in the run area, absent from the last deployed state
#             -> rsync --delete purges it
#   MODIFIED  present in both, content differs
#             -> rsync overwrites it with the incoming version
#
# Both are archived. A third class is reported but not archived:
#
#   MISSING   in the last deployed state, absent from disk
#             -> nothing to preserve; the deploy restores it
#
# SKIP RULE: if there is no ADDED and no MODIFIED path, no archive is created.
# A deploy that only reproduces what was already deployed costs one directory walk.
#
# WHY HASHES AND NOT GIT: the deploy job checks out a single commit at depth 1, so the
# previously deployed tree is not available as a git object. The state directory keeps a
# hash listing of what was actually deployed; that listing is simultaneously the drift
# baseline and the definition of "authorised" content in the run area. It also survives
# the case where the run area was never produced by a checkout at all.
#
# EXCLUSIONS: mirrors the rsync command in the deploy workflows. Any path component named
# .git, .env or .venv is ignored, because those are excluded from the copy and therefore
# are never destroyed by it.
#
# SYMLINKS: recorded by target string, not by target content. A link whose target's
# content changes is not drift here. rsync -a preserves link-ness, so the link itself is
# what the deploy would destroy.
#
# Exit codes: 0 ok (including skipped), 1 usage or precondition failure
#             (including refusal because there is no baseline).

set -Eeuo pipefail

PROG="$(basename "$0")"

RUN_AREA=""
STATE_DIR=""
DRY_RUN=0
ALLOW_BOOTSTRAP=0

die() { printf '[ERROR] %s: %s\n' "$PROG" "$*" >&2; exit 1; }
warn() { printf '[WARN]  %s: %s\n' "$PROG" "$*" >&2; }
info() { printf '[INFO]  %s: %s\n' "$PROG" "$*" >&2; }

usage() {
    cat >&2 <<EOF
Usage: $PROG --run-area DIR [--state-dir DIR] [--dry-run] [--allow-bootstrap]

  --run-area DIR       Directory the deploy will rsync into. Required.
  --state-dir DIR      Where .deployed-manifest, .deployed-commit and archive/ live.
                       Defaults to the parent of --run-area (/srv/<tier> for /srv/<tier>/tt).
  --dry-run            Classify and report, write nothing.
  --allow-bootstrap    Permit a run-area that has content but no baseline manifest.
                       Without this, that situation aborts rather than silently
                       treating every existing file as unauthorised.
EOF
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --run-area)        RUN_AREA="${2-}"; shift 2 ;;
        --state-dir)       STATE_DIR="${2-}"; shift 2 ;;
        --dry-run)         DRY_RUN=1; shift ;;
        --allow-bootstrap) ALLOW_BOOTSTRAP=1; shift ;;
        -h|--help)         usage ;;
        *)                 die "unknown argument: $1" ;;
    esac
done

[ -n "$RUN_AREA" ] || usage
[ -d "$RUN_AREA" ] || die "run area does not exist: $RUN_AREA"
RUN_AREA="$(cd -- "$RUN_AREA" && pwd)"

if [ -z "$STATE_DIR" ]; then
    STATE_DIR="$(dirname -- "$RUN_AREA")"
fi
[ -d "$STATE_DIR" ] || die "state dir does not exist: $STATE_DIR (create it: sudo install -d -o <deploy-user> -g <deploy-user> -m 0755 $STATE_DIR)"
[ -w "$STATE_DIR" ] || die "state dir is not writable: $STATE_DIR"
STATE_DIR="$(cd -- "$STATE_DIR" && pwd)"

MANIFEST="$STATE_DIR/.deployed-manifest"
COMMIT_FILE="$STATE_DIR/.deployed-commit"
ARCHIVE_ROOT="$STATE_DIR/archive"

# ── exclusions, mirroring the deploy's rsync flags ────────────────────────────
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

# Emit "TYPE<TAB>VALUE<TAB>PATH", sorted by path. TYPE is F (sha256) or L (link target).
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

# ── baseline ──────────────────────────────────────────────────────────────────
baseline_present=0
prev_commit="unknown"
if [ -f "$MANIFEST" ]; then
    baseline_present=1
    prev_commit="$(cat "$COMMIT_FILE" 2>/dev/null || echo unknown)"
    info "baseline: $MANIFEST (deployed commit ${prev_commit:0:12})"
else
    if [ "$ALLOW_BOOTSTRAP" -eq 0 ]; then
        if [ -n "$(find "$RUN_AREA" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
            printf '[ERROR] %s: %s\n' "$PROG" \
                "no baseline manifest at $MANIFEST but $RUN_AREA is not empty." >&2
            printf '       Refusing: with no baseline every existing file would be\n' >&2
            printf '       treated as unauthorised, and nothing could be archived.\n' >&2
            printf '       If this run area has never been recorded, re-run once with\n' >&2
            printf '       --allow-bootstrap.\n' >&2
            exit 2
        fi
    fi
    warn "no baseline manifest at $MANIFEST — bootstrap run, nothing will be archived"
fi

current_manifest="$(mktemp)"
trap 'rm -f -- "$current_manifest"' EXIT
build_manifest "$RUN_AREA" > "$current_manifest"

if [ "$baseline_present" -eq 1 ]; then
    diff_file="$(mktemp)"
    awk -F'\t' '
        FNR==NR { old[$3] = $1 "\t" $2; next }
        { cur[$3] = $1 "\t" $2 }
        END {
            for (p in cur) {
                if (!(p in old))                print "ADDED\t"    p;
                else if (old[p] != cur[p])      print "MODIFIED\t" p;
            }
            for (p in old) if (!(p in cur))     print "MISSING\t"  p;
        }
    ' "$MANIFEST" "$current_manifest" > "$diff_file"

    n_added=$(grep -c '^ADDED'    "$diff_file" || true)
    n_mod=$(grep -c '^MODIFIED'   "$diff_file" || true)
    n_missing=$(grep -c '^MISSING' "$diff_file" || true)
else
    diff_file=""
    n_added=0; n_mod=0; n_missing=0
fi

n_at_risk=$(( n_added + n_mod ))
if [ "$baseline_present" -eq 1 ]; then
    info "drift: ${n_added} added, ${n_mod} modified, ${n_missing} missing"
else
    # Saying "0 added, 0 modified" here would be a fabricated measurement: the diff was
    # never computed, so the zeroes would be the absence of a comparison, not a result.
    info "bootstrap: no baseline, drift not computed"
fi

if [ -n "$diff_file" ] && [ "$n_missing" -gt 0 ]; then
    # Reported, not archived: the deploy restores these from the incoming tree.
    grep '^MISSING' "$diff_file" | cut -f2 | sed 's/^/          missing: /' >&2
fi

if [ "$n_at_risk" -eq 0 ]; then
    info "nothing at risk — archive skipped"
    exit 0
fi

echo "         at risk (will be destroyed):" >&2
grep -E '^(ADDED|MODIFIED)' "$diff_file" | sort -t$'\t' -k1,1 -k2,2 \
    | awk -F'\t' '{ printf "          %-8s %s\n", $1, $2 }' >&2

if [ "$DRY_RUN" -eq 1 ]; then
    info "dry run — no archive written"
    exit 0
fi

# ── write the archive ─────────────────────────────────────────────────────────
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
short="${prev_commit:0:8}"
[ "$baseline_present" -eq 1 ] || short="bootstrap"
archive_id="${stamp}-${short}"
archive_dir="$ARCHIVE_ROOT/$archive_id"
[ -e "$archive_dir" ] && die "archive already exists: $archive_dir"

mkdir -p -- "$archive_dir/files"

# Preserve only the at-risk paths, at their run-area paths, with link-ness intact.
while IFS=$'\t' read -r cls path; do
    case "$cls" in ADDED|MODIFIED) ;; *) continue ;; esac
    mkdir -p -- "$archive_dir/files/$(dirname -- "$path")"
    cp -a -- "$RUN_AREA/$path" "$archive_dir/files/$path"
done < <(grep -E '^(ADDED|MODIFIED)' "$diff_file")

# The archive records what it holds, so a restore can verify rather than guess.
grep -E '^(ADDED|MODIFIED)' "$diff_file" | cut -f2 | sort > "$archive_dir/paths.txt"
awk -F'\t' 'NR==FNR { want[$0]=1; next } ($3 in want)' \
    "$archive_dir/paths.txt" "$current_manifest" > "$archive_dir/archive-manifest.tsv"

{
    echo "archive_id=$archive_id"
    echo "created_utc=$stamp"
    echo "run_area=$RUN_AREA"
    echo "baseline_commit=$prev_commit"
} > "$archive_dir/meta.env"

{
    echo "archive $archive_id"
    echo "run_area $RUN_AREA"
    echo "baseline_commit $prev_commit"
    echo "added $n_added"
    echo "modified $n_mod"
    echo "missing $n_missing"
    echo
    echo "class	path"
    grep -E '^(ADDED|MODIFIED|MISSING)' "$diff_file" | awk -F'\t' '{ print $1 "\t" $2 }'
} > "$archive_dir/report.txt"

n_files="$(wc -l < "$archive_dir/paths.txt" | tr -d ' ')"
info "archived ${n_files} path(s) to $archive_dir"
[ "$n_files" -eq "$n_at_risk" ] || die "archived ${n_files} of ${n_at_risk} at-risk paths — archive is incomplete"
exit 0
