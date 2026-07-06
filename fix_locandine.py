import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

# Connessione al database SQLite dell'applicazione
conn = sqlite3.connect("database/mytvtime.db")
cursor = conn.cursor()

# 1. Recupera le serie con tmdb_id mancante
cursor.execute("SELECT id, title FROM movies WHERE tmdb_id IS NULL")
missing_items = cursor.fetchall()

for db_id, title in missing_items:
    # 2. Cerca il titolo esatto su TMDB
    url = f"https://api.themoviedb.org/3/search/movies?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(url).json()

    if response.get("results"):
        # Seleziona il primo risultato (il più rilevante)
        best_match = response["results"][0]
        tmdb_id = best_match["id"]

        # 3. Salva l'ID nel database
        cursor.execute("UPDATE movies SET tmdb_id = ? WHERE id = ?", (tmdb_id, db_id))
        print(f"Collegato: {title} -> TMDB ID: {tmdb_id}")
    else:
        print(f"Nessun match trovato per: {title}")

conn.commit()
conn.close()