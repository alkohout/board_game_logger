-- 004 — Make the imperium view respect row-level security.
--
-- A plain view applies RLS as the *view owner*, not the caller. imperium is a
-- view over games owned by the database owner, so it returned every user's
-- rows no matter who asked — 157 rows for user 1 and the same 157 for a user
-- who owns nothing.
--
-- security_invoker makes the view run with the caller's privileges, so the
-- policy on games applies normally. The endpoints are owner-gated as well;
-- this is the layer underneath that, so a future caller can't reopen the hole.
--
--   ./venv/bin/python migrations/run_sql.py migrations/004_owner_only_views.sql
--
-- Must run as the database owner: altering a view requires owning it. Needs
-- PostgreSQL 15 or newer. Safe to re-run.

BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'imperium' AND relkind = 'v') THEN
        EXECUTE 'ALTER VIEW imperium SET (security_invoker = true)';
        RAISE NOTICE 'imperium: security_invoker enabled';
    ELSE
        RAISE NOTICE 'imperium: not a view here, nothing to do';
    END IF;
END $$;

COMMIT;
