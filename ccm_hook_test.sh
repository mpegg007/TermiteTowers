#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: ccm_hook_test.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:33 %
# % ccm_file_name: ccm_hook_test.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: ccm_hook_test.sh %
# % ccm_blob_sha: 12017a5672a0a74fb8c05ab7130fd704cdffd5ed %
# % ccm_exec: yes %
# % ccm_size: 1148 %
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
