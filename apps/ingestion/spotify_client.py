"""
Spotify Web API adapter.

Uses the Client Credentials flow for app-level access. As of 2026, Spotify
restricts playlist track endpoints to user-authenticated flows, so calls to
fetch playlist tracks will likely return 401/403. The adapter handles this
gracefully by raising AccessRestrictedError, and the API layer offers the
manual fallback.

If Spotify changes access rules, the token handling and fetch logic here
are ready to support it. Switching to Authorization Code flow would require
adding user login, which is out of scope for the MVP.

Only this module talks to Spotify. The API key stays server side.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import urllib.request
import urllib.error
import urllib.parse
import json

from django.conf import settings

from apps.ingestion.errors import (
    AccessRestrictedError,
    EmptyPlaylistError,
    PlaylistPrivateError,
    PlaylistTooLargeError,
    UpstreamError,
)

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"

# Module-level token cache (single process, good enough for dev).
_cached_token: str | None = None
_token_expires_at: float = 0.0

_REQUEST_TIMEOUT = 10  # seconds
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds, multiplied by attempt number


def _get_client_credentials_token() -> str:
    """
    Obtain an access token using the Client Credentials flow.
    Caches the token until it expires.
    """
    global _cached_token, _token_expires_at

    if _cached_token and time.time() < _token_expires_at - 60:
        return _cached_token

    client_id = (getattr(settings, "SPOTIFY_CLIENT_ID", "") or "").strip()
    client_secret = (getattr(settings, "SPOTIFY_CLIENT_SECRET", "") or "").strip()

    if not client_id or not client_secret:
        raise AccessRestrictedError(
            "Spotify API credentials are not configured. "
            "Paste your tracks manually instead."
        )

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
    }).encode("utf-8")

    # Basic auth header with client_id:client_secret.
    import base64
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    req = urllib.request.Request(
        _TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error("Spotify token request failed: %s", e.code)
        raise AccessRestrictedError(
            "Could not authenticate with Spotify. "
            "Paste your tracks manually instead."
        )
    except (urllib.error.URLError, TimeoutError) as e:
        logger.error("Spotify token request error: %s", e)
        raise UpstreamError("Could not reach Spotify. Try again in a moment.")

    _cached_token = body.get("access_token", "")
    expires_in = body.get("expires_in", 3600)
    _token_expires_at = time.time() + expires_in
    return _cached_token


def _api_get(path: str, token: str) -> dict[str, Any]:
    """
    Make a GET request to the Spotify Web API with retries and backoff.
    """
    url = f"{_API_BASE}{path}"

    for attempt in range(1, _MAX_RETRIES + 1):
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 401 or status == 403:
                raise AccessRestrictedError()
            if status == 404:
                raise PlaylistPrivateError()
            if status == 429:
                retry_after = int(e.headers.get("Retry-After", "2"))
                if attempt < _MAX_RETRIES:
                    time.sleep(min(retry_after, 5))
                    continue
                raise UpstreamError(
                    "Spotify is rate limiting us. Try again in a moment."
                )
            logger.error("Spotify API error %s on %s", status, path)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF * attempt)
                continue
            raise UpstreamError()
        except (urllib.error.URLError, TimeoutError) as e:
            logger.error("Spotify API network error: %s", e)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF * attempt)
                continue
            raise UpstreamError(
                "Could not reach Spotify. Try again in a moment."
            )

    raise UpstreamError()


def fetch_playlist(playlist_id: str) -> dict[str, Any]:
    """
    Fetch a playlist and its tracks.

    First attempts extraction directly from Spotify public preview pages so the
    user does not need to link a Spotify account or authorize OAuth.

    Falls back to the official Spotify Web API if public extraction encounters
    an issue.
    """
    # 1. Frictionless public scraper (no account linking needed).
    try:
        from apps.ingestion.public_scraper import fetch_public_playlist_data
        public_data = fetch_public_playlist_data(playlist_id)
        if public_data and public_data.get("tracks", {}).get("items"):
            return public_data
    except (PlaylistPrivateError, PlaylistTooLargeError):
        raise
    except EmptyPlaylistError:
        pass
    except Exception as exc:
        logger.info("Public scraper fallback to official API: %s", exc)

    # 2. Official Web API fallback.
    token = _get_client_credentials_token()
    max_tracks = settings.MAX_PLAYLIST_TRACKS

    # Fetch playlist metadata and first page of tracks without brittle fields filter.
    playlist_data = _api_get(f"/playlists/{playlist_id}", token)

    tracks_section = playlist_data.get("tracks") or {}
    all_items = tracks_section.get("items") or []
    total = tracks_section.get("total") or len(all_items)
    next_url = tracks_section.get("next")

    # If the playlist object omitted tracks, attempt querying the tracks endpoint directly.
    if not all_items:
        try:
            tracks_resp = _api_get(f"/playlists/{playlist_id}/tracks?limit=100", token)
            all_items = tracks_resp.get("items") or []
            total = tracks_resp.get("total") or len(all_items)
            next_url = tracks_resp.get("next")
            playlist_data["tracks"] = {"total": total, "items": all_items, "next": next_url}
        except Exception:
            pass

    if not all_items:
        raise EmptyPlaylistError(
            "Spotify returned no tracks for this playlist. "
            "It may be private, restricted by Spotify, or empty. "
            "Paste your tracks manually instead."
        )

    if total > max_tracks:
        raise PlaylistTooLargeError(
            f"That playlist has {total} tracks, which is over the "
            f"{max_tracks} track limit. Try a shorter playlist."
        )

    # Collect additional pages up to max_tracks if needed.
    while next_url and len(all_items) < max_tracks:
        path = next_url.replace(_API_BASE, "")
        page = _api_get(path, token)
        all_items.extend(page.get("items", []))
        next_url = page.get("next")

    playlist_data["tracks"]["items"] = all_items[:max_tracks]
    return playlist_data
