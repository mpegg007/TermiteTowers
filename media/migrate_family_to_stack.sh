#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 3828c269ae2fe4c06ba24b1dc09fba6573e34874 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 17:21:57 %
#  %ccm_git_file_last_modified: 2026-05-23 17:20:57 %
#  %ccm_git_file_name: migrate_family_to_stack.sh %
#  %ccm_git_path: media/migrate_family_to_stack.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1240 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# One-time migration: rename family/family_members/family_tag_authority
# to stacks/stack_members/stack_tag_authority in the live DB.
# Run on monolith as mpegg-adm (peer auth, local socket).
set -euo pipefail

echo "=== Migrating family → stack in ttphoto_dev1 ==="
psql -d ttphoto_dev1 <<'SQL'
SET ROLE ttphoto_dev1_owner;

-- Rename tables
ALTER TABLE families       RENAME TO stacks;
ALTER TABLE family_members RENAME TO stack_members;

-- Rename FK column
ALTER TABLE stack_members RENAME COLUMN family_id TO stack_id;

-- Drop old view; recreate with new name and column references
DROP VIEW IF EXISTS family_tag_authority;

CREATE OR REPLACE VIEW stack_tag_authority AS
SELECT DISTINCT ON (sm.stack_id, it.tag_key)
    sm.stack_id,
    it.tag_key,
    it.tag_value,
    i.id        AS source_image_id,
    i.path      AS source_path,
    i.file_date AS source_file_date
FROM stack_members sm
JOIN image_tags it ON it.image_id = sm.image_id
JOIN images     i  ON i.id        = sm.image_id
WHERE it.tag_key IN (SELECT tag_key FROM propagatable_tags)
  AND it.tag_value IS NOT NULL
  AND it.tag_value <> ''
ORDER BY sm.stack_id, it.tag_key, i.file_date DESC NULLS LAST;

RESET ROLE;
SQL
echo "Migration complete."
