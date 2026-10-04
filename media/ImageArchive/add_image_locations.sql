/*--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: media/ImageArchive/add_image_locations.sql:146 %
--  %ccm_git_author: Matthew Pegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: 4152bf33d4d45cb20c21e2317ed8d3ae607c157d %
--  %ccm_git_commit_id: ff10418d79d5d337bca240bb7739df3da4f6892a %
--  %ccm_git_commit_count: 146 %
--  %ccm_git_commit_date: 2026-05-24 20:26:55 -0400 %
--  %ccm_git_commit_author: Matthew Pegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: track duplicate image locations, scrape from all files %
--  %ccm_git_modify_date: 2026-05-24 20:26:59 %
--  %ccm_git_file_last_modified: 2026-05-24 20:26:59 %
--  %ccm_git_file_name: add_image_locations.sql %
--  %ccm_git_path: media/ImageArchive/add_image_locations.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: us-ascii %
--  %ccm_git_file_eol: CRLF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 759 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- add_image_locations.sql
-- Migration: create image_locations table to track every path/filename
-- where a given image hash has been found.
-- Run as: psql -d ttphoto_dev1 -f /tmp/add_image_locations.sql

SET ROLE ttphoto_dev1_owner;

CREATE TABLE IF NOT EXISTS image_locations (
    id        SERIAL      PRIMARY KEY,
    image_id  INTEGER     NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    path      TEXT        NOT NULL,
    file_name TEXT        NOT NULL,
    folder    TEXT,
    found_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (image_id, path)
);

CREATE INDEX IF NOT EXISTS image_locations_image_id_idx ON image_locations(image_id);
CREATE INDEX IF NOT EXISTS image_locations_file_name_idx ON image_locations(file_name);

RESET ROLE;
