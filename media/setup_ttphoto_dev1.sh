#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/setup_ttphoto_dev1.sh:147 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 405714b65d4d84a90900cf5a12a3a4cf6e1094bf %
#  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
#  %ccm_git_commit_count: 147 %
#  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: june bulk update %
#  %ccm_git_modify_date: 2026-06-10 17:10:32 %
#  %ccm_git_file_last_modified: 2026-05-23 16:30:29 %
#  %ccm_git_file_name: setup_ttphoto_dev1.sh %
#  %ccm_git_path: media/setup_ttphoto_dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1063 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
set -euo pipefail

echo "=== Creating roles and database ==="
sudo -u postgres psql <<SQL
CREATE ROLE ttphoto_dev1_owner NOLOGIN;
CREATE ROLE ttphoto_dev1_app WITH LOGIN;
CREATE DATABASE ttphoto_dev1 OWNER ttphoto_dev1_owner;
GRANT CONNECT ON DATABASE ttphoto_dev1 TO ttphoto_dev1_app;
GRANT CONNECT ON DATABASE ttphoto_dev1 TO "mpegg-adm";
GRANT ttphoto_dev1_owner TO "mpegg-adm";
SQL

echo "=== Setting default privileges inside ttphoto_dev1 ==="
sudo -u postgres psql -d ttphoto_dev1 <<SQL
ALTER DEFAULT PRIVILEGES FOR ROLE ttphoto_dev1_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ttphoto_dev1_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ttphoto_dev1_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO ttphoto_dev1_app;
SQL

echo ""
echo "=== Set the app role password (type it now — it will not be logged) ==="
sudo -u postgres psql -c "\password ttphoto_dev1_app"

echo ""
echo "Done. Update media/.env with:"
echo "  PG_DSN=postgres://ttphoto_dev1_app:<password>@192.168.4.10:5432/ttphoto_dev1"
