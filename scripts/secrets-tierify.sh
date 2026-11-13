#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/secrets-tierify.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: ed2f1893228c44525e1f882ddcac3fe821cb60f2 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: secrets-tierify.sh %
#  %ccm_git_path: scripts/secrets-tierify.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 13441 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# secrets-tierify.sh — move secrets from the flat root into a per-tier root.
#
# WHY THIS EXISTS
#   secrets-migrate-to-etc.sh moved compose env files OUT of the repo into
#   /etc/tt-secrets/env/ and left symlinks behind. It hardcodes that flat root,
#   so every tier shares one secrets directory: a dev1 stack and a prd stack with
#   correct project names can still read each other's values. This script closes
#   that gap by promoting the flat files into /etc/tt-secrets/<tier>/env/.
#
#   It does NOT edit compose files. Those changes are reviewable in git, and
#   scripts/check-tier-paths.py is what proves the result, so the compose edit
#   stays a separate, visible step.
#
# TWO SECRET KINDS
#
#   env files (default)
#     /etc/tt-secrets/env/<name>.env  ->  /etc/tt-secrets/<tier>/env/<name>.env
#
#   Docker secrets (--docker-secrets)
#     infra/docker/env/<name>.txt     ->  /etc/tt-secrets/<tier>/secrets/<name>.txt
#     These never reached /etc at all: they are still real files inside the
#     checkout (referenced as `file: ./env/<name>.txt`), which is why they are
#     also the only secrets left in a deployed-from-git tree. They are sourced
#     from the repo, not from the flat root, hence the separate kind.
#
# TWO MODES
#   promote (default)
#     /etc/tt-secrets/env/<name>.env  ->  /etc/tt-secrets/<tier>/env/<name>.env
#     Copies, sets 0640 root:<group>, verifies sha256, and leaves the flat file
#     in place so a rollback is just "point compose back at it". Refuses to
#     overwrite a tiered file whose bytes differ: that is a real conflict between
#     two secrets, and guessing which one is live is how an outage starts.
#
#   --retire
#     Deletes the flat file and the repo symlink, but ONLY once:
#       - the tiered copy exists and matches the flat file byte for byte;
#       - no compose file under infra/docker still references the flat path.
#     Run this after the service has been recreated and verified, never before.
#
# USAGE
#   sudo ./scripts/secrets-tierify.sh --tier dev1 --dry-run watchyourlan
#   sudo ./scripts/secrets-tierify.sh --tier dev1 watchyourlan
#   # ... edit compose, docker compose up -d, verify the service ...
#   sudo ./scripts/secrets-tierify.sh --tier dev1 --retire watchyourlan
#
#   Names are bare service names: `watchyourlan` means watchyourlan.env.
#   Group is overridable: TT_SECRETS_GROUP=other sudo -E ./scripts/...
#
# EXIT
#   0 success/skip   1 refusal or verification failure   2 usage error

set -euo pipefail

REPO="${TT_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FLAT_ROOT="/etc/tt-secrets/env"
REPO_ENV_DIR="$REPO/infra/docker/env"
COMPOSE_GLOB="$REPO/infra/docker"
GROUP="${TT_SECRETS_GROUP:-mpegg-adm}"

TIER=""
MODE="promote"
KIND="env"
DRY_RUN=0
NAMES=()
FROM_REPO=()

usage() {
    sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --tier)       TIER="${2-}"; shift 2 ;;
        --tier=*)     TIER="${1#*=}"; shift ;;
        --retire)     MODE="retire"; shift ;;
        --docker-secrets) KIND="secret"; shift ;;
        --from-repo)  FROM_REPO+=("${2-}"); KIND="repo"; shift 2 ;;
        --from-repo=*) FROM_REPO+=("${1#*=}"); KIND="repo"; shift ;;
        --dry-run)    DRY_RUN=1; shift ;;
        -h|--help)    usage ;;
        -*)           echo "unknown option: $1" >&2; exit 2 ;;
        *)            NAMES+=("$1"); shift ;;
    esac
done

[ -n "$TIER" ] || { echo "--tier is required (e.g. --tier dev1)" >&2; exit 2; }
case "$TIER" in
    dev[0-9]*|uat[0-9]*|prd[0-9]*) ;;
    *) echo "invalid tier '$TIER': expected dev1|uat1|prd1 style" >&2; exit 2 ;;
esac
if [ "$KIND" = "repo" ]; then
    [ "${#FROM_REPO[@]}" -gt 0 ] || { echo "--from-repo needs at least one name=path" >&2; exit 2; }
    for pair in "${FROM_REPO[@]}"; do
        case "$pair" in
            *=*) ;;
            *) echo "--from-repo expects name=path, got '$pair'" >&2; exit 2 ;;
        esac
        [ -n "${pair%%=*}" ] || { echo "--from-repo: empty name in '$pair'" >&2; exit 2; }
        [ -n "${pair#*=}" ] || { echo "--from-repo: empty path in '$pair'" >&2; exit 2; }
    done
