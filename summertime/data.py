"""Paths, the feature list, and loading the song list."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SONGS = DATA / "songs.csv"        # one row per recording; the only file edited by hand
SKIP = DATA / "skip.txt"          # Spotify track IDs never to add from the playlist
MATCHES = DATA / "matches.csv"    # which Deezer/iTunes recording each song was matched to
FEATURES_CSV = DATA / "features.csv"
CLIPS = DATA / "clips"            # downloaded previews (git-ignored)

SONG_COLUMNS = ["artist", "title", "year", "year_source", "duration_s", "spotify_url", "notes"]

FEATURES = [
    "danceability", "energy", "valence", "tempo", "loudness",
    "acousticness", "instrumentalness", "speechiness", "liveness",
]


def spotify_id(url: str) -> str:
    """'https://open.spotify.com/track/<id>?si=...' or 'spotify:track:<id>' -> '<id>'."""
    m = re.search(r"track[/:]([A-Za-z0-9]{22})", str(url))
    if not m:
        raise ValueError(f"Not a Spotify track link: {url}")
    return m.group(1)


def load_songs() -> pd.DataFrame:
    songs = pd.read_csv(SONGS, dtype={"year": "Int64"})
    songs["track_id"] = songs["spotify_url"].map(spotify_id)
    return songs


def load_skip() -> set[str]:
    if not SKIP.exists():
        return set()
    return {line.split("#")[0].strip() for line in SKIP.read_text().splitlines()} - {""}
