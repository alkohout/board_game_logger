from flask import Flask, request, jsonify, g, has_request_context
from flask_cors import CORS
import psycopg2
import psycopg2.pool
import threading
import time
import os
import random
import re
import anthropic
try:
    import stripe                       # only needed for credit top-ups
except ImportError:                     # keeps the app up if it isn't installed yet
    stripe = None
try:
    from pypdf import PdfReader         # for pulling text out of rulebooks
except ImportError:
    PdfReader = None
import io
import base64
import requests          # for a self-hosted, OpenAI-compatible model
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, urlunsplit, quote
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import smtplib
import ssl as ssl_module
from email.message import EmailMessage

load_dotenv()

# The server runs in UTC (Oracle Cloud), which is 12-13 hours behind NZ, so
# "today" must be computed in the local zone. Override with TIMEZONE env var.
LOCAL_TZ = ZoneInfo(os.getenv('TIMEZONE', 'Pacific/Auckland'))


def user_tz():
    """The caller's timezone, falling back to the server's.

    Day boundaries are per account, not per server. Auckland is up to 13 hours
    ahead of UTC, so a single server-wide zone puts an evening game in London
    on the following day and reports "played today: 0" to someone who just
    played one.
    """
    user = getattr(g, 'user', None) if has_request_context() else None
    name = (user or {}).get('timezone')
    if name:
        try:
            return ZoneInfo(name)
        except Exception:
            # An unknown zone shouldn't take the request down with it.
            app.logger.warning('Unknown timezone %r; using the server default', name)
    return LOCAL_TZ


def today_local():
    return datetime.now(user_tz()).date()

# Every play before this date is a bulk backfill of old plays, all stamped
# 2023-01-01, so it would win every "most ever" record. Records ignore it.
RECORDS_START = date(2024, 1, 1)


def period_records(cur):
    """Best-ever plays per calendar day/week/month/year. Weeks start Monday,
    matching how the current-period counts are worked out."""
    def best(period_expr):
        cur.execute(f"""
            SELECT {period_expr} AS period, COUNT(*) AS plays
            FROM games WHERE date_played >= %s
            GROUP BY period ORDER BY plays DESC, period DESC LIMIT 1
        """, (RECORDS_START,))
        row = cur.fetchone()
        return {'count': row[1], 'start': row[0]} if row else {'count': 0, 'start': None}

    return {
        'day': best("date_played"),
        'week': best("date_trunc('week', date_played::timestamp)::date"),
        'month': best("date_trunc('month', date_played::timestamp)::date"),
        'year': best("date_trunc('year', date_played::timestamp)::date"),
    }

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit
app.secret_key = os.getenv('SECRET_KEY')

