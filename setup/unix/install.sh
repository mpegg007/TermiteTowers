#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 930b6f79b825c715926a6bda27600b312d2f02ec %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-11-30 12:11:05 %
#  %ccm_git_file_last_modified: 2025-11-30 12:11:05 %
#  %ccm_git_file_name: install.sh %
#  %ccm_git_path: setup/unix/install.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1192 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
set -euo pipefail

# Get the directory where this script lives (setup/unix/)
SCRIPT_DIR="$(CDPATH= cd -- "${BASH_SOURCE[0]%/*}" 2>/dev/null && pwd)"
MARK_BEGIN="# >>> TermiteTowers util BEGIN >>>"
MARK_END="# <<< TermiteTowers util END <<<"
LINE="[ -f \"$SCRIPT_DIR/profile.tt\" ] && . \"$SCRIPT_DIR/profile.tt\""

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
chmod +x "$SCRIPT_DIR"/*.sh || true
chmod +x "$SCRIPT_DIR"/util/*.sh || true

echo "Done. Open a new shell or run: source \"$BASHRC\""
