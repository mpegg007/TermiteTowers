<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/nginx/README.md:147 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 03be1985db3500ad72fb2bd6a39266318a2f1b2c %
  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
  %ccm_git_commit_count: 147 %
  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: june bulk update %
  %ccm_git_modify_date: 2026-06-10 17:10:32 %
  %ccm_git_file_last_modified: 2026-06-10 17:10:32 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: infra/nginx/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 487 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!--
-->

# nginx (migrate to infra)

These configs are candidates to move into `../infra/nginx`.
For now, they remain here; tools and scripts should tolerate either path.

sudo certbot certonly \
  --manual \
  --preferred-challenges dns \
  --manual-auth-hook /home/mpegg-adm/source/TermiteTowers/infra/certbot/godaddy-auth-hook.sh \
  --manual-cleanup-hook /home/mpegg-adm/source/TermiteTowers/infra/certbot/godaddy-cleanup-hook.sh \
  --key-type ecdsa \
  -d MemoryLab.AnalAcres.ca

