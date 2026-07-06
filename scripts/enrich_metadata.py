"""
enrich_metadata.py
Arricchisce shows/movies/seasons/episodes nel database MyTVTime con i
metadati di TMDB (poster, overview, id ufficiale, conteggio stagioni/episodi...).

STRATEGIA DI MATCHING (in ordine di priorita'):
  1. ID esterno (IMDB o TVDB, gia' presenti da Refract) via /find -> quasi mai ambiguo
  2. Ricerca testuale per titolo (+ anno per i film) come fallback
  3. Se il fallback e' ambiguo (piu' risultati plausibili), il record NON viene
     aggiornato automaticamente: viene loggato in tmdb_review_needed.csv per
     una scelta manuale, per evitare di associare per sbaglio il film/serie sbagliata.

Uso:
    python scripts/enrich_metadata.py                  # arricchisce tutto cio' che non ha ancora un tmdb_id
    python scripts/enrich_metadata.py --force           # ri-arricchisce anche cio' che gia' lo ha
    python scripts/enrich_metadata.py --only-movies
    python scripts/enrich_metadata.py --only-shows
    python scripts/enrich_metadata.py --limit 5         # utile per un primo test
    python scripts/enrich_metadata.py --dry-run         # mostra cosa farebbe senza scrivere nel DB

Risoluzione manuale di un caso ambiguo (dopo aver controllato tmdb_review_needed.csv):
    python scripts/enrich_metadata.py --set-show-tmdb TVTIME_ID:TMDB_ID
    python scripts/enrich_metadata.py --set-movie-tmdb TVTIME_ID:TMDB_ID
"""

import argparse
import csv
import difflib
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tmdb_client import TMDBClient, TMDBError, TMDBNotFoundError, load_dotenv_if_present

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mytvtime.db"
REVIEW_CSV_PATH = BASE_DIR / "database" / "tmdb_review_needed.csv"

REQUEST_PAUSE_SECONDS = 0.05  # piccola pausa fra le chiamate, per stare larghi coi rate limit


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def normalize_title(title: str) -> str:
    """Normalizza un titolo per il confronto fuzzy: minuscolo, senza punteggiatura,
    cosi' piccole differenze di formattazione fra TV Time e TMDB non impediscono
    il match. NB: non rimuove indicazioni tipo 'Parte 1/2' perche' altrimenti
    episodi multi-parte diventerebbero indistinguibili fra loro nel fallback."""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)               # rimuove punteggiatura
    t = re.sub(r"\s+", " ", t).strip()
    return t


def has_conflicting_numbers(title_a: str, title_b: str) -> bool:
    """Rileva il caso 'Parte 1' vs 'Parte 2': titoli quasi identici come testo ma
    con numeri diversi al loro interno, che il fuzzy-match da solo non distingue
    (differiscono per un singolo carattere su stringhe lunghe = similarity alta
    comunque). Se entrambi i titoli contengono numeri e questi numeri differiscono,
    li trattiamo come episodi diversi anche se il resto del testo combacia."""
    nums_a = re.findall(r"\d+", title_a or "")
    nums_b = re.findall(r"\d+", title_b or "")
    if nums_a and nums_b and nums_a != nums_b:
        return True
    return False


# =====================================================================
# MATCHING - SERIE
# =====================================================================

def match_show(client: TMDBClient, show: dict):
    """Ritorna (tmdb_id, metodo) se trovato con certezza, altrimenti (None, motivo).
    Se ambiguo, ritorna (None, 'ambiguous') insieme alla lista dei candidati per il log."""
    imdb_id = show["imdb_id"]
    tvdb_id = show["tvtime_id"]
    title = show["title"]

    if imdb_id:
        try:
            result = client.find_by_external_id(imdb_id, "imdb_id")
            tv_results = result.get("tv_results", [])
            if len(tv_results) == 1:
                return tv_results[0]["id"], "imdb_id", []
        except TMDBError as e:
            print(f"  [WARN] find by imdb_id fallita per '{title}': {e}")

    if tvdb_id:
        try:
            result = client.find_by_external_id(tvdb_id, "tvdb_id")
            tv_results = result.get("tv_results", [])
            if len(tv_results) == 1:
                return tv_results[0]["id"], "tvdb_id", []
        except TMDBError as e:
            print(f"  [WARN] find by tvdb_id fallita per '{title}': {e}")

    # Fallback: ricerca testuale
    try:
        candidates = client.search_tv(title)
    except TMDBError as e:
        print(f"  [WARN] search_tv fallita per '{title}': {e}")
        return None, "search_failed", []

    if len(candidates) == 1:
        return candidates[0]["id"], "text_search_unique", []
    elif len(candidates) == 0:
        return None, "no_match", []
    else:
        return None, "ambiguous", candidates[:5]


