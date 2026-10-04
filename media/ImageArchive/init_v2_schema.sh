#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/init_v2_schema.sh:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 8222f673e3709911adbad1af65d358420a1800c9 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-19 14:49:00 %
#  %ccm_git_file_name: init_v2_schema.sh %
#  %ccm_git_path: media/ImageArchive/init_v2_schema.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 9216 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2026-05-24 Matthew Pegg  adding readme  % 
# %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  %
 
# Run on monolith as mpegg-adm (peer auth, local socket).
# Creates the ttphoto_dev1 schema owned by ttphoto_dev1_owner so that
# default privileges grant ttphoto_dev1_app DML access automatically.
set -euo pipefail

echo "=== Initialising ttphoto_dev1 schema ==="
psql -d ttphoto_dev1 <<'SQL'
SET ROLE ttphoto_dev1_owner;

CREATE SCHEMA IF NOT EXISTS v2;

-- 1. Ontology & Policy
CREATE TABLE v2.tag_master (
  "tag_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "tag_key" TEXT NOT NULL UNIQUE,
  "canonical_id" BIGINT REFERENCES v2.tag_master("tag_id"),
  "description" TEXT
);

CREATE TABLE v2.tag_policies (
  "policy_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "target_type" TEXT NOT NULL CHECK (target_type IN ('stack', 'image', 'file', 'location')),
  "track_history" BOOLEAN NOT NULL DEFAULT true,
  "write_to_exif" BOOLEAN NOT NULL DEFAULT false,
  "db_column_name" TEXT,
  UNIQUE ("tag_id", "target_type")
);

