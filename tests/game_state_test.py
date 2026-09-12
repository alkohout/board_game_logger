"""Saved game state: kept, resumed, and never another account's."""
import re
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
PW = generate_password_hash('pw-for-tests')
k.execute("UPDATE users SET password_hash=%s WHERE is_owner", (PW,))
k.execute("DELETE FROM login_attempts")
k.execute("DELETE FROM game_state WHERE game_key LIKE 'zz%'")
k.execute("DELETE FROM users WHERE email LIKE 'zz-gs%'")
su.commit()
c = f.app.test_client()
H = {'Authorization': 'Bearer ' + c.post('/api/login',
     json={'email': 'owner@example.com', 'password': 'pw-for-tests'}).get_json()['token']}

print('SAVING AND RESUMING')
check('nothing saved yet', c.get('/api/game_state/zztest', headers=H).get_json()['state'], None)
mid = {'appeal': 34, 'conservation': 11, 'breaks': 7, 'workers': [True, False, False, False, False]}
check('saved', c.post('/api/game_state/zztest', headers=H, json={'state': mid}).get_json()['success'], True)
d = c.get('/api/game_state/zztest', headers=H).get_json()
check('  comes back intact', d['state'], mid)
check('  with a timestamp', bool(d['updated']), True)

print('\nSAVING AGAIN REPLACES, RATHER THAN PILING UP')
c.post('/api/game_state/zztest', headers=H, json={'state': {**mid, 'appeal': 40}})
check('latest wins', c.get('/api/game_state/zztest', headers=H).get_json()['state']['appeal'], 40)
k.execute("SELECT count(*) FROM game_state WHERE game_key='zztest'")
check('  still one row', k.fetchone()[0], 1)

print('\nSEPARATE GAMES DO NOT COLLIDE')
c.post('/api/game_state/zzother', headers=H, json={'state': {'appeal': 1}})
check('each key its own', c.get('/api/game_state/zztest', headers=H).get_json()['state']['appeal'], 40)

print('\nWHAT IT REFUSES')
check('a non-object state',
      c.post('/api/game_state/zztest', headers=H, json={'state': 'nope'}).status_code, 400)
check('  and does not overwrite with it',
      c.get('/api/game_state/zztest', headers=H).get_json()['state']['appeal'], 40)
big = {'junk': 'x' * (f.GAME_STATE_MAX_BYTES + 100)}
check('one that is too large',
      c.post('/api/game_state/zztest', headers=H, json={'state': big}).status_code, 413)
check('needs a login', c.get('/api/game_state/zztest').status_code, 401)

print('\nCLEARING')
check('deleted', c.delete('/api/game_state/zztest', headers=H).get_json()['success'], True)
check('  gone', c.get('/api/game_state/zztest', headers=H).get_json()['state'], None)

print('\nONE ACCOUNT CANNOT SEE ANOTHER\'S GAME')
k.execute("""INSERT INTO users (email, password_hash, status, is_owner, display_name)
             VALUES ('zz-gs@test.com',%s,'active',false,'gs') RETURNING id""", (PW,))
other = k.fetchone()[0]; su.commit()
H2 = {'Authorization': 'Bearer ' + c.post('/api/login',
      json={'email': 'zz-gs@test.com', 'password': 'pw-for-tests'}).get_json()['token']}
c.post('/api/game_state/zzother', headers=H2, json={'state': {'appeal': 99}})
check('same key, different account, different game',
      c.get('/api/game_state/zzother', headers=H).get_json()['state']['appeal'], 1)
check('  and theirs is theirs',
      c.get('/api/game_state/zzother', headers=H2).get_json()['state']['appeal'], 99)
check('deleting theirs leaves yours',
      (c.delete('/api/game_state/zzother', headers=H2),
       c.get('/api/game_state/zzother', headers=H).get_json()['state']['appeal'])[1], 1)

print('\nSECURED LIKE EVERYTHING ELSE')
check('in the owned tables list', 'game_state' in f.USER_OWNED_TABLES, True)
k.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='game_state'")
check('  rls enabled and forced', k.fetchone(), (True, True))
c.post('/api/game_state/zzdoomed', headers=H2, json={'state': {'a': 1}})
c.delete(f'/api/users/{other}', headers=H)
k.execute("SELECT count(*) FROM game_state WHERE user_id=%s", (other,))
check('deleting the account clears its saved games', k.fetchone()[0], 0)

print('\nTHE BOARD PAGE TRACKS ONLY THE THREE MARKERS')
page = open('docs/ark_nova_board.html').read()
check('appeal, conservation and reputation', 
      all(f"stepper('{x}'" in page for x in ('appeal', 'conservation', 'reputation')), True)
# 'breaks' on its own now appears in the break-step wording, so these name
# the state and controls that would mean the page was tracking them.
for gone in ('st.breaks', 'botAppeal', 'st.workers', 'data-worker'):
    check(f'  no {gone}', gone in page, False)
