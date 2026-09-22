#!/usr/bin/env python3
"""
Cerca canzoni dal nome e, se vuoi, crea una playlist.

YouTube Music funziona subito, senza account.
Spotify è opzionale: serve un'app gratuita su https://developer.spotify.com
"""

from __future__ import annotations

import os
import webbrowser
from typing import Any

# Carica le variabili dal file .env (se esiste), così le chiavi
# Spotify non restano scritte nel codice.
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Passo 1 — Utilità per parlare con l'utente
# ---------------------------------------------------------------------------


def chiedi_si_no(domanda: str) -> bool:
    """Chiede sì/no e accetta risposte come s, si, y, n."""
    while True:
        risposta = input(f"{domanda} [s/n]: ").strip().lower()
        if risposta in {"s", "si", "sì", "y", "yes"}:
            return True
        if risposta in {"n", "no"}:
            return False
        print("    Scrivi s oppure n.")


def chiedi_brani() -> list[str]:
    """
    Raccoglie i nomi delle canzoni, uno per riga.

    L'utente scrive 'fine' quando ha finito. I duplicati vuoti vengono ignorati.
    """
    print()
    print("Inserisci i nomi delle canzoni (es. Bohemian Rhapsody Queen).")
    print("Quando hai finito, scrivi: fine")
    print()

    brani: list[str] = []
    while True:
        testo = input("Canzone: ").strip()
        if testo.lower() == "fine":
            break
        if testo:
            brani.append(testo)
    return brani


# ---------------------------------------------------------------------------
# Passo 2 — Ricerca su YouTube Music (nessuna API key)
# ---------------------------------------------------------------------------


def client_youtube():
    """
    Apre una sessione anonima verso YouTube Music.

    ytmusicapi parla con le stesse API interne del sito:
    non serve una chiave Google.
    """
    from ytmusicapi import YTMusic

    return YTMusic()


def cerca_su_youtube(yt, nome: str) -> dict[str, Any] | None:
    """
    Cerca una canzone e prende il primo risultato 'songs'.

    Restituisce un dizionario con titolo, artisti, video_id e link,
    oppure None se non trova nulla.
    """
    try:
        risultati = yt.search(nome, filter="songs", limit=1)
    except Exception as errore:
        print(f"    Errore YouTube: {errore}")
        return None

    if not risultati:
        return None

    primo = risultati[0]
    video_id = primo.get("videoId")
    if not video_id:
        return None

    artisti = primo.get("artists") or []
    nomi_artisti = ", ".join(a.get("name", "") for a in artisti if a.get("name"))

    return {
        "fonte": "youtube",
        "titolo": primo.get("title", nome),
        "artisti": nomi_artisti or "sconosciuto",
        "video_id": video_id,
        "uri": None,
        "link": f"https://www.youtube.com/watch?v={video_id}",
        "link_music": f"https://music.youtube.com/watch?v={video_id}",
    }


def link_playlist_youtube(video_ids: list[str]) -> str | None:
    """
    Crea un URL YouTube che mette i video in coda, senza account.

    YouTube accetta: https://www.youtube.com/watch_videos?video_ids=id1,id2,id3
    (funziona fino a circa 50 video).
    """
    if not video_ids:
        return None
    ids = ",".join(video_ids[:50])
    return f"https://www.youtube.com/watch_videos?video_ids={ids}"


# ---------------------------------------------------------------------------
# Passo 3 — Ricerca (e playlist) su Spotify, solo se hai le credenziali
# ---------------------------------------------------------------------------


