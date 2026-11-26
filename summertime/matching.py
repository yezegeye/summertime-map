"""Find each song's recording on Deezer (or iTunes) for its preview clip and album cover.

Spotify no longer gives new apps preview clips, so each song is matched to the same
recording on Deezer, or on Apple's iTunes Search API when Deezer doesn't have it.
A candidate must have the same artist and title; among those,
versions whose tags (instrumental, live, remix...) match the Spotify title are preferred,
and among those the one whose length is closest to the Spotify track's wins.
"""
from __future__ import annotations

import re
import unicodedata

import httpx
import pandas as pd

from .data import MATCHES

TAGS = ["instrumental", "remix", "live", "dub", "karaoke", "demo"]
MATCH_COLUMNS = ["track_id", "source", "source_id", "match_title", "album", "cover", "length_diff_s"]


def norm(s: str) -> str:
    """Lowercase and strip accents: 'Rosinha De Valença' -> 'rosinha de valenca'."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def base_title(title: str) -> str:
    """'Summertime - Mono Version' / 'Summertime (Live)' / 'Summertime / Motherless Child' -> 'summertime'."""
    return norm(re.split(r" - |\(|\[|/", title)[0]).strip()


def pick_best(cands: list[dict], artist: str, title: str, duration_s: int) -> dict | None:
    """Choose the candidate most likely to be the same recording.

    `cands` are dicts with at least "artist", "title" and "duration" (seconds).
    `artist` may list several artists separated by ";"; the first is the main one.
    """
    main = norm(artist.split(";")[0])
    short = base_title(title)

    def same_artist(c):
        return main in norm(c["artist"]) or norm(c["artist"]) in norm(artist)

    wanted = {t for t in TAGS if t in norm(title)}

    def tag_mismatches(c):
        # Tags on one title but not the other: a live take for a studio track, or vice versa.
        return len(wanted ^ {t for t in TAGS if t in norm(c["title"])})

    ok = [c for c in cands if same_artist(c) and short in norm(c["title"])]
    if not ok:
        return None
    return min(ok, key=lambda c: (tag_mismatches(c), abs(c["duration"] - duration_s)))


def deezer_candidates(http: httpx.Client, artist: str, title: str) -> list[dict]:
    main, short = artist.split(";")[0], base_title(title)
    raw = []
    for q in [f'artist:"{main}" track:"{short}"', f"{main} {short}"]:
        raw += http.get("https://api.deezer.com/search", params={"q": q, "limit": 25}).json().get("data", [])
    return [
        {"source": "deezer", "source_id": c["id"], "artist": c["artist"]["name"], "title": c["title"],
         "duration": c["duration"], "album": c["album"]["title"], "cover": c["album"]["cover_big"]}
        for c in raw
    ]


def itunes_candidates(http: httpx.Client, artist: str, title: str) -> list[dict]:
    main, short = artist.split(";")[0], base_title(title)
    r = http.get("https://itunes.apple.com/search",
                 params={"term": f"{main} {short}", "media": "music", "entity": "song", "limit": 25})
    return [
        {"source": "itunes", "source_id": c["trackId"], "artist": c["artistName"], "title": c["trackName"],
         "duration": round(c["trackTimeMillis"] / 1000), "album": c["collectionName"],
         "cover": c["artworkUrl100"].replace("100x100", "500x500")}
        for c in r.json().get("results", [])
        if c.get("previewUrl") and c.get("trackTimeMillis")
    ]


def find_recording(http: httpx.Client, artist: str, title: str, duration_s: int) -> dict:
    for candidates in (deezer_candidates, itunes_candidates):
        best = pick_best(candidates(http, artist, title), artist, title, duration_s)
        if best:
            return {
                "source": best["source"], "source_id": best["source_id"],
                "match_title": f'{best["artist"]} - {best["title"]}', "album": best["album"],
                "cover": best["cover"], "length_diff_s": best["duration"] - duration_s,
            }
    return {}


def load_matches() -> pd.DataFrame:
    if not MATCHES.exists():
        return pd.DataFrame(columns=MATCH_COLUMNS)
    return pd.read_csv(MATCHES, dtype={"source_id": "Int64"}).dropna(subset=["source_id"])


def update_matches(songs: pd.DataFrame, http: httpx.Client | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Match songs that aren't in matches.csv yet; earlier matches (including hand fixes) are kept.

    Returns (all matches, "artist - title" of the songs that were newly matched).
    """
    matches = load_matches()
    todo = songs[~songs["track_id"].isin(matches["track_id"])]
    if todo.empty:
        return matches, []
    with (http or httpx.Client(timeout=30)) as client:
        new = [{"track_id": s.track_id, **find_recording(client, s.artist, s.title, s.duration_s)}
               for s in todo.itertuples()]
    matches = pd.concat([matches, pd.DataFrame(new)], ignore_index=True).reindex(columns=MATCH_COLUMNS)
    matches.to_csv(MATCHES, index=False)
    found = [f"{s.artist} - {s.title}" for s, n in zip(todo.itertuples(), new) if n.get("source")]
    return load_matches(), found


def match_report(songs: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Every song with its match, most doubtful (biggest length difference, or unmatched) first."""
    view = songs[["track_id", "artist", "title"]].merge(matches, on="track_id", how="left")
    order = view["length_diff_s"].abs().fillna(float("inf"))
    return view.loc[order.sort_values(ascending=False).index].drop(columns=["cover"]).reset_index(drop=True)
