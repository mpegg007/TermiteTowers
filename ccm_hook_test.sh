#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:33:16 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: ccm_hook_test.sh:62 %
# % ccm_commit_id: d450999f33707bf562bcbdbb00f28d20c1dd488f %
# % ccm_commit_count: 62 %
# % ccm_commit_message: chore(repo): finalize infra flattening and wrapper shims %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-08-29 15:33:16 -0400 %
# % ccm_file_last_modified: 2025-08-29 15:33:16 %
# % ccm_file_name: ccm_hook_test.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: ccm_hook_test.sh %
# % ccm_blob_sha: 9f2284b19b8ef37e36534efe02cb2513f14f5f89 %
# % ccm_exec: no %
# % ccm_size: 1317 %
# % ccm_tag:  %
# tt-ccm.header.end

# Wrapper: forward to moved script
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
TARGET="$SCRIPT_DIR/scripts/system/ccm_hook_test.sh"
if [[ -f "$TARGET" ]]; then
	exec "$TARGET" "$@"
else
	echo "Moved script not found: $TARGET" >&2
	exit 1
fi
