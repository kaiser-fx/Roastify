"""
Tests for web app views:
- GET / (landing page)
- GET /fallback/ (fallback page)
- GET /results/ (results page with computed stats)
"""

from django.test import Client, SimpleTestCase


class WebViewsTests(SimpleTestCase):
    """Test web templates and views rendering."""

    def setUp(self):
        self.client = Client()

    def test_landing_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roastify")
        self.assertContains(response, "Spotify playlist link")
        self.assertContains(response, "Find out")

    def test_fallback_page_renders(self):
        response = self.client.get("/fallback/?error=Spotify%20blocked")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paste your tracks")
        self.assertContains(response, "Spotify blocked")

    def test_results_page_renders_with_stats(self):
        response = self.client.get("/results/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Playlist statistics")
        self.assertContains(response, "Unique artists")
        self.assertContains(response, "Artist obsession")
