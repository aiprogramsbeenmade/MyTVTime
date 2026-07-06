"""
init_db.py
Crea (o ricrea) il database SQLite MyTVTime applicando schema.sql.

Uso:
    python scripts/init_db.py
    python scripts/init_db.py --reset   # elimina il DB esistente e lo ricrea da zero
"""

import argparse
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
DB_PATH = BASE_DIR / "database" / "mytvtime.db"


def init_db(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Database esistente rimosso: {DB_PATH}")

    if not SCHEMA_PATH.exists():
        print(f"ERRORE: schema non trovato in {SCHEMA_PATH}")
        sys.exit(1)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database inizializzato correttamente in: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inizializza il database MyTVTime")
    parser.add_argument("--reset", action="store_true", help="Elimina e ricrea il database")
    args = parser.parse_args()

    init_db(reset=args.reset)
