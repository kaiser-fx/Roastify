"""
Public Spotify playlist scraper.

Extracts playlist metadata and tracks from Spotify public web pages
without requiring user login or account linking.

Spotify serves public playlist preview data through:
1. The embed player page at open.spotify.com/embed/playlist/<id>
2. The web player page at open.spotify.com/playlist/<id>

This module extracts the structured JSON payload embedded in those pages.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

from apps.ingestion.errors import (
    EmptyPlaylistError,
    PlaylistPrivateError,
    PlaylistTooLargeError,
    UpstreamError,
)

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _fetch_from_embed(playlist_id: str) -> dict[str, Any] | None:
    """
    Attempt to extract playlist data from the Spotify embed player page.
    """
    embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    req = urllib.request.Request(
        embed_url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise PlaylistPrivateError("This playlist is private or does not exist.")
        logger.warning("Spotify embed HTTP %s for %s", exc.code, playlist_id)
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("Spotify embed network error for %s: %s", playlist_id, exc)
        return None

    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return None

    entity = (
        data.get("props", {})
        .get("pageProps", {})
        .get("state", {})
        .get("data", {})
        .get("entity", {})
    )
    if not entity:
        return None

    title = entity.get("title") or entity.get("name") or "Spotify Playlist"
    raw_tracks = entity.get("trackList") or []
    if not raw_tracks:
        return None

    items: list[dict[str, Any]] = []
    for t in raw_tracks:
        track_title = (t.get("title") or "").strip()
        if not track_title:
            continue

        subtitle = (t.get("subtitle") or "").replace("\xa0", " ")
        artists = [a.strip() for a in subtitle.split(",") if a.strip()]
        if not artists:
            artists = ["Unknown Artist"]

        uri = t.get("uri") or ""
        track_id = uri.split(":")[-1] if uri else ""
        track_url = f"https://open.spotify.com/track/{track_id}" if track_id else None

        duration_ms = t.get("duration")
        if duration_ms is not None:
            try:
                duration_ms = int(duration_ms)
            except (ValueError, TypeError):
                duration_ms = None

        explicit = t.get("isExplicit")
        if explicit is not None:
            explicit = bool(explicit)

        items.append({
            "track": {
                "name": track_title,
                "artists": [{"name": a} for a in artists],
                "album": {"name": None, "release_date": None},
                "duration_ms": duration_ms,
                "explicit": explicit,
                "external_urls": {"spotify": track_url} if track_url else {},
            }
        })

    if not items:
        return None

    return {
        "name": title,
        "external_urls": {"spotify": f"https://open.spotify.com/playlist/{playlist_id}"},
        "tracks": {
            "total": len(items),
            "items": items,
        },
    }


def _fetch_from_web_player(playlist_id: str) -> dict[str, Any] | None:
    """
    Attempt to extract playlist data from the Spotify web player HTML.
    """
    web_url = f"https://open.spotify.com/playlist/{playlist_id}"
    req = urllib.request.Request(
        web_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise PlaylistPrivateError("This playlist is private or does not exist.")
        logger.warning("Spotify web player HTTP %s for %s", exc.code, playlist_id)
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("Spotify web player network error for %s: %s", playlist_id, exc)
        return None

    match = re.search(r'<script id="initialState"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None

    try:
        raw_b64 = match.group(1).strip()
        decoded_json = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
        state_data = json.loads(decoded_json)
    except (ValueError, json.JSONDecodeError):
        return None

    items_dict = state_data.get("entities", {}).get("items", {})
    pl_data = None
    target_key = f"spotify:playlist:{playlist_id}"
    if target_key in items_dict:
        pl_data = items_dict[target_key]
    else:
        for k, v in items_dict.items():
            if isinstance(v, dict) and "content" in v:
                pl_data = v
                break

    if not pl_data or not isinstance(pl_data, dict):
        return None

    title = pl_data.get("name") or "Spotify Playlist"
    content_items = pl_data.get("content", {}).get("items", [])
    if not content_items:
        return None

    items: list[dict[str, Any]] = []
    for it in content_items:
        t_data = it.get("itemV2", {}).get("data", {})
        if not t_data:
            continue

        track_title = (t_data.get("name") or "").strip()
        if not track_title:
            continue

        artist_items = t_data.get("artists", {}).get("items", [])
        artists = [
            a.get("profile", {}).get("name")
            for a in artist_items
            if a.get("profile", {}).get("name")
        ]
        if not artists:
            artists = ["Unknown Artist"]

        album_name = t_data.get("albumOfTrack", {}).get("name")
        duration_ms = t_data.get("trackDuration", {}).get("totalMilliseconds")
        tid = t_data.get("id") or ""
        track_url = f"https://open.spotify.com/track/{tid}" if tid else None

        items.append({
            "track": {
                "name": track_title,
                "artists": [{"name": a} for a in artists],
                "album": {"name": album_name, "release_date": None},
                "duration_ms": duration_ms,
                "explicit": None,
                "external_urls": {"spotify": track_url} if track_url else {},
            }
        })

    if not items:
        return None

    return {
        "name": title,
        "external_urls": {"spotify": f"https://open.spotify.com/playlist/{playlist_id}"},
        "tracks": {
            "total": len(items),
            "items": items,
        },
    }


def fetch_public_playlist_data(playlist_id: str) -> dict[str, Any]:
    """
    Extract public playlist data using the embed player or web player.
    Raises PlaylistPrivateError, EmptyPlaylistError, or PlaylistTooLargeError.
    """
    max_tracks = getattr(settings, "MAX_PLAYLIST_TRACKS", 100)

    # 1. Try embed player first (fast, structured, up to 100 tracks).
    data = _fetch_from_embed(playlist_id)

    # 2. Try web player initialState if embed player had no tracks.
    if not data:
        data = _fetch_from_web_player(playlist_id)

    if not data or not data.get("tracks", {}).get("items"):
        raise EmptyPlaylistError(
            "Spotify returned no tracks for this playlist. "
            "It may be private or empty. Paste your tracks instead."
        )

    total = data["tracks"].get("total", len(data["tracks"]["items"]))
    if total > max_tracks:
        raise PlaylistTooLargeError(
            f"That playlist has {total} tracks, which is over the "
            f"{max_tracks} track limit. Try a shorter playlist."
        )

    # Cap items to max_tracks.
    data["tracks"]["items"] = data["tracks"]["items"][:max_tracks]
    return data
