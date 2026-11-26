# Summertime Map

One song, many interpretations. This project takes a fixed list of recordings of
George Gershwin's "Summertime" and uses unsupervised learning to map how they
differ. The melody is the same in every version, so whatever separates them on
the map comes from how each artist performs it: tempo, energy, instrumentation,
mood.

> Status: early. The notebook skeleton is in place; the song list is next.

## Plan

1. **Notebook** (`notebooks/summertime.ipynb`): fetch audio features for each
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
| `year`        | 1957                                                      |
| `spotify_url` | https://open.spotify.com/track/...                        |
| `notes`       | optional, e.g. "instrumental", "live"                     |

The Spotify link gives the track ID used to look up audio features.

### Adding songs

1. Add them to the Spotify playlist.
2. Run `python scripts/sync_playlist.py`. New tracks are appended to `songs.csv`;
   rows you've already edited are left alone. Track IDs listed in `data/skip.txt`
   are never added.
3. Re-run the notebook. Only new songs are matched (Deezer, or iTunes if Deezer lacks them) and analyzed; earlier
   results are reused from `data/matches.csv` and `data/features.csv`.
4. Check the match table in step 2 of the notebook. To fix a wrong match, edit
   that row's `source` and `source_id` in `matches.csv` and delete the song's row from
   `features.csv` so it is re-analyzed.

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

## Running locally

```bash
conda env create -f environment.yml
conda activate summertime
jupyter lab notebooks/summertime.ipynb
```
