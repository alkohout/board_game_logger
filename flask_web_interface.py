from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from datetime import date, datetime, timedelta

load_dotenv()

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="boardgames",
        user="postgres",
        password=os.getenv("PASSWORD")
    )
    return conn

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
	mace_lost=mace_lost,
	mace_won=mace_won,
	mau_lost=mau_lost,
	mau_won=mau_won,
	min_lost=min_lost,
	min_won=min_won,
	olm_lost=olm_lost,
	olm_won=olm_won,
	persian_lost=persian_lost,
	persian_won=persian_won,
	qin_lost=qin_lost,
	qin_won=qin_won,
	scy_lost=scy_lost,
	scy_won=scy_won,
	uto_lost=uto_lost,
	uto_won=uto_won,
	vik_lost=vik_lost,
	vik_won=vik_won
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

