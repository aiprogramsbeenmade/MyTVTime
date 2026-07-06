"""
inspect_export.py
Script TEMPORANEO (solo per Fase 1, punto 2) per capire la struttura
del file esportato con l'estensione Refract, prima di scrivere il
mapping definitivo nell'importer.

Funziona sia con JSON che con CSV, e prova ad auto-rilevare i tipi.

Uso:
    python scripts/inspect_export.py /percorso/al/file.json
    python scripts/inspect_export.py /percorso/al/file.csv
"""

import csv
import json
import sys
from pathlib import Path


def describe_value(v, depth=0, max_depth=4, sample_list_items=1):
    """Rappresentazione leggibile e ricorsiva della struttura di un valore JSON."""
    indent = "  " * depth
    if depth > max_depth:
        print(f"{indent}... (profondità massima raggiunta)")
        return

    if isinstance(v, dict):
        print(f"{indent}dict con {len(v)} chiavi: {list(v.keys())}")
        for k, val in v.items():
            print(f"{indent}  - '{k}':")
            describe_value(val, depth + 2, max_depth, sample_list_items)
    elif isinstance(v, list):
        print(f"{indent}list con {len(v)} elementi")
        if v:
            print(f"{indent}  Esempio del primo elemento:")
            for item in v[:sample_list_items]:
                describe_value(item, depth + 2, max_depth, sample_list_items)
    else:
        preview = str(v)
        if len(preview) > 80:
            preview = preview[:80] + "..."
        print(f"{indent}{type(v).__name__} -> {preview}")


def inspect_json(path: Path):
    print(f"\n{'=' * 70}\nISPEZIONE FILE JSON: {path.name}\n{'=' * 70}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n--- Struttura di primo livello ---")
    describe_value(data, depth=0)

    # Se la root è una lista di record omogenei, mostriamo TUTTE le chiavi
    # che compaiono (utile perché alcuni record potrebbero avere chiavi
    # opzionali mancanti in altri).
    if isinstance(data, list) and data:
        print("\n--- Unione di tutte le chiavi trovate nei record (root è una lista) ---")
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        print(sorted(all_keys))

    # Se la root è un dict, cerchiamo le liste annidate (es. "shows", "movies", "episodes")
    # e facciamo lo stesso identico controllo per ciascuna.
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                print(f"\n--- Unione di tutte le chiavi trovate in data['{key}'] ---")
                all_keys = set()
                for item in val:
                    if isinstance(item, dict):
                        all_keys.update(item.keys())
                print(sorted(all_keys))


def inspect_csv(path: Path):
    print(f"\n{'=' * 70}\nISPEZIONE FILE CSV: {path.name}\n{'=' * 70}")
    with open(path, "r", encoding="utf-8", newline="") as f:
        # Prova a rilevare il delimitatore (Refract di solito usa la virgola,
        # ma alcuni export europei usano il punto e virgola)
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)

    print(f"Delimitatore rilevato: '{delimiter}'")
    print(f"Numero di righe: {len(rows)}")
    print(f"\n--- Colonne trovate ({len(reader.fieldnames or [])}) ---")
    print(reader.fieldnames)

    print("\n--- Prime 3 righe di esempio ---")
    for row in rows[:3]:
        print(row)

    print("\n--- Tipi dedotti per colonna (basati sulla prima riga non vuota) ---")
    for col in reader.fieldnames or []:
        example = next((r[col] for r in rows if r.get(col)), None)
        print(f"  {col}: esempio = {example!r}")


def main():
    if len(sys.argv) != 2:
        print("Uso: python inspect_export.py /percorso/al/file.(json|csv)")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERRORE: file non trovato: {path}")
        sys.exit(1)

    if path.suffix.lower() == ".json":
        inspect_json(path)
    elif path.suffix.lower() == ".csv":
        inspect_csv(path)
    else:
        print("ERRORE: estensione non supportata. Usa un file .json o .csv")
        sys.exit(1)


if __name__ == "__main__":
    main()
