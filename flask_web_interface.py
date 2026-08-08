from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
import psycopg2
import os
import random
import re
import anthropic
import base64
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

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


def api_auth_ok():
    auth = request.headers.get('Authorization', '')
    return auth.startswith('Bearer ') and auth[7:] == os.getenv('APP_PASSWORD', '')


@app.before_request
def require_login():
    if request.method == 'OPTIONS':
        return
    if request.endpoint == 'static':
        return
    if request.path.startswith('/api/'):
        if request.path == '/api/login':
            return
        if not api_auth_ok():
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return
    if request.endpoint in ('login', 'logout'):
        return
    if session.get('logged_in') or api_auth_ok():
        return
    return redirect(url_for('login'))

# Per-process state: gunicorn runs 2 workers, so each holds its own copy and
# a choice added through one worker is invisible to the other. The GitHub
# Pages dashboard now keeps its selector pool in localStorage instead; these
# routes remain only for the older server-rendered page below.
selector_pool = []
selector_choices = []



def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host="localhost",
        database="boardgames",
        user="postgres",
        password=os.getenv("PASSWORD")
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == os.getenv('APP_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Wrong password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_selector_game', methods=['POST'])
def add_selector_game():
    game_title = request.form.get('game_title', '').strip()
    choice_type = request.form.get('choice_type', '').strip()
    player_raw = request.form.get('player', '').strip()

    if not game_title:
        return jsonify({'success': False, 'message': 'Game title is required.'}), 400

    if choice_type not in ['first', 'second', 'third']:
        return jsonify({'success': False, 'message': 'Invalid choice type.'}), 400

    try:
        player = int(player_raw)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid player number.'}), 400

    # Prevent duplicate choice type for same player
    existing = next(
        (entry for entry in selector_choices if entry['player'] == player and entry['choice_type'] == choice_type),
        None
    )
    if existing:
        return jsonify({
            'success': False,
            'message': f'Player {player} already has a {choice_type} choice.'
        }), 400

    selector_choices.append({
        'player': player,
        'choice_type': choice_type,
        'game_title': game_title
    })

    order_map = {'first': 1, 'second': 2, 'third': 3}
    selector_choices.sort(key=lambda x: (x['player'], order_map[x['choice_type']]))

    return jsonify({
        'success': True,
        'message': f'Player {player} {choice_type} choice added: "{game_title}"',
        'choices': selector_choices
    })

@app.route('/random_selector_pick', methods=['GET'])
def random_selector_pick():
    if not selector_choices:
        return jsonify({'success': False, 'message': 'No games in the selector pool.'}), 400

    weight_map = {
        'first': 3,
        'second': 2,
        'third': 1
    }

    weighted_pool = []
    for entry in selector_choices:
        weighted_pool.extend([entry] * weight_map[entry['choice_type']])

    selected = random.choice(weighted_pool)

    return jsonify({
        'success': True,
        'selected': selected
    })

@app.route('/clear_selector_pool', methods=['POST'])
def clear_selector_pool():
    selector_choices.clear()
    return jsonify({'success': True, 'message': 'Selector pool cleared.'})

@app.route('/get_selector_pool', methods=['GET'])
def get_selector_pool():
    return jsonify({'success': True, 'pool': selector_choices})