# =====================================================================
# MATCHING - FILM
# =====================================================================

def match_movie(client: TMDBClient, movie: dict):
    imdb_id = movie["imdb_id"]
    tvdb_id = movie["tvtime_id"]
    title = movie["title"]
    year = None
    if movie["release_date"]:
        try:
            year = int(str(movie["release_date"])[:4])
        except ValueError:
            year = None

    if imdb_id:
        try:
            result = client.find_by_external_id(imdb_id, "imdb_id")
            movie_results = result.get("movie_results", [])
            if len(movie_results) == 1:
                return movie_results[0]["id"], "imdb_id", []
        except TMDBError as e:
            print(f"  [WARN] find by imdb_id fallita per '{title}': {e}")

    if tvdb_id:
        try:
            result = client.find_by_external_id(tvdb_id, "tvdb_id")
            movie_results = result.get("movie_results", [])
            if len(movie_results) == 1:
                return movie_results[0]["id"], "tvdb_id", []
        except TMDBError as e:
            print(f"  [WARN] find by tvdb_id fallita per '{title}': {e}")

    # Fallback: ricerca testuale, usando l'anno (che per i film abbiamo con precisione) per disambiguare
    try:
        candidates = client.search_movie(title, year=year)
    except TMDBError as e:
        print(f"  [WARN] search_movie fallita per '{title}': {e}")
        return None, "search_failed", []

    if year:
        candidates_matching_year = [
            c for c in candidates
            if c.get("release_date", "").startswith(str(year))
        ]
        if len(candidates_matching_year) == 1:
            return candidates_matching_year[0]["id"], "text_search_year_match", []
        candidates = candidates_matching_year or candidates

    if len(candidates) == 1:
        return candidates[0]["id"], "text_search_unique", []
    elif len(candidates) == 0:
        return None, "no_match", []
    else:
        return None, "ambiguous", candidates[:5]


# =====================================================================
# SCRITTURA SU DB
# =====================================================================

def apply_show_details(conn, show_id, tmdb_id, client, dry_run):
    details = client.get_tv_details(tmdb_id)
    if dry_run:
        print(f"    [DRY-RUN] Aggiornerei show_id={show_id} con tmdb_id={tmdb_id} ({details.get('name')})")
        return

    conn.execute("""
        UPDATE shows SET
            tmdb_id = ?,
            title = COALESCE(?, title),
            original_title = ?,
            overview = ?,
            poster_path = ?,
            first_air_date = ?,
            total_seasons = ?,
            total_episodes = ?,
            tmdb_last_synced_at = ?
        WHERE id = ?
    """, (
        tmdb_id,
        details.get("name"),
        details.get("original_name"),
        details.get("overview"),
        details.get("poster_path"),
        details.get("first_air_date") or None,
        details.get("number_of_seasons"),
        details.get("number_of_episodes"),
        now_iso(),
        show_id,
    ))
    conn.commit()


