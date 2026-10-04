/*-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: infra/backups/sql/tt_backup-role.sql:167 %
--  %ccm_git_author: mpegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: 4b7ba50085b710250e56d24d7cbffaa6d39c2684 %
--  %ccm_git_commit_id: af3b4e614eaf7f1e2342aedb19c1c31089a044fd %
--  %ccm_git_commit_count: 167 %
--  %ccm_git_commit_date: 2026-10-03 17:41:25 -0400 %
--  %ccm_git_commit_author: mpegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: backup scripts %
--  %ccm_git_modify_date: 2026-10-03 17:41:25 %
--  %ccm_git_file_last_modified: 2026-10-03 17:01:02 %
--  %ccm_git_file_name: tt_backup-role.sql %
--  %ccm_git_path: infra/backups/sql/tt_backup-role.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: us-ascii %
--  %ccm_git_file_eol: CRLF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 2524 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- tt-backup :: PostgreSQL role provisioning for the encrypted tthealth_dev1 backup
--
-- Run ONCE, as a superuser, against the tthealth_dev1 database:
--     sudo -u postgres psql -d tthealth_dev1 -f infra/backups/sql/tt_backup-role.sql
--     sudo -u postgres psql -d tthealth_dev1 -c "\password tt_backup"
--
-- Then feed that same password to the installer (it is stored in a 0600
-- pgpass file owned BY the tt-backup operating-system account):
--     sudo TTBACKUP_PG_PASSWORD='<the-password>' \
--          infra/backups/scripts/install-tt-backup-tthealth.sh
--
-- GATE MODEL - this role is intentionally "read everything, write nothing":
--   * NOT a superuser, cannot CREATE ROLE/DATABASE, cannot replicate.
--   * Member of pg_read_all_data -> can read every table/view/sequence, which
--     is exactly what pg_dump needs, and nothing else.
--   * default_transaction_read_only = on -> even a future accidental GRANT
--     cannot turn it into a writer. This is what makes the account
--     "backup-but-not-restore".
-- There are no row-level-security policies on tthealth_dev1, so BYPASSRLS is
-- NOT granted. Re-check with:
--     SELECT count(*) FROM pg_class WHERE relrowsecurity AND relkind IN ('r','p');

CREATE ROLE tt_backup LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- "read all data" (PostgreSQL 14+): SELECT on all tables/views/sequences,
-- USAGE on all schemas and types.
GRANT pg_read_all_data TO tt_backup;

-- Belt and braces: this session can never write, so it can never restore,
-- mutate or drop anything - regardless of what is granted later.
ALTER ROLE tt_backup SET default_transaction_read_only = on;

-- PUBLIC normally already holds CONNECT; stated explicitly for clarity.
GRANT CONNECT ON DATABASE tthealth_dev1 TO tt_backup;

-- ---------------------------------------------------------------------------
-- NARROWER ALTERNATIVE (if cluster-wide pg_read_all_data is considered too
-- broad). Run as the owner of each schema's objects, and repeat
-- ALTER DEFAULT PRIVILEGES for every role that creates objects:
--
--   GRANT USAGE ON SCHEMA health, public TO tt_backup;
--   GRANT SELECT ON ALL TABLES    IN SCHEMA health, public TO tt_backup;
--   GRANT SELECT ON ALL SEQUENCES IN SCHEMA health, public TO tt_backup;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA health GRANT SELECT ON TABLES TO tt_backup;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA health GRANT SELECT ON SEQUENCES TO tt_backup;
-- ---------------------------------------------------------------------------
