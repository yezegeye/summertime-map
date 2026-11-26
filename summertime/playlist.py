"""Add new tracks from the Spotify playlist to data/songs.csv.

Reads the playlist's public embed page, so no Spotify login or API key is needed.
Existing rows, including any year or notes filled in by hand, are left alone, and
track IDs in data/skip.txt are never added.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx
import pandas as pd

from .data import SONG_COLUMNS, SONGS, load_skip, spotify_id

DEFAULT_PLAYLIST = "3VVoHV6zHfcoJvqrtGrcED"


def playlist_tracks(playlist_id: str) -> list[dict]:
    r = httpx.get(
        f"https://open.spotify.com/embed/playlist/{playlist_id}",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=20,
    )
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError("Couldn't read the playlist page (Spotify may have changed its layout).")
    entity = json.loads(m.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    return [
        {
            # Artists are separated by a comma plus a (sometimes non-breaking) space.
            "artist": re.sub(r",\s*", ";", t["subtitle"]),
            "title": t["title"],
            "duration_s": round(t["duration"] / 1000),
            "spotify_url": "https://open.spotify.com/track/" + t["uri"].rsplit(":", 1)[-1],
        }
        for t in entity.get("trackList", [])
        if t.get("uri", "").startswith("spotify:track:")
    ]


@dataclass
class SyncResult:
    in_playlist: int
    added: list[str]
    gone: list[str]   # in songs.csv but no longer in the playlist (left in place)


def sync(playlist_id: str = DEFAULT_PLAYLIST) -> SyncResult:
    songs = pd.read_csv(SONGS, dtype={"year": "Int64"}) if SONGS.exists() else pd.DataFrame(columns=SONG_COLUMNS)
    have = set(songs["spotify_url"].map(spotify_id))
    skip = load_skip()
    tracks = playlist_tracks(playlist_id)

    new = [t for t in tracks if spotify_id(t["spotify_url"]) not in have | skip]
    in_playlist = {t["spotify_url"] for t in tracks}
    gone = songs[~songs["spotify_url"].isin(in_playlist)]

    if new:
        songs = pd.concat([songs, pd.DataFrame(new)], ignore_index=True)
        songs.reindex(columns=SONG_COLUMNS).to_csv(SONGS, index=False)
    return SyncResult(
        in_playlist=len(tracks),
        added=[f"{t['artist']} - {t['title']}" for t in new],
        gone=[f"{r.artist} - {r.title}" for r in gone.itertuples()],
    )
