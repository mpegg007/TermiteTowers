#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: setup/unix/util/initAliases.sh:121 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5259f2de6f2d26af54c7ad3cf4cfb056a11cac73 %
#  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
#  %ccm_git_commit_count: 121 %
#  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-11-30 12:27:17 %
#  %ccm_git_file_last_modified: 2025-11-30 12:27:17 %
#  %ccm_git_file_name: initAliases.sh %
#  %ccm_git_path: setup/unix/util/initAliases.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6267 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: november changes % 
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
    echo "Usage: goapp <app>" &&ls /srv/dev1 >&2
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

# Generic docker compose wrapper that uses APPID_DOCKER if set
# Usage: dc <command> [container] [args]
# Usage: dc <app-name> <command> [container] [args]
dc() {
  local app_name="" cmd="" compose_file="" docker_dir=""
  
  # Check if first arg looks like an app name (no hyphens, not a docker command)
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    app_name="$1"
    shift
    cmd="$1"
    shift
  else
    cmd="$1"
    shift
    app_name="${APP_NAME:-}"
  fi
  
  if [ -z "$cmd" ]; then
    echo "Usage: dc [app] <command> [container] [args]"
    echo "Commands: up, down, start, stop, restart, logs, ps, etc."
    echo "Example: dc logs pihole"
    echo "Example: dc eso logs pihole"
    return 1
  fi
  
  # Determine compose file
  if [ -n "$app_name" ]; then
    docker_dir="/srv/${tt_scmID}/${app_name}/docker"
    if [ -f "${docker_dir}/${app_name}-${tt_scmID}.yml" ]; then
      compose_file="${docker_dir}/${app_name}-${tt_scmID}.yml"
    elif [ -f "${docker_dir}/docker-compose.yml" ]; then
      compose_file="${docker_dir}/docker-compose.yml"
    fi
  else
    compose_file="${APPID_DOCKER:-none}"
    docker_dir="/srv/${tt_scmID}/${APP_NAME}/docker"
    if [ "$compose_file" != "none" ]; then
      compose_file="${docker_dir}/${compose_file}"
    fi
  fi
  
  if [ -z "$compose_file" ] || [ ! -f "$compose_file" ]; then
    echo "No docker compose file found. Use 'goapp <app>' first or specify app: dc <app> <command>" >&2
    return 1
  fi
  
  docker compose -f "$compose_file" "$cmd" "$@"
}

# Specific shortcuts using dc - these now support optional app name as first arg
# Examples: dcup, dcup eso, dclogs pihole, dclogs eso pihole
dcup() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" up -d "${@:2}"
  else
    dc up -d "$@"
  fi
}

dcdown() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" down "${@:2}"
  else
    dc down "$@"
  fi
}

dcstart() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" start "${@:2}"
  else
    dc start "$@"
  fi
}

dcstop() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" stop "${@:2}"
  else
    dc stop "$@"
  fi
}

dcrestart() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" restart "${@:2}"
  else
    dc restart "$@"
  fi
}

dclogs() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" logs -f "${@:2}"
  else
    dc logs -f "$@"
  fi
}

dcps() {
  if [[ "$1" =~ ^[a-z0-9]+$ ]] && [ -d "/srv/${tt_scmID}/$1" ]; then
    dc "$1" ps "${@:2}"
  else
    dc ps "$@"
  fi
}

# Override version: explicitly specify compose file
dcf() {
  local compose_file="$1"
  local cmd="$2"
  shift 2
  
  if [ -z "$compose_file" ] || [ -z "$cmd" ]; then
    echo "Usage: dcf <compose-file> <command> [args]"
    return 1
  fi
  
  docker compose -f "$compose_file" "$cmd" "$@"
}

# Quality-of-life
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
