#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/setup_ttphoto_dev1.sh:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 0c3fe416229dc65f64c073b41c0fc0f50bc86317 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-19 14:49:00 %
#  %ccm_git_file_name: setup_ttphoto_dev1.sh %
#  %ccm_git_path: media/ImageArchive/setup_ttphoto_dev1.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1184 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  adding readme  % 
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