# DELETE is here because deleting an account uses it. A method missing from
# this list isn't rejected by the server — the browser never sends it, because
# the preflight comes back without permission, so the button silently does
# nothing. cors_test keeps this in step with the methods the routes expose.
CORS(app,
     origins=["https://alkohout.github.io", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000"],
     allow_headers=["Authorization", "Content-Type"],
     methods=["GET", "POST", "OPTIONS", "DELETE"])


# ── Accounts and sessions ─────────────────────────────────────────────────────
# A session token is a signed, expiring statement of "this is user N", not a
# password echoed back. Signing means the server keeps no session table and a
# token cannot be forged without SECRET_KEY.

TOKEN_MAX_AGE = 60 * 60 * 24 * 30      # 30 days before a login expires
LOGIN_MAX_FAILURES = 8                  # per email per window
LOGIN_WINDOW_MINUTES = 15
MIN_PASSWORD_LENGTH = 8

# Endpoints reachable without a session.
PUBLIC_API_PATHS = {'/api/login', '/api/signup'}


def token_serializer():
    return URLSafeTimedSerializer(app.secret_key or '', salt='bgl-session')


def issue_token(user_id, token_version):
    """A token names the account *and* the password generation it was issued
    under, so changing a password retires every token that predates it."""
    return token_serializer().dumps({'uid': user_id, 'v': token_version})


def load_user(user_id):
    """Fetch a user by id. Returns None for unknown, pending or disabled accounts.

    Deliberately unstamped: `users` carries no row-level security, and this runs
    before the caller is known, so stamping here only wrote an empty scope that
    the route then immediately overwrote — two round trips to a database three
    time zones away, on every single request.
    """
    conn = raw_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, email, display_name, status, is_owner, token_version,
                   timezone
            FROM users WHERE id = %s
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row or row[3] != 'active':
        return None
    return {'id': row[0], 'email': row[1], 'display_name': row[2],
            'status': row[3], 'is_owner': row[4], 'token_version': row[5],
            'timezone': row[6]}


def request_user():
    """Resolve the caller from their bearer token, or None."""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        raw = auth[7:]
        try:
            data = token_serializer().loads(raw, max_age=TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            data = None
        if data and data.get('uid'):
            user = load_user(data['uid'])
            # A token from before the last password change no longer matches.
            if user and data.get('v') == user['token_version']:
                return user
    return None


@app.before_request
def require_login():
    if request.method == 'OPTIONS':
        return
    if request.endpoint == 'static':
        return
    if request.path.startswith('/api/'):
        if request.path in PUBLIC_API_PATHS:
            return
        user = request_user()
        if not user:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        g.user = user
        return
    if request.endpoint in ('api_root', 'stripe_webhook'):
        return
    # The handful of surviving non-/api/ endpoints are called by the site with
    # a bearer token, same as the rest. There is no browser session any more,
    # so there is nothing to redirect to.
    user = request_user()
    if not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    g.user = user


def current_user():
    return getattr(g, 'user', None)


def owner_only():
    """Guard for admin endpoints. Returns a response to send, or None to proceed."""
    user = current_user()
    if not user or not user.get('is_owner'):
        return jsonify({'success': False, 'message': 'Owner only'}), 403
    return None

EXPECTED_COLUMNS = {
    'users': ('token_version',),
    # add_game writes the Spirit Island columns on every insert, so code
    # deployed ahead of migration 012 would fail to log any game at all.
    'games': ('user_id', 'spirit', 'adversary', 'adversary_level', 'scenario',
              'civilisation'),
    'rulebooks': ('user_id', 'rules_text', 'page_count'),
    'ai_usage': ('input_tokens', 'cache_read_tokens'),
    'credit_purchases': ('stripe_session_id',),
    # 014 — without these the trackers would serve one shared campaign to
    # every account, which is exactly what going multi-user was avoiding.
    'sleeping_gods': ('user_id',),
    'sleeping_gods_totems': ('user_id',),
}


def check_schema():
    """Warn loudly at boot if a migration hasn't been run.

    Otherwise the first sign is a request failing after the work was already
    done — an AI question that cost real money and returned an error.
    """
    try:
        conn = raw_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'public'
        """)
        have = {(t, c) for t, c in cur.fetchall()}
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.warning('Could not check the schema at startup: %s', e)
        return
    missing = [f'{table}.{column}'
               for table, columns in EXPECTED_COLUMNS.items()
               for column in columns
               if (table, column) not in have and any(t == table for t, _ in have)]
    if missing:
        app.logger.error('SCHEMA OUT OF DATE — missing %s. Run the migrations in '
                         'migrations/ before serving traffic.', ', '.join(missing))
    else:
        app.logger.info('Schema check passed.')


@app.route('/')
def api_root():
    """This host is the API. The app itself lives on GitHub Pages."""
    return jsonify({'app': 'Board Game Logger API',
                    'site': 'https://alkohout.github.io/board_game_logger/'})


def _connection_settings():
    """Where and as whom to connect. Shared by the pool and by direct opens."""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        override_user = os.getenv('DB_USER')
        if override_user:
            # A hosted database hands you a URL with the owner role baked in,
            # and that role bypasses row-level security — so DB_USER has to win
            # over the URL, or setting it silently does nothing. Host, database
            # and SSL options are kept exactly as given.
            parts = urlsplit(database_url)
            netloc = '{}:{}@{}'.format(quote(override_user, safe=''),
                                       quote(os.getenv('PASSWORD', ''), safe=''),
                                       parts.hostname)
            if parts.port:
                netloc += ':{}'.format(parts.port)
            database_url = urlunsplit((parts.scheme, netloc, parts.path,
                                       parts.query, parts.fragment))
        return (database_url,), {}
    return (), dict(
        host="localhost",
        database="boardgames",
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("PASSWORD")
    )


# Opening a connection to a hosted database three time zones away costs about
# 1.3 seconds — a TLS handshake is several round trips and each one is ~200ms.
# Every request was paying that twice, once to read the caller's token and once
# for the query itself, so a keystroke in the autocomplete cost about four
# seconds before any work happened. Connections are kept and reused instead.
_POOL = None
_POOL_LOCK = threading.Lock()
POOL_MIN = int(os.getenv('DB_POOL_MIN', '1'))
POOL_MAX = int(os.getenv('DB_POOL_MAX', '4'))


def _pool():
    global _POOL
    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                args, kwargs = _connection_settings()
                # Without keepalives an idle connection is dropped somewhere in
                # the middle and only fails when it's next used.
                kwargs = dict(kwargs, keepalives=1, keepalives_idle=30,
                              keepalives_interval=10, keepalives_count=3)
                _POOL = psycopg2.pool.ThreadedConnectionPool(
                    POOL_MIN, POOL_MAX, *args, **kwargs)
    return _POOL


# Round trips are the unit of cost here: ~205ms each to us-east-1, so the
# tuning is about doing fewer of them, not about doing less work.
POOL_IDLE_CHECK_SECONDS = float(os.getenv('DB_POOL_IDLE_CHECK', '20'))


class PooledConnection:
    """A pooled connection that goes back to the pool when closed.

    Every route already calls conn.close(), so returning rather than closing
    keeps the call sites unchanged. Only a rollback happens on the way back —
    one round trip. Clearing app.user_id here would be a second, and is not
    needed: get_db_connection sets it on every checkout, to '' when there is
    no caller, so nothing inherits the previous request's scope.
    """

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        """A no-op: routes close their connection, but the request isn't over.

        Honouring it would hand the connection back after the first route that
        finished with it, and the next get_db_connection in the same request
        would check out another — the two-connections-per-request problem this
        exists to avoid. teardown_request does the real release.
        """

    def _release(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._conn.rollback()
            self._pool.putconn(self._conn)
            _POOL_IDLE_SINCE[id(self._conn)] = time.time()
        except Exception:
            # A connection that can't be cleaned up is not safe to hand on.
            try:
                self._pool.putconn(self._conn, close=True)
            except Exception:
                pass


_POOL_IDLE_SINCE = {}


def _checkout():
    """A live pooled connection, with as few round trips as possible."""
    pool = _pool()
    for _ in range(POOL_MAX + 1):
        conn = pool.getconn()
        if conn.closed:
            pool.putconn(conn, close=True)
            continue
        # Only probe a connection that has been sitting long enough to have
        # been dropped. Probing every checkout cost two round trips on the
        # hot path to catch something that almost never happens.
        idle_for = time.time() - _POOL_IDLE_SINCE.get(id(conn), 0)
        if idle_for > POOL_IDLE_CHECK_SECONDS:
            try:
                cur = conn.cursor()
                cur.execute('SELECT 1')
                cur.close()
                conn.rollback()
            except Exception:
                pool.putconn(conn, close=True)
                continue
        return PooledConnection(pool, conn)
    args, kwargs = _connection_settings()
    return psycopg2.connect(*args, **kwargs)


def raw_db_connection():
    """A connection with no identity attached. Only auth and migrations want this."""
    # Migrations and one-off scripts run outside a request and should not be
    # holding pool slots; they get a plain connection.
    if not has_request_context():
        args, kwargs = _connection_settings()
        return psycopg2.connect(*args, **kwargs)

    # One connection for the whole request. Reading the caller's token and then
    # running the route used to open two, and at ~1.3s to establish and several
    # round trips to use, that was most of the request.
    conn = getattr(g, '_db', None)
    if conn is None or conn._closed:
        conn = _checkout()
        g._db = conn
    return conn


@app.teardown_request
def _release_db(exc=None):
    conn = getattr(g, '_db', None)
    if conn is not None:
        g._db = None
        conn._release()


def get_db_connection():
    """The connection every route uses.

    Stamps the caller's id onto the session so the row-level security policies
    can filter, and so INSERTs pick up the right owner from the column default.
    SET LOCAL would be undone by the first commit, so this is session-level and
    re-stamped on every checkout.
    """
    conn = raw_db_connection()
    user = getattr(g, 'user', None) if has_request_context() else None
    wanted = str(user['id']) if user else ''

    # Always set it, including to '' when there is no caller. With a fresh
    # connection per request an unset value meant "match nothing", which was
    # safe by accident; on a pooled connection it would mean "whatever the
    # previous request left there". NULLIF('','') is NULL, so the policy still
    # matches nothing — but now it says so explicitly.
    #
    # Once per request, not once per call: routes call this repeatedly and each
    # stamp is a round trip to a database three time zones away.
    if getattr(conn, '_scope', None) != wanted:
        was_autocommit = conn.autocommit
        # Autocommit is a client-side flag, so this replaces the separate
        # COMMIT round trip the stamp used to need with nothing at all.
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT set_config('app.user_id', %s, false)", (wanted,))
        cur.close()
        conn.autocommit = was_autocommit
        try:
            conn._scope = wanted
        except AttributeError:
            pass
    return conn


def private_db_connection():
    """A connection outside the request pool, stamped with the caller.

    For work that changes session state — read-only, a different role — which
    must not follow a connection back into the pool.
    """
    args, kwargs = _connection_settings()
    conn = psycopg2.connect(*args, **kwargs)
    user = getattr(g, 'user', None) if has_request_context() else None
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.user_id', %s, false)",
                (str(user['id']) if user else '',))
    cur.close()
    conn.commit()
    return conn


def db_bypasses_rls():
    """True when the app is connected as a superuser, which ignores RLS.

    The isolation is only real once .env points at the bgl_app role, so this
    lets the risky endpoints refuse rather than quietly serving everyone's data.
    """
    conn = raw_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
        row = cur.fetchone()
        cur.close()
        return bool(row and row[0])
    except psycopg2.Error:
        return True          # can't tell, so assume the worst
    finally:
        conn.close()










@app.route('/search_sleeping_gods_location', methods=['GET'])
def search_sleeping_gods_location():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    # location is an integer column, so anything else is a 400 rather than a
    # 500 out of the driver. This only became reachable when the endpoint
    # stopped being owner-only — before that a stray value was refused earlier.
    try:
        location = int(request.args.get('term', '0'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Location must be a number.'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Search
    cur.execute("""
        SELECT id,* FROM sleeping_gods
        WHERE location = %s
    """, (location,))
    results = cur.fetchall()
    cur.close()
    conn.close()

    # Convert the results to a list of dictionaries
    data = [
        {       
	    'id': row[0],
	    'location': row[1],
	    'part': row[2],
	    'required_keyword': row[3],
	    'gained_keyword': row[4],
	    'visited': row[5],
	    'notes': row[6],
	    'combat': row[7],
	    'combat_level': row[8],
	    'gained': row[9],
	    'lost': row[10],
	    'req_coins': row[11],
	    'req_meat': row[12],
	    'req_veg': row[13],
	    'req_grain': row[14],
	    'req_artifacts': row[15],
	    'gain_coins': row[16],
	    'gain_meat': row[17],
	    'gain_veg': row[18],
	    'gain_grain': row[19],
	    'gain_artifacts': row[20],
	    'req_wood': row[21],
	    'gain_wood': row[22],
	    'gain_xp': row[23],
	    'gain_ship_damage': row[24],
	    'gain_ship_repair': row[25],
	    'gain_crew_damage': row[26],
	    'gain_crew_health': row[27],
	    'gain_low_morale': row[28],
	    'gain_fright': row[29],
	    'gain_venom': row[30],
	    'gain_weakness': row[31],
	    'gain_madness': row[32],
	    'remove_low_morale': row[33],
	    'remove_fright': row[34],
	    'remove_venom': row[35],
	    'remove_weakness': row[36],
	    'remove_madness': row[37],
	    'totem': row[38],
	    'challenge': row[39],
	    'challenge_level': row[40],
	    'gain_totem': row[41],
	    'gain_adventure': row[42],
        }
        for row in results
    ]

    return jsonify(data)

@app.route('/search_sleeping_gods_notes', methods=['GET'])
def search_sleeping_gods_notes():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    keyword = request.args.get('term', '0')
    conn = get_db_connection()
    cur = conn.cursor()

    # Search  
    cur.execute("""
        SELECT id,* FROM sleeping_gods  
        WHERE notes ILIKE %s 
           OR required_keyword ILIKE %s
           OR gained_keyword ILIKE %s
	   OR gained ILIKE %s
	   OR lost ILIKE %s
    """, (f"%{keyword}%", f"%{keyword}%",f"%{keyword}%",f"%{keyword}%",f"%{keyword}%"))
    results = cur.fetchall()
    cur.close()
    conn.close()

    # Convert the results to a list of dictionaries
    data = [
        {       
	    'id': row[0],
	    'location': row[1],
	    'part': row[2],
	    'required_keyword': row[3],
	    'gained_keyword': row[4],
	    'visited': row[5],
	    'notes': row[6],
	    'combat': row[7],
	    'combat_level': row[8],
	    'gained': row[9],
	    'lost': row[10],
	    'req_coins': row[11],
	    'req_meat': row[12],
	    'req_veg': row[13],
	    'req_grain': row[14],
	    'req_artifacts': row[15],
	    'gain_coins': row[16],
	    'gain_meat': row[17],
	    'gain_veg': row[18],
	    'gain_grain': row[19],
	    'gain_artifacts': row[20],
	    'req_wood': row[21],
	    'gain_wood': row[22],
	    'gain_xp': row[23],
	    'gain_ship_damage': row[24],
	    'gain_ship_repair': row[25],
	    'gain_crew_damage': row[26],
	    'gain_crew_health': row[27],
	    'gain_low_morale': row[28],
	    'gain_fright': row[29],
	    'gain_venom': row[30],
	    'gain_weakness': row[31],
	    'gain_madness': row[32],
	    'remove_low_morale': row[33],
	    'remove_fright': row[34],
	    'remove_venom': row[35],
	    'remove_weakness': row[36],
	    'remove_madness': row[37],
	    'totem': row[38],
	    'challenge': row[39],
	    'challenge_level': row[40],
	    'gain_totem': row[41],
	    'gain_adventure': row[42],
        }
        for row in results
    ]

    return jsonify(data)


@app.route('/delete_sleeping_gods_row', methods=['POST'])
def delete_sleeping_gods_row():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    data = request.get_json(force=True)
    row_id = data.get('id')
    if not row_id:
        return jsonify({'success': False, 'error': 'id missing'}), 400

    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM sleeping_gods WHERE id = %s", (row_id,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reset_visited_sleeping_gods', methods=['POST'])
def reset_visited_sleeping_gods():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    try:
        # Connect to your database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Scoped twice on purpose: the policy already limits this to the
        # caller, and the explicit user_id means a bare "reset everything"
        # can't reach another account if that policy is ever loosened.
        cursor.execute('UPDATE sleeping_gods SET visited = FALSE WHERE user_id = %s',
                       (current_user()['id'],))
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})

    except Exception as e:
        print(e)  # For debugging
        return jsonify({'success': False, 'error': str(e)})

@app.route('/sleeping_gods_totems_update', methods=['POST'])
def sleeping_gods_totems_update():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    try:
        data = request.get_json()
        totem_id = data['totemId']
        is_found = data['isFound']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sleeping_gods_totems SET found = %s WHERE id = %s", (bool(is_found), totem_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating totem checklist: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500  #Return error message


	

@app.route('/search_games', methods=['GET'])
def search_games():
    search_term = request.args.get('term', '')
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT game_title FROM games WHERE game_title ILIKE %s", (f"%{search_term}%",))
    suggestions = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify({'suggestions': suggestions})

@app.route('/search_last_played', methods=['GET'])
def search_last_played():
    game_title = request.args.get('term', '')
    conn = get_db_connection()
    cur = conn.cursor()

    # The most recent play, and the details of that same play.
    #
    # This used to take the date from the newest date_played but the details
    # from the highest id — the row inserted last. Log a game for an older date
    # after logging a newer one and they point at different rows, so the card
    # showed one play's date beside another play's result. Ordering by
    # date_played then id keeps them on the same row, the same rule the
    # latest-non-empty query below already follows.
    cur.execute("""
        SELECT date_played, id
        FROM games
        WHERE game_title ILIKE %s
        ORDER BY date_played DESC, id DESC
        LIMIT 1
    """, (f"%{game_title}%",))
    last_played = cur.fetchone()
    if not last_played:
        # Nothing matched — every lookup below indexes into this row, so stop
        # here rather than crashing. Common now that a new account starts empty.
        cur.close()
        conn.close()
        return jsonify({'Error': 'No record found for the specified game.'})

    # One row, one query — this was five round trips for five columns of the
    # same row, and adding the Spirit Island fields would have made it eight.
    cur.execute("""SELECT notes, result, level, my_score, bot_score,
                          spirit, adversary, adversary_level, scenario, civilisation
                   FROM games WHERE id = %s""", (last_played[1],))
    (notes, result, level, my_score, bot_score,
     spirit, adversary, adversary_level, scenario, civilisation) = cur.fetchone()

    # Fetch total number of times the game was played
    cur.execute("SELECT COUNT(*) FROM games WHERE game_title ILIKE %s", (f"%{game_title}%",))
    total_plays = cur.fetchone()[0]
    
    # Fetch the most recent play date for the game
    cur.execute("SELECT MAX(date_played) FROM games WHERE game_title ILIKE %s", (f"%{game_title}%",))
    last_played_date = cur.fetchone()[0]
    
    # Calculate date boundaries for the current week, month, and year
    today = today_local()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    
    # Count games played this week
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND game_title ILIKE %s", (start_of_week,f"%{game_title}%"))
    played_this_week = cur.fetchone()[0]
    
    # Count games played this month
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND game_title ILIKE %s", (start_of_month,f"%{game_title}%"))
    played_this_month = cur.fetchone()[0]
    
    # Count games played this year
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND game_title ILIKE %s", (start_of_year,f"%{game_title}%"))
    played_this_year = cur.fetchone()[0]

    # Query to get the ranking of games by play count
    cur.execute("SELECT game_title, RANK() OVER (ORDER BY COUNT(*) DESC) FROM games GROUP BY game_title")
    rankings = cur.fetchall()

    # Create a dictionary of game titles and their rankings
    rankings_dict = {game[0]: game[1] for game in rankings}

    # Get the ranking for the specified game
    ranking = rankings_dict.get(game_title, "Not ranked")

    # The most recent play that actually recorded something, so the hint left
    # in its notes is easy to find. Ordered by when it was played, not by id,
    # so a game logged after the fact doesn't jump the queue.
    cur.execute("""
        SELECT date_played, notes, result, level, my_score, bot_score,
               spirit, adversary, adversary_level, scenario
        FROM games
        WHERE game_title ILIKE %s
          AND ( (notes  IS NOT NULL AND btrim(notes)  NOT IN ('', 'null')) OR
                (result IS NOT NULL AND btrim(result) NOT IN ('', 'null')) OR
                -- A Spirit Island play picked from the dropdowns records real
                -- detail without necessarily typing a note or a result.
                spirit IS NOT NULL OR adversary IS NOT NULL OR scenario IS NOT NULL )
        ORDER BY date_played DESC, id DESC
        LIMIT 1
    """, (f"%{game_title}%",))
    nonempty = cur.fetchone() or (None,) * 10
    (date_nonempty, notes_nonempty, result_nonempty, level_nonempty,
     my_score_nonempty, bot_score_nonempty, spirit_nonempty, adversary_nonempty,
     adversary_level_nonempty, scenario_nonempty) = nonempty

    cur.close()
    conn.close()

    # Respond with JSON data, including stats
    if last_played:
        return jsonify({
            'notes': notes if notes else None,
            'result': result if result else None,
	    'level': level if level else None,
	    'my_score': my_score if my_score else None,
	    'bot_score': bot_score if bot_score else None,
            'spirit': spirit,
            'adversary': adversary,
            'adversary_level': adversary_level,
            'scenario': scenario,
            'civilisation': civilisation,
            'date_played': last_played[0].isoformat(),
            'date_played_nonempty': date_nonempty.isoformat() if date_nonempty else None,
            'notes_nonempty': notes_nonempty if notes_nonempty else None,
            'result_nonempty': result_nonempty if result_nonempty else None,
	    'level_nonempty': level_nonempty if level_nonempty else None,
	    'my_score_nonempty': my_score_nonempty if my_score_nonempty else None,
	    'bot_score_nonempty': bot_score_nonempty if bot_score_nonempty else None,
            'spirit_nonempty': spirit_nonempty,
            'adversary_nonempty': adversary_nonempty,
            'adversary_level_nonempty': adversary_level_nonempty,
            'scenario_nonempty': scenario_nonempty,
            #'last_played_date': last_played_date.isoformat() if last_played_date else None,
            'total_times_played': total_plays,
            'played_this_week': played_this_week,
            'played_this_month': played_this_month,
            'played_this_year': played_this_year,
            'ranking': ranking
        })
    else:
        return jsonify({'Error': 'No record found for the specified game.'})


@app.route('/update_note', methods=['POST'])
def update():
    data = request.json
    game_title = data.get('game_title')
    updated_note = data.get('note')
    updated_result = data.get('result')
    updated_level = data.get('level')
    updated_myscore = data.get('my_score')
    updated_botscore = data.get('bot_score')

    if not game_title or not updated_note:
        return jsonify({"success": False, "message": "Invalid data"})

    # Update the note in the database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE games
            SET notes = %s
            WHERE game_title = %s 
            AND date_played = (
                SELECT MAX(date_played) 
                FROM games 
                WHERE game_title = %s
            )
        """, (updated_note, game_title, game_title))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})





def usage_tokens(*usages):
    """The four token buckets across one or more calls, for the ledger."""
    total = {'input_tokens': 0, 'output_tokens': 0,
             'cache_write_tokens': 0, 'cache_read_tokens': 0}
    for u in usages:
        total['input_tokens'] += u.input_tokens or 0
        total['output_tokens'] += u.output_tokens or 0
        total['cache_write_tokens'] += getattr(u, 'cache_creation_input_tokens', 0) or 0
        total['cache_read_tokens'] += getattr(u, 'cache_read_input_tokens', 0) or 0
    return total


def usage_cost_usd(usage, price_in, price_out):
    """Cost of one call, counting the cached tokens too.

    usage.input_tokens is only the *uncached* part. With prompt caching on the
    rulebooks — which is the point of it — most of the input arrives as cache
    writes (1.25x) or cache reads (0.1x), and ignoring those bills a large
    question as almost free.
    """
    written = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    return (usage.input_tokens * price_in
            + written * price_in * 1.25
            + read * price_in * 0.10
            + usage.output_tokens * price_out) / 1_000_000


RULES_MODEL = 'claude-haiku-4-5'
RULES_PRICE_IN = 1.00      # USD per million input tokens
RULES_PRICE_OUT = 5.00


def extract_pdf_text(pdf_bytes):
    """Plain text of a rulebook, page-marked so answers can still cite pages.

    Returns '' for a PDF that is really scanned images — a couple of the books
    here are — and the caller falls back to sending the pages themselves.
    """
    if PdfReader is None:
        return ''
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        app.logger.warning('Could not read PDF for text: %s', e)
        return ''
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            body = page.extract_text() or ''
        except Exception:
            body = ''
        if body.strip():
            pages.append(f'[page {number}]\n{body.strip()}')
    return '\n\n'.join(pages)


# Roughly what a page of a rulebook costs as an image, measured across the
# books here (Ark Nova's 20 pages came to ~50,700 tokens).
TOKENS_PER_PDF_PAGE = 2500


