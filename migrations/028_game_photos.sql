-- 028 — A photo of the table, attached to a sitting.
--
-- Games get left set up part-way through, which is why a row is a sitting
-- rather than a game. A picture of the board is the natural companion to
-- "Bots turn": it's the state you're coming back to.
--
-- Its own table rather than a column on games, because a sitting can want more
-- than one shot — the board, and your hand — and because a photo is big enough
-- that you don't want it loaded every time a play is read.
--
-- bytea, not base64 text like rulebooks: base64 costs a third more space, and
-- photos are the bulkier thing by far.
--
--   ./venv/bin/python migrations/run_sql.py migrations/028_game_photos.sql
--
-- Safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS game_photos (
    id          serial PRIMARY KEY,
    user_id     integer NOT NULL
                DEFAULT (NULLIF(current_setting('app.user_id', true), ''))::integer,
    game_id     integer NOT NULL,
    image       bytea   NOT NULL,
    mime        varchar(40) NOT NULL DEFAULT 'image/jpeg',
    byte_size   integer NOT NULL,
    caption     varchar(200),
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS game_photos_game_idx ON game_photos (game_id);
CREATE INDEX IF NOT EXISTS game_photos_user_idx ON game_photos (user_id);

ALTER TABLE game_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_photos FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS game_photos_owner_only ON game_photos;
CREATE POLICY game_photos_owner_only ON game_photos
    USING      (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer)
    WITH CHECK (user_id = (NULLIF(current_setting('app.user_id', true), ''))::integer);

GRANT SELECT, INSERT, UPDATE, DELETE ON game_photos TO bgl_app;
GRANT USAGE, SELECT ON SEQUENCE game_photos_id_seq TO bgl_app;

-- The AI writes SQL against a restricted role; it has no business reading
-- image bytes, and a photo table would only bloat its schema description.
REVOKE ALL ON game_photos FROM bgl_ai, bgl_ai_owner;

COMMIT;
