-- 016 — A timezone per account.
--
-- "Today", "this week" and the records are worked out in one zone for
-- everybody, set by the TIMEZONE variable and defaulting to Pacific/Auckland.
-- That was right while there was one user in New Zealand. It is wrong for
-- anyone else: at 8pm on the 14th in London it is already the 15th in
-- Auckland, so a game logged then counts against the wrong day and "played
-- today" reads zero.
--
-- Existing accounts keep Pacific/Auckland, so nothing changes for the owner.
-- New accounts get whatever their browser reports at signup.
--
--   ./venv/bin/python migrations/run_sql.py migrations/016_user_timezone.sql
--
-- Safe to re-run.

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone text;

UPDATE users SET timezone = 'Pacific/Auckland' WHERE timezone IS NULL;

ALTER TABLE users ALTER COLUMN timezone SET DEFAULT 'Pacific/Auckland';
ALTER TABLE users ALTER COLUMN timezone SET NOT NULL;

COMMIT;
