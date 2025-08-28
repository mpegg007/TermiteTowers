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

PS1='$(if [ $? -eq 0 ]; then echo "\[\e[32m\]✔"; else echo "\[\e[31m\]✘"; fi)\[\e[0m\] '\
'\[\e[90m\][\t \[\e[33m\]${tt_scmID}:${tt_appID}\[\e[90m\]]\[\e[0m\] '\
'\[\e[92m\]\u@\h\[\e[0m\]:'\
'\[\e[94m\]\w\[\e[0m\] '\
'\[\e[97m\]\$\[\e[0m\] '