-- 2. Anchors (with normalized state & search attributes)
CREATE TABLE v2.stacks (
  "stack_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "stack_name" TEXT NOT NULL,
  "status" TEXT DEFAULT 'active', -- 'active', 'archived', 'processing'
  "event_date" TIMESTAMP WITH TIME ZONE,
  "created_at" TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE v2.images (
  "image_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "image_hash" TEXT NOT NULL UNIQUE,
  "width" INTEGER,
  "height" INTEGER,
  "format" TEXT,
  "capture_date" TIMESTAMP WITH TIME ZONE,
  "camera_model" TEXT,
  "lens_info" TEXT,
  "orientation" TEXT CHECK (orientation IN ('landscape', 'portrait', 'square', 'unknown')),
  "color_space" TEXT,
  "rating" SMALLINT DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
  "is_flagged" BOOLEAN DEFAULT false
);

CREATE TABLE v2.files (
  "file_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "image_id" BIGINT NOT NULL REFERENCES v2.images("image_id"),
  "file_hash" TEXT NOT NULL UNIQUE,
  "file_size" BIGINT,
  "mime_type" TEXT,
  "bit_depth" INTEGER,
  "color_profile" TEXT,
  "compression_ratio" NUMERIC(5,2),
  "is_master" BOOLEAN DEFAULT false,
  "is_corrupt" BOOLEAN DEFAULT false
);

CREATE TABLE v2.file_locations (
  "location_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "file_id" BIGINT NOT NULL REFERENCES v2.files("file_id"),
  "base_path" TEXT NOT NULL,
  "filename" TEXT NOT NULL,
  "storage_volume" TEXT,
  "mount_point" TEXT,
  "is_online" BOOLEAN DEFAULT true,
  "last_verified_at" TIMESTAMP WITH TIME ZONE,
  CONSTRAINT "file_locations_file_id_base_path_key" UNIQUE ("file_id", "base_path")
);

-- 3. Relationships & Mappings
CREATE TABLE v2.stack_members (
  "stack_id" BIGINT NOT NULL REFERENCES v2.stacks("stack_id") ON DELETE CASCADE,
  "image_id" BIGINT NOT NULL REFERENCES v2.images("image_id") ON DELETE CASCADE,
  "added_at" TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY ("stack_id", "image_id")
);

-- Consistent Tag Mapping Tables
CREATE TABLE v2.stack_tags (
  "stack_id" BIGINT NOT NULL REFERENCES v2.stacks("stack_id"),
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "tag_value" TEXT,
  PRIMARY KEY ("stack_id", "tag_id")
);

CREATE TABLE v2.image_tags (
  "image_id" BIGINT NOT NULL REFERENCES v2.images("image_id"),
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "tag_value" TEXT,
  PRIMARY KEY ("image_id", "tag_id")
);

CREATE TABLE v2.file_tags (
  "file_id" BIGINT NOT NULL REFERENCES v2.files("file_id"),
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "tag_value" TEXT,
  PRIMARY KEY ("file_id", "tag_id")
);

CREATE TABLE v2.location_tags (
  "location_id" BIGINT NOT NULL REFERENCES v2.file_locations("location_id"),
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "tag_value" TEXT,
  PRIMARY KEY ("location_id", "tag_id")
);

-- 4. Audit & Utility
CREATE TABLE v2.tag_history (
  "history_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "tag_id" BIGINT NOT NULL REFERENCES v2.tag_master("tag_id"),
  "stack_id" BIGINT REFERENCES v2.stacks("stack_id"),
  "image_id" BIGINT REFERENCES v2.images("image_id"),
  "file_id" BIGINT REFERENCES v2.files("file_id"),
  "location_id" BIGINT REFERENCES v2.file_locations("location_id"),
  "old_value" TEXT,
  "new_value" TEXT,
  "recorded_at" TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT "check_one_object" CHECK (num_nonnulls("stack_id", "image_id", "file_id", "location_id") = 1)
);

CREATE TABLE v2.file_backups (
  "file_id" BIGINT NOT NULL REFERENCES v2.files("file_id") ON DELETE CASCADE,
  "destination" TEXT NOT NULL,
  "remote_path" TEXT,
  "backed_up_at" TIMESTAMP WITH TIME ZONE,
  "status" TEXT NOT NULL DEFAULT 'pending',
  "file_hash" TEXT,
  "error_msg" TEXT,
  CONSTRAINT "file_backups_pkey" PRIMARY KEY ("file_id", "destination")
);

-- 5. Consolidated Performance Indices
-- Foreign Key Indices (Speeds up JOINs and Foreign Key checks)
CREATE INDEX "idx_stack_members_stack"    ON v2.stack_members ("stack_id");
CREATE INDEX "idx_stack_members_image"    ON v2.stack_members ("image_id");
CREATE INDEX "idx_tag_policies_tag_id"    ON v2.tag_policies ("tag_id");
CREATE INDEX "idx_files_image_id"         ON v2.files ("image_id");
CREATE INDEX "idx_file_loc_file_id"       ON v2.file_locations ("file_id");
CREATE INDEX "idx_stack_tags_tag_id"      ON v2.stack_tags ("tag_id");
CREATE INDEX "idx_image_tags_tag_id"      ON v2.image_tags ("tag_id");
CREATE INDEX "idx_file_tags_tag_id"       ON v2.file_tags ("tag_id");
CREATE INDEX "idx_loc_tags_tag_id"        ON v2.location_tags ("tag_id");

-- Audit/Historical Performance
-- This supports queries like: SELECT * FROM v2.tag_history WHERE tag_id = ? ORDER BY recorded_at DESC
CREATE INDEX "idx_tag_history_lookup"     ON v2.tag_history ("tag_id", "recorded_at");

CREATE OR REPLACE FUNCTION v2.fn_audit_tag_change()
RETURNS TRIGGER AS $$
DECLARE
    v_track_history BOOLEAN;
    v_target_type   TEXT;
    v_tag_id        BIGINT;
    v_old_value     TEXT;
    v_new_value     TEXT;
    v_image_id      BIGINT;
    v_stack_id      BIGINT;
    v_file_id       BIGINT;
    v_location_id   BIGINT;
BEGIN
    -- Determine target_type from the firing table
    v_target_type := CASE TG_TABLE_NAME
        WHEN 'image_tags'    THEN 'image'
        WHEN 'stack_tags'    THEN 'stack'
        WHEN 'file_tags'     THEN 'file'
        WHEN 'location_tags' THEN 'location'
    END;

    -- For DELETE use OLD row; for INSERT/UPDATE use NEW row
    v_tag_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.tag_id ELSE NEW.tag_id END;

    -- Look up policy; if absent default to track=true (always record history)
    SELECT track_history INTO v_track_history
    FROM v2.tag_policies
    WHERE tag_id = v_tag_id AND target_type = v_target_type;

    IF v_track_history IS NULL THEN
        v_track_history := true;
    END IF;

    IF v_track_history THEN
        -- Resolve old/new values per operation
        CASE TG_OP
            WHEN 'INSERT' THEN v_old_value := NULL;          v_new_value := NEW.tag_value;
            WHEN 'UPDATE' THEN v_old_value := OLD.tag_value; v_new_value := NEW.tag_value;
            WHEN 'DELETE' THEN v_old_value := OLD.tag_value; v_new_value := NULL;
        END CASE;

        -- Resolve entity id using IF/ELSIF per table name.
        -- A CASE expression is NOT short-circuit in PL/pgSQL — every branch is
        -- compiled against OLD/NEW's row type, so accessing OLD.stack_id from
        -- inside an image_tags trigger crashes at runtime.  IF/ELSIF avoids this.
        IF TG_TABLE_NAME = 'image_tags' THEN
            v_image_id    := CASE WHEN TG_OP = 'DELETE' THEN OLD.image_id    ELSE NEW.image_id    END;
        ELSIF TG_TABLE_NAME = 'stack_tags' THEN
            v_stack_id    := CASE WHEN TG_OP = 'DELETE' THEN OLD.stack_id    ELSE NEW.stack_id    END;
        ELSIF TG_TABLE_NAME = 'file_tags' THEN
            v_file_id     := CASE WHEN TG_OP = 'DELETE' THEN OLD.file_id     ELSE NEW.file_id     END;
        ELSIF TG_TABLE_NAME = 'location_tags' THEN
            v_location_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.location_id ELSE NEW.location_id END;
        END IF;

        INSERT INTO v2.tag_history
            (tag_id, old_value, new_value, image_id, stack_id, file_id, location_id)
        VALUES
            (v_tag_id, v_old_value, v_new_value,
             v_image_id, v_stack_id, v_file_id, v_location_id);
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_image_tags    AFTER INSERT OR UPDATE OR DELETE ON v2.image_tags    FOR EACH ROW EXECUTE FUNCTION v2.fn_audit_tag_change();
CREATE TRIGGER trg_audit_stack_tags    AFTER INSERT OR UPDATE OR DELETE ON v2.stack_tags    FOR EACH ROW EXECUTE FUNCTION v2.fn_audit_tag_change();
CREATE TRIGGER trg_audit_file_tags     AFTER INSERT OR UPDATE OR DELETE ON v2.file_tags     FOR EACH ROW EXECUTE FUNCTION v2.fn_audit_tag_change();
CREATE TRIGGER trg_audit_location_tags AFTER INSERT OR UPDATE OR DELETE ON v2.location_tags FOR EACH ROW EXECUTE FUNCTION v2.fn_audit_tag_change();
