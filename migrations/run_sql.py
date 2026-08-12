#!/usr/bin/env python
"""Run a .sql migration without needing the psql client installed.

Uses the same connection settings as the app, so it picks up .env exactly
like the Python migrations do.

    cd /opt/board_game_logger
    ./venv/bin/python migrations/run_sql.py migrations/001_accounts.sql

Run migrations before switching .env to DB_USER=bgl_app — creating roles and
tables needs the superuser.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask_web_interface as app                # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: run_sql.py <file.sql>')
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit(f'no such file: {path}')

    sql_text = open(path).read()
    conn = app.raw_db_connection()
    # The files carry their own BEGIN/COMMIT, so don't wrap them in another.
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql_text)
    except Exception as e:
        cur.close()
        conn.close()
        sys.exit(f'{path} failed:\n  {e}')
    cur.close()
    conn.close()
    print(f'{path} applied.')


if __name__ == '__main__':
    main()
