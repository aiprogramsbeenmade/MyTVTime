"""
check_enrichment_gaps.py
Diagnostica: elenca stagioni ed episodi che NON hanno ricevuto l'arricchimento
TMDB (tmdb_season_id / tmdb_episode_id NULL), cosi' puoi capire a colpo d'occhio
cosa manca dopo aver lanciato enrich_metadata.py.

Uso:
    python scripts/check_enrichment_gaps.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mytvtime.db"


def main():
    if not DB_PATH.exists():
        print(f"ERRORE: database non trovato in {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 70)
    print("STAGIONI non trovate su TMDB (tmdb_season_id NULL)")
    print("=" * 70)
    seasons = cur.execute("""
        SELECT s.title, se.season_number, COUNT(e.id) as n_episodi
        FROM seasons se
        JOIN shows s ON se.show_id = s.id
        LEFT JOIN episodes e ON e.show_id = se.show_id AND e.season_number = se.season_number
        WHERE se.tmdb_season_id IS NULL AND s.tmdb_id IS NOT NULL
        GROUP BY se.id
        ORDER BY s.title, se.season_number
    """).fetchall()

    if not seasons:
        print("  (nessuna)")
    for title, season_number, n_ep in seasons:
        print(f"  {title:35s} stagione {season_number:>3}  ({n_ep} episodi coinvolti)")

    print()
    print("=" * 70)
    print("EPISODI non arricchiti (tmdb_episode_id NULL), per stagioni GIA' trovate su TMDB")
    print("=" * 70)
    # Qui escludiamo le stagioni del blocco sopra, per non duplicare l'informazione:
    # questi sono episodi "orfani" dentro stagioni che TMDB HA trovato, quindi il
    # motivo e' piu' probabilmente un disallineamento di numerazione (es. special
    # con stesso season/episode number di un episodio normale, gia' visto in Fase 1).
    episodes = cur.execute("""
        SELECT s.title, e.season_number, e.episode_number, e.title, e.is_special
        FROM episodes e
        JOIN shows s ON e.show_id = s.id
        JOIN seasons se ON se.show_id = e.show_id AND se.season_number = e.season_number
        WHERE e.tmdb_episode_id IS NULL
          AND s.tmdb_id IS NOT NULL
          AND se.tmdb_season_id IS NOT NULL
        ORDER BY s.title, e.season_number, e.episode_number
    """).fetchall()

    if not episodes:
        print("  (nessuno)")
    for title, season_number, ep_number, ep_title, is_special in episodes:
        special_tag = " [SPECIAL]" if is_special else ""
        print(f"  {title:35s} S{season_number:02d}E{ep_number:02d}  '{ep_title}'{special_tag}")

    print()
    print("=" * 70)
    print("RIEPILOGO")
    print("=" * 70)
    total_ep = cur.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    enriched_ep = cur.execute("SELECT COUNT(*) FROM episodes WHERE tmdb_episode_id IS NOT NULL").fetchone()[0]
    print(f"  Episodi totali:          {total_ep}")
    print(f"  Episodi arricchiti:      {enriched_ep}")
    print(f"  Episodi NON arricchiti:  {total_ep - enriched_ep}")
    print(f"    - per stagione non trovata su TMDB: {sum(n for _, _, n in seasons)}")
    print(f"    - per disallineamento numerazione:  {len(episodes)}")

    conn.close()


if __name__ == "__main__":
    main()
