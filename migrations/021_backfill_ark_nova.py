"""021 — Read Ark Nova's map and starting appeal out of the old free text.

Logged as "Map 0, start 15" or "Map A. Start 10." in `level`, and sometimes
only in the notes — "Won map A, start 10 appeal". Both go into the columns 020
added.

`level` is read first and the notes only as a fallback, because the notes are
written forward-looking: "Try map 0. Start 10." on a play whose level says
"Map 0, start 15" is the plan for next time, not what was just played. Taking
the notes first would file every ladder step one rung out.

Only fills a blank, so re-running never overwrites a correction. Everything it
changes is printed.

    ./venv/bin/python migrations/021_backfill_ark_nova.py [--apply]

Without --apply it is a dry run and writes nothing.
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
    cur.execute("""SELECT id, date_played, level, notes, zoo_map, start_appeal
                   FROM games WHERE game_title ILIKE '%%ark nova%%'
                   ORDER BY date_played, id""")
    rows = cur.fetchall()

    changed = skipped = 0
    for gid, played, level, notes, zoo_map, appeal in rows:
        if zoo_map and appeal is not None:
            continue
        # The level is what was played; the notes usually say what to try next.
        from_level = f.ark_nova_from_text(level)
        from_notes = f.ark_nova_from_text(notes)
        new_map = zoo_map or from_level[0] or (from_notes[0] if not level else None)
        new_appeal = appeal if appeal is not None else (
            from_level[1] if from_level[1] is not None
            else (from_notes[1] if not level else None))

        updates = {}
        if new_map and new_map != zoo_map:
            updates['zoo_map'] = new_map
        if new_appeal is not None and new_appeal != appeal:
            updates['start_appeal'] = new_appeal
        if not updates:
            if (level or notes or '').strip():
                skipped += 1
            continue

        changed += 1
        shown = ', '.join(f'{k}={v!r}' for k, v in updates.items())
        source = (level or notes or '').strip()[:46]
        print(f'  {played}  {shown:<34} <- {source!r}')
        if APPLY:
            sets = ', '.join(f'{k} = %s' for k in updates)
            cur.execute(f'UPDATE games SET {sets} WHERE id = %s',
                        (*updates.values(), gid))

    if APPLY:
        conn.commit()
    cur.close()
    conn.close()
    print(f'\n  {len(rows)} Ark Nova sittings: {changed} given a map or appeal, '
          f'{skipped} with text naming neither')
    if not APPLY:
        print('  dry run — nothing written. Re-run with --apply.')


if __name__ == '__main__':
    main()
