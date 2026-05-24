/*--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: media/ImageArchive/add_file_backups.sql:145 %
--  %ccm_git_author: Matthew Pegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: 8e7be22a5dde6ac98734793d00e5ec08bce20bde %
--  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
--  %ccm_git_commit_count: 145 %
--  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
--  %ccm_git_commit_author: Matthew Pegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: adding readme %
--  %ccm_git_modify_date: 2026-05-24 15:15:01 %
--  %ccm_git_file_last_modified: 2026-05-24 15:15:01 %
--  %ccm_git_file_name: add_file_backups.sql %
--  %ccm_git_path: media/ImageArchive/add_file_backups.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: us-ascii %
--  %ccm_git_file_eol: CRLF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 621 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
/*-- %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % */
-- add_file_backups.sql
-- Migration: add file_backups table to ttphoto_dev1 schema.
-- Run: psql -d ttphoto_dev1 -f add_file_backups.sql

SET ROLE ttphoto_dev1_owner;

CREATE TABLE IF NOT EXISTS file_backups (
    image_id     INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    destination  TEXT    NOT NULL,   -- 'jottacloud'; extend for future targets
    remote_path  TEXT,
    backed_up_at TIMESTAMPTZ,
    status       TEXT,               -- 'success', 'failed'
    image_hash   TEXT,               -- hash at time of backup
    error_msg    TEXT,
    PRIMARY KEY (image_id, destination)
);

RESET ROLE;
