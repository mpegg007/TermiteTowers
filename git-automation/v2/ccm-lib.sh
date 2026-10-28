#!/usr/bin/env bash
# ccm-lib.sh: Shared library for CCM header management
# Source this from other scripts: source "$REPO_ROOT/git-automation/v2/ccm-lib.sh"

set -euo pipefail

# Maximum number of %git_commit_history entries retained in a header.
# Bounds the accumulated trail so it can never grow without limit.
CCM_HISTORY_MAX="${CCM_HISTORY_MAX:-50}"

# ─────────────────────────────────────────────────────────────────
# _ccm_trim "$value"
#
# Strip leading and trailing whitespace from a captured header value.
#
# The extraction regexes in extract_preserved_history capture `([^%]*)`
# between ": " and " %". That group is greedy, so it swallows the padding
# space: `%ccm_git_commit_message: unknown %` yields "unknown ", not
# "unknown". Every placeholder check comparing against "unknown" therefore
# failed, the first-pass header (whose commit-bound fields are legitimately
# unknown) looked like it carried a real message, and a junk
# "%git_commit_history: unknown  unknown  unknown" row was emitted on the
# NEXT run -- growing the file on every pass. Trim at the point of capture.
# ─────────────────────────────────────────────────────────────────
_ccm_trim() {
    local s="${1-}"
    s="${s#"${s%%[![:space:]]*}"}"   # strip leading
    s="${s%"${s##*[![:space:]]}"}"   # strip trailing
    printf '%s' "$s"
}

# Directory this library lives in, resolved from the library itself rather than
# from the caller's SCRIPT_DIR, so sourcing works from any entry point.
_CCM_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# ─────────────────────────────────────────────────────────────────
# capture_file_metadata "$file" "$rel_path"
#
# Captures ALL file-level metadata BEFORE any modification.
# This fixes the exec_flag timing bug: v1 captured exec_flag
# AFTER remove_ccm_header had already stripped +x.
# ─────────────────────────────────────────────────────────────────
capture_file_metadata() {
    local file="$1"
    local rel_path="$2"

    # These are exposed globally for the caller
    FILE_EXEC_FLAG=$(test -x "$file" && echo yes || echo no)
    FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo 0)
    FILE_MODIFY_DATE=$(date +"%Y-%m-%d %H:%M:%S")
    FILE_LAST_MODIFIED=$(stat -c %y "$file" 2>/dev/null | cut -d'.' -f1 || echo unknown)
    FILE_NAME=$(basename "$file")
    FILE_TYPE=$(file --brief --mime-type "$file" 2>/dev/null || echo unknown)
    FILE_ENCODING=$(file --brief --mime-encoding "$file" 2>/dev/null || echo unknown)
    FILE_EOL=$(bash "$_CCM_LIB_DIR/../detect-eol.sh" "$file")
    FILE_PATH="$rel_path"
    FILE_BLOB_SHA=$(git hash-object "$file" 2>/dev/null || echo unknown)
}

