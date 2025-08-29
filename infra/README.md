<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-29 15:31:33 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: infra/README.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-29 15:31:33 %
% ccm_file_name: README.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: infra/README.md %
% ccm_blob_sha: 8dbb219763d3af03d2ac9cfd4f8313af171596ff %
% ccm_exec: no %
% ccm_size: 1117 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Infra

Operational infrastructure configs and deployment assets.

Proposed layout:
- nginx/: vhost and site configs (currently in ../nginx)
- docker/: compose files and container configs (currently in ../docker)

Next step (optional): relocate `nginx/` and `docker/` here and leave root-level shims for compatibility.
