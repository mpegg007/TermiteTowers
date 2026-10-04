#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/db_operations.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 9fabd6a8e5327b77681075283de67f3cb0bd931f %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-19 11:57:52 %
#  %ccm_git_file_name: db_operations.py %
#  %ccm_git_path: media/ImageArchive/db_operations.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5005 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

import os
import psycopg2
from psycopg2.extras import execute_values

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

def get_or_create_tag_id(cur, tag_key: str) -> int:
    """Get or create a tag ID for the given tag key."""
    cur.execute(
        """
        INSERT INTO v2.tags (tag_key)
        VALUES (%s)
        ON CONFLICT (tag_key) DO NOTHING
        RETURNING id;
        """,
        (tag_key,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def upsert_image(cur, image_hash: str, file_hash: str, base_path: str, filename: str):
    """Upsert an image into the database."""
    cur.execute(
        """
        INSERT INTO v2.images (image_hash)
        VALUES (%s)
        ON CONFLICT (image_hash) DO NOTHING;
        """,
        (image_hash,)
    )
    cur.execute(
        """
        INSERT INTO v2.files (file_hash, base_path, filename)
        VALUES (%s, %s, %s)
        ON CONFLICT (file_hash) DO UPDATE SET
            base_path = EXCLUDED.base_path,
            filename = EXCLUDED.filename;
        """,
        (file_hash, base_path, filename)
    )
    cur.execute(
        """
        INSERT INTO v2.file_locations (image_hash, file_hash, base_path, filename)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (image_hash, file_hash) DO NOTHING;
        """,
        (image_hash, file_hash, base_path, filename)
    )


def sync_image_tags(cur, image_hash: str, tag_rows: dict[str, str]):
    """Sync tags for an image."""
    cur.execute(
        """
        DELETE FROM v2.image_tags WHERE image_hash = %s;
        """,
        (image_hash,)
    )
    execute_values(
        cur,
        """
        INSERT INTO v2.image_tags (image_hash, tag_id)
        VALUES %s
        ON CONFLICT DO NOTHING;
        """,
        [(image_hash, get_or_create_tag_id(cur, key)) for key in tag_rows]
    )


def sync_file_tags(cur, file_hash: str, tag_rows: dict[str, str]):
    """Sync tags for a file."""
    cur.execute(
        """
        DELETE FROM v2.file_tags WHERE file_hash = %s;
        """,
        (file_hash,)
    )
    execute_values(
        cur,
        """
        INSERT INTO v2.file_tags (file_hash, tag_id)
        VALUES %s
        ON CONFLICT DO NOTHING;
        """,
        [(file_hash, get_or_create_tag_id(cur, key)) for key in tag_rows]
    )


def check_schema(cur):
    """Check if the database schema is up to date."""
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'v2'
              AND table_name = 'images'
        );
        """
    )
    return cur.fetchone()[0]


def prime_tag_cache(cur):
    """Prime the tag cache with existing tags."""
    cur.execute(
        """
        SELECT tag_key, id FROM v2.tags;
        """
    )
    return {row[0]: row[1] for row in cur.fetchall()}


# ── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_env(ENV_FILE)
    with get_conn() as conn:
        with conn.cursor() as cur:
            if not check_schema(cur):
                print("ERROR: Database schema is not up to date.")
                sys.exit(1)
            tag_cache = prime_tag_cache(cur)
            # Example usage
            image_hash = "example_image_hash"
            file_hash = "example_file_hash"
            base_path = "/path/to/base"
            filename = "example.jpg"
            tags = {"tag1": "value1", "tag2": "value2"}
            upsert_image(cur, image_hash, file_hash, base_path, filename)
            sync_image_tags(cur, image_hash, tags)
            sync_file_tags(cur, file_hash, tags)