else
    [ "${#NAMES[@]}" -gt 0 ] || { echo "name at least one service (e.g. watchyourlan)" >&2; exit 2; }
fi
getent group "$GROUP" >/dev/null || { echo "group $GROUP does not exist" >&2; exit 1; }

TIER_ROOT="/etc/tt-secrets/$TIER"
TIER_ENV="$TIER_ROOT/env"
TIER_SECRETS="$TIER_ROOT/secrets"
SECRET_SRC_DIR="$REPO/infra/docker/env"

if (( ! DRY_RUN )) && [ "$(id -u)" -ne 0 ]; then
    echo "must run as root (or use --dry-run)" >&2
    exit 1
fi

sha() { sha256sum "$1" | cut -d' ' -f1; }

# Does any compose file still point at the flat path for this secret?
referenced_by_compose() {
    local flat_path="$1"
    grep -rFq -- "$flat_path" "$COMPOSE_GLOB"/*.yml 2>/dev/null
}

promote() {
    local name="$1"
    local src="$FLAT_ROOT/$name.env"
    local dst="$TIER_ENV/$name.env"

    if [ ! -e "$src" ]; then
        echo "FAIL   $name.env: no flat file at $src" >&2
        return 1
    fi

    if [ -e "$dst" ]; then
        if [ "$(sha "$src")" = "$(sha "$dst")" ]; then
            echo "skip   $name.env: already tiered at $dst (bytes match)"
            return 0
        fi
        echo "ABORT  $name.env: $dst exists with DIFFERENT bytes." >&2
        echo "         flat:   $(sha "$src")" >&2
        echo "         tiered: $(sha "$dst")" >&2
        echo "       Two different secrets claim the same slot. Resolve by hand." >&2
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  $name.env -> $dst  (mode 0640 root:$GROUP)"
        return 0
    fi

    install -d -o root -g "$GROUP" -m 0750 "$TIER_ROOT"
    install -d -o root -g "$GROUP" -m 0750 "$TIER_ENV"
    install -m 0640 -o root -g "$GROUP" "$src" "$dst"

    if [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "ABORT  $name.env: sha256 mismatch after copy; flat file untouched" >&2
        rm -f "$dst"
        return 1
    fi

    echo "tiered $name.env -> $dst"
    echo "       compose env_file line:"
    echo "         - $dst"
    return 0
}

retire() {
    local name="$1"
    local src="$FLAT_ROOT/$name.env"
    local dst="$TIER_ENV/$name.env"
    local link="$REPO_ENV_DIR/$name.env"

    if [ ! -e "$dst" ]; then
        echo "FAIL   $name.env: no tiered copy at $dst; refusing to retire" >&2
        return 1
    fi
    if [ -e "$src" ] && [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "FAIL   $name.env: flat and tiered bytes differ; refusing to retire" >&2
        return 1
    fi
    if referenced_by_compose "$src"; then
        echo "FAIL   $name.env: a compose file still references $src — repoint it first" >&2
        grep -rnF -- "$src" "$COMPOSE_GLOB"/*.yml 2>/dev/null >&2 || true
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  remove flat $src"
        [ -L "$link" ] && echo "would  remove repo symlink $link"
        return 0
    fi

    rm -f "$src" && echo "retired flat $src"
    if [ -L "$link" ]; then
        rm -f "$link" && echo "retired repo symlink $link"
    elif [ -e "$link" ]; then
        echo "warn   $link is a real file, not a symlink; left in place" >&2
    fi
    return 0
}

promote_secret() {
    local name="$1"
    local src="$SECRET_SRC_DIR/$name.txt"
    local dst="$TIER_SECRETS/$name.txt"

    if [ ! -f "$src" ]; then
        echo "FAIL   $name.txt: no repo file at $src" >&2
        return 1
    fi

    if [ -e "$dst" ]; then
        if [ "$(sha "$src")" = "$(sha "$dst")" ]; then
            echo "skip   $name.txt: already tiered at $dst (bytes match)"
            return 0
        fi
        echo "ABORT  $name.txt: $dst exists with DIFFERENT bytes." >&2
        echo "         repo:   $(sha "$src")" >&2
        echo "         tiered: $(sha "$dst")" >&2
        echo "       These feed a database. Regenerating them locks out an" >&2
        echo "       existing datadir; resolve by hand, never by overwrite." >&2
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  $name.txt -> $dst  (mode 0640 root:$GROUP)"
        return 0
    fi

    install -d -o root -g "$GROUP" -m 0750 "$TIER_SECRETS"
    install -m 0640 -o root -g "$GROUP" "$src" "$dst"

    if [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "ABORT  $name.txt: sha256 mismatch after copy; repo file untouched" >&2
        rm -f "$dst"
        return 1
    fi

    echo "tiered $name.txt -> $dst"
    echo "       compose secrets line:"
    echo "         file: $dst"
    return 0
}

retire_secret() {
    local name="$1"
    local src="$SECRET_SRC_DIR/$name.txt"
    local dst="$TIER_SECRETS/$name.txt"

    if [ ! -e "$dst" ]; then
        echo "FAIL   $name.txt: no tiered copy at $dst; refusing to retire" >&2
        return 1
    fi
    if [ -e "$src" ] && [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "FAIL   $name.txt: repo and tiered bytes differ; refusing to retire" >&2
        return 1
    fi
    if referenced_by_compose "./env/$name.txt"; then
        echo "FAIL   $name.txt: a compose file still references ./env/$name.txt" >&2
        grep -rnF -- "./env/$name.txt" "$COMPOSE_GLOB"/*.yml 2>/dev/null >&2 || true
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  remove repo secret $src"
        return 0
    fi

    rm -f "$src" && echo "retired repo secret $src"
    return 0
}

# Repo-origin env files: a secret that lives at an arbitrary path inside the
# checkout and was never in the flat root (ttmail/.env, media/.env). Addressed as
# name=path pairs so the tiered filename is explicit rather than derived.
promote_from_repo() {
    local pair="$1"
    local name="${pair%%=*}"
    local rel="${pair#*=}"
    local src="$REPO/$rel"
    local dst="$TIER_ENV/$name.env"

    if [ ! -f "$src" ]; then
        echo "FAIL   $rel: no such file in the repo" >&2
        return 1
    fi
    if [ -e "$dst" ]; then
        if [ "$(sha "$src")" = "$(sha "$dst")" ]; then
            echo "skip   $name.env: already tiered at $dst (bytes match)"
            return 0
        fi
        echo "ABORT  $name.env: $dst exists with DIFFERENT bytes." >&2
        echo "         repo:   $(sha "$src")" >&2
        echo "         tiered: $(sha "$dst")" >&2
        echo "       Resolve by hand; do not guess which one is live." >&2
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  $rel -> $dst  (mode 0640 root:$GROUP)"
        return 0
    fi

    install -d -o root -g "$GROUP" -m 0750 "$TIER_ROOT"
    install -d -o root -g "$GROUP" -m 0750 "$TIER_ENV"
    install -m 0640 -o root -g "$GROUP" "$src" "$dst"

    if [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "ABORT  $name.env: sha256 mismatch after copy; original untouched" >&2
        rm -f "$dst"
        return 1
    fi

    echo "tiered $rel -> $dst"
    return 0
}

retire_from_repo() {
    local pair="$1"
    local name="${pair%%=*}"
    local rel="${pair#*=}"
    local src="$REPO/$rel"
    local dst="$TIER_ENV/$name.env"

    if [ ! -e "$dst" ]; then
        echo "FAIL   $name.env: no tiered copy at $dst; refusing to retire" >&2
        return 1
    fi
    if [ ! -e "$src" ]; then
        echo "skip   $rel: already gone"
        return 0
    fi
    if [ "$(sha "$src")" != "$(sha "$dst")" ]; then
        echo "FAIL   $rel: repo and tiered bytes differ; refusing to retire" >&2
        return 1
    fi

    if (( DRY_RUN )); then
        echo "would  remove repo copy $src"
        return 0
    fi

    rm -f "$src" && echo "retired repo copy $src"
    echo "       NOTE: whatever read this file must now point at $dst"
    return 0
}

rc=0
if [ "$KIND" = "repo" ]; then
    for pair in "${FROM_REPO[@]}"; do
        if [ "$MODE" = "retire" ]; then
            retire_from_repo "$pair" || rc=1
        else
            promote_from_repo "$pair" || rc=1
        fi
        echo
    done
else
    for name in "${NAMES[@]}"; do
        if [ "$KIND" = "secret" ]; then
            if [ "$MODE" = "retire" ]; then
                retire_secret "$name" || rc=1
            else
                promote_secret "$name" || rc=1
            fi
        elif [ "$MODE" = "retire" ]; then
            retire "$name" || rc=1
        else
            promote "$name" || rc=1
        fi
        echo
    done
fi

if (( DRY_RUN )); then
    echo "(dry run — nothing was changed)"
fi
exit "$rc"
