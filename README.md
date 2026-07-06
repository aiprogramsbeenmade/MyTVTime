# 🍿 MyTVTime - Private

Questo programma è un sostituto locale e privato all'applicazione TVTime, nata per colmare il vuoto dopo la chiusura dei suoi servizi.

---

## 🔧 Prerequisiti

Prima di installare il codice assicurarsi di avere la chiave API di TMDB, necessaria per questo programma.
Potrete richiederne una gratuita sul sito di [The Movie Database](https://www.themoviedb.org/).

In oltre MyTVTime permette di importare il catalogo da TVTime usando il tool di Refractor installabile [QUI](https://chromewebstore.google.com/detail/tv-time-out-by-refract/pmejpdpjbkjklfceogdkolmgclldogbi)


---
## 💾 Installazione

- [Linux/OSX](#linuxosx)
- [Windows](#windows)

### Linux/OSX
Assicurarsi di avere installato Python 3.x e `pip`.

1. **Scarica il progetto da github**
    ```bash
   git clone https://github.com/aiprogramsbeenmade/MyTVTime.git
   cd MyTVTime
   pip install -r requirements.txt
   ```
2. **Crea il database**
    ```bash
   python3 scripts/init_db.py
   ```
3. **(Opzionale) Carica il database di TVTime**\
    Sposta nella cartella del programma i file di TVTime:
    ```
   Esempio dei nomi dei file:
   tvtime-movies-[data].json
   tvtime-series-[data].json
   ```
    Ora caricali nel database:
    ```bash
   python3 scripts/import_refract.py --series tvtime-series-[data].json --movies tvtime-movies-[data].json
   python3 scripts/enrich_metadata.py
   ```
    ATTENZIONE: non invertire l'ordine dei file e assicurarsi di non confondersi tra i file ``series`` e ``movies``.


4. **Inserire la chiave api in un file `.env`**\
    Crea un file chiamato ``.env`` nella cartella principale del progetto ed inserisci all'interno la chiave API di TMDB
    ```
   TMDB_API_KEY="La Tua Chiave API"
   ```
5. **Avviare ora il programma eseguendo da terminale:**
    ```bash
   streamlit run app.py
   ```

### Windows
Assicurarsi di avere installato Python 3.11+ (spuntando l'opzione "Add Python to PATH" in fase di installazione).

1. **Scarica il progetto da github**
    ```bash
   git clone https://github.com/aiprogramsbeenmade/MyTVTime.git
   cd MyTVTime
   pip install -r requirements.txt
   ```
2. **Crea il database**
    ```bash
   python3 scripts/init_db.py
   ```
3. **(Opzionale) Carica il database di TVTime**\
    Sposta nella cartella del programma i file di TVTime:
    ```
   Esempio dei nomi dei file:
   tvtime-movies-[data].json
   tvtime-series-[data].json
   ```
    Ora caricali nel database:
    ```bash
   python3 scripts/import_refract.py --series tvtime-series-[data].json --movies tvtime-movies-[data].json
   python3 scripts/enrich_metadata.py
   ```
    ATTENZIONE: non invertire l'ordine dei file e assicurarsi di non confondersi tra i file ``series`` e ``movies``.


4. **Inserire la chiave api in un file `.env`**\
    Crea un file chiamato ``.env`` nella cartella principale del progetto ed inserisci all'interno la chiave API di TMDB
    ```
   TMDB_API_KEY="La Tua Chiave API"
   ```
       
5. **Avviare ora il programma eseguendo da terminale:**
    ```bash
   streamlit run app.py
   ```
   
---
## ⚠️ DISCLAIMER️
Questa applicazione è un progetto personale e indipendente; non vuole essere un sostituto ufficiale a TVTime né tantomeno vanta diritti sui marchi registrati correlati. L'autore non si assume alcuna responsabilità nel caso in cui il software venga utilizzato in modo inappropriato. Il progetto è rilasciato senza alcuno scopo di lucro.

---
## ⚖️ LICENZA
Questo progetto è rilasciato sotto licenza GPL v3. L'utilizzo del codice sorgente, intero o parziale, per scopi commerciali, lucrativi o all'interno di piattaforme proprietarie a pagamento è **severamente vietato**. Ogni riutilizzo deve rimanere gratuito, aperto e attribuito all'autore originale.
Per altre informazioni visitare il file ``LICENSE``.