@app.route('/add', methods=['POST'])
def add_game():
    date_played = request.form['date_played']
    game_title = request.form['game_title']
    notes = request.form.get('notes', '')
    result = request.form.get('result','')
    level = request.form.get('level','')
    my_score = request.form.get('my_score','')
    bot_score = request.form.get('bot_score','')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO games (date_played, game_title, notes, result, level, my_score, bot_score) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (date_played, game_title, notes, result, level, my_score, bot_score)
    )
    conn.commit()

    cur.close()
    conn.close()

    # Redirect to the index page, passing stats as query parameters
    return redirect(url_for('index'))

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT game_title FROM games")
    game_titles = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 5
    """)
    top_games = cur.fetchall()

    # Calculate date boundaries for the current week, month, and year
    today = today_local()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    
    # Define date boundaries for last week, last month, and last year
    start_of_current_week = today - timedelta(days=today.weekday())
    end_of_last_week = start_of_current_week - timedelta(days=1)
    start_of_last_week = end_of_last_week - timedelta(days=6)

    start_of_current_month = today.replace(day=1)
    last_day_of_last_month = start_of_current_month - timedelta(days=1)
    start_of_last_month = last_day_of_last_month.replace(day=1)

    start_of_current_year = today.replace(month=1, day=1)
    last_day_of_last_year = start_of_current_year - timedelta(days=1)
    start_of_last_year = last_day_of_last_year.replace(month=1, day=1)

    # Count games played this week
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s", (start_of_week,))
    games_this_week = cur.fetchone()[0]
    
    # Count games played this month
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s", (start_of_month,))
    games_this_month = cur.fetchone()[0]
    
    # Count games played this year
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s", (start_of_year,))
    games_this_year = cur.fetchone()[0]

    # Define date boundaries for last week, last month, and last year
    start_of_current_week = today - timedelta(days=today.weekday())
    end_of_last_week = start_of_current_week - timedelta(days=1)
    start_of_last_week = end_of_last_week - timedelta(days=6)

    start_of_current_month = today.replace(day=1)
    last_day_of_last_month = start_of_current_month - timedelta(days=1)
    start_of_last_month = last_day_of_last_month.replace(day=1)

    start_of_current_year = today.replace(month=1, day=1)
    last_day_of_last_year = start_of_current_year - timedelta(days=1)
    start_of_last_year = last_day_of_last_year.replace(month=1, day=1)

    # Games played last week
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", (start_of_last_week, end_of_last_week))
    games_last_week = cur.fetchone()[0]

    # Games played last month
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", (start_of_last_month, last_day_of_last_month))
    games_last_month = cur.fetchone()[0]

    # Games played last year
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played BETWEEN %s AND %s", (start_of_last_year, last_day_of_last_year))
    games_last_year = cur.fetchone()[0]

    # Starting reference date for weekly and monthly averages calculation (removes the false 2023 data)
    start_date = date(2024, 1, 1)

    # End dates for averages (up to the start of the current period)
    end_of_last_week = start_of_week
    end_of_last_month = start_of_month
    end_of_last_year = start_of_year

    # Calculate total number of games and periods for averages
    # Weekly Average Calculation
    total_days = (end_of_last_week - start_date).days
    num_weeks = total_days // 7 if total_days >= 7 else 0

    if num_weeks > 0:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (start_date, end_of_last_week))
        total_games = cur.fetchone()[0]
        weekly_avg = round(total_games / num_weeks)
    else:
        weekly_avg = 0

    # Monthly Average Calculation
    num_months = (end_of_last_month.year - start_date.year) * 12 + (end_of_last_month.month - start_date.month)
    if num_months > 0:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (start_date, end_of_last_month))
        total_games = cur.fetchone()[0]
        monthly_avg = round(total_games / num_months)
    else:
        monthly_avg = 0

    # Yearly Average Calculation
    start_date = date(2023, 1, 1)
    num_years = end_of_last_year.year - start_date.year
    if num_years > 0:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (start_date, end_of_last_year))
        total_games = cur.fetchone()[0]
        yearly_avg = round(total_games / num_years)
    else:
        yearly_avg = 0

    # Most played game this week
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played >= %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_week,))
    most_played_this_week = cur.fetchone()
    if most_played_this_week:
        most_played_game_week = most_played_this_week[0]
        week_play_count = most_played_this_week[1]
    else:
        most_played_game_week = None
        week_play_count = 0

    # Most played game this month
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played >= %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_month,))
    most_played_this_month = cur.fetchone()
    if most_played_this_month:
        most_played_game_month = most_played_this_month[0]
        month_play_count = most_played_this_month[1]
    else:
        most_played_game_month = None
        month_play_count = 0

    # Most played game this year
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played >= %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_year,))
    most_played_this_year = cur.fetchone()
    if most_played_this_year:
        most_played_game_year = most_played_this_year[0]
        year_play_count = most_played_this_year[1]
    else:
        most_played_game_year = None
        year_play_count = 0

   # Most played game last week
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played BETWEEN %s AND %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_last_week, end_of_last_week))
    most_played_last_week = cur.fetchone()
    if most_played_last_week:
        most_played_game_last_week = most_played_last_week[0]
        last_week_play_count = most_played_last_week[1]
    else:
        most_played_game_last_week = None
        last_week_play_count = 0

    # Most played game last month
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played BETWEEN %s AND %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_last_month, last_day_of_last_month))
    most_played_last_month = cur.fetchone()
    if most_played_last_month:
        most_played_game_last_month = most_played_last_month[0]
        last_month_play_count = most_played_last_month[1]
    else:
        most_played_game_last_month = None
        last_month_play_count = 0

    # Most played game last year
    cur.execute("""
        SELECT game_title, COUNT(*) as play_count
        FROM games
        WHERE date_played BETWEEN %s AND %s
        GROUP BY game_title
        ORDER BY play_count DESC
        LIMIT 1
    """, (start_of_last_year, last_day_of_last_year))
    most_played_last_year = cur.fetchone()
    if most_played_last_year:
        most_played_game_last_year = most_played_last_year[0]
        last_year_play_count = most_played_last_year[1]
    else:
        most_played_game_last_year = None
        last_year_play_count = 0

    # Games played today and yesterday, plus the all-time bests
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played = %s", (today,))
    games_today = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE date_played = %s", (today - timedelta(days=1),))
    games_yesterday = cur.fetchone()[0]

    num_days = (today - date(2024, 1, 1)).days
    if num_days > 0:
        cur.execute("SELECT COUNT(*) FROM games WHERE date_played >= %s AND date_played < %s", (date(2024, 1, 1), today))
        daily_avg = round(cur.fetchone()[0] / num_days, 1)
    else:
        daily_avg = 0

    records = period_records(cur)

    cur.close()
    conn.close()
    return render_template(
        'index.html',
        game_titles=sorted(game_titles),
        top_games=top_games,
        today=today_local().isoformat(),
        games_today=games_today,
        games_yesterday=games_yesterday,
        daily_avg=daily_avg,
        records=records,
        games_this_week=games_this_week,
        games_this_month=games_this_month,
        games_this_year=games_this_year,
        games_last_week=games_last_week,
        games_last_month=games_last_month,
        games_last_year=games_last_year,
        most_played_game_week=most_played_game_week,
        most_played_game_month=most_played_game_month,
        most_played_game_year=most_played_game_year,
        week_play_count=week_play_count,
        month_play_count=month_play_count,
        year_play_count=year_play_count,
	most_played_game_last_week=most_played_game_last_week,
	most_played_game_last_month=most_played_game_last_month,
	most_played_game_last_year=most_played_game_last_year,
	last_week_play_count=last_week_play_count,
	last_month_play_count=last_month_play_count,
	last_year_play_count=last_year_play_count,
        weekly_avg = weekly_avg,
        monthly_avg = monthly_avg,
        yearly_avg = yearly_avg
    )

@app.route('/sleeping_gods', methods=['GET', 'POST'])
def sleeping_gods():

    if request.method == 'POST':

        # Get other form data
        location_raw = request.form.get('location', '').strip()
        location = int(location_raw) if location_raw else 0
        part = request.form.get('part', '')
        required_keyword = request.form.get('required_keyword', '')
        gained_keyword = request.form.get('gained_keyword', '')
        visited = '1' if request.form.get('visited') == '1' else '0'
        notes = request.form.get('notes', '')
        combat = '1' if request.form.get('combat') == '1' else '0'
        combat_level_raw = request.form.get('combat_level', '').strip()
        combat_level = int(combat_level_raw) if combat_level_raw else 0
        gained = request.form.get('gained', '')
        req_coins_raw = request.form.get('req_coins', '').strip()
        req_coins = int(req_coins_raw) if req_coins_raw else 0
        req_meat_raw = request.form.get('req_meat', '').strip()
        req_meat = int(req_meat_raw) if req_meat_raw else 0
        req_veg_raw = request.form.get('req_veg', '').strip()
        req_veg = int(req_veg_raw) if req_veg_raw else 0
        req_grain_raw = request.form.get('req_grain', '').strip()
        req_grain = int(req_grain_raw) if req_grain_raw else 0
        req_wood_raw = request.form.get('req_wood', '').strip()
        req_wood = int(req_wood_raw) if req_wood_raw else 0
        req_artifacts_raw = request.form.get('req_artifacts', '').strip()
        req_artifacts = int(req_artifacts_raw) if req_artifacts_raw else 0
        gain_coins_raw = request.form.get('gain_coins', '').strip()
        gain_coins = int(gain_coins_raw) if gain_coins_raw else 0
        gain_meat_raw = request.form.get('gain_meat', '').strip()
        gain_meat = int(gain_meat_raw) if gain_meat_raw else 0
        gain_veg_raw = request.form.get('gain_veg', '').strip()
        gain_veg = int(gain_veg_raw) if gain_veg_raw else 0
        gain_grain_raw = request.form.get('gain_grain', '').strip()
        gain_grain = int(gain_grain_raw) if gain_grain_raw else 0
        gain_wood_raw = request.form.get('gain_wood', '').strip()
        gain_wood = int(gain_wood_raw) if gain_wood_raw else 0
        gain_artifacts_raw = request.form.get('gain_artifacts', '').strip()
        gain_artifacts = int(gain_artifacts_raw) if gain_artifacts_raw else 0
        gain_xp_raw = request.form.get('gain_xp', '').strip()
        gain_xp = int(gain_xp_raw) if gain_xp_raw else 0
        gain_adventure_raw = request.form.get('gain_adventure', '').strip()
        gain_adventure = int(gain_adventure_raw) if gain_adventure_raw else 0
        gain_ship_damage_raw = request.form.get('gain_ship_damage', '').strip()
        gain_ship_damage = int(gain_ship_damage_raw) if gain_ship_damage_raw else 0
        gain_ship_repair_raw = request.form.get('gain_ship_repair', '').strip()
        gain_ship_repair = int(gain_ship_repair_raw) if gain_ship_repair_raw else 0
        gain_crew_damage_raw = request.form.get('gain_crew_damage', '').strip()
        gain_crew_damage = int(gain_crew_damage_raw) if gain_crew_damage_raw else 0
        gain_crew_health_raw = request.form.get('gain_crew_health', '').strip()
        gain_crew_health = int(gain_crew_health_raw) if gain_crew_health_raw else 0
        gain_low_morale_raw = request.form.get('gain_low_morale', '').strip()
        gain_low_morale = int(gain_low_morale_raw) if gain_low_morale_raw else 0
        gain_fright_raw = request.form.get('gain_fright', '').strip()
        gain_fright = int(gain_fright_raw) if gain_fright_raw else 0
        gain_venom_raw = request.form.get('gain_venom', '').strip()
        gain_venom = int(gain_venom_raw) if gain_venom_raw else 0
        gain_weakness_raw = request.form.get('gain_weakness', '').strip()
        gain_weakness = int(gain_weakness_raw) if gain_weakness_raw else 0
        gain_madness_raw = request.form.get('gain_madness', '').strip()
        gain_madness = int(gain_madness_raw) if gain_madness_raw else 0
        remove_low_morale_raw = request.form.get('remove_low_morale', '').strip()
        remove_low_morale = int(remove_low_morale_raw) if remove_low_morale_raw else 0
        remove_fright_raw = request.form.get('remove_fright', '').strip()
        remove_fright = int(remove_fright_raw) if remove_fright_raw else 0
        remove_venom_raw = request.form.get('remove_venom', '').strip()
        remove_venom = int(remove_venom_raw) if remove_venom_raw else 0
        remove_weakness_raw = request.form.get('remove_weakness', '').strip()
        remove_weakness = int(remove_weakness_raw) if remove_weakness_raw else 0
        remove_madness_raw = request.form.get('remove_madness', '').strip()
        remove_madness = int(remove_madness_raw) if remove_madness_raw else 0
        gain_totem = request.form.get('gain_totem', '')
        challenge = request.form.get('challenge', '')
        challenge_level_raw = request.form.get('challenge_level', '').strip()
        challenge_level = int(challenge_level_raw) if challenge_level_raw else 0

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sleeping_gods (location, part, required_keyword, gained_keyword, visited, notes, combat, combat_level, gained, req_coins, req_meat, req_veg, req_grain, req_wood, req_artifacts, gain_coins, gain_meat, gain_veg, gain_grain, gain_wood, gain_artifacts, gain_xp, gain_ship_damage, gain_ship_repair, gain_crew_damage, gain_crew_health, gain_low_morale, gain_fright, gain_venom, gain_weakness, gain_madness, remove_low_morale, remove_fright, remove_venom, remove_weakness, remove_madness, gain_totem, challenge, challenge_level, gain_adventure) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (location, part, required_keyword, gained_keyword, visited, notes, combat, combat_level, gained, req_coins, req_meat, req_veg, req_grain, req_wood, req_artifacts, gain_coins, gain_meat, gain_veg, gain_grain, gain_wood, gain_artifacts, gain_xp, gain_ship_damage, gain_ship_repair, gain_crew_damage, gain_crew_health, gain_low_morale, gain_fright, gain_venom, gain_weakness, gain_madness, remove_low_morale, remove_fright, remove_venom, remove_weakness, remove_madness, gain_totem, challenge, challenge_level, gain_adventure)
        )
        conn.commit()

        cur.close()
        conn.close()

    return render_template(
        'sleeping_gods.html',
    )

@app.route('/search_sleeping_gods_location', methods=['GET'])
def search_sleeping_gods_location():
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

@app.route('/search_sleeping_gods_keyword', methods=['GET'])
def search_sleeping_gods_keyword():
    keyword = request.args.get('term', '')
    conn = get_db_connection()
    cur = conn.cursor()

    # Search  
    cur.execute("""
        SELECT id,* FROM sleeping_gods  
        WHERE required_keyword ILIKE %s OR
              gained_keyword ILIKE %s 
    """, (f"%{keyword}%", f"%{keyword}%"))
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

@app.route('/sleeping_gods_totems')
def sleeping_gods_totems():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, totem, found FROM sleeping_gods_totems ORDER BY id") 
    rows = cur.fetchall()
    cur.close()
    conn.close()

    totems = [{'id': row[0], 'totem': row[1], 'found': row[2]} for row in rows]
    return render_template('sleeping_gods_totems.html', totems=totems)

@app.route('/imperium')
def imperium():
    conn = get_db_connection()
    cur = conn.cursor()

    #// Abbasids ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Abbasids%' AND result ILIKE '%lost%'
    """)
    abba_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Abbasids%' AND result ILIKE '%won%'
    """)
    abba_won=cur.fetchone()[0]

    #// Aksumites ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Aksumites%' AND result ILIKE '%lost%'
    """)
    aksu_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Aksumites%' AND result ILIKE '%won%'
    """)
    aksu_won=cur.fetchone()[0]

    #// Arthurians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Arthurians%' AND result ILIKE '%lost%'
    """)
    arth_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Arthurians%' AND result ILIKE '%won%'
    """)
    arth_won=cur.fetchone()[0]

    #// Atlanteans ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Atlant%' AND result ILIKE '%lost%'
    """)
    atlant_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Atlant%' AND result ILIKE '%won%'
    """)
    atlant_won=cur.fetchone()[0]

    #// Carthaginians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Carthag%' AND result ILIKE '%lost%'
    """)
    carthag_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Carthag%' AND result ILIKE '%won%'
    """)
    carthag_won=cur.fetchone()[0]

    #// Celts ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%celt%' AND result ILIKE '%lost%'
    """)
    celts_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Celt%' AND result ILIKE '%won%'
    """)
    celts_won=cur.fetchone()[0]

    #// Cultists ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%cult%' AND result ILIKE '%lost%'
    """)
    cult_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%cult%' AND result ILIKE '%won%'
    """)
    cult_won=cur.fetchone()[0]

    #// Egyptians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Egyptians%' AND result ILIKE '%lost%'
    """)
    egyp_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Egyptians%' AND result ILIKE '%won%'
    """)
    egyp_won=cur.fetchone()[0]

    #// Greeks ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Greek%' AND result ILIKE '%lost%'
    """)
    greek_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Greek%' AND result ILIKE '%won%'
    """)
    greek_won=cur.fetchone()[0]

    #// Guptas ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE (level ILIKE '%Guptas%' AND result ILIKE '%lost%')  

    """)
    gupt_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Guptas%' AND result ILIKE '%won%' 
    """)
    gupt_won=cur.fetchone()[0]

    #// Inuit ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Inuit%' AND result ILIKE '%lost%'
    """)
    inuit_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Inuit%' AND result ILIKE '%won%'
    """)
    inuit_won=cur.fetchone()[0]

    #// Japanese ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Japanese%' AND result ILIKE '%lost%'
    """)
    japan_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Japanese' AND result ILIKE '%won%'
    """)
    japan_won=cur.fetchone()[0]

    #// Macedonian ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Macedonian%' AND result ILIKE '%lost%'
    """)
    mace_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Macedonian%' AND result ILIKE '%won%'
    """)
    mace_won=cur.fetchone()[0]

    #// Magyars ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Magyars%' AND result ILIKE '%lost%'
    """)
    magy_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Magyars%' AND result ILIKE '%won%'
    """)
    magy_won=cur.fetchone()[0]

    #// Martians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Martians%' AND result ILIKE '%lost%'
    """)
    mart_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Martians%' AND result ILIKE '%won%'
    """)
    mart_won=cur.fetchone()[0]


    #// Mayans ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mayan%' AND result ILIKE '%lost%'
    """)
    may_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mayan%' AND result ILIKE '%won%'
    """)
    may_won=cur.fetchone()[0]

    #// Mauryans ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mauryans%' AND result ILIKE '%lost%'
    """)
    mau_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mauryans%' AND result ILIKE '%won%'
    """)
    mau_won=cur.fetchone()[0]

    #// Mayans ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mayans%' AND result ILIKE '%lost%'
    """)
    may_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Mayans%' AND result ILIKE '%won%'
    """)
    may_won=cur.fetchone()[0]

    #// Minoans ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Minoans%' AND result ILIKE '%lost%'
    """)
    min_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Minoans%' AND result ILIKE '%won%'
    """)
    min_won=cur.fetchone()[0]

    #// Olmecs ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Olmecs%' AND result ILIKE '%lost%'
    """)
    olm_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Olmecs%' AND result ILIKE '%won%'
    """)
    olm_won=cur.fetchone()[0]

    #// Persians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Persian%' AND result ILIKE '%lost%'
    """)
    persian_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Persian%' AND result ILIKE '%won%'
    """)
    persian_won=cur.fetchone()[0]


    #// Polynesians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Polynesian%' AND result ILIKE '%lost%'
    """)
    poly_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Polynesian%' AND result ILIKE '%won%'
    """)
    poly_won=cur.fetchone()[0]

    #// Qin ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Qin%' AND result ILIKE '%lost%'
    """)
    qin_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Qin%' AND result ILIKE '%won%'
    """)
    qin_won=cur.fetchone()[0]

    #// Sassanids ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Sassanids%' AND result ILIKE '%lost%'
    """)
    sass_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Sassanids%' AND result ILIKE '%won%'
    """)
    sass_won=cur.fetchone()[0]

    #// Scythians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Scythians%' AND result ILIKE '%lost%'
    """)
    scy_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Scythians%' AND result ILIKE '%won%'
    """)
    scy_won=cur.fetchone()[0]

    #// Taino ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Taino%' AND result ILIKE '%lost%'
    """)
    tai_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Taino%' AND result ILIKE '%won%'
    """)
    tai_won=cur.fetchone()[0]

    #// Tang ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Tang%' AND result ILIKE '%lost%'
    """)
    tang_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Tang%' AND result ILIKE '%won%'
    """)
    tang_won=cur.fetchone()[0]

    #// Utopians ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Utopians%' AND result ILIKE '%lost%'
    """)
    uto_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Utopians%' AND result ILIKE '%won%'
    """)
    uto_won=cur.fetchone()[0]

    #// Vikings ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Viking%' AND result ILIKE '%lost%'
    """)
    vik_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Viking%' AND result ILIKE '%won%'
    """)
    vik_won=cur.fetchone()[0]

    #// Wagadou ////////////////////////////////////////////////////
    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Wagadou%' AND result ILIKE '%lost%'
    """)
    wag_lost=cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM imperium 
        WHERE level ILIKE '%Wagadou%' AND result ILIKE '%won%'
    """)
    wag_won=cur.fetchone()[0]

    return render_template(
        'imperium.html',
	abba_lost=abba_lost,
	abba_won=abba_won,
	aksu_lost=aksu_lost,
	aksu_won=aksu_won,
	arth_lost=arth_lost,
	arth_won=arth_won,
	atlant_lost=atlant_lost,
	atlant_won=atlant_won,
	carthag_lost=carthag_lost,
	carthag_won=carthag_won,
	celts_lost=celts_lost,
	celts_won=celts_won,
	cult_lost=cult_lost,
	cult_won=cult_won,
	egyp_lost=egyp_lost,
	egyp_won=egyp_won,
	greek_lost=greek_lost,
	greek_won=greek_won,
	gupt_lost=gupt_lost,
	gupt_won=gupt_won,
	inuit_lost=inuit_lost,
	inuit_won=inuit_won,
	japan_lost=japan_lost,
	japan_won=japan_won,
	mace_lost=mace_lost,
	mace_won=mace_won,
	magy_lost=magy_lost,
	magy_won=magy_won,
	mart_lost=mart_lost,
	mart_won=mart_won,
	mau_lost=mau_lost,
	mau_won=mau_won,
	may_lost=may_lost,
	may_won=may_won,
	min_lost=min_lost,
	min_won=min_won,
	olm_lost=olm_lost,
	olm_won=olm_won,
	persian_lost=persian_lost,
	persian_won=persian_won,
	poly_lost=poly_lost,
	poly_won=poly_won,
	qin_lost=qin_lost,
	qin_won=qin_won,
	sass_lost=sass_lost,
	sass_won=sass_won,
	scy_lost=scy_lost,
	scy_won=scy_won,
	tai_lost=tai_lost,
	tai_won=tai_won,
	tang_lost=tang_lost,
	tang_won=tang_won,
	uto_lost=uto_lost,
	uto_won=uto_won,
	vik_lost=vik_lost,
	vik_won=vik_won,
	wag_lost=wag_lost,
	wag_won=wag_won
    )
	
@app.route('/games_overview')
def games_overview():
    conn = get_db_connection()
    cur = conn.cursor()

    # Calculate date boundaries
    today = today_local()
    # Current Periods
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    # Last Periods
    # Last Week
    end_of_last_week = start_of_week - timedelta(days=1)
    start_of_last_week = end_of_last_week - timedelta(days=6)
    # Last Month
    end_of_last_month = start_of_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)
    # Last Year
    end_of_last_year = start_of_year - timedelta(days=1)
    start_of_last_year = end_of_last_year.replace(month=1, day=1)

    # Define a helper function to fetch games for a period
    def fetch_games(start_date, end_date):
        cur.execute("""
            SELECT game_title, COUNT(*) as play_count
            FROM games
            WHERE date_played BETWEEN %s AND %s
            GROUP BY game_title
            ORDER BY play_count DESC
        """, (start_date, end_date))
        return cur.fetchall()

    # Fetch games for each period
    games_this_week = fetch_games(start_of_week, today)
    games_this_month = fetch_games(start_of_month, today)
    games_this_year = fetch_games(start_of_year, today)
    games_last_week = fetch_games(start_of_last_week, end_of_last_week)
    games_last_month = fetch_games(start_of_last_month, end_of_last_month)
    games_last_year = fetch_games(start_of_last_year, end_of_last_year)

    cur.close()
    conn.close()

    return render_template('games_overview.html',
                           games_this_week=games_this_week,
                           games_this_month=games_this_month,
                           games_this_year=games_this_year,
                           games_last_week=games_last_week,
                           games_last_month=games_last_month,
                           games_last_year=games_last_year)

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

@app.route('/all_games')
def all_games():
    conn = get_db_connection()
    cur = conn.cursor()

    # Query to rank all games by play count
    cur.execute("""
    SELECT 
        game_title AS game,
        RANK() OVER (ORDER BY COUNT(*) DESC) AS rank,
        COUNT(*) AS play_count,
        COALESCE(
            (SELECT notes 
             FROM games AS g2 
             WHERE g2.game_title = g.game_title 
               AND g2.notes IS NOT NULL
             ORDER BY g2.date_played DESC 
             LIMIT 1), ''
        ) AS latest_note
    FROM games AS g
    GROUP BY game_title
    ORDER BY game_title;
    """)
    all_games = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('all_games.html', all_games=all_games)

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


@app.route('/rules_assistant')
def rules_assistant():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT game_title FROM games ORDER BY game_title")
    game_titles = [row[0] for row in cur.fetchall()]
    try:
        cur.execute("SELECT game_title, bgg_forum_cache FROM rulebooks WHERE pdf_data IS NOT NULL")
        rulebook_rows = cur.fetchall()
    except Exception:
        conn.rollback()
        cur.execute("SELECT game_title FROM rulebooks WHERE pdf_data IS NOT NULL")
        rulebook_rows = [(r[0], None) for r in cur.fetchall()]
    cur.close()
    conn.close()
    has_rulebook = {g: any(r[0] == g for r in rulebook_rows) for g in game_titles}
    has_bgg = {g: any(r[0] == g and r[1] for r in rulebook_rows) for g in game_titles}
    return render_template('rules_assistant.html', game_titles=game_titles, has_rulebook=has_rulebook, has_bgg=has_bgg)


@app.route('/debug_rulebooks')
def debug_rulebooks():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT game_title, uploaded_at, length(pdf_data) as pdf_chars FROM rulebooks ORDER BY uploaded_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{'game_title': r[0], 'uploaded_at': str(r[1]), 'pdf_chars': r[2]} for r in rows])

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

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    if data.get('password') == os.getenv('APP_PASSWORD'):
        return jsonify({'success': True, 'token': os.getenv('APP_PASSWORD')})
    return jsonify({'success': False, 'message': 'Wrong password'}), 401


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


@app.route('/api/imperium_stats')
def api_imperium_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT level,
            COUNT(CASE WHEN result ILIKE '%won%' THEN 1 END) AS won,
            COUNT(CASE WHEN result ILIKE '%lost%' THEN 1 END) AS lost
        FROM imperium GROUP BY level ORDER BY level
    """)
    rows = [{'level': r[0], 'won': r[1], 'lost': r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/sleeping_gods_totems_data')
def api_sleeping_gods_totems_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, totem, found FROM sleeping_gods_totems ORDER BY id")
    rows = [{'id': r[0], 'totem': r[1], 'found': r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'totems': rows})


@app.route('/api/add_sleeping_gods', methods=['POST'])
def api_add_sleeping_gods():
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


def db_query_schema(cur):
    """Schema description handed to the model, built from the live database."""
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    tables = {}
    for table, column, dtype in cur.fetchall():
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


def db_query_run(sql):
    """Run the query in a read-only transaction. Returns (columns, rows, truncated)."""
    conn = get_db_connection()
    try:
        # Read-only is enforced by Postgres, not by our own parsing of the SQL.
        conn.set_session(readonly=True, autocommit=False)
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = '15s'")
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

    conn = get_db_connection()
    cur = conn.cursor()
    schema = db_query_schema(cur)
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
        return jsonify({'success': False, 'message': sql.split(':', 1)[-1].strip(),
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    problem = db_query_check(sql)
    if problem:
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
        return jsonify({'success': False, 'message': problem, 'sql': sql,
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)}), 400

    # 2. Run it read-only
    try:
        columns, rows, truncated = db_query_run(sql.rstrip(';'))
    except psycopg2.Error as e:
        usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE))
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
        return jsonify({'success': True, 'sql': sql, 'columns': columns, 'rows': rows,
                        'truncated': truncated, 'answer': '',
                        'cost_usd': round(usd, 4), 'cost_nzd': round(nzd, 4)})

    usd, nzd = db_query_cost((sql_response, *DB_QUERY_SQL_PRICE),
                          (answer_response, *DB_QUERY_WRITEUP_PRICE))
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

