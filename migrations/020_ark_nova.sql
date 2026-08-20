-- 020 — Ark Nova: which map, and what appeal you started the bot on.
--
-- Recorded as free text in `level` — "Map 0, start 15", "Map A. Start 10." —
-- with the same information sometimes in the notes instead. The two together
-- are the setup, and the notes show them being climbed like a difficulty
-- ladder: "Try a harder level", "Next: try start 20".
--
-- `zoo_map` rather than `map`: MAP is a reserved word in SQL:2016 and not
-- worth the argument.
--
--   ./venv/bin/python migrations/run_sql.py migrations/020_ark_nova.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS zoo_map      varchar(20);
ALTER TABLE games ADD COLUMN IF NOT EXISTS start_appeal smallint;

-- Appeal runs 0-100 on the track; anything outside that is a typo, and a
-- stray 150 would quietly distort a difficulty ladder.
ALTER TABLE games DROP CONSTRAINT IF EXISTS games_start_appeal_range;
ALTER TABLE games ADD  CONSTRAINT games_start_appeal_range
    CHECK (start_appeal IS NULL OR start_appeal BETWEEN 0 AND 100);

CREATE INDEX IF NOT EXISTS games_zoo_map_idx
    ON games (zoo_map) WHERE zoo_map IS NOT NULL;

COMMIT;
