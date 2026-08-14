-- 012 — Columns for Spirit Island plays.
--
-- Imperium fits in `level` because it has one dimension: which civilisation.
-- Spirit Island has three that vary independently in a single play — the
-- spirit you played, the adversary and its level, and the scenario — so
-- counting wins per spirit out of one free-text box is guesswork. These are
-- separate columns instead.
--
-- Null everywhere for the 2,000-odd non-Spirit-Island plays, which is what we
-- want: the stats page counts rows where the column is set.
--
-- No view rebuild needed, unlike 010/011 — `imperium` selects named columns,
-- so adding new ones doesn't disturb it. Table-level grants already cover
-- future columns, so bgl_app picks these up without further GRANTs.
--
--   ./venv/bin/python migrations/run_sql.py migrations/012_spirit_island.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE games ADD COLUMN IF NOT EXISTS spirit          varchar(100);
ALTER TABLE games ADD COLUMN IF NOT EXISTS adversary       varchar(100);
ALTER TABLE games ADD COLUMN IF NOT EXISTS adversary_level smallint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS scenario        varchar(100);

-- Only ever 1-6 on the adversary dials; a typo'd 60 would quietly skew counts.
ALTER TABLE games DROP CONSTRAINT IF EXISTS games_adversary_level_range;
ALTER TABLE games ADD  CONSTRAINT games_adversary_level_range
    CHECK (adversary_level IS NULL OR adversary_level BETWEEN 1 AND 6);

-- The stats page filters to Spirit Island titles and groups by these.
CREATE INDEX IF NOT EXISTS games_spirit_idx    ON games (spirit)    WHERE spirit    IS NOT NULL;
CREATE INDEX IF NOT EXISTS games_adversary_idx ON games (adversary) WHERE adversary IS NOT NULL;
CREATE INDEX IF NOT EXISTS games_scenario_idx  ON games (scenario)  WHERE scenario  IS NOT NULL;

COMMIT;
