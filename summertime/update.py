"""Bring the data up to date with the Spotify playlist, in one command:

    python -m summertime.update [playlist link or ID]

1. adds new playlist tracks to data/songs.csv,
2. matches new songs to a Deezer/iTunes recording (data/matches.csv),
3. computes audio features for new matches (data/features.csv),
and then lists anything worth checking by hand.
"""
from __future__ import annotations

import re
import sys

from .data import load_songs
from .features import update_features
from .matching import match_report, update_matches
from .playlist import DEFAULT_PLAYLIST, sync

LENGTH_WARNING_S = 5   # a bigger length difference often means a different recording


def main(argv: list[str]) -> None:
    playlist = re.search(r"([A-Za-z0-9]{22})", argv[0]).group(1) if argv else DEFAULT_PLAYLIST

    result = sync(playlist)
    print(f"Playlist: {result.in_playlist} tracks, {len(result.added)} new")
    for name in result.added:
        print(f"  + {name}")

    songs = load_songs()
    matches, matched = update_matches(songs)
    print(f"Matched {len(matched)} new song(s) to a preview")

    _, analyzed = update_features(matches)
    print(f"Analyzed {analyzed} new preview(s)")

    report = match_report(songs, matches)
    unmatched = report[report["source"].isna()]
    doubtful = report[report["length_diff_s"].abs() > LENGTH_WARNING_S]
    if len(unmatched) or len(doubtful) or result.gone:
        print("\nWorth checking:")
        for r in unmatched.itertuples():
            print(f"  ✗ no preview found: {r.artist} - {r.title}")
        for r in doubtful.itertuples():
            diff = f"{abs(r.length_diff_s):.0f} s {'longer' if r.length_diff_s > 0 else 'shorter'}"
            print(f"  ? {r.artist} - {r.title}: matched recording is {diff} ({r.match_title}, {r.source})")
        for name in result.gone:
            print(f"  - no longer in the playlist (delete its row in songs.csv to drop it): {name}")
    print(f"\n{len(songs)} songs in data/songs.csv")


if __name__ == "__main__":
    main(sys.argv[1:])
