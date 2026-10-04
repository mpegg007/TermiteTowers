#!/usr/bin/env bash
# =============================================================================
# DEPRECATED: This installer is NOT in use. Do NOT modify.
# The active initialization chain is:
#   setup/unix/profile.tt -> setup/unix/util/init*.sh
# This file (util/install.sh) installs the stale util/init.sh into ~/.bashrc.
# For the active installation mechanism, see: setup/unix/profile.tt
# =============================================================================
set -euo pipefail

UTIL_DIR="$(CDPATH= cd -- "${BASH_SOURCE[0]%/*}" 2>/dev/null && pwd)"
MARK_BEGIN="# >>> TermiteTowers util BEGIN >>>"
MARK_END="# <<< TermiteTowers util END <<<"
LINE="[ -f \"$UTIL_DIR/init.sh\" ] && . \"$UTIL_DIR/init.sh\""

BASHRC="$HOME/.bashrc"

if ! grep -Fq "$MARK_BEGIN" "$BASHRC" 2>/dev/null; then
  {
    echo ""
    echo "$MARK_BEGIN"
    echo "$LINE"
    echo "$MARK_END"
  } >> "$BASHRC"
  echo "Added TermiteTowers util to $BASHRC"
else
  echo "Markers already present in $BASHRC; ensuring correct line..."
  # Replace any existing block between markers
  awk -v begin="$MARK_BEGIN" -v end="$MARK_END" -v line="$LINE" '
    BEGIN { inblk=0 }
    {
      if ($0==begin) { print; print line; inblk=1; skip=1; next }
      if (inblk && $0==end) { print; inblk=0; skip=0; next }
      if (!inblk) print
    }
  ' "$BASHRC" > "$BASHRC.tmp"
  mv "$BASHRC.tmp" "$BASHRC"
  echo "Refreshed util block in $BASHRC"
fi

# Make scripts executable
chmod +x "$UTIL_DIR"/*.sh || true

echo "Done. Open a new shell or run: source \"$BASHRC\""
