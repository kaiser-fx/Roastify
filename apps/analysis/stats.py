"""
Deterministic statistics engine for Roastify playlists.
Pure functions only: no network calls, no randomness, no AI.
Computes facts from Track and Playlist objects.
Fields absent from provider data remain None.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from apps.analysis.models import ArtistShare, Playlist, PlaylistStats, Track

_YEAR_REGEX = re.compile(r"^(19\d{2}|20\d{2})")


def _extract_year(release_date: str | None) -> int | None:
    """Extract 4-digit release year from date strings like '2023-01-15' or '1999'."""
    if not release_date:
        return None
    match = _YEAR_REGEX.match(str(release_date).strip())
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def calculate_playlist_stats(playlist: Playlist) -> PlaylistStats:
    """
    Compute deterministic statistical summary from a Playlist.

    Handles edge cases:
    - Empty playlists (returns zeroes, empty lists, and None for optional fields)
    - Single track
    - All tracks by the same artist
    - Missing artist names (treated safely as 'Unknown Artist')
    - Duplicate tracks by title and artist
    """
    tracks = playlist.tracks
    total_tracks = len(tracks)

    if total_tracks == 0:
        return PlaylistStats(
            track_count=0,
            unique_artist_count=0,
            top_artists=[],
            top_artist_share=0.0,
            top3_share=0.0,
            duplicate_tracks=[],
            release_year_distribution=None,
            explicit_share=None,
            genre_distribution=None,
        )

    # Count artist appearances across all tracks.
    artist_counts: Counter[str] = Counter()
    # Track-to-artists mapping for multi-artist set calculations.
    track_artist_sets: list[set[str]] = []

    for track in tracks:
        valid_artists = [a.strip() for a in track.artists if a and a.strip()]
        if not valid_artists:
            valid_artists = ["Unknown Artist"]

        current_track_artists: set[str] = set()
        for artist in valid_artists:
            artist_counts[artist] += 1
            current_track_artists.add(artist)

        track_artist_sets.append(current_track_artists)

    unique_artist_count = len(artist_counts)

    # Build sorted list of top artists.
    top_artists: list[ArtistShare] = []
    top_artist_names: list[str] = []
    for name, count in artist_counts.most_common(10):
        share = round(count / total_tracks, 4)
        top_artists.append(ArtistShare(name=name, count=count, share=share))
        if len(top_artist_names) < 3:
            top_artist_names.append(name)

    # Top 1 artist share.
    top_artist_share = top_artists[0].share if top_artists else 0.0

    # Top 3 combined share: tracks that contain at least one of the top 3 artists.
    top3_set = set(top_artist_names)
    tracks_with_top3 = sum(
        1 for artist_set in track_artist_sets if bool(artist_set & top3_set)
    )
    top3_share = round(tracks_with_top3 / total_tracks, 4)

    # Identify duplicate tracks (same title and primary artist, case-insensitive).
    seen_track_keys: set[str] = set()
    duplicates_set: set[str] = set()
    for track in tracks:
        norm_title = track.title.strip().lower()
        primary_artist = (
            track.artists[0].strip().lower()
            if track.artists and track.artists[0].strip()
            else "unknown"
        )
        key = f"{norm_title} by {primary_artist}"
        if key in seen_track_keys:
            duplicates_set.add(track.title.strip())
        else:
            seen_track_keys.add(key)

    duplicate_tracks = sorted(list(duplicates_set))

    # Release year distribution (optional, only if dates are present).
    years: list[int] = []
    for track in tracks:
        y = _extract_year(track.release_date)
        if y is not None:
            years.append(y)

    release_year_distribution: dict[int, int] | None = None
    if years:
        year_counter = Counter(years)
        release_year_distribution = dict(sorted(year_counter.items()))

    # Explicit share (optional, only if explicit flags are present).
    explicit_known_count = 0
    explicit_true_count = 0
    for track in tracks:
        if track.explicit is not None:
            explicit_known_count += 1
            if track.explicit:
                explicit_true_count += 1

    explicit_share: float | None = None
    if explicit_known_count > 0:
        explicit_share = round(explicit_true_count / explicit_known_count, 4)

    # Genre distribution (optional, only if genres are present).
    all_genres: list[str] = []
    for track in tracks:
        if track.genres:
            for g in track.genres:
                cleaned = g.strip().lower()
                if cleaned:
                    all_genres.append(cleaned)

    genre_distribution: dict[str, int] | None = None
    if all_genres:
        genre_counter = Counter(all_genres)
        genre_distribution = dict(genre_counter.most_common(10))

    return PlaylistStats(
        track_count=total_tracks,
        unique_artist_count=unique_artist_count,
        top_artists=top_artists,
        top_artist_share=top_artist_share,
        top3_share=top3_share,
        duplicate_tracks=duplicate_tracks,
        release_year_distribution=release_year_distribution,
        explicit_share=explicit_share,
        genre_distribution=genre_distribution,
    )