# ─────────────────────────────────────────────────────────────────
# extract_preserved_history "$file"
#
# Scans the old header for commit message, date, and author
# before header removal. Also collects old %git_commit_history lines
# so they can be re-emitted after the new header.
# ─────────────────────────────────────────────────────────────────
extract_preserved_history() {
    local file="$1"

    PRESERVED_COMMIT_MSG=""
    PRESERVED_COMMIT_DATE=""
    PRESERVED_COMMIT_AUTHOR=""
    OLD_HISTORY_LINES=()

    local line

    # Extract commit message
    line=$(grep -m1 '%ccm_git_commit_message' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_message\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_MSG="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_message:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_MSG="${BASH_REMATCH[1]}"
    fi

    # Extract commit date (YYYY-MM-DD portion)
    line=$(grep -m1 '%ccm_git_commit_date' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_date\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_date:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    fi
    if [[ "$PRESERVED_COMMIT_DATE" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        PRESERVED_COMMIT_DATE="${BASH_REMATCH[1]}"
    fi

    # Extract commit author
    line=$(grep -m1 '%ccm_git_commit_author' "$file" 2>/dev/null || echo "")
    if [[ "$line" =~ %ccm_git_commit_author\":[[:space:]]*\"([^\"]*)\" ]]; then
        PRESERVED_COMMIT_AUTHOR="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ %ccm_git_commit_author:[[:space:]]*([^%]*)[[:space:]]*% ]]; then
        PRESERVED_COMMIT_AUTHOR="${BASH_REMATCH[1]}"
    fi

    # Collect old history lines (survive header removal, float in file body).
    # Deduplicate by normalized content (ignoring a trailing CR / spaces) and
    # cap to CCM_HISTORY_MAX so the trail can never compound or grow unbounded.
    #
    # ANCHORED to column <=9 deliberately. An unanchored match harvests any line
    # that merely *mentions* the token -- e.g. documentation describing this
    # mechanism -- and format_ccm_header then re-emits those body lines verbatim
    # after the header, duplicating them. Real history rows always sit at the
    # start of a comment line (markdown "<!-- " = column 5, shell "# " = column 2),
    # so the anchor is what makes collection, deletion and the artifact count in
    # remove_ccm_header agree.
    local hist_line hist_key
    local -A seen_history=()
    while IFS= read -r line; do
        [[ "$line" =~ ^.{0,9}%git_commit_history ]] || continue
        hist_line="${line%$'\r'}"
        hist_line="${hist_line%"${hist_line##*[![:space:]]}"}"   # rstrip trailing spaces
        hist_key="$hist_line"
        [[ -n "${seen_history[$hist_key]:-}" ]] && continue
        [ "${#OLD_HISTORY_LINES[@]}" -ge "$CCM_HISTORY_MAX" ] && break
        seen_history["$hist_key"]=1
        OLD_HISTORY_LINES+=("$hist_line")
    done < "$file"

    # Sanitize placeholders.
    #
    # "unknown" means the field was never filled in -- on ccm-apply's first pass
    # the commit-bound fields are unknown by design. Blanking only the message
    # left date and author holding the literal "unknown", so the guard in
    # format_ccm_header saw a non-empty message and emitted a junk row
    # ("%git_commit_history: unknown  unknown  unknown") on the NEXT run, growing
    # the file on every pass. Blank all three.
    #
    # Written as `if` blocks deliberately: a bare `[ ... ] && x` returns non-zero
    # when the test is false, which under `set -e` aborts the caller.
    # Trim the capture padding FIRST -- otherwise the "unknown" comparisons
    # below never match (see _ccm_trim).
    PRESERVED_COMMIT_MSG=$(_ccm_trim "$PRESERVED_COMMIT_MSG")
    PRESERVED_COMMIT_DATE=$(_ccm_trim "$PRESERVED_COMMIT_DATE")
    PRESERVED_COMMIT_AUTHOR=$(_ccm_trim "$PRESERVED_COMMIT_AUTHOR")

    if [ "$PRESERVED_COMMIT_MSG" = "unknown" ]; then
        PRESERVED_COMMIT_MSG=""
    fi
    if [ "$PRESERVED_COMMIT_DATE" = "unknown" ]; then
        PRESERVED_COMMIT_DATE=""
    fi
    if [ "$PRESERVED_COMMIT_AUTHOR" = "unknown" ]; then
        PRESERVED_COMMIT_AUTHOR=""
    fi

    # Sanitize: blank if no alphanumeric content (placeholders)
    if [ -n "$PRESERVED_COMMIT_MSG" ] && ! [[ "$PRESERVED_COMMIT_MSG" =~ [A-Za-z0-9] ]]; then
        PRESERVED_COMMIT_MSG=""
    fi
}

# ─────────────────────────────────────────────────────────────────
# remove_ccm_header "$file"
#
# Strips CCM header lines AND accumulated %git_commit_history lines
# from the file. History is re-emitted (deduplicated, capped) by
# format_ccm_header, so removal and re-emission stay balanced and the
# trail cannot compound across runs.
# ─────────────────────────────────────────────────────────────────
remove_ccm_header() {
    local file="$1"
    local tmpfile="${file}.tmp.removeccm"

    local line_count_before
    line_count_before=$(wc -l < "$file")

    # Remove CCM header lines, template markers, and accumulated history
    # Every pattern here MUST stay anchored to the same column threshold as the
    # artifact_lines count below. The former `/^.{0,9}.*%git_commit_history/d`
    # matched the token anywhere in a line, so deleting body prose that mentioned
    # it and counting only column-<=9 occurrences disagreed -- tripping the
    # subset assertion, aborting the strip, and (via ccm-apply's `|| true`)
    # appending a second header.
    sed -E \
        -e '/^.{0,9}%ccm_.*: .* %/d' \
        -e '/^.{0,9}% ccm_.*: .* %/d' \
        -e '/^.{0,9}TermiteTowers Continuous Code Management Header TEMPLATE/d' \
        -e '/^.{0,9}tt-ccm.header.end/d' \
        -e '/^.{0,9}%git_commit_history/d' \
        "$file" > "$tmpfile"

    local line_count_after
    line_count_after=$(wc -l < "$tmpfile")
    local lines_removed=$((line_count_before - line_count_after))

    # SAFETY: every line deleted above must be a recognisable CCM artifact.
    # The header is bounded (24/26/27 lines) but the history trail is not, so
    # a fixed line cap is wrong here — it would block the one-time cleanup of
    # an already-bloated trail and, via `|| true`, silently append a second
    # header. Instead assert the deletions are a subset of the CCM artifact
    # family; a broader/buggy sed pattern is what this actually needs to catch.
    local artifact_lines
    artifact_lines=$(grep -cE '^.{0,9}(% ?ccm_|%git_commit_history|TermiteTowers Continuous Code Management Header TEMPLATE|tt-ccm\.header\.end)' "$file" || true)
    if [ "$lines_removed" -gt "$artifact_lines" ]; then
        echo "[ERROR] SAFETY: removed $lines_removed line(s) but only $artifact_lines CCM artifact line(s) present in $file. Aborting." >&2
        rm -f "$tmpfile"
        return 1
    fi

    if cmp -s "$file" "$tmpfile"; then
        echo "[WARN] No header lines removed from $file" >&2
        rm -f "$tmpfile"
        return 1  # No header found — signal to caller
    fi

    mv "$tmpfile" "$file"
    return 0
}

# ─────────────────────────────────────────────────────────────────
# parse_template_directives "$template_file"
#
# Returns template directives: TEMPLATE_ASIS, HISTORY_ASIS,
# COMMIT_HISTORY_FORMAT. Also strips directive lines from the
# working copy.
# ─────────────────────────────────────────────────────────────────
parse_template_directives() {
    local tmpfile="$1"

    TEMPLATE_ASIS=""
    HISTORY_ASIS=""
    COMMIT_HISTORY_FORMAT=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^##TEMPLATE_ASIS ]]; then
            TEMPLATE_ASIS="yes"
        elif [[ "$line" =~ ^##HISTORY_ASIS ]]; then
            HISTORY_ASIS="yes"
        elif [[ "$line" =~ ^##COMMIT_HISTORY:[[:space:]]*(.*) ]]; then
            COMMIT_HISTORY_FORMAT="${BASH_REMATCH[1]}"
        fi
    done < "$tmpfile"

    # Remove directive lines from working copy
    sed -i '/^##TEMPLATE_ASIS$/d; /^##HISTORY_ASIS$/d; /^##COMMIT_HISTORY:/d' "$tmpfile"
}

# ─────────────────────────────────────────────────────────────────
# format_ccm_header "$template_file" "$block_start" "$block_end" \
#                    "$line_comment" "$line_end"
#
# Formats the CCM header lines and writes them to stdout.
# Output is captured by the caller into a temp file.
# ─────────────────────────────────────────────────────────────────
format_ccm_header() {
    local tpl_file="$1"
    local block_start="$2"
    local block_end="$3"
    local line_comment="$4"
    local line_end="$5"

    local tmp_header
    tmp_header=$(mktemp)
    cp "$tpl_file" "$tmp_header"

    parse_template_directives "$tmp_header"

    # Read all template lines (stripped of CR)
    local header_lines=()
    local line
    while IFS= read -r line; do
        line="${line%$'\r'}"
        header_lines+=("$line")
    done < "$tmp_header"

    if [ "$TEMPLATE_ASIS" = "yes" ]; then
        # ASIS mode: emit every line verbatim
        for l in "${header_lines[@]}"; do
            echo "$l"
        done
    else
        # Default mode: wrap with language comment syntax
        local count=${#header_lines[@]}
        for i in "${!header_lines[@]}"; do
            local out_line="${header_lines[$i]}"
            if [ "$i" -eq 0 ]; then
                out_line="${block_start}${line_comment} $out_line"
            else
                out_line="$line_comment $out_line"
            fi
            if [ "$i" -eq $((count - 1)) ]; then
                out_line="$out_line $block_end"
            fi
            if [ -n "$line_end" ]; then
                out_line="$out_line$line_end"
            fi
            echo "$out_line"
        done
    fi

    # Append preserved commit history as a new line. Skipped when the identical
    # entry is already present in the preserved trail, so re-running the hook on
    # an unchanged commit does not duplicate it.
    if [ -n "$PRESERVED_COMMIT_MSG" ] && [ -n "$COMMIT_HISTORY_FORMAT" ]; then
        local hist="${COMMIT_HISTORY_FORMAT}"
        hist="${hist//\$MESSAGE/$PRESERVED_COMMIT_MSG}"
        hist="${hist//\$DATE/$PRESERVED_COMMIT_DATE}"
        hist="${hist//\$AUTHOR/$PRESERVED_COMMIT_AUTHOR}"
        local hist_out
        if [ "$HISTORY_ASIS" = "yes" ]; then
            hist_out="$hist"
        else
            hist_out="${block_start}${line_comment} $hist $block_end"
        fi
        local existing duplicate=""
        for existing in "${OLD_HISTORY_LINES[@]}"; do
            if [ "$existing" = "$hist_out" ]; then
                duplicate="yes"
                break
            fi
        done
        if [ -z "$duplicate" ]; then
            echo "$hist_out"
        fi
    fi

    # Re-emit old history lines (survived header removal)
    for old_line in "${OLD_HISTORY_LINES[@]}"; do
        echo "$old_line"
    done

    rm -f "$tmp_header"
}

# ─────────────────────────────────────────────────────────────────
# apply_ccm_field_updates "$file" "$lang_mode" "$author" "$author_email" \
#     "$repo" "$branch"
#
# Applies sed replacements for all CCM fields. Shared between
# pre-commit (sets unknown for commit-bound fields) and post-commit
# (fills final values) and update-ccm-header.
# ─────────────────────────────────────────────────────────────────
apply_ccm_field_updates() {
    local file="$1"
    local lang_mode="$2"
    local author="${3-}"
    local author_email="${4-}"
    local repo="${5-}"
    local branch="${6-}"
    local commit_id="${7:-unknown}"
    local commit_count="${8:-unknown}"
    local commit_message="${9:-unknown}"
    local commit_author="${10:-unknown}"
    local commit_email="${11:-unknown}"
    local commit_date="${12:-unknown}"

    # %ccm_git_object_id is <path>@<repo-depth ordinal>. post-commit is
    # authoritative once the commit lands, but pre-commit must still write a
    # correct value: the post-commit amend is skipped when the branch is behind
    # upstream, and "unknown" would then leave the field permanently empty.
    # The pending commit becomes depth+1, so predict that here.
    local object_depth="$commit_count"
    if [ -z "$object_depth" ] || [ "$object_depth" = "unknown" ]; then
        object_depth=$(git rev-list --count HEAD 2>/dev/null || echo 0)
        object_depth=$((object_depth + 1))
    fi
    local object_id="${FILE_PATH}@${object_depth}"

    sed -i \
        -e "s|%ccm_git_modify_date: .* %|%ccm_git_modify_date: $FILE_MODIFY_DATE %|g" \
        -e "s|%ccm_git_author: .* %|%ccm_git_author: ${author:-unknown} %|g" \
        -e "s|%ccm_git_author_email: .* %|%ccm_git_author_email: ${author_email:-unknown} %|g" \
        -e "s|%ccm_git_repo: .* %|%ccm_git_repo: ${repo:-unknown} %|g" \
        -e "s|%ccm_git_branch: .* %|%ccm_git_branch: ${branch:-unknown} %|g" \
        -e "s|%ccm_git_object_id: .* %|%ccm_git_object_id: ${object_id} %|g" \
        -e "s|%ccm_git_commit_id: .* %|%ccm_git_commit_id: ${commit_id} %|g" \
        -e "s|%ccm_git_commit_count: .* %|%ccm_git_commit_count: ${commit_count} %|g" \
        -e "s|%ccm_git_commit_message: .* %|%ccm_git_commit_message: ${commit_message} %|g" \
        -e "s|%ccm_git_commit_author: .* %|%ccm_git_commit_author: ${commit_author} %|g" \
        -e "s|%ccm_git_commit_email: .* %|%ccm_git_commit_email: ${commit_email} %|g" \
        -e "s|%ccm_git_commit_date: .* %|%ccm_git_commit_date: ${commit_date} %|g" \
        -e "s|%ccm_git_file_last_modified: .* %|%ccm_git_file_last_modified: $FILE_LAST_MODIFIED %|g" \
        -e "s|%ccm_git_file_name: .* %|%ccm_git_file_name: $FILE_NAME %|g" \
        -e "s|%ccm_git_file_type: .* %|%ccm_git_file_type: $FILE_TYPE %|g" \
        -e "s|%ccm_git_file_encoding: .* %|%ccm_git_file_encoding: $FILE_ENCODING %|g" \
        -e "s|%ccm_git_file_eol: .* %|%ccm_git_file_eol: $FILE_EOL %|g" \
        -e "s|%ccm_git_path: .* %|%ccm_git_path: $FILE_PATH %|g" \
        -e "s|%ccm_git_blob_sha: .* %|%ccm_git_blob_sha: $FILE_BLOB_SHA %|g" \
        -e "s|%ccm_git_exec: .* %|%ccm_git_exec: $FILE_EXEC_FLAG %|g" \
        -e "s|%ccm_git_size: .* %|%ccm_git_size: $FILE_SIZE %|g" \
        -e "s|%ccm_git_tag: .* %|%ccm_git_tag:  %|g" \
        -e "s|%ccm_git_language_mode: .* %|%ccm_git_language_mode: $lang_mode %|g" \
        "$file"
}

# ─────────────────────────────────────────────────────────────────
# preserve_permissions "$file"
#
# Restores original execute bit after all file modifications.
# Uses FILE_EXEC_FLAG captured by capture_file_metadata().
# ─────────────────────────────────────────────────────────────────
preserve_permissions() {
    local file="$1"
    if [ "$FILE_EXEC_FLAG" = "yes" ]; then
        chmod +x "$file"
    fi
}

# ─────────────────────────────────────────────────────────────────
# insert_header_after_shebang "$file" "$formatted_header"
#
# Inserts the formatted header into the file, preserving shebang
# or pseudo-shebang as the first line. Replaces file in-place.
# ─────────────────────────────────────────────────────────────────
insert_header_after_shebang() {
    local file="$1"
    local header_file="$2"

    local first_line
    first_line=$(head -n 1 "$file")

    local newfile="${file}.new"

    if head -n 1 "$file" | grep -q '^#!'; then
        { head -n 1 "$file"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif echo "$first_line" | grep -qiE '^(#!|#Requires |# yaml-language-server:|# *coding[:=]|# *-\*- coding:|<\?xml|<!DOCTYPE html|<\?php)'; then
        { echo "$first_line"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif [[ "$file" == *.json ]] && echo "$first_line" | grep -q '^{'; then
        { echo "$first_line"; cat "$header_file"; tail -n +2 "$file"; } > "$newfile"
    elif [[ "$file" == *.bat || "$file" == *.cmd ]]; then
        { head -n 1 "$file" | grep -qiE '^@echo|^echo' && head -n 1 "$file" || echo "@echo off"
          cat "$header_file"
          tail -n +2 "$file"; } > "$newfile"
    else
        { cat "$header_file"; cat "$file"; } > "$newfile"
    fi

    if cmp -s "$file" "$newfile"; then
        echo "[ERROR] Header insertion produced no change for $file" >&2
        rm -f "$newfile"
        return 1
    fi

    mv "$newfile" "$file"
    return 0
}