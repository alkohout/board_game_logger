#!/usr/bin/env python
"""Credit any top-up Stripe took payment for but the webhook never delivered.

A dropped or mis-signed webhook means real money taken and no credit given.
This asks Stripe directly about every purchase still sitting at 'pending' and
credits the ones it says are paid.

    ./venv/bin/python migrations/reconcile_stripe.py            # report only
    ./venv/bin/python migrations/reconcile_stripe.py --apply    # fix them

Safe to run any time; it only ever moves 'pending' to 'paid'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask_web_interface as app                # noqa: E402


def main():
    os.environ.pop('DB_USER', None)              # read every user's rows
    apply_changes = '--apply' in sys.argv

    if not app.stripe or not os.getenv('STRIPE_SECRET_KEY'):
        sys.exit('Stripe is not configured.')
    app.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    conn = app.raw_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.user_id, p.amount_nzd, p.stripe_session_id, u.email, p.created_at
        FROM credit_purchases p JOIN users u ON u.id = p.user_id
        WHERE p.status = 'pending' AND p.stripe_session_id IS NOT NULL
        ORDER BY p.created_at
    """)
    pending = cur.fetchall()
    if not pending:
        print('No pending top-ups.')
        return

    print(f'{len(pending)} pending top-up(s):\n')
    fixed = 0
    for pid, user_id, amount, session_id, email, created in pending:
        try:
            session = app.stripe.checkout.Session.retrieve(session_id)
        except Exception as e:
            print(f'  #{pid} {email} NZ${amount} — could not check: {e}')
            continue
        paid = session.get('payment_status') == 'paid'
        print(f'  #{pid} {email} NZ${amount} ({created:%Y-%m-%d %H:%M}) — Stripe says '
              f'{session.get("payment_status")}')
        if paid and apply_changes:
            cur.execute("SELECT * FROM credit_mark_paid(%s)", (session_id,))
            if cur.fetchone():
                conn.commit()
                fixed += 1
                print('       -> credited')
        elif paid:
            print('       -> would credit (re-run with --apply)')

    cur.close()
    conn.close()
    if apply_changes:
        print(f'\nCredited {fixed} purchase(s).')


if __name__ == '__main__':
    main()
