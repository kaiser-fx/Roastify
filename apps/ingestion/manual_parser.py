"""
Manual track list and CSV parsers.

Pasted text format: one track per line, "Title - Artist" (multiple artists
separated by commas).

CSV upload with columns: title, artist. Optional: album, release_date.

All input is treated as untrusted. Hard caps on file size and row count.
"""

from __future__ import annotations

import csv
import io
from typing import BinaryIO

from django.conf import settings

from apps.analysis.models import Playlist, Track
from apps.ingestion.errors import EmptyPlaylistError, InvalidURLError

# Limits for untrusted input.
_MAX_TEXT_LENGTH = 50_000  # characters
_MAX_CSV_SIZE = 512_000  # bytes (500 KB)
_MAX_LINE_LENGTH = 500  # characters per line


def parse_track_list(text: str) -> Playlist:
    """
    Parse a pasted track list into a Playlist.

    Each line should be: Title - Artist
    Artists can be separated by commas.
    Blank lines are skipped.
    """
    if not text or not text.strip():
        raise EmptyPlaylistError("Paste at least one track (Title - Artist).")

    if len(text) > _MAX_TEXT_LENGTH:
        raise InvalidURLError(
            f"The pasted text is too long (max {_MAX_TEXT_LENGTH:,} characters)."
        )

    max_tracks = getattr(settings, "MAX_PLAYLIST_TRACKS", 200)
    tracks: list[Track] = []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > _MAX_LINE_LENGTH:
            line = line[:_MAX_LINE_LENGTH]

        # Split on the first " - " separator.
        if " - " in line:
            title_part, artist_part = line.split(" - ", 1)
        elif " – " in line:
            # Handle en-dash as a common alternative.
            title_part, artist_part = line.split(" – ", 1)
        else:
            # No separator: treat the whole line as a title.
            title_part = line
            artist_part = ""

        title = title_part.strip()
        if not title:
            continue

        artists = [
            a.strip() for a in artist_part.split(",") if a.strip()
        ] if artist_part.strip() else ["Unknown Artist"]

        tracks.append(Track(title=title, artists=artists))

        if len(tracks) >= max_tracks:
            break

    if not tracks:
        raise EmptyPlaylistError("No valid tracks found. Use the format: Title - Artist")

    return Playlist(source="manual", tracks=tracks)


def parse_csv(file_obj: BinaryIO, filename: str = "upload.csv") -> Playlist:
    """
    Parse a CSV file into a Playlist.

    Expected columns: title, artist. Optional: album, release_date.
    The first row is treated as a header.
    """
    # Read with size limit.
    raw = file_obj.read(_MAX_CSV_SIZE + 1)
    if len(raw) > _MAX_CSV_SIZE:
        raise InvalidURLError(
            f"The CSV file is too large (max {_MAX_CSV_SIZE // 1000} KB)."
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            raise InvalidURLError("Could not read the CSV file. Check the encoding.")

    max_tracks = getattr(settings, "MAX_PLAYLIST_TRACKS", 200)
    tracks: list[Track] = []

    reader = csv.DictReader(io.StringIO(text))

    # Normalize header names to lowercase.
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

    if not reader.fieldnames or "title" not in reader.fieldnames:
        raise InvalidURLError(
            "The CSV must have at least a 'title' column. "
            "Optional columns: artist, album, release_date."
        )

    for row in reader:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        if len(title) > _MAX_LINE_LENGTH:
            title = title[:_MAX_LINE_LENGTH]

        artist_raw = (row.get("artist") or row.get("artists") or "").strip()
        artists = [
            a.strip() for a in artist_raw.split(",") if a.strip()
        ] if artist_raw else ["Unknown Artist"]

        album = (row.get("album") or "").strip() or None
        release_date = (row.get("release_date") or "").strip() or None

        tracks.append(Track(
            title=title,
            artists=artists,
            album=album,
            release_date=release_date,
        ))

        if len(tracks) >= max_tracks:
            break

    if not tracks:
        raise EmptyPlaylistError(
            "No valid tracks found in the CSV. "
            "Make sure it has a 'title' column."
        )

    return Playlist(source="manual", tracks=tracks)
