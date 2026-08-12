-- 003 — AI usage ledger and purchased credit.
--
-- Every AI question is metered against a balance made of two parts:
--
--   free   — NZ$0.50 granted per calendar month, does not accumulate
--   credit — bought through Stripe, persists until spent
--
-- Each usage row records which pot it came out of, so the two can be reported
-- and reconciled separately without inferring anything after the fact. The
-- owner is never blocked, but their usage is still recorded.
--
--   ./venv/bin/python migrations/run_sql.py migrations/003_credit.sql
--
-- Safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS ai_usage (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER     NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    kind          TEXT        NOT NULL,          -- 'rules' | 'db_query'
    cost_nzd      NUMERIC(10, 5) NOT NULL,
    cost_usd      NUMERIC(10, 5),
    funded_by     TEXT        NOT NULL CHECK (funded_by IN ('free', 'credit', 'owner')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_usage_user_time ON ai_usage (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS credit_purchases (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER     NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    amount_nzd        NUMERIC(10, 2) NOT NULL CHECK (amount_nzd > 0),
    status            TEXT        NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'paid', 'cancelled')),
    stripe_session_id TEXT        UNIQUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS credit_purchases_user ON credit_purchases (user_id, status);

-- Same ownership rule as the game tables: you only ever see your own rows.
ALTER TABLE ai_usage         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage         FORCE  ROW LEVEL SECURITY;
ALTER TABLE credit_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_purchases FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ai_usage_owner_only ON ai_usage;
CREATE POLICY ai_usage_owner_only ON ai_usage
    USING      (user_id = nullif(current_setting('app.user_id', true), '')::integer)
    WITH CHECK (user_id = nullif(current_setting('app.user_id', true), '')::integer);

DROP POLICY IF EXISTS credit_purchases_owner_only ON credit_purchases;
CREATE POLICY credit_purchases_owner_only ON credit_purchases
    USING      (user_id = nullif(current_setting('app.user_id', true), '')::integer)
    WITH CHECK (user_id = nullif(current_setting('app.user_id', true), '')::integer);

-- The Stripe webhook arrives with no session, so it credits the balance
-- through a definer function rather than by turning the policies off.
CREATE OR REPLACE FUNCTION credit_mark_paid(p_session_id TEXT)
RETURNS TABLE (purchase_id INTEGER, user_id INTEGER, amount_nzd NUMERIC)
LANGUAGE sql SECURITY DEFINER
AS $$
    UPDATE credit_purchases
    SET status = 'paid', paid_at = now()
    WHERE stripe_session_id = p_session_id AND status = 'pending'
    RETURNING id, user_id, amount_nzd;
$$;

GRANT SELECT, INSERT, UPDATE ON ai_usage, credit_purchases TO bgl_app;
GRANT USAGE, SELECT ON SEQUENCE ai_usage_id_seq, credit_purchases_id_seq TO bgl_app;
GRANT EXECUTE ON FUNCTION credit_mark_paid(TEXT) TO bgl_app;

-- The AI's own SQL must never reach billing data.
REVOKE ALL ON ai_usage, credit_purchases FROM bgl_ai, bgl_ai_owner;

COMMIT;
