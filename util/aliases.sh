# =============================================================================
# DEPRECATED: This file is NOT in use. Do NOT modify.
# The active aliases file is: setup/unix/util/initAliases.sh
# This file (util/aliases.sh) is a stale legacy copy kept for reference only.
# The active initialization chain is:
#   setup/unix/profile.tt -> setup/unix/util/initAliases.sh
# =============================================================================
# shellcheck shell=bash
# Aliases and helper functions for TermiteTowers (DEPRECATED - NOT ACTIVE)

# Use tt_scmID directly for environment-specific paths (e.g., /srv/$tt_scmID/<app>).

# ============================================================================
# SECTION 1: App Navigation (cdapp / goapp)
# ============================================================================

# Safely cd to an app under /srv/<region>/<app>
cdapp() {
  local app="$1"
  if [ -z "$app" ]; then
    echo "Usage: cdapp <app>" >&2
    return 2
  fi
  local region
  local target="/srv/${tt_scmID}/${app}"
  if [ -d "$target" ]; then
    cd "$target" || return
  else
    echo "Directory not found: $target" >&2
    return 1
  fi
}

# Source an app's environment script if present, or just cd there
# Convention: /srv/<region>/<app>/scripts/appEnv.sh
# The appEnv.sh can:
# - set up Python venv and activate it, or
# - export env vars for Docker compose commands, etc.
# The function is careful to source (.) the script in the current shell.
goapp() {
  local app="$1"
  if [ -z "$app" ]; then
    echo "Usage: goapp <app>" >&2
    return 2
  fi
  local base envscript venv_dir venv_activate
  base="/srv/${tt_scmID}/${app}"
  envscript="${base}/scripts/appEnv.sh"
  venv_dir="${base}/venv"
  venv_activate="${venv_dir}/bin/activate"

  if [ -d "$base" ]; then
    cd "$base" || return
  else
    echo "Directory not found: $base" >&2
    return 1
  fi

  # Make app name available to env scripts and shell
  export APP_NAME="$app"
  export tt_appID="$app"
  export APPID_CACHE="none"
  export APPID_DOCKER="none"

  if [ -f "$envscript" ]; then
    # Prefer explicit app environment script
    # shellcheck source=/dev/null
    . "$envscript"
  fi

  # Default behavior: ensure correct venv and basic env
  # Deactivate currently active venv if it is different
  if [ -n "$VIRTUAL_ENV" ] && [ "$VIRTUAL_ENV" != "$venv_dir" ]; then
    if type -t deactivate >/dev/null 2>&1; then
      deactivate || true
    fi
  fi

  # Activate app venv if present
  if [ -f "$venv_activate" ]; then
    # shellcheck source=/dev/null
    . "$venv_activate"
  fi

  # Identify docker compose file in docker/ folder
  # Priority: <app>-${tt_scmID}.yml -> docker-compose.yml -> none
  local docker_dir docker_file_candidate
  docker_dir="${base}/docker"
  docker_file_candidate="none"
  if [ -d "$docker_dir" ]; then
    if [ -f "${docker_dir}/${APP_NAME}-${tt_scmID}.yml" ]; then
      docker_file_candidate="${APP_NAME}-${tt_scmID}.yml"
    elif [ -f "${docker_dir}/docker-compose.yml" ]; then
      docker_file_candidate="docker-compose.yml"
    fi
  fi

  export APPID_CACHE="${APP_NAME}"
  export APPID_DOCKER="$docker_file_candidate"
}

# ============================================================================
# SECTION 2: App-Specific Wrappers & Generic Docker Compose
# ============================================================================

# Convenience wrappers for specific apps you mentioned
alias cdlobe='cdapp lobechat'

golobe() { goapp lobechat; }

# Example docker helpers that depend on env from appEnv.sh if it set variables
# Users can optionally define LOBE_COMPOSE or similar in appEnv.sh
lobeup() {
  local base compose
  base="/srv/${tt_scmID}/lobechat"
  compose="${LOBE_COMPOSE:-docker compose}"
  if [ -d "$base" ]; then
    ( cd "$base" && $compose up -d )
  else
    echo "LobeChat dir not found: $base" >&2
    return 1
  fi
}

lobedown() {
  local base compose
  base="/srv/${tt_scmID}/lobechat"
  compose="${LOBE_COMPOSE:-docker compose}"
  if [ -d "$base" ]; then
    ( cd "$base" && $compose down )
  else
    echo "LobeChat dir not found: $base" >&2
    return 1
  fi
}

