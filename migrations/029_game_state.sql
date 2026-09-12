-- 029 — Somewhere to keep a game in progress.
--
-- The Ark Nova board takes the whole table, so the plan is to leave the cards,
-- the zoo map and the conservation board out and let a page stand in for the
-- big shared board. That page needs its state to survive closing a tab, and to
-- follow you from the phone at the table to a laptop later, so it lives here
-- rather than in one browser's storage.
--
-- jsonb rather than a column per counter: this is the state of a play aid, not
-- something to be reported on. Its shape will change as the page does, and a
-- migration per counter would be silly. Anything worth analysing later gets
-- logged as a play, which is typed properly.
--
-- One row per account per game.
--
--   ./venv/bin/python migrations/run_sql.py migrations/029_game_state.sql
--
-- Safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS game_state (
    id         serial PRIMARY KEY,
    user_id    integer NOT NULL
               DEFAULT (NULLIF(current_setting('app.user_id', true), ''))::integer,
    game_key   varchar(40) NOT NULL,
    state      jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, game_key)
);

ALTER TABLE game_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_state FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS game_state_owner_only ON game_state;
CREATE POLICY game_state_owner_only ON game_state
    USING      (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer)
    WITH CHECK (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer);

GRANT SELECT, INSERT, UPDATE, DELETE ON game_state TO bgl_app;
GRANT USAGE, SELECT ON SEQUENCE game_state_id_seq TO bgl_app;
REVOKE ALL ON game_state FROM bgl_ai, bgl_ai_owner;

COMMIT;
