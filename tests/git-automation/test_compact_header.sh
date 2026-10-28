#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/git-automation/test_compact_header.sh@192 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 90c17429c20bfc63c8d218a95424cf1396a55281 %
#  %ccm_git_commit_id: 474193c0e3b1613e35051d9df26e7e13045a998e %
#  %ccm_git_commit_count: 192 %
#  %ccm_git_commit_date: 2026-10-28 17:04:18 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(ccm): make the compact header carry provenance, not just a flag %
#  %ccm_git_modify_date: 2026-10-28 17:04:18 %
#  %ccm_git_file_last_modified: 2026-10-28 17:00:11 %
#  %ccm_git_file_name: test_compact_header.sh %
#  %ccm_git_path: tests/git-automation/test_compact_header.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 11635 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# test_compact_header.sh: Tests for %ccm_compact one-line header mode.
#
# Contract under test:
#   A file whose FIRST LINE carries %ccm_compact gets a single-line header
#   instead of the 9/24-line block and the accumulating %git_commit_history
#   trail. The line carries real provenance:
#
#     <!-- %ccm_compact: path=<rel> branch=<branch> committed=<ISO8601> sha=<7> -->
#
#   ccm-apply.sh (pre-commit) refreshes path/branch and PRESERVES the recorded
#   commit fields, so a manual run never destroys them.
#   post-commit.sh overwrites committed=/sha= with HEAD's real values.
#
# Cases:
#   1. Line 1 becomes the informative compact header; line count unchanged
#   2. Idempotent: re-running ccm-apply produces an identical file
#   3. ccm-apply preserves an existing committed=/sha= pair
#   4. post-commit fills committed=/sha= from HEAD and keeps path= intact
#   5. No %git_commit_history trail is ever added
#   6. Detection is line-1-only: token on line 3 still gets the full header
#   7. A plain file still gets the full header
#   8. Prose mentioning %git_commit_history is not harvested as history
#      (regression canary for the unanchored-match bug fixed 2026-10-28)
#
# Usage: tests/git-automation/test_compact_header.sh

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CCM_APPLY="$REPO_ROOT/git-automation/v2/ccm-apply.sh"
POST_COMMIT="$REPO_ROOT/git-automation/v2/post-commit.sh"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

FAIL=0
pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; FAIL=1; }

for f in "$CCM_APPLY" "$POST_COMMIT"; do
    if [ ! -x "$f" ]; then
        echo -e "${RED}FAIL${NC}: not executable: $f"
        exit 1
    fi
done

cd "$REPO_ROOT" || exit 1

# Scratch dir must live inside the repo: ccm-apply.sh resolves paths via git.
WORK_DIR="$REPO_ROOT/tests/git-automation/.tmp-compact"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

rel_path_for() { realpath --relative-to="$REPO_ROOT" "$1"; }
field_of() { sed -nE "s/.*[[:space:]]$2=([^[:space:]]+).*/\1/p" <<< "$1"; }

HEAD_SHA=$(git rev-parse --verify HEAD 2>/dev/null | cut -c1-7 || echo "")

# ─────────────────────────────────────────────────────────────────
# Case 1: informative one-line header, line count unchanged
# ─────────────────────────────────────────────────────────────────
echo "=== Case 1: single informative line ==="
COMPACT="$WORK_DIR/status.md"
cat > "$COMPACT" <<'EOF'
<!-- %ccm_compact: -->
# Status

Current focus: nothing to see here.
EOF

BEFORE_LINES=$(wc -l < "$COMPACT" | tr -d ' ')
EXPECTED_REL="$(rel_path_for "$COMPACT")"

"$CCM_APPLY" "$COMPACT" "$EXPECTED_REL" 2>/dev/null || true
LINE1=$(head -n 1 "$COMPACT")

if grep -q '%ccm_compact' <<< "$LINE1"; then
    pass "line 1 still carries the %ccm_compact token"
