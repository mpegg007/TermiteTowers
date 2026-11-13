#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/git-automation/test_eol_and_markdown.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 262225dda6d4a34b1c915abd590a89427bf2ea8f %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: test_eol_and_markdown.sh %
#  %ccm_git_path: tests/git-automation/test_eol_and_markdown.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 9298 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Test suite for EOL classification and the compact markdown CCM header.
# Usage: ./tests/git-automation/test_eol_and_markdown.sh
#
# Covers the regression that motivated detect-eol.sh:
#   `grep -q $'\r\n'` split into CR + an empty alternative, so the empty
#   branch matched every line and every file was reported as CRLF.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DETECT_EOL="$REPO_ROOT/git-automation/detect-eol.sh"
DETECT_LANG_V2="$REPO_ROOT/git-automation/v2/detect-language.sh"
DETECT_LANG_V1="$REPO_ROOT/git-automation/get_language_mode_and_comments.sh"
CCM_APPLY="$REPO_ROOT/git-automation/v2/ccm-apply.sh"
RESULTS_FILE="$SCRIPT_DIR/results.xml"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

set -uo pipefail

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILURES=0
TESTS=0

echo "Running EOL + markdown header tests against: $REPO_ROOT"
echo "<testsuites>" > "$RESULTS_FILE"
echo "  <testsuite name=\"EolAndMarkdown\">" >> "$RESULTS_FILE"

pass() {
    TESTS=$((TESTS+1))
    printf "${GREEN}PASS${NC}: %s\n" "$1"
    echo "    <testcase name=\"$1\"/>" >> "$RESULTS_FILE"
}

fail() {
    TESTS=$((TESTS+1))
    FAILURES=$((FAILURES+1))
    printf "${RED}FAIL${NC}: %s\n" "$1"
    printf "      Expected: %s\n" "$2"
    printf "      Actual:   %s\n" "$3"
    echo "    <testcase name=\"$1\"><failure message=\"$2 != $3\"/></testcase>" >> "$RESULTS_FILE"
}

check() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        pass "$name"
    else
        fail "$name" "$expected" "$actual"
    fi
}

# ── Fixtures ─────────────────────────────────────────────────────
printf 'line1\nline2\nline3\n'        > "$WORK/lf.txt"
printf 'line1\r\nline2\r\nline3\r\n'  > "$WORK/crlf.txt"
printf 'a\rb\rc\r'                    > "$WORK/cr.txt"
printf 'a\0b\n'                       > "$WORK/nul.txt"
: > "$WORK/empty.txt"
printf '\377\376r\000e\000a\000d\000\n\000' > "$WORK/utf16le.txt"

# ── detect-eol.sh classification ─────────────────────────────────
echo ""
echo "── detect-eol.sh ──"
check "LF file is LF"             "LF"     "$(bash "$DETECT_EOL" "$WORK/lf.txt")"
check "CRLF file is CRLF"         "CRLF"   "$(bash "$DETECT_EOL" "$WORK/crlf.txt")"
check "CR-only file is CR"        "CR"     "$(bash "$DETECT_EOL" "$WORK/cr.txt")"
check "NUL file is BINARY"        "BINARY" "$(bash "$DETECT_EOL" "$WORK/nul.txt")"
check "UTF-16LE file is BINARY"   "BINARY" "$(bash "$DETECT_EOL" "$WORK/utf16le.txt")"
check "Empty file is EMPTY"       "EMPTY"  "$(bash "$DETECT_EOL" "$WORK/empty.txt")"
check "Missing file is EMPTY"     "EMPTY"  "$(bash "$DETECT_EOL" "$WORK/nope-xyz")"
check "No argument is EMPTY"      "EMPTY"  "$(bash "$DETECT_EOL")"

# The old idiom, kept as an explicit canary: it must NOT be trusted.
# A pure-LF file used to be misreported as CRLF by this exact expression.
echo ""

# ── Language detectors propagate line_end ────────────────────────
echo "── line_end plumbing ──"
printf '# My Doc\n\nSome text.\n' > "$WORK/doc.md"

IFS='|' read -r _ _ _ _ v2_lf_end _   <<< "$(bash "$DETECT_LANG_V2" "$WORK/lf.txt")"
IFS='|' read -r _ _ _ _ v2_crlf_end _ <<< "$(bash "$DETECT_LANG_V2" "$WORK/crlf.txt")"
check "v2 detect-language: LF file has empty line_end"  ""      "$v2_lf_end"
check "v2 detect-language: CRLF file has CR line_end"   $'\r'   "$v2_crlf_end"

IFS='|' read -r _ _ _ _ v1_lf_end _   <<< "$(bash "$DETECT_LANG_V1" "$WORK/lf.txt")"
IFS='|' read -r _ _ _ _ v1_crlf_end _ <<< "$(bash "$DETECT_LANG_V1" "$WORK/crlf.txt")"
check "v1 helper: LF file has empty line_end"           ""      "$v1_lf_end"
check "v1 helper: CRLF file has CR line_end"            $'\r'   "$v1_crlf_end"

IFS='|' read -r _ _ _ _ _ v2_md_tpl <<< "$(bash "$DETECT_LANG_V2" "$WORK/doc.md")"
check "v2 detects markdown template" "CCM_MARKDOWN_HEADER_TEMPLATE.txt" "$v2_md_tpl"