check('  and no stepper for the break track', "stepper('breaks'" in page, False)

print('\nTHE BOARD REFERENCE IS COPIED, NOT GUESSED')
check('there is an editor for it', 'ref-editor' in page, True)
check('  covering all four tables',
      all(f"key: '{x}'" in page for x in ('appeal', 'conservation', 'reputation', 'rounds')), True)
check('  appeal 7 pays 11, as the rulebook states', "at: 7, text: '11'" in page, True)
# The income bands were read off the board photo rather than the rulebook, so
# the check that matters is that they tile the track: every appeal 0-113 lands
# in exactly one band, and the incomes run 5 to 37 with none missing or twice.
bands = sorted((int(a), int(t)) for a, t in
               re.findall(r"\{ at: (\d+), text: '(\d+)' \}", page))
check('  income bands run 5 to 37', [t for _, t in bands], list(range(5, 38)))
check('  covering appeal 0 to 113 exactly',
      sum((bands[i + 1][0] - 1 if i + 1 < len(bands) else 113) - a + 1
          for i, (a, _) in enumerate(bands)), 114)
# The break steps are the rulebook's, not the board icons', so what matters
# is that all six are there and numbered in order.
steps = re.findall(r"\{ at: (\d), text: '[^']+' \},", page.split('rounds: [')[1].split('],')[0])
check('  all six break steps, in order', [int(x) for x in steps], [1, 2, 3, 4, 5, 6])
check('  with a way back to the printed values', "id='ref-reset'" in page or
      'id="ref-reset"' in page, True)
print('\nSCORING AREAS, READ OFF THE BOARD')
# The page hardcodes the mapping, so re-derive it here from the two rules it
# claims and check it against the board instead of against itself: the blocks
# must tile appeal 4-113 with no gap or overlap, and each of the ten printed
# shields must land inside its own block.
check('the page computes a target number', 'function targetNumber' in page, True)
check('  and victory points from it', 'function victoryPoints' in page, True)
check('  two-wide blocks to conservation 10', '114 - 2 * c' in page, True)
check('  three-wide after that', '94 - 3 * (c - 10)' in page, True)

def area(c):
    lo = 114 - 2 * c if c <= 10 else 94 - 3 * (c - 10)
    return lo, lo + (1 if c <= 10 else 2)
spaces = [a for c in range(1, 41) for a in range(area(c)[0], area(c)[1] + 1)]
check('  blocks tile appeal 4-113 exactly', sorted(spaces), list(range(4, 114)))
# Where each shield sat on the photo, as the ticket it was centred over.
shields = {2: 110.5, 5: 104.5, 8: 98.5, 10: 94.5, 15: 80,
           20: 65, 25: 50, 30: 35, 35: 20, 40: 5}
check('  all ten shields land in their own block',
      [c for c, mid in shields.items() if not area(c)[0] <= mid <= area(c)[1]], [])
# Rulebook p19: VP is appeal minus the target; p20 makes 0 or better the solo
# win. Conservation 2 with appeal 110 is the counters exactly meeting.
check('  meeting the counters is 0 VP', 110 - area(2)[0], 0)
check('  and conservation 20 meets at appeal 64', 64 - area(20)[0], 0)
check('the solo win is 0 VP, not a final round', 'solo game is won' in page, True)
check('  and a new game asks where appeal starts', 'Starting appeal?' in page, True)

print('\nTHE REST OF THE BOARD PAGE')
check('a marker reads the band at or below it', 'function bandFor' in page, True)
check('  and shows what is coming', 'function nextBand' in page, True)
check('a milestone announces once', 'st.seen.includes' in page, True)
check('  resuming does not replay old ones', 'checkMilestones(false)' in page, True)
check('  but stepping back down arms it again', 'st.seen.filter' in page, True)
check('saves are debounced', 'saveTimer' in page, True)

print('\nA NEW GAME KEEPS THE REFERENCE')
check('they are separate keys', "'/api/game_state/ark_nova_ref'" in page, True)
c.post('/api/game_state/zzref', headers=H, json={'state': {'appeal': [{'at': 7, 'text': '11'}]}})
c.post('/api/game_state/zzgame', headers=H, json={'state': {'appeal': 40}})
c.post('/api/game_state/zzgame', headers=H, json={'state': {'appeal': 0}})   # new game
check('resetting the game leaves the reference alone',
      c.get('/api/game_state/zzref', headers=H).get_json()['state']['appeal'][0]['text'], '11')
k.execute("DELETE FROM game_state WHERE game_key IN ('zzref','zzgame')")
su.commit()

k.execute("DELETE FROM game_state WHERE game_key LIKE 'zz%'")
k.execute("DELETE FROM users WHERE email LIKE 'zz-gs%'")
su.commit(); k.close(); su.close()
print(f'\n{ok} passed, {fail} failed')
