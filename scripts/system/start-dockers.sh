#!/bin/bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/system/start-dockers.sh:158 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 93d3e3f85e6d33312f5fe0bf42d9c0663db26f5f %
#  %ccm_git_commit_id: d7e19382f49384e00dc61fb86a10a9255583a0c8 %
#  %ccm_git_commit_count: 158 %
#  %ccm_git_commit_date: 2026-09-25 21:05:38 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: chore(homarr): retire Homarr - configured but never used day to day %
#  %ccm_git_modify_date: 2026-09-25 21:05:38 %
#  %ccm_git_file_last_modified: 2026-09-25 21:04:24 %
#  %ccm_git_file_name: start-dockers.sh %
#  %ccm_git_path: scripts/system/start-dockers.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1706 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  comment cleanup  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
# %git_commit_history: unknown  unknown  unknown  % 
# %git_commit_history: 2026-02-07 mpegg  comment cleanup  % 
# %git_commit_history: 2026-02-07 mpegg  feb2026  % 
echo "Starting Docker containers..."
# Databases first
docker start snipeit-db-dev1 powerdns-admin-db-dev1 powerdns-db-dev1
# Everything else
docker start nextcloud-dev1 mealie-dev1 openwebui-dev1 snipeit-dev1 mkdocs_app-dev1 esphome-dev1 uptime-kuma-dev1 watchyourlan-dev1 powerdns-dev1 powerdns-admin-dev1 lobechat-dev1 dozzle-dev1 dbgate-dev1 pihole-dev1 searxng-dev1 prometheus-dev1 llm-server-dev1
echo "Done."
