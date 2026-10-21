"""
Fallback template roast generator.
Used when the Gemini API is unreachable, rate limited, or returns malformed output.
Builds grounded, hilarious roasts purely from real playlist statistics.
"""

from __future__ import annotations

from typing import Any

from apps.analysis.models import PlaylistStats, Score
from apps.roasting.schema import validate_roast_report


def generate_fallback_roast(
    stats: PlaylistStats,
    scores: list[Score],
    intensity: str = "savage",
    playlist_title: str | None = None,
) -> dict[str, Any]:
    """
    Generate a deterministic fallback roast report based on stats and intensity.
    Guarantees that every observation and roast cites real numbers.
    """
    intensity = intensity.lower()
    if intensity not in ("mild", "savage", "nuclear"):
        intensity = "savage"

    title = playlist_title or "Untitled Playlist"
    top_artist_name = (
        stats.top_artists[0].name if stats.top_artists else "Unknown Artist"
    )
    top_artist_count = stats.top_artists[0].count if stats.top_artists else 0
    top_share_pct = round(stats.top_artist_share * 100, 1)

    # Build grounded observations directly from verified facts.
    observations: list[str] = [
        f"{top_artist_count} of {stats.track_count} tracks come from {top_artist_name} ({top_share_pct}%).",
        f"Only {stats.unique_artist_count} unique artists show up across the entire playlist.",
    ]

    if stats.duplicate_tracks:
        dup_names = ", ".join(stats.duplicate_tracks[:2])
        observations.append(
            f"You have {len(stats.duplicate_tracks)} duplicate songs on repeat, including {dup_names}."
        )
    elif stats.release_year_distribution and len(stats.release_year_distribution) > 1:
        years = list(stats.release_year_distribution.keys())
        observations.append(
            f"Your music history spans from {min(years)} to {max(years)}."
        )
    else:
        top3_pct = round(stats.top3_share * 100, 1)
        observations.append(
            f"Your top 3 artists control {top3_pct}% of the whole rotation."
        )

    # Determine angle based on statistics.
    is_obsessed = stats.top_artist_share >= 0.3
    has_duplicates = bool(stats.duplicate_tracks)
    is_scattered = (
        stats.track_count > 5
        and (stats.unique_artist_count / max(stats.track_count, 1)) > 0.8
    )

    if intensity == "mild":
        if is_obsessed:
            headline = "Comfort Zone Champion"
            personality = "The Dedicated Disciple"
            roast = (
                f"You really found your comfort artist in {top_artist_name} and "
                f"decided {top_share_pct}% of your listening was set in stone. "
                f"There is loyalty, and then there is whatever this is."
            )
            verdict = f"A cozy shrine to {top_artist_name} with a few guest stars."
        elif is_scattered:
            headline = "The Musical Butterfly"
            personality = "The Genre Hopper"
            roast = (
                f"With {stats.unique_artist_count} unique artists across {stats.track_count} tracks, "
                f"your attention span is having a great time. Every track is a new adventure."
            )
            verdict = "Never predictable, always keeping your speakers guessing."
        else:
            headline = "The Safe Playlist Curator"
            personality = "The Casual Listener"
            roast = (
                f"A pleasant, safe collection of {stats.track_count} tracks. "
                f"It won't start a riot, but it won't clear the dancefloor either."
            )
            verdict = "Harmonious background music for everyday life."

    elif intensity == "nuclear":
        if is_obsessed:
            headline = "Clinically obsessed, shuffle button is screaming"
            personality = "The Monomaniacal Cult President"
            roast = (
                f"{top_artist_count} tracks from {top_artist_name} out of {stats.track_count}? "
                f"That is {top_share_pct}% pure, unfiltered hyperfixation. If Spotify charged you rent per artist, "
                f"you would be facing immediate eviction. Your shuffle button needs trauma therapy."
            )
            verdict = f"Legally married to {top_artist_name}'s discography. Everyone else is trespassing."
        elif has_duplicates:
            headline = "Severe short-term musical memory loss"
            personality = "The Infinite Looper"
            roast = (
                f"You literally put {len(stats.duplicate_tracks)} duplicate songs onto a {stats.track_count} track playlist. "
                f"Do you forget you just heard it, or do you require sonic waterboarding to feel anything?"
            )
            verdict = "Repeat button abuse in the first degree."
        else:
            headline = "Auditory whiplash with zero coherent identity"
            personality = "The Sonic Tornado"
            roast = (
                f"You jammed {stats.unique_artist_count} different artists into {stats.track_count} tracks. "
                f"This playlist has the emotional consistency of a microwave timer. Pick a lane or hand over the aux."
            )
            verdict = "Chaotic evil in playlist form."

    else:  # savage (default)
        if is_obsessed:
            headline = "Your shuffle button needs a lawyer"
            personality = "The Dedicated Fan Club President"
            roast = (
                f"{top_artist_count} of your {stats.track_count} tracks come from {top_artist_name}? "
                f"That is {top_share_pct}% of the entire list. This is less a playlist and more an "
                f"unpaid internship in the fan club. Your shuffle button is fighting for its life."
            )
            verdict = f"Your playlist has commitment issues with everyone except {top_artist_name}."
        elif has_duplicates:
            headline = "Stuck in an infinite acoustic loop"
            personality = "The Broken Record"
            roast = (
                f"Putting {len(stats.duplicate_tracks)} duplicate tracks into a single playlist is bold. "
                f"Your repeat button is doing heavy lifting that no algorithm asked for."
            )
            verdict = "Your playlist repeats itself because you refuse to move on."
        elif is_scattered:
            headline = "Commitment issues in audio format"
            personality = "The Identity Tourist"
            roast = (
                f"{stats.unique_artist_count} unique artists in {stats.track_count} songs. "
                f"You refuse to stay with one sound for more than four minutes. "
                f"It is not eclectic taste, it is an inability to commit to a vibe."
            )
            verdict = "A sonic mood board that cannot agree on what room it is decorating."
        else:
            headline = "Algorithmically groomed taste"
            personality = "The Playlist Conformist"
            roast = (
                f"{stats.track_count} tracks, nicely distributed, perfectly predictable. "
                f"It looks like an automated weekly mix generated by a server that wanted to avoid complaints."
            )
            verdict = "Tastefully boring. Safe for dentists' waiting rooms everywhere."

    meta_line = (
        f"{stats.track_count} tracks, {stats.unique_artist_count} unique artists, "
        f"{top_artist_count} tracks from {top_artist_name} ({top_share_pct}%)."
    )

    report_dict = {
        "headline": headline,
        "personality": personality,
        "meta_line": meta_line,
        "observations": observations,
        "roast": roast,
        "final_verdict": verdict,
    }

    return validate_roast_report(
        report_dict,
        fallback_scores=scores,
        intensity=intensity,
        meta_line=meta_line,
    )
