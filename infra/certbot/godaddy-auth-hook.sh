#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/certbot/godaddy-auth-hook.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: bd3b2a1ba6fec702ad1bc86732b57e4df0d633c6 %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:31 %
#  %ccm_git_file_last_modified: 2026-05-16 17:01:50 %
#  %ccm_git_file_name: godaddy-auth-hook.sh %
#  %ccm_git_path: infra/certbot/godaddy-auth-hook.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 2849 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# GoDaddy DNS-01 auth hook for certbot
# Called by certbot to create the ACME challenge TXT record.
#
# Required environment variables (set in /etc/letsencrypt/godaddy.env):
#   GODADDY_API_KEY
#   GODADDY_API_SECRET
#
# certbot sets these automatically:
#   CERTBOT_DOMAIN   - the domain being validated (e.g. termitetowers.ca)
#   CERTBOT_VALIDATION - the TXT record value to set

set -euo pipefail

ENV_FILE="/etc/letsencrypt/godaddy.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

: "${GODADDY_API_KEY:?GODADDY_API_KEY not set}"
: "${GODADDY_API_SECRET:?GODADDY_API_SECRET not set}"
: "${CERTBOT_DOMAIN:?CERTBOT_DOMAIN not set}"
: "${CERTBOT_VALIDATION:?CERTBOT_VALIDATION not set}"

# Strip leading wildcard if present
DOMAIN="${CERTBOT_DOMAIN#\*.}"

# Extract the registrar base domain (last two labels, e.g. justanotherhuman.ca from www.justanotherhuman.ca)
BASE_DOMAIN=$(echo "$DOMAIN" | awk -F. '{print $(NF-1)"."$NF}')

# Build the TXT record name relative to the base domain
if [[ "$DOMAIN" == "$BASE_DOMAIN" ]]; then
    RECORD_NAME="_acme-challenge"
else
    SUB="${DOMAIN%.$BASE_DOMAIN}"
    RECORD_NAME="_acme-challenge.${SUB}"
fi

echo "[godaddy-auth-hook] Setting TXT record ${RECORD_NAME}.${BASE_DOMAIN} = ${CERTBOT_VALIDATION}"

# Fetch existing TXT records for this record name to avoid overwriting a previous hook call
# (certbot calls this hook once per domain when multiple SANs share the same record name)
EXISTING=$(curl -s \
    "https://api.godaddy.com/v1/domains/${BASE_DOMAIN}/records/TXT/${RECORD_NAME}" \
    -H "Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}" \
    -H "Content-Type: application/json")

# Build new records array: keep existing non-placeholder entries, append the new value
NEW_RECORD="{\"data\": \"${CERTBOT_VALIDATION}\", \"ttl\": 600}"

if echo "$EXISTING" | grep -q '"data"' && ! echo "$EXISTING" | grep -q '"removed"'; then
    # Extract existing data values and build a combined array
    EXISTING_ENTRIES=$(echo "$EXISTING" | grep -o '"data":"[^"]*"' | sed 's/"data":"\([^"]*\)"/{"data": "\1", "ttl": 600}/' | tr '\n' ',')
    PAYLOAD="[${EXISTING_ENTRIES}${NEW_RECORD}]"
else
    PAYLOAD="[${NEW_RECORD}]"
fi

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    "https://api.godaddy.com/v1/domains/${BASE_DOMAIN}/records/TXT/${RECORD_NAME}" \
    -H "Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [[ "$HTTP_CODE" != "200" ]]; then
    echo "[godaddy-auth-hook] ERROR: GoDaddy API returned HTTP $HTTP_CODE: $BODY" >&2
    exit 1
fi

echo "[godaddy-auth-hook] Waiting 120 seconds for DNS propagation..."
sleep 120
echo "[godaddy-auth-hook] Done."