def count_pdf_pages(pdf_bytes):
    if PdfReader is None:
        return None
    try:
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return None


def image_cost_nzd(pages):
    """What sending this many pages as images adds to a question."""
    if not pages:
        return None
    usd = pages * TOKENS_PER_PDF_PAGE * RULES_PRICE_IN / 1_000_000
    return round(usd * float(os.getenv('NZD_RATE', '1.68')), 3)


@app.route('/upload_rulebook', methods=['POST'])
def upload_rulebook():
    game_title = request.form.get('game_title', '').strip()
    rulebook_name = (request.form.get('rulebook_name') or 'Base').strip()
    if not game_title:
        return jsonify({'success': False, 'message': 'Game title required'}), 400
    if 'pdf_file' not in request.files or request.files['pdf_file'].filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    pdf_file = request.files['pdf_file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'File must be a PDF'}), 400

    pdf_file.stream.seek(0)
    pdf_bytes = pdf_file.stream.read()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')
    pages = count_pdf_pages(pdf_bytes)
    # Extracted once here rather than per question: the text costs about a
    # third of the tokens the page images do.
    rules_text = extract_pdf_text(pdf_bytes)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO rulebooks (game_title, rulebook_name, pdf_data, rules_text, page_count)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (game_title, rulebook_name) DO UPDATE
                SET pdf_data = EXCLUDED.pdf_data,
                    rules_text = EXCLUDED.rules_text,
                    page_count = EXCLUDED.page_count,
                    uploaded_at = NOW()
        """, (game_title, rulebook_name, pdf_b64, rules_text or None, pages))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'DB error: {str(e)}'}), 500
    if rules_text:
        detail = f'text extracted, {len(rules_text):,} characters'
    elif PdfReader is None:
        detail = 'stored as pages — text extraction unavailable on the server'
    else:
        detail = 'no text in this PDF, so its pages will be sent as images (costs more)'
    return jsonify({'success': True,
                    'message': f'"{rulebook_name}" saved for {game_title} — {detail}',
                    'has_text': bool(rules_text)})


@app.route('/delete_rulebook', methods=['POST'])
def delete_rulebook():
    try:
        data = request.get_json()
        game_title = (data.get('game_title') or '').strip()
        rulebook_name = (data.get('rulebook_name') or '').strip()
        if not game_title or not rulebook_name:
            return jsonify({'success': False, 'message': 'game_title and rulebook_name required'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM rulebooks WHERE game_title = %s AND rulebook_name = %s", (game_title, rulebook_name))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/clear_bgg_cache', methods=['POST'])
def clear_bgg_cache():
    try:
        data = request.get_json()
        game_title = (data.get('game_title') or '').strip()
        if not game_title:
            return jsonify({'success': False, 'message': 'Game title required'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE rulebooks SET bgg_forum_cache = NULL WHERE game_title = %s", (game_title,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/cache_bgg_threads', methods=['POST'])
def cache_bgg_threads():
    try:
        data = request.get_json()
        game_title = (data.get('game_title') or '').strip()
        threads_text = (data.get('threads_text') or '').strip()
        if not game_title or not threads_text:
            return jsonify({'success': False, 'message': 'Missing data'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE rulebooks
            SET bgg_forum_cache = CASE
                WHEN bgg_forum_cache IS NULL OR bgg_forum_cache = '' THEN %s
                ELSE bgg_forum_cache || E'\n\n===\n\n' || %s
            END
            WHERE game_title = %s
        """, (threads_text, threads_text, game_title))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/ask_rules', methods=['POST'])
def ask_rules():
    try:
        data = request.get_json()
        game_title = (data.get('game_title') or '').strip()
        question = (data.get('question') or '').strip()
        if not game_title or not question:
            return jsonify({'success': False, 'message': 'Game and question required'}), 400

        # Books the caller has asked to see as page images, either because the
        # model said the text wasn't enough or because they ticked the box.
        want_images = {n.strip().lower() for n in (data.get('with_images') or [])}

        blocked = ai_spend_blocked()
        if blocked:
            return blocked

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT pdf_data, bgg_forum_cache, rulebook_name, rules_text, page_count
            FROM rulebooks WHERE game_title = %s AND pdf_data IS NOT NULL
            ORDER BY rulebook_name
        """, (game_title,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return jsonify({'success': False, 'message': f'No rulebook found for {game_title} — try re-uploading'}), 404

        bgg_section = next((r[1] for r in rows if r[1]), '')

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'message': 'ANTHROPIC_API_KEY not configured'}), 500

        # A rulebook goes as extracted text where we have it — about a third of
        # the tokens the page images cost, which is what keeps a game like
        # Spirit Island under the context limit. Books that are really scanned
        # images extract nothing, so those still go as pages.
        book_blocks = []
        as_images = []
        available = []
        for pdf_b64, _bgg, name, text, pages in rows:
            label = name or 'Rulebook'
            has_text = bool(text and text.strip())
            available.append({'name': label, 'pages': pages, 'has_text': has_text,
                              'image_cost_nzd': image_cost_nzd(pages)})
            # Images when the caller asked for this book, or when it has no text.
            if has_text and label.lower() not in want_images:
                book_blocks.append({'type': 'text',
                                    'text': f'=== {label} ===\n{text}'})
            else:
                book_blocks.append({'type': 'document',
                                    'source': {'type': 'base64',
                                               'media_type': 'application/pdf',
                                               'data': pdf_b64}})
                as_images.append(label)

        # Page images are big; refuse before the API does, with something useful.
        image_pages = sum(b['pages'] or 0 for b in available if b['name'] in as_images)
        if image_pages * TOKENS_PER_PDF_PAGE > 170_000:
            return jsonify({'success': False, 'books': available,
                            'message': (f'Those {image_pages} pages of images are too much for one '
                                        f'question. Pick fewer books to send as images.')}), 400

        history = data.get('history', [])  # [{role, content}] of previous text turns

        # First user message always includes PDFs + optional BGG + first question
        first_question = history[0]['content'] if history else question
        first_content = list(book_blocks)
        if bgg_section:
            first_content.append({'type': 'text', 'text': f'BGG Rules Forum Discussions:\n{bgg_section}'})
        # One breakpoint on the last shared block caches every rulebook above
        # it. Marking each book separately would exceed the four-breakpoint
        # limit as soon as a game had five.
        if first_content:
            first_content[-1] = dict(first_content[-1], cache_control={'type': 'ephemeral'})
        first_content.append({'type': 'text', 'text': first_question})

        messages = [{'role': 'user', 'content': first_content}]
        # Replay subsequent history turns as plain text
        for turn in history[1:]:
            messages.append({'role': turn['role'], 'content': turn['content']})
        # Add current question if this is a follow-up
        if history:
            messages.append({'role': 'user', 'content': question})

        book_names = ', '.join(r[2] or 'Rulebook' for r in rows)
        sources_used = book_names + (' + pasted BGG content' if bgg_section else ' + training knowledge')
        if as_images:
            sources_used += f" ({', '.join(as_images)} sent as page images)"
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            system=(
                f'You are a board game rules expert for "{game_title}". '
                f'Answer questions directly without any preamble, disclaimers, or meta-commentary about your sources. '
                f'Use these sources in priority order: '
                f'(1) the provided rulebook, '
                f'(2) any BGG forum content provided, '
                f'(3) your training knowledge of community clarifications and BGG discussions for this game. '
                f'Just give the answer. Briefly note the source inline where useful '
                f'(e.g. "Rulebook p.12" or "BGG community consensus") but never open with an explanation of what you do or don\'t have.'
                + ("""

The rulebooks above are the extracted text, so you cannot see artwork, icons,
board layout or card faces. If — and only if — answering genuinely needs to
see them, reply with exactly:

NEED_IMAGES: <one sentence on what you need to see>

