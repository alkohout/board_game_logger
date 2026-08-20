-- 026 — Two facts about Ares Expedition that the data didn't say out loud.
--
-- A win is a terraformed planet. That's the win condition, so a won game
-- reached 8 C, 14% oxygen and 9 oceans by definition — those parameters were
-- never unknown, just never written down. Four wins had no numbers at all and
-- so showed as blank rather than as the 100% they were.
--
-- Everything before the first Expert game was played on Advanced. Difficulty
-- only started being recorded on 2025-03-17; the 16 sittings before it carry
-- none, which put them in a "not recorded" bucket of their own instead of
-- alongside the Advanced game that follows them.
--
-- Both are inferences, but from rules rather than guesswork, and both only
-- fill blanks — anything already recorded is left exactly as it is.
--
--   ./venv/bin/python migrations/run_sql.py migrations/026_ares_wins_and_advanced.sql
--
-- Safe to re-run.

BEGIN;

-- A win means every parameter reached its target.
UPDATE games
SET ares_temp_me   = COALESCE(ares_temp_me, 8),
    ares_oxygen_me = COALESCE(ares_oxygen_me, 14),
    ares_oceans_me = COALESCE(ares_oceans_me, 9)
WHERE game_title ILIKE '%ares expedition%'
  AND result ILIKE '%won%'
  AND (ares_temp_me IS NULL OR ares_oxygen_me IS NULL OR ares_oceans_me IS NULL);

-- Everything before difficulty started being recorded was Advanced.
UPDATE games
SET difficulty = 'Advanced'
WHERE game_title ILIKE '%ares expedition%'
  AND difficulty IS NULL
  AND date_played < (
      SELECT min(date_played) FROM games
      WHERE game_title ILIKE '%ares expedition%' AND difficulty = 'Expert');

COMMIT;
