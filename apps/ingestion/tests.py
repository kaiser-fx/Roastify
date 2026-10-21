"""
Tests for the ingestion app:
- URL validator
- Manual track list parser
- CSV upload parser
- Normalizer
"""

import io
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from apps.analysis.models import Playlist, Track
from apps.ingestion.errors import (
    EmptyPlaylistError,
    InvalidURLError,
)
from apps.ingestion.manual_parser import parse_csv, parse_track_list
from apps.ingestion.normalizer import normalize_spotify_response
from apps.ingestion.url_validator import extract_playlist_id


class URLValidatorTests(SimpleTestCase):
    """Test Spotify playlist URL validation and ID extraction."""

    def test_valid_web_urls(self):
        valid_ids = [
            "37i9dQZF1DXcBWIGoYBM5M",
            "1234567890abcdefABCDEF",
            "aBcDeFgHiJkLmNoPqRsTuV",
        ]
        for pid in valid_ids:
            url = f"https://open.spotify.com/playlist/{pid}"
            self.assertEqual(extract_playlist_id(url), pid)

            # With query parameters
            url_with_query = f"https://open.spotify.com/playlist/{pid}?si=abc123xyz"
            self.assertEqual(extract_playlist_id(url_with_query), pid)

    def test_valid_uri(self):
        pid = "37i9dQZF1DXcBWIGoYBM5M"
        self.assertEqual(
            extract_playlist_id(f"spotify:playlist:{pid}"),
            pid,
        )

    def test_invalid_hosts_rejected(self):
        invalid_urls = [
            "https://evil.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "https://spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "http://169.254.169.254/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com.attacker.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        ]
        for url in invalid_urls:
            with self.assertRaises(InvalidURLError):
                extract_playlist_id(url)

    def test_invalid_paths_rejected(self):
        invalid_paths = [
            "https://open.spotify.com/track/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com/album/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com/artist/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com/playlist/",
        ]
        for url in invalid_paths:
            with self.assertRaises(InvalidURLError):
                extract_playlist_id(url)

    def test_empty_and_oversized_urls(self):
        with self.assertRaises(InvalidURLError):
            extract_playlist_id("")

        with self.assertRaises(InvalidURLError):
            extract_playlist_id("   ")

        oversized = "https://open.spotify.com/playlist/" + "a" * 350
        with self.assertRaises(InvalidURLError):
            extract_playlist_id(oversized)


class ManualParserTests(SimpleTestCase):
    """Test manual text and CSV parsers."""

    def test_parse_valid_text(self):
        text = """
        Blinding Lights - The Weeknd
        Bohemian Rhapsody - Queen
        Stay - The Kid LAROI, Justin Bieber
        """
        playlist = parse_track_list(text)
        self.assertEqual(playlist.source, "manual")
        self.assertEqual(len(playlist.tracks), 3)

        t1 = playlist.tracks[0]
        self.assertEqual(t1.title, "Blinding Lights")
        self.assertEqual(t1.artists, ["The Weeknd"])

        t3 = playlist.tracks[2]
        self.assertEqual(t3.title, "Stay")
        self.assertEqual(t3.artists, ["The Kid LAROI", "Justin Bieber"])

    def test_parse_en_dash_separator(self):
        text = "Anti-Hero \u2013 Taylor Swift"
        playlist = parse_track_list(text)
        self.assertEqual(len(playlist.tracks), 1)
        self.assertEqual(playlist.tracks[0].title, "Anti-Hero")
        self.assertEqual(playlist.tracks[0].artists, ["Taylor Swift"])

    def test_parse_missing_artist_defaults_to_unknown(self):
        text = "Song Without Separator"
        playlist = parse_track_list(text)
        self.assertEqual(len(playlist.tracks), 1)
        self.assertEqual(playlist.tracks[0].title, "Song Without Separator")
        self.assertEqual(playlist.tracks[0].artists, ["Unknown Artist"])

    def test_empty_text_raises_error(self):
        with self.assertRaises(EmptyPlaylistError):
            parse_track_list("")
        with self.assertRaises(EmptyPlaylistError):
            parse_track_list("   \n\n   ")

    def test_parse_valid_csv(self):
        csv_content = (
            "title,artist,album,release_date\n"
            "Flowers,Miley Cyrus,Endless Summer Vacation,2023-01-13\n"
            "Cruel Summer,Taylor Swift,Lover,2019-08-23\n"
        ).encode("utf-8")

        file_obj = io.BytesIO(csv_content)
        playlist = parse_csv(file_obj, "test.csv")
        self.assertEqual(len(playlist.tracks), 2)
        self.assertEqual(playlist.tracks[0].title, "Flowers")
        self.assertEqual(playlist.tracks[0].artists, ["Miley Cyrus"])
        self.assertEqual(playlist.tracks[0].album, "Endless Summer Vacation")
        self.assertEqual(playlist.tracks[0].release_date, "2023-01-13")

    def test_csv_missing_title_raises_error(self):
        csv_content = "artist,album\nDrake,Certified Lover Boy\n".encode("utf-8")
        file_obj = io.BytesIO(csv_content)
        with self.assertRaises(InvalidURLError):
            parse_csv(file_obj, "bad.csv")


class NormalizerTests(SimpleTestCase):
    """Test Spotify raw response normalizer."""

    def test_normalize_spotify_payload(self):
        raw = {
            "name": "My Heavy Rotation",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/xyz"},
            "tracks": {
                "total": 2,
                "items": [
                    {
                        "track": {
                            "name": "Karma",
                            "artists": [{"name": "Taylor Swift"}],
                            "album": {
                                "name": "Midnights",
                                "release_date": "2022-10-21",
                            },
                            "duration_ms": 204852,
                            "explicit": False,
                            "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                        }
                    },
                    {
                        "track": {
                            "name": "Starboy",
                            "artists": [{"name": "The Weeknd"}, {"name": "Daft Punk"}],
                            "album": {
                                "name": "Starboy",
                                "release_date": "2016-11-25",
                            },
                            "duration_ms": 230453,
                            "explicit": True,
                            "external_urls": {},
                        }
                    },
                ],
            },
        }

        playlist = normalize_spotify_response(raw)
        self.assertEqual(playlist.title, "My Heavy Rotation")
        self.assertEqual(playlist.source, "spotify")
        self.assertEqual(len(playlist.tracks), 2)

        t1 = playlist.tracks[0]
        self.assertEqual(t1.title, "Karma")
        self.assertEqual(t1.artists, ["Taylor Swift"])
        self.assertEqual(t1.album, "Midnights")
        self.assertEqual(t1.release_date, "2022-10-21")
        self.assertEqual(t1.duration_ms, 204852)
        self.assertEqual(t1.explicit, False)

        t2 = playlist.tracks[1]
        self.assertEqual(t2.artists, ["The Weeknd", "Daft Punk"])
        self.assertEqual(t2.explicit, True)

    def test_missing_metadata_stays_none(self):
        raw = {
            "name": "Minimal",
            "tracks": {
                "items": [
                    {
                        "track": {
                            "name": "Barebones",
                            "artists": [{"name": "Solo Artist"}],
                        }
                    }
                ]
            },
        }
        playlist = normalize_spotify_response(raw)
        self.assertEqual(len(playlist.tracks), 1)
        t = playlist.tracks[0]
        self.assertIsNone(t.album)
        self.assertIsNone(t.release_date)
        self.assertIsNone(t.duration_ms)
        self.assertIsNone(t.explicit)


class PublicScraperTests(SimpleTestCase):
    """Test public Spotify web scraping without user account linking."""

    @patch("urllib.request.urlopen")
    def test_scrape_embed_success(self, mock_urlopen):
        mock_html = """
        <html>
        <head>
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "state": {
                "data": {
                  "entity": {
                    "title": "Weekend Vibes",
                    "trackList": [
                      {
                        "title": "Espresso",
                        "subtitle": "Sabrina Carpenter",
                        "duration": 175000,
                        "isExplicit": false,
                        "uri": "spotify:track:2qSkXiYOKdqDC3EJz2iRZs"
                      },
                      {
                        "title": "Birds of a Feather",
                        "subtitle": "Billie Eilish,\xa0FINNEAS",
                        "duration": 190000,
                        "isExplicit": true,
                        "uri": "spotify:track:6dOtVTDmmpTTKUgfZrVVFr"
                      }
                    ]
                  }
                }
              }
            }
          }
        }
        </script>
        </head>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_html.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        from apps.ingestion.public_scraper import fetch_public_playlist_data
        data = fetch_public_playlist_data("test_pid")
        self.assertEqual(data["name"], "Weekend Vibes")
        self.assertEqual(data["tracks"]["total"], 2)
        items = data["tracks"]["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["track"]["name"], "Espresso")
        self.assertEqual(items[0]["track"]["artists"], [{"name": "Sabrina Carpenter"}])
        self.assertEqual(items[1]["track"]["name"], "Birds of a Feather")
        self.assertEqual(
            items[1]["track"]["artists"],
            [{"name": "Billie Eilish"}, {"name": "FINNEAS"}],
        )

    @patch("urllib.request.urlopen")
    def test_scrape_404_raises_private_error(self, mock_urlopen):
        import urllib.error
        from apps.ingestion.errors import PlaylistPrivateError
        from apps.ingestion.public_scraper import fetch_public_playlist_data

        err = urllib.error.HTTPError(
            url="https://open.spotify.com/embed/playlist/notfound",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = err

        with self.assertRaises(PlaylistPrivateError):
            fetch_public_playlist_data("notfound")

    @patch("urllib.request.urlopen")
    def test_scrape_empty_playlist_raises_error(self, mock_urlopen):
        mock_html = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "state": {
                "data": {
                  "entity": {
                    "title": "Empty Playlist",
                    "trackList": []
                  }
                }
              }
            }
          }
        }
        </script>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_html.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        from apps.ingestion.errors import EmptyPlaylistError
        from apps.ingestion.public_scraper import fetch_public_playlist_data

        with self.assertRaises(EmptyPlaylistError):
            fetch_public_playlist_data("empty_pid")

    @patch("urllib.request.urlopen")
    def test_scrape_web_player_fallback_success(self, mock_urlopen):
        import base64
        import json

        embed_html = "<html><body>No embed data</body></html>"
        
        state_dict = {
            "entities": {
                "items": {
                    "spotify:playlist:test_pid": {
                        "name": "Chill Beats",
                        "content": {
                            "items": [
                                {
                                    "itemV2": {
                                        "data": {
                                            "name": "Lofi Rain",
                                            "artists": {
                                                "items": [{"profile": {"name": "Cozy Producer"}}]
                                            },
                                            "albumOfTrack": {"name": "Rainy Days"},
                                            "trackDuration": {"totalMilliseconds": 140000},
                                            "id": "track_123",
                                        }
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        b64_state = base64.b64encode(json.dumps(state_dict).encode("utf-8")).decode("utf-8")
        web_html = f'<html><script id="initialState" type="text/plain">{b64_state}</script></html>'

        resp_embed = MagicMock()
        resp_embed.read.return_value = embed_html.encode("utf-8")
        resp_embed.__enter__.return_value = resp_embed

        resp_web = MagicMock()
        resp_web.read.return_value = web_html.encode("utf-8")
        resp_web.__enter__.return_value = resp_web

        mock_urlopen.side_effect = [resp_embed, resp_web]

        from apps.ingestion.public_scraper import fetch_public_playlist_data
        data = fetch_public_playlist_data("test_pid")
        self.assertEqual(data["name"], "Chill Beats")
        items = data["tracks"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["track"]["name"], "Lofi Rain")
        self.assertEqual(items[0]["track"]["artists"], [{"name": "Cozy Producer"}])
        self.assertEqual(items[0]["track"]["album"]["name"], "Rainy Days")


