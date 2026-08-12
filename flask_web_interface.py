from flask import Flask, request, jsonify, g, has_request_context
from flask_cors import CORS
import psycopg2
import os
import random
import re
import anthropic
try:
    import stripe                       # only needed for credit top-ups
except ImportError:                     # keeps the app up if it isn't installed yet
    stripe = None
import base64
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


def today_local():
    return datetime.now(LOCAL_TZ).date()

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

CORS(app,
     origins=["https://alkohout.github.io", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000"],
     allow_headers=["Authorization", "Content-Type"],
     methods=["GET", "POST", "OPTIONS"])


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


def issue_token(user_id):
    return token_serializer().dumps({'uid': user_id})


def load_user(user_id):
    """Fetch a user by id. Returns None for unknown, pending or disabled accounts."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, email, display_name, status, is_owner
            FROM users WHERE id = %s
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row or row[3] != 'active':
        return None
    return {'id': row[0], 'email': row[1], 'display_name': row[2],
            'status': row[3], 'is_owner': row[4]}


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
            if user:
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

@app.route('/')
def api_root():
    """This host is the API. The app itself lives on GitHub Pages."""
    return jsonify({'app': 'Board Game Logger API',
                    'site': 'https://alkohout.github.io/board_game_logger/'})


def raw_db_connection():
    """A connection with no identity attached. Only auth and migrations want this."""
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
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host="localhost",
        database="boardgames",
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("PASSWORD")
    )


def get_db_connection():
    """The connection every route uses.

    Stamps the caller's id onto the session so the row-level security policies
    can filter, and so INSERTs pick up the right owner from the column default.
    Every route opens and closes its own connection, so a session-level SET is
    scoped to this request — SET LOCAL would be undone by the first commit.
    """
    conn = raw_db_connection()
    user = getattr(g, 'user', None) if has_request_context() else None
    if user:
        cur = conn.cursor()
        cur.execute("SELECT set_config('app.user_id', %s, false)", (str(user['id']),))
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
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
    location = request.args.get('term', '0')
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
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
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
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
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
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
    try:
        # Connect to your database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update all records to set visited to 0
        cursor.execute('UPDATE sleeping_gods SET visited = FALSE')
        
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
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
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

    # Search for the most recent play and notes
    cur.execute("""
        SELECT g.date_played,  
	    COALESCE( (SELECT g2.id
       		  FROM games AS g2
       		  WHERE g2.game_title = g.game_title
       		  ORDER BY g2.id DESC
       		  LIMIT 1), 0) 
        FROM games AS g 
        WHERE g.game_title ILIKE %s 
        ORDER BY g.date_played DESC 
        LIMIT 1
    """, (f"%{game_title}%",))
    last_played = cur.fetchone()
    if not last_played:
        # Nothing matched — every lookup below indexes into this row, so stop
        # here rather than crashing. Common now that a new account starts empty.
        cur.close()
        conn.close()
        return jsonify({'Error': 'No record found for the specified game.'})

    # Fetch notes
    cur.execute("SELECT notes FROM games WHERE id = %s", (f"{last_played[1]}",))
    notes = cur.fetchone()[0]

    # Fetch result
    cur.execute("SELECT result FROM games WHERE id = %s", (f"{last_played[1]}",))
    result = cur.fetchone()[0]

    # Fetch level 
    cur.execute("SELECT level FROM games WHERE id = %s", (f"{last_played[1]}",))
    level = cur.fetchone()[0]

    # Fetch my_score 
    cur.execute("SELECT my_score FROM games WHERE id = %s", (f"{last_played[1]}",))
    my_score = cur.fetchone()[0]

    # Fetch bot_score 
    cur.execute("SELECT bot_score FROM games WHERE id = %s", (f"{last_played[1]}",))
    bot_score = cur.fetchone()[0]

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
        SELECT date_played, notes, result, level, my_score, bot_score
        FROM games
        WHERE game_title ILIKE %s
          AND ( (notes  IS NOT NULL AND btrim(notes)  NOT IN ('', 'null')) OR
                (result IS NOT NULL AND btrim(result) NOT IN ('', 'null')) )
        ORDER BY date_played DESC, id DESC
        LIMIT 1
    """, (f"%{game_title}%",))
    nonempty = cur.fetchone()
    date_nonempty = nonempty[0] if nonempty else None
    notes_nonempty = nonempty[1] if nonempty else None
    result_nonempty = nonempty[2] if nonempty else None
    level_nonempty = nonempty[3] if nonempty else None
    my_score_nonempty = nonempty[4] if nonempty else None
    bot_score_nonempty = nonempty[5] if nonempty else None

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
            'date_played': last_played[0].isoformat(),
            'date_played_nonempty': date_nonempty.isoformat() if date_nonempty else None,
            'notes_nonempty': notes_nonempty if notes_nonempty else None,
            'result_nonempty': result_nonempty if result_nonempty else None,
	    'level_nonempty': level_nonempty if level_nonempty else None,
	    'my_score_nonempty': my_score_nonempty if my_score_nonempty else None,
	    'bot_score_nonempty': bot_score_nonempty if bot_score_nonempty else None,
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
    pdf_b64 = base64.standard_b64encode(pdf_file.stream.read()).decode('utf-8')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO rulebooks (game_title, rulebook_name, pdf_data)
            VALUES (%s, %s, %s)
            ON CONFLICT (game_title, rulebook_name) DO UPDATE
                SET pdf_data = EXCLUDED.pdf_data,
                    uploaded_at = NOW()
        """, (game_title, rulebook_name, pdf_b64))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'DB error: {str(e)}'}), 500
    return jsonify({'success': True, 'message': f'"{rulebook_name}" saved for {game_title}'})


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

        blocked = ai_spend_blocked()
        if blocked:
            return blocked

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT pdf_data, bgg_forum_cache, rulebook_name
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

        # PDF blocks with cache_control so follow-up questions reuse the cached context
        pdf_blocks = [
            {
                'type': 'document',
                'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': r[0]},
                'cache_control': {'type': 'ephemeral'}
            }
            for r in rows
        ]

        history = data.get('history', [])  # [{role, content}] of previous text turns

        # First user message always includes PDFs + optional BGG + first question
        first_question = history[0]['content'] if history else question
        first_content = list(pdf_blocks)
        if bgg_section:
            first_content.append({'type': 'text', 'text': f'BGG Rules Forum Discussions:\n{bgg_section}'})
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
            ),
            messages=messages
        )
        # Haiku pricing: $0.80/MTok input, $4.00/MTok output
        input_cost  = response.usage.input_tokens  * 0.80 / 1_000_000
        output_cost = response.usage.output_tokens * 4.00 / 1_000_000
        cost_usd = input_cost + output_cost
        nzd_rate = float(os.getenv('NZD_RATE', '1.68'))
        cost_nzd = cost_usd * nzd_rate
        record_ai_usage('rules', cost_nzd, cost_usd)

        return jsonify({
            'success': True,
            'answer': response.content[0].text,
            'sources': sources_used,
            'cost_nzd': round(cost_nzd, 4),
            'cost_usd': round(cost_usd, 4)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Static-frontend JSON API ──────────────────────────────────────────────────

def user_public(user):
    return {'id': user['id'], 'email': user['email'],
            'display_name': user['display_name'], 'is_owner': user['is_owner']}


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
            INSERT INTO users (email, password_hash, display_name, status)
            VALUES (%s, %s, %s, 'pending')
        """, (email, generate_password_hash(password), display_name))
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
            SELECT id, email, display_name, status, is_owner, password_hash
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
                'status': row[3], 'is_owner': row[4]}
    finally:
        cur.close()
        conn.close()

    return jsonify({'success': True, 'token': issue_token(user['id']),
                    'user': user_public(user)})


