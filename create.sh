# Create a new database called "boardgames"
createdb boardgames

# Connect to the database and create a table called "games"
psql -d boardgames -c "CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    date_played DATE NOT NULL,
    game_title VARCHAR(255) NOT NULL
);"
