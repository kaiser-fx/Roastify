"""
Entertainment score formulas for Roastify.
All scores are clamped between 0 and 100.
Formulas are deterministic pure functions designed for entertainment only.
"""

from __future__ import annotations

from apps.analysis.models import PlaylistStats, Score


def _clamp(value: float) -> int:
    """Clamp a floating point value to an integer between 0 and 100."""
    return max(0, min(100, int(round(value))))


def calculate_artist_obsession(stats: PlaylistStats) -> int:
    """
    Calculate the Artist Obsession score (0 to 100).

    Formula rationale:
    Measures how heavily the playlist leans on its single favorite artist
    and the overall lack of artist diversity.

    Components:
    1. Top artist share (70% weight): scaled directly from top_artist_share.
       A top artist with 50% of tracks provides 50 / 0.6 * 0.7 = ~58 points.
    2. Concentration factor (30% weight):
       Calculated from 1.0 minus (unique_artist_count / track_count).
       If every track is a different artist, concentration is 0.
       If every track is the same artist, concentration is 1.

    Edge cases:
    - Empty playlist: returns 0.
    - Single track: returns 25 (a single track is not enough to prove obsession).
    """
    if stats.track_count == 0:
        return 0

    if stats.track_count == 1:
        return 25

    # 1. Share factor (0.0 to 1.0, scaled so 60% share hits near maximum)
    share_factor = min(1.0, stats.top_artist_share / 0.6)

    # 2. Diversity factor
    diversity_ratio = stats.unique_artist_count / stats.track_count
    concentration = 1.0 - diversity_ratio

    raw = (share_factor * 70.0) + (concentration * 30.0)
    return _clamp(raw)


def calculate_main_character_energy(stats: PlaylistStats) -> int:
    """
    Calculate the Main Character Energy score (0 to 100).

    Formula rationale:
    Measures cinematic playlist concentration, high top 3 artist dominance,
    and repetition of signature anthems.

    Components:
    1. Top 3 artist dominance (55% weight):
       Scaled from top3_share. A playlist where top 3 artists control 75%
       reaches full points in this component.
    2. Duplicate tracks bonus (25% weight):
       Listeners repeating the exact same songs have elevated main character energy.
       Presence of duplicate tracks adds up to 25 points.
    3. Baseline confidence (20% weight):
       Playlists with at least 15 tracks receive the full baseline points.

    Edge cases:
    - Empty playlist: returns 0.
    - Single track: returns 30.
    """
    if stats.track_count == 0:
        return 0

    if stats.track_count == 1:
        return 30

    # 1. Top 3 dominance (scaled so 75% share gets 1.0)
    top3_factor = min(1.0, stats.top3_share / 0.75)

    # 2. Duplicate tracks factor
    dup_count = len(stats.duplicate_tracks)
    dup_factor = min(1.0, dup_count / 3.0)

    # 3. Playlist volume factor (peaks at 20 tracks)
    volume_factor = min(1.0, stats.track_count / 20.0)

    raw = (top3_factor * 55.0) + (dup_factor * 25.0) + (volume_factor * 20.0)
    return _clamp(raw)


def calculate_emotional_damage(stats: PlaylistStats) -> int:
    """
    Calculate the Emotional Damage score (0 to 100).

    Formula rationale:
    Measures signs of emotional looping, repetitive listening,
    vintage year clustering, and intense artist focus.

    Components:
    1. Looping and repetition (40% weight):
       Derived from top artist share and duplicate tracks.
    2. Era clustering (35% weight):
       If release dates exist, checks whether tracks are clustered
       in a tight span (e.g. within 4 years) or older nostalgic eras.
       If dates are absent, substitutes artist concentration.
    3. Monotony factor (25% weight):
       Low unique artist count relative to track count.

    Edge cases:
    - Empty playlist: returns 0.
    - Single track: returns 20.
    """
    if stats.track_count == 0:
        return 0

    if stats.track_count == 1:
        return 20

    # 1. Looping factor: high top artist share + duplicates
    dup_count = len(stats.duplicate_tracks)
    looping = min(1.0, (stats.top_artist_share * 0.7) + (dup_count * 0.15))

    # 2. Era clustering factor
    era_factor = 0.5  # Neutral default
    if stats.release_year_distribution and len(stats.release_year_distribution) > 0:
        years = list(stats.release_year_distribution.keys())
        year_span = max(years) - min(years)
        # Tight time span indicates hyperfixating on a specific era
        if year_span <= 3:
            era_factor = 0.9
        elif year_span <= 7:
            era_factor = 0.7
        else:
            era_factor = 0.4
    else:
        # Fallback to top3 share if no release years available
        era_factor = min(1.0, stats.top3_share)

    # 3. Monotony factor
    monotony = 1.0 - (stats.unique_artist_count / stats.track_count)

    raw = (looping * 40.0) + (era_factor * 35.0) + (monotony * 25.0)
    return _clamp(raw)


def calculate_scores(stats: PlaylistStats) -> list[Score]:
    """
    Calculate all three entertainment scores for a playlist summary.
    Returns a list of Score objects ready for display in the UI or report.
    """
    return [
        Score(
            label="Artist obsession",
            value=calculate_artist_obsession(stats),
        ),
        Score(
            label="Main character energy",
            value=calculate_main_character_energy(stats),
        ),
        Score(
            label="Emotional damage",
            value=calculate_emotional_damage(stats),
        ),
    ]
