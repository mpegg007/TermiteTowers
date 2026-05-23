#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a2dd3d82c342a746cecc8f5a5b24c323a4b732f7 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-05-23 17:21:53 %
#  %ccm_git_file_last_modified: 2026-05-23 17:20:40 %
#  %ccm_git_file_name: init_schema.sh %
#  %ccm_git_path: media/init_schema.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 2245 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Run on monolith as mpegg-adm (peer auth, local socket).
# Creates the ttphoto_dev1 schema owned by ttphoto_dev1_owner so that
# default privileges grant ttphoto_dev1_app DML access automatically.
set -euo pipefail

echo "=== Initialising ttphoto_dev1 schema ==="
psql -d ttphoto_dev1 <<'SQL'
SET ROLE ttphoto_dev1_owner;

CREATE TABLE IF NOT EXISTS images (
    id            SERIAL PRIMARY KEY,
    path          TEXT UNIQUE NOT NULL,
    image_hash    TEXT,
    file_name     TEXT,
    file_type     TEXT,
    folder        TEXT,
    archive_owner TEXT,
    file_date     TEXT,
    file_bytes    BIGINT,
    scan_name     TEXT,
    sidecar_path  TEXT,
    loaded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS image_tags (
    image_id  INTEGER REFERENCES images(id) ON DELETE CASCADE,
    tag_key   TEXT NOT NULL,
    tag_value TEXT,
    PRIMARY KEY (image_id, tag_key)
);

CREATE TABLE IF NOT EXISTS tag_history (
    id          SERIAL PRIMARY KEY,
    image_id    INTEGER REFERENCES images(id) ON DELETE CASCADE,
    snapshot_ts TEXT,
    change_type TEXT,
    tag_key     TEXT NOT NULL,
    tag_value   TEXT,
    UNIQUE (image_id, snapshot_ts, change_type, tag_key)
);

CREATE TABLE IF NOT EXISTS stacks (
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stack_members (
    stack_id  INTEGER REFERENCES stacks(id) ON DELETE CASCADE,
    image_id  INTEGER REFERENCES images(id) ON DELETE CASCADE,
    PRIMARY KEY (stack_id, image_id)
);

CREATE TABLE IF NOT EXISTS propagatable_tags (
    tag_key   TEXT PRIMARY KEY,
    tag_group TEXT,
    notes     TEXT
);

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
echo "Schema ready."