and nothing else. The pages will then be sent as images and you will be asked
again. Do not use this for anything the text can answer.""" if not want_images else '')
            ),
            messages=messages
        )
        cost_usd = usage_cost_usd(response.usage, RULES_PRICE_IN, RULES_PRICE_OUT)
        nzd_rate = float(os.getenv('NZD_RATE', '1.68'))
        cost_nzd = cost_usd * nzd_rate
        record_ai_usage('rules', cost_nzd, cost_usd, usage_tokens(response.usage))

        answer_text = response.content[0].text
        if answer_text.strip().startswith('NEED_IMAGES'):
            # The text wasn't enough. Don't spend the images automatically —
            # say what it costs and let the person decide.
            reason = answer_text.split(':', 1)[-1].strip()
            with_text = [b for b in available if b['has_text']]
            return jsonify({
                'success': False,
                'needs_images': True,
                'reason': reason,
                'books': available,
                'suggested': [b['name'] for b in with_text],
                'message': 'The rulebook text alone cannot answer this.',
                'cost_nzd': round(cost_nzd, 4), 'cost_usd': round(cost_usd, 4),
            })

        return jsonify({
            'success': True,
            'balance_nzd': balance_after(),
            'answer': answer_text,
            'books': available,
            'sources': sources_used,
            'cost_nzd': round(cost_nzd, 4),
            'cost_usd': round(cost_usd, 4)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Static-frontend JSON API ──────────────────────────────────────────────────

def valid_timezone(name):
    """An IANA zone name we can actually use, or None.

    The browser supplies this, so it is checked before it reaches the database
    — an unknown zone here would break every date calculation for that account.
    """
    name = (name or '').strip()
    if not name or len(name) > 64:
        return None
    try:
        ZoneInfo(name)
    except Exception:
        return None
    return name


@app.route('/api/set_timezone', methods=['POST'])
def api_set_timezone():
    """Change which zone this account's days are measured in."""
    name = valid_timezone((request.get_json() or {}).get('timezone'))
    if not name:
        return jsonify({'success': False, 'message': 'Unknown timezone.'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET timezone = %s WHERE id = %s",
                (name, current_user()['id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'timezone': name})


def user_public(user):
    return {'id': user['id'], 'email': user['email'],
            'display_name': user['display_name'], 'is_owner': user['is_owner'],
            'timezone': user.get('timezone')}


def recent_login_failures(cur, email):
    cur.execute("""
        SELECT COUNT(*) FROM login_attempts
        WHERE lower(email) = lower(%s)
          AND attempted_at > now() - make_interval(mins => %s)
    """, (email, LOGIN_WINDOW_MINUTES))
    return cur.fetchone()[0]


def owner_email():
    """Where notifications go: the owner's own address, unless overridden."""
    override = os.getenv('NOTIFY_EMAIL')
    if override:
        return override
    conn = raw_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE is_owner")
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except psycopg2.Error:
        return None
    finally:
        conn.close()


def send_notification(subject, body):
    """Send the owner an email. Never raises: a notification failing must not
    take down whatever triggered it.

    Needs SMTP_HOST, SMTP_USER and SMTP_PASSWORD in .env. With Gmail that
    means an app password, not the account password. Returns True if sent.
    """
    host = os.getenv('SMTP_HOST')
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    to_address = owner_email()
    if not (host and user and password and to_address):
        app.logger.warning('Email not configured — skipping notification: %s', subject)
        return False

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = os.getenv('SMTP_FROM', user)
    message['To'] = to_address
    message.set_content(body)

    port = int(os.getenv('SMTP_PORT', '587'))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15,
                                  context=ssl_module.create_default_context()) as server:
                server.login(user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls(context=ssl_module.create_default_context())
                server.login(user, password)
                server.send_message(message)
        app.logger.info('Sent notification to %s: %s', to_address, subject)
        return True
    except Exception as e:                      # network, auth, anything
        app.logger.error('Notification failed (%s): %s', subject, e)
        return False


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    display_name = (data.get('display_name') or '').strip() or None

    if '@' not in email or len(email) < 5:
        return jsonify({'success': False, 'message': 'A valid email is required.'}), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({'success': False,
                        'message': f'Password must be at least {MIN_PASSWORD_LENGTH} characters.'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (email, password_hash, display_name, status, timezone)
            VALUES (%s, %s, %s, 'pending', %s)
        """, (email, generate_password_hash(password), display_name,
              valid_timezone(data.get('timezone')) or 'Pacific/Auckland'))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        # Don't confirm which emails exist; the message is the same either way.
        return jsonify({'success': True, 'message':
                        'Thanks — your request is with the owner for approval.'})
    finally:
        cur.close()
        conn.close()

    site = os.getenv('SITE_URL', 'https://alkohout.github.io/board_game_logger')
    send_notification(
        f'Board Game Logger: {email} wants an account',
        f'{display_name or "Someone"} has requested an account.\n\n'
        f'  Name:  {display_name or "(not given)"}\n'
        f'  Email: {email}\n\n'
        f'They cannot log in until you approve them:\n'
        f'  {site}/users.html\n')

    return jsonify({'success': True, 'message':
                    'Thanks — your request is with the owner for approval.'})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required.'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if recent_login_failures(cur, email) >= LOGIN_MAX_FAILURES:
            return jsonify({'success': False, 'message':
                            'Too many attempts. Try again in a few minutes.'}), 429

        cur.execute("""
            SELECT id, email, display_name, status, is_owner, password_hash, token_version
            FROM users WHERE lower(email) = lower(%s)
        """, (email,))
        row = cur.fetchone()

        if not row or not check_password_hash(row[5], password):
            cur.execute("INSERT INTO login_attempts (email, ip) VALUES (%s, %s)",
                        (email, request.headers.get('X-Forwarded-For', request.remote_addr)))
            conn.commit()
            return jsonify({'success': False, 'message': 'Wrong email or password.'}), 401

        if row[3] == 'pending':
            return jsonify({'success': False, 'message':
                            'Your account is waiting for the owner to approve it.'}), 403
        if row[3] != 'active':
            return jsonify({'success': False, 'message': 'This account is disabled.'}), 403

        # A clean login clears the throttle for that email.
        cur.execute("DELETE FROM login_attempts WHERE lower(email) = lower(%s)", (email,))
        conn.commit()
        user = {'id': row[0], 'email': row[1], 'display_name': row[2],
                'status': row[3], 'is_owner': row[4], 'token_version': row[6]}
    finally:
        cur.close()
        conn.close()

    return jsonify({'success': True, 'token': issue_token(user['id'], user['token_version']),
                    'user': user_public(user)})


# The per-game trackers, and the title that means you own the game. A tracker
# only appears once an account has logged a play of it — advertising a page for
# a game someone doesn't own is just clutter.
GAME_TRACKERS = [
    {'key': 'spirit_island',  'label': 'Spirit Island',    'page': 'spirit_island.html',
     'match': '%spirit island%'},
    {'key': 'imperium',       'label': 'Imperium Stats',   'page': 'imperium.html',
     'match': '%imperium%'},
    {'key': 'sleeping_gods',  'label': 'Sleeping Gods Log', 'page': 'sleeping_gods.html',
     'match': '%sleeping gods%'},
]


@app.route('/api/me')
def api_me():
    user = current_user()
    payload = {'success': True, 'user': user_public(user)}
    conn = get_db_connection()
    cur = conn.cursor()

    # One query rather than three: which of the tracked games this account has
    # actually played. RLS keeps the counts to their own rows.
    cur.execute(
        'SELECT ' + ', '.join(
            f"count(*) FILTER (WHERE game_title ILIKE %s) > 0" for _ in GAME_TRACKERS
        ) + ' FROM games', [t['match'] for t in GAME_TRACKERS])
    played = cur.fetchone()
    payload['trackers'] = [
        {'key': t['key'], 'label': t['label'], 'page': t['page']}
        for t, has in zip(GAME_TRACKERS, played) if has
    ]

    if user['is_owner']:
        # Belt and braces: if the notification email ever fails or gets
        # filtered, a waiting request still shows up in the app.
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
        payload['pending_users'] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify(payload)


@app.route('/api/change_password', methods=['POST'])
def api_change_password():
    """Change your own password. Requires the current one, so a stolen token
    can't lock you out of your own account."""
    data = request.get_json() or {}
    current = data.get('current_password') or ''
    new = data.get('new_password') or ''
    if len(new) < MIN_PASSWORD_LENGTH:
        return jsonify({'success': False,
                        'message': f'New password must be at least {MIN_PASSWORD_LENGTH} characters.'}), 400

    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user['id'],))
    row = cur.fetchone()
    if not row or not check_password_hash(row[0], current):
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Current password is wrong.'}), 403

    cur.execute("""
        UPDATE users SET password_hash = %s, token_version = token_version + 1
        WHERE id = %s RETURNING token_version
    """, (generate_password_hash(new), user['id']))
    new_version = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    # Every token issued before now is dead, including any an attacker holds.
    # Hand this session a fresh one so the person changing it stays logged in.
    return jsonify({'success': True, 'token': issue_token(user['id'], new_version),
                    'message': 'Password changed. Any other signed-in devices have been logged out.'})


@app.route('/api/users')
def api_users():
    denied = owner_only()
    if denied:
        return denied
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, email, display_name, status, is_owner, created_at, approved_at
        FROM users ORDER BY (status = 'pending') DESC, created_at DESC
    """)
    users = [{'id': r[0], 'email': r[1], 'display_name': r[2], 'status': r[3],
              'is_owner': r[4], 'created_at': r[5].isoformat() if r[5] else None,
              'approved_at': r[6].isoformat() if r[6] else None}
             for r in cur.fetchall()]

    # What each account owns, so "Delete" can say what it is about to destroy
    # instead of asking for a blind yes.
    for u in users:
        u['data'] = count_user_data(cur, u['id'])
    # count_user_data leaves the policy pointing at the last user inspected.
    cur.execute("SELECT set_config('app.user_id', %s, true)", (str(current_user()['id']),))

    cur.close()
    conn.close()
    return jsonify({'success': True, 'users': users})


# Everything an account owns. Ordered so the tables are emptied before the
# users row they point at — there are no foreign keys here, so nothing cascades
# and nothing stops a user row being deleted out from under its own data.
#
# Anything gaining a user_id has to be added here as well. The sleeping gods
# tables got theirs in 014, after this list was written, so deleting an account
# left its campaign behind — rows owned by an id that no longer exists, visible
# to nobody and never cleaned up. check_owned_tables below now catches that.
USER_OWNED_TABLES = ('ai_usage', 'credit_purchases', 'rulebooks',
                     'sleeping_gods', 'sleeping_gods_totems', 'games')


def check_owned_tables():
    """Warn if a table has a user_id that account deletion doesn't clear."""
    try:
        conn = raw_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.columns
            WHERE table_schema = 'public' AND column_name = 'user_id'
        """)
        owned = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.warning('Could not check owned tables at startup: %s', e)
        return
    missed = sorted(owned - set(USER_OWNED_TABLES))
    if missed:
        app.logger.error('DELETING AN ACCOUNT WOULD ORPHAN ROWS IN %s — add them '
                         'to USER_OWNED_TABLES.', ', '.join(missed))


def count_user_data(cur, user_id):
    """How many rows an account owns.

    Row-level security hides other accounts' rows even from the owner, so
    counting someone else's data means pointing the policy at them for the
    duration. Transaction-scoped, so it reverts on commit.
    """
    cur.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
    counts = {}
    for table in USER_OWNED_TABLES:
        cur.execute(f'SELECT count(*) FROM {table} WHERE user_id = %s', (user_id,))
        counts[table] = cur.fetchone()[0]
    return counts


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """Remove an account and everything it owns. There is no undo."""
    denied = owner_only()
    if denied:
        return denied
    me = current_user()
    if user_id == me['id']:
        return jsonify({'success': False,
                        'message': "You can't delete your own account."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_owner, email FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'success': False, 'message': 'No such user.'}), 404
    if row[0]:
        cur.close(); conn.close()
        return jsonify({'success': False,
                        'message': "The owner account can't be deleted."}), 400
    email = row[1]

    try:
        deleted = {}
        # Both guards on purpose: set_config satisfies the RLS policy, and the
        # WHERE clause means a delete still can't run away if that policy is
        # ever loosened. A bare DELETE trusting RLS alone is one migration away
        # from emptying the table.
        cur.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
        for table in USER_OWNED_TABLES:
            cur.execute(f'DELETE FROM {table} WHERE user_id = %s', (user_id,))
            deleted[table] = cur.rowcount
        cur.execute("DELETE FROM users WHERE id = %s AND NOT is_owner", (user_id,))
        if cur.rowcount != 1:
            raise ValueError('user row not removed')
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        app.logger.exception('Deleting user %s failed', user_id)
        return jsonify({'success': False, 'message': f'Delete failed: {e}'}), 500

    cur.close()
    conn.close()
    app.logger.info('Deleted account %s (%s) and %s', user_id, email, deleted)
    return jsonify({'success': True, 'email': email, 'deleted': deleted})


@app.route('/api/users/<int:user_id>/status', methods=['POST'])
def api_set_user_status(user_id):
    denied = owner_only()
    if denied:
        return denied
    status = (request.get_json() or {}).get('status')
    if status not in ('active', 'disabled', 'pending'):
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
    if user_id == current_user()['id']:
        return jsonify({'success': False, 'message': "You can't change your own status."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_owner FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'No such user.'}), 404
    if row[0]:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': "The owner account can't be changed."}), 400

    cur.execute("""
        UPDATE users
        SET status = %s,
            approved_at = CASE WHEN %s = 'active' AND approved_at IS NULL
                               THEN now() ELSE approved_at END
        WHERE id = %s
    """, (status, status, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT game_title FROM games ORDER BY game_title")
    game_titles = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT game_title, COUNT(*) FROM games
        GROUP BY game_title ORDER BY COUNT(*) DESC LIMIT 5
    """)
    top_games = [{'game': r[0], 'count': r[1]} for r in cur.fetchall()]

    today = today_local()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    end_of_last_week = start_of_week - timedelta(days=1)
    start_of_last_week = end_of_last_week - timedelta(days=6)
    last_day_of_last_month = start_of_month - timedelta(days=1)
    start_of_last_month = last_day_of_last_month.replace(day=1)
    last_day_of_last_year = start_of_year - timedelta(days=1)
    start_of_last_year = last_day_of_last_year.replace(month=1, day=1)

    def count(q, *args): cur.execute(q, args); return cur.fetchone()[0]
    def most_played(start, end=None):
        if end:
            cur.execute("""SELECT game_title, COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s
                GROUP BY game_title ORDER BY COUNT(*) DESC LIMIT 1""", (start, end))
        else:
            cur.execute("""SELECT game_title, COUNT(*) FROM games WHERE date_played >= %s
                GROUP BY game_title ORDER BY COUNT(*) DESC LIMIT 1""", (start,))
        row = cur.fetchone()
        return {'game': row[0], 'count': row[1]} if row else {'game': None, 'count': 0}

    # Period counts
    td = count("SELECT COUNT(*) FROM games WHERE date_played = %s", today)
    yd = count("SELECT COUNT(*) FROM games WHERE date_played = %s", today - timedelta(days=1))
    tw = count("SELECT COUNT(*) FROM games WHERE date_played >= %s", start_of_week)
    tm = count("SELECT COUNT(*) FROM games WHERE date_played >= %s", start_of_month)
    ty = count("SELECT COUNT(*) FROM games WHERE date_played >= %s", start_of_year)
    lw = count("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", start_of_last_week, end_of_last_week)
    lm = count("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", start_of_last_month, last_day_of_last_month)
    ly = count("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", start_of_last_year, last_day_of_last_year)

    # Averages
    ref = date(2024, 1, 1)
    total_days = (start_of_week - ref).days
    num_weeks = total_days // 7 if total_days >= 7 else 0
    if num_weeks:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (ref, start_of_week))
        weekly_avg = round(cur.fetchone()[0] / num_weeks)
    else:
        weekly_avg = 0
    num_months = (start_of_month.year - ref.year) * 12 + (start_of_month.month - ref.month)
    if num_months:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (ref, start_of_month))
        monthly_avg = round(cur.fetchone()[0] / num_months)
    else:
        monthly_avg = 0
    ref_y = date(2023, 1, 1)
    num_years = start_of_year.year - ref_y.year
    if num_years:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (ref_y, start_of_year))
        yearly_avg = round(cur.fetchone()[0] / num_years)
    else:
        yearly_avg = 0

    num_days = (today - ref).days
    if num_days > 0:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (ref, today))
        daily_avg = round(cur.fetchone()[0] / num_days, 1)
    else:
        daily_avg = 0

    records = {k: {'count': v['count'], 'start': v['start'].isoformat() if v['start'] else None}
               for k, v in period_records(cur).items()}

    result = {
        'game_titles': game_titles,
        'top_games': top_games,
        'today': today.isoformat(),
        'games_played': {
            'today': td, 'yesterday': yd,
            'this_week': tw, 'this_month': tm, 'this_year': ty,
            'last_week': lw, 'last_month': lm, 'last_year': ly,
            'daily_avg': daily_avg,
            'weekly_avg': weekly_avg, 'monthly_avg': monthly_avg, 'yearly_avg': yearly_avg,
        },
        'records': records,
        'most_played': {
            'this_week': most_played(start_of_week),
            'last_week': most_played(start_of_last_week, end_of_last_week),
            'this_month': most_played(start_of_month),
            'last_month': most_played(start_of_last_month, last_day_of_last_month),
            'this_year': most_played(start_of_year),
            'last_year': most_played(start_of_last_year, last_day_of_last_year),
        },
    }
    cur.close()
    conn.close()
    return jsonify(result)


@app.route('/api/add_game', methods=['POST'])
def api_add_game():
    data = request.get_json() or {}
    spirit, adversary, level, scenario = spirit_island_fields(data)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO games (date_played, game_title, notes, result, level, my_score, bot_score,"
            " spirit, adversary, adversary_level, scenario, civilisation)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (data.get('date_played'), data.get('game_title'), data.get('notes', ''),
             data.get('result', ''), data.get('level', ''), data.get('my_score', ''), data.get('bot_score', ''),
             spirit, adversary, level, scenario, imperium_civilisation(data))
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/games_overview')
def api_games_overview():
    conn = get_db_connection()
    cur = conn.cursor()
    today = today_local()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    end_of_last_week = start_of_week - timedelta(days=1)
    start_of_last_week = end_of_last_week - timedelta(days=6)
    end_of_last_month = start_of_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)
    end_of_last_year = start_of_year - timedelta(days=1)
    start_of_last_year = end_of_last_year.replace(month=1, day=1)

    def fetch(start, end):
        cur.execute("""SELECT game_title, COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s
            GROUP BY game_title ORDER BY COUNT(*) DESC""", (start, end))
        return [{'game': r[0], 'count': r[1]} for r in cur.fetchall()]

    result = {
        'this_week': fetch(start_of_week, today),
        'this_month': fetch(start_of_month, today),
        'this_year': fetch(start_of_year, today),
        'last_week': fetch(start_of_last_week, end_of_last_week),
        'last_month': fetch(start_of_last_month, end_of_last_month),
        'last_year': fetch(start_of_last_year, end_of_last_year),
    }
    cur.close()
    conn.close()
    return jsonify(result)


