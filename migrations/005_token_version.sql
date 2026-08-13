-- 005 — Make a password change invalidate existing logins.
--
-- Tokens are signed statements of "this is user N" with a 30-day life. Until
-- now, changing a password did nothing to tokens already issued: a leaked one
-- stayed usable for up to a month, and the obvious remedy didn't work.
--
-- Each token now carries the version it was issued under. Changing a password
-- bumps the version, so every older token stops matching and is refused.
--
--   ./venv/bin/python migrations/run_sql.py migrations/005_token_version.sql
--
-- Everyone is logged out once when this ships. Safe to re-run.

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

COMMIT;
