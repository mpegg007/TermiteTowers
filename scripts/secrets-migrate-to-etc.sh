#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/secrets-migrate-to-etc.sh@202 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: ad730d9c9e4fcefa39f6e43e1a249e730e93490d %
#  %ccm_git_commit_id: 2cc1a444bf5a5dcfdb033641139c16458b0ed48f %
#  %ccm_git_commit_count: 202 %
#  %ccm_git_commit_date: 2026-11-09 10:31:57 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: zoo change %
#  %ccm_git_modify_date: 2026-11-09 10:31:57 %
#  %ccm_git_file_last_modified: 2026-11-09 10:29:05 %
#  %ccm_git_file_name: secrets-migrate-to-etc.sh %
#  %ccm_git_path: scripts/secrets-migrate-to-etc.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 3923 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#
# secrets-migrate-to-etc.sh — move compose env files out of the repo and into
# /etc/tt-secrets/env, leaving a symlink behind so nothing that already works
# breaks.
#
# WHY THIS EXISTS
#   The repo is deployed to /srv/dev1/tt and /srv/prd/tt by rsync. Those trees
#   contain only what git tracks, and `.gitignore` excludes
#   `infra/docker/env/*.env`. So a deployed tree has no secrets and cannot start
#   a compose service that references `./env/<service>.env`.
#
#   The obvious fix — symlinking the env DIRECTORY into the tree — is wrong:
#   the next `rsync -a --delete` sees a symlink where the source has a real
#   directory and replaces it, deleting the secrets quietly.
#
#   So secrets live in exactly one place outside every checkout, and compose
#   files reference that place by ABSOLUTE path.
#
# WHAT IT DOES, PER FILE
#   1. copy  infra/docker/env/<name>.env  ->  /etc/tt-secrets/env/<name>.env
#   2. verify the copy with sha256sum and abort on any mismatch
#   3. replace the repo file with a symlink to the /etc copy
#
#   Step 3 is what keeps existing consumers working: the per-service trees under
#   /srv/dev1/<svc>/docker/env/ are symlinks into the repo, so they follow the
#   new link chain and still resolve.
#
#   Already-migrated files (repo path is a symlink) are skipped, so the script is
#   idempotent.
#
# OWNERSHIP AND MODE
#   /etc/tt-secrets            root:mpegg-adm  0750   (traverse needs group)
#   /etc/tt-secrets/env/*.env  root:mpegg-adm  0640   (docker CLI runs as
#   mpegg-adm and must read them; only root may write)
#
# USAGE
#   sudo ./scripts/secrets-migrate-to-etc.sh --dry-run
#   sudo ./scripts/secrets-migrate-to-etc.sh
#
# Group name is overridable: TT_SECRETS_GROUP=other sudo -E ./scripts/...

set -euo pipefail

REPO="${TT_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SRC="$REPO/infra/docker/env"
DEST_ROOT="/etc/tt-secrets"
DEST="$DEST_ROOT/env"
GROUP="${TT_SECRETS_GROUP:-mpegg-adm}"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,45p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done

[ -d "$SRC" ] || { echo "source dir missing: $SRC" >&2; exit 1; }
getent group "$GROUP" >/dev/null || { echo "group $GROUP does not exist" >&2; exit 1; }

if (( ! DRY_RUN )); then
    install -d -o root -g "$GROUP" -m 0750 "$DEST_ROOT"
    install -d -o root -g "$GROUP" -m 0750 "$DEST"
fi

copied=0 skipped=0
for f in "$SRC"/*.env; do
    [ -e "$f" ] || [ -L "$f" ] || continue
    name="$(basename "$f")"
    target="$DEST/$name"

    if [ -L "$f" ]; then
        echo "skip    $name (already a symlink -> $(readlink "$f"))"
        skipped=$((skipped + 1))
        continue
    fi

    if [ -e "$target" ]; then
        # Never clobber: the /etc copy may be the newer one after an edit there.
        echo "skip    $name (/etc copy exists; remove it first to re-migrate)"
        skipped=$((skipped + 1))
        continue
    fi

    if (( DRY_RUN )); then
        echo "would   $name -> $target"
        copied=$((copied + 1))
        continue
    fi

    install -m 0640 -o root -g "$GROUP" "$f" "$target"

    src_hash="$(sha256sum "$f" | cut -d' ' -f1)"
    dst_hash="$(sha256sum "$target" | cut -d' ' -f1)"
    if [ "$src_hash" != "$dst_hash" ]; then
        echo "ABORT   $name: sha256 mismatch after copy; original left untouched" >&2
        exit 1
    fi

    ln -sfn "$target" "$f"
    echo "migrated $name -> $target"
    copied=$((copied + 1))
done

echo
echo "copied/would copy: $copied   already done or conflicting: $skipped"
if (( ! DRY_RUN )); then
    echo "--- $DEST ---"
    ls -l "$DEST" 2>/dev/null || true
    echo
    echo "Next: compose files must reference these by absolute path, e.g."
    echo "  env_file:"
    echo "    - /etc/tt-secrets/env/nextcloud.env"
fi