@app.route('/api/me')
def api_me():
    user = current_user()
    payload = {'success': True, 'user': user_public(user)}
    if user['is_owner']:
        # Belt and braces: if the notification email ever fails or gets
        # filtered, a waiting request still shows up in the app.
        conn = get_db_connection()
        cur = conn.cursor()
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

    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new), user['id']))
    conn.commit()
    cur.close()
    conn.close()
    # Existing tokens keep working: they identify the account, not the password.
    return jsonify({'success': True, 'message': 'Password changed.'})


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
    cur.close()
    conn.close()
    return jsonify({'success': True, 'users': users})


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
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO games (date_played, game_title, notes, result, level, my_score, bot_score) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (data.get('date_played'), data.get('game_title'), data.get('notes', ''),
             data.get('result', ''), data.get('level', ''), data.get('my_score', ''), data.get('bot_score', ''))
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


@app.route('/api/imperium_stats')
def api_imperium_stats():
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
    conn = get_db_connection()
    cur = conn.cursor()
    # One pass over the plays; the per-civilisation tally happens here rather
    # than in the 56 separate count queries the old page used.
    cur.execute("SELECT level, result FROM imperium")
    plays = [((r[0] or '').lower(), (r[1] or '').lower()) for r in cur.fetchall()]
    cur.close()
    conn.close()

    expansions = []
    for expansion, name, stars in IMPERIUM_CIVS:
        key = name.lower()
        won = sum(1 for lvl, res in plays if key in lvl and 'won' in res)
        lost = sum(1 for lvl, res in plays if key in lvl and 'lost' in res)
        if not expansions or expansions[-1]['expansion'] != expansion:
            expansions.append({'expansion': expansion, 'civilisations': []})
        expansions[-1]['civilisations'].append(
            {'name': name, 'stars': stars, 'won': won, 'lost': lost})

    # Plays whose level matches no known civilisation — a new expansion, or a typo.
    known = [name.lower() for _, name, _ in IMPERIUM_CIVS]
    unmatched = sorted({lvl.strip() for lvl, _ in plays
                        if lvl.strip() and not any(k in lvl for k in known)})

    return jsonify({'expansions': expansions, 'unmatched_levels': unmatched,
                    'total_plays': len(plays)})


