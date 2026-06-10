#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/certbot/godaddy-cleanup-hook.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 07fe688d750a472dfae4d8fbe4db8de04752bb00 %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-05-16 17:01:19 %
#  %ccm_git_file_name: godaddy-cleanup-hook.sh %
#  %ccm_git_path: infra/certbot/godaddy-cleanup-hook.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1459 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# GoDaddy DNS-01 cleanup hook for certbot
# Called by certbot to remove the ACME challenge TXT record after validation.
#
# Required environment variables (set in /etc/letsencrypt/godaddy.env):
#   GODADDY_API_KEY
#   GODADDY_API_SECRET
#
# certbot sets these automatically:
#   CERTBOT_DOMAIN   - the domain being validated (e.g. termitetowers.ca)

set -euo pipefail

ENV_FILE="/etc/letsencrypt/godaddy.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

: "${GODADDY_API_KEY:?GODADDY_API_KEY not set}"
: "${GODADDY_API_SECRET:?GODADDY_API_SECRET not set}"
: "${CERTBOT_DOMAIN:?CERTBOT_DOMAIN not set}"

# Strip leading wildcard if present
DOMAIN="${CERTBOT_DOMAIN#\*.}"

# Extract the registrar base domain (last two labels)
BASE_DOMAIN=$(echo "$DOMAIN" | awk -F. '{print $(NF-1)"."$NF}')

# Build the TXT record name relative to the base domain
if [[ "$DOMAIN" == "$BASE_DOMAIN" ]]; then
    RECORD_NAME="_acme-challenge"
else
    SUB="${DOMAIN%.$BASE_DOMAIN}"
    RECORD_NAME="_acme-challenge.${SUB}"
fi

echo "[godaddy-cleanup-hook] Removing TXT record ${RECORD_NAME}.${BASE_DOMAIN}"

curl -s -X PUT \
    "https://api.godaddy.com/v1/domains/${BASE_DOMAIN}/records/TXT/${RECORD_NAME}" \
    -H "Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}" \
    -H "Content-Type: application/json" \
    -d '[{"data": "removed", "ttl": 600}]'

echo ""
echo "[godaddy-cleanup-hook] Done."
