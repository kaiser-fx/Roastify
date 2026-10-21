"""
Typed ingestion errors.
Each error maps to an error code returned in the API response,
telling the frontend what happened and whether to offer the manual fallback.
"""


class IngestionError(Exception):
    """Base class for ingestion errors."""

    code: str = "UPSTREAM_ERROR"
    fallback: str = "manual"

    def __init__(self, message: str = "") -> None:
        self.message = message or self._default_message()
        super().__init__(self.message)

    def _default_message(self) -> str:
        return "Something went wrong while fetching the playlist."


class InvalidURLError(IngestionError):
    """The URL is not a valid Spotify playlist link."""

    code = "INVALID_URL"
    fallback = ""

    def _default_message(self) -> str:
        return (
            "That does not look like a valid Spotify playlist URL. "
            "Expected a link like https://open.spotify.com/playlist/..."
        )


class PlaylistPrivateError(IngestionError):
    """The playlist exists but is private or not accessible."""

    code = "PLAYLIST_PRIVATE"

    def _default_message(self) -> str:
        return (
            "That playlist appears to be private or unavailable. "
            "Try a public playlist, or paste your tracks manually."
        )


class AccessRestrictedError(IngestionError):
    """Spotify blocked access (API restrictions, missing scopes)."""

    code = "ACCESS_RESTRICTED"

    def _default_message(self) -> str:
        return (
            "Spotify is not allowing us to read playlist tracks right now. "
            "This is a known limitation. Paste your tracks below instead."
        )


class PlaylistTooLargeError(IngestionError):
    """The playlist exceeds the maximum allowed track count."""

    code = "PLAYLIST_TOO_LARGE"
    fallback = ""

    def _default_message(self) -> str:
        return (
            "That playlist has too many tracks. "
            "Try a shorter playlist (under 200 tracks)."
        )


class EmptyPlaylistError(IngestionError):
    """The playlist has no tracks or tracks cannot be read."""

    code = "EMPTY_PLAYLIST"
    fallback = "manual"

    def _default_message(self) -> str:
        return (
            "We could not read any tracks from that playlist. "
            "Spotify may have restricted access to it, or it is private. "
            "Paste your tracks below instead."
        )


class UpstreamError(IngestionError):
    """Spotify or another upstream service returned an unexpected error."""

    code = "UPSTREAM_ERROR"

    def _default_message(self) -> str:
        return (
            "Something went wrong while talking to Spotify. "
            "Try again in a moment, or paste your tracks manually."
        )
