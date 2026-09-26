#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/system/disk-audit.sh:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a6f3d9f7acfee3eaeedb7017e6ab3c148bad2f3d %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-09-04 17:31:41 %
#  %ccm_git_file_name: disk-audit.sh %
#  %ccm_git_path: scripts/system/disk-audit.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 17065 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#
# disk-audit.sh - Read-only disk clutter audit for dev1.
#
# PURPOSE
#   Produce a human-readable report of reclaimable disk space across the four
#   big clutter buckets on this host (dev1):
#     1. Ollama models          (/mnt/ai_storage/models/ollama, via ollama list)
#     2. Docker images/builds   (docker system df + per-image detail)
#     3. Shared ML caches       (/mnt/ai_storage/models/{huggingface,pip,torch,...})
#     4. PyPI proxies           (devpi on 3141 and the service on 4080)
#
#   The script NEVER deletes anything. It prints suggested cleanup commands at
#   the end for the operator to review and run.
#
# USAGE
#   sudo ./disk-audit.sh        # complete report (recommended)
#   ./disk-audit.sh             # partial report; blocked sections say "skipped"
#
# DESIGN NOTES
#   - Runs fine under a non-admin account. Anything that requires privileges is
#     probed first and reported as "skipped (needs sudo)" rather than failing.
#   - Local HTTP endpoints (ollama:11434, devpi:3141, pypi:4080) are used where
#     they expose the same info without filesystem access.
#
#   Caches under /mnt/ai_storage/models/* are re-downloadable; see
#   wiki/storage-model.md and wiki/backup-strategy.md (they are excluded from
#   backups by design).

set -uo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
AI_STORAGE="/mnt/ai_storage"
MODELS_DIR="${AI_STORAGE}/models"
OLLAMA_MODELS_DIR="${MODELS_DIR}/ollama"
OPENWEBUI_DATA="${AI_STORAGE}/openwebui/data"
REPO_DIR="/home/mpegg-adm/source/TermiteTowers"
COMPOSE_DIR="${REPO_DIR}/infra/docker"
HAS_SUDO=0
HAS_DOCKER=0
CAN_READ_AI=0

# Color helpers (disabled when not a tty)
if [ -t 1 ]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLU=$'\033[34m'
  C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_BOLD=""; C_DIM=""; C_RST=""
fi

section() { echo; echo "${C_BOLD}===== $1 =====${C_RST}"; }
sub()      { echo "  ${C_BLU}-- $1${C_RST}"; }
ok()       { echo "  ${C_GRN}OK${C_RST} $1"; }
skip()     { echo "  ${C_YEL}skipped${C_RST} $1"; }
warn()     { echo "  ${C_RED}!!${C_RST} $1"; }
hdr()      { printf "  %-42s %12s %s\n" "$1" "$2" "$3"; }
row()      { printf "  %-42s %12s %s\n" "$1" "$2" "$3"; }

human() {
  # human <bytes> -> "123.4G"
  local b=${1:-0}
  if   [ "$b" -ge 1073741824 ]; then awk -v x="$b" 'BEGIN{printf "%.1fG", x/1073741824}'
  elif [ "$b" -ge 1048576 ];    then awk -v x="$b" 'BEGIN{printf "%.1fM", x/1048576}'
  elif [ "$b" -ge 1024 ];       then awk -v x="$b" 'BEGIN{printf "%.1fK", x/1024}'
  else echo "${b}B"; fi
}

bytes_of_dir() {
  # bytes_of_dir <path> -> total bytes (du) or empty if unreadable
  local p="$1" out
  if [ -e "$p" ]; then
    out=$(du -sb "$p" 2>/dev/null) && { echo "${out%%	*}"; return 0; }
  fi
  return 1
}

run_cmd() {
  # run_cmd <label> <cmd...> : run a privileged command if we have sudo/docker
  # else mark it skipped. Prints raw output.
  local label="$1"; shift
  if [ "$label" = docker ] && [ "$HAS_DOCKER" -ne 1 ]; then
    skip "docker not accessible to this account"; return 1
  fi
  if [ "$label" = sudo ] && [ "$HAS_SUDO" -ne 1 ]; then
    skip "requires sudo (not available non-interactively)"; return 1
  fi
  "$@"
}

