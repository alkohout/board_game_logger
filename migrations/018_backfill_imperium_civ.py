"""018 — Read the Imperium deck faced out of the old free text.

Plays were written as "Imperator. Romans (me) vs Atlanteans (bot)." and the
stats page dug the opponent out of that string every time it loaded. This
lifts it into the column 017 added, so the page reads a field instead of
parsing prose.

Two things it fixes on the way:

  * Singular spellings. Eleven plays say "Viking", "Greek" or "Carthaginian",
    and exact matching dropped every one of them.
  * Ambiguity about who is who. Anything after "vs"/"versus" is the opponent;
    what comes before it is you. Romans isn't a listed civilisation anyway, so
    "Romans (me)" was never at risk, but the rule holds if that ever changes.

Only fills a blank, so re-running never overwrites a correction made by hand.
Everything it changes is printed, and anything it can't read is printed too.

    ./venv/bin/python migrations/018_backfill_imperium_civ.py [--apply]

Without --apply it is a dry run and writes nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Migrations connect as the owning role, not the app role, or RLS hides the
# very rows we are here to fix.
os.environ.pop('DB_USER', None)

import flask_web_interface as f  # noqa: E402

APPLY = '--apply' in sys.argv


def main():
    conn = f.raw_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.user_id', %s, false)",
                (os.environ.get('BACKFILL_USER_ID', '1'),))

    cur.execute("""SELECT id, date_played, level, result, civilisation
                   FROM games
                   WHERE game_title ILIKE '%%imperium%%'
                   ORDER BY date_played, id""")
    rows = cur.fetchall()

    changed = blank = unreadable = 0
    for gid, played, level, result, civ in rows:
        if civ:
            continue
        text = ' '.join(x for x in (level, result) if x)
        if not text.strip():
            blank += 1
            continue
        found = f.imperium_civ_from_text(text)
        if not found:
            unreadable += 1
            print(f'  no deck found  {played}  {text.strip()[:66]!r}')
            continue
        changed += 1
        print(f'  {played}  {found:<16} <- {text.strip()[:56]!r}')
        if APPLY:
            cur.execute("UPDATE games SET civilisation = %s WHERE id = %s",
                        (found, gid))

    if APPLY:
        conn.commit()
    cur.close()
    conn.close()

    print(f'\n  {len(rows)} Imperium plays: {changed} given a deck, '
          f'{unreadable} with text naming none, {blank} with nothing recorded')
    if not APPLY:
        print('  dry run — nothing written. Re-run with --apply.')


if __name__ == '__main__':
    main()
