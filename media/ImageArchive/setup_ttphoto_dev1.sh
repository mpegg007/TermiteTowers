#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/setup_ttphoto_dev1.sh:145 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: dc891414480f590c7692c6cf53b77042a767b22a %
#  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
#  %ccm_git_commit_count: 145 %
#  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: adding readme %
#  %ccm_git_modify_date: 2026-05-24 15:15:26 %
#  %ccm_git_file_last_modified: 2026-05-24 15:15:25 %
#  %ccm_git_file_name: setup_ttphoto_dev1.sh %
#  %ccm_git_path: media/ImageArchive/setup_ttphoto_dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1117 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % 
# %git_commit_history: unknown  unknown  unknown  % 
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
