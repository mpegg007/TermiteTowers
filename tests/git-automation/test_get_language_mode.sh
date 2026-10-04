#!/usr/bin/env bash
# # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  

# Test suite for get_language_mode_and_comments.sh
# Usage: ./test_get_language_mode.sh

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TARGET_SCRIPT="$REPO_ROOT/git-automation/get_language_mode_and_comments.sh"
RESULTS_FILE="$SCRIPT_DIR/results.xml"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Running tests against: $TARGET_SCRIPT"
echo "<testsuites>" > "$RESULTS_FILE"
echo "  <testsuite name=\"LanguageDetection\">" >> "$RESULTS_FILE"

FAILURES=0
TESTS=0

run_test() {
    local filename="$1"
    local expected_mode="$2"
    local expected_comment="$3"
    
    TESTS=$((TESTS+1))
    
    # Create dummy file to avoid 'head' errors in script
    touch "$filename"
    
    local output
    output=$("$TARGET_SCRIPT" "$filename")
    
    # Clean up
    rm "$filename"
    
    # Parse output: mode|block_start|block_end|line_comment
    local actual_mode=$(echo "$output" | cut -d'|' -f1)
    local actual_comment=$(echo "$output" | cut -d'|' -f4)
    
    if [[ "$actual_mode" == "$expected_mode" ]] && [[ "$actual_comment" == "$expected_comment" ]]; then
        echo -e "${GREEN}PASS${NC}: $filename -> $actual_mode"
        echo "    <testcase classname=\"LanguageDetection\" name=\"$filename\" />" >> "$RESULTS_FILE"
    else
        echo -e "${RED}FAIL${NC}: $filename"
        echo "      Expected: Mode='$expected_mode', Comment='$expected_comment'"
        echo "      Actual:   Mode='$actual_mode', Comment='$actual_comment'"
        FAILURES=$((FAILURES+1))
        echo "    <testcase classname=\"LanguageDetection\" name=\"$filename\">" >> "$RESULTS_FILE"
        echo "      <failure message=\"Expected $expected_mode, got $actual_mode\" />" >> "$RESULTS_FILE"
        echo "    </testcase>" >> "$RESULTS_FILE"
    fi
}

# --- Test Cases ---

# 1. Standard Python
run_test "script.py" "python" "#"

# 2. Standard Bash
run_test "script.sh" "shellscript" "#"

# 3. Dockerfile (No extension)
run_test "Dockerfile" "dockerfile" "#"

# 4. JSON (C-style comments allowed in VS Code JSONC)
run_test "config.json" "json" "//"

# 5. Terraform
run_test "main.tf" "terraform" "#"

# 6. Azure Bicep (The "New Feature" we want to add)
# Currently this should FAIL because we haven't added it yet
run_test "deploy.bicep" "bicep" "//"

# --- End Suite ---

echo "  </testsuite>" >> "$RESULTS_FILE"
echo "</testsuites>" >> "$RESULTS_FILE"

echo "------------------------------------------------"
echo "Tests: $TESTS | Failures: $FAILURES"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
