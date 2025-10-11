<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: wiki/databases.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
🧠 PostgreSQL Database Strategy — Termite Towers
🎯 Purpose
Establish a clear, traceable PostgreSQL structure for service isolation, environment promotion, and archival hygiene. This replaces legacy kea usage with a structured multi-DB approach.

🗂 Database Layout
Database	Purpose
kea	Legacy — used by Kea DHCP; slated for migration
ttdb-dev1	Development — all new services and schemas start here
ttdb-prd1	Production — promoted from ttdb-dev1 after validation
ttdb-arc1	Archive — long-term storage of historical or retired data
🔁 Promotion Workflow
Develop in ttdb-dev1

New schemas (e.g. powerdns, havoc, inventory) created here

Full forensic traceability: schema ownership, role privileges, audit triggers

Promote to ttdb-prd1

After validation, schema is exported and rehydrated in ttdb-prd1

Roles and privileges re-applied with production constraints

Archive to ttdb-arc1

Retired or historical data moved here

Read-only roles enforced, indexing optimized for cold storage

🔐 Role Strategy
Each service gets a dedicated role:

kea, powerdns, havoc, etc.

Roles are scoped to their schema only

Passwords managed via secrets vault or .pgpass

🧪 Migration Plan for Kea
Create kea schema inside ttdb-dev1

Export data from legacy kea DB

Re-import into ttdb-dev1.kea

Validate backend hooks and schema alignment

Promote to ttdb-prd1.kea once confirmed

🧼 Operational Hygiene
No cross-schema access

No shared roles across databases

All schema changes tracked via Git + audit triggers

Archive DB (ttdb-arc1) purged quarterly of expired data
