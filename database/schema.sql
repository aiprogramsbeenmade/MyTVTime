-- =====================================================================
-- MyTVTime - Schema SQLite
-- Fase 1: struttura dati per contenuti, stagioni/episodi e storico visioni
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- SERIE TV
-- Una riga per ogni serie tracciata. I metadati (poster, overview, ecc.)
-- vengono arricchiti in un secondo momento tramite le API di TMDB;
-- in fase di import potrebbero quindi essere NULL.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shows (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id             INTEGER UNIQUE,               -- ID TMDB (NULL finché non arricchito)
    tvtime_id           INTEGER UNIQUE,               -- ID TheTVDB usato da TV Time/Refract, chiave di matching in import
    imdb_id             TEXT UNIQUE,                   -- ID IMDB (es. 'tt0903747'), utile per il matching TMDB "find by external id"
    title               TEXT NOT NULL,
    original_title      TEXT,
    overview            TEXT,
    poster_path         TEXT,
    first_air_date      TEXT,                         -- formato ISO YYYY-MM-DD
    total_seasons       INTEGER,
    total_episodes      INTEGER,
    episode_per_season  TEXT,
    watch_status        TEXT NOT NULL DEFAULT 'watching'
                         CHECK (watch_status IN ('watching','completed','on_hold','dropped','plan_to_watch')),
    is_favorite         INTEGER NOT NULL DEFAULT 0,   -- 0/1 boolean
    rating              REAL DEFAULT 0,
    tmdb_last_synced_at TEXT,                         -- timestamp ultimo arricchimento TMDB
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- STAGIONI
-- ---------------------------------------------------------------------
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

-- ---------------------------------------------------------------------
-- EPISODI
-- Anagrafica dell'episodio (non è ancora lo storico delle visioni:
-- serve a sapere QUALI episodi esistono, indipendentemente dal fatto
-- che tu li abbia visti o meno).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS episodes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id         INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    season_number   INTEGER NOT NULL,
    episode_number  INTEGER NOT NULL,
    tmdb_episode_id INTEGER,
    tvdb_id         INTEGER,                         -- ID TheTVDB dell'episodio, utile per il matching TMDB futuro
    is_special      INTEGER NOT NULL DEFAULT 0,      -- 0/1: alcuni provider numerano gli special con lo stesso (stagione, numero) di un episodio normale
    title           TEXT,
    air_date        TEXT,
    overview        TEXT,
    UNIQUE (show_id, season_number, episode_number, is_special)
);

-- ---------------------------------------------------------------------
-- FILM
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id             INTEGER UNIQUE,
    tvtime_id           INTEGER UNIQUE,               -- ID TheTVDB usato da TV Time/Refract per i film
    imdb_id             TEXT UNIQUE,
    title               TEXT NOT NULL,
    original_title      TEXT,
    overview            TEXT,
    poster_path         TEXT,
    release_date        TEXT,
    runtime_minutes     INTEGER,
    watch_status        TEXT NOT NULL DEFAULT 'watched'
                         CHECK (watch_status IN ('watched','plan_to_watch','dropped')),
    is_favorite         INTEGER NOT NULL DEFAULT 0,
    rating              REAL DEFAULT 0,
    tmdb_last_synced_at TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- STORICO VISIONI
-- Cuore del tracking: una riga per OGNI visione (anche i rewatch).
-- Fa riferimento a un episodio OPPURE a un film, mai entrambi:
-- il CHECK in fondo garantisce la coerenza (discriminatore content_type).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS watch_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type    TEXT NOT NULL CHECK (content_type IN ('episode','movie')),
    episode_id      INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
    movie_id        INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    watched_at      TEXT NOT NULL,      -- data/ora visione, ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)
    play_count      INTEGER NOT NULL DEFAULT 1,  -- numero di visioni cumulate registrate da TV Time a questa data (rewatch inclusi)
    rating          REAL,               -- voto personale opzionale (es. 0-10)
    notes           TEXT,
    source          TEXT DEFAULT 'tvtime_import',  -- 'tvtime_import' | 'manual' | 'app'
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (
        (content_type = 'episode' AND episode_id IS NOT NULL AND movie_id IS NULL)
        OR
        (content_type = 'movie'   AND movie_id   IS NOT NULL AND episode_id IS NULL)
    )
);

-- ---------------------------------------------------------------------
-- INDICI
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_seasons_show          ON seasons(show_id);
CREATE INDEX IF NOT EXISTS idx_episodes_show         ON episodes(show_id);
CREATE INDEX IF NOT EXISTS idx_episodes_show_season  ON episodes(show_id, season_number);
CREATE INDEX IF NOT EXISTS idx_watch_history_episode ON watch_history(episode_id);
CREATE INDEX IF NOT EXISTS idx_watch_history_movie   ON watch_history(movie_id);
CREATE INDEX IF NOT EXISTS idx_watch_history_date    ON watch_history(watched_at);
CREATE INDEX IF NOT EXISTS idx_shows_status          ON shows(watch_status);
CREATE INDEX IF NOT EXISTS idx_movies_status         ON movies(watch_status);

-- ---------------------------------------------------------------------
-- TRIGGER: aggiornamento automatico di updated_at
-- ---------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_shows_updated_at
AFTER UPDATE ON shows
FOR EACH ROW
BEGIN
    UPDATE shows SET updated_at = datetime('now') WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_movies_updated_at
AFTER UPDATE ON movies
FOR EACH ROW
BEGIN
    UPDATE movies SET updated_at = datetime('now') WHERE id = OLD.id;
END;
