"""
Web app views. Serve pages using Django templates.
Views stay thin: they pass data to templates, business logic lives in services.
"""

import json
from pathlib import Path

from django.shortcuts import render

from apps.analysis.models import Playlist, Track
from apps.analysis.stats import calculate_playlist_stats

# Load demo report from the reference data for prototyping.
_DEMO_REPORT_PATH = Path(__file__).resolve().parent.parent.parent / "roastify-docs" / "reference" / "ui" / "demo_report.json"


def _load_demo_report() -> dict:
    """Load the bundled demo report JSON for the UI prototype."""
    try:
        with open(_DEMO_REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "headline": "Something went wrong",
            "personality": "The Invisible Fan",
            "tone_label": "Savage",
            "meta_line": "No data available.",
            "scores": [],
            "observations": ["Could not load demo report."],
            "roast": "We tried to roast you, but the oven was off.",
            "final_verdict": "Try again later.",
        }


def _build_demo_playlist() -> Playlist:
    """
    Build a demo playlist matching the reference demo report
    (48 tracks, 13 unique artists, 15 tracks from the top artist).
    """
    tracks: list[Track] = []
    # 15 tracks from top artist Taylor Swift
    for i in range(15):
        tracks.append(Track(
            title=f"Anti-Hero {i+1}" if i > 0 else "Anti-Hero",
            artists=["Taylor Swift"],
            release_date="2022-10-21",
        ))

    # 33 tracks from 12 other artists (totalling 13 unique artists)
    other_artists = [
        "The Weeknd", "Dua Lipa", "Harry Styles", "Olivia Rodrigo",
        "Billie Eilish", "SZA", "Lorde", "Lana Del Rey",
        "Charli XCX", "Chappell Roan", "Sabrina Carpenter", "Boygenius",
    ]
    for i in range(33):
        artist = other_artists[i % len(other_artists)]
        tracks.append(Track(
            title=f"Sample Track {i+16}",
            artists=[artist],
            release_date="2023-03-15",
        ))

    return Playlist(source="spotify", tracks=tracks, title="Heavy Rotation")


def landing(request):
    """Landing page with URL input, tone selector and record shelf."""
    return render(request, "web/landing.html")


def results(request):
    """Results page showing the roast report and real computed statistics."""
    report = _load_demo_report()
    demo_playlist = _build_demo_playlist()
    stats = calculate_playlist_stats(demo_playlist)

    context = {
        "report": report,
        "stats": stats,
        "top_artist_share_pct": round(stats.top_artist_share * 100, 1),
        "top3_share_pct": round(stats.top3_share * 100, 1),
    }
    return render(request, "web/results.html", context)


def fallback(request):
    """Fallback page for manual track list and CSV upload."""
    error_message = request.GET.get("error", "")
    context = {}
    if error_message:
        context["error_message"] = error_message
    return render(request, "web/fallback.html", context)
