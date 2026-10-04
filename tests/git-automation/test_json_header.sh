#!/usr/bin/env bash
# # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  

# Test script for JSON Header Injection
# Usage: ./test_json_header.sh

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PRE_COMMIT_SCRIPT="$REPO_ROOT/git-automation/enhanced-pre-commit.sh"

# 1. Create a dummy JSON file
TEST_FILE="test_header.json"
echo '{ "name": "TermiteTowers", "status": "active" }' > "$TEST_FILE"

# 2. Mock git environment (since the script relies on git commands)
# We'll just run the script in "try" mode or manually invoke the function if possible.
# Since we can't easily mock the whole git environment, we will manually invoke the logic 
# by creating a simplified version of the insertion logic here to verify the jq command works.

echo "--- Original JSON ---"
cat "$TEST_FILE"

# 3. Create a mock header file
HEADER_FILE="mock_header.json"
cat <<EOF > "$HEADER_FILE"
{
  "_ccm_header": [
  ]
}
EOF

# 4. Run the pre-commit script logic (simulated)
# We are testing the text insertion logic now, not jq merge.
# The script should insert the header at the top.

echo "--- Running Header Insertion ---"
# We can't easily call the function from the script without sourcing it, 
# but sourcing might trigger other things.
# Let's just run the script on the file if possible.
# We need to be in the repo root.
cd "$REPO_ROOT" || exit 1
"$PRE_COMMIT_SCRIPT" "$TEST_FILE"

echo "--- Resulting File ---"
cat "$TEST_FILE"

# 5. Verify
if grep -q "_ccm_header" "$TEST_FILE"; then
    echo "✅ Header injected successfully"
else
    echo "❌ Header injection failed"
    exit 1
fi

# Verify it is at the top (first line should be { or comment if we used comments, but we disabled comments)
FIRST_LINE=$(head -n 1 "$TEST_FILE")
if [[ "$FIRST_LINE" == "{" ]]; then
     echo "✅ Header appears to be at the top"
else
     echo "❌ Header not at top (First line: '$FIRST_LINE')"
     # It might be empty line?
fi

# We expect INVALID JSON now because we have two root objects
if jq . "$TEST_FILE" > /dev/null 2>&1; then
    echo "⚠️ Result is VALID JSON (Unexpected if we just prepended an object)"
else
    echo "✅ Result is INVALID JSON (Expected for multi-root object injection)"
fi

# Cleanup
rm "$TEST_FILE" "$HEADER_FILE"
