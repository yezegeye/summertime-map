"""Add new tracks from the Spotify playlist to data/songs.csv.

Reads the playlist's public embed page (no Spotify login or API key needed) and
appends any track that isn't already in songs.csv. Existing rows, including any
year or notes you've filled in, are left as they are. Track IDs listed in
data/skip.txt are never added.

    python scripts/sync_playlist.py [playlist link or ID]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
import pandas as pd

DEFAULT_PLAYLIST = "3VVoHV6zHfcoJvqrtGrcED"
DATA = Path(__file__).resolve().parent.parent / "data"
COLUMNS = ["artist", "title", "year", "duration_s", "spotify_url", "notes"]


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
        sys.exit("Couldn't read the playlist page (Spotify may have changed its layout).")
    entity = json.loads(m.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    return [
        {
            "artist": re.sub(r",\s*", ";", t["subtitle"]),
            "title": t["title"],
            "year": None,
            "duration_s": round(t["duration"] / 1000),
            "spotify_url": "https://open.spotify.com/track/" + t["uri"].rsplit(":", 1)[-1],
            "notes": None,
        }
        for t in entity.get("trackList", [])
        if t.get("uri", "").startswith("spotify:track:")
    ]


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PLAYLIST
    playlist_id = re.search(r"([A-Za-z0-9]{22})", arg).group(1)

    songs_path = DATA / "songs.csv"
    songs = pd.read_csv(songs_path) if songs_path.exists() else pd.DataFrame(columns=COLUMNS)
    skip_path = DATA / "skip.txt"
    skip = set()
    if skip_path.exists():
        skip = {line.split("#")[0].strip() for line in skip_path.read_text().splitlines()} - {""}

    have = {url.rsplit("/", 1)[-1] for url in songs["spotify_url"]}
    tracks = playlist_tracks(playlist_id)
    new = [t for t in tracks if (tid := t["spotify_url"].rsplit("/", 1)[-1]) not in have and tid not in skip]

    in_playlist = {t["spotify_url"] for t in tracks}
    gone = songs[~songs["spotify_url"].isin(in_playlist)]

    print(f"Playlist has {len(tracks)} tracks; {len(new)} new.")
    for t in new:
        print(f"  + {t['artist']} - {t['title']}")
    if len(gone):
        print("In songs.csv but no longer in the playlist (left in place; delete the rows if you want them gone):")
        for row in gone.itertuples():
            print(f"  ? {row.artist} - {row.title}")

    if new:
        songs = pd.concat([songs, pd.DataFrame(new)], ignore_index=True)[COLUMNS]
        songs.to_csv(songs_path, index=False)


if __name__ == "__main__":
    main()
