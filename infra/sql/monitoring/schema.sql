/*-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
--  %ccm_git_repo: TermiteTowers %
--  %ccm_git_branch: dev1 %
--  %ccm_git_object_id: infra/sql/monitoring/schema.sql@218 %
--  %ccm_git_author: mpegg %
--  %ccm_git_author_email: mpegg@hotmail.com %
--  %ccm_git_blob_sha: 4019cd92724aeaf0f28e6b25eba4b433ab06cf59 %
--  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
--  %ccm_git_commit_count: 218 %
--  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
--  %ccm_git_commit_author: mpegg %
--  %ccm_git_commit_email: mpegg@hotmail.com %
--  %ccm_git_commit_message: changes 261113 %
--  %ccm_git_modify_date: 2026-11-13 14:50:46 %
--  %ccm_git_file_last_modified: 2026-11-13 14:49:38 %
--  %ccm_git_file_name: schema.sql %
--  %ccm_git_path: infra/sql/monitoring/schema.sql %
--  %ccm_git_language_mode: sql %
--  %ccm_git_file_type: text/plain %
--  %ccm_git_file_encoding: us-ascii %
--  %ccm_git_file_eol: LF %
--  %ccm_git_exec: no %
--  %ccm_git_size: 6369 %
--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  */
-- ---------------------------------------------------------------------------
-- monitoring :: long-term availability archive for TermiteTowers (dev1)
--
-- WHY THIS SCHEMA EXISTS
--   Uptime Kuma keeps heartbeats in its own SQLite file and discards them on
--   its own retention, and Prometheus keeps 30 days with a 5 GB cap. Neither
--   answers "what was the availability of PowerDNS in Q1 2026, and how long
--   were the outages" two years from now. That question is cheap to answer:
--   one row per monitor per day, plus one row per outage.
--
-- WHY DAILY AND NOT EVERY SCRAPE
--   Measured volume at 15 monitors is 5,475 rows a year - a decade is 55 k
--   rows. Storing raw samples here would duplicate Prometheus for no gain.
--   The finest grain kept is a day, plus exact incident boundaries which the
--   daily rows would otherwise lose.
--
-- WHY monitor_key IS TEXT, NOT A NUMERIC ID
--   The identity a monitor exposes depends on what Kuma's /metrics actually
--   emits, and that endpoint is behind a token that has not been issued yet.
--   Guessing a numeric monitor_id would force a migration the moment the real
--   labels differ. A text key (the monitor's name, or an explicit id label
--   when one exists) is stable under both. Renames are handled by upserting
--   the dimension row, not by rewriting history.
--
-- WHY NOT READ kuma.db DIRECTLY
--   It is a live WAL SQLite file owned by the application, and its schema
--   moves between 2.x releases. The Prometheus query API is stable and its
--   30-day window covers any gap in the nightly job.
--
-- APPLY (idempotent, safe to re-run):
--   psql -d ttdb_dev1 -f infra/sql/monitoring/schema.sql
--
-- mpegg-adm holds CREATE on ttdb_dev1, so no superuser is needed.
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Dimension. Upserted every run, so a monitor rename or a new monitor is
-- captured without orphaning the history rows keyed on it.
CREATE TABLE IF NOT EXISTS monitoring.monitor (
    monitor_key  text        PRIMARY KEY,
    name         text        NOT NULL,
    type         text,
    target       text,
    first_seen   timestamptz NOT NULL DEFAULT now(),
    last_seen    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE monitoring.monitor IS
    'Monitor dimension, refreshed from Prometheus labels on every archive run.';

-- One row per monitor per day. NULL uptime_ratio means "no checks that day",
-- which is deliberately different from 0.0 ("checked and down") - conflating
-- them would turn a monitoring gap into a fake outage.
CREATE TABLE IF NOT EXISTS monitoring.monitor_daily (
    monitor_key      text    NOT NULL REFERENCES monitoring.monitor (monitor_key)
                             ON DELETE CASCADE,
    day              date    NOT NULL,
    checks           integer NOT NULL CHECK (checks >= 0),
    up_checks        integer NOT NULL CHECK (up_checks >= 0),
    uptime_ratio     numeric(6, 4) CHECK (uptime_ratio IS NULL
                                          OR (uptime_ratio >= 0 AND uptime_ratio <= 1)),
    avg_response_ms  numeric(12, 3),
    max_response_ms  numeric(12, 3),
    PRIMARY KEY (monitor_key, day),
    CONSTRAINT monitor_daily_up_le_checks CHECK (up_checks <= checks)
);

COMMENT ON COLUMN monitoring.monitor_daily.uptime_ratio IS
    'up_checks/checks. NULL when checks = 0, never 0.0 - a monitoring gap is not an outage.';

-- One row per contiguous down window. ended_at IS NULL means still down at the
-- time of the last archive run; the next run closes it once the monitor
-- recovers, so an open incident is updated rather than duplicated.
CREATE TABLE IF NOT EXISTS monitoring.monitor_incident (
    monitor_key  text        NOT NULL REFERENCES monitoring.monitor (monitor_key)
                             ON DELETE CASCADE,
    started_at   timestamptz NOT NULL,
    ended_at     timestamptz,
    duration_s   integer,
    last_status  text,
    error        text,
    PRIMARY KEY (monitor_key, started_at),
    CONSTRAINT monitor_incident_order CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- The "is anything down right now" query, which is the one that gets run.
CREATE INDEX IF NOT EXISTS monitor_incident_open_idx
    ON monitoring.monitor_incident (monitor_key, started_at DESC)
    WHERE ended_at IS NULL;

CREATE INDEX IF NOT EXISTS monitor_incident_recent_idx
    ON monitoring.monitor_incident (started_at DESC);

CREATE INDEX IF NOT EXISTS monitor_daily_day_idx
    ON monitoring.monitor_daily (day DESC);

-- Run heartbeat. Without it a silently dead timer looks identical to "nothing
-- interesting happened", which is the failure this whole archive exists to
-- prevent. Pruned to a rolling window by the archiver itself.
CREATE TABLE IF NOT EXISTS monitoring.archive_run (
    run_at        timestamptz PRIMARY KEY DEFAULT now(),
    window_start  timestamptz NOT NULL,
    window_end    timestamptz NOT NULL,
    days_written  integer     NOT NULL DEFAULT 0,
    rows_written  integer     NOT NULL DEFAULT 0,
    incidents     integer     NOT NULL DEFAULT 0,
    duration_ms   integer,
    note          text
);

COMMENT ON TABLE monitoring.archive_run IS
    'One row per archiver run. A stale max(run_at) means the timer is dead - alert on it.';