@app.route('/api/all_games')
def api_all_games():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT game_title, RANK() OVER (ORDER BY COUNT(*) DESC), COUNT(*),
            COALESCE((SELECT notes FROM games g2 WHERE g2.game_title = g.game_title
                AND g2.notes IS NOT NULL ORDER BY g2.date_played DESC LIMIT 1), '')
        FROM games g GROUP BY game_title ORDER BY game_title
    """)
    rows = [{'game': r[0], 'rank': r[1], 'play_count': r[2], 'latest_note': r[3]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)


# The civilisations grouped by expansion, with difficulty stars, exactly as
# the page has always listed them. A play records its civilisation in the
# `level` column, matched case-insensitively the way the old page did.
IMPERIUM_CIVS = [
    # Classics
    ('Classics', 'Carthaginians', 2),
    ('Classics', 'Celts', 2),
    ('Classics', 'Greeks', 3),
    ('Classics', 'Macedonians', 1),
    ('Classics', 'Persians', 1),
    ('Classics', 'Scythians', 2),
    ('Classics', 'Vikings', 3),
    # Legends
    ('Legends', 'Arthurians', 5),
    ('Legends', 'Atlanteans', 3),
    ('Legends', 'Egyptians', 3),
    ('Legends', 'Mauryans', 2),
    ('Legends', 'Minoans', 2),
    ('Legends', 'Olmecs', 4),
    ('Legends', 'Qin', 2),
    ('Legends', 'Utopians', 6),
    # Horizons
    ('Horizons', 'Abbasids', 2),
    ('Horizons', 'Aksumites', 2),
    ('Horizons', 'Cultists', 6),
    ('Horizons', 'Guptas', 2),
    ('Horizons', 'Inuit', 4),
    ('Horizons', 'Japanese', 2),
    ('Horizons', 'Magyars', 2),
    ('Horizons', 'Martians', 2),
    ('Horizons', 'Mayans', 2),
    ('Horizons', 'Polynesians', 5),
    ('Horizons', 'Sassanids', 4),
    ('Horizons', 'Tang', 3),
    ('Horizons', 'Wagadou', 3),
]


# Spirit Island, for the four products owned: base, Branch & Claw, Jagged Earth
# and Nature Incarnate. Promo Pack 2 / Feather & Flame content (the Scotland
# adversary, A Diversity of Spirits, Varied Terrains) is deliberately absent —
# add it here if those are ever picked up, and the page follows automatically.
SPIRIT_ISLAND_SPIRITS = [
    ('Spirit Island', "Lightning's Swift Strike"),
    ('Spirit Island', 'River Surges in Sunlight'),
    ('Spirit Island', 'Vital Strength of the Earth'),
    ('Spirit Island', 'Shadows Flicker Like Flame'),
    ('Spirit Island', 'Thunderspeaker'),
    ('Spirit Island', 'A Spread of Rampant Green'),
    ('Spirit Island', "Ocean's Hungry Grasp"),
    ('Spirit Island', 'Bringer of Dreams and Nightmares'),
    ('Branch & Claw', 'Keeper of the Forbidden Wilds'),
    ('Branch & Claw', 'Sharp Fangs Behind the Leaves'),
    ('Jagged Earth', "Stone's Unyielding Defiance"),
    ('Jagged Earth', 'Shifting Memory of Ages'),
    ('Jagged Earth', 'Grinning Trickster Stirs Up Trouble'),
    ('Jagged Earth', 'Lure of the Deep Wilderness'),
    ('Jagged Earth', 'Many Minds Move as One'),
    ('Jagged Earth', 'Volcano Looming High'),
    ('Jagged Earth', 'Shroud of Silent Mist'),
    ('Jagged Earth', 'Vengeance as a Burning Plague'),
    ('Jagged Earth', 'Starlight Seeks Its Form'),
    ('Jagged Earth', 'Fractured Days Split the Sky'),
    ('Nature Incarnate', 'Ember-Eyed Behemoth'),
    ('Nature Incarnate', 'Hearth-Vigil'),
    ('Nature Incarnate', 'Breath of Darkness Down Your Spine'),
    ('Nature Incarnate', 'Relentless Gaze of the Sun'),
    ('Nature Incarnate', 'Towering Roots of the Jungle'),
    ('Nature Incarnate', 'Dances Up Earthquakes'),
    ('Nature Incarnate', 'Wandering Voice Keens Delirium'),
    ('Nature Incarnate', 'Wounded Waters Bleeding'),
]

SPIRIT_ISLAND_ADVERSARIES = [
    ('Spirit Island', 'Brandenburg-Prussia'),
    ('Spirit Island', 'England'),
    ('Spirit Island', 'Sweden'),
    ('Branch & Claw', 'France'),
    ('Jagged Earth', 'Habsburg Monarchy'),
    ('Jagged Earth', 'Russia'),
    ('Nature Incarnate', 'Habsburg Mining Expedition'),
]

SPIRIT_ISLAND_SCENARIOS = [
    ('Spirit Island', 'Blitz'),
    ('Spirit Island', "Guard the Isle's Heart"),
    ('Spirit Island', 'Rituals of Terror'),
    ('Spirit Island', 'Dahan Insurrection'),
    ('Branch & Claw', 'Second Wave'),
    ('Branch & Claw', 'Powers Long Forgotten'),
    ('Branch & Claw', 'Ward the Shores'),
    ('Branch & Claw', 'Rituals of the Destroying Flame'),
    ('Jagged Earth', 'Elemental Invocation'),
    ('Jagged Earth', 'Despicable Theft'),
    ('Jagged Earth', 'The Great River'),
    ('Nature Incarnate', 'Destiny Unfolds'),
    ('Nature Incarnate', 'Surges of Colonization'),
]

# Titles that count as a Spirit Island play. Matched with ILIKE, so this also
# picks up Horizons of Spirit Island — and pointedly not "Bah Humbug: the
# giving spirit", which a bare '%spirit%' would have swept in.
SPIRIT_ISLAND_TITLE = '%spirit island%'

# The adversary dial, written as "Level 3", "lvl 3", "L3" or just "3" after the
# name. Habsburg is the one name that appears twice, so longest-match wins.
ADVERSARY_LEVEL_RE = re.compile(r'(?:level|lvl|l)\s*([1-6])\b', re.I)


def _tally(rows):
    return {
        'won': sum(1 for p in rows if 'won' in (p['result'] or '').lower()),
        'lost': sum(1 for p in rows if 'lost' in (p['result'] or '').lower()),
        # plays counts every logged game, including the many with no result
        # recorded — otherwise a spirit played six times looks unplayed.
        'plays': len(rows),
    }


def _best_level(rows):
    """Highest adversary level actually beaten in these plays."""
    levels = [p['adversary_level'] for p in rows
              if p['adversary_level'] and 'won' in (p['result'] or '').lower()]
    return max(levels) if levels else None


# Losses at one setup with nothing to show for them. Not a rule, a nudge: the
# point of the page is partly to notice when to stop banging at the same wall.
STUCK_AFTER_LOSSES = 3

ADVERSARY_LEVELS = [1, 2, 3, 4, 5, 6]


def adversary_grids_by(plays, field):
    """One adversary grid per spirit, or per scenario.

    Scenarios combine with adversaries — "Blitz against England 3" is as much
    a setup as either on its own — so both get the same treatment. Only values
    actually taken against an adversary are included: twenty-eight empty grids
    would bury the one with something in it.
    """
    used = [v for v in (p[field] for p in plays if p['adversary']) if v]
    out = []
    for value in dict.fromkeys(used):
        mine = [p for p in plays if p[field] == value]
        out.append({
            'name': value,
            'groups': adversary_grid(mine),
            **_tally([p for p in mine if p['adversary']]),
        })
    out.sort(key=lambda s: (-s['plays'], s['name']))
    return out


def adversary_grid(plays):
    """Each adversary against each of its six levels.

    A setup is an adversary at a level, so that is what the table is made of —
    a flat per-adversary tally hides that five losses at level 3 and a win at
    level 1 are different situations.
    """
    groups = []
    for product, name in SPIRIT_ISLAND_ADVERSARIES:
        key = name.lower()
        rows = [p for p in plays if (p['adversary'] or '').lower() == key]
        cells = []
        for level in ADVERSARY_LEVELS:
            at = [p for p in rows if p['adversary_level'] == level]
            tally = _tally(at)
            cells.append({
                'level': level, **tally,
                # Losses with no win here yet: the "maybe try something else"
                # signal, and the reason losses are counted separately at all.
                'stuck': tally['lost'] >= STUCK_AFTER_LOSSES and tally['won'] == 0,
            })
        # Plays whose level was never written down still belong to the
        # adversary; they just can't sit in a column.
        no_level = _tally([p for p in rows if not p['adversary_level']])
        if not groups or groups[-1]['product'] != product:
            groups.append({'product': product, 'items': []})
        groups[-1]['items'].append({
            'name': name, 'cells': cells, 'best_level': _best_level(rows),
            'no_level': no_level, **_tally(rows),
        })
    return groups


def spirit_island_group(entries, plays, field, by_spirit=False):
    """Won/lost per named thing, grouped by the product it came in.

    by_spirit adds the spirits used against each one. The pairing is already on
    the row — a play records its spirit and its adversary together — it just
    isn't visible in a flat tally.
    """
    groups = []
    for product, name in entries:
        key = name.lower()
        rows = [p for p in plays if (p[field] or '').lower() == key]
        item = {'name': name, **_tally(rows)}

        if field == 'adversary':
            item['best_level'] = _best_level(rows)

        if by_spirit:
            seen = []
            for spirit in dict.fromkeys(p['spirit'] for p in rows):
                against = [p for p in rows if p['spirit'] == spirit]
                entry = {
                    # Plays from before the pickers existed often name no
                    # spirit. Say so rather than dropping them, or the
                    # sub-rows won't add up to the row above them.
                    'name': spirit or 'not recorded',
                    'recorded': spirit is not None,
                    **_tally(against),
                }
                if field == 'adversary':
                    entry['best_level'] = _best_level(against)
                seen.append(entry)
            # Most-played first; the unrecorded bucket always sits last.
            item['spirits'] = sorted(
                seen, key=lambda s: (s['recorded'] is False, -s['plays'], s['name']))

        if not groups or groups[-1]['product'] != product:
            groups.append({'product': product, 'items': []})
        groups[-1]['items'].append(item)
    return groups


# The official Sleeping Gods achievements sheet, in its three sections. Used
# to seed a new account's checklist; the owner's own rows predate this and use
# a few different spellings, which is why the page classifies by shape (below)
# rather than by matching these strings.
SLEEPING_GODS_TOTEMS = [
    'Axe of the Cinderlands', 'Blade of Thrack', 'Book of Fame and Infame',
    'Centipede Crown (Ruin)', 'Clockwork Owl', 'Cursed Ruby (Ruin)',
    'Ethereal Mask (Dungeons)', 'Fish Bone Spear (Dungeons)', 'Gate Stone',
    'God Stone', "Hunter's Pebble (Ruin)", 'Key Stone', 'Lava Sword (Ruin)',
    'Life Seed', "Meecra's Guitar", "Meecra's Salt", "Mystic's Idol (Ruin)",
    'Nautilus Stone (Dungeons)', 'Nightmare Stone (Ruin)',
    'Obsidian Greaves (Dungeons)', 'Obsidian Heart', "Ohmlude's Crystal",
    'Pigment Stone (Ruin)', 'Puzzle Box', "Raltolde's Shield",
    "Raltolde's Spear", 'Shadow Lantern (Ruin)', "Shorme's Hammer",
    'Snake Bangle', 'Stone of Absence (Ruin)', 'Stone of Bargaining',
    'Stone of Blood', 'Stone of Cats', 'Stone of Chains',
    'Stone of Changing (Dungeons)', 'Stone of Deceit', 'Stone of Earthquakes',
    'Stone of Fitness', 'Stone of Freezing', 'Stone of Gluttony',
    'Stone of Healing', 'Stone of the Lost (Ruin)', 'Stone of Madness',
    'Stone of Many Eyes', 'Stone of Mending', 'Stone of Mirrors (Ruin)',
    'Stone of Muscle', 'Stone of Music', 'Stone of Mist (Ruin)',
    'Stone of Riddles', 'Stone of Roaming', 'Stone of Sacrifice',
    'Stone of Screaming (Ruin)', 'Stone of Shanties', 'Stone of Spirits (Ruin)',
    'Stone of Squids', 'Stone of Storms', 'Stone of the Deep',
    'Stone of the Hunt', 'Stone of the Mind', 'Stone of the Wind',
    'Stone of the Wind & Waves', 'Stone of Teeth (Ruin)', 'Stone of Time',
    'Stone of Undeath', 'Stone of Vengeance (Ruin)', 'Stone of Vim (Dungeons)',
    'Stone of Weakness', 'Stone of Worldly Sorrows (Ruin)',
    'Sword of the Duelist', 'The Perpetual Flame', "Thrack's Charm",
    "Valard's Prism (Ruin)", "Zacra's Mask", 'Zrell Stone (Ruin)',
]

# The leading number is the count of totems-and-endings that unlocks the card,
# which is why the threshold is read off the name rather than kept separately.
SLEEPING_GODS_UNLOCKED = [
    '4 (Quests 171-172)', '7 (Quest 169-170)', '9 (Quest 168)',
    '11 (Quest 174)', '13 (Quest 175)', '15 (Quests 176-177)',
    '18 (Quest 178-180)', '22 (Quest 173)',
]

SLEEPING_GODS_ENDINGS = [f'#{n}' for n in range(1, 14)]

SLEEPING_GODS_SHEET = (SLEEPING_GODS_TOTEMS + SLEEPING_GODS_UNLOCKED
                       + SLEEPING_GODS_ENDINGS)

_ENDING_RE  = re.compile(r'^#\s*(\d+)$')
_UNLOCKED_RE = re.compile(r'^(\d+)\s*\(Quests?\b[^)]*\)$', re.I)


def sleeping_gods_category(name):
    """Which section of the sheet a row belongs to, and its unlock threshold.

    Matched by shape, not by exact string. The owner's list predates the
    seeded one and differs in small ways — "Quests 171 - 172" with spaces,
    "Ohmludes's Crystal" with an extra s — and position can't be used either,
    because the page used to slice the array by index and any reordering (or a
    row added by hand) silently regrouped everything.
    """
    name = (name or '').strip()
    m = _ENDING_RE.match(name)
    if m:
        return 'ending', int(m.group(1))
    m = _UNLOCKED_RE.match(name)
    if m:
        return 'unlocked', int(m.group(1))
    return 'totem', None



def imperium_civilisation(data):
    """The deck faced, validated against the official list.

    Same rule as the Spirit Island pickers: only a name we know is stored, so
    the stats page can count on it rather than parsing prose.
    """
    value = (data.get('civilisation') or '').strip()
    return next((n for _, n, _ in IMPERIUM_CIVS if n.lower() == value.lower()), None)


@app.route('/api/imperium_options')
def api_imperium_options():
    """The civilisation picker on the log form."""
    return jsonify({'civilisations': [
        {'name': n, 'expansion': e, 'stars': st} for e, n, st in IMPERIUM_CIVS]})


def spirit_island_fields(data):
    """Validate the Spirit Island pickers off a request body.

    Shared by logging and editing so the two can't drift: only names from the
    official lists are stored, which is what lets the stats page count on them.
    """
    def picked(field, allowed):
        value = (data.get(field) or '').strip()
        return next((n for _, n in allowed if n.lower() == value.lower()), None)

    level = data.get('adversary_level')
    try:
        level = int(level) if str(level or '').strip() else None
    except (TypeError, ValueError):
        level = None
    if level is not None and not 1 <= level <= 6:
        level = None

    adversary = picked('adversary', SPIRIT_ISLAND_ADVERSARIES)
    return (picked('spirit', SPIRIT_ISLAND_SPIRITS),
            adversary,
            # A level with no adversary is meaningless and would skew "best beaten".
            level if adversary else None,
            picked('scenario', SPIRIT_ISLAND_SCENARIOS))


PLAY_COLUMNS = ('id', 'date_played', 'game_title', 'result', 'level', 'my_score',
                'bot_score', 'notes', 'spirit', 'adversary', 'adversary_level',
                'scenario', 'civilisation')


def play_row(row):
    play = dict(zip(PLAY_COLUMNS, row))
    play['date_played'] = play['date_played'].isoformat() if play['date_played'] else None
    return play


@app.route('/api/game_info')
def api_game_info():
    """Everything the Games tab shows about one game.

    The search term is resolved to a single real title first. The old endpoint
    counted every title matching the term but looked up the ranking under the
    term itself, so searching "spirit" ranked nothing and counted several
    different games together.
    """
    term = (request.args.get('term') or '').strip()
    if not term:
        return jsonify({'success': False, 'message': 'No game given.'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cols = ', '.join(PLAY_COLUMNS)

    # Most recently played wins; id breaks ties, so a game logged twice on one
    # date resolves to the row entered last rather than an arbitrary one.
    cur.execute(f"""SELECT {cols} FROM games WHERE game_title ILIKE %s
                    ORDER BY date_played DESC, id DESC LIMIT 1""", (f'%{term}%',))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'success': False, 'message': f'No plays found for "{term}".'}), 404
    last = play_row(row)
    title = last['game_title']

    # The most recent play that recorded anything — where the "what to try
    # next" note lives, which is usually a play or two back.
    cur.execute(f"""
        SELECT {cols} FROM games
        WHERE game_title = %s
          AND ( (notes  IS NOT NULL AND btrim(notes)  NOT IN ('', 'null')) OR
                (result IS NOT NULL AND btrim(result) NOT IN ('', 'null')) OR
                spirit IS NOT NULL OR adversary IS NOT NULL OR scenario IS NOT NULL )
        ORDER BY date_played DESC, id DESC LIMIT 1
    """, (title,))
    row = cur.fetchone()
    detailed = play_row(row) if row else None

    today = today_local()
    cur.execute("""
        SELECT count(*),
               count(*) FILTER (WHERE result ILIKE '%%won%%'),
               count(*) FILTER (WHERE result ILIKE '%%lost%%'),
               count(*) FILTER (WHERE date_played >= %s),
               count(*) FILTER (WHERE date_played >= %s),
               count(*) FILTER (WHERE date_played >= %s),
               min(date_played), max(date_played)
        FROM games WHERE game_title = %s
    """, (today - timedelta(days=today.weekday()), today.replace(day=1),
          today.replace(month=1, day=1), title))
    (total, won, lost, this_week, this_month, this_year, first, latest) = cur.fetchone()

    # Rank by play count across every game, then read this title's place off it.
    cur.execute("""
        SELECT rank FROM (
            SELECT game_title, RANK() OVER (ORDER BY count(*) DESC) AS rank
            FROM games GROUP BY game_title
        ) ranked WHERE game_title = %s
    """, (title,))
    row = cur.fetchone()
    ranking = row[0] if row else None
    cur.execute("SELECT count(DISTINCT game_title) FROM games")
    of_games = cur.fetchone()[0]

    cur.close()
    conn.close()
    return jsonify({
        'success': True,
        'title': title,
        'last': last,
        'latest_detailed': detailed,
        'stats': {
            'total_plays': total, 'won': won, 'lost': lost,
            'this_week': this_week, 'this_month': this_month, 'this_year': this_year,
            'first_played': first.isoformat() if first else None,
            'last_played': latest.isoformat() if latest else None,
            'ranking': ranking, 'of_games': of_games,
        },
    })


@app.route('/api/update_play', methods=['POST'])
def api_update_play():
    """Correct a play that was logged wrong.

    Targets one row by id rather than "the most recent play of this title",
    which guessed at the row whenever a game was logged twice on a date.
    Row-level security is what stops an id belonging to someone else being
    edited — the UPDATE simply matches nothing.
    """
    data = request.get_json() or {}
    try:
        play_id = int(data.get('id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Which play?'}), 400
    if not (data.get('date_played') or '').strip():
        return jsonify({'success': False, 'message': 'A date is required.'}), 400

    spirit, adversary, level, scenario = spirit_island_fields(data)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE games SET date_played = %s, result = %s, level = %s,
                             my_score = %s, bot_score = %s, notes = %s,
                             spirit = %s, adversary = %s, adversary_level = %s,
                             scenario = %s, civilisation = %s
            WHERE id = %s
        """, (data.get('date_played'), data.get('result', ''), data.get('level', ''),
              data.get('my_score', ''), data.get('bot_score', ''), data.get('notes', ''),
              spirit, adversary, level, scenario,
              imperium_civilisation(data), play_id))
        if cur.rowcount != 1:
            conn.rollback()
            cur.close(); conn.close()
            return jsonify({'success': False, 'message': 'No such play.'}), 404
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500
    cur.close()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/spirit_island_options')
