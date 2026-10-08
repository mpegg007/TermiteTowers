#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/nginx-relocate-symlinks.sh:177 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: bcb044dae0f1890e49ffd52c5501fc3a831f9630 %
#  %ccm_git_commit_id: cb13d8f4b660ac68d925e62910e996ead5fe260d %
#  %ccm_git_commit_count: 177 %
#  %ccm_git_commit_date: 2026-10-07 21:15:42 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: migration scripts %
#  %ccm_git_modify_date: 2026-10-07 21:15:43 %
#  %ccm_git_file_last_modified: 2026-10-07 21:09:46 %
#  %ccm_git_file_name: nginx-relocate-symlinks.sh %
#  %ccm_git_path: scripts/nginx-relocate-symlinks.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 6525 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#
# nginx-relocate-symlinks.sh
#
# Relocate the host's Nginx site symlinks so the production source of truth is
# the deployed tree at /srv/prd/tt instead of the authoring checkout under
# /home/mpegg-adm/source/TermiteTowers.
#
# Nothing physically moves: the repo (dev1 -> prd) stays the authoring source,
# the CI deploy mirrors it into /srv/prd/tt, and this script only repoints the
# /etc/nginx symlinks at that mirror.
#
# Four privileged operations, all run once via sudo:
#   1. Back up the current /etc/nginx/sites-{available,enabled} symlink layout.
#   2. Repoint every symlink in /etc/nginx/sites-available/ to
#        ${TT_ROOT}/infra/nginx/sites-available/<name>.conf
#   3. Repoint every symlink in /etc/nginx/sites-enabled/ to
#        /etc/nginx/sites-available/<name>
#      (uniform 2-hop chain; also fixes the legacy 1-hop 'dns' link that
#       pointed straight at the repo instead of via sites-available.)
#   4. Validate with `nginx -t` and reload; auto-roll back on failure.
#
# Non-symlink entries (e.g. sites-available/default) are never touched.
# No `root`/`alias` directive is modified. Idempotent: safe to re-run.
#
# Usage:
#   sudo bash scripts/nginx-relocate-symlinks.sh              # apply
#   sudo bash scripts/nginx-relocate-symlinks.sh --no-reload  # apply, no reload
#        bash scripts/nginx-relocate-symlinks.sh --dry-run    # preview (no sudo)

set -euo pipefail
shopt -s nullglob

TT_ROOT="/srv/prd/tt"
AVAIL_DIR="/etc/nginx/sites-available"
ENABLED_DIR="/etc/nginx/sites-enabled"
BACKUP_DIR="/var/backups"
DRY_RUN=0
DO_RELOAD=1
DO_BACKUP=1

usage() {
  # Print the leading comment block (skip shebang, stop at first code line).
  awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)  DRY_RUN=1 ;;
    --no-reload)   DO_RELOAD=0 ;;
    --no-backup)   DO_BACKUP=0 ;;
    --root)        TT_ROOT="${2:?--root requires a path}"; shift ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

SRC_AVAIL="${TT_ROOT}/infra/nginx/sites-available"

log()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

