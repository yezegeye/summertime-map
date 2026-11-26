import pytest

from summertime.data import spotify_id
from summertime.matching import base_title, norm, pick_best


def test_spotify_id_from_link_and_uri():
    tid = "3eYCJXTViFwl5mdtcTsF4G"
    assert spotify_id(f"https://open.spotify.com/track/{tid}?si=abc") == tid
    assert spotify_id(f"spotify:track:{tid}") == tid
    with pytest.raises(ValueError):
        spotify_id("https://open.spotify.com/playlist/3VVoHV6zHfcoJvqrtGrcED")


def test_norm_strips_accents_and_case():
    assert norm("Rosinha De Valença") == "rosinha de valenca"


@pytest.mark.parametrize("title", [
    "Summertime", "Summertime - Mono Version", "Summertime (Live)",
    "Summertime [2026 Remaster]", "Summertime / Sometimes I Feel Like a Motherless Child",
])
def test_base_title(title):
    assert base_title(title) == "summertime"


def cand(artist, title, duration):
    return {"artist": artist, "title": title, "duration": duration}


def test_prefers_closest_length():
    best = pick_best([cand("Nina Simone", "Summertime", 362), cand("Nina Simone", "Summertime", 340)],
                     "Nina Simone", "Summertime", 339)
    assert best["duration"] == 340


def test_avoids_unwanted_version_tags_even_if_length_matches():
    # The instrumental mix has the exact length, but the Spotify track isn't an instrumental.
    best = pick_best([cand("Sublime", "Doin' Time (Marshall Arts Instrumental Version)", 251),
                      cand("Sublime", "Doin' Time", 252)],
                     "Sublime", "Doin' Time", 251)
    assert best["title"] == "Doin' Time"


def test_keeps_tag_when_spotify_title_has_it():
    best = pick_best([cand("T-Pain", "Summertime", 145), cand("T-Pain", "Summertime (Live)", 146)],
                     "T-Pain", "Summertime - Live", 145)
    assert best["title"] == "Summertime (Live)"


def test_rejects_other_artists_and_songs():
    cands = [cand("Will Smith", "Summertime", 240), cand("Janis Joplin", "Piece of My Heart", 241)]
    assert pick_best(cands, "Big Brother & The Holding Company;Janis Joplin", "Summertime", 241) is None


def test_matches_any_listed_artist():
    best = pick_best([cand("Ella Fitzgerald", "Summertime", 298)],
                     "Ella Fitzgerald;Louis Armstrong", "Summertime", 298)
    assert best is not None
