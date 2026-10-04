#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/init_v2_schema.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 98eb3fb37cc4eb3e6b0d5050c3dbbce4fa38c95c %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-19 12:51:38 %
#  %ccm_git_file_name: init_v2_schema.py %
#  %ccm_git_path: media/ImageArchive/init_v2_schema.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6163 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

import os
import psycopg2
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────────

ENV_FILE = Path(__file__).parent.parent / ".env"

# ── Env / connection ─────────────────────────────────────────────────────────────

def load_env(path: Path):
    """Load environment variables from a .env file."""
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value


def get_conn():
    """Get a database connection using the PG_DSN environment variable."""
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        print("ERROR: PG_DSN not set. Add PG_DSN=postgres://... to media/.env")
        sys.exit(1)
    return psycopg2.connect(dsn)


# ── Database operations ────────────────────────────────────────────────────────

def init_db_schema():
    """Initialize the ttphoto_dev1 schema."""
    conn = None
    try:
        # Connect to the PostgreSQL server
        conn = get_conn()
        cur = conn.cursor()

        # Set role and create schema if not exists
        cur.execute("SET ROLE ttphoto_dev1_owner;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS v2;")

        # Create tables
        tables = [
            """
            CREATE TABLE v2.tag_master (
                id SERIAL PRIMARY KEY,
                tag_key VARCHAR(255) UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE v2.tag_policies (
                id SERIAL PRIMARY KEY,
                policy_name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT
            );
            """,
            """
            CREATE TABLE v2.stacks (
                id SERIAL PRIMARY KEY,
                stack_key VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.images (
                image_hash BYTEA PRIMARY KEY,
                file_hash BYTEA UNIQUE NOT NULL,
                base_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.files (
                file_hash BYTEA PRIMARY KEY,
                base_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.file_locations (
                image_hash BYTEA REFERENCES v2.images(image_hash) ON DELETE CASCADE,
                file_hash BYTEA REFERENCES v2.files(file_hash) ON DELETE CASCADE,
                base_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.stack_members (
                stack_id INTEGER REFERENCES v2.stacks(id) ON DELETE CASCADE,
                image_hash BYTEA REFERENCES v2.images(image_hash) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.stack_tags (
                stack_id INTEGER REFERENCES v2.stacks(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES v2.tag_master(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.image_tags (
                image_hash BYTEA REFERENCES v2.images(image_hash) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES v2.tag_master(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.file_tags (
                file_hash BYTEA REFERENCES v2.files(file_hash) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES v2.tag_master(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.location_tags (
                image_hash BYTEA REFERENCES v2.images(image_hash) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES v2.tag_master(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.tag_history (
                id SERIAL PRIMARY KEY,
                tag_key VARCHAR(255) NOT NULL,
                action VARCHAR(10) NOT NULL,  -- e.g., 'create', 'update'
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE v2.file_backups (
                file_hash BYTEA PRIMARY KEY,
                backup_data BYTEA NOT NULL,
                backed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]

        for table in tables:
            cur.execute(table)

        # Commit the changes and close the connection
        conn.commit()
        print("Schema initialized successfully.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
    finally:
        if conn is not None:
            conn.close()


# ── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_env(ENV_FILE)
    init_db_schema()