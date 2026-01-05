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
    KEY_V_SPLITTER_STATE = "window/vSplitterState"
    KEY_RIGHT_PANEL_SPLITTER_STATE = "window/rightPanelSplitterState"
    KEY_RIGHT_PANEL_TOGGLES = "window/rightPanelToggles" # JSON: {history: bool, editor: bool, compact: bool}
    KEY_RIGHT_PANEL_TAB = "window/rightPanelTab"
    KEY_RIGHT_PANEL_WIDTH_EDITOR = "window/rightPanelWidthEditor"
    KEY_RIGHT_PANEL_WIDTH_NORMAL = "window/rightPanelWidthNormal"
    
    # Library settings

    KEY_LIBRARY_LAYOUTS = "library/column_layouts"  # Robust structure (Named visibility + order)
    KEY_LAST_IMPORT_DIRECTORY = "library/lastImportDirectory"
    KEY_TYPE_FILTER = "library/typeFilter"
    KEY_ROOT_DIRECTORY = "library/rootDirectory"
    KEY_DATABASE_PATH = "library/databasePath"
    KEY_LOG_PATH = "library/logPath"
    KEY_DEFAULT_YEAR = "library/defaultYear"
    
    # Renaming/Moving settings
    KEY_RENAME_PATTERN = "rules/renamePattern"
    KEY_RENAME_ENABLED = "rules/renameEnabled"
    KEY_MOVE_AFTER_DONE = "rules/moveAfterDone"
    
    # Playback settings
    KEY_VOLUME = "playback/volume"
    KEY_LAST_PLAYLIST = "playback/lastPlaylist"
    KEY_LAST_SONG_PATH = "playback/lastSongPath"
    KEY_LAST_POSITION = "playback/lastPosition"
    KEY_CROSSFADE_ENABLED = "playback/crossfadeEnabled"
    KEY_CROSSFADE_DURATION = "playback/crossfadeDuration"
    
    # Conversion settings
    KEY_CONVERSION_ENABLED = "conversion/enabled"
    KEY_CONVERSION_BITRATE = "conversion/bitrate" # e.g. "320k"
    KEY_FFMPEG_PATH = "conversion/ffmpegPath"
    KEY_DELETE_WAV_AFTER_CONVERSION = "conversion/deleteWavAfterConversion"
    KEY_DELETE_ZIP_AFTER_IMPORT = "library/deleteZipAfterImport"
    
    # Search Settings (T-81)
    KEY_SEARCH_PROVIDER = "search/provider"
    
    # Filter Tree Settings
    KEY_FILTER_TREE_EXPANSION = "filter_tree/expansion_state"
    
    # Default values
    DEFAULT_VOLUME = 50
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    DEFAULT_CROSSFADE_ENABLED = True
    DEFAULT_CROSSFADE_DURATION = 3000
    DEFAULT_ROOT_DIRECTORY = "C:/GoslingLibrary"
    DEFAULT_RENAME_PATTERN = "{Artist}/{Album}/{Title}"
    DEFAULT_RENAME_ENABLED = True
    DEFAULT_MOVE_AFTER_DONE = True
    
    DEFAULT_CONVERSION_ENABLED = False
    DEFAULT_CONVERSION_BITRATE = "320k"
    DEFAULT_FFMPEG_PATH = "ffmpeg"
    DEFAULT_SEARCH_PROVIDER = "Google"
    DEFAULT_YEAR = 0 # 0 = Dynamic (Current Year)
    
    def __init__(self, organization: str = "Prodo", application: str = "Gosling2"):
        """
        Initialize settings manager.
        Uses INI format for easy manual editing.
        """
        self._settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, organization, application)
        # Fallback to local file if needed? UserScope puts it in AppData.
        # If user wants it next to exe, we might need absolute path.
        # For now, standard User location is safer than Program Files.
    
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
    
    def get_v_splitter_state(self) -> Optional[QByteArray]:
        """Get saved vertical splitter state"""
        return self._settings.value(self.KEY_V_SPLITTER_STATE)
    
    def set_v_splitter_state(self, state: QByteArray) -> None:
        """Save vertical splitter state"""
        self._settings.setValue(self.KEY_V_SPLITTER_STATE, state)
    
    def get_right_panel_tab(self) -> int:
        """Get last selected right panel tab (0 = Playlist, 1 = Editor)"""
        return int(self._settings.value(self.KEY_RIGHT_PANEL_TAB, 0))
    
    def set_right_panel_tab(self, index: int) -> None:
        """Save selected right panel tab"""
        self._settings.setValue(self.KEY_RIGHT_PANEL_TAB, index)
    
    def get_splitter_state_by_mode(self, mode: str) -> Optional[QByteArray]:
        """Get splitter state for a specific mode ('log' or 'edit')."""
        return self._settings.value(f"window/splitter/{mode}")

    def set_splitter_state_by_mode(self, mode: str, state: QByteArray) -> None:
        """Save splitter state for a specific mode."""
        self._settings.setValue(f"window/splitter/{mode}", state)

    def get_right_panel_splitter_state(self) -> Optional[QByteArray]:
        """Get saved right panel splitter state"""
        return self._settings.value(self.KEY_RIGHT_PANEL_SPLITTER_STATE)

    def set_right_panel_splitter_state(self, state: QByteArray) -> None:
        """Save right panel vertical splitter state"""
        self._settings.setValue(self.KEY_RIGHT_PANEL_SPLITTER_STATE, state)
        
    def get_right_panel_width_editor(self) -> int:
        return int(self._settings.value(self.KEY_RIGHT_PANEL_WIDTH_EDITOR, 500))
        
    def set_right_panel_width_editor(self, width: int) -> None:
        self._settings.setValue(self.KEY_RIGHT_PANEL_WIDTH_EDITOR, width)
        
    def get_right_panel_width_normal(self) -> int:
        return int(self._settings.value(self.KEY_RIGHT_PANEL_WIDTH_NORMAL, 350))
        
    def set_right_panel_width_normal(self, width: int) -> None:
        self._settings.setValue(self.KEY_RIGHT_PANEL_WIDTH_NORMAL, width)

    def get_right_panel_toggles(self) -> dict:
        """Get visibility states: {'history': bool, 'editor': bool, 'compact': bool}"""
        return self._settings.value(self.KEY_RIGHT_PANEL_TOGGLES, {'history': False, 'editor': False, 'compact': False})

    def set_right_panel_toggles(self, states: dict) -> None:
        """Save visibility states"""
        self._settings.setValue(self.KEY_RIGHT_PANEL_TOGGLES, states)
    
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

    def get_root_directory(self) -> str:
        """Get the root directory for file organization"""
        return self._settings.value(self.KEY_ROOT_DIRECTORY, self.DEFAULT_ROOT_DIRECTORY, type=str)
        
    def set_root_directory(self, path: str) -> None:
        """Set the root directory for file organization"""
        self._settings.setValue(self.KEY_ROOT_DIRECTORY, path)

    def get_database_path(self) -> Optional[str]:
        """Get the custom database path. Returns None if default should be used."""
        return self._settings.value(self.KEY_DATABASE_PATH)
        
    def set_database_path(self, path: str) -> None:
        """Set a custom database path."""
        self._settings.setValue(self.KEY_DATABASE_PATH, path)

    def get_log_path(self) -> Optional[str]:
        """Get the custom log path. Returns None if default should be used."""
        return self._settings.value(self.KEY_LOG_PATH)
        
    def set_log_path(self, path: str) -> None:
        """Set a custom log path."""
        self._settings.setValue(self.KEY_LOG_PATH, path)

    def get_default_year(self) -> int:
        """Get default year for auto-fill (0 = Dynamic/Current)."""
        return int(self._settings.value(self.KEY_DEFAULT_YEAR, self.DEFAULT_YEAR))

    def set_default_year(self, year: int) -> None:
        """Set default year for auto-fill."""
        self._settings.setValue(self.KEY_DEFAULT_YEAR, year)

    # ===== Renaming Rules =====
    
    def get_rename_pattern(self) -> str:
        return self._settings.value(self.KEY_RENAME_PATTERN, self.DEFAULT_RENAME_PATTERN, type=str)
        
    def set_rename_pattern(self, pattern: str) -> None:
        self._settings.setValue(self.KEY_RENAME_PATTERN, pattern)

    def get_rename_enabled(self) -> bool:
        return self._settings.value(self.KEY_RENAME_ENABLED, self.DEFAULT_RENAME_ENABLED, type=bool)

    def set_rename_enabled(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_RENAME_ENABLED, enabled)

    def get_move_after_done(self) -> bool:
        return self._settings.value(self.KEY_MOVE_AFTER_DONE, self.DEFAULT_MOVE_AFTER_DONE, type=bool)

    def set_move_after_done(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_MOVE_AFTER_DONE, enabled)
    
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

    # ===== Conversion Settings =====

    def get_conversion_enabled(self) -> bool:
        return self._settings.value(self.KEY_CONVERSION_ENABLED, False, type=bool)

    def set_conversion_enabled(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_CONVERSION_ENABLED, enabled)

    def get_conversion_bitrate(self) -> str:
        return self._settings.value(self.KEY_CONVERSION_BITRATE, self.DEFAULT_CONVERSION_BITRATE, type=str)

    def set_conversion_bitrate(self, bitrate: str) -> None:
        self._settings.setValue(self.KEY_CONVERSION_BITRATE, bitrate)

    def get_ffmpeg_path(self) -> str:
        return self._settings.value(self.KEY_FFMPEG_PATH, self.DEFAULT_FFMPEG_PATH, type=str)

    def set_ffmpeg_path(self, path: str) -> None:
        self._settings.setValue(self.KEY_FFMPEG_PATH, path)

    def get_delete_wav_after_conversion(self) -> bool:
        return self._settings.value(self.KEY_DELETE_WAV_AFTER_CONVERSION, False, type=bool)

    def set_delete_wav_after_conversion(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_DELETE_WAV_AFTER_CONVERSION, enabled)

    def get_delete_zip_after_import(self) -> bool:
        return self._settings.value(self.KEY_DELETE_ZIP_AFTER_IMPORT, False, type=bool)

    def set_delete_zip_after_import(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_DELETE_ZIP_AFTER_IMPORT, enabled)

    # ===== Search Settings (T-81) =====
    
    def get_search_provider(self) -> str:
        return self._settings.value(self.KEY_SEARCH_PROVIDER, self.DEFAULT_SEARCH_PROVIDER, type=str)

    def set_search_provider(self, provider: str) -> None:
        self._settings.setValue(self.KEY_SEARCH_PROVIDER, provider)
    
    # ===== Filter Tree Settings =====
    
    def get_filter_tree_expansion_state(self) -> dict:
        """Get saved expansion state for filter tree items."""
        import json
        state_json = self._settings.value(self.KEY_FILTER_TREE_EXPANSION, "{}", type=str)
        try:
            return json.loads(state_json)
        except:
            return {}
    
    def set_filter_tree_expansion_state(self, state: dict) -> None:
        """Save expansion state for filter tree items."""
        import json
        state_json = json.dumps(state)
        self._settings.setValue(self.KEY_FILTER_TREE_EXPANSION, state_json)
    
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