else
    fail "line 1 lost the token: $LINE1"
fi

if [ "$(field_of "$LINE1" path)" = "$EXPECTED_REL" ]; then
    pass "line 1 records the real path ($EXPECTED_REL)"
else
    fail "path field is '$(field_of "$LINE1" path)', expected '$EXPECTED_REL'"
fi

if [ -n "$(field_of "$LINE1" branch)" ] && [ "$(field_of "$LINE1" branch)" != "unknown" ]; then
    pass "line 1 records the branch ($(field_of "$LINE1" branch))"
else
    fail "branch field missing or unknown"
fi

AFTER_LINES=$(wc -l < "$COMPACT" | tr -d ' ')
if [ "$AFTER_LINES" = "$BEFORE_LINES" ]; then
    pass "line count unchanged ($AFTER_LINES) - no block header added"
else
    fail "line count is $AFTER_LINES, expected $BEFORE_LINES"
fi

# ─────────────────────────────────────────────────────────────────
# Case 2: idempotent
# ─────────────────────────────────────────────────────────────────
echo "=== Case 2: idempotent ==="
cp "$COMPACT" "$WORK_DIR/status.run1"
"$CCM_APPLY" "$COMPACT" "$EXPECTED_REL" 2>/dev/null || true
if cmp -s "$COMPACT" "$WORK_DIR/status.run1"; then
    pass "second ccm-apply run produces an identical file"
else
    fail "second run changed the file"
    diff "$WORK_DIR/status.run1" "$COMPACT" | sed 's/^/    /'
fi

# ─────────────────────────────────────────────────────────────────
# Case 3: existing commit fields are preserved by ccm-apply
# ─────────────────────────────────────────────────────────────────
echo "=== Case 3: committed/sha preserved by ccm-apply ==="
cat > "$COMPACT" <<'EOF'
<!-- %ccm_compact: path=placeholder branch=placeholder committed=2026-01-02T03:04:05-05:00 sha=deadbee -->
# Status
EOF
"$CCM_APPLY" "$COMPACT" "$EXPECTED_REL" 2>/dev/null || true
LINE1=$(head -n 1 "$COMPACT")

if [ "$(field_of "$LINE1" committed)" = "2026-01-02T03:04:05-05:00" ]; then
    pass "committed= preserved across a ccm-apply run"
else
    fail "committed= became '$(field_of "$LINE1" committed)'"
fi

if [ "$(field_of "$LINE1" sha)" = "deadbee" ]; then
    pass "sha= preserved across a ccm-apply run"
else
    fail "sha= became '$(field_of "$LINE1" sha)'"
fi

# ─────────────────────────────────────────────────────────────────
# Case 4: post-commit fills HEAD values and keeps path
# ─────────────────────────────────────────────────────────────────
echo "=== Case 4: post-commit fills committed=/sha= from HEAD ==="
if [ -z "$HEAD_SHA" ]; then
    fail "no HEAD commit available to test against"