probe() {
  section "Capability probe"
  echo "  user: $(id -un)  uid: $(id -u)  groups: $(id -Gn | tr ' ' ',')"

  if sudo -n true 2>/dev/null; then HAS_SUDO=1; ok "passwordless sudo available"
  else skip "sudo requires a password (run this script with 'sudo' for full report)"; fi

  if docker info >/dev/null 2>&1; then HAS_DOCKER=1; ok "docker socket accessible"
  else skip "docker socket not accessible (not in 'docker' group / no sudo)"; fi

  if [ -r "$AI_STORAGE" ]; then CAN_READ_AI=1; ok "can read $AI_STORAGE"
  else skip "cannot read $AI_STORAGE (run under sudo)"; fi

  if [ -r "$OLLAMA_MODELS_DIR" ]; then ok "can read $OLLAMA_MODELS_DIR"
  else skip "cannot read $OLLAMA_MODELS_DIR"; fi
}

# ---------------------------------------------------------------------------
# 1. OLLAMA MODELS
# ---------------------------------------------------------------------------
# Extracts model names actually used in OpenWebUI chat history (webui.db).
# OpenWebUI stores chats as JSON in the `chat` table; each assistant message
# object under `$.history.messages` carries a `model` field.
openwebui_used_models() {
  local db="" out=""
  if [ -d "$OPENWEBUI_DATA" ] && [ -r "$OPENWEBUI_DATA" ]; then
    db=$(find "$OPENWEBUI_DATA" -maxdepth 1 -name '*.db' 2>/dev/null | head -n1)
  fi
  [ -n "$db" ] || return 1
  command -v sqlite3 >/dev/null 2>&1 || return 1
  out=$(sqlite3 -readonly "$db" \
    "SELECT DISTINCT json_extract(value, '\$.model')
     FROM chat, json_each(json_extract(chat, '\$.history.messages'))
     WHERE json_extract(value, '\$.model') IS NOT NULL
       AND json_extract(value, '\$.model') != '';" 2>/dev/null) || return 1
  printf '%s\n' "$out"
}

# Best-effort: does an installed model name share a distinctive token with any
# model referenced in chat history? e.g. installed "Hermes-3-8B-Instruct"
# matches chat "hermes3:latest". Generic tokens (latest/instruct/gguf/...) are
# ignored so they cannot cause false matches.
chat_family_match() {
  local inst="$1" used="$2" tok
  local norm_inst
  local blacklist=" latest instruct gguf chat text vision base medium small large abliterated instructabliterated 8b 7b 13b 12b 14b 16b 20b 32b 34b 3b 1b 1 2 3 4 5 6 7 8 9 10 11 17 v2 v3 v4 v5 "
  norm_inst=$(printf '%s' "$inst" | tr '[:upper:]' '[:lower:]' | tr -c '[:alnum:]' ' ' | tr -s ' ')
  for tok in $norm_inst; do
    case "${#tok}" in
      0|1|2|3) continue ;;                 # skip tiny/ambiguous tokens
    esac
    case "$blacklist" in
      *" $tok "*) continue ;;              # skip generic tokens
    esac
    # token must be reasonably distinctive to count as a family signal
    printf '%s\n' "$used" | grep -qiE "${tok}" && return 0
  done
  return 1
}

