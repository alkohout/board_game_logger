-- 011 — Room for result and the score fields.
--
-- All varchar(50), and all being used as free text rather than short codes:
--
--   result    37 of 50 used   "Lost. Romans (me) vs Abbasids (bot)"
--   my_score  43 of 50 used   the tightest of the three
--   bot_score 24 of 50 used   same kind of field, same treatment
--
-- Raised to 500, matching level. game_title is left at 255: it uses 49.
--
-- Same view dance as 010 — imperium reads these columns, so it is dropped and
-- rebuilt, and security_invoker and the grants restored with it. Miss those
-- and the view goes back to showing every user's rows to anyone.
--
--   ./venv/bin/python migrations/run_sql.py migrations/011_longer_result_scores.sql
--
-- Safe to re-run.

BEGIN;

DROP VIEW IF EXISTS imperium;

ALTER TABLE games ALTER COLUMN result    TYPE varchar(500);
ALTER TABLE games ALTER COLUMN my_score  TYPE varchar(500);
ALTER TABLE games ALTER COLUMN bot_score TYPE varchar(500);

CREATE VIEW imperium AS
    SELECT id, date_played, game_title, notes, result, my_score, bot_score, level
    FROM games
    WHERE game_title ILIKE '%Imperium%';

ALTER VIEW imperium SET (security_invoker = true);
GRANT SELECT, INSERT, UPDATE, DELETE ON imperium TO bgl_app;
GRANT SELECT ON imperium TO bgl_ai_owner;

COMMIT;
