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
            source_id=1,
            source="C:/Test/Path/song.mp3",
            name="Test Song",
            duration=180.5,
            bpm=120,
            recording_year=2023,
            performers=["Dua Lipa"],
            composers=["Writer 1", "Writer 2"]
        )
        
        # Test backward compatibility properties
        assert song.file_id == 1
        assert song.path == "C:/Test/Path/song.mp3"
        assert song.title == "Test Song"
        
        assert song.source_id == 1
        assert song.source == "C:/Test/Path/song.mp3"
        assert song.name == "Test Song"
        assert song.duration == 180.5
        assert song.bpm == 120
        assert song.recording_year == 2023
        assert song.performers == ["Dua Lipa"]
        assert song.composers == ["Writer 1", "Writer 2"]

    def test_get_display_performers_with_performers(self):
        """Test getting display performers when performers exist"""
        song = Song(performers=["performer 1", "performer 2"])
        assert song.get_display_performers() == "performer 1, performer 2"

    def test_get_display_performers_without_performers(self):
        """Test getting display performers when no performers"""
        song = Song()
        assert song.get_display_performers() == "Unknown Performer"

    def test_get_display_title_with_title(self):
        """Test getting display title when title exists"""
        song = Song(name="My Song")
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

