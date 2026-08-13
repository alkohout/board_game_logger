#!/usr/bin/env python
"""Create (or repair) the owner account.

The owner is the existing single user of the app — every play already in the
database belongs to them. Run this once after 001_accounts.sql:

    cd /opt/board_game_logger
    ./venv/bin/python migrations/seed_owner.py you@example.com

You'll be prompted for the initial password (or set APP_PASSWORD and it will
use that). Change it from the app's Account box afterwards.

Re-running is safe: it updates the email of the existing owner rather than
creating a second one.
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash   # noqa: E402
import flask_web_interface as app                      # noqa: E402


def main():
    # Migrations do DDL — create roles, alter tables, own views — so they must
    # connect as the database owner from DATABASE_URL, not as the restricted
    # app role. DB_USER is the app's override and does not apply here.
    os.environ.pop('DB_USER', None)

    if len(sys.argv) != 2:
        sys.exit('usage: seed_owner.py <email>')
    email = sys.argv[1].strip().lower()

    password = os.getenv('APP_PASSWORD')
    if not password:
        password = getpass.getpass(f'Initial password for {email}: ')
        if len(password) < 8:
            sys.exit('Password must be at least 8 characters.')

    conn = app.get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, email FROM users WHERE is_owner")
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE users SET email = %s WHERE id = %s", (email, existing[0]))
        conn.commit()
        print(f'Owner already existed (id {existing[0]}, was {existing[1]}) — email set to {email}.')
    else:
        cur.execute("""
            INSERT INTO users (email, password_hash, display_name, status, is_owner, approved_at)
            VALUES (%s, %s, %s, 'active', TRUE, now())
            RETURNING id
        """, (email, generate_password_hash(password), 'Owner'))
        owner_id = cur.fetchone()[0]
        conn.commit()
        print(f'Owner account created: id {owner_id}, {email}')
        print('Use the password you just set to log in, then change it in the app.')

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
