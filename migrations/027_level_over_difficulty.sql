-- 027 — Level goes back to being the one field; difficulty is retired.
--
-- 022 split difficulty out of level on the grounds that a bare "Expert" was
-- structured data. In practice level is the better field: a difficulty always
-- reads sensibly as a level, but plenty of levels aren't difficulties —
-- "Scenario 4 (All D cards)", "Imperator. Romans (me) vs Qin (bot)" — so
-- having both meant one box that could hold everything and another that
-- couldn't, and no rule about which to use.
--
-- Nothing is lost. Every value difficulty holds is either already the same
-- word in level, or is moved there first. The Ares inference that 026 wrote
-- into difficulty — everything before the first Expert game was Advanced —
-- lands in level instead.
--
--   ./venv/bin/python migrations/run_sql.py migrations/027_level_over_difficulty.sql
--
-- Safe to re-run. Drops a column, so take a backup first if you want one.

BEGIN;

-- Anything difficulty knows that level doesn't.
UPDATE games
SET level = difficulty
WHERE difficulty IS NOT NULL
  AND coalesce(btrim(level), '') IN ('', 'null');

-- Ares sittings before difficulty was ever recorded were played on Advanced.
-- Written here as well as in 026 so this migration stands on its own.
UPDATE games
SET level = 'Advanced'
WHERE game_title ILIKE '%ares expedition%'
  AND coalesce(btrim(level), '') IN ('', 'null')
  AND date_played < (
      SELECT min(date_played) FROM games
      WHERE game_title ILIKE '%ares expedition%'
        AND btrim(lower(coalesce(level, ''))) = 'expert');

ALTER TABLE games DROP COLUMN IF EXISTS difficulty;

COMMIT;
