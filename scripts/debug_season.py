"""
debug_season.py
Stampa fianco a fianco gli episodi di una stagione secondo TMDB (dato grezzo,
cosi' come restituito dall'API) e secondo il nostro database locale, per
capire visivamente eventuali disallineamenti di numerazione o titolo.

Uso:
    python scripts/debug_season.py "Brooklyn Nine-Nine" 8
    python scripts/debug_season.py "I Griffin" 8
    python scripts/debug_season.py "Tulsa King" 4
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tmdb_client import TMDBClient, TMDBError, load_dotenv_if_present

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mytvtime.db"


def main():
    if len(sys.argv) != 3:
        print('Uso: python scripts/debug_season.py "Titolo Serie" numero_stagione')
        sys.exit(1)

    show_title = sys.argv[1]
    season_number = int(sys.argv[2])

    load_dotenv_if_present()
    if not DB_PATH.exists():
        print(f"ERRORE: database non trovato in {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    row = cur.execute("SELECT id, tmdb_id, tvtime_id FROM shows WHERE title = ?", (show_title,)).fetchone()
    if not row:
        # magari il titolo e' stato sovrascritto da TMDB, proviamo una LIKE
        row = cur.execute("SELECT id, tmdb_id, tvtime_id FROM shows WHERE title LIKE ?", (f"%{show_title}%",)).fetchone()
    if not row:
        print(f"ERRORE: nessuna serie trovata con titolo simile a '{show_title}'")
        sys.exit(1)

    show_id, tmdb_id, tvtime_id = row
    if not tmdb_id:
        print(f"ERRORE: la serie '{show_title}' non ha ancora un tmdb_id (arricchimento show non riuscito)")
        sys.exit(1)

    print(f"Serie: '{show_title}' | show_id locale={show_id} | tmdb_id={tmdb_id} | tvdb_id(tvtime_id)={tvtime_id}")
    print()

    print(f"{'='*70}\nEPISODI SECONDO TMDB (stagione {season_number}, dato grezzo dall'API)\n{'='*70}")
    try:
        client = TMDBClient()
        season_data = client.get_season_details(tmdb_id, season_number)
    except TMDBError as e:
        print(f"ERRORE nella chiamata TMDB: {e}")
        conn.close()
        sys.exit(1)

    tmdb_eps = season_data.get("episodes", [])
    print(f"Numero episodi restituiti da TMDB per questa stagione: {len(tmdb_eps)}")
    for ep in tmdb_eps:
        print(f"  E{ep.get('episode_number'):>3}  id={ep.get('id')!s:>10}  '{ep.get('name')}'  (air_date={ep.get('air_date')})")

    print()
    print(f"{'='*70}\nEPISODI SECONDO IL NOSTRO DATABASE LOCALE (stagione {season_number})\n{'='*70}")
    local_eps = cur.execute("""
        SELECT episode_number, title, is_special, tmdb_episode_id
        FROM episodes WHERE show_id = ? AND season_number = ?
        ORDER BY episode_number
    """, (show_id, season_number)).fetchall()
    print(f"Numero episodi nel nostro DB per questa stagione: {len(local_eps)}")
    for ep_number, title, is_special, tmdb_episode_id in local_eps:
        tag = " [SPECIAL]" if is_special else ""
        matched = "OK" if tmdb_episode_id else "NON ARRICCHITO"
        print(f"  E{ep_number:>3}  '{title}'{tag}  -> {matched}")

    conn.close()


if __name__ == "__main__":
    main()