"""Ark Nova: map and starting appeal, and which way the ladder runs.

Lower starting appeal is harder — the official solo rules set 20 as easy, 10
as normal and 0 as "a challenge". This was built backwards first time, so the
direction is pinned here rather than left to be re-derived.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import dotenv_values
SUPER_PW = dotenv_values('.env').get('PASSWORD', '')
os.environ.update(SECRET_KEY='k', DB_USER='bgl_app', PASSWORD='local-test-pw',
                  ANTHROPIC_API_KEY='stub')
import psycopg2, flask_web_interface as f
f.app.secret_key = 'k'

ok = fail = 0
def check(label, got, want):
    global ok, fail
    good = got == want
    ok, fail = ok + good, fail + (not good)
    print(f'  {"ok  " if good else "FAIL"} {label}: {got}' + ('' if good else f'  (expected {want})'))

su = psycopg2.connect(host='localhost', database='boardgames', user='postgres', password=SUPER_PW)
k = su.cursor()
from werkzeug.security import generate_password_hash
k.execute("UPDATE users SET password_hash=%s WHERE is_owner", (generate_password_hash('pw-for-tests'),))
k.execute("DELETE FROM login_attempts")
k.execute("DELETE FROM games WHERE game_title LIKE 'ZZan%'")
su.commit()
c = f.app.test_client()
H = {'Authorization': 'Bearer ' + c.post('/api/login',
     json={'email': 'owner@example.com', 'password': 'pw-for-tests'}).get_json()['token']}

def grid():
    return c.get('/api/ark_nova_stats', headers=H).get_json()

print('READING THE OLD FREE TEXT')
T = f.ark_nova_from_text
check('comma form', T('Map 0, start 15'), ('0', 15))
check('full stops', T('Map A. Start 10.'), ('A', 10))
check('"started at"', T('Ooops. Started at 20.'), (None, 20))
check('a map that does not exist', T('Map Z, start 10'), (None, 10))

print('\nLOWER STARTING APPEAL IS HARDER')
d = grid()
check('the endpoint says so outright', d['harder_is'], 'lower')
check('  and names the official rungs',
      {int(k2): v for k2, v in d['appeal_names'].items()},
      {20: 'easy', 10: 'normal', 0: 'challenge'})

k.execute("DELETE FROM games WHERE game_title='ZZan Ark Nova'")
for appeal, res in ((20, 'Won'), (15, 'Won'), (10, 'Lost')):
    k.execute("""INSERT INTO games (user_id, date_played, game_title, zoo_map,
                                    start_appeal, result)
                 VALUES (1,'2026-09-01','ZZan Ark Nova','4',%s,%s)""", (appeal, res))
su.commit()
m4 = {m['map']: m for m in grid()['maps']}['4']
check('hardest beaten is the lowest appeal won, not the highest',
      m4['best_appeal'], 15)
check('  a loss at 10 does not count as beaten',
      {x['appeal']: (x['won'], x['lost']) for x in m4['cells']}[10], (0, 1))

# Winning the harder rung should move the marker down, not up.
k.execute("""INSERT INTO games (user_id, date_played, game_title, zoo_map,
                                start_appeal, result)
             VALUES (1,'2026-09-02','ZZan Ark Nova','4',10,'Won')""")
su.commit()
m4 = {m['map']: m for m in grid()['maps']}['4']
check('winning at 10 makes it the hardest beaten', m4['best_appeal'], 10)

print('\nTHE PAGE POINTS DOWNWARDS')
page = open('docs/ark_nova.html').read()
check('it offers a step down, not up', 'Next step down' in page, True)
check('  and no longer a rung up', 'Next rung up' in page, False)
check('  the caption says which way is harder', 'lower is harder' in page, True)
check('  and the columns carry the official names', 'rung-name' in page, True)

# The maths the page does for the next rung.
appeals = grid()['appeals']
def next_step_down(best):
    return next((a for a in sorted(appeals, reverse=True) if a < best), None)
check('below 15 is 10', next_step_down(15), 10)
check('below 10 is 5', next_step_down(10), 5)
check('below 0 is nothing left', next_step_down(0), None)

print('\nEVERY MAP IS STILL LISTED')
d = grid()
check('ten base maps', len(d['maps']), 10)
check('  map packs not offered',
      any(m['map'] in ('9', '10', '11') for m in d['maps']), False)

k.execute("DELETE FROM games WHERE game_title LIKE 'ZZan%'")
su.commit(); k.close(); su.close()
print(f'\n{ok} passed, {fail} failed')