def api_spirit_island_options():
    """The pickers on the log form. One source of truth with the stats page."""
    return jsonify({
        'spirits': [n for _, n in SPIRIT_ISLAND_SPIRITS],
        'adversaries': [n for _, n in SPIRIT_ISLAND_ADVERSARIES],
        'scenarios': [n for _, n in SPIRIT_ISLAND_SCENARIOS],
    })


@app.route('/api/spirit_island_stats')
def api_spirit_island_stats():
    # Unlike Imperium, this reads `games`, which is row-level-secured — so it
    # needs no owner gate. Every account sees its own Spirit Island plays.
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""SELECT spirit, adversary, adversary_level, scenario, result
                   FROM games WHERE game_title ILIKE %s""", (SPIRIT_ISLAND_TITLE,))
    plays = [{'spirit': r[0], 'adversary': r[1], 'adversary_level': r[2],
              'scenario': r[3], 'result': r[4]} for r in cur.fetchall()]
    cur.close()
    conn.close()

    by_spirit = adversary_grids_by(plays, 'spirit')
    by_scenario = adversary_grids_by(plays, 'scenario')

    recorded = sum(1 for p in plays
                   if p['spirit'] or p['adversary'] or p['scenario'])
    return jsonify({
        'spirits': spirit_island_group(SPIRIT_ISLAND_SPIRITS, plays, 'spirit'),
        'adversaries': spirit_island_group(
            SPIRIT_ISLAND_ADVERSARIES, plays, 'adversary', by_spirit=True),
        'adversary_grid': adversary_grid(plays),
        'adversary_levels': ADVERSARY_LEVELS,
        'adversary_by_spirit': by_spirit,
        'adversary_by_scenario': by_scenario,
        'stuck_after_losses': STUCK_AFTER_LOSSES,
        'scenarios': spirit_island_group(
            SPIRIT_ISLAND_SCENARIOS, plays, 'scenario', by_spirit=True),
        'total_plays': len(plays),
        # Plays with nothing recorded aren't a bug to hide — the page says so,
        # otherwise the totals look wrong against the Games tab.
        'unrecorded_plays': len(plays) - recorded,
    })


# Imperium: you always play Romans, so the deck that varies is the opponent's.
# Romans is deliberately absent from IMPERIUM_CIVS, which is why "Romans (me)"
# can never be read as the deck faced.
_IMPERIUM_SPLIT = re.compile(r'\bv(?:s|ersus)\b\.?', re.I)


def imperium_civ_from_text(text):
    """Pull the opponent deck out of a free-text Imperium note.

    Used both to read plays logged before there was a field for it, and to
    backfill them. Singular spellings count: eleven plays were written
    "Viking", "Greek", "Carthaginian", and the old exact matching dropped them.
    Anything after "vs"/"versus" wins, since what comes before it is you.
    """
    whole = (text or '').lower()
    if not whole:
        return None
    parts = _IMPERIUM_SPLIT.split(whole, maxsplit=1)
    hay = parts[1] if len(parts) > 1 else whole
    best = None
    for _, name, _ in IMPERIUM_CIVS:
        low = name.lower()
        forms = [low] + ([low[:-1]] if low.endswith('s') else [])
        for form in forms:
            if re.search(r'\b' + re.escape(form) + r'\b', hay):
                # Longest wins, so "Qin" can't shadow a longer name sharing it.
                if best is None or len(form) > len(best[1]):
                    best = (name, form)
                break
    return best[0] if best else None


def imperium_civ_of(play):
    """The deck faced: the recorded field if set, else the old free text."""
    if play.get('civilisation'):
        return play['civilisation']
    return imperium_civ_from_text(play.get('level'))


@app.route('/api/imperium_stats')
def api_imperium_stats():
    # The imperium view reads `games` with security_invoker, so it has always
    # applied row-level security as whoever is asking — the owner gate that
    # used to sit here was the only thing making this the owner's alone.
    conn = get_db_connection()
    cur = conn.cursor()
    # One pass over the plays; the per-civilisation tally happens here rather
    # than in the 56 separate count queries the old page used.
    cur.execute("SELECT level, result, civilisation FROM imperium")
    plays = [{'level': r[0], 'result': r[1], 'civilisation': r[2]}
             for r in cur.fetchall()]
    cur.close()
    conn.close()

    # The recorded deck if there is one, otherwise read the old free text.
    # Resolved once per play so a play can never be counted under two decks.
    for p in plays:
        p['civ'] = imperium_civ_of(p)
        p['res'] = (p['result'] or '').lower()

    expansions = []
    for expansion, name, stars in IMPERIUM_CIVS:
        mine = [p for p in plays if p['civ'] == name]
        if not expansions or expansions[-1]['expansion'] != expansion:
            expansions.append({'expansion': expansion, 'civilisations': []})
        expansions[-1]['civilisations'].append({
            'name': name, 'stars': stars,
            'won': sum(1 for p in mine if 'won' in p['res']),
            'lost': sum(1 for p in mine if 'lost' in p['res']),
            # Plays counts every game against this deck, recorded result or
            # not — the same reason the Spirit Island page shows it.
            'plays': len(mine),
            # How many still rely on the free text. Zero once backfilled, and
            # worth seeing if it ever climbs again.
            'from_text': sum(1 for p in mine if not p['civilisation']),
        })

    # Text that names no known deck: a new expansion, a typo, or a play with no
    # opponent recorded at all.
    unmatched = sorted({(p['level'] or '').strip() for p in plays
                        if (p['level'] or '').strip() and not p['civ']})

    return jsonify({'expansions': expansions, 'unmatched_levels': unmatched,
                    'total_plays': len(plays),
                    'recorded': sum(1 for p in plays if p['civilisation']),
                    'from_text': sum(1 for p in plays if p['civ'] and not p['civilisation'])})


@app.route('/api/sleeping_gods_totems_data')
def api_sleeping_gods_totems_data():
    # Per-account since 014: row-level security scopes these rows, so the
    # endpoint no longer needs an owner gate.
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sleeping_gods_totems")
    if cur.fetchone()[0] == 0:
        # First visit: hand this account the whole sheet — 75 totems, 8
        # unlocked cards and 13 endings. user_id comes from the column
        # default, which reads the same setting the policy checks.
        cur.executemany("INSERT INTO sleeping_gods_totems (totem, found) VALUES (%s, false)",
                        [(t,) for t in SLEEPING_GODS_SHEET])
        conn.commit()
    cur.execute("SELECT id, totem, found FROM sleeping_gods_totems ORDER BY id")
    rows = []
    for r in cur.fetchall():
        category, threshold = sleeping_gods_category(r[1])
        rows.append({'id': r[0], 'totem': r[1], 'found': r[2],
                     'category': category, 'unlocks_at': threshold})
    cur.close()
    conn.close()
    # The count that unlocks cards is totems and endings only — the cards
    # themselves don't count towards their own thresholds.
    return jsonify({
        'totems': rows,
        'achieved': sum(1 for r in rows if r['found'] and r['category'] != 'unlocked'),
    })


@app.route('/api/add_sleeping_gods', methods=['POST'])
def api_add_sleeping_gods():
    # Per-account since 014: these rows carry a user_id and row-level security
    # scopes them, so the endpoint is no longer the boundary.
    try:
        d = request.get_json() or {}
        def i(k): return int(d.get(k) or 0)
        def s(k): return str(d.get(k) or '')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sleeping_gods (location, part, required_keyword, gained_keyword, visited, notes, combat, combat_level, gained, req_coins, req_meat, req_veg, req_grain, req_wood, req_artifacts, gain_coins, gain_meat, gain_veg, gain_grain, gain_wood, gain_artifacts, gain_xp, gain_ship_damage, gain_ship_repair, gain_crew_damage, gain_crew_health, gain_low_morale, gain_fright, gain_venom, gain_weakness, gain_madness, remove_low_morale, remove_fright, remove_venom, remove_weakness, remove_madness, gain_totem, challenge, challenge_level, gain_adventure) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (i('location'), s('part'), s('required_keyword'), s('gained_keyword'),
             '1' if d.get('visited') else '0', s('notes'),
             '1' if d.get('combat') else '0', i('combat_level'), s('gained'),
             i('req_coins'), i('req_meat'), i('req_veg'), i('req_grain'), i('req_wood'), i('req_artifacts'),
             i('gain_coins'), i('gain_meat'), i('gain_veg'), i('gain_grain'), i('gain_wood'), i('gain_artifacts'),
             i('gain_xp'), i('gain_ship_damage'), i('gain_ship_repair'), i('gain_crew_damage'), i('gain_crew_health'),
             i('gain_low_morale'), i('gain_fright'), i('gain_venom'), i('gain_weakness'), i('gain_madness'),
             i('remove_low_morale'), i('remove_fright'), i('remove_venom'), i('remove_weakness'), i('remove_madness'),
             s('gain_totem'), s('challenge'), i('challenge_level'), i('gain_adventure'))
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/rules_assistant_data')
def api_rules_assistant_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT game_title FROM games ORDER BY game_title")
    game_titles = [row[0] for row in cur.fetchall()]
    try:
        cur.execute("SELECT game_title, rulebook_name, bgg_forum_cache FROM rulebooks WHERE pdf_data IS NOT NULL ORDER BY game_title, rulebook_name")
        rulebook_rows = cur.fetchall()
    except Exception:
        conn.rollback()
        cur.execute("SELECT game_title FROM rulebooks WHERE pdf_data IS NOT NULL")
        rulebook_rows = [(r[0], 'Base', None) for r in cur.fetchall()]
    cur.close()
    conn.close()
    has_rulebook = {g: any(r[0] == g for r in rulebook_rows) for g in game_titles}
    rulebook_names = {g: [r[1] for r in rulebook_rows if r[0] == g] for g in game_titles}
    has_bgg = {g: any(r[0] == g and r[2] for r in rulebook_rows) for g in game_titles}
    return jsonify({'game_titles': game_titles, 'has_rulebook': has_rulebook, 'rulebook_names': rulebook_names, 'has_bgg': has_bgg})


# ── Optional self-hosted model ────────────────────────────────────────────────
# Point LOCAL_LLM_URL at anything speaking the OpenAI chat API — Ollama,
# llama.cpp's server, vLLM — and name the features it should answer:
#
#   LOCAL_LLM_URL=http://192.168.1.50:11434/v1
#   LOCAL_LLM_MODEL=qwen2.5-coder:14b
#   LOCAL_LLM_FOR=db_query
#
# Left unset, everything goes to Claude exactly as before. Per-feature because
# the two are very different asks: Database Query sends ~800 tokens and wants
# one SELECT, which a 14B model on a CPU manages; the Rules Assistant sends
# 65,000 tokens of rulebook, which needs a GPU to be bearable.

LOCAL_LLM_URL = os.getenv('LOCAL_LLM_URL')
LOCAL_LLM_MODEL = os.getenv('LOCAL_LLM_MODEL', 'qwen2.5-coder:14b')
LOCAL_LLM_FOR = {f.strip() for f in os.getenv('LOCAL_LLM_FOR', '').split(',') if f.strip()}
LOCAL_LLM_TIMEOUT = int(os.getenv('LOCAL_LLM_TIMEOUT', '300'))
# On by default: a home machine reboots, sleeps and updates, and a question
# quietly costing two cents beats the feature being broken until you notice.
LOCAL_LLM_FALLBACK = os.getenv('LOCAL_LLM_FALLBACK', 'true').lower() != 'false'


class ModelReply:
    """What both providers hand back: the text, token counts, and who answered."""

    def __init__(self, text, usage, provider, cost_usd):
        self.text = text
        self.usage = usage
        self.provider = provider
        self.cost_usd = cost_usd


class LocalUsage:
    def __init__(self, prompt, completion):
        self.input_tokens = prompt
        self.output_tokens = completion
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0


def local_llm_for(feature):
    return bool(LOCAL_LLM_URL) and feature in LOCAL_LLM_FOR


def ask_model(feature, system, user, max_tokens, claude_call):
    """Answer one call, locally if configured, otherwise with Claude.

    A local failure — machine asleep, model still loading, empty reply —
    falls through to Claude rather than surfacing an error, unless
    LOCAL_LLM_FALLBACK=false says to fail loudly instead.
    """
    if local_llm_for(feature):
        try:
            reply = local_llm_chat(system, user, max_tokens)
            if reply.text:
                return reply
            raise ValueError('local model returned nothing')
        except Exception as e:
            if not LOCAL_LLM_FALLBACK:
                raise
            app.logger.warning('Local model failed (%s) — falling back to Claude: %s',
                               feature, e)
            reply = claude_call()
            reply.provider = 'claude (local unavailable)'
            return reply
    return claude_call()


def local_llm_chat(system, user, max_tokens):
    """One completion from the self-hosted model. Raises on failure so the
    caller can fall back to Claude rather than serve a broken answer."""
    response = requests.post(
        LOCAL_LLM_URL.rstrip('/') + '/chat/completions',
        timeout=LOCAL_LLM_TIMEOUT,
        headers={'Authorization': 'Bearer ' + os.getenv('LOCAL_LLM_KEY', 'not-needed')},
        json={
            'model': LOCAL_LLM_MODEL,
            'max_tokens': max_tokens,
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': user}],
        },
    )
    response.raise_for_status()
    body = response.json()
    text = (body['choices'][0]['message']['content'] or '').strip()
    usage = body.get('usage') or {}
    return ModelReply(text,
                      LocalUsage(usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)),
                      'local', 0.0)      # electricity isn't billed per question


# ── AI credit ─────────────────────────────────────────────────────────────────
# Every AI question is metered against a balance in two parts: a free grant
# that resets each calendar month, and credit bought through Stripe that
# doesn't. Each usage row records which pot paid for it, so the two never have
# to be untangled after the fact. The owner is never blocked but is still
# metered, so the running cost of other people's questions stays visible.

FREE_MONTHLY_NZD = 2.00        # ~100 database questions, or ~15 rulebook ones
MIN_BALANCE_NZD = 0.25         # a rulebook question with images can cost ~0.20
TOPUP_OPTIONS_NZD = (5, 10, 20)


def ai_balance(user_id):
    """What this account has left to spend, split by where it came from."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
          COALESCE(SUM(cost_nzd) FILTER (
              WHERE funded_by = 'free'
                AND created_at >= date_trunc('month', now())), 0),
          COALESCE(SUM(cost_nzd) FILTER (WHERE funded_by = 'credit'), 0),
          COALESCE(SUM(cost_nzd) FILTER (
              WHERE created_at >= date_trunc('month', now())), 0)
        FROM ai_usage WHERE user_id = %s
    """, (user_id,))
    free_used, credit_used, month_spend = cur.fetchone()
    cur.execute("""
        SELECT COALESCE(SUM(amount_nzd), 0) FROM credit_purchases
        WHERE user_id = %s AND status = 'paid'
    """, (user_id,))
    purchased = cur.fetchone()[0]
    cur.close()
    conn.close()

    free_remaining = max(0.0, FREE_MONTHLY_NZD - float(free_used))
    credit_remaining = float(purchased) - float(credit_used)
    return {
        'free_remaining': round(free_remaining, 4),
        'credit_remaining': round(credit_remaining, 4),
        'available': round(free_remaining + credit_remaining, 4),
        'month_spend': round(float(month_spend), 4),
        'purchased_total': round(float(purchased), 2),
        'free_monthly': FREE_MONTHLY_NZD,
    }


def balance_after(user=None):
    """What this account has left, for showing beside an answer. None if the
    account is uncapped, so the page can say so rather than print a number."""
    user = user or current_user()
    if not user or user.get('is_owner'):
        return None
    return ai_balance(user['id'])['available']


def ai_spend_blocked():
    """Response to return if this user can't afford a question, else None."""
    user = current_user()
    if user.get('is_owner'):
        return None
    balance = ai_balance(user['id'])
    if balance['available'] < MIN_BALANCE_NZD:
        return jsonify({
            'success': False,
            'out_of_credit': True,
            'balance': balance,
            'message': ("You're out of AI credit. Your free NZ$%.2f resets at the start "
                        "of the month, or you can top up." % FREE_MONTHLY_NZD),
        }), 402
    return None


