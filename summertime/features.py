"""Audio features for each song, computed from its 30-second preview.

ReccoBeats' full-track database covers only some of these recordings, and features
computed from a clip don't agree with full-track ones, so every song is analyzed the
same way: its preview is uploaded to ReccoBeats' audio-analysis endpoint. The map
therefore describes the excerpt, which is also what the website plays.
"""
from __future__ import annotations

import time

import httpx
import pandas as pd

from .data import CLIPS, FEATURES, FEATURES_CSV

ANALYZE_URL = "https://api.reccobeats.com/v1/analysis/audio-features"


def preview_url(http: httpx.Client, source: str, source_id: int) -> str:
    """A fresh preview link (they expire, so they aren't stored)."""
    if source == "deezer":
        return http.get(f"https://api.deezer.com/track/{source_id}").json()["preview"]
    return http.get("https://itunes.apple.com/lookup", params={"id": source_id}).json()["results"][0]["previewUrl"]


def analyze_clip(http: httpx.Client, source: str, source_id: int) -> dict[str, float]:
    ext, mime = ("mp3", "audio/mpeg") if source == "deezer" else ("m4a", "audio/mp4")
    CLIPS.mkdir(parents=True, exist_ok=True)
    clip = CLIPS / f"{source}-{source_id}.{ext}"
    if not clip.exists():
        clip.write_bytes(http.get(preview_url(http, source, source_id)).content)
    for _ in range(3):
        with clip.open("rb") as f:
            r = http.post(ANALYZE_URL, files={"audioFile": (clip.name, f, mime)})
        if r.status_code == 429:  # rate limited: wait and retry
            time.sleep(min(int(r.headers.get("Retry-After", "5")), 30))
            continue
        r.raise_for_status()
        return {f: float(r.json()[f]) for f in FEATURES}
    raise RuntimeError(f"ReccoBeats kept rate-limiting {source} {source_id}")


def load_features() -> pd.DataFrame:
    if not FEATURES_CSV.exists():
        return pd.DataFrame(columns=["track_id", *FEATURES])
    return pd.read_csv(FEATURES_CSV)


def update_features(matches: pd.DataFrame, http: httpx.Client | None = None) -> tuple[pd.DataFrame, int]:
    """Analyze matched songs that aren't in features.csv yet. Returns (all features, number added)."""
    feats = load_features()
    todo = matches[~matches["track_id"].isin(feats["track_id"])]
    with (http or httpx.Client(timeout=60)) as client:
        for m in todo.itertuples():
            row = {"track_id": m.track_id, **analyze_clip(client, m.source, int(m.source_id))}
            feats = pd.concat([feats, pd.DataFrame([row])], ignore_index=True)
            feats.to_csv(FEATURES_CSV, index=False)  # save as we go, so a failure loses nothing
    feats[FEATURES] = feats[FEATURES].astype(float)
    return feats, len(todo)


def load_dataset() -> pd.DataFrame:
    """One row per song that has features: song list + match + features."""
    from .data import load_songs
    from .matching import load_matches

    df = load_songs().merge(load_matches(), on="track_id").merge(load_features(), on="track_id")
    df[FEATURES] = df[FEATURES].astype(float)
    return df.dropna(subset=FEATURES).reset_index(drop=True)
