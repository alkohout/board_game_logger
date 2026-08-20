-- 024 — Ares Expedition's end state, for you and for the bot.
--
-- Finished games were recorded as prose in the score fields:
--   my_score  "8 C, 13 %, 9 ocean Tiles"
--   bot_score "8 C, 14 %, 9 ocean"
-- Temperature, oxygen and oceans, sometimes megacredits. The bot is nearly
-- always 8/14/9 — fully terraformed — which is the thing being raced.
--
-- Ranges follow the board: temperature -30 to +8, oxygen 0-14%, oceans 0-9.
-- Generous on megacredits, which has no ceiling.
--
--   ./venv/bin/python migrations/run_sql.py migrations/024_ares_expedition.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_temp_me    smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_oxygen_me  smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_oceans_me  smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_mc_me      smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_temp_bot   smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_oxygen_bot smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_oceans_bot smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ares_mc_bot     smallint;

ALTER TABLE games DROP CONSTRAINT IF EXISTS games_ares_ranges;
ALTER TABLE games ADD  CONSTRAINT games_ares_ranges CHECK (
    (ares_temp_me    IS NULL OR ares_temp_me    BETWEEN -40 AND 20) AND
    (ares_temp_bot   IS NULL OR ares_temp_bot   BETWEEN -40 AND 20) AND
    (ares_oxygen_me  IS NULL OR ares_oxygen_me  BETWEEN 0 AND 20) AND
    (ares_oxygen_bot IS NULL OR ares_oxygen_bot BETWEEN 0 AND 20) AND
    (ares_oceans_me  IS NULL OR ares_oceans_me  BETWEEN 0 AND 12) AND
    (ares_oceans_bot IS NULL OR ares_oceans_bot BETWEEN 0 AND 12) AND
    (ares_mc_me      IS NULL OR ares_mc_me      BETWEEN 0 AND 999) AND
    (ares_mc_bot     IS NULL OR ares_mc_bot     BETWEEN 0 AND 999)
);

COMMIT;
