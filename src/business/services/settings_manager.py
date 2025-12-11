"""Settings management service for application-wide settings"""
from typing import Optional, Dict, Any
from PyQt6.QtCore import QSettings, QByteArray


class SettingsManager:
    """Centralized settings management for the application"""
    
    # Settings keys as constants
    # Window settings
    KEY_WINDOW_GEOMETRY = "window/geometry"
    KEY_WINDOW_SIZE = "window/size"
    KEY_MAIN_SPLITTER_STATE = "window/mainSplitterState"
    
    # Library settings
    KEY_COLUMN_VISIBILITY = "library/columnVisibility"
    KEY_LAST_IMPORT_DIRECTORY = "library/lastImportDirectory"
    
    # Playback settings
    KEY_VOLUME = "playback/volume"
    KEY_LAST_PLAYLIST = "playback/lastPlaylist"
    KEY_LAST_SONG_PATH = "playback/lastSongPath"
    KEY_LAST_POSITION = "playback/lastPosition"
    
    # Default values
    DEFAULT_VOLUME = 50
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    
    def __init__(self, organization: str = "Prodo", application: str = "Gosling2"):
        """
        Initialize settings manager
        
        Args:
            organization: Organization name for settings storage
            application: Application name for settings storage
        """
        self._settings = QSettings(organization, application)
    
    # ===== Window Settings =====
    
    def get_window_geometry(self) -> Optional[QByteArray]:
        """Get saved window geometry"""
        return self._settings.value(self.KEY_WINDOW_GEOMETRY)
    
    def set_window_geometry(self, geometry: QByteArray) -> None:
        """Save window geometry"""
        self._settings.setValue(self.KEY_WINDOW_GEOMETRY, geometry)
    
    def get_main_splitter_state(self) -> Optional[QByteArray]:
        """Get saved main splitter state"""
        return self._settings.value(self.KEY_MAIN_SPLITTER_STATE)
    
    def set_main_splitter_state(self, state: QByteArray) -> None:
        """Save main splitter state"""
        self._settings.setValue(self.KEY_MAIN_SPLITTER_STATE, state)
    
    def get_default_window_size(self) -> tuple[int, int]:
        """Get default window size"""
        return (self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
    
    # ===== Library Settings =====
    
    def get_column_visibility(self) -> Dict[str, bool]:
        """Get column visibility states"""
        return self._settings.value(self.KEY_COLUMN_VISIBILITY, {})
    
    def set_column_visibility(self, visibility_states: Dict[str, bool]) -> None:
        """Save column visibility states"""
        self._settings.setValue(self.KEY_COLUMN_VISIBILITY, visibility_states)
    
    def get_last_import_directory(self) -> Optional[str]:
        """Get last directory used for importing files"""
        return self._settings.value(self.KEY_LAST_IMPORT_DIRECTORY)
    
    def set_last_import_directory(self, directory: str) -> None:
        """Save last directory used for importing files"""
        self._settings.setValue(self.KEY_LAST_IMPORT_DIRECTORY, directory)
    
    # ===== Playback Settings =====
    
    def get_volume(self) -> int:
        """
        Get saved volume level
        
        Returns:
            Volume level (0-100), defaults to DEFAULT_VOLUME if not set
        """
        return self._settings.value(self.KEY_VOLUME, self.DEFAULT_VOLUME, type=int)
    
    def set_volume(self, volume: int) -> None:
        """
        Save volume level
        
        Args:
            volume: Volume level (0-100)
        """
        # Clamp volume to valid range
        volume = max(0, min(100, volume))
        self._settings.setValue(self.KEY_VOLUME, volume)
    
    def get_last_playlist(self) -> list[str]:
        """Get last playlist (list of file paths)"""
        playlist = self._settings.value(self.KEY_LAST_PLAYLIST, [])
        # Ensure it's a list
        if not isinstance(playlist, list):
            return []
        return playlist
    
    def set_last_playlist(self, playlist: list[str]) -> None:
        """Save last playlist"""
        self._settings.setValue(self.KEY_LAST_PLAYLIST, playlist)
    
    def get_last_song_path(self) -> Optional[str]:
        """Get path of last played song"""
        return self._settings.value(self.KEY_LAST_SONG_PATH)
    
    def set_last_song_path(self, path: str) -> None:
        """Save path of last played song"""
        self._settings.setValue(self.KEY_LAST_SONG_PATH, path)
    
    def get_last_position(self) -> int:
        """Get last playback position in milliseconds"""
        return self._settings.value(self.KEY_LAST_POSITION, 0, type=int)
    
    def set_last_position(self, position: int) -> None:
        """Save last playback position in milliseconds"""
        self._settings.setValue(self.KEY_LAST_POSITION, position)
    
    # ===== Utility Methods =====
    
    def clear_all(self) -> None:
        """Clear all settings (use with caution!)"""
        self._settings.clear()
    
    def sync(self) -> None:
        """Force synchronization of settings to disk"""
        self._settings.sync()
    
    def get_all_keys(self) -> list[str]:
        """Get all setting keys (useful for debugging)"""
        return self._settings.allKeys()
    
    def has_setting(self, key: str) -> bool:
        """Check if a setting exists"""
        return self._settings.contains(key)
    
    def remove_setting(self, key: str) -> None:
        """Remove a specific setting"""
        self._settings.remove(key)
