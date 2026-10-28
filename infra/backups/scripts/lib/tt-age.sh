#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/lib/tt-age.sh@182 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: b602aa0034f69a9d37a200b9aaec50a2e6556130 %
#  %ccm_git_commit_id: 31bcb4a343122a83e17b11cff96a518079bbc65e %
#  %ccm_git_commit_count: 182 %
#  %ccm_git_commit_date: 2026-10-28 11:08:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): per-tier age DEKs with a master-wrapped keyring (phase 1) %
#  %ccm_git_modify_date: 2026-10-28 11:08:37 %
#  %ccm_git_file_last_modified: 2026-10-28 10:58:17 %
#  %ccm_git_file_name: tt-age.sh %
#  %ccm_git_path: infra/backups/scripts/lib/tt-age.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2104 %
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

TT_AGE_DIR="${TT_AGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../age" 2>/dev/null && pwd)}"

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

# Current generation label for a tier, e.g. 2026Q4 (from the public registry).
tt_age_current_gen() {
    local tier="$1" reg="$TT_AGE_DIR/registry.json"
    [ -n "$tier" ] || return 3
    [ -r "$reg" ] || return 3
    command -v jq >/dev/null 2>&1 || return 3
    jq -er --arg t "$tier" '.tiers[$t].current' "$reg" 2>/dev/null
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