IFS='|' read -r _ _ _ _ _ v1_md_tpl <<< "$(bash "$DETECT_LANG_V1" "$WORK/doc.md")"
check "v1 detects shared markdown template" "v2/CCM_MARKDOWN_HEADER_TEMPLATE.txt" "$v1_md_tpl"

# ── Compact markdown header shape ────────────────────────────────
echo ""
echo "── markdown header ──"
printf '# My Doc\n\nSome text.\n' > "$WORK/doc.md"
(cd "$REPO_ROOT" && bash "$CCM_APPLY" "$WORK/doc.md" "docs/doc.md" >/dev/null 2>&1)

header_span=$(awk '/ccm_git_header_start/{s=NR} /ccm_git_header_end/{e=NR} END{print e-s+1}' "$WORK/doc.md")
check "markdown header is 9 lines (was 24)" "9" "$header_span"

non_comment=$(awk '/ccm_git_header_start/{f=1} f && !/^<!--.*-->$/ && NR>0 {c++} /ccm_git_header_end/{f=0} END{print c+0}' "$WORK/doc.md")
check "every markdown header line is an HTML comment" "0" "$non_comment"

check "markdown header is idempotent on re-run" "1" \
    "$( (cd "$REPO_ROOT" && bash "$CCM_APPLY" "$WORK/doc.md" "docs/doc.md" >/dev/null 2>&1); grep -c 'ccm_git_header_start' "$WORK/doc.md")"

# Fields proven wrong by the amend design must not appear in the compact block.
check "no always-stale commit_id in markdown header" "0" \
    "$(grep -c 'ccm_git_commit_id' "$WORK/doc.md" 2>/dev/null || true)"
check "no always-stale blob_sha in markdown header" "0" \
    "$(grep -c 'ccm_git_blob_sha' "$WORK/doc.md" 2>/dev/null || true)"

# ── object_id format: path@depth, never path:depth ───────────────
echo ""
echo "── object_id format ──"
printf '# Fmt\n\nBody.\n' > "$WORK/fmt.md"
(cd "$REPO_ROOT" && bash "$CCM_APPLY" "$WORK/fmt.md" "docs/fmt.md" >/dev/null 2>&1)

# Pre-commit alone must already write path@depth: the post-commit amend is
# skipped when the branch is behind upstream, so "unknown" is not acceptable.
pre_oid=$(grep -m1 -o 'ccm_git_object_id: [^%]*' "$WORK/fmt.md" | sed 's/.*ccm_git_object_id: //;s/ *$//')
check "object_id is populated by pre-commit alone" "yes" \
    "$( printf '%s' "$pre_oid" | grep -qE '^[^:]+@[0-9]+$' && echo yes || echo no )"

# post-commit --try finalizes commit-bound fields without git add/amend
(cd "$REPO_ROOT" && bash "$REPO_ROOT/git-automation/v2/post-commit.sh" "$WORK/fmt.md" --try >/dev/null 2>&1)

oid=$(grep -m1 -o 'ccm_git_object_id: [^%]*' "$WORK/fmt.md" | sed 's/.*ccm_git_object_id: //;s/ *$//')
check "object_id is populated by post-commit" "yes" \
    "$( [ -n "$oid" ] && echo yes || echo no )"
check "object_id matches path@depth" "yes" \
    "$( printf '%s' "$oid" | grep -qE '^[^:]+@[0-9]+$' && echo yes || echo no )"
check "object_id has no colon (cannot be misread as file:line)" "no" \
    "$( printf '%s' "$oid" | grep -q ':' && echo yes || echo no )"
check "redundant path field is deliberately retained" "1" \
    "$(grep -c 'ccm_git_path' "$WORK/fmt.md" 2>/dev/null || true)"

# ── End-to-end CRLF preservation through ccm-apply ───────────────
echo ""
echo "── CRLF preservation ──"
printf '#!/bin/bash\r\n# body\r\necho hi\r\n' > "$WORK/crlf.sh"
(cd "$REPO_ROOT" && bash "$CCM_APPLY" "$WORK/crlf.sh" "test/crlf.sh" >/dev/null 2>&1)
cr=$(LC_ALL=C tr -dc '\r' < "$WORK/crlf.sh" | wc -c)
lf=$(LC_ALL=C tr -dc '\n' < "$WORK/crlf.sh" | wc -c)
check "CRLF file keeps one CR per LF after header injection" "$lf" "$cr"
check "CRLF file grew a header (more lines than before)" "yes" \
    "$( [ "$lf" -gt 3 ] && echo yes || echo no )"

printf '#!/bin/bash\n# body\necho hi\n' > "$WORK/lf.sh"
(cd "$REPO_ROOT" && bash "$CCM_APPLY" "$WORK/lf.sh" "test/lf.sh" >/dev/null 2>&1)
cr_lf=$(LC_ALL=C tr -dc '\r' < "$WORK/lf.sh" | wc -c)
check "LF file gets no stray CR" "0" "$cr_lf"

echo ""
echo "------------------------------------------------"
echo "Tests: $TESTS | Failures: $FAILURES"
echo "  </testsuite>" >> "$RESULTS_FILE"
echo "</testsuites>" >> "$RESULTS_FILE"

if [ "$FAILURES" -gt 0 ]; then
    printf "${RED}SOME TESTS FAILED${NC}\n"
    exit 1
fi
printf "${GREEN}ALL TESTS PASSED${NC}\n"
exit 0
