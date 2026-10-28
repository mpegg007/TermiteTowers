#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/lib/tt-age.sh@186 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 31afd06d81022d4a0a96134d1ebcc8104a8f4152 %
#  %ccm_git_commit_id: 39d8262239b8cbb295886dbe654023e96f65ada9 %
#  %ccm_git_commit_count: 186 %
#  %ccm_git_commit_date: 2026-10-28 11:35:25 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 3 - encrypt to per-tier keys %
#  %ccm_git_modify_date: 2026-10-28 11:35:26 %
#  %ccm_git_file_last_modified: 2026-10-28 11:27:13 %
#  %ccm_git_file_name: tt-age.sh %
#  %ccm_git_path: infra/backups/scripts/lib/tt-age.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 4538 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# ---------------------------------------------------------------------------
# lib/tt-age.sh :: tier -> age recipient resolution for the backup scripts.
#
# Source it, do not execute it:
#     . "$(dirname "${BASH_SOURCE[0]}")/lib/tt-age.sh"
#     recip="$(tt_age_require_recipient health)" || { log ERROR "..."; exit 3; }
#
# There is deliberately NO default/fallback tier. A missing recipient for the
# requested tier is a hard failure, so a backup job can never silently encrypt
# to a stronger tier's key - that is exactly how single-key sprawl creeps back
# into a tiered design.
#
# Return codes follow the tt-backup convention: 3 = configuration error.
# ---------------------------------------------------------------------------

# Layout-aware default: <repo>/infra/backups/age when running from a checkout,
# /etc/tt-backup/age for the installed copy (the installed lib lives at
# /usr/local/lib/tt-backup/lib/, which has no ../../age, so it falls through).
if [ -z "${TT_AGE_DIR:-}" ]; then
    _tt_age_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../age" 2>/dev/null && pwd || true)"
    if [ -n "$_tt_age_repo" ] && [ -d "$_tt_age_repo" ]; then
        TT_AGE_DIR="$_tt_age_repo"
    elif [ -d /etc/tt-backup/age ]; then
        TT_AGE_DIR=/etc/tt-backup/age
    else
        TT_AGE_DIR="${_tt_age_repo:-/etc/tt-backup/age}"
    fi
    unset _tt_age_repo
fi

# Path of the current recipient file for a tier (public key, safe to read).
tt_age_recipient_file() {
    printf '%s/%s.recipient\n' "$TT_AGE_DIR" "$1"
}

# Path of the current recipient file, or return 3 if it is missing/unusable.
tt_age_require_recipient() {
    local tier="$1" file
    [ -n "$tier" ] || return 3
    file="$(tt_age_recipient_file "$tier")"
    [ -r "$file" ] || return 3
    grep -Eqs '^age1[0-9a-z]{50,}$' <(grep -Ev '^[[:space:]]*(#|$)' "$file") || return 3
    printf '%s\n' "$file"
}

# Generation label carried in a recipient file's comment header, e.g.
#   "# tier: health | generation: 2026Q4 | created: 2026-10-28"
# This is what lets the *installed* service script name its artifacts without a
# registry.json (it only gets the recipient file).
tt_age_gen_from_file() {
    local file="$1" gen
    [ -r "$file" ] || return 3
    gen="$(sed -n 's/.*| *generation: *\([^ |]*\) *|.*/\1/p' "$file" | head -1)"
    [ -n "$gen" ] || return 3
    printf '%s\n' "$gen"
}

# Current generation label for a tier: the public registry when present,
# otherwise the recipient file's header (installed layout).
tt_age_current_gen() {
    local tier="$1" reg="$TT_AGE_DIR/registry.json" gen=""
    [ -n "$tier" ] || return 3
    if [ -r "$reg" ] && command -v jq >/dev/null 2>&1; then
        gen="$(jq -er --arg t "$tier" '.tiers[$t].current' "$reg" 2>/dev/null || true)"
    fi
    if [ -z "$gen" ]; then
        gen="$(tt_age_gen_from_file "$(tt_age_recipient_file "$tier")" || true)"
    fi
    [ -n "$gen" ] || return 3
    printf '%s\n' "$gen"
}

# Artifact base name carrying its tier+generation, e.g.
#   tt_age_artifact_name "tthealth_dev1_20261028_033000" health
#   -> tthealth_dev1_20261028_033000__health-2026Q4
# Restore selects the key from this suffix; see infra/backups/README.md.
tt_age_artifact_name() {
    local base="$1" tier="$2" gen
    gen="$(tt_age_current_gen "$tier")" || return 3
    printf '%s__%s-%s\n' "$base" "$tier" "$gen"
}
