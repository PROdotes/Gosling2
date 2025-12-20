"""Tests for SettingsManager"""
import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtCore import QByteArray
from src.business.services.settings_manager import SettingsManager


class TestSettingsManager:
    """Test settings management functionality"""

    @pytest.fixture
    def settings_manager(self, qtbot):
        """Create a SettingsManager instance for testing"""
        # Use a unique organization/app name for testing to avoid conflicts
        manager = SettingsManager("TestOrg", "TestApp")
        # Clear all settings before each test to ensure isolation
        manager.clear_all()
        return manager

    def test_initialization(self, settings_manager):
        """Test that SettingsManager initializes correctly"""
        assert settings_manager is not None
        assert settings_manager._settings is not None

    # ===== Window Settings Tests =====

    def test_window_geometry_get_set(self, settings_manager):
        """Test getting and setting window geometry"""
        test_geometry = QByteArray(b"test_geometry_data")
        
        settings_manager.set_window_geometry(test_geometry)
        retrieved = settings_manager.get_window_geometry()
        
        assert retrieved == test_geometry

    def test_window_geometry_none_when_not_set(self, settings_manager):
        """Test that window geometry returns None when not set"""
        assert settings_manager.get_window_geometry() is None

    def test_main_splitter_state_get_set(self, settings_manager):
        """Test getting and setting main splitter state"""
        test_state = QByteArray(b"splitter_state_data")
        
        settings_manager.set_main_splitter_state(test_state)
        retrieved = settings_manager.get_main_splitter_state()
        
        assert retrieved == test_state

    def test_default_window_size(self, settings_manager):
        """Test default window size"""
        width, height = settings_manager.get_default_window_size()
        assert width == 1200
        assert height == 800

    # ===== Library Settings Tests =====
    # Note: get/set_column_visibility was replaced by get/set_column_layout
    # Those tests are in the "New Column Layout Tests" section below

    # ===== New Column Layout Tests =====
    
    def test_column_layout_get_set(self, settings_manager):
        """Test getting and setting column layout"""
        order = [0, 2, 1, 3, 4, 5]
        hidden = [4, 5]
        
        settings_manager.set_column_layout(order, hidden, "default")
        layout = settings_manager.get_column_layout("default")
        
        assert layout["order"] == order
        assert layout["hidden"] == hidden
    
    def test_column_layout_empty_when_not_set(self, settings_manager):
        """Test that column layout returns empty dict when not set"""
        assert settings_manager.get_column_layout("default") == {}
    
    def test_column_layout_order_includes_all_columns(self, settings_manager):
        """Test that order includes all columns even hidden ones"""
        # All columns in custom order, with some hidden
        order = [0, 2, 1, 3, 4, 5, 6, 7, 8]  # All columns
        hidden = [6, 7, 8]  # Some hidden
        
        settings_manager.set_column_layout(order, hidden, "default")
        layout = settings_manager.get_column_layout("default")
        
        # Order should include all columns
        assert len(layout["order"]) == 9
        # Hidden should only include the hidden ones
        assert layout["hidden"] == [6, 7, 8]
    
    def test_column_layout_hidden_column_position_preserved(self, settings_manager):
        """Test that hidden columns keep their position in order array"""
        # Column 2 is at position 2 but hidden
        order = [0, 1, 2, 3, 4]
        hidden = [2]
        
        settings_manager.set_column_layout(order, hidden, "default")
        layout = settings_manager.get_column_layout("default")
        
        # Column 2 should still be at index 2 in order
        assert layout["order"][2] == 2
        assert 2 in layout["hidden"]
    
    def test_column_layout_named_layouts(self, settings_manager):
        """Test saving multiple named layouts"""
        order1 = [0, 1, 2, 3]
        order2 = [3, 2, 1, 0]
        
        settings_manager.set_column_layout(order1, [], "Editing")
        settings_manager.set_column_layout(order2, [0, 1], "Browsing")
        
        layout1 = settings_manager.get_column_layout("Editing")
        layout2 = settings_manager.get_column_layout("Browsing")
        
        assert layout1["order"] == order1
        assert layout2["order"] == order2
        assert layout2["hidden"] == [0, 1]


    def test_last_import_directory_get_set(self, settings_manager):
        """Test getting and setting last import directory"""
        test_dir = "/path/to/music"
        
        settings_manager.set_last_import_directory(test_dir)
        retrieved = settings_manager.get_last_import_directory()
        
        assert retrieved == test_dir

    # ===== Playback Settings Tests =====

    def test_volume_get_set(self, settings_manager):
        """Test getting and setting volume"""
        settings_manager.set_volume(75)
        assert settings_manager.get_volume() == 75

    def test_volume_default_value(self, settings_manager):
        """Test that volume returns default when not set"""
        assert settings_manager.get_volume() == 50

    def test_volume_clamping_upper_bound(self, settings_manager):
        """Test that volume is clamped to 100"""
        settings_manager.set_volume(150)
        assert settings_manager.get_volume() == 100

    def test_volume_clamping_lower_bound(self, settings_manager):
        """Test that volume is clamped to 0"""
        settings_manager.set_volume(-10)
        assert settings_manager.get_volume() == 0

    def test_last_playlist_get_set(self, settings_manager):
        """Test getting and setting last playlist"""
        playlist = ["/path/song1.mp3", "/path/song2.mp3"]
        
        settings_manager.set_last_playlist(playlist)
        retrieved = settings_manager.get_last_playlist()
        
        assert retrieved == playlist

    def test_last_playlist_empty_when_not_set(self, settings_manager):
        """Test that last playlist returns empty list when not set"""
        assert settings_manager.get_last_playlist() == []

    def test_last_song_path_get_set(self, settings_manager):
        """Test getting and setting last song path"""
        path = "/path/to/song.mp3"
        
        settings_manager.set_last_song_path(path)
        retrieved = settings_manager.get_last_song_path()
        
        assert retrieved == path

    def test_last_position_get_set(self, settings_manager):
        """Test getting and setting last playback position"""
        position = 45000  # 45 seconds in milliseconds
        
        settings_manager.set_last_position(position)
        retrieved = settings_manager.get_last_position()
        
        assert retrieved == position

    def test_last_position_default_zero(self, settings_manager):
        """Test that last position defaults to 0"""
        assert settings_manager.get_last_position() == 0

    # ===== Utility Methods Tests =====

    def test_has_setting(self, settings_manager):
        """Test checking if a setting exists"""
        assert not settings_manager.has_setting(SettingsManager.KEY_VOLUME)
        
        settings_manager.set_volume(50)
        assert settings_manager.has_setting(SettingsManager.KEY_VOLUME)

    def test_remove_setting(self, settings_manager):
        """Test removing a setting"""
        settings_manager.set_volume(75)
        assert settings_manager.has_setting(SettingsManager.KEY_VOLUME)
        
        settings_manager.remove_setting(SettingsManager.KEY_VOLUME)
        assert not settings_manager.has_setting(SettingsManager.KEY_VOLUME)
        # Should return default after removal
        assert settings_manager.get_volume() == 50

    def test_get_all_keys(self, settings_manager):
        """Test getting all setting keys"""
        settings_manager.set_volume(50)
        settings_manager.set_last_import_directory("/test")
        
        keys = settings_manager.get_all_keys()
        assert SettingsManager.KEY_VOLUME in keys
        assert SettingsManager.KEY_LAST_IMPORT_DIRECTORY in keys

    def test_sync(self, settings_manager):
        """Test that sync doesn't raise an error"""
        settings_manager.set_volume(50)
        settings_manager.sync()  # Should not raise

    def test_clear_all(self, settings_manager):
        """Test clearing all settings"""
        settings_manager.set_volume(75)
        settings_manager.set_last_import_directory("/test")
        
        settings_manager.clear_all()
        
        # Should return defaults after clear
        assert settings_manager.get_volume() == 50
        assert settings_manager.get_last_import_directory() is None

    # ===== Integration Tests =====

    def test_multiple_settings_persistence(self, settings_manager):
        """Test that multiple settings can be saved and retrieved"""
        # Set multiple settings
        settings_manager.set_volume(65)
        settings_manager.set_last_import_directory("/music")
        settings_manager.set_last_playlist(["/song1.mp3", "/song2.mp3"])
        settings_manager.set_last_position(30000)
        
        # Retrieve and verify
        assert settings_manager.get_volume() == 65
        assert settings_manager.get_last_import_directory() == "/music"
        assert settings_manager.get_last_playlist() == ["/song1.mp3", "/song2.mp3"]
        assert settings_manager.get_last_position() == 30000
