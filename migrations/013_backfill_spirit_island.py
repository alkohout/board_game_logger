"""013 — Read the existing Spirit Island plays into the new columns.

Nine plays recorded what was played, in free text, in `level` — sometimes a
scenario, sometimes an adversary, sometimes a spirit — and a few name the
spirit only in `notes`. This lifts what is unambiguous into the columns 012
added, so the stats page opens with real history instead of zeros.

Deliberately conservative:

  * `level` is read for spirits, adversaries and scenarios.
  * `notes` is read for spirits ONLY. Notes are written forward-looking —
    "Onto next scenario - Dahan insurrection" describes the NEXT game, so
    harvesting scenarios from them files plays under the wrong one.
  * Only columns that are still NULL are filled, so re-running never
    overwrites anything corrected by hand afterwards.

Everything it changes is printed. Anything it can't match is printed too,
rather than passed over in silence.

    ./venv/bin/python migrations/013_backfill_spirit_island.py [--apply]

Without --apply it is a dry run and writes nothing.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Migrations connect as the owning role, not the app role, or RLS hides the
# very rows we are here to fix.
os.environ.pop('DB_USER', None)

import flask_web_interface as f  # noqa: E402

APPLY = '--apply' in sys.argv


def norm(text):
    """Lowercase, apostrophes dropped, everything else non-alphanumeric to space.

    Dropping apostrophes rather than spacing them is what makes the logged
    "Guard the isles heart" meet the official "Guard the Isle's Heart".
    """
    text = (text or '').replace("'", '').replace('’', '')
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text.lower()).split())


# Shorthand actually used in the old notes. Kept here rather than in the app,
# because these are one person's abbreviations in historic free text, not
# official names — new plays are picked from a list and need none of this.
ALIASES = [
    ('flickering shadow',    'Shadows Flicker Like Flame'),
    ('shadows flicker',      'Shadows Flicker Like Flame'),
    ('bringer of nightmares', 'Bringer of Dreams and Nightmares'),
    ('rampant green',        'A Spread of Rampant Green'),
    ('river surge',          'River Surges in Sunlight'),
    ('vital strength',       'Vital Strength of the Earth'),
    ('oceans hungry grasp',  "Ocean's Hungry Grasp"),
    ('lightnings swift strike', "Lightning's Swift Strike"),
    ('brandenburg',          'Brandenburg-Prussia'),
    ('guard the isles heart', "Guard the Isle's Heart"),
    ('dahan insurrection',   'Dahan Insurrection'),
]


def find(haystack, entries):
    """Earliest mention wins; longest breaks a tie at the same position.

    Both halves earn their keep. Earliest, because a note reading "Played
    thunderspeaker. Next bringer of dreams and nightmares" names the spirit
    played first and the one intended next — longest-wins picks the wrong one.
    Longest at equal position, because 'Habsburg Mining Expedition' and
    'Habsburg Monarchy' both start on the same word.
    """
    hay = norm(haystack)
    if not hay:
        return None
    official = {name for _, name in entries}
    candidates = [(name, name) for _, name in entries]
    # An alias only counts if it stands for something in this list, so spirit
    # shorthand can't leak into the adversary or scenario column.
    candidates += [(alias, name) for alias, name in ALIASES if name in official]

    hits = []
    for text, name in candidates:
        at = hay.find(norm(text))
        if at >= 0:
            hits.append((at, -len(norm(text)), name))
    return min(hits)[2] if hits else None


def main():
    conn = f.raw_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.user_id', %s, false)",
                (os.environ.get('BACKFILL_USER_ID', '1'),))

    cur.execute("""SELECT id, date_played, level, notes, result, spirit, adversary,
                          adversary_level, scenario
                   FROM games WHERE game_title ILIKE %s
                   ORDER BY date_played""", (f.SPIRIT_ISLAND_TITLE,))
    rows = cur.fetchall()

    changed = unmatched = 0
    prose_results = []
    for (gid, played, level, notes, result, spirit, adversary,
         adv_level, scenario) in rows:
        if not ((level or '') + (notes or '')).strip():
            continue

        # An outcome written only into the prose counts as neither won nor
        # lost. Worth reporting — but not worth guessing at, because "Lost on
        # blight" and "try not to lose next time" look alike to a substring.
        if not (result or '').strip():
            words = norm(f'{level} {notes}').split()
            if 'won' in words or 'win' in words or 'lost' in words:
                prose_results.append((played, (notes or level).strip()[:70]))

        # Only ever fill a blank; a value already there was put there on purpose.
        new_spirit = spirit or find(level, f.SPIRIT_ISLAND_SPIRITS) \
            or find(notes, f.SPIRIT_ISLAND_SPIRITS)
        new_adversary = adversary or find(level, f.SPIRIT_ISLAND_ADVERSARIES)
        new_scenario = scenario or find(level, f.SPIRIT_ISLAND_SCENARIOS)

        new_level = adv_level
        if new_adversary and new_level is None:
            found = f.ADVERSARY_LEVEL_RE.search(level or '')
            if found:
                new_level = int(found.group(1))

        updates = {'spirit': new_spirit, 'adversary': new_adversary,
                   'adversary_level': new_level, 'scenario': new_scenario}
        updates = {k: v for k, v in updates.items()
                   if v is not None and v != {'spirit': spirit, 'adversary': adversary,
                                              'adversary_level': adv_level,
                                              'scenario': scenario}[k]}
        if not updates:
            if (level or '').strip():
                unmatched += 1
                print(f'  no match  {played}  level={level.strip()!r}')
            continue

        changed += 1
        shown = ', '.join(f'{k}={v!r}' for k, v in updates.items())
        print(f'  {played}  {shown}')
        if APPLY:
            sets = ', '.join(f'{k} = %s' for k in updates)
            cur.execute(f'UPDATE games SET {sets} WHERE id = %s',
                        (*updates.values(), gid))

    if APPLY:
        conn.commit()
    cur.close()
    conn.close()

    print(f'\n  {len(rows)} Spirit Island plays, {changed} updated, '
          f'{unmatched} with text that matched nothing')

    if prose_results:
        print(f'\n  {len(prose_results)} plays state a result in the text but leave the'
              '\n  Result field empty, so they count as neither won nor lost:')
        for played, text in prose_results:
            print(f'    {played}  {text!r}')
        print('  Left alone — fix these in the app if the counts matter.')

    if not APPLY:
        print('  dry run — nothing written. Re-run with --apply.')


if __name__ == '__main__':
    main()
