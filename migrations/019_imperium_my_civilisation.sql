-- 019 — Which civilisation you played, for when it stops being Romans.
--
-- Every Imperium play so far has been Romans, which is why the stats page
-- tracks the opponent's deck and Romans isn't in IMPERIUM_CIVS at all. That
-- holds until the day it doesn't, so plays now record your own side too.
--
-- Backfilled only where the old free text actually says so — "Romans (me)" —
-- rather than assuming it of every row. Plays with nothing recorded stay null;
-- the form defaults to Romans for new ones.
--
--   ./venv/bin/python migrations/run_sql.py migrations/019_imperium_my_civilisation.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS my_civilisation varchar(100);

-- "Romans (me)", "Roman (me)", "Roman's (me)" — all of them mean the same.
UPDATE games
SET my_civilisation = 'Romans'
WHERE game_title ILIKE '%imperium%'
  AND my_civilisation IS NULL
  AND (coalesce(level, '') || ' ' || coalesce(result, '')) ~* 'roman[’''s]*\s*\(\s*me\s*\)';

DROP VIEW IF EXISTS imperium;

CREATE VIEW imperium AS
    SELECT id, date_played, game_title, notes, result, my_score, bot_score,
           level, civilisation, my_civilisation
    FROM games
    WHERE game_title ILIKE '%Imperium%';

ALTER VIEW imperium SET (security_invoker = true);
GRANT SELECT, INSERT, UPDATE, DELETE ON imperium TO bgl_app;
GRANT SELECT ON imperium TO bgl_ai_owner;

COMMIT;
