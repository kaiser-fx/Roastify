"""
API views. JSON endpoints for the roast workflow.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.analysis.models import Playlist, PlaylistStats, Score
from apps.analysis.scoring import calculate_scores
from apps.analysis.stats import calculate_playlist_stats
from apps.roasting.llm_client import generate_roast
from apps.api.throttling import get_client_ip, is_rate_limited
from apps.ingestion.errors import (
    AccessRestrictedError,
    EmptyPlaylistError,
    IngestionError,
    InvalidURLError,
    PlaylistPrivateError,
    PlaylistTooLargeError,
    UpstreamError,
)
from apps.ingestion.manual_parser import parse_csv, parse_track_list
from apps.ingestion.normalizer import normalize_spotify_response
from apps.ingestion.spotify_client import fetch_playlist
from apps.ingestion.url_validator import extract_playlist_id

logger = logging.getLogger(__name__)

# Map error codes to HTTP status codes.
_ERROR_STATUS_MAP: dict[str, int] = {
    "INVALID_URL": 400,
    "EMPTY_PLAYLIST": 400,
    "PLAYLIST_TOO_LARGE": 400,
    "PLAYLIST_PRIVATE": 404,
    "ACCESS_RESTRICTED": 403,
    "RATE_LIMITED": 429,
    "UPSTREAM_ERROR": 502,
}


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Simple health check endpoint."""
    return JsonResponse({"status": "ok"})


def _serialize_playlist(playlist: Playlist) -> dict[str, Any]:
    """Serialize Playlist dataclass to a JSON-safe dictionary."""
    return {
        "title": playlist.title or "Untitled Playlist",
        "track_count": len(playlist.tracks),
        "source": playlist.source,
        "source_url": playlist.source_url,
        "tracks": [
            {
                "title": t.title,
                "artists": t.artists,
                "album": t.album,
                "release_date": t.release_date,
                "duration_ms": t.duration_ms,
                "explicit": t.explicit,
                "source_url": t.source_url,
            }
            for t in playlist.tracks
        ],
    }


def _serialize_stats(stats: PlaylistStats) -> dict[str, Any]:
    """Serialize PlaylistStats dataclass to a JSON-safe dictionary."""
    return {
        "track_count": stats.track_count,
        "unique_artist_count": stats.unique_artist_count,
        "top_artists": [
            {"name": a.name, "count": a.count, "share": a.share}
            for a in stats.top_artists
        ],
        "top_artist_share": stats.top_artist_share,
        "top3_share": stats.top3_share,
        "duplicate_tracks": stats.duplicate_tracks,
        "release_year_distribution": stats.release_year_distribution,
        "explicit_share": stats.explicit_share,
        "genre_distribution": stats.genre_distribution,
    }


def _serialize_scores(scores: list[Score]) -> list[dict[str, Any]]:
    """Serialize Score list to JSON-safe dictionary format."""
    return [{"label": s.label, "value": s.value} for s in scores]


@require_POST
def roast(request: HttpRequest) -> JsonResponse:
    """
    Handle playlist ingestion, stats computation, and scoring for roasting.
    Supports JSON body and multipart/form-data (for CSV uploads).
    Returns normalized playlist, stats, and scores.
    """
    client_ip = get_client_ip(request)
    if is_rate_limited(client_ip):
        return JsonResponse(
            {
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please wait a minute and try again.",
                    "fallback": "",
                }
            },
            status=429,
        )

    # Extract input parameters from JSON or form data.
    content_type = request.content_type or ""
    source = ""
    url = ""
    tracks_text = ""
    intensity = "savage"
    csv_file = None

    if "application/json" in content_type:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {
                    "error": {
                        "code": "INVALID_URL",
                        "message": "Invalid JSON request body.",
                        "fallback": "",
                    }
                },
                status=400,
            )
        source = body.get("source", "").strip()
        url = body.get("url", "").strip()
        tracks_text = body.get("tracks_text", "")
        intensity = body.get("intensity", "savage").strip() or "savage"
    else:
        source = request.POST.get("source", "").strip()
        url = request.POST.get("url", "").strip()
        tracks_text = request.POST.get("tracks_text", "")
        intensity = request.POST.get("intensity", "savage").strip() or "savage"
        csv_file = request.FILES.get("csv_file")

    # Normalize tone intensity to accepted values.
    if intensity not in ("mild", "savage", "nuclear"):
        intensity = "savage"

    # Ingest playlist based on source and provided fields.
    try:
        playlist: Playlist

        if csv_file:
            playlist = parse_csv(csv_file.file, csv_file.name)
        elif tracks_text.strip() or source == "manual":
            playlist = parse_track_list(tracks_text)
        elif url or source == "spotify":
            playlist_id = extract_playlist_id(url)
            raw_data = fetch_playlist(playlist_id)
            playlist = normalize_spotify_response(raw_data)
        else:
            raise EmptyPlaylistError(
                "Please provide a Spotify playlist link or paste your tracks."
            )

        # Check cache for identical playlist content and intensity
        cache_key = None
        if playlist.tracks:
            sig_content = "|".join(
                f"{t.title}:{','.join(t.artists)}" for t in playlist.tracks
            )
            content_hash = hashlib.sha256(sig_content.encode("utf-8")).hexdigest()
            cache_key = f"roast_cache:{content_hash}:{intensity}"
            cached_data = cache.get(cache_key)
            if cached_data:
                return JsonResponse(cached_data)

        # Compute deterministic statistics and entertainment scores.
        stats = calculate_playlist_stats(playlist)
        scores = calculate_scores(stats)
        report = generate_roast(
            stats=stats,
            sample_tracks=playlist.tracks,
            intensity=intensity,
            playlist_title=playlist.title,
            scores=scores,
        )

        response_data = {
            "playlist": _serialize_playlist(playlist),
            "stats": _serialize_stats(stats),
            "scores": _serialize_scores(scores),
            "report": report,
            "intensity": intensity,
        }

        if cache_key:
            cache.set(cache_key, response_data, timeout=1800)

        return JsonResponse(response_data)

    except IngestionError as err:
        status_code = _ERROR_STATUS_MAP.get(err.code, 400)
        return JsonResponse(
            {
                "error": {
                    "code": err.code,
                    "message": err.message,
                    "fallback": err.fallback,
                }
            },
            status=status_code,
        )
    except Exception as exc:
        logger.exception("Unexpected error during playlist processing: %s", exc)
        return JsonResponse(
            {
                "error": {
                    "code": "UPSTREAM_ERROR",
                    "message": "An unexpected error occurred. Paste your tracks instead.",
                    "fallback": "manual",
                }
            },
            status=500,
        )
