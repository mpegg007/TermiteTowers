#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/setup-dhcp-history-db.sh:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 47efaac387ab0adab1c94dce3fda150bc16d9cd7 %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:20 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:20 %
#  %ccm_git_file_name: setup-dhcp-history-db.sh %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/setup-dhcp-history-db.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3784 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2025-11-30 mpegg  cleanup  % 
# %git_commit_history: november changes % 
# %git_commit_history: dhcp logging % 

# Setup script for DHCP History Database
# Creates dedicated user, schema, and permissions in ttdb_dev1

set -euo pipefail

# Configuration
DB_NAME="ttdb_dev1"
SCHEMA_NAME="dhcp_history"
DB_USER="dhcp_history"
DB_PASSWORD="termitetowers-db"

echo "=========================================="
echo "DHCP History Database Setup"
echo "=========================================="
echo "Database: $DB_NAME"
echo "Schema:   $SCHEMA_NAME"
echo "User:     $DB_USER"
echo "=========================================="
echo ""

# Function to run SQL as postgres user
run_sql() {
    sudo -u postgres psql -d "$DB_NAME" -c "$1"
}

# Check if database exists
echo "📋 Checking database $DB_NAME..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "❌ Database $DB_NAME does not exist!"
    echo "   Please create it first or run this against an existing database."
    exit 1
fi
echo "✅ Database exists"

# Create role if it doesn't exist
echo ""
echo "👤 Creating role $DB_USER..."
sudo -u postgres psql -d "$DB_NAME" <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'Role $DB_USER created';
    ELSE
        RAISE NOTICE 'Role $DB_USER already exists';
    END IF;
END
\$\$;
EOF
echo "✅ Role ready"

# Grant database connection and schema creation
echo ""
echo "🔌 Granting database connection..."
run_sql "GRANT CONNECT ON DATABASE $DB_NAME TO $DB_USER;"
run_sql "GRANT CREATE ON DATABASE $DB_NAME TO $DB_USER;"
echo "✅ Connection granted"

# Create schema
echo ""
echo "📦 Creating schema $SCHEMA_NAME..."
run_sql "CREATE SCHEMA IF NOT EXISTS $SCHEMA_NAME AUTHORIZATION $DB_USER;"
echo "✅ Schema ready"

# Set search path for user
echo ""
echo "🔍 Setting search path..."
run_sql "ALTER ROLE $DB_USER SET search_path TO $SCHEMA_NAME, public;"
echo "✅ Search path configured"

# Grant schema usage
echo ""
echo "🔐 Granting schema permissions..."
run_sql "GRANT USAGE ON SCHEMA $SCHEMA_NAME TO $DB_USER;"
run_sql "GRANT CREATE ON SCHEMA $SCHEMA_NAME TO $DB_USER;"
run_sql "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA $SCHEMA_NAME TO $DB_USER;"
run_sql "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA $SCHEMA_NAME TO $DB_USER;"
echo "✅ Permissions granted"

# Set default privileges for future objects
echo ""
echo "🔮 Setting default privileges..."
run_sql "ALTER DEFAULT PRIVILEGES IN SCHEMA $SCHEMA_NAME GRANT ALL ON TABLES TO $DB_USER;"
run_sql "ALTER DEFAULT PRIVILEGES IN SCHEMA $SCHEMA_NAME GRANT ALL ON SEQUENCES TO $DB_USER;"
echo "✅ Default privileges set"

# Summary
echo ""
echo "=========================================="
echo "✅ DHCP History Database Setup Complete!"
echo "=========================================="
echo ""
echo "📊 Database Info:"
echo "   Database:   $DB_NAME"
echo "   Schema:     $SCHEMA_NAME"
echo "   Owner:      $DB_USER"
echo ""
echo "🔑 Connection Details:"
echo "   Host:       localhost"
echo "   Port:       5432"
echo "   Database:   $DB_NAME"
echo "   User:       $DB_USER"
echo "   Password:   $DB_PASSWORD"
echo ""
echo "📝 Next Steps:"
echo "   1. Initialize schema:"
echo "      sudo python3 parse-kea-logs.py --init-schema"
echo ""
echo "   2. Test parsing (dry run):"
echo "      sudo python3 parse-kea-logs.py --dry-run"
echo ""
echo "   3. Run initial full parse:"
echo "      sudo python3 parse-kea-logs.py --full-parse"
echo ""
echo "   4. Set up cron job for continuous monitoring"
echo "=========================================="