@app.route('/api/sleeping_gods_totems_data')
def api_sleeping_gods_totems_data():
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, totem, found FROM sleeping_gods_totems ORDER BY id")
    rows = [{'id': r[0], 'totem': r[1], 'found': r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'totems': rows})


@app.route('/api/add_sleeping_gods', methods=['POST'])
def api_add_sleeping_gods():
    # Imperium and Sleeping Gods are the owner's own campaign trackers: the
    # tables have no owner column, so the endpoint is the boundary.
    denied = owner_only()
    if denied:
        return denied
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


# ── AI credit ─────────────────────────────────────────────────────────────────
# Every AI question is metered against a balance in two parts: a free grant
# that resets each calendar month, and credit bought through Stripe that
# doesn't. Each usage row records which pot paid for it, so the two never have
# to be untangled after the fact. The owner is never blocked but is still
# metered, so the running cost of other people's questions stays visible.

FREE_MONTHLY_NZD = 0.50        # roughly 25-35 questions
MIN_BALANCE_NZD = 0.05         # refuse below this: one question can cost ~0.03
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


def record_ai_usage(kind, cost_nzd, cost_usd):
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
    cur.execute("""
        INSERT INTO ai_usage (user_id, kind, cost_nzd, cost_usd, funded_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (user['id'], kind, round(cost_nzd, 5), round(cost_usd, 5), funded_by))
    conn.commit()
    cur.close()
    conn.close()


@app.route('/api/credit')
def api_credit():
    user = current_user()
    balance = ai_balance(user['id'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT kind, cost_nzd, funded_by, created_at FROM ai_usage
        WHERE user_id = %s ORDER BY created_at DESC LIMIT 20
    """, (user['id'],))
    recent = [{'kind': r[0], 'cost_nzd': float(r[1]), 'funded_by': r[2],
               'at': r[3].isoformat()} for r in cur.fetchall()]
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
        cur.execute("""
            UPDATE credit_purchases SET status = 'cancelled'
            WHERE stripe_session_id = %s AND status = 'pending'
        """, (event['data']['object']['id'],))
        conn.commit()
        cur.close()
        conn.close()

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
    """Run the query in a read-only transaction. Returns (columns, rows, truncated)."""
    conn = get_db_connection()
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