else
    "$POST_COMMIT" "$COMPACT" >/dev/null 2>&1 || true
    LINE1=$(head -n 1 "$COMPACT")

    if [ "$(field_of "$LINE1" sha)" = "$HEAD_SHA" ]; then
        pass "sha= updated to HEAD ($HEAD_SHA)"
    else
        fail "sha= is '$(field_of "$LINE1" sha)', expected '$HEAD_SHA'"
    fi

    if [[ "$(field_of "$LINE1" committed)" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
        pass "committed= is ISO 8601 without spaces ($(field_of "$LINE1" committed))"
    else
        fail "committed= is not ISO 8601: '$(field_of "$LINE1" committed)'"
    fi

    if [ "$(field_of "$LINE1" path)" = "$EXPECTED_REL" ]; then
        pass "path= survived post-commit (not clobbered to unknown)"
    else
        fail "post-commit set path= to '$(field_of "$LINE1" path)'"
    fi
fi

# ─────────────────────────────────────────────────────────────────
# Case 5: no history trail
# ─────────────────────────────────────────────────────────────────
echo "=== Case 5: no history trail ==="
if grep -q '%git_commit_history' "$COMPACT"; then
    fail "%git_commit_history was added to a compact file"
else
    pass "no %git_commit_history trail added"
fi

if [ "$(grep -c 'Continuous Code Management Header TEMPLATE' "$COMPACT")" = "0" ]; then
    pass "no block header present"
else
    fail "a block header leaked into a compact file"
fi

# ─────────────────────────────────────────────────────────────────
# Case 6: line-1-only detection
# ─────────────────────────────────────────────────────────────────
echo "=== Case 6: token on line 3 does NOT trigger compact mode ==="
LATE="$WORK_DIR/late-token.md"
cat > "$LATE" <<'EOF'
# Documented token

This doc merely describes `%ccm_compact:` usage.
EOF
"$CCM_APPLY" "$LATE" "$(rel_path_for "$LATE")" 2>/dev/null || true
if head -n 1 "$LATE" | grep -q 'Continuous Code Management Header'; then
    pass "full header applied when the token is not on line 1"
else
    fail "no block header applied; line 1 is: $(head -n 1 "$LATE")"
fi

# ─────────────────────────────────────────────────────────────────
# Case 7: plain file still gets the full header
# ─────────────────────────────────────────────────────────────────
echo "=== Case 7: plain file gets the full header ==="
PLAIN="$WORK_DIR/plain.md"
printf '# Plain\n\nNo token at all.\n' > "$PLAIN"
"$CCM_APPLY" "$PLAIN" "$(rel_path_for "$PLAIN")" 2>/dev/null || true
if head -n 1 "$PLAIN" | grep -q 'Continuous Code Management Header'; then
    pass "plain file received the standard header"
else
    fail "plain file did not receive a header"
fi
if grep -q '%ccm_git_path: ' "$PLAIN"; then
    pass "full-header fields populated"
else
    fail "full-header fields missing"
fi

# ─────────────────────────────────────────────────────────────────
# Case 8: prose mentioning %git_commit_history is not harvested
# ─────────────────────────────────────────────────────────────────
echo "=== Case 8: prose mentioning %git_commit_history is not harvested ==="
PROSE="$WORK_DIR/prose.md"
cat > "$PROSE" <<'EOF'
# Prose

The implementer should never remove the %git_commit_history row by hand.
A second sentence mentioning %git_commit_history again, mid-line.
EOF
"$CCM_APPLY" "$PROSE" "$(rel_path_for "$PROSE")" 2>/dev/null || true
PROSE_MID=$(wc -l < "$PROSE" | tr -d ' ')
"$CCM_APPLY" "$PROSE" "$(rel_path_for "$PROSE")" 2>/dev/null || true
PROSE_AFTER=$(wc -l < "$PROSE" | tr -d ' ')

if [ "$(grep -c '%git_commit_history' "$PROSE")" = "2" ]; then
    pass "both prose mentions survived"
else
    fail "expected 2 mentions, found $(grep -c '%git_commit_history' "$PROSE")"
fi

if [ "$PROSE_MID" = "$PROSE_AFTER" ]; then
    pass "re-running does not grow the file ($PROSE_AFTER lines)"
else
    fail "file grew on re-run: $PROSE_MID -> $PROSE_AFTER"
fi

if [ "$(grep -c 'Continuous Code Management Header TEMPLATE' "$PROSE")" = "2" ]; then
    pass "exactly one block header (2 marker lines)"
else
    fail "expected 2 header marker lines, found $(grep -c 'Continuous Code Management Header TEMPLATE' "$PROSE")"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}All compact-header tests passed${NC}"
    exit 0
else
    echo -e "${RED}Some compact-header tests FAILED${NC}"
    exit 1
fi