def record_ai_usage(kind, cost_nzd, cost_usd, tokens=None):
    """Bill a question. Free grant first, then purchased credit.

    Charged whole to one pot rather than split across both — a question costs
    a couple of cents, so the rounding is worth the simpler ledger.
    """
    user = current_user()
    if not user:
        return
    if user.get('is_owner'):
        funded_by = 'owner'
    else:
        funded_by = 'free' if ai_balance(user['id'])['free_remaining'] >= cost_nzd else 'credit'
    conn = get_db_connection()
    cur = conn.cursor()
    t = tokens or {}
    try:
        cur.execute("""
            INSERT INTO ai_usage (user_id, kind, cost_nzd, cost_usd, funded_by,
                                  input_tokens, output_tokens, cache_write_tokens, cache_read_tokens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user['id'], kind, round(cost_nzd, 5), round(cost_usd, 5), funded_by,
              t.get('input_tokens'), t.get('output_tokens'),
              t.get('cache_write_tokens'), t.get('cache_read_tokens')))
        conn.commit()
    except psycopg2.Error as e:
        # The model call has already happened and been paid for. Losing the
        # answer as well would be the worse of the two failures — log the
        # missed charge and let the caller have what they paid for.
        conn.rollback()
        app.logger.error('Could not record %s usage of NZ$%.5f for user %s: %s',
                         kind, cost_nzd, user['id'], e)
    finally:
        cur.close()
        conn.close()


@app.route('/api/credit')
def api_credit():
    user = current_user()
    balance = ai_balance(user['id'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT kind, cost_nzd, funded_by, created_at,
               input_tokens, output_tokens, cache_write_tokens, cache_read_tokens
        FROM ai_usage WHERE user_id = %s ORDER BY created_at DESC LIMIT 20
    """, (user['id'],))
    recent = [{'kind': r[0], 'cost_nzd': float(r[1]), 'funded_by': r[2],
               'at': r[3].isoformat(),
               'tokens': ((r[4] or 0) + (r[5] or 0) + (r[6] or 0) + (r[7] or 0)) or None}
              for r in cur.fetchall()]
    cur.execute("""
        SELECT amount_nzd, status, created_at, paid_at FROM credit_purchases
        WHERE user_id = %s ORDER BY created_at DESC LIMIT 20
    """, (user['id'],))
    purchases = [{'amount_nzd': float(r[0]), 'status': r[1],
                  'at': r[2].isoformat(), 'paid_at': r[3].isoformat() if r[3] else None}
                 for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'success': True, 'balance': balance, 'uncapped': bool(user['is_owner']),
                    'recent_usage': recent, 'purchases': purchases,
                    'topup_options': list(TOPUP_OPTIONS_NZD),
                    'stripe_enabled': bool(stripe and os.getenv('STRIPE_SECRET_KEY'))})


