"""
Unit tests for the analysis engine:
- Deterministic stats computation (empty, 1 track, same artist, missing artists, duplicates, large playlists)
- Optional stats (release year, explicit share, genre distribution)
- Entertainment score formulas and bounds clamping (0 to 100)
"""

from django.test import SimpleTestCase

from apps.analysis.models import Playlist, Track
from apps.analysis.scoring import (
    calculate_artist_obsession,
    calculate_emotional_damage,
    calculate_main_character_energy,
    calculate_scores,
)
from apps.analysis.stats import calculate_playlist_stats


class StatsEdgeCasesTests(SimpleTestCase):
    """Test deterministic statistics across edge cases and regular playlists."""

    def test_empty_playlist(self):
        playlist = Playlist(source="manual", tracks=[])
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 0)
        self.assertEqual(stats.unique_artist_count, 0)
        self.assertEqual(stats.top_artists, [])
        self.assertEqual(stats.top_artist_share, 0.0)
        self.assertEqual(stats.top3_share, 0.0)
        self.assertEqual(stats.duplicate_tracks, [])
        self.assertIsNone(stats.release_year_distribution)
        self.assertIsNone(stats.explicit_share)
        self.assertIsNone(stats.genre_distribution)

    def test_single_track(self):
        track = Track(
            title="Solo Track",
            artists=["Solo Artist"],
            release_date="2021-05-21",
            explicit=False,
            genres=["indie pop"],
        )
        playlist = Playlist(source="spotify", tracks=[track])
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 1)
        self.assertEqual(stats.unique_artist_count, 1)
        self.assertEqual(len(stats.top_artists), 1)
        self.assertEqual(stats.top_artists[0].name, "Solo Artist")
        self.assertEqual(stats.top_artists[0].count, 1)
        self.assertEqual(stats.top_artists[0].share, 1.0)
        self.assertEqual(stats.top_artist_share, 1.0)
        self.assertEqual(stats.top3_share, 1.0)
        self.assertEqual(stats.duplicate_tracks, [])
        self.assertEqual(stats.release_year_distribution, {2021: 1})
        self.assertEqual(stats.explicit_share, 0.0)
        self.assertEqual(stats.genre_distribution, {"indie pop": 1})

    def test_all_same_artist(self):
        tracks = [
            Track(title=f"Song {i}", artists=["Radiohead"])
            for i in range(10)
        ]
        playlist = Playlist(source="manual", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 10)
        self.assertEqual(stats.unique_artist_count, 1)
        self.assertEqual(len(stats.top_artists), 1)
        self.assertEqual(stats.top_artists[0].name, "Radiohead")
        self.assertEqual(stats.top_artists[0].count, 10)
        self.assertEqual(stats.top_artist_share, 1.0)
        self.assertEqual(stats.top3_share, 1.0)

    def test_missing_artist_names(self):
        tracks = [
            Track(title="Nameless Track 1", artists=[]),
            Track(title="Nameless Track 2", artists=["   ", ""]),
            Track(title="Named Track", artists=["Valid Artist"]),
        ]
        playlist = Playlist(source="manual", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 3)
        # Should gracefully treat empty artist lists as 'Unknown Artist'
        artist_names = [a.name for a in stats.top_artists]
        self.assertIn("Unknown Artist", artist_names)
        self.assertIn("Valid Artist", artist_names)

    def test_duplicate_tracks_detection(self):
        tracks = [
            Track(title="Blinding Lights", artists=["The Weeknd"]),
            Track(title="blinding lights", artists=["the weeknd"]),
            Track(title="Save Your Tears", artists=["The Weeknd"]),
            Track(title="Save Your Tears", artists=["The Weeknd"]),
            Track(title="Unique Track", artists=["Different Artist"]),
        ]
        playlist = Playlist(source="manual", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 5)
        # Both Blinding Lights and Save Your Tears appear more than once
        self.assertIn("blinding lights", [d.lower() for d in stats.duplicate_tracks])
        self.assertIn("save your tears", [d.lower() for d in stats.duplicate_tracks])
        self.assertEqual(len(stats.duplicate_tracks), 2)

    def test_very_large_playlist(self):
        # 500 tracks across 50 artists
        tracks = [
            Track(title=f"Track {i}", artists=[f"Artist {i % 50}"])
            for i in range(500)
        ]
        playlist = Playlist(source="manual", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.track_count, 500)
        self.assertEqual(stats.unique_artist_count, 50)
        self.assertEqual(len(stats.top_artists), 10)  # Top 10 returned
        for a in stats.top_artists:
            self.assertEqual(a.count, 10)
            self.assertEqual(a.share, 0.02)
        self.assertEqual(stats.top_artist_share, 0.02)
        # Top 3 artists have 30 tracks out of 500 = 0.06
        self.assertEqual(stats.top3_share, 0.06)

    def test_absent_optional_fields_stay_none(self):
        tracks = [
            Track(title="Plain Track", artists=["Artist A"])
        ]
        playlist = Playlist(source="manual", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertIsNone(stats.release_year_distribution)
        self.assertIsNone(stats.explicit_share)
        self.assertIsNone(stats.genre_distribution)

    def test_release_year_and_explicit_stats(self):
        tracks = [
            Track(title="T1", artists=["A1"], release_date="1999-04-12", explicit=True),
            Track(title="T2", artists=["A2"], release_date="1999-10-01", explicit=False),
            Track(title="T3", artists=["A3"], release_date="2020", explicit=True),
            Track(title="T4", artists=["A4"], release_date="invalid-date", explicit=None),
        ]
        playlist = Playlist(source="spotify", tracks=tracks)
        stats = calculate_playlist_stats(playlist)

        self.assertEqual(stats.release_year_distribution, {1999: 2, 2020: 1})
        # 2 explicit out of 3 known = 2/3 = 0.6667
        self.assertEqual(stats.explicit_share, 0.6667)


class ScoringBoundsTests(SimpleTestCase):
    """Test that entertainment score formulas return clamped values (0 to 100)."""

    def test_scores_empty_playlist(self):
        empty_stats = calculate_playlist_stats(Playlist(source="manual", tracks=[]))
        scores = calculate_scores(empty_stats)

        for s in scores:
            self.assertGreaterEqual(s.value, 0)
            self.assertLessEqual(s.value, 100)
            self.assertEqual(s.value, 0)

    def test_scores_single_track(self):
        track = Track(title="One", artists=["Solo"])
        stats = calculate_playlist_stats(Playlist(source="manual", tracks=[track]))
        scores = calculate_scores(stats)

        for s in scores:
            self.assertGreaterEqual(s.value, 0)
            self.assertLessEqual(s.value, 100)

    def test_scores_high_obsession(self):
        # 20 tracks, 19 from the same artist
        tracks = [
            Track(title=f"Track {i}", artists=["Obsession Artist"])
            for i in range(19)
        ] + [Track(title="Outlier", artists=["Other Artist"])]

        stats = calculate_playlist_stats(Playlist(source="manual", tracks=tracks))
        obsession = calculate_artist_obsession(stats)
        self.assertGreaterEqual(obsession, 80)
        self.assertLessEqual(obsession, 100)

    def test_scores_bounds_extreme_values(self):
        # Test boundary clamping
        tracks = [
            Track(title="Duplicate Song", artists=["Artist A"], release_date="2024")
            for _ in range(50)
        ]
        stats = calculate_playlist_stats(Playlist(source="manual", tracks=tracks))
        scores = calculate_scores(stats)

        for score in scores:
            self.assertIsInstance(score.value, int)
            self.assertGreaterEqual(score.value, 0)
            self.assertLessEqual(score.value, 100)
