# Summertime Map

One song, many interpretations. This project takes a fixed list of recordings of
George Gershwin's "Summertime" and uses unsupervised learning to map how they
differ. The melody is the same in every version, so whatever separates them on
the map comes from how each artist performs it: tempo, energy, instrumentation,
mood.

> Status: in progress. 54 versions collected with audio features; the analysis
> (PCA, clustering) and the website are next.

## Plan

1. **Notebook** (`notebooks/summertime.ipynb`): load the audio features for each
   version, standardize them, run PCA to 2-D, cluster with K-Means, check how
   valid the clusters are (silhouette score, stability across resamples), and
   draft a description of each cluster.
2. **Export:** write songs, coordinates, clusters, album covers and preview links
   to one JSON file for the website.
3. **Website v1** (`site/`): a static, interactive map. Hover a point to see its
   album cover; read what each cluster might represent and how much to trust it.
4. **Website v2:** after one click to enable sound, hovering a point for about a
   second plays a 30-second preview.
5. **Later:** add more jazz standards, working toward
   [Playlist Cartographer](../playlist-cartographer).

## The song list

`data/songs.csv` has one row per recording:

| column        | example                                                   |
|---------------|-----------------------------------------------------------|
| `artist`      | Ella Fitzgerald & Louis Armstrong                         |
| `title`       | Summertime                                                |
| `year`        | 1957 (year the performance was recorded, not the reissue) |
| `year_source` | where the year came from, e.g. "draft - verify", "Discogs" |
| `spotify_url` | https://open.spotify.com/track/...                        |
| `notes`       | optional, e.g. "instrumental", "live"                     |

The Spotify link gives the track ID used to look up audio features.

Years can't be filled in automatically: streaming services and databases list the
date of whichever reissue or compilation a track is on now (a 1939 Sidney Bechet
recording shows up as "2026 Remaster"). So they are entered by hand. Year is not
used for clustering; it's used afterwards, to check whether the sound-based groups
line up with era.

### Adding songs

1. Add them to the Spotify playlist.
2. Run `python -m summertime.update`. It adds new tracks to `songs.csv` (rows
   you've edited are left alone; track IDs in `data/skip.txt` are never added),
   matches them to a preview on Deezer or iTunes, computes their audio features,
   and lists anything worth checking, such as a matched recording whose length
   differs from Spotify's.
3. Re-run the notebook.

To fix a wrong match, edit that row's `source` and `source_id` in
`data/matches.csv` and delete the song's row from `data/features.csv` so it is
re-analyzed.

## Where the data comes from

- **Song list:** the Spotify playlist, read from its public embed page.
- **Previews and album covers:** Spotify no longer gives new apps preview clips,
  so these come from Deezer, or Apple's iTunes Search API when Deezer doesn't have
  a recording. Each song is matched by artist, title and length.
- **Audio features** (danceability, energy, valence, tempo, loudness,
  acousticness, instrumentalness, speechiness, liveness): computed from each
  30-second preview by [ReccoBeats](https://reccobeats.com)' audio-analysis
  endpoint, the same way for every song, so the map describes the excerpt rather
  than the whole track. (Spotify closed its own audio-features endpoint to new
  apps in November 2024, and ReccoBeats' full-track database covers only some of
  these recordings.)

## Project layout

```
data/
  songs.csv        the song list (the only file edited by hand)
  skip.txt         playlist tracks to leave out
  matches.csv      the Deezer/iTunes recording matched to each song
  features.csv     audio features per song
summertime/        Python package
  data.py          paths, feature list, loading the song list
  playlist.py      reads the Spotify playlist
  matching.py      matches songs to Deezer/iTunes recordings
  features.py      previews -> audio features
  update.py        `python -m summertime.update`: all of the above in one go
notebooks/
  summertime.ipynb the analysis, step by step
tests/             tests for the matching logic
site/              the website (to come)
```

## Running locally

```bash
conda env create -f environment.yml
conda activate summertime
python -m summertime.update          # bring data up to date with the playlist
jupyter lab notebooks/summertime.ipynb
pytest                               # run the tests
```
