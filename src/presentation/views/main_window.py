"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QAction

from ..widgets import PlaylistWidget, PlaybackControlWidget, LibraryWidget
from ...business.services import LibraryService, MetadataService, PlaybackService, SettingsManager

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        # Initialize Data Access Layer
        from ...data.repositories import SongRepository, ContributorRepository
        self.song_repository = SongRepository()
        self.contributor_repository = ContributorRepository()

        # Initialize Services
        self.settings_manager = SettingsManager()
        self.library_service = LibraryService(self.song_repository, self.contributor_repository)
        self.metadata_service = MetadataService()
        self.playback_service = PlaybackService(self.settings_manager)

        # Initialize UI
        self._init_ui()
        self._load_window_geometry()
        self._load_splitter_states()
        self._setup_connections()
        
        self._restore_volume()
        self._restore_playlist()

    def _init_ui(self) -> None:
        """Initialize the user interface"""
        self.setWindowTitle("Gosling2 Music Player")

        # Create central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 3, 5, 3)

        # Splitter: Library | Playlist
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Library Widget (Left/Center)
        self.library_widget = LibraryWidget(
            self.library_service, 
            self.metadata_service,
            self.settings_manager
        )
        
        # Playlist Widget (Right)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        playlist_label = QLabel("Playlist")
        self.playlist_widget = PlaylistWidget()
        right_layout.addWidget(playlist_label)
        right_layout.addWidget(self.playlist_widget)

        self.splitter.addWidget(self.library_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter, 1)

        # Bottom bar
        self.playback_widget = PlaybackControlWidget(
            self.playback_service,
            self.settings_manager
        )
        main_layout.addWidget(self.playback_widget)

    def _setup_connections(self) -> None:
        """Setup signal/slot connections"""
        # Library interactions
        self.library_widget.add_to_playlist.connect(self._add_to_playlist)
        
        # Playlist interactions
        # Double-click disabled by user request (prevent accidental play)
        # self.playlist_widget.itemDoubleClicked.connect(self._on_playlist_double_click)

        # Playback Controls
        self.playback_widget.play_pause_clicked.connect(self._toggle_play_pause)
        self.playback_widget.next_clicked.connect(self._play_next)
        self.playback_widget.volume_changed.connect(self._on_volume_changed)
        
        # Monitor playlist count
        model = self.playlist_widget.model()
        model.rowsInserted.connect(self._on_playlist_changed)
        model.rowsRemoved.connect(self._on_playlist_changed)

    def _on_playlist_changed(self, parent, start, end):
        # Update widget with new count
        self.playback_widget.set_playlist_count(self.playlist_widget.count())

        # Media Status (auto-advance)
        self.playback_service.media_status_changed.connect(self._on_media_status_changed)

    def _add_to_playlist(self, items) -> None:
        """Add items from library to playlist"""
        from PyQt6.QtWidgets import QListWidgetItem
        for item_data in items:
            path = item_data["path"]
            performer = item_data["performer"]
            title = item_data["title"]
            
            list_item = QListWidgetItem(f"{performer} | {title}")
            list_item.setData(Qt.ItemDataRole.UserRole, {"path": path})
            self.playlist_widget.addItem(list_item)

    def _play_item(self, item) -> None:
        """Play specific playlist item (Internal helper)"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and "path" in data:
            path = data["path"]
            self.playback_service.load(path)
            self.playback_service.play()
            self._update_song_label(path)

    def _toggle_play_pause(self) -> None:
        """Toggle play/pause/resume"""
        if self.playback_service.is_playing():
            self.playback_service.pause()
        elif self.playback_service.active_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.playback_service.play()
        elif self.playlist_widget.count() > 0:
            first_item = self.playlist_widget.item(0)
            self.playlist_widget.setCurrentRow(0)
            self._play_item(first_item)
        else:
            self.playback_service.play()

    def _play_next(self) -> None:
        """Play next (remove top, play new top)"""
        if self.playlist_widget.count() > 1:
            next_item = self.playlist_widget.item(1)
            if next_item:
                # Get data directly
                data = next_item.data(Qt.ItemDataRole.UserRole)
                if data and "path" in data:
                    path = data["path"]
                    # Use Crossfade-aware transition
                    self.playback_service.crossfade_to(path)
                    self._update_song_label(path)
                
                # Update UI list
                self.playlist_widget.setCurrentRow(1)
                item_to_delete = self.playlist_widget.takeItem(0)
                del item_to_delete

    def _on_volume_changed(self, value) -> None:
        self.playback_service.set_volume(value / 100.0)

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()

    def _update_song_label(self, path: str) -> None:
        try:
            song = self.metadata_service.extract_from_mp3(path)
            text = f"{song.get_display_performers()} - {song.get_display_title()} ({song.get_formatted_duration()})"
            self.playback_widget.update_song_label(text)
        except Exception:
            self.playback_widget.update_song_label(os.path.basename(path))

    def closeEvent(self, event) -> None:
        """Handle window close"""
        # Save current state before cleanup
        self._save_volume()
        self._save_playlist()
        self._save_window_geometry()
        self._save_splitter_states()
        
        # Clean up playback service resources
        self.playback_service.cleanup()
        
        event.accept()

    def _load_window_geometry(self) -> None:
        geometry = self.settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Use default size from settings manager
            width, height = self.settings_manager.get_default_window_size()
            self.resize(width, height)

    def _save_window_geometry(self) -> None:
        self.settings_manager.set_window_geometry(self.saveGeometry())

    def _load_splitter_states(self) -> None:
        splitter_state = self.settings_manager.get_main_splitter_state()
        if splitter_state:
            self.splitter.restoreState(splitter_state)

    def _save_splitter_states(self) -> None:
        self.settings_manager.set_main_splitter_state(self.splitter.saveState())
    
    def _restore_volume(self) -> None:
        """Restore saved volume level"""
        volume = self.settings_manager.get_volume()
        self.playback_widget.set_volume(volume)
    
    def _save_volume(self) -> None:
        """Save current volume level"""
        volume = self.playback_widget.get_volume()
        self.settings_manager.set_volume(volume)
    
    def _restore_playlist(self) -> None:
        """Restore last playlist"""
        playlist = self.settings_manager.get_last_playlist()
        if playlist:
            from PyQt6.QtWidgets import QListWidgetItem
            for path in playlist:
                # Try to extract metadata for display
                try:
                    song = self.metadata_service.extract_from_mp3(path)
                    display_text = f"{song.get_display_performers()} | {song.get_display_title()}"
                except Exception:
                    display_text = os.path.basename(path)
                
                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, {"path": path})
                self.playlist_widget.addItem(list_item)
        
        # Initial update of button state
        self.playback_widget.set_playlist_count(self.playlist_widget.count())
    
    def _save_playlist(self) -> None:
        """Save current playlist"""
        playlist = []
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and "path" in data:
                playlist.append(data["path"])
        self.settings_manager.set_last_playlist(playlist)
