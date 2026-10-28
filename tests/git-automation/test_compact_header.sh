#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/git-automation/test_compact_header.sh@190 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: def809b7ece45014f8ab892173e68bfd218b16fe %
#  %ccm_git_commit_id: 85f57600d664c6d5133411bec61113aee47c3cb8 %
#  %ccm_git_commit_count: 190 %
#  %ccm_git_commit_date: 2026-10-28 16:35:23 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: refactor(context): retire memory-bank and add %%ccm_compact status headers %
#  %ccm_git_modify_date: 2026-10-28 16:35:23 %
#  %ccm_git_file_last_modified: 2026-10-28 16:28:57 %
#  %ccm_git_file_name: test_compact_header.sh %
#  %ccm_git_path: tests/git-automation/test_compact_header.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 6665 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#   3. No %git_commit_history trail is ever added
if grep -q '%git_commit_history' "$COMPACT"; then
    fail "%git_commit_history trail was added to a compact file"
    pass "no %git_commit_history trail added"
# test_compact_header.sh: Tests for %ccm_compact opt-out mode.
#
# Contract under test (ccm-apply.sh Step 0):
#   A file whose FIRST LINE carries the %ccm_compact: token is left
#   completely untouched. The token is the header.
#
# Cases:
#   1. Compact file survives ccm-apply byte-identical, exit 0
#   2. Re-running is idempotent (no accumulation, still 1 line)
#   3. No %git_commit_history trail is ever added
#   4. post-commit.sh's gate does NOT recognise the file, so it is
#      skipped there too (no field rewrite, no amend churn)
#   5. Detection is line-1-only: the token on line 3 still gets a full
#      header, so docs that merely *describe* the token are unaffected
#   6. A plain file with no token still gets a normal CCM header
#
# Usage: tests/git-automation/test_compact_header.sh

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CCM_APPLY="$REPO_ROOT/git-automation/v2/ccm-apply.sh"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

FAIL=0
pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; FAIL=1; }

if [ ! -x "$CCM_APPLY" ]; then
    echo -e "${RED}FAIL${NC}: ccm-apply.sh not found or not executable at $CCM_APPLY"
    exit 1
fi

cd "$REPO_ROOT" || exit 1

# Scratch dir must live inside the repo: ccm-apply.sh resolves paths via git.
WORK_DIR="$REPO_ROOT/tests/git-automation/.tmp-compact"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

rel_path_for() {
    # Repo-relative path, which is what ccm-apply.sh records.
    realpath --relative-to="$REPO_ROOT" "$1"
}

# ─────────────────────────────────────────────────────────────────
# Case 1 + 2 + 3: compact file is untouched, idempotently, no history
# ─────────────────────────────────────────────────────────────────
echo "=== Case 1-3: compact file left untouched ==="
COMPACT="$WORK_DIR/status.md"
cat > "$COMPACT" <<'EOF'
<!-- %ccm_compact: -->
# Status

Current focus: nothing to see here.
EOF

cp "$COMPACT" "$WORK_DIR/status.before"
BEFORE_LINES=$(wc -l < "$WORK_DIR/status.before" | tr -d ' ')

"$CCM_APPLY" "$COMPACT" "$(rel_path_for "$COMPACT")" 2>/dev/null
RC=$?

if [ "$RC" -eq 0 ]; then
    pass "ccm-apply.sh exits 0 for a compact file"
else
    fail "ccm-apply.sh exited $RC for a compact file (expected 0)"
fi

if cmp -s "$COMPACT" "$WORK_DIR/status.before"; then
    pass "compact file is byte-identical after ccm-apply"
else
    fail "compact file was modified by ccm-apply"
    diff -u "$WORK_DIR/status.before" "$COMPACT" | sed 's/^/    /'
fi

"$CCM_APPLY" "$COMPACT" "$(rel_path_for "$COMPACT")" 2>/dev/null
if cmp -s "$COMPACT" "$WORK_DIR/status.before"; then
    pass "second run is idempotent (no accumulation)"
else
    fail "second run changed the file"
fi

LINE_COUNT=$(wc -l < "$COMPACT" | tr -d ' ')
if [ "$LINE_COUNT" = "$BEFORE_LINES" ]; then
    pass "line count unchanged ($LINE_COUNT lines)"
else
    fail "line count is $LINE_COUNT, expected $BEFORE_LINES"
fi

if grep -q '%git_commit_history' "$COMPACT"; then
    fail "%git_commit_history trail was added to a compact file"
else
    pass "no %git_commit_history trail added"
fi

# ─────────────────────────────────────────────────────────────────
# Case 4: post-commit.sh's gate does not recognise a compact file
# ─────────────────────────────────────────────────────────────────
echo "=== Case 4: post-commit gate excludes compact files ==="
# post-commit.sh only processes files matching this regex (line 98).
if grep -qE '%ccm_git_.*: .* %' "$COMPACT"; then
    fail "post-commit.sh WOULD process the compact file (gate matched) - amend churn expected"
else
    pass "post-commit.sh gate rejects the compact file, so it is skipped there too"
fi

# ─────────────────────────────────────────────────────────────────
# Case 5: detection is line-1-only
# ─────────────────────────────────────────────────────────────────
echo "=== Case 5: token on line 3 does NOT trigger compact mode ==="
LATE="$WORK_DIR/late-token.md"
cat > "$LATE" <<'EOF'
# Documented token

This doc merely describes `%ccm_compact:` usage.
EOF

"$CCM_APPLY" "$LATE" "$(rel_path_for "$LATE")" 2>/dev/null
RC=$?

if [ "$RC" -eq 0 ]; then
    pass "ccm-apply.sh exits 0 for a non-compact file"
else
    fail "ccm-apply.sh exited $RC for a non-compact file (expected 0)"
fi

if head -n 1 "$LATE" | grep -q 'Continuous Code Management Header'; then
    pass "full header applied when the token is not on line 1"
else
    fail "no header applied, or header not on line 1; line 1 is: $(head -n 1 "$LATE")"
fi

if cmp -s "$LATE" "$WORK_DIR/status.before"; then
    fail "file was NOT modified despite lacking a line-1 token"
fi

# ─────────────────────────────────────────────────────────────────
# Case 6: plain file still gets the normal header
# ─────────────────────────────────────────────────────────────────
echo "=== Case 6: plain file gets a normal header ==="
PLAIN="$WORK_DIR/plain.md"
cat > "$PLAIN" <<'EOF'
# Plain

No token at all.
EOF

"$CCM_APPLY" "$PLAIN" "$(rel_path_for "$PLAIN")" 2>/dev/null

if head -n 1 "$PLAIN" | grep -q 'Continuous Code Management Header'; then
    pass "plain file received the standard header"
else
    fail "plain file did not receive a header"
fi

if grep -q '%ccm_git_path: ' "$PLAIN"; then
    pass "header fields populated"
else
    fail "header fields missing"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}All compact-header tests passed${NC}"
    exit 0
else
    echo -e "${RED}Some compact-header tests FAILED${NC}"
    exit 1
fi
