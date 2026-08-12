#!/usr/bin/env python
"""002 — Data ownership and row-level security.

Gives every play and rulebook an owner, then makes Postgres itself enforce
that owners only ever see their own rows.

Why RLS rather than adding WHERE clauses to 65 queries: a forgotten filter
would silently return someone else's data, and the Database Query (AI)
endpoint runs SQL the *model* writes, which no amount of application-side
filtering can constrain. With RLS the database refuses the rows, so the worst
case is an empty result instead of a leak.

Three pieces:

  1. user_id on games and rulebooks, backfilled to the owner, NOT NULL, with
     a DEFAULT that reads the per-request setting — so INSERTs need no code
     change and can't accidentally write an unowned row.
  2. Two non-superuser roles. bgl_app runs the app; bgl_ai runs the AI's
     generated SQL and has SELECT on the data tables only — it cannot read
     the users table at all, so a creative query can't reach password hashes.
  3. RLS policies keyed to current_setting('app.user_id').

Superusers bypass RLS, which is why the app must stop connecting as postgres.

    cd /opt/board_game_logger
    BGL_DB_PASSWORD='pick-a-strong-one' ./venv/bin/python migrations/002_ownership.py

Take a backup first. Re-running is safe.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2                                  # noqa: E402
from psycopg2 import sql                         # noqa: E402
import flask_web_interface as app                # noqa: E402

OWNED_TABLES = ('games', 'rulebooks')


def main():
    db_password = os.getenv('BGL_DB_PASSWORD')
    if not db_password:
        sys.exit('Set BGL_DB_PASSWORD to the password you want the app role to use.')

    conn = app.get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id, email FROM users WHERE is_owner")
    owner = cur.fetchone()
    if not owner:
        sys.exit('No owner account — run 001_accounts.sql and seed_owner.py first.')
    owner_id, owner_email = owner
    print(f'Owner is {owner_email} (id {owner_id}).')

    # ── 1. Ownership column ───────────────────────────────────────────────
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = ANY(%s)
    """, (list(OWNED_TABLES),))
    present = [r[0] for r in cur.fetchall()]
    for missing in set(OWNED_TABLES) - set(present):
        print(f'  {missing}: not in this database, skipping')

    for table in present:
        cur.execute(sql.SQL("""
            ALTER TABLE {} ADD COLUMN IF NOT EXISTS user_id INTEGER
        """).format(sql.Identifier(table)))
        cur.execute(sql.SQL("UPDATE {} SET user_id = %s WHERE user_id IS NULL")
                    .format(sql.Identifier(table)), (owner_id,))
        print(f'  {table}: {cur.rowcount} existing rows assigned to the owner')

        # Reads the per-request setting, so an INSERT that forgets user_id
        # gets the right owner instead of a NULL.
        cur.execute(sql.SQL("""
            ALTER TABLE {} ALTER COLUMN user_id
            SET DEFAULT nullif(current_setting('app.user_id', true), '')::integer
        """).format(sql.Identifier(table)))
        cur.execute(sql.SQL("ALTER TABLE {} ALTER COLUMN user_id SET NOT NULL")
                    .format(sql.Identifier(table)))
        cur.execute(sql.SQL("""
            DO $$ BEGIN
                ALTER TABLE {tbl} ADD CONSTRAINT {con}
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
            EXCEPTION WHEN duplicate_object THEN NULL; END $$
        """).format(tbl=sql.Identifier(table),
                    con=sql.Identifier(f'{table}_user_id_fkey')))
        cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (user_id)")
                    .format(sql.Identifier(f'{table}_user_id_idx'), sql.Identifier(table)))

    # ── 2. Roles ──────────────────────────────────────────────────────────
    # bgl_ai      — everyone's AI queries: the games table only, RLS-scoped.
    # bgl_ai_owner— the owner's AI queries: also the single-user campaign
    #               trackers, which have no owner column and stay the owner's.
    for role in ('bgl_app', 'bgl_ai', 'bgl_ai_owner'):
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        if cur.fetchone():
            print(f'  role {role} already exists')
        else:
            cur.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role)))
            print(f'  role {role} created')
    # bgl_ai has no password: it is only ever reached via SET ROLE, never a login.
    cur.execute(sql.SQL("ALTER ROLE bgl_app PASSWORD {}").format(sql.Literal(db_password)))
    cur.execute("ALTER ROLE bgl_ai NOLOGIN")
    cur.execute("ALTER ROLE bgl_ai_owner NOLOGIN")

    cur.execute("SELECT current_database()")
    dbname = cur.fetchone()[0]
    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO bgl_app")
                .format(sql.Identifier(dbname)))
    cur.execute("GRANT USAGE ON SCHEMA public TO bgl_app, bgl_ai")

    # The app can work with everything; the AI role only reads game data.
    cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bgl_app")
    cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bgl_app")
    cur.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM bgl_ai, bgl_ai_owner")
    cur.execute("GRANT USAGE ON SCHEMA public TO bgl_ai_owner")
    if 'games' in present:
        cur.execute("GRANT SELECT ON games TO bgl_ai, bgl_ai_owner")
    # Campaign trackers: owner's AI queries only. They have no user_id, so
    # granting them to the shared AI role would expose them to every account.
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('imperium', 'sleeping_gods', 'sleeping_gods_totems')
    """)
    for (table,) in cur.fetchall():
        cur.execute(sql.SQL("GRANT SELECT ON {} TO bgl_ai_owner").format(sql.Identifier(table)))
    # So the app can hand either role over mid-transaction.
    cur.execute("GRANT bgl_ai, bgl_ai_owner TO bgl_app")

    # ── 3. Row-level security ─────────────────────────────────────────────
    for table in present:
        cur.execute(sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY")
                    .format(sql.Identifier(table)))
        # FORCE so the policy still applies if the table owner ever queries it.
        cur.execute(sql.SQL("ALTER TABLE {} FORCE ROW LEVEL SECURITY")
                    .format(sql.Identifier(table)))
        cur.execute(sql.SQL("DROP POLICY IF EXISTS {} ON {}")
                    .format(sql.Identifier(f'{table}_owner_only'), sql.Identifier(table)))
        cur.execute(sql.SQL("""
            CREATE POLICY {} ON {}
            USING      (user_id = nullif(current_setting('app.user_id', true), '')::integer)
            WITH CHECK (user_id = nullif(current_setting('app.user_id', true), '')::integer)
        """).format(sql.Identifier(f'{table}_owner_only'), sql.Identifier(table)))
        print(f'  {table}: row-level security on')

    conn.commit()
    cur.close()
    conn.close()

    print()
    print('Done. Point the app at the new role by setting these in .env:')
    print('    DB_USER=bgl_app')
    print("    PASSWORD=<the BGL_DB_PASSWORD you just used>")
    print('Then restart the service. Until you do, the app connects as a')
    print('superuser and superusers bypass RLS — the isolation is not active.')


if __name__ == '__main__':
    main()