def sync_seasons_and_episodes(conn, show_id, tmdb_id, client, dry_run, stats):
    cur = conn.cursor()
    season_numbers = [row[0] for row in cur.execute(
        "SELECT DISTINCT season_number FROM seasons WHERE show_id = ?", (show_id,)
    ).fetchall()]

    for season_number in season_numbers:
        try:
            season_data = client.get_season_details(tmdb_id, season_number)
        except TMDBNotFoundError:
            stats["seasons_not_found_on_tmdb"] += 1
            ep_count = cur.execute(
                "SELECT COUNT(*) FROM episodes WHERE show_id = ? AND season_number = ?",
                (show_id, season_number)
            ).fetchone()[0]
            stats["episodes_skipped_season_not_found"] += ep_count
            continue
        except TMDBError as e:
            print(f"    [WARN] get_season_details fallita (show_id={show_id}, stagione {season_number}): {e}")
            continue

        time.sleep(REQUEST_PAUSE_SECONDS)

        if not dry_run:
            conn.execute("""
                UPDATE seasons SET
                    tmdb_season_id = ?,
                    name = COALESCE(?, name),
                    episode_count = ?,
                    poster_path = ?
                WHERE show_id = ? AND season_number = ?
            """, (
                season_data.get("id"),
                season_data.get("name"),
                len(season_data.get("episodes", [])),
                season_data.get("poster_path"),
                show_id, season_number,
            ))

        matched_tmdb_ep_numbers = set()

        for ep in season_data.get("episodes", []):
            ep_number = ep.get("episode_number")
            if ep_number is None:
                continue

            # NB: TMDB raggruppa gli special sotto season_number=0; se nel nostro DB
            # uno special e' stato importato con lo stesso season_number di un episodio
            # normale (caso osservato con Refract, es. Black Mirror), qui potremmo non
            # trovare un corrispondente is_special=1 in questa stagione: viene semplicemente
            # ignorato (nessun errore) e conteggiato in stats.
            existing = cur.execute("""
                SELECT id, is_special FROM episodes
                WHERE show_id = ? AND season_number = ? AND episode_number = ?
            """, (show_id, season_number, ep_number)).fetchall()

            if not existing:
                stats["episodes_not_matched"] += 1
                continue

            # Se c'e' ambiguita' (normale + special con stesso numero), aggiorniamo
            # quello non-special di default, che e' il caso piu' comune.
            target_id, target_is_special, target_title = None, None, None
            for r_id, r_special in existing:
                if r_special == 0:
                    target_id, target_is_special = r_id, r_special
                    break
            if target_id is None:
                target_id, target_is_special = existing[0]
            target_title = cur.execute("SELECT title FROM episodes WHERE id = ?", (target_id,)).fetchone()[0]

            # SANITY CHECK: se sia il titolo locale che quello TMDB sono valorizzati
            # ma non si somigliano per nulla, e' piu' probabile un disallineamento di
            # numerazione (episodio diverso) che un vero match: rifiutiamo l'update
            # diretto e lasciamo che sia il fallback per titolo (sotto) a cercare il
            # vero corrispondente altrove, per non scrivere dati dell'episodio sbagliato.
            if target_title and ep.get("name"):
                similarity = difflib.SequenceMatcher(
                    None, normalize_title(target_title), normalize_title(ep.get("name"))
                ).ratio()
                if similarity < 0.35 or has_conflicting_numbers(target_title, ep.get("name")):
                    stats["episodes_number_match_rejected"] += 1
                    continue  # NB: non aggiungiamo ep_number a matched_tmdb_ep_numbers: resta disponibile per il fallback

            matched_tmdb_ep_numbers.add(ep_number)

            if not dry_run:
                conn.execute("""
                    UPDATE episodes SET
                        tmdb_episode_id = ?,
                        air_date = ?,
                        overview = ?
                    WHERE id = ?
                """, (
                    ep.get("id"),
                    ep.get("air_date"),
                    ep.get("overview"),
                    target_id,
                ))
            stats["episodes_enriched"] += 1

        # ---------------------------------------------------------------
        # FALLBACK PER TITOLO: solo per episodi NON-special rimasti orfani
        # dopo il match per numero. Serve per i casi di rinumerazione reale
        # (es. episodi doppi accorpati diversamente fra TV Time e TMDB).
        # Volutamente escluso per gli special: il rumore fra contenuti
        # extra non canonici renderebbe il fuzzy-match troppo rischioso.
        # ---------------------------------------------------------------
        unmatched_local = cur.execute("""
            SELECT id, episode_number, title FROM episodes
            WHERE show_id = ? AND season_number = ? AND is_special = 0 AND tmdb_episode_id IS NULL
        """, (show_id, season_number)).fetchall()

        if unmatched_local:
            available_tmdb_eps = [
                e for e in season_data.get("episodes", [])
                if e.get("episode_number") not in matched_tmdb_ep_numbers and e.get("name")
            ]

            for local_id, local_ep_number, local_title in unmatched_local:
                norm_local = normalize_title(local_title)
                if not norm_local or not available_tmdb_eps:
                    continue

                candidates = [e for e in available_tmdb_eps if not has_conflicting_numbers(local_title, e.get("name"))]
                if not candidates:
                    continue

                scored = sorted(
                    (
                        (difflib.SequenceMatcher(None, norm_local, normalize_title(e.get("name"))).ratio(), e)
                        for e in candidates
                    ),
                    key=lambda pair: pair[0], reverse=True
                )

                best_score, best_ep = scored[0]
                second_score = scored[1][0] if len(scored) > 1 else 0.0

                if best_score >= 0.55 and (best_score - second_score) >= 0.15:
                    if not dry_run:
                        conn.execute("""
                            UPDATE episodes SET
                                tmdb_episode_id = ?,
                                air_date = ?,
                                overview = ?
                            WHERE id = ?
                        """, (best_ep.get("id"), best_ep.get("air_date"), best_ep.get("overview"), local_id))
                    stats["episodes_matched_by_title_fallback"] += 1
                    stats["episodes_enriched"] += 1
                    available_tmdb_eps.remove(best_ep)
                    print(f"    [FALLBACK TITOLO] S{season_number:02d}E{local_ep_number:02d} "
                          f"'{local_title}' -> TMDB '{best_ep.get('name')}' (score={best_score:.2f})")

    if not dry_run:
        conn.commit()


