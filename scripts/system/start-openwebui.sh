#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/start-openwebui.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:34 %
# % ccm_file_name: start-openwebui.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/start-openwebui.sh %
# % ccm_blob_sha: d51db253ac14985a45af5fe05c190478a1e8807a %
# % ccm_exec: yes %
# % ccm_size: 1082 %
# % ccm_tag:  %
# tt-ccm.header.end

set -euxo pipefail

sudo docker rm -f openwebui-dev1 || true

sudo docker run -d \
  --name openwebui-dev1 \
  -e PORT=3000 \
  -p 3000:3000 \
  ghcr.io/open-webui/open-webui:main
