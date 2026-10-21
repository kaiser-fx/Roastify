"""
Track and Playlist dataclasses.
Plain Python dataclasses, not Django models, because nothing is stored in the MVP.
See PRD section 9 for the data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Track:
    """A single track with metadata from any source."""

    title: str
    artists: list[str]
    album: str | None = None
    release_date: str | None = None
    genres: list[str] | None = None
    duration_ms: int | None = None
    explicit: bool | None = None
    source_url: str | None = None


@dataclass
class Playlist:
    """A collection of tracks from a single source."""

    source: str  # "spotify" or "manual"
    tracks: list[Track] = field(default_factory=list)
    title: str | None = None
    source_url: str | None = None


@dataclass
class ArtistShare:
    """Statistics for an artist appearing in a playlist."""

    name: str
    count: int
    share: float  # Percentage ratio between 0.0 and 1.0


@dataclass
class Score:
    """Entertainment score with a label and clamped 0-100 value."""

    label: str
    value: int


@dataclass
class PlaylistStats:
    """
    Pure statistical summary of a playlist.
    Computed deterministically from Track data.
    Fields absent from provider data remain None.
    """

    track_count: int
    unique_artist_count: int
    top_artists: list[ArtistShare] = field(default_factory=list)
    top_artist_share: float = 0.0
    top3_share: float = 0.0
    duplicate_tracks: list[str] = field(default_factory=list)
    release_year_distribution: dict[int, int] | None = None
    explicit_share: float | None = None
    genre_distribution: dict[str, int] | None = None
