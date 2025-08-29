# TermiteTowers util init
# Source prompt and aliases only for interactive bash shells

# shellcheck shell=bash

case $- in
  *i*) : ;;   # interactive
  *) return 0 ;; # non-interactive, skip
esac

# Resolve this script directory (POSIX-ish)
TT_UTIL_DIR="$(CDPATH= cd -- "${BASH_SOURCE[0]%/*}" 2>/dev/null && pwd)"

# Default region fallback when not inside /srv/<region>
export TT_DEFAULT_REGION="${TT_DEFAULT_REGION:-dev1}"

# Source components
if [ -f "$TT_UTIL_DIR/prompt.sh" ]; then
  # shellcheck source=/dev/null
  . "$TT_UTIL_DIR/prompt.sh"
fi
if [ -f "$TT_UTIL_DIR/aliases.sh" ]; then
  # shellcheck source=/dev/null
  . "$TT_UTIL_DIR/aliases.sh"
fi
