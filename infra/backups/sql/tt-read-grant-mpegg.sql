/*-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: infra/backups/sql/tt-read-grant-mpegg.sql@218 %
--  %ccm_git_author: mpegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: 03900572193635f0c772eefb754212d4749e9102 %
--  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
--  %ccm_git_commit_count: 218 %
--  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
--  %ccm_git_commit_author: mpegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: changes 261113 %
--  %ccm_git_modify_date: 2026-11-13 14:50:44 %
--  %ccm_git_file_last_modified: 2026-11-13 14:49:36 %
--  %ccm_git_file_name: tt-read-grant-mpegg.sql %
--  %ccm_git_path: infra/backups/sql/tt-read-grant-mpegg.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: us-ascii %
--  %ccm_git_file_eol: LF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 4588 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- ---------------------------------------------------------------------------
-- tt-backup :: read-only grant so the user-level backup job can dump every
-- schema in ttdb_dev1 without a password, a service account or root.
--
-- WHY THIS EXISTS
--   infra/backups/scripts/backup-db-user.sh runs as the invoking user
--   (mpegg-adm) over the local unix socket using peer auth. That works for
--   ttphoto_dev1 because mpegg-adm holds ttphoto_dev1_owner, but NOT for
--   ttdb_dev1: mpegg-adm can read kea TABLES yet not its SEQUENCES, so
--   pg_dump dies at
--       permission denied for sequence dhcp4_audit_id_seq
--   and several other schemas grant no USAGE at all. The dump is therefore
--   either impossible or silently partial - which is the failure this file
--   prevents.
--
--   pg_read_all_data is a predefined PostgreSQL role: it grants SELECT on
--   every table, view and sequence in every database, and nothing else. It
--   cannot write, create, alter or drop. It is the same posture the
--   "tt_backup" service account already has (/etc/tt-backup), so this widens
--   no privilege that a backup identity should not hold.
--
-- TRADE-OFF, STATED PLAINLY
--   backup-tthealth.sh runs as "tt-backup", which holds ONLY the age
--   recipient and cannot unwrap a DEK. A job running as mpegg-adm CAN unlock
--   the keyring, so the "the backup identity cannot decrypt what it protects"
--   property does NOT hold for the two general-tier jobs. That is accepted
--   deliberately: the alternative is a root-only install, and these two
--   databases had no backup at all for that reason.
--
-- RUN ONCE, as a superuser (needs a password, so the human runs it):
--   sudo -u postgres psql -d ttdb_dev1 -f infra/backups/sql/tt-read-grant-mpegg.sql
--
-- Idempotent: safe to re-run.
-- ---------------------------------------------------------------------------

-- Without this, psql reports exit 0 even when a statement fails, so a broken
-- verification query below would look like a clean run.
\set ON_ERROR_STOP on

GRANT pg_read_all_data TO "mpegg-adm";

-- Verification: every one of these must be true, and the count of unreadable
-- sequences must be 0. A dump that cannot read a sequence FAILS rather than
-- silently omitting it, but proving it here avoids discovering that at 03:50.
SELECT 'schema_usage' AS check,
       string_agg(n.nspname || '=' || has_schema_privilege('mpegg-adm', n.oid, 'USAGE'),
                  ' ' ORDER BY n.nspname) AS result
FROM pg_namespace n
WHERE n.nspname NOT LIKE 'pg\_%'
  AND n.nspname <> 'information_schema';

-- has_table_privilege, not has_sequence_privilege. The planner is free to
-- evaluate a WHERE-clause function on rows whose relkind filter has not been
-- applied yet (a wrapping subquery is pulled up and does not help), so
-- has_sequence_privilege() was being handed a pg_class row that is not a
-- sequence and aborted the file with
--     ERROR: "pg_toast_20509" is not a sequence
-- that is a verification failure wearing a grant failure's clothes.
-- has_table_privilege() accepts any relation, including a sequence, and still
-- tests the SELECT privilege that pg_dump needs.
SELECT 'unreadable_sequences' AS check,
       count(*) AS result
FROM (
    SELECT c.oid
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'S'
      AND n.nspname NOT LIKE 'pg\_%'
      AND n.nspname <> 'information_schema'
) seqs
WHERE NOT has_table_privilege('mpegg-adm', seqs.oid, 'SELECT');
