#!/usr/bin/env bash
set -euo pipefail

# One-time migration: add/normalize CCM headers across the repo for text files.
# - Adds header if missing (top of file)
# - Converts old last_* keys to commit_*
# - Removes deprecated version fields
# - Leaves binary files untouched
# - Skips git-automation/*

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

LOG_FILE="${TMPDIR:-/tmp}/ccm-migrate.log"
echo "CCM migration started at $(date)" > "$LOG_FILE"

# Detect text files from Git's perspective (respects .gitattributes) and iterate
# Use -z for NUL delimiting to handle spaces
while IFS= read -r -d '' path; do
  case "$path" in
    git-automation/*) echo "skip automation: $path" >> "$LOG_FILE"; continue ;;
    .git/*) continue ;;
  esac

  # Only regular files
  [ -f "$path" ] || continue

  # Check Git's text attribute; treat unset as text by inspecting mime too
  attr=$(git check-attr -z text -- "$path" | awk -v RS='\0' 'NR==3 {print}')
  is_text=0
  if [[ "$attr" == "set" || "$attr" == "auto" || -z "$attr" ]]; then
    # Heuristic: non-binary via file command
    if file --mime "$path" | grep -qi 'charset=us-ascii\|charset=utf-8\|text/'; then
      is_text=1
    fi
  fi
  [ $is_text -eq 1 ] || continue

  # Ensure header exists; if not, insert a minimal one at top
  if ! grep -qE '^[[:space:]]*# % ccm_repo:' -- "$path"; then
    fname=$(basename "$path")
    eol="LF"
    if grep -q $'\r\n' "$path"; then eol="CRLF"; elif grep -q $'\r' "$path"; then eol="CR"; fi
    tmpfile=$(mktemp)
    {
      echo "# % ccm_modify_date: 1970-01-01 00:00:00 %"
      echo "# % ccm_author: unknown %"
      echo "# % ccm_author_email: unknown %"
      echo "# % ccm_repo: unknown %"
      echo "# % ccm_branch: unknown %"
      echo "# % ccm_object_id: $path:0 %"
      echo "# % ccm_commit_id: unknown %"
      echo "# % ccm_commit_count: 0 %"
      echo "# % ccm_commit_message: unknown %"
      echo "# % ccm_commit_author: unknown %"
      echo "# % ccm_commit_email: unknown %"
      echo "# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %"
      echo "# % ccm_file_last_modified: 1970-01-01 00:00:00 %"
      echo "# % ccm_file_name: $fname %"
      echo "# % ccm_file_type: text/plain %"
      echo "# % ccm_file_encoding: us-ascii %"
      echo "# % ccm_file_eol: $eol %"
      echo "# % ccm_path: $path %"
      echo "# % ccm_blob_sha: unknown %"
      echo "# % ccm_exec: no %"
      echo "# % ccm_size: 0 %"
      echo
      cat "$path"
    } > "$tmpfile"
    mv "$tmpfile" "$path"
    echo "added header: $path" >> "$LOG_FILE"
  fi

  # Normalize existing headers: rename last_* to commit_*, drop version fields
  sed -i 's/% ccm_last_commit_message: /% ccm_commit_message: /g' "$path"
  sed -i 's/% ccm_last_commit_author: /% ccm_commit_author: /g' "$path"
  sed -i 's/% ccm_last_commit_email: /% ccm_commit_email: /g' "$path"
  sed -i 's/% ccm_last_commit_date: /% ccm_commit_date: /g' "$path"
  sed -i '/% version: .* %/d' "$path"
  sed -i '/% ccm_version: .* %/d' "$path"

done < <(git ls-files -z)

echo "CCM migration finished at $(date)" >> "$LOG_FILE"

# Stage all changes from migration
git add -A
