"""No account can see or touch another's data, anywhere.

A condensed rebuild of the audit suite that was lost with /tmp. Two accounts
get a marker in every user-owned table, then every endpoint is called as each
and checked for the other's marker.
"""
import os, sys, io
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
PW = generate_password_hash('pw-for-tests')

def wipe():
    k.execute("SELECT id FROM users WHERE email LIKE 'zz-iso%'")
    for (uid,) in k.fetchall():
        for t in f.USER_OWNED_TABLES:
            k.execute(f"DELETE FROM {t} WHERE user_id=%s", (uid,))
    k.execute("DELETE FROM users WHERE email LIKE 'zz-iso%'")
    k.execute("DELETE FROM login_attempts")
    su.commit()
wipe()
k.execute("UPDATE users SET password_hash=%s WHERE is_owner", (PW,))
su.commit()
c = f.app.test_client()

def make(tag):
    k.execute("""INSERT INTO users (email, password_hash, status, is_owner, display_name)
                 VALUES (%s,%s,'active',false,%s) RETURNING id""",
              (f'zz-iso-{tag}@test.com', PW, f'iso{tag}'))
    uid = k.fetchone()[0]
    k.execute("""INSERT INTO games (user_id, date_played, game_title, notes, result, level)
                 VALUES (%s,'2026-07-01',%s,%s,'Won',%s) RETURNING id""",
              (uid, f'ZZ{tag} Spirit Island', f'note-{tag}', f'level-{tag}'))
    gid = k.fetchone()[0]
    k.execute("""INSERT INTO rulebooks (user_id, game_title, rulebook_name, rules_text)
                 VALUES (%s,%s,%s,%s)""", (uid, f'ZZ{tag} Game', f'rb-{tag}.pdf', f'text-{tag}'))
    k.execute("""INSERT INTO ai_usage (user_id, kind, cost_nzd, funded_by, input_tokens)
                 VALUES (%s,'db_query',0.05,'free',100)""", (uid,))
    k.execute("""INSERT INTO credit_purchases (user_id, amount_nzd, stripe_session_id, status)
                 VALUES (%s,5.00,%s,'paid')""", (uid, f'zz_iso_{tag}'))
    k.execute("""INSERT INTO sleeping_gods (user_id, location, notes, visited)
                 VALUES (%s,%s,%s,false) RETURNING id""", (uid, 400 + len(tag), f'sg-{tag}'))
    sg = k.fetchone()[0]
    k.execute("""INSERT INTO sleeping_gods_totems (user_id, totem, found)
                 VALUES (%s,%s,false) RETURNING id""", (uid, f'ZZ Totem {tag}'))
    totem = k.fetchone()[0]
    k.execute("""INSERT INTO game_photos (user_id, game_id, image, mime, byte_size)
                 VALUES (%s,%s,%s,'image/png',4) RETURNING id""",
              (uid, gid, psycopg2.Binary(b'\x89PNG')))
    photo = k.fetchone()[0]
    su.commit()
    tok = c.post('/api/login', json={'email': f'zz-iso-{tag}@test.com',
                                     'password': 'pw-for-tests'}).get_json()['token']
    return {'uid': uid, 'h': {'Authorization': 'Bearer ' + tok}, 'game': gid,
            'sg': sg, 'totem': totem, 'photo': photo, 'tag': tag}

A, B = make('A'), make('B')

GETS = ['/api/dashboard', '/api/recent_plays', '/api/all_games', '/api/games_overview',
        '/api/spirit_island_stats', '/api/imperium_stats', '/api/sleeping_gods_totems_data',
        '/api/rules_assistant_data', '/api/credit', '/api/me', '/api/ares_stats',
        '/api/ark_nova_stats', '/api/cascadia_stats',
        '/search_games?term=ZZ', '/search_last_played?term=ZZ', '/api/game_info?term=ZZ',
        '/search_sleeping_gods_notes?term=sg-']

print('NO ENDPOINT SHOWS ONE ACCOUNT ANOTHER\'S DATA')
leaks = []
for path in GETS:
    for me, them in ((A, B), (B, A)):
        body = c.get(path, headers=me['h']).get_data(as_text=True)
        if f'-{them["tag"]}' in body or f'ZZ{them["tag"]} ' in body:
            leaks.append((path, me['tag']))
check('every GET, both directions', leaks, [])

