#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-31 14:14:22 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/gen-secret-hex.sh:66 %
# % ccm_commit_id: 3d871d06b965d4535465831e23237bb71288ef20 %
# % ccm_commit_count: 66 %
# % ccm_commit_message: adding homarr as home.termitetowers.ca %
# % ccm_commit_author: mpegg %
# % ccm_commit_email: mpegg@hotmail.com %
# % ccm_commit_date: 2025-08-31 14:14:22 -0400 %
# % ccm_file_last_modified: 2025-08-31 14:14:22 %
# % ccm_file_name: gen-secret-hex.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/gen-secret-hex.sh %
# % ccm_blob_sha: d9eefcfed467ee9c9ccb3ddfe3dce25dab3a3603 %
# % ccm_exec: no %
# % ccm_size: 998 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euo pipefail
# Generate a 64-char hex secret suitable for Homarr SECRET_ENCRYPTION_KEY
openssl rand -hex 32
