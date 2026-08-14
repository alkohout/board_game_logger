-- 010 — Give `level` room to breathe.
--
-- varchar(50), and the longest value in use was already 46 characters. Raised
-- to 500.
--
-- The imperium view reads this column, and Postgres refuses to alter a type a
-- view depends on, so the view is dropped and rebuilt. Rebuilding it means
-- restoring security_invoker and the grants as well — without those it would
-- go back to showing every user's rows to anyone who asked, which is exactly
-- what 004 fixed.
--
--   ./venv/bin/python migrations/run_sql.py migrations/010_longer_level.sql
--
-- Safe to re-run.

BEGIN;

DROP VIEW IF EXISTS imperium;

ALTER TABLE games ALTER COLUMN level TYPE varchar(500);

CREATE VIEW imperium AS
    SELECT id, date_played, game_title, notes, result, my_score, bot_score, level
    FROM games
    WHERE game_title ILIKE '%Imperium%';

-- Back exactly as 002 and 004 left it.
ALTER VIEW imperium SET (security_invoker = true);
GRANT SELECT, INSERT, UPDATE, DELETE ON imperium TO bgl_app;
GRANT SELECT ON imperium TO bgl_ai_owner;

COMMIT;
