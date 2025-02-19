from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from datetime import date, datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="boardgames",
        user="postgres",
        password="6601"
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

