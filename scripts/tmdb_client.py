"""
tmdb_client.py
Wrapper minimale attorno alle API di TMDB (The Movie Database) v3.

Autenticazione: imposta UNA delle due variabili d'ambiente
    - TMDB_API_KEY       (auth v3 "API Key", stringa breve)
    - TMDB_ACCESS_TOKEN  (auth v4 "Access Token", stringa lunga tipo JWT)

Il client rileva automaticamente quale delle due e' impostata.
Per ottenerle: https://www.themoviedb.org/settings/api (account gratuito).

Come impostarle (Linux/macOS):
    export TMDB_API_KEY="la-tua-chiave"
Come impostarle (Windows PowerShell):
    $env:TMDB_API_KEY = "la-tua-chiave"

Puoi anche metterla in un file .env nella root del progetto (vedi .env.example)
e lo script enrich_metadata.py la caricherà automaticamente, senza bisogno di
librerie esterne.
"""

import os
import time
from pathlib import Path

import requests

BASE_URL = "https://api.themoviedb.org/3"
DEFAULT_LANGUAGE = "it-IT"   # metadati in italiano quando disponibili, TMDB fa fallback automatico all'inglese
MAX_RETRIES = 5
REQUEST_TIMEOUT = 15


class TMDBError(Exception):
    """Errore generico nelle chiamate TMDB (dopo aver esaurito i retry)."""
    pass


class TMDBAuthError(TMDBError):
    """Nessuna credenziale trovata o credenziale non valida (401)."""
    pass


class TMDBNotFoundError(TMDBError):
    """Risorsa non trovata (404) - es. un tmdb_id non piu' valido."""
    pass


def load_dotenv_if_present(env_path: Path = None):
    """Carica variabili da un file .env senza dipendenze esterne (python-dotenv).
    Non sovrascrive variabili d'ambiente già impostate a livello di sistema."""
    env_path = env_path or (Path(__file__).resolve().parent.parent / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class TMDBClient:
    def __init__(self, api_key: str = None, access_token: str = None, language: str = DEFAULT_LANGUAGE):
        self.language = language
        self.session = requests.Session()

        self.api_key = api_key or os.environ.get("TMDB_API_KEY")
        self.access_token = access_token or os.environ.get("TMDB_ACCESS_TOKEN")

        if self.access_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "accept": "application/json",
            })
            self.auth_mode = "v4_bearer"
        elif self.api_key:
            self.auth_mode = "v3_query_param"
        else:
            raise TMDBAuthError(
                "Nessuna credenziale TMDB trovata. Imposta TMDB_API_KEY o TMDB_ACCESS_TOKEN "
                "(variabile d'ambiente o file .env nella root del progetto)."
            )

    def _get(self, endpoint: str, params: dict = None) -> dict:
        params = dict(params or {})
        params.setdefault("language", self.language)
        if self.auth_mode == "v3_query_param":
            params["api_key"] = self.api_key

        url = f"{BASE_URL}{endpoint}"
        last_exception = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as e:
                last_exception = e
                time.sleep(min(2 ** attempt, 20))
                continue

            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 401:
                raise TMDBAuthError("Credenziale TMDB non valida (401). Controlla TMDB_API_KEY/TMDB_ACCESS_TOKEN.")
            if resp.status_code == 404:
                raise TMDBNotFoundError(f"Risorsa non trovata: {endpoint}")
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 1))
                time.sleep(retry_after)
                continue
            if 500 <= resp.status_code < 600:
                time.sleep(min(2 ** attempt, 20))
                continue

            raise TMDBError(f"Errore HTTP {resp.status_code} su {endpoint}: {resp.text[:200]}")

        raise TMDBError(f"Superato il numero massimo di retry ({MAX_RETRIES}) su {endpoint}: {last_exception}")

    # -----------------------------------------------------------------
    # RICERCA PER ID ESTERNO (il modo piu' affidabile per il matching)
    # -----------------------------------------------------------------
    def find_by_external_id(self, external_id: str, source: str) -> dict:
        """source: 'imdb_id' | 'tvdb_id'
        Ritorna il dict completo con chiavi 'movie_results' e 'tv_results'."""
        return self._get(f"/find/{external_id}", params={"external_source": source})

    # -----------------------------------------------------------------
    # RICERCA TESTUALE (fallback quando manca l'ID esterno o non da' match)
    # -----------------------------------------------------------------
    def search_tv(self, query: str) -> list:
        data = self._get("/search/tv", params={"query": query})
        return data.get("results", [])

    def search_movie(self, query: str, year: int = None) -> list:
        params = {"query": query}
        if year:
            params["year"] = year
        data = self._get("/search/movie", params=params)
        return data.get("results", [])

    # -----------------------------------------------------------------
    # DETTAGLI
    # -----------------------------------------------------------------
    def get_tv_details(self, tmdb_id: int) -> dict:
        return self._get(f"/tv/{tmdb_id}")

    def get_season_details(self, tmdb_id: int, season_number: int) -> dict:
        return self._get(f"/tv/{tmdb_id}/season/{season_number}")

    def get_movie_details(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}")
