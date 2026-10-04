#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: start-openwebui.sh:0 %
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
# % ccm_path: start-openwebui.sh %
# % ccm_blob_sha: 796f176f0dbe5c4d581101a430736c5c4fc1cdbc %
# % ccm_exec: yes %
# % ccm_size: 1359 %
# % ccm_tag:  %
# tt-ccm.header.end

# Wrapper: forward to moved script
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
TARGET="$SCRIPT_DIR/scripts/system/start-openwebui.sh"
if [[ -f "$TARGET" ]]; then
  exec "$TARGET" "$@"
else
  echo "Moved script not found: $TARGET" >&2
  exit 1
fi
#!/usr/bin/env bash
set -euxo pipefail

sudo docker rm -f openwebui-dev1 || true

sudo docker run -d \
  --name openwebui-dev1 \
  -e PORT=3000 \
  -p 3000:3000 \
  ghcr.io/open-webui/open-webui:main
