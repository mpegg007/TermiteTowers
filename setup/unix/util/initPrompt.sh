# shellcheck shell=bash
# Prompt for TermiteTowers

# Build PS1: mm.dd HH:MM:SS user:path [region]
# Notes:
# - \d uses locale; we want precise mm.dd => use \D{%m.%d}
# - time: \t is HH:MM:SS
# - tt_scmID & tt_appID
# - user: \u, path: \w
# Colors kept simple; adjust as desired

# Colorized single-line prompt with status, time, user@host, [region:group], path
# Non-printing sequences are wrapped in \[ \] for correct line editing
if [ ! -z ${tt_myps1} ]; then
  return
fi

# --- subshell-free prompt ---

__tt_prompt() {
    local mark
    if [ "$__tt_last_exit" = "0" ]; then
        mark="\[\e[32m\]✔"
    else
        mark="\[\e[31m\]✘"
    fi

    local venv_pfx=""
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        venv_pfx="\[\e[35m\](${VIRTUAL_ENV##*/}) \[\e[0m\]"
    fi

    PS1="${venv_pfx}${mark}\[\e[0m\] "
    PS1+="\[\e[90m\][\t \[\e[33m\]${tt_scmID}:${tt_appID}\[\e[90m\]]\[\e[0m\] "
    PS1+="\[\e[92m\]\u@\h\[\e[0m\]:"
    PS1+="\[\e[94m\]\w\[\e[0m\] "
    PS1+="\[\e[97m\]\$\[\e[0m\] "
}

PROMPT_COMMAND="__tt_last_exit=\$?; __tt_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"