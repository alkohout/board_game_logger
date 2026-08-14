-- 014 — Sleeping Gods becomes per-account.
--
-- Imperium and Spirit Island were already per-user: both read `games`, which
-- carries user_id and row-level security, and the imperium view is
-- security_invoker so it applies the policy as whoever is asking. Only their
-- endpoints were gated. These two tables are the exception — shared by
-- everyone, so a second account would have seen the owner's campaign.
--
-- Same shape as games: a user_id defaulting to the current app.user_id, RLS
-- enabled and FORCEd so the table owner is subject to it too, and one policy
-- covering all commands.
--
--   ./venv/bin/python migrations/run_sql.py migrations/014_sleeping_gods_per_user.sql
--
-- Existing rows go to the owner. Safe to re-run.

BEGIN;

-- The owner takes everything already recorded.
CREATE TEMP TABLE _owner ON COMMIT DROP AS
    SELECT id FROM users WHERE is_owner ORDER BY id LIMIT 1;

ALTER TABLE sleeping_gods        ADD COLUMN IF NOT EXISTS user_id integer;
ALTER TABLE sleeping_gods_totems ADD COLUMN IF NOT EXISTS user_id integer;

UPDATE sleeping_gods        SET user_id = (SELECT id FROM _owner) WHERE user_id IS NULL;
UPDATE sleeping_gods_totems SET user_id = (SELECT id FROM _owner) WHERE user_id IS NULL;

-- Same default as games, so an insert picks up the caller without naming them.
ALTER TABLE sleeping_gods ALTER COLUMN user_id
    SET DEFAULT (NULLIF(current_setting('app.user_id', true), ''))::integer;
ALTER TABLE sleeping_gods_totems ALTER COLUMN user_id
    SET DEFAULT (NULLIF(current_setting('app.user_id', true), ''))::integer;

ALTER TABLE sleeping_gods        ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE sleeping_gods_totems ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE sleeping_gods        ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleeping_gods        FORCE  ROW LEVEL SECURITY;
ALTER TABLE sleeping_gods_totems ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleeping_gods_totems FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sleeping_gods_owner_only ON sleeping_gods;
CREATE POLICY sleeping_gods_owner_only ON sleeping_gods
    USING      (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer)
    WITH CHECK (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer);

DROP POLICY IF EXISTS sleeping_gods_totems_owner_only ON sleeping_gods_totems;
CREATE POLICY sleeping_gods_totems_owner_only ON sleeping_gods_totems
    USING      (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer)
    WITH CHECK (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer);

CREATE INDEX IF NOT EXISTS sleeping_gods_user_idx        ON sleeping_gods (user_id);
CREATE INDEX IF NOT EXISTS sleeping_gods_totems_user_idx ON sleeping_gods_totems (user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON sleeping_gods        TO bgl_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON sleeping_gods_totems TO bgl_app;

COMMIT;
