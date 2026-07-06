"""
import_refract.py
Legge i file esportati con l'estensione "TV Time Out by Refract",
pulisce i dati e popola il database SQLite MyTVTime.

Struttura reale confermata (via inspect_export.py) dei file Refract:

FILM (lista di oggetti):
    {
      "id": {"tvdb": 140, "imdb": "tt1790864"},
      "uuid": "...",
      "created_at": "2026-05-18T20:13:14Z",
      "title": "The Maze Runner",
      "year": 2014,
      "watched_at": "2026-05-18T20:13:15Z" | null,
      "is_watched": true,
      "is_favorite": true,
      "rewatch_count": 0
    }

SERIE (lista di oggetti):
    {
      "uuid": "...",
      "id": {"tvdb": 12345, "imdb": null},
      "created_at": "...",
      "title": "Elite",
      "status": "continuing" | "up_to_date" | "not_started_yet",
      "is_favorite": false,
      "_noEpisodeData": false,
      "seasons": [
        {
          "number": 1,
          "is_specials": false,
          "episodes": [
            {
              "id": {"tvdb": 6671792, "imdb": null},
              "number": 1,
              "name": "Benvenuti",
              "special": false,
              "is_watched": true,
              "watched_at": "2026-05-20 19:38:40",
              "rewatch_count": 0,
              "watched_count": 1
            }, ...
          ]
        }, ...
      ]
    }

Uso:
    python scripts/import_refract.py --series tvtime-series-2026-07-04.json --movies tvtime-movies-2026-07-04.json
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mytvtime.db"

# Mappatura status "serie" di TV Time -> watch_status ammessi dallo schema
SHOW_STATUS_MAP = {
    "not_started_yet": "plan_to_watch",
    "continuing": "watching",
    "up_to_date": "watching",   # tutto visto finora; potrà essere raffinato in Fase 2 con lo stato TMDB (Ended/Returning)
}


def normalize_datetime(value):
    """Normalizza i formati data osservati nei file Refract in ISO 8601
    (YYYY-MM-DDTHH:MM:SS), preservando l'orario quando presente."""
    if not value:
        return None
    value = str(value).strip()

    # Es. "2026-05-18T20:13:15Z" (film, timestamp creazione)
    if value.endswith("Z"):
        value = value[:-1]
        # Puo' avere microsecondi tipo "2026-05-20T19:38:31.135015"
        value = value.split(".")[0]
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

    # Es. "2026-05-20 19:38:40" (episodi, spazio invece di 'T')
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass

    # Es. "2026-05-20T19:38:40" gia' nel formato giusto
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass

    print(f"  [WARN] Formato data/ora non riconosciuto, ignorato: {value!r}")
    return None


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------
# IMPORT FILM
# ---------------------------------------------------------------------

def import_movies(conn: sqlite3.Connection, movies: list, stats: dict):
    cur = conn.cursor()

    for m in movies:
        title = m.get("title")
        if not title:
            print(f"  [SKIP] Film senza titolo: {m}")
            stats["movies_skipped"] += 1
            continue

        ext_ids = m.get("id") or {}
        tvdb_id = ext_ids.get("tvdb")
        imdb_id = ext_ids.get("imdb")
        year = m.get("year")
        release_date = str(year) if year else None  # precisione parziale: solo l'anno, TMDB in Fase 2 fornira' la data completa
        is_favorite = 1 if m.get("is_favorite") else 0

        cur.execute("""
            INSERT INTO movies (tvtime_id, imdb_id, title, release_date, is_favorite, watch_status)
            VALUES (?, ?, ?, ?, ?, 'watched')
            ON CONFLICT(tvtime_id) DO UPDATE SET
                imdb_id = excluded.imdb_id,
                title = excluded.title,
                release_date = excluded.release_date,
                is_favorite = excluded.is_favorite
        """, (tvdb_id, imdb_id, title, release_date, is_favorite))

        movie_id = cur.execute(
            "SELECT id FROM movies WHERE tvtime_id = ? OR (tvtime_id IS NULL AND title = ?)",
            (tvdb_id, title)
        ).fetchone()[0]
        stats["movies_imported"] += 1

        if m.get("is_watched") and m.get("watched_at"):
            watched_at = normalize_datetime(m["watched_at"])
            if watched_at:
                play_count = 1 + int(m.get("rewatch_count") or 0)
                exists = cur.execute(
                    "SELECT 1 FROM watch_history WHERE movie_id = ? AND watched_at = ?",
                    (movie_id, watched_at)
                ).fetchone()
                if not exists:
                    cur.execute("""
                        INSERT INTO watch_history (content_type, movie_id, watched_at, play_count, source)
                        VALUES ('movie', ?, ?, ?, 'tvtime_import')
                    """, (movie_id, watched_at, play_count))
                    stats["watch_events_imported"] += 1

    conn.commit()


