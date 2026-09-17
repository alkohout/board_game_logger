"""The connection layer: scoping, rollbacks, and what the pool hands back."""
import os, sys, time
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

def scope(conn):
    cur = conn.cursor()
    cur.execute("SELECT current_setting('app.user_id', true)")
    v = cur.fetchone()[0]
    cur.close()
    return v

print('THE CALLER IS STAMPED ONTO THE CONNECTION')
with f.app.test_request_context('/api/dashboard'):
    f.g.user = {'id': 7, 'timezone': None, 'is_owner': False}
    conn = f.get_db_connection()
    check('stamped with the caller', scope(conn), '7')
    check('  and the wrapper remembers it', conn._scope, '7')

with f.app.test_request_context('/api/login'):
    conn = f.get_db_connection()
    check("no caller stamps '' rather than inheriting", scope(conn), '')

print('\nA ROLLBACK DOES NOT LEAVE THE REQUEST UNSCOPED')
# Postgres has no non-transactional SET, so the stamp is made inside whichever
# transaction is open and a rollback discards it. Routes that roll back keep
# using the cursor they already hold, so nothing would re-stamp: every query
# after the rollback would run with no scope and row-level security would match
# nothing, silently, rather than raise.
with f.app.test_request_context('/api/dashboard'):
    f.g.user = {'id': 7, 'timezone': None, 'is_owner': False}
    conn = f.get_db_connection()
    # Something has already read on this connection, as auth does on every
    # real request, so a transaction is open before the stamp is made.
    cur = conn.cursor(); cur.execute('SELECT 1'); cur.fetchone(); cur.close()
    check('stamped before', scope(conn), '7')
    conn.rollback()
    check('  still stamped after a rollback', scope(conn), '7')
    conn.commit()
    check('  and after a commit', scope(conn), '7')

print('\nTHE WRAPPER DOES NOT SWALLOW CONNECTION ATTRIBUTES')
# PooledConnection has __getattr__ but no __setattr__, so an assignment lands
# on the wrapper and never reaches the connection. get_db_connection used to
# flip autocommit that way, which did nothing at all — and hid the fact that
# doing it for real raises inside a transaction.
with f.app.test_request_context('/api/dashboard'):
    f.g.user = {'id': 7, 'timezone': None, 'is_owner': False}
    conn = f.get_db_connection()
    check('autocommit is not shadowed on the wrapper',
          'autocommit' in conn.__dict__, False)
    check('  it reads through to the connection',
          conn.autocommit, conn._conn.autocommit)

print('\nWHAT THE POOL HANDS BACK IS ALWAYS THE SAME SHAPE')
# The fallback for "every pooled connection is dead" used to return a bare
# psycopg2 connection. raw_db_connection then tests conn._closed and teardown
# calls conn._release(), neither of which a bare connection has — so a
# recoverable blip became an AttributeError.
args, kwargs = f._connection_settings()
bare = psycopg2.connect(*args, **kwargs)
wrapped = f.PooledConnection(None, bare)
check('close() is a no-op', (wrapped.close(), wrapped._closed)[1], False)
check('  _closed is present', hasattr(wrapped, '_closed'), True)
check('  _release is present', hasattr(wrapped, '_release'), True)
wrapped._release()
check('an unpooled wrapper really closes on release', bare.closed, 1)
check('  and releasing twice is harmless', (wrapped._release(), True)[1], True)

print('\nTHE FREE GRANT RESETS IN THE CALLER\'S MONTH')
# date_trunc('month', now()) uses the database session's zone, which is UTC.
# In New Zealand that reset the allowance thirteen hours late.
with f.app.test_request_context('/'):
    f.g.user = {'id': 1, 'timezone': 'Pacific/Auckland', 'is_owner': False}
    nz = f.month_start_local()
    f.g.user = {'id': 1, 'timezone': 'UTC', 'is_owner': False}
    utc = f.month_start_local()
check('the month starts at midnight', (nz.hour, nz.minute, nz.day), (0, 0, 1))
check('  in the account\'s own zone', str(nz.tzinfo), 'Pacific/Auckland')
check('  which is not the same instant as UTC', nz.utcoffset() == utc.utcoffset(), False)

print('\nLOGIN COSTS THE SAME FOR AN ADDRESS THAT DOES NOT EXIST')
# Skipping the hash for an unknown address answers far faster, which is a way
# of asking whether an address is registered — what signup refuses to answer.
su = psycopg2.connect(host='localhost', database='boardgames', user='postgres', password=SUPER_PW)
k = su.cursor()
from werkzeug.security import generate_password_hash
k.execute("UPDATE users SET password_hash=%s WHERE is_owner",
          (generate_password_hash('pw-for-tests'),))
k.execute("DELETE FROM login_attempts")
su.commit()
c = f.app.test_client()

def timed(email):
    k.execute("DELETE FROM login_attempts"); su.commit()
    start = time.perf_counter()
    r = c.post('/api/login', json={'email': email, 'password': 'definitely-wrong'})
    return time.perf_counter() - start, r.status_code

known_t, known_s = timed('owner@example.com')
absent_t, absent_s = timed('nobody-at-all@example.com')
check('both are rejected the same way', (known_s, absent_s), (401, 401))
# Without the dummy hash the unknown address returns orders of magnitude
# faster. Half is a wide margin that still fails an unguarded path.
check('  and take comparable time', absent_t > known_t * 0.5, True)
if absent_t <= known_t * 0.5:
    print(f'       known {known_t*1000:.1f}ms vs absent {absent_t*1000:.1f}ms')

k.execute("DELETE FROM login_attempts"); su.commit()
k.close(); su.close()

print('\nLATEST NOTE MEANS THE LATEST NOTE, NOT THE LATEST ROW')
# A blank note is not a note. The old query took the newest row whose notes
# were merely NOT NULL, so a game whose most recent sitting had an empty note
# showed nothing at all even when earlier sittings had one.
page = open('flask_web_interface.py').read()
check('blanks are skipped, not just NULLs',
      "btrim(COALESCE(notes, '')) <> ''" in page, True)
check('  and ties break on id, as search_last_played does',
      'ORDER BY game_title, date_played DESC, id DESC' in page, True)
check('the correlated per-title subquery is gone',
      'FROM games g2 WHERE g2.game_title = g.game_title' in page, False)

print(f'\n{ok} passed, {fail} failed')
