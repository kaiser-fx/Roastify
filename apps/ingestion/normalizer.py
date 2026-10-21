"""
Normalizer: converts raw Spotify API response data into our Playlist dataclass.
Provider data goes in, clean Playlist comes out.
Never invents metadata. If a field is missing, it stays None.
"""

from __future__ import annotations

from typing import Any

from apps.analysis.models import Playlist, Track


def normalize_spotify_response(raw: dict[str, Any]) -> Playlist:
    """
    Convert a raw Spotify API playlist response to a Playlist dataclass.
    """
    tracks_data = raw.get("tracks", {})
    items = tracks_data.get("items", [])

    tracks: list[Track] = []
    for item in items:
        track_obj = item.get("track")
        if not track_obj:
            continue

        # Extract artist names, skip if missing.
        artists_raw = track_obj.get("artists", [])
        artists = [
            a.get("name", "").strip()
            for a in artists_raw
            if a.get("name", "").strip()
        ]

        title = (track_obj.get("name") or "").strip()
        if not title:
            continue

        # Album info (optional).
        album_obj = track_obj.get("album", {})
        album = (album_obj.get("name") or "").strip() or None
        release_date = (album_obj.get("release_date") or "").strip() or None

        # Duration.
        duration_ms = track_obj.get("duration_ms")
        if duration_ms is not None:
            try:
                duration_ms = int(duration_ms)
            except (ValueError, TypeError):
                duration_ms = None

        # Explicit flag.
        explicit = track_obj.get("explicit")
        if explicit is not None:
            explicit = bool(explicit)

        # Source URL.
        external_urls = track_obj.get("external_urls", {})
        source_url = external_urls.get("spotify") or None

        tracks.append(Track(
            title=title,
            artists=artists if artists else ["Unknown Artist"],
            album=album,
            release_date=release_date,
            duration_ms=duration_ms,
            explicit=explicit,
            source_url=source_url,
        ))

    # Playlist-level metadata.
    playlist_title = (raw.get("name") or "").strip() or None
    ext_urls = raw.get("external_urls", {})
    source_url = ext_urls.get("spotify") or None

    return Playlist(
        source="spotify",
        tracks=tracks,
        title=playlist_title,
        source_url=source_url,
    )