# ---------------------------------------------------------------------
# IMPORT SERIE + STAGIONI + EPISODI + STORICO
# ---------------------------------------------------------------------

def import_series(conn: sqlite3.Connection, shows: list, stats: dict):
    cur = conn.cursor()

    for s in shows:
        title = s.get("title")
        if not title:
            print(f"  [SKIP] Serie senza titolo: {s}")
            stats["shows_skipped"] += 1
            continue

        ext_ids = s.get("id") or {}
        tvdb_id = ext_ids.get("tvdb")
        imdb_id = ext_ids.get("imdb")
        is_favorite = 1 if s.get("is_favorite") else 0
        watch_status = SHOW_STATUS_MAP.get(s.get("status"), "watching")

        cur.execute("""
            INSERT INTO shows (tvtime_id, imdb_id, title, is_favorite, watch_status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(tvtime_id) DO UPDATE SET
                imdb_id = excluded.imdb_id,
                title = excluded.title,
                is_favorite = excluded.is_favorite,
                watch_status = excluded.watch_status
        """, (tvdb_id, imdb_id, title, is_favorite, watch_status))

        show_id = cur.execute(
            "SELECT id FROM shows WHERE tvtime_id = ? OR (tvtime_id IS NULL AND title = ?)",
            (tvdb_id, title)
        ).fetchone()[0]
        stats["shows_imported"] += 1

        for season in s.get("seasons", []):
            season_number = season.get("number")
            if season_number is None:
                continue
            season_name = "Specials" if season.get("is_specials") else f"Stagione {season_number}"

            cur.execute("""
                INSERT INTO seasons (show_id, season_number, name)
                VALUES (?, ?, ?)
                ON CONFLICT(show_id, season_number) DO UPDATE SET name = excluded.name
            """, (show_id, season_number, season_name))

            for ep in season.get("episodes", []):
                ep_number = ep.get("number")
                if ep_number is None:
                    continue
                ep_title = ep.get("name")
                ep_ext_ids = ep.get("id") or {}
                ep_tvdb_id = ep_ext_ids.get("tvdb")
                is_special = 1 if ep.get("special") else 0

                cur.execute("""
                    INSERT INTO episodes (show_id, season_number, episode_number, is_special, title, tvdb_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(show_id, season_number, episode_number, is_special) DO UPDATE SET
                        title = excluded.title,
                        tvdb_id = excluded.tvdb_id
                """, (show_id, season_number, ep_number, is_special, ep_title, ep_tvdb_id))

                episode_id = cur.execute("""
                    SELECT id FROM episodes
                    WHERE show_id = ? AND season_number = ? AND episode_number = ? AND is_special = ?
                """, (show_id, season_number, ep_number, is_special)).fetchone()[0]

                if ep.get("is_watched") and ep.get("watched_at"):
                    watched_at = normalize_datetime(ep["watched_at"])
                    if watched_at:
                        play_count = ep.get("watched_count") or (1 + int(ep.get("rewatch_count") or 0))
                        exists = cur.execute(
                            "SELECT 1 FROM watch_history WHERE episode_id = ? AND watched_at = ?",
                            (episode_id, watched_at)
                        ).fetchone()
                        if not exists:
                            cur.execute("""
                                INSERT INTO watch_history (content_type, episode_id, watched_at, play_count, source)
                                VALUES ('episode', ?, ?, ?, 'tvtime_import')
                            """, (episode_id, watched_at, play_count))
                            stats["watch_events_imported"] += 1

    conn.commit()


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Importa i dati export di Refract in MyTVTime")
    parser.add_argument("--series", type=str, help="Percorso file JSON export serie TV")
    parser.add_argument("--movies", type=str, help="Percorso file JSON export film")
    args = parser.parse_args()

    if not args.series and not args.movies:
        print("Devi specificare almeno uno tra --series e --movies")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"ERRORE: database non trovato in {DB_PATH}. Esegui prima 'python scripts/init_db.py'")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    stats = {
        "shows_imported": 0, "shows_skipped": 0,
        "movies_imported": 0, "movies_skipped": 0,
        "watch_events_imported": 0,
    }

    try:
        if args.series:
            data = load_json(Path(args.series))
            print(f"\nImportazione serie da {args.series} ...")
            import_series(conn, data, stats)
        if args.movies:
            data = load_json(Path(args.movies))
            print(f"\nImportazione film da {args.movies} ...")
            import_movies(conn, data, stats)
    finally:
        conn.close()

    print("\n" + "=" * 50)
    print("IMPORT COMPLETATO")
    print("=" * 50)
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
