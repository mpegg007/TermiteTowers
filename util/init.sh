# =============================================================================
# DEPRECATED: This file is NOT in use. Do NOT modify.
# The active initialization chain is:
#   setup/unix/profile.tt -> setup/unix/util/init*.sh
# This file (util/init.sh) is a stale legacy copy kept for reference only.
# For the active aliases, see: setup/unix/util/initAliases.sh
# For the active prompt, see:  setup/unix/util/initPrompt.sh
# For the active history, see:  setup/unix/util/initHistory.sh
# =============================================================================
# TermiteTowers util init (DEPRECATED - NOT ACTIVE)
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