def apply_movie_details(conn, movie_id, tmdb_id, client, dry_run):
    details = client.get_movie_details(tmdb_id)
    if dry_run:
        print(f"    [DRY-RUN] Aggiornerei movie_id={movie_id} con tmdb_id={tmdb_id} ({details.get('title')})")
        return

    runtime = details.get("runtime")
    conn.execute("""
        UPDATE movies SET
            tmdb_id = ?,
            title = COALESCE(?, title),
            original_title = ?,
            overview = ?,
            poster_path = ?,
            release_date = ?,
            runtime_minutes = ?,
            tmdb_last_synced_at = ?
        WHERE id = ?
    """, (
        tmdb_id,
        details.get("title"),
        details.get("original_title"),
        details.get("overview"),
        details.get("poster_path"),
        details.get("release_date") or None,
        runtime,
        now_iso(),
        movie_id,
    ))
    conn.commit()


# =====================================================================
# LOG DEI CASI AMBIGUI / NON TROVATI
# =====================================================================

def init_review_log():
    is_new = not REVIEW_CSV_PATH.exists()
    f = open(REVIEW_CSV_PATH, "a", newline="", encoding="utf-8")
    writer = csv.writer(f)
    if is_new:
        writer.writerow(["tipo", "tvtime_id", "titolo", "motivo", "candidati_tmdb_id_e_titolo"])
    return f, writer


def log_review(writer, tipo, tvtime_id, titolo, motivo, candidates):
    candidates_str = "; ".join(
        f"{c['id']}:{c.get('name') or c.get('title')} ({c.get('first_air_date') or c.get('release_date','')[:4]})"
        for c in candidates
    )
    writer.writerow([tipo, tvtime_id, titolo, motivo, candidates_str])


# =====================================================================
# MAIN
# =====================================================================

def process_shows(conn, client, force, limit, dry_run, review_writer, stats):
    cur = conn.cursor()
    query = "SELECT id, tvtime_id, imdb_id, title FROM shows"
    if not force:
        query += " WHERE tmdb_id IS NULL"
    if limit:
        query += f" LIMIT {int(limit)}"
    shows = cur.execute(query).fetchall()

    print(f"\n--- Arricchimento SERIE ({len(shows)} da processare) ---")
    for show_id, tvtime_id, imdb_id, title in shows:
        print(f"  '{title}' (tvtime_id={tvtime_id}) ...")
        show_dict = {"imdb_id": imdb_id, "tvtime_id": tvtime_id, "title": title}
        tmdb_id, method, candidates = match_show(client, show_dict)
        time.sleep(REQUEST_PAUSE_SECONDS)

        if tmdb_id:
            print(f"    -> match trovato: tmdb_id={tmdb_id} (metodo: {method})")
            apply_show_details(conn, show_id, tmdb_id, client, dry_run)
            sync_seasons_and_episodes(conn, show_id, tmdb_id, client, dry_run, stats)
            stats["shows_enriched"] += 1
        else:
            print(f"    -> NESSUN match automatico (motivo: {method})")
            log_review(review_writer, "show", tvtime_id, title, method, candidates)
            stats["shows_needing_review"] += 1


def process_movies(conn, client, force, limit, dry_run, review_writer, stats):
    cur = conn.cursor()
    query = "SELECT id, tvtime_id, imdb_id, title, release_date FROM movies"
    if not force:
        query += " WHERE tmdb_id IS NULL"
    if limit:
        query += f" LIMIT {int(limit)}"
    movies = cur.execute(query).fetchall()

    print(f"\n--- Arricchimento FILM ({len(movies)} da processare) ---")
    for movie_id, tvtime_id, imdb_id, title, release_date in movies:
        print(f"  '{title}' (tvtime_id={tvtime_id}) ...")
        movie_dict = {"imdb_id": imdb_id, "tvtime_id": tvtime_id, "title": title, "release_date": release_date}
        tmdb_id, method, candidates = match_movie(client, movie_dict)
        time.sleep(REQUEST_PAUSE_SECONDS)

        if tmdb_id:
            print(f"    -> match trovato: tmdb_id={tmdb_id} (metodo: {method})")
            apply_movie_details(conn, movie_id, tmdb_id, client, dry_run)
            stats["movies_enriched"] += 1
        else:
            print(f"    -> NESSUN match automatico (motivo: {method})")
            log_review(review_writer, "movie", tvtime_id, title, method, candidates)
            stats["movies_needing_review"] += 1


