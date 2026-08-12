-- 001 — Accounts.
--
-- Phase 1 of multi-user: who exists and who is allowed in. Data ownership and
-- row-level security come in 002; nothing here changes what any query returns.
--
-- Signup creates a 'pending' row. Only the owner can move it to 'active'.
--
--   ./venv/bin/python migrations/run_sql.py migrations/001_accounts.sql
--
-- Safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT        NOT NULL,
    password_hash TEXT        NOT NULL,
    display_name  TEXT,
    status        TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'active', 'disabled')),
    is_owner      BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at   TIMESTAMPTZ
);

-- Emails are compared case-insensitively; the app lowercases on the way in and
-- this index makes a mixed-case duplicate impossible even if it forgets to.
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_key ON users (lower(email));

-- Exactly one owner, enforced by the database rather than by convention.
CREATE UNIQUE INDEX IF NOT EXISTS users_single_owner ON users ((is_owner)) WHERE is_owner;

-- Failed logins, for throttling. Module-level counters would not work here:
-- gunicorn runs two workers and each would keep its own tally.
CREATE TABLE IF NOT EXISTS login_attempts (
    id         SERIAL PRIMARY KEY,
    email      TEXT        NOT NULL,
    ip         TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS login_attempts_email_time
    ON login_attempts (lower(email), attempted_at DESC);

COMMIT;
