/*--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: media/ImageArchive/create_v_tag_master.sql:146 %
--  %ccm_git_author: Matthew Pegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: d89dac27b9d6f7083043676a8db0c2a597921184 %
--  %ccm_git_commit_id: ff10418d79d5d337bca240bb7739df3da4f6892a %
--  %ccm_git_commit_count: 146 %
--  %ccm_git_commit_date: 2026-05-24 20:26:55 -0400 %
--  %ccm_git_commit_author: Matthew Pegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: track duplicate image locations, scrape from all files %
--  %ccm_git_modify_date: 2026-05-24 20:27:04 %
--  %ccm_git_file_last_modified: 2026-05-24 20:27:04 %
--  %ccm_git_file_name: create_v_tag_master.sql %
--  %ccm_git_path: media/ImageArchive/create_v_tag_master.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: utf-8 %
--  %ccm_git_file_eol: CRLF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 1437 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- v_tag_master
-- Mirrors the tag_master Excel export:
--   tag_master columns  — from tag_master table (NULL when tag not yet loaded)
--   stat columns        — always calculated live from image_tags / images
--
-- Usage:
--   SELECT * FROM v_tag_master WHERE propagatable IS NULL;   -- unclassified tags
--   SELECT * FROM v_tag_master ORDER BY image_count DESC;    -- most-used first

CREATE OR REPLACE VIEW v_tag_master AS
WITH agg AS (
    SELECT it.tag_key,
           COUNT(DISTINCT it.image_id)  AS image_count,
           COUNT(DISTINCT it.tag_value) AS distinct_values,
           STRING_AGG(DISTINCT i.archive_owner, ', '
                      ORDER BY i.archive_owner)  AS owners
    FROM image_tags it
    LEFT JOIN images i ON i.id = it.image_id
    GROUP BY it.tag_key
),
val_counts AS (
    SELECT tag_key, tag_value, COUNT(*) AS cnt
    FROM image_tags
    WHERE tag_value IS NOT NULL AND tag_value <> ''
    GROUP BY tag_key, tag_value
),
top_val AS (
    SELECT DISTINCT ON (tag_key) tag_key, tag_value AS most_common_value
    FROM val_counts
    ORDER BY tag_key, cnt DESC
)
SELECT
    a.tag_key,
    tm.propagatable,
    tm.include_in_report,
    tm.canonical_key,
    tm.description,
    tm.notes,
    a.image_count,
    a.distinct_values,
    a.owners,
    t.most_common_value
FROM agg a
LEFT JOIN tag_master tm ON tm.tag_key = a.tag_key
LEFT JOIN top_val   t   ON t.tag_key  = a.tag_key
ORDER BY a.tag_key;
