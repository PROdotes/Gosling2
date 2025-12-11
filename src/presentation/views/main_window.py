"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QTableView, QPushButton, QLabel, QSlider,
    QLineEdit, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction
from PyQt6.QtCore import Qt, QSettings, QSortFilterProxyModel, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer

from ..widgets import SeekSlider, PlaylistWidget
from ...business.services import LibraryService, MetadataService, PlaybackService
from ...data.models import Song


GREEN_HEX = "5f8a53"


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
        self._setup_connections()
        self._load_library()

    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Gosling2 Music Player")

        # Create central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 3, 5, 3)

        # Setup UI sections
        self._setup_top_controls(main_layout)
        self._setup_middle_panels(main_layout)
        self._setup_bottom_bar(main_layout)

    def _setup_top_controls(self, parent_layout):
        """Setup top control buttons"""
        top_layout = QHBoxLayout()

        # Add buttons
        self.btn_import = QPushButton("Import File(s)")
        self.btn_scan_folder = QPushButton("Scan Folder")
        self.btn_refresh = QPushButton("Refresh Library")

        top_layout.addWidget(self.btn_import)
        top_layout.addWidget(self.btn_scan_folder)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addStretch()

        parent_layout.addLayout(top_layout)

    def _setup_middle_panels(self, parent_layout):
        """Setup middle panels with splitters"""
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Filter tree
        self.filter_tree_model = QStandardItemModel()
        self.filter_tree_view = QTreeView()
        self.filter_tree_view.setModel(self.filter_tree_model)
        self.filter_tree_view.setHeaderHidden(True)

        # Center panel - Library table
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search library...")

        self.library_model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.library_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.setSortingEnabled(True)

        center_layout.addWidget(self.search_box)
        center_layout.addWidget(self.table_view)

        # Right panel - Playlist
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        playlist_label = QLabel("Playlist")
        self.playlist_widget = PlaylistWidget()

        right_layout.addWidget(playlist_label)
        right_layout.addWidget(self.playlist_widget)

        # Add panels to splitter
        splitter.addWidget(self.filter_tree_view)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        parent_layout.addWidget(splitter, 1)

    def _setup_bottom_bar(self, parent_layout):
        """Setup bottom playback controls"""
        bottom_layout = QVBoxLayout()

        # Song info label
        self.song_label = QLabel("No song loaded")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Seek slider
        self.playback_slider = SeekSlider()
        self.playback_slider.setPlayer(self.playback_service.player)

        # Playback controls
        controls_layout = QHBoxLayout()

        self.btn_previous = QPushButton("⏮")
        self.btn_play_pause = QPushButton("▶")
        self.btn_stop = QPushButton("⏹")
        self.btn_next = QPushButton("⏭")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)

        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_previous)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addWidget(QLabel("Volume:"))
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addStretch()

        bottom_layout.addWidget(self.song_label)
        bottom_layout.addWidget(self.playback_slider)
        bottom_layout.addLayout(controls_layout)

        parent_layout.addLayout(bottom_layout)

    def _setup_connections(self):
        """Setup signal/slot connections"""
        # Top controls
        self.btn_import.clicked.connect(self._import_files)
        self.btn_scan_folder.clicked.connect(self._scan_folder)
        self.btn_refresh.clicked.connect(self._load_library)

        # Search
        self.search_box.textChanged.connect(self._on_search)

        # Table
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(self._on_table_double_click)

        # Playlist
        self.playlist_widget.itemDoubleClicked.connect(self._on_playlist_double_click)

        # Playback controls
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        self.btn_stop.clicked.connect(self._stop_playback)
        self.btn_previous.clicked.connect(self._play_previous)
        self.btn_next.clicked.connect(self._play_next)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        # Playback service signals
        self.playback_service.position_changed.connect(self._update_position)
        self.playback_service.media_status_changed.connect(self._on_media_status_changed)
        self.playback_service.state_changed.connect(self._on_playback_state_changed)

    def _load_window_geometry(self):
        """Load window geometry from settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 800)

    def _save_window_geometry(self):
        """Save window geometry to settings"""
        self.settings.setValue("geometry", self.saveGeometry())

    def _load_library(self):
        """Load library from database"""
        headers, data = self.library_service.get_all_songs()

        self.library_model.clear()
        if headers:
            self.library_model.setHorizontalHeaderLabels(headers)

        for row_data in data:
            items = [QStandardItem(str(cell) if cell else "") for cell in row_data]
            self.library_model.appendRow(items)

        # Resize columns
        self.table_view.resizeColumnsToContents()

    def _import_files(self):
        """Import files to library"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.mp3 *.flac *.wav *.m4a)"
        )

        if not files:
            return

        imported_count = 0
        for file_path in files:
            try:
                # Add to database
                file_id = self.library_service.add_file(file_path)
                if file_id:
                    # Extract and update metadata
                    song = self.metadata_service.extract_from_mp3(file_path, file_id)
                    self.library_service.update_song(song)
                    imported_count += 1
            except Exception as e:
                print(f"Error importing {file_path}: {e}")

        if imported_count > 0:
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {imported_count} file(s)"
            )
            self._load_library()

    def _scan_folder(self):
        """Scan folder for audio files"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        imported_count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.flac', '.wav', '.m4a')):
                    file_path = os.path.join(root, file)
                    try:
                        file_id = self.library_service.add_file(file_path)
                        if file_id:
                            song = self.metadata_service.extract_from_mp3(file_path, file_id)
                            self.library_service.update_song(song)
                            imported_count += 1
                    except Exception as e:
                        print(f"Error importing {file_path}: {e}")

        if imported_count > 0:
            QMessageBox.information(
                self,
                "Scan Complete",
                f"Imported {imported_count} file(s)"
            )
            self._load_library()

    def _on_search(self, text):
        """Handle search text change"""
        self.proxy_model.setFilterWildcard(f"*{text}*")

    def _show_table_context_menu(self, position):
        """Show context menu for table"""
        menu = QMenu()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        add_to_playlist_action = QAction("Add to Playlist", self)
        add_to_playlist_action.triggered.connect(self._add_selected_to_playlist)
        menu.addAction(add_to_playlist_action)

        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _delete_selected(self):
        """Delete selected songs"""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {len(indexes)} song(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for index in indexes:
                source_index = self.proxy_model.mapToSource(index)
                file_id_item = self.library_model.item(source_index.row(), 0)
                if file_id_item:
                    file_id = int(file_id_item.text())
                    self.library_service.delete_song(file_id)

            self._load_library()

    def _add_selected_to_playlist(self):
        """Add selected songs to playlist"""
        indexes = self.table_view.selectionModel().selectedRows()
        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            path_item = self.library_model.item(source_index.row(), 4)  # Path column
            artist_item = self.library_model.item(source_index.row(), 1)
            title_item = self.library_model.item(source_index.row(), 2)

            if path_item:
                path = path_item.text()
                artist = artist_item.text() if artist_item else "Unknown"
                title = title_item.text() if title_item else "Unknown"

                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(f"{artist} | {title}")
                item.setData(Qt.ItemDataRole.UserRole, {"path": path})
                self.playlist_widget.addItem(item)

    def _on_table_double_click(self, index):
        """Handle table double-click"""
        source_index = self.proxy_model.mapToSource(index)
        path_item = self.library_model.item(source_index.row(), 4)

        if path_item:
            path = path_item.text()
            self.playback_service.load(path)
            self.playback_service.play()
            self._update_song_label(path)

    def _on_playlist_double_click(self, item):
        """Handle playlist double-click"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and "path" in data:
            path = data["path"]
            self.playback_service.load(path)
            self.playback_service.play()
            self._update_song_label(path)

    def _toggle_play_pause(self):
        """Toggle play/pause"""
        if self.playback_service.is_playing():
            self.playback_service.pause()
        else:
            self.playback_service.play()

    def _stop_playback(self):
        """Stop playback"""
        self.playback_service.stop()

    def _play_previous(self):
        """Play previous song"""
        current_row = self.playlist_widget.currentRow()
        if current_row > 0:
            self.playlist_widget.setCurrentRow(current_row - 1)
            item = self.playlist_widget.currentItem()
            if item:
                self._on_playlist_double_click(item)

    def _play_next(self):
        """Play next song"""
        current_row = self.playlist_widget.currentRow()
        if current_row < self.playlist_widget.count() - 1:
            self.playlist_widget.setCurrentRow(current_row + 1)
            item = self.playlist_widget.currentItem()
            if item:
                self._on_playlist_double_click(item)

    def _on_volume_changed(self, value):
        """Handle volume change"""
        self.playback_service.set_volume(value / 100.0)

    def _update_position(self, position):
        """Update playback position"""
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(position)
        self.playback_slider.blockSignals(False)

    def _on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()

    def _on_playback_state_changed(self, state):
        """Handle playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("⏸")
        else:
            self.btn_play_pause.setText("▶")

    def _update_song_label(self, path: str):
        """Update the current song label"""
        try:
            song = self.metadata_service.extract_from_mp3(path)
            text = f"{song.get_display_artists()} - {song.get_display_title()} ({song.get_formatted_duration()})"
            self.song_label.setText(text)
        except Exception:
            self.song_label.setText(os.path.basename(path))

    def closeEvent(self, event):
        """Handle window close"""
        self._save_window_geometry()
        event.accept()