@app.route('/api/credit/checkout', methods=['POST'])
def api_credit_checkout():
    """Start a Stripe Checkout session for a top-up.

    Nothing is credited here. The amount is picked from a server-side list
    rather than taken from the request, and only the signed webhook marks a
    purchase paid — a success redirect can be forged, a signature can't.
    """
    if not stripe or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'success': False, 'message': 'Top-ups are not configured.'}), 503
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    amount = (request.get_json() or {}).get('amount_nzd')
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = None
    if amount not in TOPUP_OPTIONS_NZD:
        return jsonify({'success': False, 'message': 'Choose one of the listed amounts.'}), 400

    user = current_user()
    site = os.getenv('SITE_URL', 'https://alkohout.github.io/board_game_logger')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO credit_purchases (user_id, amount_nzd, status)
        VALUES (%s, %s, 'pending') RETURNING id
    """, (user['id'], amount))
    purchase_id = cur.fetchone()[0]
    conn.commit()

    try:
        checkout = stripe.checkout.Session.create(
            mode='payment',
            line_items=[{
                'quantity': 1,
                'price_data': {
                    'currency': 'nzd',
                    'unit_amount': amount * 100,
                    'product_data': {'name': f'Board Game Logger AI credit — NZ${amount}'},
                },
            }],
            success_url=f'{site}/credit.html?paid=1',
            cancel_url=f'{site}/credit.html?cancelled=1',
            # Real money: Stripe emails the payer a receipt, and the address
            # shows on the payment so a query can be traced to an account.
            customer_email=user['email'],
            client_reference_id=str(purchase_id),
            metadata={'purchase_id': str(purchase_id), 'user_id': str(user['id'])},
        )
    except Exception as e:                                  # stripe.StripeError and friends
        cur.execute("UPDATE credit_purchases SET status = 'cancelled' WHERE id = %s",
                    (purchase_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': f'Stripe error: {e}'}), 502

    cur.execute("UPDATE credit_purchases SET stripe_session_id = %s WHERE id = %s",
                (checkout.id, purchase_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'url': checkout.url})


@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """The only thing that turns a pending purchase into credit.

    Unauthenticated by necessity — Stripe calls it — so the signature is what
    establishes trust, and a missing signing secret means we refuse rather
    than take the payload's word for it.
    """
    if not stripe:
        return jsonify({'success': False}), 503
    secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    if not secret:
        app.logger.error('Stripe webhook received but STRIPE_WEBHOOK_SECRET is not set')
        return jsonify({'success': False}), 503
    try:
        event = stripe.Webhook.construct_event(
            request.data, request.headers.get('Stripe-Signature', ''), secret)
    except Exception:
        app.logger.warning('Rejected Stripe webhook with a bad signature')
        return jsonify({'success': False}), 400

    if event['type'] == 'checkout.session.completed':
        session_id = event['data']['object']['id']
        conn = raw_db_connection()          # no logged-in user on this request
        cur = conn.cursor()
        # SECURITY DEFINER function: credits the row without disabling RLS.
        cur.execute("SELECT * FROM credit_mark_paid(%s)", (session_id,))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            app.logger.info('Credited NZ$%s to user %s', row[2], row[1])
        # A repeat delivery finds nothing pending and is a no-op, which is the
        # point: Stripe retries, and a top-up must not be credited twice.
    elif event['type'] == 'checkout.session.expired':
        conn = raw_db_connection()
        cur = conn.cursor()
        # SECURITY DEFINER, for the same reason as the paid path: this request
        # has no logged-in caller, so the connection carries no app.user_id and
        # a plain UPDATE matched nothing under RLS — abandoned checkouts stayed
        # 'pending' for ever.
        cur.execute("SELECT * FROM credit_mark_cancelled(%s)",
                    (event['data']['object']['id'],))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            app.logger.info('Cancelled abandoned checkout %s for user %s', row[0], row[1])

    return jsonify({'success': True})


# ── Database Query (AI) ───────────────────────────────────────────────────────
# Ask a question in English; Claude writes the SQL, we run it read-only and
# Claude reads the rows back. The model never touches the database itself.

# Writing the SQL is the half that can quietly produce a wrong answer, and its
# input is just the schema (~770 tokens) however big the result set is — so the
# expensive model sits on the small half. The write-up step carries all the row
# data, so it stays on Haiku.
DB_QUERY_SQL_MODEL = 'claude-opus-5'
DB_QUERY_SQL_PRICE = (5.00, 25.00)     # USD per million tokens, (input, output)
DB_QUERY_SQL_EFFORT = 'low'            # raise to medium/high if the SQL gets sloppy

DB_QUERY_WRITEUP_MODEL = 'claude-haiku-4-5'
DB_QUERY_WRITEUP_PRICE = (1.00, 5.00)

DB_QUERY_MAX_ROWS = 200               # rows handed back to the model and the page
DB_QUERY_MAX_CELL = 300               # characters per cell, so a stray blob can't flood

# Account tables are never described to the model. The bgl_ai role can't read
# them either, so this is about not wasting tokens describing a dead end.
DB_QUERY_HIDDEN_TABLES = {'users', 'login_attempts', 'ai_usage', 'credit_purchases'}

# Single-user campaign trackers: no owner column, so they stay the owner's and
# are neither described nor readable for anyone else.
DB_QUERY_OWNER_ONLY_TABLES = {'imperium', 'sleeping_gods', 'sleeping_gods_totems'}

# Columns holding base64 PDFs or scraped text — enormous, and useless as answers.
DB_QUERY_HIDDEN_COLUMNS = {
    ('rulebooks', 'pdf_data'),
    ('rulebooks', 'rules_text'),
    ('rulebooks', 'bgg_forum_cache'),
}

# Belt to the read-only transaction's braces: a keyword here means the model
# ignored its instructions, so refuse rather than rely on the database alone.
DB_QUERY_BANNED = re.compile(
    r'\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|'
    r'vacuum|reindex|merge|call|do|lock|listen|notify|prepare|execute|'
    r'pg_read_file|pg_sleep|dblink|pg_terminate_backend)\b', re.I)

DB_QUERY_NOTES = """
Notes on this data:
- Every play before 2024-01-01 is a bulk backfill, all stamped 2023-01-01. It is not
  real per-day data. Exclude it (date_played >= '2024-01-01') for anything about
  dates, streaks, or "best ever" records, but include it for lifetime play totals.
- `result` is free text typed by hand and inconsistent: 'Won', 'won', 'Won ',
  'Lost.', 'Lost. Romans (me) vs Abbasids (bot)', '-'. Match with
  btrim(lower(result)) LIKE 'won%' / 'lost%' rather than equality.
- `my_score`, `bot_score` and `level` are varchar, not numeric, and are often blank.
  Cast with NULLIF(btrim(x), '')::numeric and guard against non-numeric text.
- Weeks start Monday. The owner is in New Zealand; today is __TODAY__.
- `game_title` is free text too, so the same game can appear with slightly different
  spellings. Prefer ILIKE matching over equality when the user names a game.
"""


def db_query_schema(cur, is_owner=False):
    """Schema description handed to the model, built from the live database."""
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    tables = {}
    for table, column, dtype in cur.fetchall():
        if table in DB_QUERY_HIDDEN_TABLES:
            continue
        if table in DB_QUERY_OWNER_ONLY_TABLES and not is_owner:
            continue
        note = ' -- HUGE, never select' if (table, column) in DB_QUERY_HIDDEN_COLUMNS else ''
        tables.setdefault(table, []).append(f'  {column} {dtype}{note}')
    return '\n\n'.join(f'{t}:\n' + '\n'.join(cols) for t, cols in tables.items())


def db_query_check(sql):
    """Reject anything that isn't a single read-only statement. Returns an error string."""
    stripped = sql.strip().rstrip(';').strip()
    if not stripped:
        return 'No SQL was produced.'
    if ';' in stripped:
        return 'Only a single statement is allowed.'
    if not re.match(r'^(select|with)\b', stripped, re.I):
        return 'Only SELECT queries are allowed.'
    banned = DB_QUERY_BANNED.search(stripped)
    if banned:
        return f'Query rejected: it contains "{banned.group(0)}".'
    return None


def db_query_run(sql, is_owner=False):
    """Run the query in a read-only transaction. Returns (columns, rows, truncated).

    On a connection of its own, deliberately. set_session can't be called with a
    transaction already open, which the shared request connection usually has —
    and a pooled connection handed back still marked read-only would break the
    next writer to borrow it. The extra connection costs about a second; an AI
    question already costs several.
    """
    conn = private_db_connection()
    try:
        # Read-only is enforced by Postgres, not by our own parsing of the SQL.
        conn.set_session(readonly=True, autocommit=False)
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = '15s'")
        # Hand the model's SQL to a role that can only read game rows: no users
        # table, no rulebooks, and row-level security still scoped to the caller.
        cur.execute("SET LOCAL ROLE " + ('bgl_ai_owner' if is_owner else 'bgl_ai'))
        cur.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        raw = cur.fetchmany(DB_QUERY_MAX_ROWS + 1)
        truncated = len(raw) > DB_QUERY_MAX_ROWS
        rows = [
            ['' if v is None else str(v)[:DB_QUERY_MAX_CELL] for v in row]
            for row in raw[:DB_QUERY_MAX_ROWS]
        ]
        conn.rollback()
        cur.close()
        return columns, rows, truncated
    finally:
        conn.close()


def reply_cost(*replies):
    """USD/NZD across replies from either provider. A local model costs nothing
    per question, so its replies contribute zero."""
    usd = sum(r.cost_usd for r in replies)
    return usd, usd * float(os.getenv('NZD_RATE', '1.68'))


def db_query_cost(*priced):
    """Combined USD/NZD cost. Each argument is (response, usd_in, usd_out) per MTok."""
    usd = sum(usage_cost_usd(r.usage, price_in, price_out) for r, price_in, price_out in priced)
    return usd, usd * float(os.getenv('NZD_RATE', '1.68'))


def db_query_text(response):
    """First text block — skips a thinking block if the model emits one."""
    return next((b.text for b in response.content if b.type == 'text'), '').strip()


@app.route('/api/ask_database', methods=['POST'])
def api_ask_database():
    data = request.get_json() or {}
    question = (data.get('question') or '').strip()
    history = data.get('history') or []      # [{question, sql, answer}, ...]
    if not question:
        return jsonify({'success': False, 'message': 'Question required'}), 400

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'message': 'ANTHROPIC_API_KEY not configured'}), 500

    # This endpoint runs SQL the model writes, so it is only safe while the
    # database is enforcing row-level security. A superuser connection ignores
    # policies, which would let a generated query read every user's rows.
    # A local model costs nothing per question, so there is nothing to charge
    # for and no reason to turn anyone away.
    if not local_llm_for('db_query'):
        blocked = ai_spend_blocked()
        if blocked:
            return blocked

    if db_bypasses_rls():
        return jsonify({'success': False, 'message':
                        'Disabled: the app is connected as a superuser, which bypasses '
                        'row-level security. Point DB_USER at bgl_app and restart.'}), 503

    conn = get_db_connection()
    cur = conn.cursor()
    is_owner = bool(current_user() and current_user().get('is_owner'))
    schema = db_query_schema(cur, is_owner=is_owner)
    cur.close()
    conn.close()

    client = anthropic.Anthropic(api_key=api_key)
    # Plain replace, not %-formatting: the notes contain LIKE patterns with %.
    notes = DB_QUERY_NOTES.replace('__TODAY__', today_local().isoformat())

    # 1. Question -> SQL
    prior = ''.join(
        f'\nEarlier question: {h.get("question", "")}\nSQL you wrote: {h.get("sql", "")}\n'
        for h in history[-3:]
    )
    sql_system = (
                'You write PostgreSQL for a personal board game log. Reply with one '
                'SELECT statement and nothing else — no explanation, no markdown fences, '
                'no trailing semicolon. If the question cannot be answered from this '
                'schema, reply with exactly "UNSUPPORTED: " followed by a short reason.\n\n'
                f'Schema:\n{schema}\n{notes}\n'
        f'Return at most {DB_QUERY_MAX_ROWS} rows — add a LIMIT unless the query '
        'is already an aggregate. Never select the columns marked HUGE.'
    )
    sql_user = f'{prior}\nQuestion: {question}'

    def sql_via_claude():
        response = client.messages.create(
            model=DB_QUERY_SQL_MODEL, max_tokens=8000,
            output_config={'effort': DB_QUERY_SQL_EFFORT},
            system=sql_system,
            messages=[{'role': 'user', 'content': sql_user}])
        return ModelReply(db_query_text(response), response.usage, 'claude',
                          usage_cost_usd(response.usage, *DB_QUERY_SQL_PRICE))

    try:
        sql_reply = ask_model('db_query', sql_system, sql_user, 2000, sql_via_claude)
    except requests.RequestException as e:
        return jsonify({'success': False,
                        'message': f'Could not reach the local model: {e}'}), 502
    except anthropic.APIStatusError as e:
        return jsonify({'success': False, 'message': f'Claude error: {e.message}'}), 502
    except anthropic.APIConnectionError:
        return jsonify({'success': False, 'message': 'Could not reach Claude.'}), 502

    sql = sql_reply.text
    sql = re.sub(r'^```(?:sql)?|```$', '', sql, flags=re.I | re.M).strip()

    if sql.upper().startswith('UNSUPPORTED'):
        usd, nzd = reply_cost(sql_reply)
        record_ai_usage('db_query', nzd, usd, usage_tokens(sql_reply.usage))
        return jsonify({'success': False, 'message': sql.split(':', 1)[-1].strip(),
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    problem = db_query_check(sql)
    if problem:
        usd, nzd = reply_cost(sql_reply)
        record_ai_usage('db_query', nzd, usd, usage_tokens(sql_reply.usage))
        return jsonify({'success': False, 'message': problem, 'sql': sql,
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)}), 400

    # 2. Run it read-only
    try:
        columns, rows, truncated = db_query_run(sql.rstrip(';'), is_owner=is_owner)
    except psycopg2.Error as e:
        usd, nzd = reply_cost(sql_reply)
        record_ai_usage('db_query', nzd, usd, usage_tokens(sql_reply.usage))
        return jsonify({'success': False, 'message': f'Query failed: {str(e).strip()}',
                        'sql': sql, 'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)}), 400

    # 3. Rows -> plain English
    table = ' | '.join(columns) + '\n' + '\n'.join(' | '.join(r) for r in rows)
    if truncated:
        table += f'\n(only the first {DB_QUERY_MAX_ROWS} rows are shown)'
    answer_system = (
                'You answer questions about a personal board game log. You are given the '
                'question, the SQL that was run, and its results. Answer directly in a '
                'sentence or two — no preamble, no restating the question, no markdown '
                'tables (the results are already shown to the user). Quote the actual '
        'numbers. If the results are empty, say so plainly and, if the reason is '
        'obvious from the query, say what it is.'
    )
    answer_user = f'Question: {question}\n\nSQL:\n{sql}\n\nResults ({len(rows)} rows):\n{table}'

    def answer_via_claude():
        response = client.messages.create(
            model=DB_QUERY_WRITEUP_MODEL, max_tokens=2000,
            system=answer_system,
            messages=[{'role': 'user', 'content': answer_user}])
        return ModelReply(db_query_text(response), response.usage, 'claude',
                          usage_cost_usd(response.usage, *DB_QUERY_WRITEUP_PRICE))

    try:
        answer_reply = ask_model('db_query', answer_system, answer_user, 1000, answer_via_claude)
    except (requests.RequestException, anthropic.APIStatusError, anthropic.APIConnectionError):
        # The data is good even if the write-up failed — return it without prose.
        usd, nzd = reply_cost(sql_reply)
        record_ai_usage('db_query', nzd, usd, usage_tokens(sql_reply.usage))
        return jsonify({'success': True, 'sql': sql, 'columns': columns, 'rows': rows,
                        'truncated': truncated, 'answer': '', 'provider': sql_reply.provider,
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    usd, nzd = reply_cost(sql_reply, answer_reply)
    record_ai_usage('db_query', nzd, usd)
    return jsonify({
        'success': True,
        'balance_nzd': balance_after(),
        'provider': answer_reply.provider,
        'answer': answer_reply.text,
        'sql': sql,
        'columns': columns,
        'rows': rows,
        'row_count': len(rows),
        'truncated': truncated,
        'cost_usd': round(usd, 4),
        'cost_nzd': round(nzd, 4),
    })


@app.route('/api/recent_plays')
def api_recent_plays():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT date_played, game_title, result, level, my_score, bot_score, notes
        FROM games
        ORDER BY date_played DESC, id DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        'date_played': str(r[0]),
        'game_title': r[1],
        'result': r[2] or '',
        'level': r[3] or '',
        'my_score': r[4] or '',
        'bot_score': r[5] or '',
        'notes': r[6] or '',
    } for r in rows])


# Runs once per worker at boot, after everything it needs is defined.
check_schema()
check_owned_tables()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')