def manual_set(conn, client, kind, mapping_str, dry_run):
    tvtime_id_str, tmdb_id_str = mapping_str.split(":")
    tvtime_id, tmdb_id = int(tvtime_id_str), int(tmdb_id_str)
    cur = conn.cursor()

    if kind == "show":
        row = cur.execute("SELECT id FROM shows WHERE tvtime_id = ?", (tvtime_id,)).fetchone()
        if not row:
            print(f"ERRORE: nessuna serie trovata con tvtime_id={tvtime_id}")
            return
        show_id = row[0]
        stats = {"episodes_enriched": 0, "episodes_not_matched": 0, "seasons_not_found_on_tmdb": 0,
                  "episodes_skipped_season_not_found": 0, "episodes_matched_by_title_fallback": 0,
                  "episodes_number_match_rejected": 0}
        apply_show_details(conn, show_id, tmdb_id, client, dry_run)
        sync_seasons_and_episodes(conn, show_id, tmdb_id, client, dry_run, stats)
        print(f"Serie tvtime_id={tvtime_id} associata manualmente a tmdb_id={tmdb_id}. Stats episodi: {stats}")
    else:
        row = cur.execute("SELECT id FROM movies WHERE tvtime_id = ?", (tvtime_id,)).fetchone()
        if not row:
            print(f"ERRORE: nessun film trovato con tvtime_id={tvtime_id}")
            return
        movie_id = row[0]
        apply_movie_details(conn, movie_id, tmdb_id, client, dry_run)
        print(f"Film tvtime_id={tvtime_id} associato manualmente a tmdb_id={tmdb_id}.")


def main():
    parser = argparse.ArgumentParser(description="Arricchisce il database MyTVTime con i metadati TMDB")
    parser.add_argument("--force", action="store_true", help="Ri-arricchisce anche i record che hanno gia' un tmdb_id")
    parser.add_argument("--only-shows", action="store_true")
    parser.add_argument("--only-movies", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Limita il numero di record processati (utile per test)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa farebbe senza scrivere nel DB")
    parser.add_argument("--set-show-tmdb", type=str, help="Formato TVTIME_ID:TMDB_ID, per risolvere manualmente un caso ambiguo")
    parser.add_argument("--set-movie-tmdb", type=str, help="Formato TVTIME_ID:TMDB_ID, per risolvere manualmente un caso ambiguo")
    args = parser.parse_args()

    load_dotenv_if_present()

    if not DB_PATH.exists():
        print(f"ERRORE: database non trovato in {DB_PATH}. Esegui prima init_db.py e import_refract.py")
        sys.exit(1)

    try:
        client = TMDBClient()
    except TMDBError as e:
        print(f"ERRORE di configurazione TMDB: {e}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    if args.set_show_tmdb:
        manual_set(conn, client, "show", args.set_show_tmdb, args.dry_run)
        conn.close()
        return
    if args.set_movie_tmdb:
        manual_set(conn, client, "movie", args.set_movie_tmdb, args.dry_run)
        conn.close()
        return

    review_file, review_writer = init_review_log()
    stats = {
        "shows_enriched": 0, "shows_needing_review": 0,
        "movies_enriched": 0, "movies_needing_review": 0,
        "episodes_enriched": 0, "episodes_not_matched": 0,
        "seasons_not_found_on_tmdb": 0, "episodes_skipped_season_not_found": 0,
        "episodes_matched_by_title_fallback": 0, "episodes_number_match_rejected": 0,
    }

    try:
        if not args.only_movies:
            process_shows(conn, client, args.force, args.limit, args.dry_run, review_writer, stats)
        if not args.only_shows:
            process_movies(conn, client, args.force, args.limit, args.dry_run, review_writer, stats)
    finally:
        review_file.close()
        conn.close()

    print("\n" + "=" * 50)
    print("ARRICCHIMENTO COMPLETATO")
    print("=" * 50)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["shows_needing_review"] or stats["movies_needing_review"]:
        print(f"\nCasi da rivedere manualmente salvati in: {REVIEW_CSV_PATH}")
        print("Risolvili con: python scripts/enrich_metadata.py --set-show-tmdb TVTIME_ID:TMDB_ID")


if __name__ == "__main__":
    main()