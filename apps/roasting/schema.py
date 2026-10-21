"""
Roast report schema and validator.
Enforces type safety, score clamping, string length caps, and sanitization.
All AI output must pass this validator before reaching the frontend.
"""

from __future__ import annotations

import html
import re
from typing import Any

from apps.analysis.models import Score

_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_text(text: Any, max_length: int = 500) -> str:
    """Strip HTML tags, unescape entities, and truncate to max_length."""
    if text is None:
        return ""
    clean = _TAG_RE.sub("", str(text).strip())
    clean = html.unescape(clean)
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip() + "..."
    return clean


def validate_roast_report(
    raw_report: dict[str, Any],
    fallback_scores: list[Score] | None = None,
    intensity: str = "savage",
    meta_line: str = "",
) -> dict[str, Any]:
    """
    Validate and normalize raw AI output dict against the RoastReport schema.

    Raises ValueError if required fields are missing or unrecoverable.
    Clamps scores to 0-100, caps text lengths, and ensures safe strings.
    """
    if not isinstance(raw_report, dict):
        raise ValueError("Roast report must be a dictionary.")

    headline = _sanitize_text(raw_report.get("headline"), max_length=140)
    if not headline:
        raise ValueError("Missing or empty headline in roast report.")

    personality = _sanitize_text(raw_report.get("personality"), max_length=80)
    if not personality:
        personality = "The Uncategorized Listener"

    roast = _sanitize_text(raw_report.get("roast"), max_length=900)
    if not roast:
        raise ValueError("Missing or empty roast text in roast report.")

    final_verdict = _sanitize_text(raw_report.get("final_verdict"), max_length=220)
    if not final_verdict:
        final_verdict = "Verdict pending another listen."

    # Validate observations: must be list of strings.
    raw_obs = raw_report.get("observations")
    observations: list[str] = []
    if isinstance(raw_obs, list):
        for item in raw_obs:
            cleaned = _sanitize_text(item, max_length=220)
            if cleaned:
                observations.append(cleaned)

    # Ensure at least 2 observations
    if len(observations) < 2:
        raise ValueError("Roast report must contain at least 2 observations.")
    observations = observations[:5]

    # Validate or substitute scores
    scores_data: list[dict[str, Any]] = []
    raw_scores = raw_report.get("scores")

    if isinstance(raw_scores, list) and len(raw_scores) == 3:
        for s in raw_scores:
            if isinstance(s, dict) and "label" in s and "value" in s:
                val = max(0, min(100, int(round(float(s["value"])))))
                scores_data.append({"label": str(s["label"]), "value": val})

    # If scores missing or malformed, use code-computed scores
    if len(scores_data) != 3 and fallback_scores:
        scores_data = [{"label": s.label, "value": s.value} for s in fallback_scores]

    tone_map = {
        "mild": "Mild",
        "savage": "Savage",
        "nuclear": "Nuclear",
    }
    tone_label = tone_map.get(intensity.lower(), "Savage")

    return {
        "headline": headline,
        "personality": personality,
        "tone_label": tone_label,
        "meta_line": meta_line or _sanitize_text(raw_report.get("meta_line", ""), max_length=200),
        "scores": scores_data,
        "observations": observations,
        "roast": roast,
        "final_verdict": final_verdict,
    }
