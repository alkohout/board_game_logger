"""023 — Lift difficulty and scenario number out of `level`.

`level` held a bare difficulty word for some games — "Expert", "Normal" — and
a ladder rung for others: "Scenario 4 (All D cards)". Both now have columns.

The original `level` text is left exactly as it was. It is the record of what
was written at the time, and some of it carries more than these two fields do
("All D cards" is the scoring-card variant, which has no field yet).

    ./venv/bin/python migrations/023_backfill_difficulty_scenario.py [--apply]

Without --apply it is a dry run. Only fills blanks, so re-running is safe.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop('DB_USER', None)

import flask_web_interface as f  # noqa: E402

APPLY = '--apply' in sys.argv

# Only a level that is *nothing but* a difficulty word. "Expert" is a
# difficulty; "Imperator. Romans (me) vs Qin (bot)" is not, and a looser match
# would start finding words inside sentences.
DIFFICULTY_ONLY = re.compile(
    r'^(very\s+)?(easy|normal|medium|hard|expert|beginner|standard|advanced|nightmare)\.?$',
    re.I)
SCENARIO_RE = re.compile(r'\bscenario\s*(\d{1,3})\b', re.I)


def main():
    conn = f.raw_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.user_id', %s, false)",
                (os.environ.get('BACKFILL_USER_ID', '1'),))
    cur.execute("""SELECT id, date_played, game_title, level, difficulty, scenario_number
                   FROM games
                   WHERE coalesce(btrim(level), '') NOT IN ('', 'null')
                   ORDER BY date_played, id""")
    rows = cur.fetchall()

    difficulty = scenario = 0
    for gid, played, title, level, have_diff, have_scen in rows:
        text = (level or '').strip()
        updates = {}
        if not have_diff:
            found = DIFFICULTY_ONLY.match(text)
            if found:
                # Stored as written, capitalised: Expert, not EXPERT or expert.
                updates['difficulty'] = text.rstrip('.').strip().title()
        if have_scen is None:
            found = SCENARIO_RE.search(text)
            if found and 1 <= int(found.group(1)) <= 999:
                updates['scenario_number'] = int(found.group(1))
        if not updates:
            continue
        difficulty += 'difficulty' in updates
        scenario += 'scenario_number' in updates
        shown = ', '.join(f'{k}={v!r}' for k, v in updates.items())
        print(f'  {played}  {title[:22]:<22} {shown:<34} <- {text[:30]!r}')
        if APPLY:
            sets = ', '.join(f'{k} = %s' for k in updates)
            cur.execute(f'UPDATE games SET {sets} WHERE id = %s',
                        (*updates.values(), gid))

    if APPLY:
        conn.commit()
    cur.close()
    conn.close()
    print(f'\n  {difficulty} difficulties and {scenario} scenario numbers found '
          f'across {len(rows)} sittings with a level')
    if not APPLY:
        print('  dry run — nothing written. Re-run with --apply.')


if __name__ == '__main__':
    main()