audit_ollama() {
  section "Ollama models"
  local api_out="" used="" total=0
  api_out=$(curl -fsS --max-time 5 http://localhost:11434/api/tags 2>/dev/null) \
    && ok "ollama API reachable (localhost:11434)" \
    || skip "ollama API not reachable (is service running?)"

  # Cross-reference set: models used anywhere in OpenWebUI chat history.
  used=$(openwebui_used_models) && used_n=1 || used_n=0

  if [ -n "$api_out" ]; then
    sub "installed models (name / size / seen in chat history?)"
    printf "  %-42s %12s  %s\n" "model" "size" "in chats?"
    if [ "$used_n" -eq 1 ]; then
      echo "$api_out" | jq -r '.models[] | [.name, (.size|tostring)] | @tsv' 2>/dev/null \
        | sort -k2 -n \
        | while IFS=$'\t' read -r name size; do
            if chat_family_match "$name" "$used"; then
              printf "  %-42s %12s  %s\n" "$name" "$(human "${size:-0}")" "YES"
            else
              printf "  %-42s %12s  %s\n" "$name" "$(human "${size:-0}")" "no match -> review"
            fi
          done
    else
      echo "$api_out" | jq -r '.models[] | [.name, (.size|tostring)] | @tsv' 2>/dev/null \
        | sort -k2 -n \
        | while IFS=$'\t' read -r name size; do
            printf "  %-42s %12s\n" "$name" "$(human "${size:-0}")"
          done
      skip "no chat-history set available for usage cross-reference"
    fi
  fi

  # Filesystem view (sizes + detect stale/duplicate stores)
  if [ -d "$OLLAMA_MODELS_DIR" ] && [ -r "$OLLAMA_MODELS_DIR" ]; then
    total=$(du -sh "$OLLAMA_MODELS_DIR" 2>/dev/null | cut -f1)
    ok "active ollama store: $OLLAMA_MODELS_DIR (total ${total})"
  else
    skip "cannot read $OLLAMA_MODELS_DIR"
  fi

  # Detect orphaned stores (e.g. old OLLAMA_MODELS location)
  local candidate dir_n
  for candidate in "${MODELS_DIR}"/ollama_models "${MODELS_DIR}"/ollama-models; do
    if [ -d "$candidate" ] && [ "$candidate" != "$OLLAMA_MODELS_DIR" ]; then
      dir_n=$(du -sh "$candidate" 2>/dev/null | cut -f1)
      warn "possible stale/duplicate ollama store: $candidate (${dir_n})"
      echo "       -> if orphaned, reclaim with: sudo rm -rf '$candidate'"
      sub "tags found in stale store"
      find "$candidate/manifests" -type f 2>/dev/null \
        | sed "s#${candidate}/manifests/##" | sort | sed 's/^/    /'
    fi
  done
}

# ---------------------------------------------------------------------------
# 2. DOCKER
# ---------------------------------------------------------------------------
audit_docker() {
  section "Docker"
  if [ "$HAS_DOCKER" -ne 1 ]; then
    skip "docker not accessible"
    return
  fi

  sub "system df"
  docker system df

  sub "images not referenced by infra/docker compose files"
  # Build a regex of image refs used in compose files
  local refs imgs img id
  refs=$(grep -rhoE '^\s*image:\s*.*' "${COMPOSE_DIR}"/*-dev1.yml 2>/dev/null \
         | sed -E 's/^\s*image:\s*//' | tr -d '"' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
         | grep -v '^\$' | grep -v '^#' | sort -u)
  if [ -n "$refs" ]; then
    echo "  Compose-referenced images:"
    echo "$refs" | sed 's/^/    /'
  fi

  docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}' 2>/dev/null \
    | while IFS=$'\t' read -r img id size created; do
        if [ "$img" = "<none>:<none>" ]; then
          warn "dangling image: id=$id size=$size (safe to prune)"
        fi
      done
  sub "full image list (sort by size descending)"
  docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}' 2>/dev/null \
    | sort -h -k3 -r | while IFS=$'\t' read -r img id size created; do
        row "$img" "$size" "id=$id created=$created"
      done

  sub "suggested safe reclaim (review before running)"
  echo "    # Remove dangling images / build cache:"
  echo "    docker image prune -f"
  echo "    docker builder prune -f"
  echo "    # More aggressive (also stops nothing; only unused):"
  echo "    docker system prune -af   # DANGER: also removes stopped containers & unused networks"
}

# ---------------------------------------------------------------------------
# 3. SHARED ML CACHES
# ---------------------------------------------------------------------------
audit_caches() {
  section "Shared ML caches ($MODELS_DIR)"
  local dir total_gb
  local grand_total=0
  local first=1
  for dir in "$MODELS_DIR"/*/; do
    [ -d "$dir" ] || continue
    local name total
    name=$(basename "$dir")
    if [ "$first" -eq 1 ]; then
      hdr "dir" "size" "regenerable?"
      first=0
    fi
    if [ -r "$dir" ]; then
      total=$(du -sb "$dir" 2>/dev/null | cut -f1)
      total=${total:-0}
      grand_total=$((grand_total + total))
      case "$name" in
        huggingface) row "$name" "$(human "$total")" "yes (re-download)";;
        pip)         row "$name" "$(human "$total")" "yes (pip cache purge)";;
        torch)       row "$name" "$(human "$total")" "yes (re-download)";;
        whisper)     row "$name" "$(human "$total")" "no (runtime model)";;
        *)           row "$name" "$(human "$total")" "?";;
      esac
    else
      skip "cannot read $dir (run under sudo)"
    fi
  done
  [ "$grand_total" -gt 0 ] && echo "  ${C_DIM}Total under $MODELS_DIR: $(human "$grand_total")${C_RST}"

  # HF cache detail (blobs are the biggest win and safely re-downloadable)
  local hf="$MODELS_DIR/huggingface"
  if [ -d "$hf" ] && [ -r "$hf" ]; then
    sub "huggingface cache breakdown"
    for sdir in "$hf"/*/; do
      [ -d "$sdir" ] || continue
      local sname stotal
      sname=$(basename "$sdir"); stotal=$(du -sb "$sdir" 2>/dev/null | cut -f1)
      row "  $sname" "$(human "${stotal:-0}")" ""
    done
    echo "    ${C_DIM}blobs/ are content-addressed downloads; safe to delete & re-fetch.${C_RST}"
  fi
}

