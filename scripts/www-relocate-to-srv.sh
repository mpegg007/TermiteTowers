#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/www-relocate-to-srv.sh:179 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 513319fc3803c195cce726e7ea930e534f1c50da %
#  %ccm_git_commit_id: 5374d00e1d9cc50947a2b000c73308e0263dce3c %
#  %ccm_git_commit_count: 179 %
#  %ccm_git_commit_date: 2026-10-08 20:03:29 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: impl www from prd branch %
#  %ccm_git_modify_date: 2026-10-08 20:03:30 %
#  %ccm_git_file_last_modified: 2026-10-08 19:46:19 %
#  %ccm_git_file_name: www-relocate-to-srv.sh %
#  %ccm_git_path: scripts/www-relocate-to-srv.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 11274 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#
# www-relocate-to-srv.sh
#
# Make the host's Nginx web roots (e.g. /var/www/chat) symlinks into the
# CI-managed production mirror at /srv/prd/tt/infra/nginx/www/<name>, so the
# published tree is the single source of truth and perms/ownership stop
# drifting between hand-copies and CI.
#
# Every privileged operation lives in THIS script, so the whole migration is
# one sudo approval. Run it WITHOUT sudo and it re-execs itself once via
# `exec sudo`; or run it as `sudo bash scripts/www-relocate-to-srv.sh`.
#
# Steps, in order:
#   1. Preflight  - validate target names, confirm the mirror exists/non-empty,
#                   and (default) require the mirror to match the repo source
#                   so an un-published page can never be linked live early.
#   2. Backup     - tar the current /var/www/<name> entries to
#                   /var/backups/www-relocate-<ts>.tgz (+ a manifest).
#   3. Swap       - replace each /var/www/<name> real dir with a symlink
#                   -> /srv/prd/tt/infra/nginx/www/<name>. Idempotent.
#   4. Verify     - re-check the links, read them back AS www-data (the nginx
#                   worker user), `nginx -t`, reload. On failure: auto-roll back
#                   from the backup, reload, exit non-zero.
#
# Nothing outside /var/www/<name> is touched. No conf content changes: the
# existing `root /var/www/chat` resolves THROUGH the new symlink unchanged.
# Targets owned by other services (tag-viewer, justanotherhuman, html) are
# refused by design.
#
# Usage:
#   bash scripts/www-relocate-to-srv.sh --dry-run          # preview, no sudo
#   bash scripts/www-relocate-to-srv.sh                    # apply chat (1 prompt)
#   bash scripts/www-relocate-to-srv.sh --include-media    # apply chat + media
#   sudo bash scripts/www-relocate-to-srv.sh               # apply, already root
#
# Flags:
#   -n, --dry-run       Print the plan only; never escalates, never writes.
#       --include-media Also migrate the `media` web root (default: chat only).
#       --target NAME   Add/replace a target name (repeatable).
#       --no-sync-check Skip the "mirror must match repo source" guard.
#       --no-backup     Skip the pre-change tarball (NOT recommended).
#       --no-reload     Validate with `nginx -t` but do not reload.
#       --root PATH     Alternate production mirror root (default /srv/prd/tt).
#       --www-root PATH Alternate web-root parent (default /var/www).
#   -h, --help          Show this help.

set -euo pipefail
shopt -s nullglob

TT_ROOT="/srv/prd/tt"
WWW_ROOT="/var/www"
BACKUP_DIR="/var/backups"
SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# Never migrated by this script unless a maintainer edits this list deliberately.
PROTECTED_TARGETS="html justanotherhuman tag-viewer"

DRY_RUN=0
DO_BACKUP=1
DO_RELOAD=1
DO_SYNC_CHECK=1
INCLUDE_MEDIA=0
TARGETS=()

log()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  # Print the human comment block (skip shebang and the CCM header block).
  awk '
    NR==1 {next}
    /ccm_git_header_start/ {in_hdr=1; next}
    /ccm_git_header_end/   {in_hdr=0; next}
    in_hdr {next}
    /^#/ {sub(/^# ?/, ""); print; next}
    {exit}
  ' "$SCRIPT_PATH"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)    DRY_RUN=1 ;;
    --no-reload)     DO_RELOAD=0 ;;
    --no-backup)     DO_BACKUP=0 ;;
    --no-sync-check) DO_SYNC_CHECK=0 ;;
    --include-media) INCLUDE_MEDIA=1 ;;
    --target)        TARGETS+=("${2:?--target requires a name}"); shift ;;
    --root)          TT_ROOT="${2:?--root requires a path}"; shift ;;
    --www-root)      WWW_ROOT="${2:?--www-root requires a path}"; shift ;;
    -h|--help)       usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

