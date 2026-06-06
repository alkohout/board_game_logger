from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import psycopg2
import os
import re
import random
import time
import anthropic
import base64
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from datetime import date, datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB upload limit
app.secret_key = os.getenv('SECRET_KEY')

@app.before_request
def require_login():
    if request.endpoint in ('login', 'logout', 'static'):
        return
    if not session.get('logged_in'):
        return redirect(url_for('login'))

selector_pool = []
selector_choices = []

_bgg_id_cache = {}

STOP_WORDS = {'the','a','an','is','in','on','at','to','for','of','and','or',
              'do','how','what','when','can','i','if','it','be','with','my',
              'does','are','was','were','have','has','about','which','that'}

def _bgg_fetch(url, params, timeout=10):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return ET.fromstring(r.content)
            if r.status_code == 202:
                time.sleep(2 + attempt)
                continue
        except Exception:
            return None
    return None

def bgg_search_game_id(game_title):
    if game_title in _bgg_id_cache:
        return _bgg_id_cache[game_title]
    for exact in ('1', '0'):
        try:
            root = _bgg_fetch('https://boardgamegeek.com/xmlapi2/search',
                              {'query': game_title, 'type': 'boardgame', 'exact': exact})
            if root is not None:
                items = root.findall('item')
                if items:
                    gid = items[0].get('id')
                    _bgg_id_cache[game_title] = gid
                    return gid
        except Exception:
            pass
    return None

def bgg_get_rules_forum_id(game_id):
    try:
        root = _bgg_fetch('https://boardgamegeek.com/xmlapi2/forumlist',
                          {'id': game_id, 'type': 'thing'})
        if root is None:
            return None
        forums = root.findall('forum')
        for f in forums:
            if 'rule' in f.get('title', '').lower():
                return f.get('id')
        return forums[0].get('id') if forums else None
    except Exception:
        return None

