-- 007 — Grant the app role access to tables created from now on.
--
-- 002 granted bgl_app rights on the tables that existed at that moment, so a
-- table added later is invisible to the app until someone remembers to grant
-- it. That surfaces as "permission denied for table X" in production, long
-- after the migration that created it looked successful.
--
-- Default privileges close that: anything the database owner creates in
-- public from here on is granted automatically.
--
--   ./venv/bin/python migrations/run_sql.py migrations/007_default_privileges.sql
--
-- Safe to re-run.

BEGIN;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bgl_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO bgl_app;

-- Catch up anything already created since 002.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bgl_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bgl_app;

-- The AI roles keep their narrow grants: never the account or billing tables.
REVOKE ALL ON users, login_attempts, ai_usage, credit_purchases FROM bgl_ai, bgl_ai_owner;

COMMIT;