MIRROR_ROOT="${TT_ROOT}/infra/nginx/www"
REPO_WWW="${REPO_ROOT}/infra/nginx/www"

# --- single sudo prompt -----------------------------------------------------
# Arguments are already validated above, so a typo never triggers a prompt.
if [[ $DRY_RUN -eq 0 && ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Escalating once via sudo (this is the only password prompt)..." >&2
  exec sudo -- bash "$SCRIPT_PATH" "$@"
fi

# --- target list ------------------------------------------------------------
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=("chat")
fi
[[ $INCLUDE_MEDIA -eq 1 ]] && TARGETS+=("media")

# De-duplicate while preserving order.
if [[ ${#TARGETS[@]} -gt 1 ]]; then
  mapfile -t TARGETS < <(printf '%s\n' "${TARGETS[@]}" | awk '!seen[$0]++')
fi

# --- 1. preflight -----------------------------------------------------------
log "[1/4] Preflight"
for name in "${TARGETS[@]}"; do
  case "$name" in
    */*|.|..|"") die "invalid target name: '$name' (must be a single path component)" ;;
  esac
  for p in $PROTECTED_TARGETS; do
    [[ "$name" == "$p" ]] && die "'$name' is owned by another service (protected); refusing"
  done

  src="${MIRROR_ROOT}/${name}"
  [[ -d "$src" ]] || die "mirror target missing: $src  (has it been deployed to prd yet?)"
  [[ -n "$(ls -A "$src" 2>/dev/null)" ]] || die "mirror target is empty: $src"

  dest="${WWW_ROOT}/${name}"
  if [[ -L "$dest" && "$(readlink "$dest")" == "$src" ]]; then
    log "  $name: already a symlink -> $src (will re-verify)"
  elif [[ -L "$dest" ]]; then
    log "  $name: symlink -> $(readlink "$dest")  (will repoint to $src)"
  elif [[ -e "$dest" ]]; then
    log "  $name: real dir/files ($(ls -A "$dest" 2>/dev/null | wc -l) entries) -> will link to $src"
  else
    log "  $name: absent -> will create symlink to $src"
  fi
done

# --- sync guard: mirror must match the authoring repo source ---------------
if [[ $DO_SYNC_CHECK -eq 1 ]]; then
  for name in "${TARGETS[@]}"; do
    rsrc="${REPO_WWW}/${name}"
    if [[ ! -d "$rsrc" ]]; then
      warn "no repo source at $rsrc; skipping sync check for '$name'"
      continue
    fi
    if ! diff -rq "$rsrc" "${MIRROR_ROOT}/${name}" >/dev/null 2>&1; then
      warn "mirror for '$name' differs from repo source ($rsrc):"
      diff -rq "$rsrc" "${MIRROR_ROOT}/${name}" 2>&1 | sed 's/^/    /' >&2
      die "publish first: merge dev1 -> prd, let deploy-prd.yml rsync, then re-run (bypass: --no-sync-check)"
    fi
    log "  sync ok: ${name} mirror matches repo source"
  done
fi

log ""
log "Plan: ${TARGETS[*]}  ->  ${MIRROR_ROOT}/<name>"
if [[ $DRY_RUN -eq 1 ]]; then
  log "Dry-run only. Re-run without --dry-run to apply (one sudo prompt)."
  exit 0
fi

# --- 2. backup --------------------------------------------------------------
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="${BACKUP_DIR}/www-relocate-${TS}.tgz"
MANIFEST="${BACKUP_DIR}/www-relocate-${TS}.manifest"
log ""
log "[2/4] Backup current /var/www entries"
if [[ $DO_BACKUP -eq 1 ]]; then
  mkdir -p "$BACKUP_DIR"
  tar -C "$WWW_ROOT" -czf "$BACKUP" "${TARGETS[@]}"
  {
    echo "# web-root manifest generated ${TS}"
    for name in "${TARGETS[@]}"; do
      printf '%s\n' "-- ${WWW_ROOT}/${name}"
      ls -la "${WWW_ROOT}/${name}" 2>&1 | sed 's/^/   /'
    done
  } > "$MANIFEST"
  log "  backup:   $BACKUP"
  log "  manifest: $MANIFEST"
  log "  rollback: sudo tar -xzf $BACKUP -C $WWW_ROOT && sudo systemctl reload nginx"
else
  log "  skipped (--no-backup)"
fi

restore_backup() {
  [[ $DO_BACKUP -eq 1 && -f "$BACKUP" ]] || return 1
  for name in "${TARGETS[@]}"; do rm -rf "${WWW_ROOT:?}/${name}"; done
  tar -xzf "$BACKUP" -C "$WWW_ROOT"
}

# --- 3. swap ----------------------------------------------------------------
log ""
log "[3/4] Swap real dirs for symlinks into the mirror"
swapped=0 already=0
for name in "${TARGETS[@]}"; do
  src="${MIRROR_ROOT}/${name}"
  dest="${WWW_ROOT}/${name}"
  if [[ -L "$dest" && "$(readlink "$dest")" == "$src" ]]; then
    already=$((already + 1))
    log "  $name: already correct (no change)"
    continue
  fi
  rm -rf "${WWW_ROOT:?}/${name}"
  [[ -d "$WWW_ROOT" ]] || mkdir -p "$WWW_ROOT"
  ln -s "$src" "$dest"
  log "  $name: $dest -> $src"
  swapped=$((swapped + 1))
done

# --- 4. verify + validate + reload -----------------------------------------
log ""
log "[4/4] Verify (as www-data), validate, reload"
verify_ok=1
for name in "${TARGETS[@]}"; do
  src="${MIRROR_ROOT}/${name}"
  dest="${WWW_ROOT}/${name}"
  if [[ ! -L "$dest" || "$(readlink "$dest")" != "$src" ]]; then
    warn "$name: $dest is not the expected symlink"; verify_ok=0; continue
  fi
  probe="${dest}/index.html"; [[ -f "$probe" ]] || probe="$dest"
  if ! runuser -u www-data -- test -r "$probe"; then
    warn "$name: www-data cannot read $probe"; verify_ok=0; continue
  fi
  log "  $name: ok  ($(runuser -u www-data -- head -c 40 "$probe" 2>/dev/null | tr -d '\n' | cut -c1-40)...)"
done

rollback() {
  if restore_backup; then
    if nginx -t; then
      [[ $DO_RELOAD -eq 1 ]] && systemctl reload nginx || true
    fi
    log "  rolled back; /var/www restored from $BACKUP"
  else
    warn "no backup available to roll back from!"
  fi
}

if [[ $verify_ok -eq 0 ]]; then
  warn "read-back verification FAILED -> rolling back"
  rollback
  exit 1
fi

if nginx -t; then
  if [[ $DO_RELOAD -eq 1 ]]; then
    systemctl reload nginx
    log "  nginx config OK; reloaded"
  else
    log "  nginx config OK (reload skipped: --no-reload)"
  fi
else
  warn "nginx -t FAILED -> rolling back"
  rollback
  exit 1
fi

# Best-effort live probe (derives the vhost from the site conf; never fatal).
for name in "${TARGETS[@]}"; do
  conf="${TT_ROOT}/infra/nginx/sites-available/${name}.conf"
  [[ -f "$conf" ]] || continue
  server="$(awk '/^[[:space:]]*server_name[[:space:]]/{print $2; exit}' "$conf" 2>/dev/null || true)"
  [[ -n "$server" && "$server" != "_" ]] || continue
  if command -v curl >/dev/null 2>&1; then
    code="$(curl -ks -o /dev/null -w '%{http_code}' --max-time 10 "https://${server}/" 2>/dev/null || echo 000)"
    log "  probe https://${server}/ -> HTTP ${code}"
  fi
done

log ""
log "Summary"
log "  swapped: $swapped   already-correct: $already"
for name in "${TARGETS[@]}"; do
  log "  ${WWW_ROOT}/${name} -> $(readlink "${WWW_ROOT}/${name}")"
done
