#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dns/godaddy-ddns.sh@200 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 73b3af3e865a6df7da61b0ccb2e8556e0b48da02 %
#  %ccm_git_commit_id: 07c638fcfb4804b40c226db94358725a8b6ef636 %
#  %ccm_git_commit_count: 200 %
#  %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: zoo.261109 %
#  %ccm_git_modify_date: 2026-11-09 10:16:58 %
#  %ccm_git_file_last_modified: 2026-11-08 14:23:49 %
#  %ccm_git_file_name: godaddy-ddns.sh %
#  %ccm_git_path: infra/dns/godaddy-ddns.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 3920 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# GoDaddy Dynamic DNS updater
# Checks current public IP and updates GoDaddy A records if changed.
#
# Credentials sourced from /etc/letsencrypt/godaddy.env:
#   GODADDY_API_KEY
#   GODADDY_API_SECRET
#
# Configure DDNS_DOMAINS below — space-separated list of "domain:name" pairs.
# Use "@" for the root record, "www" for www, etc.
#
# Examples:
#   "justanotherhuman.ca:@"   -> justanotherhuman.ca A record
#   "justanotherhuman.ca:www" -> www.justanotherhuman.ca A record

set -euo pipefail

DDNS_DOMAINS=(
    "justanotherhuman.ca:@"
    "analacres.ca:memorylab"
    # analacres.ca service family (nginx listener 3261 on monolith).
    # Each name needs its own per-host certificate, issued with the DNS-01
    # GoDaddy hooks in infra/certbot/ — see infra/nginx/README.md.
    # auth.analacres.ca is deliberately absent: it belongs to the Authelia
    # portal, which is Phase 2 (wiki/runbook-authelia.md).
    "analacres.ca:wordbank"
    "analacres.ca:soundbank"
    # Nextcloud, published under a neutral name. The public hostname is
    # filebank.analacres.ca; the container, dataset and database keep the
    # name "nextcloud". nextcloud.termitetowers.ca is a redirect only.
    "analacres.ca:filebank"
)

ENV_FILE="/etc/letsencrypt/godaddy.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

: "${GODADDY_API_KEY:?GODADDY_API_KEY not set}"
: "${GODADDY_API_SECRET:?GODADDY_API_SECRET not set}"

log() {
    echo "[godaddy-ddns] $(date '+%Y-%m-%d %H:%M:%S') $*"
    logger -t godaddy-ddns "$*"
}

# Get current public IP
CURRENT_IP=$(curl -s --max-time 10 https://api.ipify.org)
if [[ -z "$CURRENT_IP" ]]; then
    log "ERROR: Could not determine public IP"
    exit 1
fi

for ENTRY in "${DDNS_DOMAINS[@]}"; do
    DOMAIN="${ENTRY%%:*}"
    NAME="${ENTRY##*:}"

    # Get current GoDaddy A record value
    GODADDY_IP=$(curl -s --max-time 10 \
        "https://api.godaddy.com/v1/domains/${DOMAIN}/records/A/${NAME}" \
        -H "Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}" \
        -H "Content-Type: application/json" \
        | grep -o '"data":"[^"]*"' | head -1 | cut -d'"' -f4 || true)

    if [[ "$CURRENT_IP" == "$GODADDY_IP" ]]; then
        log "OK: ${NAME}.${DOMAIN} already points to ${CURRENT_IP}"
    else
        log "UPDATE: ${NAME}.${DOMAIN} ${GODADDY_IP} -> ${CURRENT_IP}"
        curl -s -X PUT \
            "https://api.godaddy.com/v1/domains/${DOMAIN}/records/A/${NAME}" \
            -H "Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}" \
            -H "Content-Type: application/json" \
            -d "[{\"data\": \"${CURRENT_IP}\", \"ttl\": 600}]"
        log "DONE: ${NAME}.${DOMAIN} updated to ${CURRENT_IP}"
    fi
done