def db_query_cost(*priced):
    """Combined USD/NZD cost. Each argument is (response, usd_in, usd_out) per MTok."""
    usd = sum(r.usage.input_tokens * price_in / 1_000_000 +
              r.usage.output_tokens * price_out / 1_000_000
              for r, price_in, price_out in priced)
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
    try:
        sql_response = client.messages.create(
            model=DB_QUERY_SQL_MODEL,
            max_tokens=8000,
            output_config={'effort': DB_QUERY_SQL_EFFORT},
            system=(
                'You write PostgreSQL for a personal board game log. Reply with one '
                'SELECT statement and nothing else — no explanation, no markdown fences, '
                'no trailing semicolon. If the question cannot be answered from this '
                'schema, reply with exactly "UNSUPPORTED: " followed by a short reason.\n\n'
                f'Schema:\n{schema}\n{notes}\n'
                f'Return at most {DB_QUERY_MAX_ROWS} rows — add a LIMIT unless the query '
                'is already an aggregate. Never select the columns marked HUGE.'
            ),
            messages=[{'role': 'user', 'content': f'{prior}\nQuestion: {question}'}],
        )
    except anthropic.APIStatusError as e:
        return jsonify({'success': False, 'message': f'Claude error: {e.message}'}), 502
    except anthropic.APIConnectionError:
        return jsonify({'success': False, 'message': 'Could not reach Claude.'}), 502

    sql = db_query_text(sql_response)
    sql = re.sub(r'^```(?:sql)?|```$', '', sql, flags=re.I | re.M).strip()

    if sql.upper().startswith('UNSUPPORTED'):
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
        record_ai_usage('db_query', nzd, usd)
        return jsonify({'success': False, 'message': sql.split(':', 1)[-1].strip(),
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    problem = db_query_check(sql)
    if problem:
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
        record_ai_usage('db_query', nzd, usd)
        return jsonify({'success': False, 'message': problem, 'sql': sql,
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)}), 400

    # 2. Run it read-only
    try:
        columns, rows, truncated = db_query_run(sql.rstrip(';'), is_owner=is_owner)
    except psycopg2.Error as e:
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
        record_ai_usage('db_query', nzd, usd)
        return jsonify({'success': False, 'message': f'Query failed: {str(e).strip()}',
                        'sql': sql, 'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)}), 400

    # 3. Rows -> plain English
    table = ' | '.join(columns) + '\n' + '\n'.join(' | '.join(r) for r in rows)
    if truncated:
        table += f'\n(only the first {DB_QUERY_MAX_ROWS} rows are shown)'
    try:
        answer_response = client.messages.create(
            model=DB_QUERY_WRITEUP_MODEL,
            max_tokens=2000,
            system=(
                'You answer questions about a personal board game log. You are given the '
                'question, the SQL that was run, and its results. Answer directly in a '
                'sentence or two — no preamble, no restating the question, no markdown '
                'tables (the results are already shown to the user). Quote the actual '
                'numbers. If the results are empty, say so plainly and, if the reason is '
                'obvious from the query, say what it is.'
            ),
            messages=[{'role': 'user', 'content':
                       f'Question: {question}\n\nSQL:\n{sql}\n\nResults ({len(rows)} rows):\n{table}'}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        # The data is good even if the write-up failed — return it without prose.
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
        record_ai_usage('db_query', nzd, usd)
        return jsonify({'success': True, 'sql': sql, 'columns': columns, 'rows': rows,
                        'truncated': truncated, 'answer': '',
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE),
                          (answer_response, *DB_QUERY_WRITEUP_PRICE))
    record_ai_usage('db_query', nzd, usd)
    return jsonify({
        'success': True,
        'answer': db_query_text(answer_response),
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')

