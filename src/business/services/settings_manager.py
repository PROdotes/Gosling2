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
    KEY_RIGHT_PANEL_TAB = "window/rightPanelTab"
    
    # Library settings

    KEY_LIBRARY_LAYOUTS = "library/column_layouts"  # Robust structure (Named visibility + order)
    KEY_LAST_IMPORT_DIRECTORY = "library/lastImportDirectory"
    KEY_TYPE_FILTER = "library/typeFilter"
    
    # Playback settings
    KEY_VOLUME = "playback/volume"
    KEY_LAST_PLAYLIST = "playback/lastPlaylist"
    KEY_LAST_SONG_PATH = "playback/lastSongPath"
    KEY_LAST_POSITION = "playback/lastPosition"
    KEY_CROSSFADE_ENABLED = "playback/crossfadeEnabled"
    KEY_CROSSFADE_DURATION = "playback/crossfadeDuration"
    
    # Default values
    DEFAULT_VOLUME = 50
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    DEFAULT_CROSSFADE_ENABLED = True
    DEFAULT_CROSSFADE_DURATION = 3000
    
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
    
    def get_right_panel_tab(self) -> int:
        """Get last selected right panel tab (0 = Playlist, 1 = Editor)"""
        return int(self._settings.value(self.KEY_RIGHT_PANEL_TAB, 0))
    
    def set_right_panel_tab(self, index: int) -> None:
        """Save selected right panel tab"""
        self._settings.setValue(self.KEY_RIGHT_PANEL_TAB, index)
    
    def get_default_window_size(self) -> tuple[int, int]:
        """Get default window size"""
        return (self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
    
    # ===== Library Settings =====
    

    
    def get_last_import_directory(self) -> Optional[str]:
        """Get last directory used for importing files"""
        return self._settings.value(self.KEY_LAST_IMPORT_DIRECTORY)
    
    def set_last_import_directory(self, directory: str) -> None:
        """Save last directory used for importing files"""
        self._settings.setValue(self.KEY_LAST_IMPORT_DIRECTORY, directory)
    
    def get_type_filter(self) -> int:
        """Get last selected type tab index (0 = All)"""
        return int(self._settings.value(self.KEY_TYPE_FILTER, 0))
    
    def set_type_filter(self, index: int) -> None:
        """Save selected type tab index"""
        self._settings.setValue(self.KEY_TYPE_FILTER, index)
    
    def get_column_layout(self, layout_name: str = "default") -> Dict[str, Any]:
        """
        Get column layout (order and hidden) for a named layout.
        
        Returns dict with 'order' (list of field names) and 'hidden' (map of name -> bool).
        Returns empty dict if no layout saved.
        """
        layouts = self._settings.value(self.KEY_LIBRARY_LAYOUTS, {})
        if not isinstance(layouts, dict):
            return {}
        layout = layouts.get(layout_name, {})
        return layout.get("columns", {})
    
    def set_column_layout(self, order: list, hidden: list, layout_name: str = "default", widths: dict = None) -> None:
        """
        Save column layout (order, hidden, widths) for a named layout.
        
        Args:
            order: List of field names in visual order
            hidden: Map of hidden columns (name -> bool)
            layout_name: Name of the layout (default: "default")
            widths: Map of column widths (name -> int)
            
        Note: This is critical for persisting user resizing. LibraryWidget should call this
        BEFORE repopulating the table (e.g. on filter change) to prevent layout reset.
        """
        layouts = self._settings.value(self.KEY_LIBRARY_LAYOUTS, {})
        if not isinstance(layouts, dict):
            layouts = {}
        
        if layout_name not in layouts:
            layouts[layout_name] = {}
        
        layout_data = {
            "order": order,
            "hidden": hidden
        }
        if widths:
            layout_data["widths"] = widths
            
        layouts[layout_name]["columns"] = layout_data
        layouts["_active"] = layout_name
        
        self._settings.setValue(self.KEY_LIBRARY_LAYOUTS, layouts)
        self._settings.sync()
    
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
        
    def get_crossfade_enabled(self) -> bool:
        """Get whether crossfade is enabled"""
        return self._settings.value(self.KEY_CROSSFADE_ENABLED, self.DEFAULT_CROSSFADE_ENABLED, type=bool)

    def set_crossfade_enabled(self, enabled: bool) -> None:
        """Set whether crossfade is enabled"""
        self._settings.setValue(self.KEY_CROSSFADE_ENABLED, enabled)

    def get_crossfade_duration(self) -> int:
        """Get crossfade duration in milliseconds"""
        return self._settings.value(self.KEY_CROSSFADE_DURATION, self.DEFAULT_CROSSFADE_DURATION, type=int)

    def set_crossfade_duration(self, duration: int) -> None:
        """Set crossfade duration in milliseconds"""
        self._settings.setValue(self.KEY_CROSSFADE_DURATION, duration)
    
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
