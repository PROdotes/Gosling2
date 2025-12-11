"""Unit tests for Song model"""
import pytest
from src.data.models.song import Song


class TestSongModel:
    """Test cases for Song model"""

    def test_song_creation_with_defaults(self):
        """Test creating a song with default values"""
        song = Song()

        assert song.file_id is None
        assert song.path is None
        assert song.title is None
        assert song.duration is None
        assert song.bpm is None
        assert song.performers == []
        assert song.composers == []
        assert song.lyricists == []
        assert song.producers == []
        assert song.groups == []

    def test_song_creation_with_values(self):
        """Test creating a song with specific values"""
        song = Song(
            file_id=1,
            path="/path/to/song.mp3",
            title="Test Song",
            duration=180.5,
            bpm=120,
            performers=["Artist 1", "Artist 2"],
            composers=["Composer 1"]
        )

        assert song.file_id == 1
        assert song.path == "/path/to/song.mp3"
        assert song.title == "Test Song"
        assert song.duration == 180.5
        assert song.bpm == 120
        assert song.performers == ["Artist 1", "Artist 2"]
        assert song.composers == ["Composer 1"]

    def test_get_display_artists_with_performers(self):
        """Test getting display artists when performers exist"""
        song = Song(performers=["Artist 1", "Artist 2"])
        assert song.get_display_artists() == "Artist 1, Artist 2"

    def test_get_display_artists_without_performers(self):
        """Test getting display artists when no performers"""
        song = Song()
        assert song.get_display_artists() == "Unknown Artist"

    def test_get_display_title_with_title(self):
        """Test getting display title when title exists"""
        song = Song(title="My Song")
        assert song.get_display_title() == "My Song"

    def test_get_display_title_without_title(self):
        """Test getting display title when no title"""
        song = Song()
        assert song.get_display_title() == "Unknown Title"

    def test_get_formatted_duration_with_duration(self):
        """Test formatted duration"""
        song = Song(duration=185.5)  # 3:05
        assert song.get_formatted_duration() == "03:05"

    def test_get_formatted_duration_without_duration(self):
        """Test formatted duration when no duration"""
        song = Song()
        assert song.get_formatted_duration() == "00:00"

    def test_get_formatted_duration_various_times(self):
        """Test various duration formats"""
        test_cases = [
            (0, "00:00"),
            (30, "00:30"),
            (60, "01:00"),
            (125, "02:05"),
            (3599, "59:59"),
        ]

        for duration, expected in test_cases:
            song = Song(duration=duration)
            assert song.get_formatted_duration() == expected

    def test_post_init_initializes_lists(self):
        """Test that post_init properly initializes None lists"""
        song = Song(
            performers=None,
            composers=None,
            lyricists=None,
            producers=None,
            groups=None
        )

        assert song.performers == []
        assert song.composers == []
        assert song.lyricists == []
        assert song.producers == []
        assert song.groups == []

