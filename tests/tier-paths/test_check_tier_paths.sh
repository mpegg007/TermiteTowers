#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/tier-paths/test_check_tier_paths.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: ac53171e733866dd66f61ce882f1c89aa4fbc9f8 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: test_check_tier_paths.sh %
#  %ccm_git_path: tests/tier-paths/test_check_tier_paths.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 13682 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Test suite for scripts/check-tier-paths.py.
# Usage: ./tests/tier-paths/test_check_tier_paths.sh
#
# Goal: prove the checker ENFORCES the tier rule, not merely reports on it.
# Every test below is a case that must go red, plus the allowlisted and
# correctly-tiered cases that must stay green. A checker that never fails is
# worse than no checker: it certifies files it never examined.
#
# The property under test, from plans/per-tier-secrets.md §3:
#   in *-<tier>.yml, every absolute host path carries <tier> as a path
#   COMPONENT, or matches the reviewed allowlist.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CHECKER="$REPO_ROOT/scripts/check-tier-paths.py"
RESULTS_FILE="$SCRIPT_DIR/results.xml"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

set -uo pipefail

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

ALLOWLIST="$WORK/allowlist.conf"
cat > "$ALLOWLIST" <<'ALLOW'
/etc/localtime   | ok      | host clock
/var/run/docker.sock | ok  | accepted risk
/mnt/ai_storage/models/* | ok | shared caches
/gallery/shares/* | must-ro | photo pools shared; non-owner ro
ALLOW

FAILURES=0
TESTS=0

echo "Running tier-path checker tests against: $REPO_ROOT"
echo "<testsuites>" > "$RESULTS_FILE"
echo "  <testsuite name=\"TierPaths\">" >> "$RESULTS_FILE"

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

# run <compose-file> [extra args...] -> sets RC and OUT
run() {
    local file="$1"; shift
    OUT="$(python3 "$CHECKER" "$file" \
        --allowlist "$ALLOWLIST" \
        --baseline "$WORK/baseline.txt" \
        --repo-root "$WORK" "$@" 2>&1)"
    RC=$?
}

# mk <name> <<'EOF' ... EOF
mk() {
    cat > "$WORK/$1"
    echo "$WORK/$1"
}

# expect <label> <exit-code> <class-or-'clean'>
expect() {
    local label="$1" want_rc="$2" want_class="$3"
    if [ "$want_class" = "clean" ]; then
        if [ "$RC" -eq 0 ] && ! grep -qE '\[(PATH_TIER|REL_ENV|SHARED_RW)\]' <<<"$OUT"; then
            pass "$label"
        else
            fail "$label" "exit 0, no violations" "exit $RC / $(grep -oE '\[[A-Z_]+\]' <<<"$OUT" | tr '\n' ' ')"
        fi
    else
        if [ "$RC" -eq "$want_rc" ] && grep -q "\[$want_class\]" <<<"$OUT"; then
            pass "$label"
        else
            fail "$label" "exit $want_rc with [$want_class]" "exit $RC / $(grep -oE '\[[A-Z_]+\]' <<<"$OUT" | tr '\n' ' ')"
        fi
    fi
}

# ---------------------------------------------------------------------------
# 1. The happy path: a correctly tiered file is silent.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/dev1/svc/data:/data
    env_file:
      - /etc/tt-secrets/dev1/env/svc.env
EOF
)"
run "$f" --strict
expect "tier-correct paths pass" 0 clean

# ---------------------------------------------------------------------------
# 2. The bug this exists to stop: a prd file mounting dev1's data.
# ---------------------------------------------------------------------------
f="$(mk svc-prd1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/dev1/svc/data:/data
EOF
)"
run "$f" --strict
expect "prd1 file mounting dev1 data fails" 1 PATH_TIER

# ---------------------------------------------------------------------------
# 3. Component match, not substring: 'dev11' must not satisfy 'dev1'.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/dev11/svc/data:/data
EOF
)"
run "$f" --strict
expect "dev11 does not satisfy dev1 (component not substring)" 1 PATH_TIER

# ---------------------------------------------------------------------------
# 4. env_file given as an absolute path with no tier segment.
#    This is the current /etc/tt-secrets/env/<name>.env shape.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    env_file:
      - /etc/tt-secrets/env/svc.env
EOF
)"
run "$f" --strict
expect "flat /etc/tt-secrets/env path fails" 1 PATH_TIER

# ---------------------------------------------------------------------------
# 5. Relative env_file: absent from a deployed tree, so REL_ENV.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    env_file:
      - ./env/svc.env
EOF
)"
run "$f" --strict
expect "relative env_file fails" 1 REL_ENV

# ---------------------------------------------------------------------------
# 6. secrets/configs `file:` is covered too.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    secrets:
      - pw
secrets:
  pw:
    file: ./env/pw.txt
EOF
)"
run "$f" --strict
expect "relative secrets file fails" 1 REL_ENV

# ---------------------------------------------------------------------------
# 7. Allowlisted shared paths stay silent, including the glob.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /mnt/ai_storage/models/huggingface:/models/hf
EOF
)"
run "$f" --strict
expect "allowlisted shared paths pass" 0 clean

# ---------------------------------------------------------------------------
# 8/9. must-ro: read-write is the violation, ':ro' is fine.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /gallery/shares/mpegg:/photos
EOF
)"
run "$f" --strict
expect "shared photo pool mounted rw fails" 1 SHARED_RW

f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /gallery/shares/mpegg:/photos:ro
EOF
)"
run "$f" --strict
expect "shared photo pool mounted ro passes" 0 clean

# ---------------------------------------------------------------------------
# 10. Commented-out mounts must not be reported (snipeit carries a whole
#     usage block of absolute paths in comments).
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      # - /mnt/ai_storage/other/data:/data
      - /mnt/ai_storage/dev1/svc/data:/data
EOF
)"
run "$f" --strict
expect "commented-out mount ignored" 0 clean

# ---------------------------------------------------------------------------
# 11. Long-form volumes source: and build context are covered.
# ---------------------------------------------------------------------------
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    build:
      context: /home/someone/elsewhere
    volumes:
      - type: bind
        source: /mnt/ai_storage/dev1/svc/data
        target: /data
EOF
)"
run "$f" --strict
expect "build context without tier fails" 1 PATH_TIER
if grep -q '/home/someone/elsewhere' <<<"$OUT"; then
    pass "build context is the reported subject"
else
    fail "build context is the reported subject" "/home/someone/elsewhere named" "$(head -3 <<<"$OUT")"
fi

# ---------------------------------------------------------------------------
# 12. Untiered filenames are skipped, not silently passed.
# ---------------------------------------------------------------------------
f="$(mk svc.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/dev1/svc/data:/data
EOF
)"
run "$f" --strict
check "untiered file skipped (no violations)" 0 "$RC"
if grep -qi 'no tier token' <<<"$OUT"; then
    pass "untiered file is reported as skipped"
else
    fail "untiered file is reported as skipped" "a 'no tier token' note" "$OUT"
fi

# ---------------------------------------------------------------------------
# 13. Baseline ratchet: accept, then catch regressions only.
# ---------------------------------------------------------------------------
BL="$WORK/ratchet-baseline.txt"
f="$(mk svc-dev1.yml <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/svc/data:/data
EOF
)"
python3 "$CHECKER" "$f" --allowlist "$ALLOWLIST" --baseline "$BL" \
    --repo-root "$WORK" --baseline-write >/dev/null 2>&1
if [ -s "$BL" ]; then
    pass "baseline file written with entries"
else
    fail "baseline file written with entries" "non-empty $BL" "missing/empty"
fi

OUT="$(python3 "$CHECKER" "$f" --allowlist "$ALLOWLIST" --baseline "$BL" \
    --repo-root "$WORK" 2>&1)"; RC=$?
if [ "$RC" -eq 0 ] && grep -q 'pre-existing' <<<"$OUT"; then
    pass "baselined violation no longer fails"
else
    fail "baselined violation no longer fails" "exit 0 w/ pre-existing note" "exit $RC / $OUT"
fi

# Drop the baseline: the same file must fail again (ratchet is not a mute).
: > "$BL"
OUT="$(python3 "$CHECKER" "$f" --allowlist "$ALLOWLIST" --baseline "$BL" \
    --repo-root "$WORK" 2>&1)"; RC=$?
check "emptied baseline fails again" 1 "$RC"

# ---------------------------------------------------------------------------
# 14. A baseline entry must not absorb an unrelated new violation.
# ---------------------------------------------------------------------------
cat > "$BL" <<'EOF'
svc-dev1.yml|PATH_TIER|/mnt/ai_storage/svc/data
EOF
cat > "$WORK/svc-dev1.yml" <<'EOF'
services:
  app:
    image: busybox
    volumes:
      - /mnt/ai_storage/svc/data:/data
      - /mnt/ai_storage/svc/secret:/secret
EOF
OUT="$(python3 "$CHECKER" "$WORK/svc-dev1.yml" --allowlist "$ALLOWLIST" \
    --baseline "$BL" --repo-root "$WORK" 2>&1)"; RC=$?
if [ "$RC" -eq 1 ] && grep -q '/mnt/ai_storage/svc/secret' <<<"$OUT"; then
    pass "baseline does not absorb a new violation"
else
    fail "baseline does not absorb a new violation" "exit 1 naming /secret" "exit $RC / $OUT"
fi

# ---------------------------------------------------------------------------
# 15. The real tree: the checker runs and the allowlist actually bites.
# ---------------------------------------------------------------------------
OUT="$(python3 "$REPO_ROOT/scripts/check-tier-paths.py" --strict --json 2>/dev/null)"
if grep -q '"new_count"' <<<"$OUT"; then
    pass "runs against the real compose tree"
else
    fail "runs against the real compose tree" "json with new_count" "no output"
fi
for probe in '/etc/localtime' '/var/run/docker.sock' '/mnt/ai_storage/models/'; do
    if grep -q "\"path\": \"$probe" <<<"$OUT"; then
        fail "real tree: allowlisted $probe suppressed" "absent from report" "present"
    else
        pass "real tree: allowlisted $probe suppressed"
    fi
done

# ---------------------------------------------------------------------------
# 16. Running from a subdirectory must not silently lose the allowlist.
#     The defaults are repo-relative; resolved against the caller's CWD they
#     come back empty, and every shared path is then reported as a violation.
# ---------------------------------------------------------------------------
SUB_OUT="$(cd "$REPO_ROOT/infra/docker" && python3 "$REPO_ROOT/scripts/check-tier-paths.py" 2>&1)"
SUB_RC=$?
ROOT_OUT="$(cd "$REPO_ROOT" && python3 "$REPO_ROOT/scripts/check-tier-paths.py" 2>&1)"
ROOT_RC=$?
check "subdir run gives the same exit code as repo-root run" "$ROOT_RC" "$SUB_RC"
if grep -qE '\[(PATH_TIER|SHARED_RW)\] /gallery/shares/' <<<"$SUB_OUT"; then
    fail "subdir run still honours the allowlist" "no /gallery/shares violations" "shared path reported"
else
    pass "subdir run still honours the allowlist"
fi

echo "  </testsuite>" >> "$RESULTS_FILE"
echo "</testsuites>" >> "$RESULTS_FILE"

echo
echo "-------------------------------------------"
if [ "$FAILURES" -eq 0 ]; then
    printf "${GREEN}ALL %d TESTS PASSED${NC}\n" "$TESTS"
    exit 0
else
    printf "${RED}%d of %d TESTS FAILED${NC}\n" "$FAILURES" "$TESTS"
    exit 1
fi
