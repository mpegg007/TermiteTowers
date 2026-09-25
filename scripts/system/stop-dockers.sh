#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/system/stop-dockers.sh:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c739a83f3bd2ebbde6db36cb35777c0d85c18dec %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:23 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:23 %
#  %ccm_git_file_name: stop-dockers.sh %
#  %ccm_git_path: scripts/system/stop-dockers.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 504 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  comment cleanup  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
echo "Stopping Docker containers..."
docker stop nextcloud-dev1 mealie-dev1 openwebui-dev1 snipeit-dev1 snipeit-db-dev1 mkdocs_app-dev1 esphome-dev1 uptime-kuma-dev1 watchyourlan-dev1 powerdns-dev1 powerdns-admin-dev1 powerdns-admin-db-dev1 powerdns-db-dev1 lobechat-dev1 dozzle-dev1 dbgate-dev1 pihole-dev1 searxng-dev1 prometheus-dev1 homarr-dev1 llm-server-dev1
echo "Done."
