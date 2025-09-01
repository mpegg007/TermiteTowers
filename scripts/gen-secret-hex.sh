#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-09-01 15:47:13 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/gen-secret-hex.sh:68 %
# % ccm_commit_id: fe785a319b8d06e69d2978b17dc9bb8512161977 %
# % ccm_commit_count: 68 %
# % ccm_commit_message: misc updated %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-09-01 15:47:12 -0400 %
# % ccm_file_last_modified: 2025-09-01 15:47:12 %
# % ccm_file_name: gen-secret-hex.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/gen-secret-hex.sh %
# % ccm_blob_sha: 6d97054a5f42e98885b0680a4cb5ac930938bedc %
# % ccm_exec: yes %
# % ccm_size: 1080 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euo pipefail
# Generate a 64-char hex secret suitable for Homarr SECRET_ENCRYPTION_KEY
openssl rand -hex 32
