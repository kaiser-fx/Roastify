"""
Spotify playlist URL validator.
Accepts only open.spotify.com playlist URLs and spotify:playlist: URIs.
Extracts the playlist ID with a strict regex.
Rejects every other host, scheme, or path (SSRF prevention).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from apps.ingestion.errors import InvalidURLError

# Playlist IDs are base-62 strings, typically 22 characters.
_PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{15,30}$")

# open.spotify.com/playlist/{id} with optional query and fragment.
_WEB_URL_PATTERN = re.compile(
    r"^/playlist/(?P<id>[A-Za-z0-9]{15,30})(?:/.*)?$"
)

# spotify:playlist:{id} URI form.
_URI_PATTERN = re.compile(
    r"^spotify:playlist:(?P<id>[A-Za-z0-9]{15,30})$"
)

# Maximum URL length to prevent abuse.
_MAX_URL_LENGTH = 300


def extract_playlist_id(raw_url: str) -> str:
    """
    Validate a Spotify playlist URL or URI and return the playlist ID.

    Raises InvalidURLError for anything that is not an allowed format.
    """
    url = raw_url.strip()

    if not url:
        raise InvalidURLError("Please enter a Spotify playlist URL.")

    if len(url) > _MAX_URL_LENGTH:
        raise InvalidURLError("That URL is too long.")

    # Try the spotify:playlist:ID URI form first.
    uri_match = _URI_PATTERN.match(url)
    if uri_match:
        return uri_match.group("id")

    # Parse as a web URL.
    try:
        parsed = urlparse(url)
    except ValueError:
        raise InvalidURLError()

    # Only allow HTTPS (or HTTP for dev convenience) on the exact host.
    if parsed.scheme not in ("https", "http"):
        raise InvalidURLError()

    if parsed.hostname != "open.spotify.com":
        raise InvalidURLError(
            "Only open.spotify.com playlist URLs are supported."
        )

    # Match the path.
    path_match = _WEB_URL_PATTERN.match(parsed.path)
    if not path_match:
        raise InvalidURLError(
            "That URL does not point to a Spotify playlist. "
            "Expected a link like https://open.spotify.com/playlist/..."
        )

    return path_match.group("id")