def credenziali_spotify() -> tuple[str, str, str] | None:
    """Legge Client ID, Secret e Redirect URI dal file .env."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    redirect = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback").strip()
    if not client_id or not client_secret:
        return None
    return client_id, client_secret, redirect


def client_spotify_ricerca():
    """
    Client 'Client Credentials': va bene per CERCARE brani,
    ma NON può creare playlist (non c'è un utente loggato).
    """
    from spotipy import Spotify
    from spotipy.oauth2 import SpotifyClientCredentials

    credenziali = credenziali_spotify()
    if credenziali is None:
        return None

    client_id, client_secret, _ = credenziali
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return Spotify(auth_manager=auth)


def client_spotify_utente():
    """
    Client con login nel browser.

    Serve per creare una playlist nel TUO account.
    La prima volta si apre Spotify e chiede il permesso;
    poi il token viene salvato in .cache.
    """
    from spotipy import Spotify
    from spotipy.oauth2 import SpotifyOAuth

    credenziali = credenziali_spotify()
    if credenziali is None:
        return None

    client_id, client_secret, redirect = credenziali
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect,
        scope="playlist-modify-public playlist-modify-private",
        cache_path=".cache",
        open_browser=True,
    )
    return Spotify(auth_manager=auth)


def cerca_su_spotify(sp, nome: str) -> dict[str, Any] | None:
    """Cerca una traccia su Spotify e prende il primo risultato."""
    try:
        dati = sp.search(q=nome, type="track", limit=1, market="IT")
    except Exception as errore:
        print(f"    Errore Spotify: {errore}")
        return None

    items = (dati.get("tracks") or {}).get("items") or []
    if not items:
        return None

    traccia = items[0]
    artisti = ", ".join(a["name"] for a in traccia.get("artists", []) if a.get("name"))

    return {
        "fonte": "spotify",
        "titolo": traccia.get("name", nome),
        "artisti": artisti or "sconosciuto",
        "video_id": None,
        "uri": traccia.get("uri"),
        "link": traccia.get("external_urls", {}).get("spotify", ""),
        "link_music": None,
    }


def crea_playlist_spotify(nome_playlist: str, uris: list[str]) -> str | None:
    """
    Crea una playlist pubblica nel tuo account e aggiunge i brani trovati.

    Ogni brano su Spotify ha un 'URI' tipo spotify:track:xxxxx.
    """
    if not uris:
        return None

    sp = client_spotify_utente()
    if sp is None:
        return None

    me = sp.current_user()
    user_id = me["id"]
    playlist = sp.user_playlist_create(
        user=user_id,
        name=nome_playlist,
        public=True,
        description="Creata con cerca-canzoni",
    )
    sp.playlist_add_items(playlist["id"], uris)
    return playlist.get("external_urls", {}).get("spotify")


# ---------------------------------------------------------------------------
# Passo 4 — Salvare la playlist sul computer
# ---------------------------------------------------------------------------


def salva_file_testo(percorso: str, titoli_cercati: list[str], risultati: list[dict | None]) -> None:
    """Scrive un .txt leggibile, utile da aprire o condividere."""
    with open(percorso, "w", encoding="utf-8") as file:
        file.write("PLAYLIST\n")
        file.write("=" * 50 + "\n\n")
        for i, (cercato, trovato) in enumerate(zip(titoli_cercati, risultati), start=1):
            file.write(f"{i}. cercato: {cercato}\n")
            if trovato:
                file.write(f"   {trovato['titolo']} — {trovato['artisti']}\n")
                file.write(f"   {trovato['link']}\n")
            else:
                file.write("   non trovato\n")
            file.write("\n")


def salva_file_html(
    percorso: str,
    titoli_cercati: list[str],
    risultati: list[dict | None],
    link_mix: str | None,
) -> None:
    """Scrive una pagina HTML con i link cliccabili."""
    righe = [
        "<!DOCTYPE html>",
        "<html lang='it'><head><meta charset='utf-8'>",
        "<title>Playlist</title>",
        "<style>body{font-family:sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem}</style>",
        "</head><body>",
        "<h1>Playlist</h1>",
    ]
    if link_mix:
        righe.append(f"<p><a href='{link_mix}'>Apri mix su YouTube</a></p>")
    righe.append("<ol>")
    for cercato, trovato in zip(titoli_cercati, risultati):
        if trovato:
            righe.append(
                f"<li><a href='{trovato['link']}'>{trovato['titolo']}</a>"
                f" — {trovato['artisti']}<br><small>cercato: {cercato}</small></li>"
            )
        else:
            righe.append(f"<li>{cercato} — non trovato</li>")
    righe.append("</ol></body></html>")
    with open(percorso, "w", encoding="utf-8") as file:
        file.write("\n".join(righe))


# ---------------------------------------------------------------------------
# Passo 5 — Il programma principale (il flusso che vedi nel terminale)
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 54)
    print("  Cerca canzoni  |  YouTube subito, Spotify opzionale")
    print("=" * 54)

    # 5.1 — Quali servizi usare
    usa_youtube = True
    usa_spotify = credenziali_spotify() is not None

    if usa_spotify:
        print("\nHo trovato le credenziali Spotify nel file .env.")
        usa_spotify = chiedi_si_no("Vuoi cercare anche su Spotify?")
    else:
        print("\nSpotify non è configurato: userò solo YouTube Music.")
        print("Per attivarlo, copia .env.example in .env e inserisci Client ID/Secret.")

    # 5.2 — Elenco dei nomi
    brani = chiedi_brani()
    if not brani:
        print("\nNessuna canzone inserita. Ciao!")
        return

    # 5.3 — Avvio i client una sola volta (è più veloce)
    yt = client_youtube() if usa_youtube else None
    sp = client_spotify_ricerca() if usa_spotify else None

    # 5.4 — Per ogni nome, cerco il brano
    print()
    print("=" * 54)
    print("  Ricerca")
    print("=" * 54)

    risultati_yt: list[dict | None] = []
    risultati_sp: list[dict | None] = []

    for i, nome in enumerate(brani, start=1):
        print(f"\n[{i}/{len(brani)}] {nome}")

        yt_hit = cerca_su_youtube(yt, nome) if yt else None
        sp_hit = cerca_su_spotify(sp, nome) if sp else None
        risultati_yt.append(yt_hit)
        risultati_sp.append(sp_hit)

        if yt_hit:
            print(f"    YouTube: {yt_hit['titolo']} — {yt_hit['artisti']}")
            print(f"             {yt_hit['link']}")
        elif yt:
            print("    YouTube: non trovato")

        if sp_hit:
            print(f"    Spotify: {sp_hit['titolo']} — {sp_hit['artisti']}")
            print(f"             {sp_hit['link']}")
        elif sp:
            print("    Spotify: non trovato")

    # 5.5 — Vuoi creare una playlist adesso?
    print()
    print("=" * 54)
    if not chiedi_si_no("Vuoi creare una playlist adesso?"):
        print("Ok, lascio solo i risultati qui sopra.")
        return

    nome_playlist = input("Nome della playlist: ").strip() or "La mia playlist"

    # Playlist YouTube = file + URL mix
    video_ids = [r["video_id"] for r in risultati_yt if r and r.get("video_id")]
    mix = link_playlist_youtube(video_ids)

    salva_file_testo("playlist.txt", brani, risultati_yt)
    salva_file_html("playlist.html", brani, risultati_yt, mix)
    print("\nSalvato: playlist.txt e playlist.html")

    if mix:
        print(f"Mix YouTube: {mix}")
        if chiedi_si_no("Apro il mix YouTube nel browser?"):
            webbrowser.open(mix)

    # Playlist su Spotify (solo se abbiamo URI e credenziali)
    uris = [r["uri"] for r in risultati_sp if r and r.get("uri")]
    if uris and credenziali_spotify() is not None:
        if chiedi_si_no("Creo anche la playlist sul tuo account Spotify?"):
            url = crea_playlist_spotify(nome_playlist, uris)
            if url:
                print(f"Playlist Spotify: {url}")
                if chiedi_si_no("Apro Spotify nel browser?"):
                    webbrowser.open(url)
            else:
                print("Non sono riuscito a creare la playlist su Spotify.")
    elif usa_spotify:
        print("Nessun brano Spotify da mettere in playlist.")

    print("\nFatto.")


if __name__ == "__main__":
    # Questo if serve a far partire main() solo se esegui
    # il file direttamente (python cerca.py), non se lo importi.
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrotto.")