# ---------------------------------------------------------------------------
# 4. PYPI PROXIES (the 4080 mystery)
# ---------------------------------------------------------------------------
audit_proxies() {
  section "PyPI / package proxies"
  sub "listeners on known package ports"
  ss -ltn 2>/dev/null | awk 'NR==1 || /:(3141|4080|3110|3120)\b/' || skip "ss unavailable"

  local url svc
  for url in "3141|http://localhost:3141" "4080|http://localhost:4080"; do
    local port="${url%%|*}" base="${url##*|}" body who
    body=$(curl -fsS --max-time 5 "$base" 2>/dev/null) && who="responds" || who="no HTTP response"
    echo "  port $port: $who"
    if [ -n "$body" ]; then
      echo "$body" | head -c 400 | sed 's/^/      /'
      echo
    fi
  done

  # devpi data dir
  if [ -d "/mnt/ai-storage/devpi" ] && [ -r "/mnt/ai-storage/devpi" ]; then
    ok "devpi serverdir: /mnt/ai-storage/devpi ($(du -sh /mnt/ai-storage/devpi 2>/dev/null | cut -f1))"
  else
    skip "cannot read devpi serverdir /mnt/ai-storage/devpi (run under sudo)"
  fi

  # what is on 4080? systemd unit or container?
  sub "identify what serves port 4080"
  if command -v systemctl >/dev/null 2>&1 && [ "$HAS_SUDO" -eq 1 ]; then
    systemctl list-units --type=service --all --no-legend 2>/dev/null | grep -iE 'pypi|devpi|bandersnatch|nexus' || true
    systemctl status --no-pager 2>/dev/null | grep -iE '4080' || true
  else
    skip "requires sudo for systemctl detail"
  fi
  if [ "$HAS_DOCKER" -eq 1 ]; then
    docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null | grep -E ':4080|:3141' || \
      echo "    (no docker container maps 3141/4080)"
  else
    skip "docker not accessible"
  fi
}

# ---------------------------------------------------------------------------
# 5. OpenWebUI chat history (ground truth for model usage)
# ---------------------------------------------------------------------------
audit_usage() {
  section "Model usage ground truth (OpenWebUI chat history)"
  local db="" counts
  if [ -d "$OPENWEBUI_DATA" ] && [ -r "$OPENWEBUI_DATA" ]; then
    db=$(find "$OPENWEBUI_DATA" -maxdepth 1 -name '*.db' 2>/dev/null | head -n1)
  fi
  if [ -z "$db" ]; then
    skip "no sqlite db found under $OPENWEBUI_DATA"
    return
  fi
  if ! command -v sqlite3 >/dev/null 2>&1; then
    skip "sqlite3 CLI not installed"
    return
  fi
  ok "using $db"
  sub "model references in chat history (distinct model / message count)"
  counts=$(sqlite3 -readonly "$db" \
    "SELECT json_extract(value, '\$.model') AS model, COUNT(*) AS n
     FROM chat, json_each(json_extract(chat, '\$.history.messages'))
     WHERE json_extract(value, '\$.model') IS NOT NULL
       AND json_extract(value, '\$.model') != ''
     GROUP BY model ORDER BY n DESC;" 2>/dev/null)
  if [ -n "$counts" ]; then
    printf '%s\n' "$counts" | sed 's/|/  ->  /; s/^/    /'
  else
    skip "no assistant messages with a model field found (empty history?)"
  fi
}

# ---------------------------------------------------------------------------
# 6. DISK TOP-LEVEL
# ---------------------------------------------------------------------------
audit_disks() {
  section "Filesystem usage"
  df -h / 2>/dev/null | sed 's/^/  /'
  if [ -r "$AI_STORAGE" ]; then
    sub "largest dirs under $AI_STORAGE"
    du -h --max-depth=2 "$AI_STORAGE" 2>/dev/null | sort -rh | head -25 | sed 's/^/  /'
  else
    skip "cannot read $AI_STORAGE (run under sudo)"
  fi
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
  echo "${C_BOLD}TermiteTowers dev1 disk audit (read-only)${C_RST}"
  echo "  run: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "  note: this script NEVER deletes anything."

  probe
  audit_ollama
  audit_docker
  audit_caches
  audit_proxies
  audit_usage
  audit_disks

  section "Next steps"
  echo "  Review the sections above, then run suggested commands individually."
  echo "  For Ollama: ollama rm <model>"
  echo "  For Docker: docker image prune -f && docker builder prune -f"
  echo "  For caches: pip cache purge (or delete specific /mnt/ai_storage/models/* dirs)"
  echo "  Re-run this audit after cleanup to confirm reclaim."
  echo
}

main "$@"
