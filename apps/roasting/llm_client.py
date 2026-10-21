"""
Gemini API adapter for generating roast reports.
Only this module imports the Google Gen AI SDK.
Handles authentication, timeouts, retries, structured JSON parsing, and graceful fallbacks.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors

from apps.analysis.models import PlaylistStats, Score, Track
from apps.analysis.scoring import calculate_scores
from apps.roasting.fallback import generate_fallback_roast
from apps.roasting.prompts import build_system_prompt, build_user_prompt
from apps.roasting.schema import validate_roast_report

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1
_RETRY_DELAY = 1.0  # seconds


def generate_roast(
    stats: PlaylistStats,
    sample_tracks: list[Track],
    intensity: str = "savage",
    playlist_title: str | None = None,
    scores: list[Score] | None = None,
) -> dict[str, Any]:
    """
    Generate an AI roast report using the Gemini API.

    Enforces:
    1. Pre-computed scores from scoring.py
    2. Structured JSON response with validation
    3. One retry on transient or malformed output
    4. Graceful fallback to template roast if API is unavailable or unconfigured
    """
    if scores is None:
        scores = calculate_scores(stats)

    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

    # If no API key configured, use deterministic fallback roast.
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Using fallback roast generator.")
        return generate_fallback_roast(
            stats,
            scores=scores,
            intensity=intensity,
            playlist_title=playlist_title,
        )

    system_prompt = build_system_prompt(intensity=intensity)
    user_prompt = build_user_prompt(
        stats=stats,
        sample_tracks=sample_tracks,
        scores=scores,
        playlist_title=playlist_title,
    )

    top_artist_name = stats.top_artists[0].name if stats.top_artists else "Unknown"
    top_artist_count = stats.top_artists[0].count if stats.top_artists else 0
    top_share_pct = round(stats.top_artist_share * 100, 1)
    meta_line = (
        f"{stats.track_count} tracks, {stats.unique_artist_count} unique artists, "
        f"{top_artist_count} tracks from {top_artist_name} ({top_share_pct}%)."
    )

    client = genai.Client(api_key=api_key)

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.85,
                    "max_output_tokens": 1000,
                },
            )

            raw_text = (response.text or "").strip()
            if not raw_text:
                raise ValueError("Empty response received from Gemini API.")

            raw_json = json.loads(raw_text)
            validated = validate_roast_report(
                raw_json,
                fallback_scores=scores,
                intensity=intensity,
                meta_line=meta_line,
            )
            return validated

        except (json.JSONDecodeError, ValueError) as val_err:
            logger.warning(
                "Attempt %d: Malformed or invalid output from Gemini: %s",
                attempt + 1,
                val_err,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)
                continue

        except (genai_errors.APIError, Exception) as api_err:
            logger.warning(
                "Attempt %d: Gemini API request failed: %s",
                attempt + 1,
                api_err,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)
                continue

    # All attempts exhausted: return grounded fallback roast.
    logger.info("All Gemini attempts failed. Falling back to template roast generator.")
    return generate_fallback_roast(
        stats,
        scores=scores,
        intensity=intensity,
        playlist_title=playlist_title,
    )
