"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QAction

from ..widgets import PlaylistWidget, PlaybackControlWidget, LibraryWidget
from ...business.services import LibraryService, MetadataService, PlaybackService

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.library_service = LibraryService()
        self.metadata_service = MetadataService()
        self.playback_service = PlaybackService()

        # Settings
        self.settings = QSettings("Prodo", "Gosling2")

        # Initialize UI
        self._init_ui()
        self._load_window_geometry()
        self._load_splitter_states()
        self._setup_connections()

    def _init_ui(self):
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
        self.library_widget = LibraryWidget(self.library_service, self.metadata_service)
        
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
        self.playback_widget = PlaybackControlWidget(self.playback_service)
        main_layout.addWidget(self.playback_widget)

    def _setup_connections(self):
        """Setup signal/slot connections"""
        # Library interactions
        self.library_widget.add_to_playlist.connect(self._add_to_playlist)
        
        # Playlist interactions
        self.playlist_widget.itemDoubleClicked.connect(self._on_playlist_double_click)

        # Playback Controls
        self.playback_widget.play_pause_clicked.connect(self._toggle_play_pause)
        self.playback_widget.next_clicked.connect(self._play_next)
        self.playback_widget.volume_changed.connect(self._on_volume_changed)

        # Media Status (auto-advance)
        self.playback_service.media_status_changed.connect(self._on_media_status_changed)

    def _add_to_playlist(self, items):
        """Add items from library to playlist"""
        from PyQt6.QtWidgets import QListWidgetItem
        for item_data in items:
            path = item_data["path"]
            artist = item_data["artist"]
            title = item_data["title"]
            
            list_item = QListWidgetItem(f"{artist} | {title}")
            list_item.setData(Qt.ItemDataRole.UserRole, {"path": path})
            self.playlist_widget.addItem(list_item)

    def _on_playlist_double_click(self, item):
        """Handle playlist double-click"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and "path" in data:
            path = data["path"]
            self.playback_service.load(path)
            self.playback_service.play()
            self._update_song_label(path)

    def _toggle_play_pause(self):
        """Toggle play/pause/resume"""
        if self.playback_service.is_playing():
            self.playback_service.pause()
        elif self.playback_service.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.playback_service.play()
        elif self.playlist_widget.count() > 0:
            first_item = self.playlist_widget.item(0)
            self.playlist_widget.setCurrentRow(0)
            self._on_playlist_double_click(first_item)
        else:
            self.playback_service.play()

    def _play_next(self):
        """Play next (remove top, play new top)"""
        if self.playlist_widget.count() > 1:
            next_item = self.playlist_widget.item(1)
            if next_item:
                self.playlist_widget.setCurrentRow(1)
                self._on_playlist_double_click(next_item)
                item_to_delete = self.playlist_widget.takeItem(0)
                del item_to_delete

    def _on_volume_changed(self, value):
        self.playback_service.set_volume(value / 100.0)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()

    def _update_song_label(self, path: str):
        try:
            song = self.metadata_service.extract_from_mp3(path)
            text = f"{song.get_display_artists()} - {song.get_display_title()} ({song.get_formatted_duration()})"
            self.playback_widget.update_song_label(text)
        except Exception:
            self.playback_widget.update_song_label(os.path.basename(path))

    def closeEvent(self, event):
        """Handle window close"""
        self._save_window_geometry()
        self._save_splitter_states()
        # Column visibility is now handled by LibraryWidget settings individually
        event.accept()

    def _load_window_geometry(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Center on screen 50% size? Or default
            self.resize(1200, 800)

    def _save_window_geometry(self):
        self.settings.setValue("geometry", self.saveGeometry())

    def _load_splitter_states(self):
        splitter_state = self.settings.value("mainSplitterState")
        if splitter_state:
            self.splitter.restoreState(splitter_state)

    def _save_splitter_states(self):
        self.settings.setValue("mainSplitterState", self.splitter.saveState())
