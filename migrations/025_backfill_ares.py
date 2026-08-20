"""025 — Lift the Ares Expedition end state out of the score fields.

Finished games recorded temperature, oxygen and oceans as prose in my_score
and bot_score — "8 C, 13 %, 9 ocean Tiles" — sometimes with megacredits. Those
now have columns.

The original score text is left as written. It occasionally says more than the
columns hold, and it is the record of what was actually typed.

    ./venv/bin/python migrations/025_backfill_ares.py [--apply]

Dry run without --apply. Only fills blanks, so re-running is safe.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop('DB_USER', None)

import flask_web_interface as f  # noqa: E402

APPLY = '--apply' in sys.argv


def main():
    conn = f.raw_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.user_id', %s, false)",
                (os.environ.get('BACKFILL_USER_ID', '1'),))
    cols = [f'ares_{k}_{side}' for side in ('me', 'bot') for k in f.ARES_FIELDS]
    cur.execute(f"""SELECT id, date_played, my_score, bot_score, {', '.join(cols)}
                    FROM games WHERE game_title ILIKE %s
                    ORDER BY date_played, id""", (f.ARES_MATCH,))
    rows = cur.fetchall()

    changed = partial = 0
    for row in rows:
        gid, played, my_score, bot_score = row[:4]
        existing = dict(zip(cols, row[4:]))
        updates = {}
        for side, text in (('me', my_score), ('bot', bot_score)):
            for key, value in f.ares_from_text(text).items():
                column = f'ares_{key}_{side}'
                if existing[column] is None:
                    updates[column] = value
        if not updates:
            continue
        changed += 1
        # A row where the text named some but not all three is worth seeing.
        got_me = [k for k in ('temp', 'oxygen', 'oceans')
                  if updates.get(f'ares_{k}_me') is not None
                  or existing[f'ares_{k}_me'] is not None]
        if (my_score or '').strip() and len(got_me) < 3:
            partial += 1
            print(f'  {played}  PARTIAL me={got_me}  <- {(my_score or "").strip()[:34]!r}')
        else:
            shown = ' '.join(f'{k.split("_",1)[1]}={v}' for k, v in sorted(updates.items()))
            print(f'  {played}  {shown}')
        if APPLY:
            sets = ', '.join(f'{k} = %s' for k in updates)
            cur.execute(f'UPDATE games SET {sets} WHERE id = %s',
                        (*updates.values(), gid))

    if APPLY:
        conn.commit()
    cur.close()
    conn.close()
    print(f'\n  {len(rows)} Ares sittings: {changed} given numbers, '
          f'{partial} where the text named only some of them')
    if not APPLY:
        print('  dry run — nothing written. Re-run with --apply.')


if __name__ == '__main__':
    main()
