-- 022 — A difficulty for any game, and a scenario number for ladders.
--
-- Difficulty was going into `level` as a bare word — Expert, Normal, Standard,
-- Easy, Advanced, Beginner — across Ares Expedition, Earth, Lorcana and both
-- Centurys. One field serves all of them and anything future, rather than a
-- bespoke build per game.
--
-- scenario_number is for games climbed a rung at a time. Cascadia records
-- "Scenario 4 (All D cards)" through "Scenario 8"; For Northwood! does the
-- same by season. Kept general so the next one needs no migration.
--
-- Deliberately not a fixed list: difficulty wording differs per game (Standard
-- is Century's word, Expert is Earth's) and a closed set would reject a name
-- some other game uses.
--
--   ./venv/bin/python migrations/run_sql.py migrations/022_difficulty_and_scenario_number.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS difficulty      varchar(40);
ALTER TABLE games ADD COLUMN IF NOT EXISTS scenario_number smallint;

-- A ladder rung, not a score; three digits is already generous.
ALTER TABLE games DROP CONSTRAINT IF EXISTS games_scenario_number_range;
ALTER TABLE games ADD  CONSTRAINT games_scenario_number_range
    CHECK (scenario_number IS NULL OR scenario_number BETWEEN 1 AND 999);

CREATE INDEX IF NOT EXISTS games_difficulty_idx
    ON games (difficulty) WHERE difficulty IS NOT NULL;

COMMIT;
