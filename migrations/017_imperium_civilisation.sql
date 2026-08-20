-- 017 — A column for the Imperium deck you faced.
--
-- Imperium plays were recorded as free text in `level`:
--   "Imperator. Romans (me) vs Atlanteans (bot)."
-- The stats page pulled the opponent out by looking for a civilisation name
-- inside that string, which worked for 51 of 62 plays and missed the rest
-- because they were written singular — "Viking", "Greek", "Carthaginian".
--
-- You always play Romans, so the deck that varies is the opponent's, and that
-- is what this column holds. Romans is deliberately not in IMPERIUM_CIVS, so
-- "Romans (me)" can never be mistaken for the deck faced.
--
-- Nothing is required to use it: the stats page still reads the old free text
-- for any play with no civilisation set, so every game already logged keeps
-- counting exactly as it did.
--
-- The imperium view has to be rebuilt to expose the new column, which means
-- restoring security_invoker and the grants in the same transaction. Dropping
-- a view silently discards both, and without them it shows every account's
-- rows to anyone — the leak 004 fixed.
--
--   ./venv/bin/python migrations/run_sql.py migrations/017_imperium_civilisation.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS civilisation varchar(100);

CREATE INDEX IF NOT EXISTS games_civilisation_idx
    ON games (civilisation) WHERE civilisation IS NOT NULL;

DROP VIEW IF EXISTS imperium;

CREATE VIEW imperium AS
    SELECT id, date_played, game_title, notes, result, my_score, bot_score,
           level, civilisation
    FROM games
    WHERE game_title ILIKE '%Imperium%';

ALTER VIEW imperium SET (security_invoker = true);
GRANT SELECT, INSERT, UPDATE, DELETE ON imperium TO bgl_app;
GRANT SELECT ON imperium TO bgl_ai_owner;

COMMIT;
