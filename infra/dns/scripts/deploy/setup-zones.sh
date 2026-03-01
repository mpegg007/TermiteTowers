#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dns/scripts/deploy/setup-zones.sh:130 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: e2133fd2bc86ff6d1a7da16067339b795d2a43b7 %
#  %ccm_git_commit_id: 3395da0009f399bd9abd836085b72ec8a4d7f2f3 %
#  %ccm_git_commit_count: 130 %
#  %ccm_git_commit_date: 2026-02-07 15:49:15 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feb2026.1 %
#  %ccm_git_modify_date: 2026-02-07 15:49:19 %
#  %ccm_git_file_last_modified: 2026-02-07 15:49:19 %
#  %ccm_git_file_name: setup-zones.sh %
#  %ccm_git_path: infra/dns/scripts/deploy/setup-zones.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3564 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# Setup PowerDNS Zones for TermiteTowers
# Creates authoritative zones: .local, tt.omp, aa.omp
#
# Usage:
#   ./setup-zones.sh              # Create all zones with example records
#   ./setup-zones.sh --zones-only # Create zones only, no records
#
# Manual record management:
#   ./add-dns-record.sh <zone> <name> <ip>

set -e

API_KEY="${PDNS_API_KEY:-changeme123}"
API_URL="${PDNS_API_URL:-http://localhost:3021/api/v1/servers/localhost}"

echo "Setting up PowerDNS zones..."
echo "API URL: ${API_URL}"

# Function to create a zone (handles existing zones gracefully)
create_zone() {
    local zone_name=$1
    local nameserver=$2
    
    echo -n "Creating zone: $zone_name ... "
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/zones" \
      -H "X-API-Key: ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"${zone_name}.\",
        \"kind\": \"Native\",
        \"masters\": [],
        \"nameservers\": [\"${nameserver}.\"]
      }")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "201" ]]; then
        echo "✓ Created"
        return 0
    elif [[ "$http_code" == "409" ]]; then
        echo "⊘ Already exists"
        return 0
    else
        echo "✗ Failed (HTTP $http_code)"
        echo "$body" | jq -r '.error // .' || echo "$body"
        return 1
    fi
}

# Function to add an A record
add_a_record() {
    local zone=$1
    local name=$2
    local ip=$3
    
    echo -n "  Adding A record: ${name}.${zone} → ${ip} ... "
    
    response=$(curl -s -w "\n%{http_code}" -X PATCH "${API_URL}/zones/${zone}." \
      -H "X-API-Key: ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{
        \"rrsets\": [{
          \"name\": \"${name}.${zone}.\",
          \"type\": \"A\",
          \"ttl\": 300,
          \"changetype\": \"REPLACE\",
          \"records\": [{
            \"content\": \"${ip}\",
            \"disabled\": false
          }]
        }]
      }")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "204" ]]; then
        echo "✓"
        return 0
    else
        echo "✗ (HTTP $http_code)"
        return 1
    fi
}

# Create zones
echo ""
echo "=== Creating Zones ==="
create_zone "local" "ns1.local"
create_zone "tt.omp" "ns1.tt.omp"
create_zone "aa.omp" "ns1.aa.omp"

# Exit if only creating zones
if [[ "$1" == "--zones-only" ]]; then
    echo ""
    echo "✓ Zones created (no records added)"
    exit 0
fi

echo ""
echo "=== Adding Example Records ==="

# Add example records for .local
echo ".local zone:"
add_a_record "local" "ns1" "192.168.1.10"
add_a_record "local" "dns" "192.168.1.10"
add_a_record "local" "esp32-node06" "192.168.1.106"
add_a_record "local" "test" "192.168.1.100"

# Add example records for tt.omp
echo ""
echo "tt.omp zone:"
add_a_record "tt.omp" "ns1" "192.168.1.10"
add_a_record "tt.omp" "dns" "192.168.1.10"
add_a_record "tt.omp" "router" "192.168.1.1"
add_a_record "tt.omp" "server" "192.168.1.10"

# Add example records for aa.omp
echo ""
echo "aa.omp zone:"
add_a_record "aa.omp" "ns1" "192.168.1.10"
add_a_record "aa.omp" "dns" "192.168.1.10"

echo ""
echo "✓ All zones configured!"
echo ""
echo "Test with:"
echo "  dig @192.168.1.10 esp32-node06.local"
echo "  dig @192.168.1.10 router.tt.omp"
echo "  dig @192.168.1.10 google.com  # Should forward to internet"
echo ""
echo "View zones at: http://localhost:3020 (PowerDNS Admin)"
echo "  Username: admin"
echo "  Password: admin"
