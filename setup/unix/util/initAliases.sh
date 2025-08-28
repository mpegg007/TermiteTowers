# shellcheck shell=bash
# Aliases and helper functions for TermiteTowers

# Use tt_scmID directly for environment-specific paths (e.g., /srv/$tt_scmID/<app>).

# Safely cd to an app under /srv/<region>/<app>
cdapp() {
  local app="$1"
  if [ -z "$app" ]; then
    echo "Usage: cdapp <app>" >&2
    return 2
  fi
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

# Quality-of-life
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
