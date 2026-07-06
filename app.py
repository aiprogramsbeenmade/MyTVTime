import streamlit as st
import sqlite3
import os
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# CONFIGURAZIONE PAGINA
# =====================================================================
st.set_page_config(
    page_title="MyTVTime",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# STILE GRAFICO
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: radial-gradient(circle at 10% 0%, #1a1c24 0%, #101117 45%, #0b0c10 100%);
        color: #EDEDED;
    }

    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #FF7A45, #FF3C78);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }

    section[data-testid="stSidebar"] {
        background-color: #14151c !important;
        border-right: 1px solid #24262f;
    }

    /* Card contenuti */
    .media-card {
        position: relative;
        background: linear-gradient(160deg, #1b1c24 0%, #16171d 100%);
        border-radius: 14px;
        padding: 12px;
        border: 1px solid #26272f;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        text-align: center;
        margin-bottom: 8px;
        cursor: pointer;
    }

    .poster-wrap {
        width: 100%;
        aspect-ratio: 2 / 3;
        border-radius: 10px;
        overflow: hidden;
        background: linear-gradient(135deg, #23242e, #1a1b22);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 8px;
    }
    .poster-wrap img { width: 100%; height: 100%; object-fit: cover; }
    .poster-placeholder { font-size: 2.6rem; opacity: 0.35; }

    .media-title {
        font-weight: 700;
        font-size: 0.92rem;
        margin-top: 2px;
        height: 42px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    .stars-row { color: #FFC93C; font-size: 0.95rem; letter-spacing: 2px; margin: 4px 0; }

    /* --- Card cliccabile: la copertina intera apre la gestione --- */

    /* 1. SOLO le colonne che contengono una media-card fanno da perimetro spaziale */
    div[data-testid="stColumn"]:has(.media-card) {
        position: relative !important;
    }

    /* 2. Disintegra i limiti strutturali dei wrapper SOLO dentro le colonne delle card */
    div[data-testid="stColumn"]:has(.media-card) div[data-testid="stElementContainer"]:has(.stButton),
    div[data-testid="stColumn"]:has(.media-card) .stButton {
        display: contents !important;
    }

    /* 3. Il pulsante invisibile si espande al 100% SOLO se si trova dentro la colonna di una card */
    div[data-testid="stColumn"]:has(.media-card) button {
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        opacity: 0 !important;               
        z-index: 9999 !important;            
        cursor: pointer !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 4. Effetto HOVER: isolato alla colonna specifica */
    div[data-testid="stColumn"]:has(.media-card):hover .media-card {
        transform: translateY(-4px) !important;
        border-color: #FF3C78 !important;
        box-shadow: 0 10px 30px rgba(255, 60, 120, 0.22) !important;
        transition: all 0.2s ease-in-out !important;
    }

    /* 5. Mostra il badge "Apri" centrato sopra la card puntata */
    div[data-testid="stColumn"]:has(.media-card):hover .media-card::after {
        content: "✏️ Apri" !important;
        position: absolute !important;
        bottom: 12px !important; 
        left: 50% !important;
        transform: translateX(-50%) !important;
        background: rgba(0, 0, 0, 0.85) !important;
        color: #fff !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        pointer-events: none !important;
        z-index: 10000 !important; 
        border: 1px solid #FF3C78 !important;
        white-space: nowrap !important;
    }

    /* --- Status Badges --- */
    .status-badge {
        font-size: 0.68rem;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .status-watching  { background-color: rgba(255, 122, 69, 0.18); color: #FF7A45; border: 1px solid #FF7A45; }
    .status-completed { background-color: rgba(46, 204, 113, 0.15); color: #2ECC71; border: 1px solid #2ECC71; }
    .status-watchlist { background-color: rgba(84, 160, 255, 0.15); color: #54A0FF; border: 1px solid #54A0FF; }

    /* --- Pulsanti Standard dell'App (Inclusi quelli della Modale) --- */
    div.stButton > button {
        background: linear-gradient(90deg, #FF7A45, #FF3C78) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        width: 100%;
        transition: filter 0.15s, transform 0.1s;
    }
    div.stButton > button:hover { filter: brightness(1.12); transform: translateY(-1px); }
    div.stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid #FF3C78 !important;
        color: #FF3C78 !important;
    }

    /* --- Metrics --- */
    div[data-testid="stMetric"] {
        background-color: #181923;
        border: 1px solid #26272f;
        border-radius: 10px;
        padding: 10px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# DATABASE
# =====================================================================
DB_NAME = os.path.join("database", "mytvtime.db")


def get_db_connection():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Inizializza il database riflettendo fedelmente lo schema ufficiale."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shows (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        tmdb_id             INTEGER UNIQUE,
        tvtime_id           INTEGER UNIQUE,
        imdb_id             TEXT UNIQUE,
        title               TEXT NOT NULL,
        original_title      TEXT,
        overview            TEXT,
        poster_path         TEXT,
        first_air_date      TEXT,
        total_seasons       INTEGER,
        total_episodes      INTEGER,
        episode_per_season  TEXT,
        watch_status        TEXT NOT NULL DEFAULT 'watching'
                             CHECK (watch_status IN ('watching','completed','on_hold','dropped','plan_to_watch')),
        is_favorite         INTEGER NOT NULL DEFAULT 0,
        rating              REAL DEFAULT 0,
        tmdb_last_synced_at TEXT,
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        show_id         INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
        season_number   INTEGER NOT NULL,
        tmdb_season_id  INTEGER,
        name            TEXT,
        episode_count   INTEGER,
        poster_path     TEXT,
        UNIQUE (show_id, season_number)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS episodes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        show_id         INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
        season_number   INTEGER NOT NULL,
        episode_number  INTEGER NOT NULL,
        tmdb_episode_id INTEGER,
        tvdb_id         INTEGER,
        is_special      INTEGER NOT NULL DEFAULT 0,
        title           TEXT,
        air_date        TEXT,
        overview        TEXT,
        UNIQUE (show_id, season_number, episode_number, is_special)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        tmdb_id             INTEGER UNIQUE,
        tvtime_id           INTEGER UNIQUE,
        imdb_id             TEXT UNIQUE,
        title               TEXT NOT NULL,
        original_title      TEXT,
        overview            TEXT,
        poster_path         TEXT,
        release_date        TEXT,
        runtime_minutes     INTEGER,
        watch_status        TEXT NOT NULL DEFAULT 'plan_to_watch'
                             CHECK (watch_status IN ('watched','plan_to_watch','dropped')),
        is_favorite         INTEGER NOT NULL DEFAULT 0,
        rating              REAL DEFAULT 0,
        tmdb_last_synced_at TEXT,
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watch_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        content_type    TEXT NOT NULL CHECK (content_type IN ('episode','movie')),
        episode_id      INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
        movie_id        INTEGER REFERENCES movies(id) ON DELETE CASCADE,
        watched_at      TEXT NOT NULL,
        play_count      INTEGER NOT NULL DEFAULT 1,
        rating          REAL,
        notes           TEXT,
        source          TEXT DEFAULT 'tvtime_import',
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        CHECK (
            (content_type = 'episode' AND episode_id IS NOT NULL AND movie_id IS NULL)
            OR
            (content_type = 'movie'   AND movie_id   IS NOT NULL AND episode_id IS NULL)
        )
    );
    """)

    # Indici
    cur.execute("CREATE INDEX IF NOT EXISTS idx_seasons_show          ON seasons(show_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_show         ON episodes(show_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_show_season  ON episodes(show_id, season_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_watch_history_episode ON watch_history(episode_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_watch_history_movie   ON watch_history(movie_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_watch_history_date    ON watch_history(watched_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shows_status          ON shows(watch_status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_status         ON movies(watch_status);")

    conn.commit()
    conn.close()


init_db()


def get_or_create_episode_id(conn, show_id, season_number, episode_number):
    """Garantisce l'esistenza dell'anagrafica episodio e ne restituisce l'ID."""
    row = conn.execute(
        "SELECT id FROM episodes WHERE show_id = ? AND season_number = ? AND episode_number = ?",
        (show_id, season_number, episode_number)
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO episodes (show_id, season_number, episode_number) VALUES (?, ?, ?)",
        (show_id, season_number, episode_number)
    )
    return cursor.lastrowid


# =====================================================================
# CHIAVE API TMDB
# =====================================================================
if "tmdb_api_key" not in st.session_state:
    st.session_state["tmdb_api_key"] = os.getenv("TMDB_API_KEY", "")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def get_poster_url(poster_path):
    if poster_path and poster_path not in ("None", ""):
        if poster_path.startswith("http"):
            return poster_path
        return f"{TMDB_IMAGE_BASE}{poster_path}"
    return None


def poster_html(poster_path, fallback_icon="🎬"):
    url = get_poster_url(poster_path)
    if url:
        return f'<div class="poster-wrap"><img src="{url}" /></div>'
    return f'<div class="poster-wrap"><span class="poster-placeholder">{fallback_icon}</span></div>'


def query_tmdb_search(api_key, query, media_type="movie"):
    if not api_key:
        return []
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/search/{endpoint}"
    params = {"api_key": api_key, "query": query, "language": "it-IT"}
    try:
        response = requests.get(url, params=params, timeout=6)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception:
        pass
    return []


def query_tmdb_tv_details(api_key, tmdb_id):
    if not api_key:
        return None
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {"api_key": api_key, "language": "it-IT"}
    try:
        response = requests.get(url, params=params, timeout=6)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def build_episodes_per_season(tv_details):
    seasons = tv_details.get("seasons", []) if tv_details else []
    eps = {}
    for s in seasons:
        num = s.get("season_number")
        count = s.get("episode_count", 0)
        if num and num > 0 and count:
            eps[str(num)] = count
    return eps


# =====================================================================
# ETICHETTE DI STATO
# =====================================================================
MOVIE_STATUS_LABELS = {"plan_to_watch": "Da Vedere", "watched": "Visto", "dropped": "Abbandonato"}
SHOW_STATUS_LABELS = {"plan_to_watch": "Da Vedere", "watching": "In Corso", "completed": "Completata",
                      "on_hold": "In Pausa", "dropped": "Abbandonata"}
BADGE_CLASS = {"plan_to_watch": "status-watchlist", "watching": "status-watching",
               "watched": "status-completed", "completed": "status-completed", "on_hold": "status-watchlist",
               "dropped": "status-watchlist"}


def render_stars(rating):
    rating = int(rating or 0)
    return "★" * rating + "☆" * (5 - rating)


# =====================================================================
# STATISTICHE (SIDEBAR)
# =====================================================================
conn = get_db_connection()

movies_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
shows_count = conn.execute("SELECT COUNT(*) FROM shows").fetchone()[0]
total_media = movies_count + shows_count

completed_movies = conn.execute("SELECT COUNT(*) FROM movies WHERE watch_status='watched'").fetchone()[0]
completed_shows = conn.execute("SELECT COUNT(*) FROM shows WHERE watch_status='completed'").fetchone()[0]
completed_count = completed_movies + completed_shows

watching_count = conn.execute("SELECT COUNT(*) FROM shows WHERE watch_status='watching'").fetchone()[0]
total_episodes_watched = conn.execute("SELECT COUNT(*) FROM watch_history WHERE content_type = 'episode'").fetchone()[0]

st.sidebar.markdown("<h2 style='text-align:center;'>🎬 MyTVTime</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

with st.sidebar.expander("🔐 Configurazione API"):
    tmdb_key_input = st.text_input(
        "TMDB API Key (v3)",
        value=st.session_state.get("tmdb_api_key", ""),
        type="password"
    )
    if tmdb_key_input:
        st.session_state["tmdb_api_key"] = tmdb_key_input

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Le tue Statistiche")
col_side1, col_side2 = st.sidebar.columns(2)
with col_side1:
    st.metric("Contenuti Totali", total_media)
    st.metric("In Corso", watching_count)
with col_side2:
    st.metric("Episodi Visti", total_episodes_watched)
    st.metric("Completati", completed_count)

st.sidebar.markdown("---")
st.sidebar.info("💡 Il database locale vive in `database/mytvtime.db`. I tuoi dati restano privati sul tuo computer.")


# =====================================================================
# DIALOG: GESTIONE FILM
# =====================================================================
@st.dialog("Gestisci Film")
def open_manage_movie_dialog(movie_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if not item:
        st.error("Contenuto non trovato.")
        conn.close()
        return

    st.markdown(f"### {item['title']}")
    if item["overview"]:
        st.caption(item["overview"][:300] + ("..." if len(item["overview"]) > 300 else ""))

    new_status = st.selectbox(
        "Stato di Visione",
        list(MOVIE_STATUS_LABELS.keys()),
        format_func=lambda x: MOVIE_STATUS_LABELS[x],
        index=list(MOVIE_STATUS_LABELS.keys()).index(item["watch_status"])
    )

    st.write("**La tua Valutazione**")
    star_options = {0: "❌ Senza voto", 1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
    current_rating = int(item["rating"]) if item["rating"] in star_options else 0
    chosen_label = st.select_slider(
        "Seleziona il voto",
        options=list(star_options.values()),
        value=star_options[current_rating],
        key=f"movie_slider_{movie_id}"
    )
    new_rating = [k for k, v in star_options.items() if v == chosen_label][0]

    st.write("---")
    col_sav, col_del = st.columns(2)
    with col_sav:
        if st.button("💾 Salva Modifiche", type="primary", key=f"save_movie_{movie_id}"):
            conn.execute(
                "UPDATE movies SET watch_status = ?, rating = ? WHERE id = ?",
                (new_status, new_rating, movie_id)
            )
            if new_status == "watched":
                exists = conn.execute("SELECT id FROM watch_history WHERE content_type='movie' AND movie_id=?",
                                      (movie_id,)).fetchone()
                if not exists:
                    today = datetime.now().strftime("%Y-%m-%d")
                    conn.execute(
                        "INSERT INTO watch_history (content_type, movie_id, watched_at) VALUES ('movie', ?, ?)",
                        (movie_id, today))
            else:
                conn.execute("DELETE FROM watch_history WHERE content_type='movie' AND movie_id=?", (movie_id,))

            conn.commit()
            conn.close()
            st.toast("Film aggiornato!")
            st.rerun()

    with col_del:
        confirm = st.checkbox("Conferma eliminazione", key=f"confirm_del_movie_{movie_id}")
        if st.button("🗑️ Elimina", type="secondary", key=f"del_movie_{movie_id}", disabled=not confirm):
            conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            conn.commit()
            conn.close()
            st.success("Film eliminato.")
            st.rerun()

    conn.close()


# =====================================================================
# DIALOG: GESTIONE SERIE TV
# =====================================================================
@st.dialog("Gestisci Serie TV")
def open_manage_show_dialog(show_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if not item:
        st.error("Contenuto non trovato.")
        conn.close()
        return

    st.markdown(f"### {item['title']}")
    if item["overview"]:
        st.caption(item["overview"][:300] + ("..." if len(item["overview"]) > 300 else ""))

    eps_per_season = json.loads(item["episode_per_season"] or "{}")

    if not eps_per_season:
        api_key = st.session_state.get("tmdb_api_key", "")
        if item["tmdb_id"] and api_key:
            if st.button("📡 Carica stagioni ed episodi da TMDB", key=f"load_seasons_{show_id}"):
                with st.spinner("Scaricamento dati da TMDB in corso..."):
                    details = query_tmdb_tv_details(api_key, item["tmdb_id"])
                    if details:
                        eps_map = build_episodes_per_season(details)
                        total_eps = sum(eps_map.values())

                        conn.execute(
                            "UPDATE shows SET episode_per_season = ?, total_episodes = ? WHERE id = ?",
                            (json.dumps(eps_map), total_eps, show_id)
                        )
                        conn.commit()

                        st.toast("Dati scaricati con successo!")
                        eps_per_season = eps_map
                    else:
                        st.error("Impossibile recuperare i dati da TMDB.")
        else:
            st.warning("Imposta la chiave API TMDB nella sidebar per tracciare stagioni ed episodi.")

    # Allineamento con tabella episodes e watch_history polimorfica
    watched_rows = conn.execute(
        """
        SELECT e.season_number, e.episode_number 
        FROM watch_history h
        JOIN episodes e ON h.episode_id = e.id
        WHERE e.show_id = ? AND h.content_type = 'episode'
        """,
        (show_id,)
    ).fetchall()
    watched_set = {(r["season_number"], r["episode_number"]) for r in watched_rows}
    total_eps = sum(eps_per_season.values()) if eps_per_season else 0

    if total_eps > 0:
        progress = len(watched_set) / total_eps
        numero_visti = len(watched_set)
        st.progress(min(progress, 1.0), text=f"{numero_visti} / {total_eps} episodi visti")

    new_status = st.selectbox(
        "Stato di Visione",
        list(SHOW_STATUS_LABELS.keys()),
        format_func=lambda x: SHOW_STATUS_LABELS[x],
        index=list(SHOW_STATUS_LABELS.keys()).index(item["watch_status"])
    )

    st.write("**La tua Valutazione**")
    star_options = {0: "❌ Nessun voto", 1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
    current_rating = int(item["rating"]) if item["rating"] in star_options else 0

    chosen_label = st.select_slider(
        "Seleziona il voto per la serie",
        options=list(star_options.values()),
        value=star_options[current_rating],
        key=f"show_slider_{show_id}"
    )
    new_rating = [k for k, v in star_options.items() if v == chosen_label][0]

    st.write("---")

    if eps_per_season:
        st.write("##### 📺 Prossimo episodio")
        next_ep = None
        for season_str in sorted(eps_per_season.keys(), key=int):
            season_num = int(season_str)
            for ep_num in range(1, eps_per_season[season_str] + 1):
                if (season_num, ep_num) not in watched_set:
                    next_ep = (season_num, ep_num)
                    break
            if next_ep:
                break

        if next_ep:
            col_next1, col_next2 = st.columns([3, 1])
            with col_next1:
                st.write(f"Stagione {next_ep[0]}, Episodio {next_ep[1]}")
            with col_next2:
                if st.button("✅ Segna visto", key=f"next_ep_{show_id}"):
                    next_season_int = int(next_ep[0])
                    next_episode_int = int(next_ep[1])
                    today = datetime.now().strftime("%Y-%m-%d")

                    ep_id = get_or_create_episode_id(conn, show_id, next_season_int, next_episode_int)
                    conn.execute(
                        """
                        INSERT INTO watch_history (content_type, episode_id, watched_at) 
                        VALUES ('episode', ?, ?)
                        """,
                        (ep_id, today)
                    )
                    conn.commit()
                    st.toast("Episodio segnato come visto!")
                    st.rerun()
        else:
            st.success("🎉 Hai visto tutti gli episodi disponibili!")

        st.write("---")
        st.write("##### 🗂️ Gestione per Stagione")

        @st.fragment
        def render_season_management(season_num, n_episodes, show_id, watched_set):
            state_key = f"watched_set_{show_id}_{season_num}"
            if state_key not in st.session_state:
                st.session_state[state_key] = watched_set

            current_watched = st.session_state[state_key]
            watched_in_season = sum(1 for s, e in current_watched if s == season_num)

            with st.expander(f"Stagione {season_num} — {watched_in_season}/{n_episodes} visti"):
                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("✅ Segna tutta la stagione", key=f"season_all_{show_id}_{season_num}"):
                        frag_conn = get_db_connection()
                        today = datetime.now().strftime("%Y-%m-%d")
                        for ep_num in range(1, n_episodes + 1):
                            if (season_num, ep_num) not in current_watched:
                                ep_id = get_or_create_episode_id(frag_conn, show_id, season_num, ep_num)
                                frag_conn.execute(
                                    """
                                    INSERT INTO watch_history (content_type, episode_id, watched_at) 
                                    VALUES ('episode', ?, ?)
                                    """,
                                    (ep_id, today)
                                )
                                current_watched.add((season_num, ep_num))
                        frag_conn.execute("UPDATE shows SET watch_status = 'watching' WHERE id = ?", (show_id,))
                        frag_conn.commit()
                        frag_conn.close()

                        st.session_state[state_key] = current_watched
                        st.toast(f"Stagione {season_num} segnata come vista!")

                with col_b:
                    if st.button("↩️ Azzera stagione", key=f"season_clear_{show_id}_{season_num}"):
                        frag_conn = get_db_connection()
                        frag_conn.execute(
                            """
                            DELETE FROM watch_history 
                            WHERE content_type = 'episode' AND episode_id IN (
                                SELECT id FROM episodes WHERE show_id = ? AND season_number = ?
                            )
                            """,
                            (show_id, season_num)
                        )
                        frag_conn.commit()
                        frag_conn.close()

                        for ep_num in range(1, n_episodes + 1):
                            current_watched.discard((season_num, ep_num))

                        st.session_state[state_key] = current_watched
                        st.toast(f"Cronologia Stagione {season_num} azzerata!")

                with st.form(key=f"season_form_{show_id}_{season_num}"):
                    checks = {}
                    n_cols = 6
                    ep_range = list(range(1, n_episodes + 1))
                    for row_start in range(0, len(ep_range), n_cols):
                        row_cols = st.columns(n_cols)
                        for idx, ep_num in enumerate(ep_range[row_start:row_start + n_cols]):
                            already = (season_num, ep_num) in current_watched
                            checks[ep_num] = row_cols[idx].checkbox(
                                f"E{ep_num}", value=already, key=f"ep_{show_id}_{season_num}_{ep_num}"
                            )

                    if st.form_submit_button("💾 Salva episodi di questa stagione"):
                        frag_conn = get_db_connection()
                        today = datetime.now().strftime("%Y-%m-%d")
                        for ep_num, is_checked in checks.items():
                            originally_checked = (season_num, ep_num) in current_watched
                            if is_checked and not originally_checked:
                                ep_id = get_or_create_episode_id(frag_conn, show_id, season_num, ep_num)
                                frag_conn.execute(
                                    """
                                    INSERT INTO watch_history (content_type, episode_id, watched_at) 
                                    VALUES ('episode', ?, ?)
                                    """,
                                    (ep_id, today)
                                )
                                current_watched.add((season_num, ep_num))
                            elif not is_checked and originally_checked:
                                frag_conn.execute(
                                    """
                                    DELETE FROM watch_history 
                                    WHERE content_type = 'episode' AND episode_id IN (
                                        SELECT id FROM episodes WHERE show_id = ? AND season_number = ? AND episode_number = ?
                                    )
                                    """,
                                    (show_id, season_num, ep_num)
                                )
                                current_watched.discard((season_num, ep_num))
                        frag_conn.commit()
                        frag_conn.close()

                        st.session_state[state_key] = current_watched
                        st.toast(f"Stagione {season_num} aggiornata!")

        for season_str in sorted(eps_per_season.keys(), key=int):
            season_num = int(season_str)
            n_episodes = eps_per_season[season_str]
            render_season_management(season_num, n_episodes, show_id, watched_set)

    st.write("---")
    col_sav, col_del = st.columns(2)
    with col_sav:
        if st.button("💾 Salva Stato e Voto", type="primary", key=f"save_show_{show_id}"):
            final_status = new_status
            if total_eps > 0:
                if len(watched_set) == 0:
                    final_status = "plan_to_watch" if new_status == "plan_to_watch" else new_status
                elif len(watched_set) >= total_eps:
                    final_status = "completed"
                elif len(watched_set) > 0:
                    final_status = "watching" if new_status == "plan_to_watch" else new_status

            conn.execute(
                "UPDATE shows SET watch_status = ?, rating = ? WHERE id = ?",
                (final_status, new_rating, show_id)
            )
            conn.commit()
            conn.close()
            st.toast("Serie TV aggiornata!")
            st.rerun()

    with col_del:
        confirm = st.checkbox("Conferma eliminazione", key=f"confirm_del_show_{show_id}")
        if st.button("🗑️ Elimina", type="secondary", key=f"del_show_{show_id}", disabled=not confirm):
            conn.execute("DELETE FROM shows WHERE id = ?", (show_id,))
            conn.commit()
            conn.close()
            st.success("Serie TV eliminata dalla libreria.")
            st.rerun()

    conn.close()


# =====================================================================
# INTERFACCIA PRINCIPALE
# =====================================================================
st.title("🎬 MyTVTime")
st.write("La tua dashboard personale per serie TV e film.")

tab_home, tab_search, tab_analytics = st.tabs(["🏠 La Mia Libreria", "🔍 Cerca & Aggiungi", "📈 Analisi Dati"])

# ---------------------------------------------------------------------
# TAB 1: LA MIA LIBRERIA
# ---------------------------------------------------------------------
with tab_home:
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1.3])
    with filter_col1:
        search_filter = st.text_input("🔎 Filtra per titolo...", key="library_search")
    with filter_col2:
        type_filter = st.selectbox("Tipo", ["Tutti", "Film", "Serie TV"])
    with filter_col3:
        status_filter = st.selectbox("Stato", ["Tutti", "Da Vedere", "In Corso", "Completati"])
    with filter_col4:
        sort_option = st.selectbox(
            "Ordina per",
            ["Titolo (A-Z)", "Titolo (Z-A)", "Voto (alto-basso)", "Voto (basso-alto)",
             "Aggiunti di recente", "Data di uscita (recenti prima)"]
        )

    sort_map = {
        "Titolo (A-Z)": "title ASC",
        "Titolo (Z-A)": "title DESC",
        "Voto (alto-basso)": "rating DESC, title ASC",
        "Voto (basso-alto)": "rating ASC, title ASC",
        "Aggiunti di recente": "added_at DESC",
        "Data di uscita (recenti prima)": "date_field DESC",
    }
    order_clause = sort_map[sort_option]

    # Sostituzione di added_at con created_at e recupero dinamico di watched_at per i film
    movie_query = """
        SELECT id, title, 'movie' as type, watch_status as status, rating, poster_path,
               release_date as date_field, created_at as added_at, 
               (SELECT MAX(watched_at) FROM watch_history WHERE movie_id = movies.id) as watched_at, 
               NULL as episode_per_season
        FROM movies WHERE 1=1
    """

    show_query = """
        SELECT id, title, 'show' as type, watch_status as status, rating, poster_path,
               first_air_date as date_field, created_at as added_at, 
               created_at as watched_at, episode_per_season
        FROM shows WHERE 1=1
    """
    movie_params, show_params = [], []

    if search_filter:
        movie_query += " AND title LIKE ?"
        show_query += " AND title LIKE ?"
        movie_params.append(f"%{search_filter}%")
        show_params.append(f"%{search_filter}%")

    if status_filter == "Da Vedere":
        movie_query += " AND watch_status = 'plan_to_watch'"
        show_query += " AND watch_status = 'plan_to_watch'"
    elif status_filter == "In Corso":
        movie_query += " AND 1=0"
        show_query += " AND watch_status = 'watching'"
    elif status_filter == "Completati":
        movie_query += " AND watch_status = 'watched'"
        show_query += " AND watch_status = 'completed'"

    query_parts, params = [], []
    if type_filter in ("Tutti", "Film"):
        query_parts.append(movie_query)
        params.extend(movie_params)
    if type_filter in ("Tutti", "Serie TV"):
        query_parts.append(show_query)
        params.extend(show_params)

    library_items = []
    if query_parts:
        full_query = f"SELECT * FROM ({' UNION ALL '.join(query_parts)}) ORDER BY {order_clause}"
        library_items = conn.execute(full_query, params).fetchall()

    if not library_items:
        st.info("Nessun contenuto trovato nella libreria con i filtri selezionati.")
    else:
        columns_per_row = 5
        for i in range(0, len(library_items), columns_per_row):
            cols = st.columns(columns_per_row)
            for j in range(columns_per_row):
                if i + j >= len(library_items):
                    continue
                item = library_items[i + j]
                with cols[j]:
                    labels = MOVIE_STATUS_LABELS if item["type"] == "movie" else SHOW_STATUS_LABELS
                    badge_label = labels.get(item["status"], item["status"])
                    badge_class = BADGE_CLASS.get(item["status"], "status-watchlist")
                    icon = "🎬" if item["type"] == "movie" else "📺"

                    stars_display = render_stars(item['rating']) if item['rating'] > 0 else "Non valutato"

                    with st.container():
                        st.markdown(f"""
                        <div class="media-card">
                            {poster_html(item['poster_path'], icon)}
                            <div class="media-title">{item['title']}</div>
                            <div class="stars-row">{stars_display}</div>
                            <span class="status-badge {badge_class}">{badge_label}</span>
                        </div>
                        """, unsafe_allow_html=True)

                        # Il testo viene impostato a "" per nasconderlo visivamente
                        clicked = st.button(
                            "",
                            key=f"card_click_{item['type']}_{item['id']}",
                            help=f"Apri {item['title']}"
                        )
                        if clicked:
                            if item["type"] == "movie":
                                open_manage_movie_dialog(item["id"])
                            else:
                                open_manage_show_dialog(item["id"])

# ---------------------------------------------------------------------
# TAB 2: CERCA & AGGIUNGI (TMDB ONLINE)
# ---------------------------------------------------------------------
with tab_search:
    st.header("🔍 Cerca nuovi titoli su TMDB")

    api_key = st.session_state.get("tmdb_api_key", "")

    if not api_key:
        st.warning(
            "⚠️ Inserisci la chiave TMDB_API_KEY nella sidebar (o nel file .env) per sbloccare la ricerca online.")
    else:
        search_query = st.text_input("Scrivi il nome del film o della serie...")
        search_type = st.radio("Cosa stai cercando?", ["Film", "Serie TV"], horizontal=True)

        if search_query:
            media_type = "movie" if search_type == "Film" else "tv"
            results = query_tmdb_search(api_key, search_query, media_type)

            if not results:
                st.error("Nessun risultato trovato. Verifica la stringa cercata o la validità della chiave API.")
            else:
                st.write(f"### Risultati Trovati ({len(results)}):")

                for i in range(0, len(results), 4):
                    cols = st.columns(4)
                    for j in range(4):
                        if i + j >= len(results):
                            continue
                        res = results[i + j]
                        title = res.get("title") if media_type == "movie" else res.get("name")
                        release = res.get("release_date") if media_type == "movie" else res.get("first_air_date")
                        poster = res.get("poster_path", "")
                        overview = res.get("overview", "Nessuna trama disponibile.")
                        tmdb_id = res.get("id")

                        with cols[j]:
                            st.markdown(poster_html(poster, "🎬" if media_type == "movie" else "📺"),
                                        unsafe_allow_html=True)
                            st.markdown(f"**{title}**")
                            if release:
                                st.caption(f"Uscita: {release[:4]}")

                            if st.button("➕ Aggiungi alla Libreria", key=f"add_tmdb_{media_type}_{tmdb_id}"):
                                existing_show = conn.execute(
                                    "SELECT id FROM shows WHERE tmdb_id = ?", (str(tmdb_id),)).fetchone()
                                existing_movie = conn.execute(
                                    "SELECT id FROM movies WHERE tmdb_id = ?", (str(tmdb_id),)).fetchone()

                                if existing_show or existing_movie:
                                    st.warning("Questo contenuto è già presente nella tua libreria!")
                                elif media_type == "movie":
                                    conn.execute("""
                                        INSERT INTO movies (tmdb_id, title, watch_status, poster_path, overview, release_date)
                                        VALUES (?, ?, 'plan_to_watch', ?, ?, ?)
                                    """, (str(tmdb_id), title, poster, overview, release))
                                    conn.commit()
                                    st.success(f"'{title}' aggiunto correttamente alla tua libreria!")
                                    st.rerun()
                                else:
                                    tv_details = query_tmdb_tv_details(api_key, tmdb_id)
                                    eps_map = build_episodes_per_season(tv_details) if tv_details else {}
                                    total_eps = sum(eps_map.values())
                                    conn.execute("""
                                        INSERT INTO shows (tmdb_id, title, watch_status, poster_path, overview,
                                                           first_air_date, episode_per_season, total_episodes)
                                        VALUES (?, ?, 'plan_to_watch', ?, ?, ?, ?, ?)
                                    """, (str(tmdb_id), title, poster, overview, release,
                                          json.dumps(eps_map), total_eps))
                                    conn.commit()
                                    st.success(f"'{title}' aggiunto correttamente alla tua libreria!")
                                    st.rerun()

# ---------------------------------------------------------------------
# TAB 3: GRAFICI E ANALISI
# ---------------------------------------------------------------------
with tab_analytics:
    st.header("📈 Le tue Statistiche di Visione")

    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        st.subheader("Distribuzione Contenuti")
        df_distribution = pd.DataFrame({
            "Tipo": ["Film 🎬", "Serie TV 📺"],
            "Conteggio": [movies_count, shows_count]
        })
        if movies_count + shows_count > 0:
            st.bar_chart(df_distribution.set_index("Tipo"))
        else:
            st.info("Nessun dato disponibile.")

    with col_graph2:
        st.subheader("I tuoi Voti")
        df_ratings_m = pd.read_sql_query(
            "SELECT rating FROM movies WHERE rating > 0", conn)
        df_ratings_s = pd.read_sql_query(
            "SELECT rating FROM shows WHERE rating > 0", conn)

        if not (df_ratings_m.empty and df_ratings_s.empty):
            df_ratings = pd.concat([df_ratings_m, df_ratings_s])
            counts = df_ratings["rating"].value_counts().sort_index()
            st.bar_chart(counts)
        else:
            st.info("Assegna qualche stella per generare il grafico dei voti.")

    st.write("---")
    st.subheader("🏆 Top Valutazioni")
    top_movies = conn.execute(
        "SELECT title, rating FROM movies WHERE rating > 0 ORDER BY rating DESC, title ASC LIMIT 5").fetchall()
    top_shows = conn.execute(
        "SELECT title, rating FROM shows WHERE rating > 0 ORDER BY rating DESC, title ASC LIMIT 5").fetchall()

    col_top1, col_top2 = st.columns(2)
    with col_top1:
        st.write("**🎬 Film**")
        if top_movies:
            for m in top_movies:
                st.write(f"{render_stars(m['rating'])} — {m['title']}")
        else:
            st.caption("Nessun film valutato ancora.")
    with col_top2:
        st.write("**📺 Serie TV**")
        if top_shows:
            for s in top_shows:
                st.write(f"{render_stars(s['rating'])} — {s['title']}")
        else:
            st.caption("Nessuna serie valutata ancora.")

    st.write("---")
    st.subheader("🛠️ Manutenzione Archivio")
    if st.button("🔄 Sincronizza Copertine Mancanti"):
        api_key = st.session_state.get("tmdb_api_key", "")
        if not api_key:
            st.error("Inserisci prima la chiave API nella barra laterale!")
        else:
            # Estendiamo la query per intercettare anche eventuali testi "None" o "null" parassiti
            query_movies = """
                SELECT id, tmdb_id FROM movies 
                WHERE poster_path IS NULL 
                   OR poster_path = '' 
                   OR poster_path = 'None' 
                   OR poster_path = 'null'
            """
            query_shows = """
                SELECT id, tmdb_id FROM shows 
                WHERE poster_path IS NULL 
                   OR poster_path = '' 
                   OR poster_path = 'None' 
                   OR poster_path = 'null'
            """

            # Forza il recupero come dizionario se non è impostato a monte
            try:
                conn.row_factory = sqlite3.Row
            except Exception:
                pass

            missing_movies = conn.execute(query_movies).fetchall()
            missing_shows = conn.execute(query_shows).fetchall()

            updated_count = 0

            # --- CICLO FILM ---
            for item in missing_movies:
                if item["tmdb_id"]:
                    url = f"https://api.themoviedb.org/3/movie/{item['tmdb_id']}?api_key={api_key}&language=it-IT"
                    try:
                        res = requests.get(url, timeout=6)
                        if res.status_code == 200:
                            poster_path = res.json().get("poster_path")
                            if poster_path:
                                conn.execute("UPDATE movies SET poster_path = ? WHERE id = ?",
                                             (poster_path, item["id"]))
                                updated_count += 1
                        elif res.status_code == 401:
                            st.error("Chiave API TMDB non valida!")
                            st.stop()
                    except Exception as e:
                        st.warning(f"Errore durante il recupero del film ID {item['id']}: {e}")
                        continue

            # --- CICLO SERIE TV ---
            for item in missing_shows:
                if item["tmdb_id"]:
                    url = f"https://api.themoviedb.org/3/tv/{item['tmdb_id']}?api_key={api_key}&language=it-IT"
                    try:
                        res = requests.get(url, timeout=6)
                        if res.status_code == 200:
                            poster_path = res.json().get("poster_path")
                            if poster_path:
                                conn.execute("UPDATE shows SET poster_path = ? WHERE id = ?",
                                             (poster_path, item["id"]))
                                updated_count += 1
                    except Exception as e:
                        st.warning(f"Errore durante il recupero della serie ID {item['id']}: {e}")
                        continue

            # --- VERIFICA FINALE ---
            if updated_count > 0:
                conn.commit()
                st.success(f"🎉 Aggiornate {updated_count} copertine!")
                st.rerun()
            else:
                st.info("Nessuna nuova copertina trovata. Verifica che i film nel DB abbiano un TMDB ID valido.")

    st.sidebar.markdown("---")
    st.subheader("📅 Ultime Attività")

    # Query riadattata per estrarre la cronologia unificata dallo schema reale
    recent_history = conn.execute("""
                SELECT watched_at, content_type, title, season_number, episode_number FROM (
                    SELECT
                        h.watched_at as watched_at,
                        'episode' as content_type,
                        s.title as title,
                        e.season_number as season_number,
                        e.episode_number as episode_number
                    FROM watch_history h
                    JOIN episodes e ON h.episode_id = e.id
                    JOIN shows s ON e.show_id = s.id
                    WHERE h.content_type = 'episode'

                    UNION ALL

                    SELECT
                        h.watched_at as watched_at,
                        'movie' as content_type,
                        m.title as title,
                        NULL as season_number,
                        NULL as episode_number
                    FROM watch_history h
                    JOIN movies m ON h.movie_id = m.id
                    WHERE h.content_type = 'movie'
                )
                ORDER BY watched_at DESC
                LIMIT 10
            """).fetchall()

    if recent_history:
        history_table = []
        for r in recent_history:
            info = f"Stagione {r['season_number']}, Episodio {r['episode_number']}" if r[
                                                                                           'content_type'] == 'episode' else "Visto completo"
            history_table.append({
                "Titolo": r["title"] if r["title"] else "Titolo Sconosciuto",
                "Dettaglio": info,
                "Data di Visione": r["watched_at"]
            })
        st.table(pd.DataFrame(history_table))
    else:
        st.info("Nessun contenuto guardato di recente.")

conn.close()