/*--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: media/ImageArchive/add_tag_history_recorded_at.sql:146 %
--  %ccm_git_author: Matthew Pegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: ea1d1d09a9de88fe74f4dfbc9450e0b919e41f67 %
--  %ccm_git_commit_id: ff10418d79d5d337bca240bb7739df3da4f6892a %
--  %ccm_git_commit_count: 146 %
--  %ccm_git_commit_date: 2026-05-24 20:26:55 -0400 %
--  %ccm_git_commit_author: Matthew Pegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: track duplicate image locations, scrape from all files %
--  %ccm_git_modify_date: 2026-05-24 20:27:02 %
--  %ccm_git_file_last_modified: 2026-05-24 20:27:01 %
--  %ccm_git_file_name: add_tag_history_recorded_at.sql %
--  %ccm_git_path: media/ImageArchive/add_tag_history_recorded_at.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: utf-8 %
--  %ccm_git_file_eol: CRLF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 604 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- add_tag_history_recorded_at.sql
-- Migration: add recorded_at column to tag_history.
-- recorded_at = File:FileModifyDate from the source file — the best available
-- proxy for when the tags were last written to disk.  This is distinct from
-- snapshot_ts (the photo's capture date) and from NOW() (ingestion time).
-- Run as: psql -d ttphoto_dev1 -f /tmp/add_tag_history_recorded_at.sql

SET ROLE ttphoto_dev1_owner;

ALTER TABLE tag_history
    ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS tag_history_recorded_at_idx
    ON tag_history(recorded_at);

RESET ROLE;