def bgg_get_relevant_threads(forum_id, question, max_threads=5):
    try:
        root = _bgg_fetch('https://boardgamegeek.com/xmlapi2/forum',
                          {'id': forum_id, 'page': 1})
        if root is None:
            return []
        threads = root.findall('threads/thread')
    except Exception:
        return []

    question_words = set(question.lower().split()) - STOP_WORDS
    scored = []
    for t in threads:
        subject = t.get('subject', '')
        score = len(question_words & set(subject.lower().split()))
        scored.append((score, t.get('id'), subject))
    scored.sort(reverse=True)

    results = []
    for score, thread_id, subject in scored[:max_threads]:
        try:
            root = _bgg_fetch('https://boardgamegeek.com/xmlapi2/thread',
                              {'id': thread_id})
            if root is None:
                continue
            posts = []
            for article in root.findall('articles/article')[:8]:
                body = article.find('body')
                if body is not None and body.text:
                    posts.append(body.text.strip()[:1200])
            if posts:
                results.append(f"Thread: {subject}\n\n" + '\n\n---\n\n'.join(posts))
        except Exception:
            continue
    return results


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
    today = date.today()
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

    cur.close()
    conn.close()
    return render_template(
        'index.html',
        game_titles=sorted(game_titles),
        top_games=top_games,
        today=date.today().isoformat(),
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
    today = date.today()
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
    today = datetime.now().date()
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

    print(rankings)
    # Create a dictionary of game titles and their rankings
    rankings_dict = {game[0]: game[1] for game in rankings}

    # Get the ranking for the specified game
    ranking = rankings_dict.get(game_title, "Not ranked")

    # Search for the most recent play and notes
    cur.execute("""
        SELECT COALESCE( (SELECT g.id FROM games AS g 
        WHERE g.game_title ILIKE %s 
        AND ( (g.notes IS NOT NULL AND g.notes <> '' AND g.notes <> 'null') OR
		(g.result IS NOT NULL AND g.result <> '') )
	ORDER BY g.id DESC
        LIMIT 1),0)
    """, (f"%{game_title}%",))
    nonempty = cur.fetchone()

    # Fetch notes
    cur.execute("SELECT notes FROM games WHERE id = %s", nonempty)
    notes_nonempty = (res := cur.fetchone()) and res[0]

    # Fetch result
    cur.execute("SELECT result FROM games WHERE id = %s", (f"{nonempty[0]}",))
    result_nonempty = (res := cur.fetchone()) and res[0]

    # Fetch level 
    cur.execute("SELECT level FROM games WHERE id = %s", (f"{nonempty[0]}",))
    level_nonempty = (res := cur.fetchone()) and res[0]

    # Fetch my_score 
    cur.execute("SELECT my_score FROM games WHERE id = %s", (f"{nonempty[0]}",))
    my_score_nonempty = (res := cur.fetchone()) and res[0]

    # Fetch bot_score 
    cur.execute("SELECT bot_score FROM games WHERE id = %s", (f"{nonempty[0]}",))
    bot_score_nonempty = (res := cur.fetchone()) and res[0]

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
    cur.execute("SELECT game_title, bgg_game_id FROM rulebooks WHERE pdf_data IS NOT NULL")
    rulebook_rows = cur.fetchall()
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
    if not game_title:
        return jsonify({'success': False, 'message': 'Game title required'}), 400
    if 'pdf_file' not in request.files or request.files['pdf_file'].filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    pdf_file = request.files['pdf_file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'File must be a PDF'}), 400

    bgg_url = request.form.get('bgg_url', '').strip()
    bgg_id = None
    if bgg_url:
        m = re.search(r'/boardgame/(\d+)', bgg_url)
        if m:
            bgg_id = m.group(1)

    pdf_file.stream.seek(0)
    pdf_b64 = base64.standard_b64encode(pdf_file.stream.read()).decode('utf-8')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO rulebooks (game_title, pdf_data, bgg_game_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (game_title) DO UPDATE
                SET pdf_data = EXCLUDED.pdf_data,
                    bgg_game_id = COALESCE(EXCLUDED.bgg_game_id, rulebooks.bgg_game_id),
                    uploaded_at = NOW()
        """, (game_title, pdf_b64, bgg_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'DB error: {str(e)}'}), 500
    return jsonify({'success': True, 'message': f'Rulebook saved for {game_title}', 'bgg_linked': bgg_id is not None})

@app.route('/set_bgg_url', methods=['POST'])
def set_bgg_url():
    try:
        data = request.get_json()
        game_title = (data.get('game_title') or '').strip()
        bgg_url = (data.get('bgg_url') or '').strip()
        if not game_title or not bgg_url:
            return jsonify({'success': False, 'message': 'Game title and BGG URL required'}), 400
        m = re.search(r'/boardgame/(\d+)', bgg_url)
        if not m:
            return jsonify({'success': False, 'message': 'Could not find game ID in URL — paste the full BGG game page URL'}), 400
        bgg_id = m.group(1)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE rulebooks SET bgg_game_id = %s WHERE game_title = %s", (bgg_id, game_title))
        conn.commit()
        cur.close()
        conn.close()
        _bgg_id_cache[game_title] = bgg_id
        return jsonify({'success': True, 'bgg_id': bgg_id})
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
        cur.execute("SELECT pdf_data, bgg_game_id FROM rulebooks WHERE game_title = %s", (game_title,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row[0]:
            return jsonify({'success': False, 'message': f'No rulebook found for {game_title} — try re-uploading'}), 404

        pdf_b64, stored_bgg_id = row[0], row[1]
        if stored_bgg_id:
            _bgg_id_cache[game_title] = stored_bgg_id

        # Fetch relevant BGG forum threads
        bgg_section = ''
        bgg_game_id = stored_bgg_id or bgg_search_game_id(game_title)
        if bgg_game_id:
            forum_id = bgg_get_rules_forum_id(bgg_game_id)
            if forum_id:
                threads = bgg_get_relevant_threads(forum_id, question)
                if threads:
                    bgg_section = '\n\n---\n\n'.join(threads)

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'message': 'ANTHROPIC_API_KEY not configured'}), 500

        # Build user message: PDF document + optional BGG text + question
        user_content = [
            {
                'type': 'document',
                'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': pdf_b64}
            }
        ]
        question_text = question
        if bgg_section:
            question_text = f'BGG Rules Forum Discussions:\n{bgg_section}\n\nQuestion: {question}'
        user_content.append({'type': 'text', 'text': question_text})

        sources_used = 'rulebook' + (' + BGG forum' if bgg_section else '')
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-8',
            max_tokens=1024,
            system=(
                f'You are a board game rules expert for "{game_title}". '
                f'Answer using the rulebook and BGG forum discussions provided. '
                f'Cite which source supports your answer. '
                f'If neither addresses the question, say so.'
            ),
            messages=[{'role': 'user', 'content': user_content}]
        )
        return jsonify({'success': True, 'answer': response.content[0].text, 'sources': sources_used})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')

