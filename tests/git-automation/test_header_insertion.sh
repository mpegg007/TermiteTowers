#!/usr/bin/env bash
# # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  

# Test script for CCM Header Insertion (Shebang handling)
# Usage: ./tests/git-automation/test_header_insertion.sh

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PRE_COMMIT_SCRIPT="$REPO_ROOT/git-automation/enhanced-pre-commit.sh"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Setup dummy file
TEST_FILE="test_script.py"
echo "#!/usr/bin/env python3" > "$TEST_FILE"
echo "print('Hello World')" >> "$TEST_FILE"

echo "--- Original File ---"
cat "$TEST_FILE"

# Run the pre-commit script on the file
# We need to ensure we are in the repo root for the script to work correctly
cd "$REPO_ROOT" || exit 1

# The script expects to be run from repo root usually, or at least find git root.
# We pass the file as argument to trigger file mode.
"$PRE_COMMIT_SCRIPT" "$TEST_FILE"

echo "--- Processed File ---"
head -n 5 "$TEST_FILE"

# Verify
LINE1=$(head -n 1 "$TEST_FILE")
LINE2=$(head -n 2 "$TEST_FILE" | tail -n 1)

FAIL=0

if [[ "$LINE1" == "#!/usr/bin/env python3" ]]; then
    echo -e "${GREEN}PASS${NC}: Shebang preserved on line 1"
else
    echo -e "${RED}FAIL${NC}: Line 1 is '$LINE1', expected shebang"
    FAIL=1
fi

if [[ "$LINE2" == *"TermiteTowers Continuous Code Management Header TEMPLATE"* ]]; then
    echo -e "${GREEN}PASS${NC}: Header inserted on line 2"
else
    echo -e "${RED}FAIL${NC}: Line 2 does not start with header template"
    FAIL=1
fi

# Cleanup
rm "$TEST_FILE"

# --- Test Case 2: No Shebang ---
TEST_FILE_2="test_plain.txt"
echo "Just some text" > "$TEST_FILE_2"

echo "--- Original File 2 ---"
cat "$TEST_FILE_2"

"$PRE_COMMIT_SCRIPT" "$TEST_FILE_2"

echo "--- Processed File 2 ---"
head -n 3 "$TEST_FILE_2"

LINE1_2=$(head -n 1 "$TEST_FILE_2")

if [[ "$LINE1_2" == *"TermiteTowers Continuous Code Management Header TEMPLATE"* ]]; then
    echo -e "${GREEN}PASS${NC}: Header inserted on line 1 for plain file"
else
    echo -e "${RED}FAIL${NC}: Line 1 does not start with header template for plain file"
    FAIL=1
fi

rm "$TEST_FILE_2"

if [ $FAIL -eq 0 ]; then
    exit 0
else
    exit 1
fi