if [[ $DRY_RUN -eq 0 && ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "This script makes privileged changes under /etc/nginx." >&2
  echo "Re-run with: sudo bash $0" >&2
  echo "(Use --dry-run to preview without root.)" >&2
  exit 1
fi

log "============================================================"
log " Nginx symlink relocation -> ${TT_ROOT}"
if [[ $DRY_RUN -eq 1 ]]; then
  log " mode: DRY-RUN (no changes will be made)"
else
  log " mode: APPLY (running as root)"
fi
log "============================================================"

if [[ ! -d "$SRC_AVAIL" ]]; then
  warn "source tree not found: $SRC_AVAIL"
  warn "has the production deploy run yet? (it rsyncs the 'prd' branch into ${TT_ROOT})"
  [[ $DRY_RUN -eq 1 ]] || exit 1
fi

# --- 1. backup -------------------------------------------------------------
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="${BACKUP_DIR}/nginx-symlinks-${TS}.tgz"
MANIFEST="${BACKUP_DIR}/nginx-symlinks-${TS}.manifest"

log ""
log "[1/4] Backup current symlink layout"
if [[ $DO_BACKUP -eq 1 ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    log "  (dry-run) would create: $BACKUP"
  else
    mkdir -p "$BACKUP_DIR"
    tar -C /etc/nginx -czf "$BACKUP" sites-available sites-enabled
    {
      echo "# nginx symlink manifest generated ${TS}"
      find "$AVAIL_DIR" "$ENABLED_DIR" -maxdepth 1 -type l -printf '%p -> %l\n' | sort
    } > "$MANIFEST"
    log "  backup:   $BACKUP"
    log "  manifest: $MANIFEST"
    log "  rollback: sudo tar -xzf $BACKUP -C /etc/nginx && sudo systemctl reload nginx"
  fi
else
  log "  skipped (--no-backup)"
fi

# --- 2. sites-available -> ${TT_ROOT} --------------------------------------
log ""
log "[2/4] sites-available: repoint -> ${SRC_AVAIL}/<name>.conf"
avail_fixed=0 avail_ok=0 avail_missing=0
for link in "$AVAIL_DIR"/*; do
  [[ -L "$link" ]] || continue                       # skip real files (default)
  name="$(basename "$link")"
  want="${SRC_AVAIL}/${name}.conf"
  cur="$(readlink "$link")"
  if [[ "$cur" == "$want" ]]; then
    avail_ok=$((avail_ok + 1))
    continue
  fi
  if [[ ! -e "$want" ]]; then
    avail_missing=$((avail_missing + 1))
    warn "no source for '$name' at $want (leaving link unchanged)"
    continue
  fi
  [[ $DRY_RUN -eq 0 ]] && ln -sfn "$want" "$link"
  log "  -> $name : $cur => $want"
  avail_fixed=$((avail_fixed + 1))
done

# --- 3. sites-enabled -> sites-available (uniform 2-hop) -------------------
log ""
log "[3/4] sites-enabled: repoint -> ${AVAIL_DIR}/<name>"
en_fixed=0 en_ok=0 en_missing=0
for link in "$ENABLED_DIR"/*; do
  [[ -L "$link" ]] || continue
  name="$(basename "$link")"
  want="${AVAIL_DIR}/${name}"
  cur="$(readlink "$link")"
  if [[ "$cur" == "$want" ]]; then
    en_ok=$((en_ok + 1))
    continue
  fi
  if [[ ! -e "$want" ]]; then
    en_missing=$((en_missing + 1))
    warn "no sites-available entry for enabled '$name' (leaving link unchanged)"
    continue
  fi
  [[ $DRY_RUN -eq 0 ]] && ln -sfn "$want" "$link"
  log "  -> $name : $cur => $want"
  en_fixed=$((en_fixed + 1))
done

# --- 4. verify + validate + reload -----------------------------------------
log ""
log "[4/4] Verify symlinks, validate, reload"
broken=0
for d in "$AVAIL_DIR" "$ENABLED_DIR"; do
  for link in "$d"/*; do
    [[ -L "$link" ]] || continue
    if [[ ! -e "$link" ]]; then
      warn "broken: $link -> $(readlink "$link")"
      broken=$((broken + 1))
    fi
  done
done
log "  broken symlinks: $broken"

if [[ $DRY_RUN -eq 1 ]]; then
  log "  (dry-run) would run: nginx -t && systemctl reload nginx"
else
  if nginx -t; then
    if [[ $DO_RELOAD -eq 1 ]]; then
      systemctl reload nginx
      log "  nginx config OK; reloaded"
    else
      log "  nginx config OK (reload skipped: --no-reload)"
    fi
  else
    warn "nginx -t FAILED -> rolling back from $BACKUP"
    tar -xzf "$BACKUP" -C /etc/nginx
    if nginx -t; then
      systemctl reload nginx
      log "  rolled back and reloaded; /etc/nginx restored"
    fi
    exit 1
  fi
fi

log ""
log "Summary"
log "  sites-available: $avail_fixed changed, $avail_ok already-correct, $avail_missing missing-source"
log "  sites-enabled:   $en_fixed changed, $en_ok already-correct, $en_missing missing-source"
log "  broken symlinks: $broken"
if [[ $DRY_RUN -eq 1 ]]; then
  log ""
  log "Dry-run only. Re-run with sudo to apply."
fi