# Generic docker compose shortcuts for current directory
alias dcu='docker compose up -d'
alias dcd='docker compose down'
alias dcl='docker compose logs -f'

# ============================================================================
# SECTION 3: App-Aware Docker Compose (uses APPID_DOCKER from goapp)
# ============================================================================

# Generic docker compose up/down/logs that work from any app dir after goapp
dcup() {
  if [ "${APPID_DOCKER:-none}" = "none" ]; then
    echo "No docker compose file found for current app. Did you run 'goapp <app>'?" >&2
    return 1
  fi
  docker compose -f "docker/${APPID_DOCKER}" up -d
}

dcdown() {
  if [ "${APPID_DOCKER:-none}" = "none" ]; then
    echo "No docker compose file found for current app. Did you run 'goapp <app>'?" >&2
    return 1
  fi
  docker compose -f "docker/${APPID_DOCKER}" down
}

dclogs() {
  if [ "${APPID_DOCKER:-none}" = "none" ]; then
    echo "No docker compose file found for current app. Did you run 'goapp <app>'?" >&2
    return 1
  fi
  docker compose -f "docker/${APPID_DOCKER}" logs -f
}

# ============================================================================
# SECTION 4: General Docker Shortcuts
# ============================================================================

alias dps='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
alias dpsa='docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
alias dimg='docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"'
alias dprune='docker system prune -a --volumes'

# ============================================================================
# SECTION 5: Systemd Service Helpers
# ============================================================================

# Generic systemctl shortcut (sctl <action> <service>)
sctl() {
  local action="$1" svc="$2"
  if [ -z "$action" ] || [ -z "$svc" ]; then
    echo "Usage: sctl <action> <service>" >&2
    echo "Examples: sctl status ollama-dev1, sctl restart comfyui-dev1" >&2
    return 2
  fi
  sudo systemctl "$action" "$svc"
}

# Shortcuts for checking service status and logs
alias scs='sudo systemctl status'
alias jc='sudo journalctl -u'

# ============================================================================
# SECTION 6: Navigation & Workspace Shortcuts
# ============================================================================

# TermiteTowers project directories
alias cdtt='cd ~/source/TermiteTowers'
alias cdsc='cd ~/source/TermiteTowers/scripts'
alias cdwi='cd ~/source/TermiteTowers/wiki'
alias cdin='cd ~/source/TermiteTowers/infra'
alias cddc='cd ~/source/TermiteTowers/infra/docker'

# Directory traversal shortcuts
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'

# ============================================================================
# SECTION 7: Saner Defaults for Common Commands
# ============================================================================

alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'
alias df='df -h'
alias du='du -h'
alias free='free -h'
alias mkdir='mkdir -p'
alias diff='diff --color=auto'

# ============================================================================
# SECTION 8: Network & System Quick-Checks
# ============================================================================

alias myip='hostname -I'
alias ports='ss -tlnp'
alias mypubip='curl -s ifconfig.me && echo'

# ============================================================================
# SECTION 9: History Improvements
# ============================================================================

alias hg='history | grep'
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend 2>/dev/null

# ============================================================================
# SECTION 10: Quality-of-Life (existing)
# ============================================================================

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias codeaa='code ~/source/AnalAcres.code-workspace'
alias codemr='code ~/source/Multi-root.code-workspace'
alias codett='code ~/source/TermiteTowers.code-workspace'

# ============================================================================
# SECTION 11: Reload & Environment
# ============================================================================

# Resolve TT_UTIL_DIR if not already set by init.sh
if [ -z "${TT_UTIL_DIR:-}" ]; then
  TT_UTIL_DIR="$(CDPATH= cd -- "${BASH_SOURCE[0]%/*}" 2>/dev/null && pwd)"
fi

# Reload all TermiteTowers shell init without opening a new shell
alias reload='. "$TT_UTIL_DIR/init.sh"'

# ============================================================================
# SECTION 12: Utility Functions
# ============================================================================

# List all apps in the current region under /srv/<region>/
lsapps() {
  local region="${tt_scmID:-$TT_DEFAULT_REGION}"
  echo "Apps under /srv/${region}/:"
  ls -1 "/srv/${region}/" 2>/dev/null || echo "  (no apps found or region missing)"
}

# Search all runbook markdown files for a keyword
rbgrep() {
  if [ -z "$1" ]; then
    echo "Usage: rbgrep <keyword>" >&2
    return 2
  fi
  grep -rin --color=auto "$1" ~/source/TermiteTowers/wiki/runbook-*.md
}

# Quick disk usage check for AI storage mount
alias dfai='df -h /mnt/ai_storage'