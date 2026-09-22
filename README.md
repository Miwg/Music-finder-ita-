# Music finder

Un programmino in Python che ti aiuta a creare playlist musicali. La lingua principale usata nel codice/interfaccia è l'italiano, ma è pensato in modo che chiunque possa modificarlo per aggiungere altre lingue.

## Cosa fa

Il programma genera playlist usando:
- **YouTube Music** (tramite `ytmusicapi`)
- **Spotify** (opzionale — vedi sotto)

## Requisiti

Prima di tutto installa le librerie necessarie:

```bash
pip install -r requirements.txt
```

## Configurazione

Il programma usa un file `.env` per le chiavi/credenziali segrete (API key, ecc.).
Crea un file chiamato `.env` nella cartella del progetto con dentro le tue credenziali, ad esempio:

```
SPOTIFY_CLIENT_ID=il_tuo_client_id
SPOTIFY_CLIENT_SECRET=il_tuo_client_secret
```

⚠️ **Importante:** non caricare mai il file `.env` su GitHub! Contiene dati segreti.

## Non vuoi usare Spotify?

Nessun problema: basta cancellare la parte di codice relativa a Spotify (e togliere `spotipy` dal `requirements.txt`). Il programma funzionerà comunque con YouTube Music.

## Aggiungere altre lingue

Il programma è scritto principalmente in italiano. Se vuoi aiutare ad aggiungere altre lingue, sei il benvenuto: basta tradurre le stringhe di testo usate nell'interfaccia/messaggi del programma.

## Come si usa

1. Installa le librerie (`pip install -r requirements.txt`)
2. Crea il file `.env` con le tue credenziali (se usi Spotify)
3. Avvia il programma:

```bash
python main.py
```

## Contributi

Pull request e suggerimenti sono benvenuti!