print('\nAND EACH SEES ITS OWN')
blind = [p for p in ('/api/all_games', '/search_games?term=ZZ') for me in (A, B)
         if f'ZZ{me["tag"]}' not in c.get(p, headers=me['h']).get_data(as_text=True)]
check('own data visible', blind, [])

print('\nWRITES CANNOT REACH ACROSS')
check('update_play', c.post('/api/update_play', headers=B['h'], json={
    'id': A['game'], 'date_played': '2000-01-01', 'result': 'HACKED'}).status_code, 404)
k.execute("SELECT result FROM games WHERE id=%s", (A['game'],))
check('  row untouched', k.fetchone()[0], 'Won')
c.post('/delete_sleeping_gods_row', headers=B['h'], json={'id': A['sg']})
k.execute("SELECT count(*) FROM sleeping_gods WHERE id=%s", (A['sg'],))
check('sleeping gods row survives', k.fetchone()[0], 1)
c.post('/sleeping_gods_totems_update', headers=B['h'], json={'totemId': A['totem'], 'isFound': True})
k.execute("SELECT found FROM sleeping_gods_totems WHERE id=%s", (A['totem'],))
check('totem not flipped', k.fetchone()[0], False)
check('photo not readable', c.get(f'/api/photos/{A["photo"]}', headers=B['h']).status_code, 404)
check('photo not deletable', c.delete(f'/api/photos/{A["photo"]}', headers=B['h']).status_code, 404)
check('cannot attach to their play',
      c.post(f'/api/games/{A["game"]}/photo', headers=B['h'],
             data={'photo': (io.BytesIO(b'\x89PNG'), 'p.png', 'image/png')},
             content_type='multipart/form-data').status_code, 404)

print('\nOWNER-ONLY STAYS OWNER-ONLY')
check('/api/users', c.get('/api/users', headers=A['h']).status_code, 403)
check('delete an account', c.delete(f'/api/users/{B["uid"]}', headers=A['h']).status_code, 403)
check('change a status',
      c.post(f'/api/users/{B["uid"]}/status', headers=A['h'], json={'status': 'disabled'}).status_code, 403)

print('\nNEW ROWS GET THE RIGHT OWNER')
r = c.post('/api/add_game', headers=B['h'],
           json={'date_played': '2026-07-09', 'game_title': 'ZZB Owner Check'}).get_json()
k.execute("SELECT user_id FROM games WHERE game_title='ZZB Owner Check'")
check('add_game stamps the caller', k.fetchone()[0], B['uid'])
check('  and returns the id', isinstance(r.get('id'), int), True)

print('\nDISABLED AND PENDING ACCOUNTS CANNOT ACT')
for status in ('disabled', 'pending'):
    k.execute("UPDATE users SET status=%s WHERE id=%s", (status, B['uid'])); su.commit()
    check(f'a {status} account is refused',
          c.get('/api/dashboard', headers=B['h']).status_code, 401)
k.execute("UPDATE users SET status='active' WHERE id=%s", (B['uid'],)); su.commit()

print('\nLOGGED OUT IS REFUSED')
for path in ('/api/dashboard', '/api/me', '/api/game_info?term=ZZ',
             f'/api/photos/{A["photo"]}'):
    check(f'  {path.split("?")[0]}', c.get(path).status_code, 401)

print('\nEVERY OWNED TABLE IS ACTUALLY SECURED')
for table in f.USER_OWNED_TABLES:
    k.execute("""SELECT relrowsecurity, relforcerowsecurity FROM pg_class
                 WHERE relname=%s""", (table,))
    check(f'  {table}', k.fetchone(), (True, True))
k.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname='bgl_app'")
check('the app role cannot bypass it', k.fetchone()[0], False)

print('\nDELETING AN ACCOUNT CLEARS EVERYTHING IT OWNED')
OWNER_H = {'Authorization': 'Bearer ' + c.post('/api/login',
           json={'email': 'owner@example.com', 'password': 'pw-for-tests'}).get_json()['token']}
c.delete(f'/api/users/{B["uid"]}', headers=OWNER_H)
orphans = []
for table in f.USER_OWNED_TABLES:
    k.execute(f"SELECT count(*) FROM {table} WHERE user_id=%s", (B['uid'],))
    if k.fetchone()[0]:
        orphans.append(table)
check('no orphaned rows', orphans, [])
k.execute("SELECT count(*) FROM games WHERE user_id=%s", (A['uid'],))
check('  and the other account keeps its own', k.fetchone()[0], 1)

wipe()
k.close(); su.close()
print(f'\n{ok} passed, {fail} failed')
