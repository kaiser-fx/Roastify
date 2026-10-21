"""
Tests for API views and endpoints:
- GET /healthz
- POST /api/roast/ (JSON and multipart)
- Error handling and fallback codes
- Rate limiting
"""

import io
import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase
from django.core.cache import cache

from apps.ingestion.errors import AccessRestrictedError, PlaylistPrivateError


class APIRoastEndpointTests(SimpleTestCase):
    """Test the /api/roast/ ingestion endpoint."""

    def setUp(self):
        self.client = Client()
        cache.clear()
        patcher = patch("apps.api.views.generate_roast")
        self.mock_roast = patcher.start()
        self.mock_roast.return_value = {
            "headline": "Mocked Roast Headline",
            "personality": "The Mocked Critic",
            "tone_label": "Savage",
            "meta_line": "Test meta line",
            "scores": [
                {"label": "Artist obsession", "value": 50},
                {"label": "Main character energy", "value": 50},
                {"label": "Emotional damage", "value": 50},
            ],
            "observations": ["Obs 1", "Obs 2"],
            "roast": "This is a mocked roast.",
            "final_verdict": "Mocked verdict.",
        }
        self.addCleanup(patcher.stop)

    def test_healthz(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_roast_manual_text_json(self):
        payload = {
            "source": "manual",
            "tracks_text": "Song One - Artist A\nSong Two - Artist B",
            "intensity": "nuclear",
        }
        response = self.client.post(
            "/api/roast/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("playlist", data)
        self.assertIn("stats", data)
        self.assertIn("scores", data)
        self.assertEqual(data["intensity"], "nuclear")
        self.assertEqual(data["playlist"]["track_count"], 2)
        self.assertEqual(data["playlist"]["tracks"][0]["title"], "Song One")
        self.assertEqual(data["stats"]["track_count"], 2)
        self.assertEqual(data["stats"]["unique_artist_count"], 2)
        self.assertEqual(len(data["scores"]), 3)

    def test_roast_manual_csv_multipart(self):
        csv_bytes = b"title,artist\nHeat Waves,Glass Animals\nAs It Was,Harry Styles\n"
        csv_file = io.BytesIO(csv_bytes)
        csv_file.name = "playlist.csv"

        response = self.client.post(
            "/api/roast/",
            data={
                "source": "manual",
                "intensity": "mild",
                "csv_file": csv_file,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intensity"], "mild")
        self.assertEqual(data["playlist"]["track_count"], 2)
        self.assertEqual(data["playlist"]["tracks"][0]["title"], "Heat Waves")

    def test_roast_invalid_url(self):
        payload = {
            "source": "spotify",
            "url": "https://evil.com/playlist/fake",
        }
        response = self.client.post(
            "/api/roast/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "INVALID_URL")

    def test_roast_empty_input(self):
        payload = {"source": "manual", "tracks_text": "   "}
        response = self.client.post(
            "/api/roast/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "EMPTY_PLAYLIST")

    @patch("apps.api.views.fetch_playlist")
    def test_roast_spotify_access_restricted_fallback(self, mock_fetch):
        mock_fetch.side_effect = AccessRestrictedError()
        payload = {
            "source": "spotify",
            "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        }
        response = self.client.post(
            "/api/roast/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data["error"]["code"], "ACCESS_RESTRICTED")
        self.assertEqual(data["error"]["fallback"], "manual")

    @patch("apps.api.views.fetch_playlist")
    def test_roast_spotify_success(self, mock_fetch):
        mock_fetch.return_value = {
            "name": "Top Hits",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"},
            "tracks": {
                "total": 1,
                "items": [
                    {
                        "track": {
                            "name": "Levitating",
                            "artists": [{"name": "Dua Lipa"}],
                            "album": {"name": "Future Nostalgia", "release_date": "2020-03-27"},
                            "duration_ms": 203000,
                            "explicit": False,
                        }
                    }
                ],
            },
        }

        payload = {
            "source": "spotify",
            "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "intensity": "savage",
        }
        response = self.client.post(
            "/api/roast/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["playlist"]["title"], "Top Hits")
        self.assertEqual(data["playlist"]["track_count"], 1)

    def test_rate_limiting(self):
        with patch("apps.api.throttling.settings.RATE_LIMIT_PER_MINUTE", 2):
            payload = {
                "source": "manual",
                "tracks_text": "Track - Artist",
            }
            # Request 1
            r1 = self.client.post("/api/roast/", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(r1.status_code, 200)
            # Request 2
            r2 = self.client.post("/api/roast/", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(r2.status_code, 200)
            # Request 3 should be rate limited
            r3 = self.client.post("/api/roast/", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(r3.status_code, 429)
            self.assertEqual(r3.json()["error"]["code"], "RATE_LIMITED")
