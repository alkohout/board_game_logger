#!/usr/bin/env python
"""006 — Pull the text out of rulebooks already uploaded.

New uploads extract text as they arrive. This does the same for the books
that were stored before that existed, so questions stop shipping every page
as an image.

    cd /opt/board_game_logger
    ./venv/bin/pip install -r requirements.txt      # needs pypdf
    ./venv/bin/python migrations/006_extract_rulebook_text.py

Books that are genuinely scanned images extract nothing; those keep going as
pages and are listed at the end. Re-running only touches books with no text
yet — pass --force to redo them all.
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask_web_interface as app                # noqa: E402


def main():
    # DDL and cross-user reads: connect as the database owner, not the app role.
    os.environ.pop('DB_USER', None)
    force = '--force' in sys.argv

    if app.PdfReader is None:
        sys.exit('pypdf is not installed — run: ./venv/bin/pip install -r requirements.txt')

    conn = app.raw_db_connection()
    cur = conn.cursor()
    where = '' if force else "AND (rules_text IS NULL OR rules_text = '' OR page_count IS NULL)"
    cur.execute(f"""
        SELECT game_title, rulebook_name, pdf_data
        FROM rulebooks WHERE pdf_data IS NOT NULL {where}
        ORDER BY game_title, rulebook_name
    """)
    rows = cur.fetchall()
    if not rows:
        print('Nothing to do — every rulebook already has text.')
        return

    print(f'{len(rows)} rulebook(s) to process\n')
    no_text = []
    for game, name, b64 in rows:
        raw = base64.b64decode(b64)
        text = app.extract_pdf_text(raw)
        cur.execute("""
            UPDATE rulebooks SET rules_text = %s, page_count = %s
            WHERE game_title = %s AND rulebook_name = %s
        """, (text or None, app.count_pdf_pages(raw), game, name))
        conn.commit()
        label = f'{game} / {name or "Rulebook"}'
        if text:
            print(f'  {label:<44} {len(text):>8,} characters')
        else:
            print(f'  {label:<44} {"no text":>8}')
            no_text.append(label)

    cur.close()
    conn.close()
    print()
    if no_text:
        print('These are image-only and will still be sent as pages:')
        for label in no_text:
            print(f'  - {label}')
    print('Done.')


if __name__ == '__main__':
    main()
