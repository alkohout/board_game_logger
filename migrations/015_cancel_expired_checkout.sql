-- 015 — Let the Stripe webhook cancel an expired checkout.
--
-- The webhook has no logged-in caller, so its connection carries no
-- app.user_id, and credit_purchases has FORCE row-level security. The
-- expired-session handler's UPDATE therefore matched zero rows and every
-- abandoned checkout stayed 'pending' forever. Nothing was mis-credited —
-- the paid path already goes through credit_mark_paid, which is
-- SECURITY DEFINER — but the ledger slowly filled with stale pending rows.
--
-- Same fix as the paid path: a SECURITY DEFINER function, so the policy is
-- satisfied by the function's owner rather than by disabling RLS. It only ever
-- touches a row identified by a Stripe session id, and only one that is still
-- pending, so a replayed webhook is a no-op.
--
--   ./venv/bin/python migrations/run_sql.py migrations/015_cancel_expired_checkout.sql
--
-- Safe to re-run.

BEGIN;

CREATE OR REPLACE FUNCTION credit_mark_cancelled(p_session_id text)
RETURNS TABLE (id integer, user_id integer)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE credit_purchases
    SET status = 'cancelled'
    WHERE stripe_session_id = p_session_id
      AND status = 'pending'
    RETURNING credit_purchases.id, credit_purchases.user_id;
$$;

REVOKE ALL ON FUNCTION credit_mark_cancelled(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION credit_mark_cancelled(text) TO bgl_app;

COMMIT;
