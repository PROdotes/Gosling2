"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QMenu, QMessageBox,
    QSizeGrip
)
from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QAction

from ..widgets import (
    PlaylistWidget, PlaybackControlWidget, LibraryWidget, 
    SidePanelWidget, CustomTitleBar, JingleCurtain, HistoryDrawer
)
from ...business.services import LibraryService, MetadataService, PlaybackService, SettingsManager, RenamingService, DuplicateScannerService
from PyQt6.QtWidgets import (
    QPushButton, QFrame
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import pyqtSignal, QSize, QItemSelectionModel

class ResizeGrip(QWidget):
    """Custom resize grip with visible triangle indicator"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._pressing = False
        self._start_pos = None
        self._start_geometry = None
    
    def mousePressEvent(self, event):
        """Start resize operation"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = True
            self._start_pos = event.globalPosition().toPoint()
            self._start_geometry = self.window().geometry()
    
    def mouseMoveEvent(self, event):
        """Handle resize dragging"""
        if self._pressing and self._start_pos and self._start_geometry:
            delta = event.globalPosition().toPoint() - self._start_pos
            new_width = max(self._start_geometry.width() + delta.x(), self.window().minimumWidth())
            new_height = max(self._start_geometry.height() + delta.y(), self.window().minimumHeight())
            self.window().resize(new_width, new_height)
    
    def mouseReleaseEvent(self, event):
        """End resize operation"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = False
            self._start_pos = None
            self._start_geometry = None
    
    def paintEvent(self, event):
        """Draw diagonal lines forming a resize triangle"""
        from PyQt6.QtGui import QPainter, QPen
        from PyQt6.QtCore import QPoint
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Transparent background - no fill needed
        
        # Draw three diagonal lines forming a triangle grip
        pen = QPen(QColor("#555555"), 2.0)
        painter.setPen(pen)
        
        # Line 1 (bottom-most)
        painter.drawLine(QPoint(10, 14), QPoint(14, 10))
        # Line 2 (middle)
        painter.drawLine(QPoint(6, 14), QPoint(14, 6))
        # Line 3 (top-most)
        painter.drawLine(QPoint(2, 14), QPoint(14, 2))
        
        painter.end()

class TerminalHeader(QFrame):
    """Custom header for the Independent Operations Terminal."""
    prep_toggled = pyqtSignal(bool)
    jingles_toggled = pyqtSignal(bool)
    history_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setObjectName("TerminalHeader")
        self.setStyleSheet("""
            #TerminalHeader {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #1A1A1A, stop:0.4 #222, 
                                          stop:0.5 #2A2A2A, stop:0.6 #222, 
                                          stop:1 #1A1A1A);
                border-bottom: 2px solid #000;
                border-top: 1px solid #333;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        # 1. The Dots (Independent Terminal Feel)
        dots_container = QWidget()
        dots_layout = QHBoxLayout(dots_container)
        dots_layout.setContentsMargins(0, 0, 0, 0)
        dots_layout.setSpacing(6)
        
        for color in ["#FF5F56", "#FFBD2E", "#27C93F"]:
            dot = QFrame()
            dot.setFixedSize(11, 11)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
            dots_layout.addWidget(dot)
        
        layout.addWidget(dots_container)
        layout.addStretch()
        
        # 2. UTILITY TOGGLES
        self.history_btn = self._create_toggle("LOG", self.history_toggled)
        self.jingle_btn = self._create_toggle("CHIPS", self.jingles_toggled)
        
        layout.addWidget(self.history_btn)
        layout.addWidget(self.jingle_btn)
        
        # 3. THE BIG HINGE (Prep Mode)
        self.prep_btn = QPushButton("[ PREP LOG ]")
        self.prep_btn.setCheckable(True)
        self.prep_btn.setFixedWidth(120)
        self.prep_btn.setObjectName("PrepLogButton")
        self.prep_btn.setStyleSheet("""
            QPushButton#PrepLogButton {
                background-color: #080808;
                border: 1px solid #333;
                border-radius: 4px;
                color: #888;
                font-family: 'Agency FB', 'Bahnschrift Condensed';
                font-weight: bold;
                font-size: 10pt;
                letter-spacing: 2px;
            }
            QPushButton#PrepLogButton:hover { border-color: #FF8BA0; color: #CCC; }
            QPushButton#PrepLogButton:checked {
                background-color: #1A1208;
                border: 1px solid #FF8C00;
                color: #FF8C00;
            }
        """)
        self.prep_btn.toggled.connect(self.prep_toggled.emit)
        layout.addWidget(self.prep_btn)
        
        layout.addStretch()
        
        # 4. THE LED (Status)
        self.status_led = QFrame()
        self.status_led.setFixedSize(8, 8)
        self.status_led.setStyleSheet("background-color: #222; border-radius: 4px;")
        layout.addWidget(self.status_led)
        
        self.prep_btn.toggled.connect(self._on_prep_toggled)

    def _create_toggle(self, text, signal):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedSize(50, 22)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #111;
                border: 1px solid #222;
                border-radius: 3px;
                color: #555;
                font-family: 'Agency FB';
                font-size: 8pt;
                font-weight: bold;
            }
            QPushButton:hover { border-color: #444; color: #888; }
            QPushButton:checked {
                border-color: #FF8C00;
                color: #FF8C00;
                background-color: #000;
            }
        """)
        btn.toggled.connect(signal.emit)
        return btn

    def _on_prep_toggled(self, checked):
        if checked:
            self.status_led.setStyleSheet("background-color: #FF8C00; border: 1px solid #FFD580; border-radius: 4px;")
        else:
            self.status_led.setStyleSheet("background-color: #222; border-radius: 4px;")

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        # 1. Initialize Settings First (Required for Hardware Unlocking)
        self.settings_manager = SettingsManager()
        db_path = self.settings_manager.get_database_path()

        # 2. Initialize Data Access Layer with injected path
        from ...data.repositories import SongRepository, ContributorRepository, AlbumRepository
        self.song_repository = SongRepository(db_path)
        self.contributor_repository = ContributorRepository(db_path)
        self.album_repository = AlbumRepository(db_path)

        # 3. Initialize Business Services
        self.library_service = LibraryService(
            self.song_repository, 
            self.contributor_repository, 
            self.album_repository
        )
        self.metadata_service = MetadataService()
        self.playback_service = PlaybackService(self.settings_manager)
        self.renaming_service = RenamingService(self.settings_manager)
        self.duplicate_scanner = DuplicateScannerService(self.library_service)

        # Initialize UI
        self._init_ui()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        # Hide status bar to prevent automatic size grip
        self.setStatusBar(None)
        
        self._load_window_geometry()
        self._load_splitter_states()
        # Setup Connections
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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Global Industrial Amber Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #0A0A0A; }
            QWidget { color: #DDD; }
            
            /* Industrial Amber Scrollbars */
            QScrollBar:vertical {
                border: none;
                background: #0F0F0F;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #333;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #FF8C00;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #0F0F0F;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #333;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #FF8C00;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            QToolTip {
                background-color: #1A1A1A;
                color: #FF8C00;
                border: 1px solid #FF8C00;
            }
        """)
        
        # 0. Integrated Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        main_layout.addWidget(self.title_bar)

        # Content Container (where margins apply)
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container) # Root is Horizontal to allow Right Panel Full Height
        content_layout.setContentsMargins(5, 5, 0, 0) # No bottom/right margin for flush docking
        content_layout.setSpacing(1)
        main_layout.addWidget(content_container, 1)

        # === THE MAIN SPLITTER (Left/Center Block | Right Panel) ===
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("MainRootSplitter")
        # Handle width controlled by QSS

        # --- LEFT+CENTER BLOCK (Archive + Library + Scrubber) ---
        lc_container = QWidget()
        lc_layout = QVBoxLayout(lc_container)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setSpacing(0)
        
        # LC Splitter (Archive | Library)
        self.lc_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.lc_splitter.setHandleWidth(1)
        
        # 1. Archive/Library (Currently just LibraryWidget acting as both)
        self.library_widget = LibraryWidget(
            self.library_service, 
            self.metadata_service,
            self.settings_manager,
            self.renaming_service,
            self.duplicate_scanner
        )
        self.lc_splitter.addWidget(self.library_widget)
        
        lc_layout.addWidget(self.lc_splitter, 1)
        
        # 2. FOOTER (Scrubber)
        self.playback_widget = PlaybackControlWidget(
            self.playback_service,
            self.settings_manager
        )
        self.playback_widget.setObjectName("PlaybackDeck")
        lc_layout.addWidget(self.playback_widget)
        
        # Add LC Block to Main Splitter
        self.main_splitter.addWidget(lc_container)

        # --- RIGHT PANEL (Command Deck) ---
        from ..widgets.right_panel_widget import RightPanelWidget
        self.right_panel = RightPanelWidget(
            self.library_service,
            self.metadata_service,
            self.renaming_service,
            self.duplicate_scanner,
            self.settings_manager
        )
        self.main_splitter.addWidget(self.right_panel)
        
        # COMPATIBILITY ALIAS: Mapping legacy self.playlist_widget to the new nested instance
        # This prevents crashes in _play_next, _toggle_play_pause, etc.
        self.playlist_widget = self.right_panel.playlist_widget
        
        # Stretches: LC=1 (Taking all space), R=0 (Fixed/Respected Size)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        # Prevent Center (Library) from collapsing to 0
        self.main_splitter.setCollapsible(0, False)
        # Prevent Right Panel from collapsing to 0 (Hard Stop)
        self.main_splitter.setCollapsible(1, False)

        content_layout.addWidget(self.main_splitter)
        
        # Add resize grip to bottom-right corner (for frameless window)
        self.size_grip = ResizeGrip(self)
        # Position it in the bottom-right corner
        self.size_grip.raise_()


    def _setup_connections(self) -> None:
        """Setup signal/slot connections"""
        # --- Library Signals ---
        self.library_widget.add_to_playlist.connect(self._add_to_playlist)
        self.library_widget.remove_from_playlist.connect(self._remove_from_playlist)
        self.library_widget.play_immediately.connect(self._play_path_now)
        
        # Connect Selection -> Right Panel Facade
        self.library_widget.table_view.selectionModel().selectionChanged.connect(self._on_library_selection_changed)

        # --- Right Panel (Command Deck) Signals ---
        self.right_panel.transport_command.connect(self._handle_transport_command)
        self.right_panel.transition_command.connect(self._handle_transition_command)
        
        # --- Editor Signals (Transient Wiring) ---
        # Direct access to inner widget until SidePanel refactor is complete
        editor = self.right_panel.editor_widget
        editor.save_requested.connect(self._on_side_panel_save_requested)
        editor.staging_changed.connect(self.library_widget.update_dirty_rows)
        
        # --- Playlist Signals (Transient Wiring) ---
        # Access inner Playlist widget
        playlist = self.right_panel.playlist_widget
        playlist.itemDoubleClicked.connect(self._on_playlist_double_click)

        # --- Playback Controls (Global Footer) ---
        self.playback_widget.play_pause_clicked.connect(self._toggle_play_pause)
        self.playback_widget.prev_clicked.connect(self._play_prev)
        self.playback_widget.next_clicked.connect(self._play_next)
        self.playback_widget.volume_changed.connect(self._on_volume_changed)
        
        # --- Media Status (Auto-Advance) ---
        self.playback_service.media_status_changed.connect(self._on_media_status_changed)
        
        # --- Global Search Wiring ---
        self.title_bar.search_text_changed.connect(self.library_widget.set_search_text)
        self.library_widget.focus_search_requested.connect(lambda: self.title_bar.search_box.setFocus())
        
        # --- T-57: Global Settings Trigger ---
        self.title_bar.settings_requested.connect(lambda: print("TODO: Open Settings Dialog (T-52)"))


    def _setup_shortcuts(self) -> None:
        """Setup global keyboard shortcuts (T-31 legacy shortcuts)."""
        # Ctrl+S – Save staged changes (Side Panel)
        self.action_save_selected = QAction(self)
        self.action_save_selected.setShortcut("Ctrl+S")
        # Fix T-54: Access editor via Right Panel
        self.action_save_selected.triggered.connect(self.right_panel.editor_widget.trigger_save)
        self.addAction(self.action_save_selected)

        # Ctrl+D – Mark selection as Done (Yellberus-gated)
        self.action_mark_done = QAction(self)
        self.action_mark_done.setShortcut("Ctrl+D")
        self.action_mark_done.triggered.connect(self.library_widget.mark_selection_done)
        self.addAction(self.action_mark_done)

        # Ctrl+F – Focus search/filter box
        self.action_focus_search = QAction(self)
        self.action_focus_search.setShortcut("Ctrl+F")
        self.action_focus_search.triggered.connect(self.library_widget.focus_search)
        self.addAction(self.action_focus_search)

        # Ctrl+R – Rename File(s)
        self.action_rename = QAction(self)
        self.action_rename.setShortcut("Ctrl+R")
        self.action_rename.triggered.connect(self.library_widget.rename_selection)
        self.addAction(self.action_rename)

    def _on_playlist_changed(self, parent, start, end):
        # Update widget with new count
        self.playback_widget.set_playlist_count(self.playlist_widget.count())

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

    def _remove_from_playlist(self, rows: list) -> None:
        """Remove items from playlist by row index"""
        # Sort rows descending to avoid index shifting issues
        for row in sorted(rows, reverse=True):
            if 0 <= row < self.playlist_widget.count():
                self.playlist_widget.takeItem(row)

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

    def _play_prev(self) -> None:
        """Play previous (Placeholder/Simple: Re-play current or top)"""
        # For now, just seek to start or re-trigger current
        self.playback_service.seek(0)

    def _on_volume_changed(self, value):
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

    def _on_playlist_double_click(self, item) -> None:
        """Handle double-click on playlist item"""
        self._play_item(item)

    def _play_path_now(self, path: str) -> None:
        """Direct play from library (bypassing playlist)"""
        self.playback_service.load(path)
        self.playback_service.play()
        self._update_song_label(path)

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
            # Main Horizontal
            self.main_splitter.restoreState(splitter_state)

    def _save_splitter_states(self) -> None:
        self.settings_manager.set_main_splitter_state(self.main_splitter.saveState())
    
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
        playlist_data = self.settings_manager.get_last_playlist()
        if playlist_data:
            from PyQt6.QtWidgets import QListWidgetItem
            # T-54: Access nested playlist widget
            playlist_widget = self.right_panel.playlist_widget
            
            for path in playlist_data:
                # Try to extract metadata for display
                try:
                    song = self.metadata_service.extract_from_mp3(path)
                    display_text = f"{song.get_display_performers()} | {song.get_display_title()}"
                except Exception:
                    display_text = os.path.basename(path)
                
                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, {"path": path})
                playlist_widget.addItem(list_item)
        
        # Initial update of button state
        self.playback_widget.set_playlist_count(self.right_panel.playlist_widget.count())
    
    def _save_playlist(self) -> None:
        """Save current playlist"""
        playlist_data = []
        # T-54: Access nested playlist widget
        playlist_widget = self.right_panel.playlist_widget
        for i in range(playlist_widget.count()):
            item = playlist_widget.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and "path" in data:
                playlist_data.append(data["path"])
        self.settings_manager.set_last_playlist(playlist_data)


    def _on_right_tab_changed(self, index: int) -> None:
        """Legacy handler - keep for now to avoid breaking other connections if any"""
        pass

    def _on_library_selection_changed(self, selected, deselected) -> None:
        """Handle library row selection."""
        # Get selected songs from the model
        selection_model = self.library_widget.table_view.selectionModel()
        indexes = selection_model.selectedRows()
        
        songs = []
        if indexes:
            for idx in indexes:
                song = self._get_selected_song_object(idx)
                if song:
                    songs.append(song)
            
        # Facade Pattern: Pass data to Right Panel
        self.right_panel.update_selection(songs)

    def _handle_transport_command(self, cmd: str) -> None:
        """Route transport commands from Right Panel to Service helpers"""
        # We must call the internal helpers (_play_next, etc.) because they 
        # manage the UI state (removing items from playlist, updating labels).
        # Calling service directly bypasses the 'Playlist Logic'.
        
        if cmd == 'play':
            self._toggle_play_pause()
        elif cmd == 'stop':
            self.playback_service.stop()
        elif cmd == 'next':
            self._play_next()
        elif cmd == 'prev':
            self._play_prev()

    def _handle_transition_command(self, type_str: str, duration_ms: int) -> None:
        """Route transition commands."""
        if type_str == 'cut':
            # Force hard switch for next song
             current_enabled = self.playback_service.crossfade_enabled
             self.playback_service.crossfade_enabled = False
             self._play_next() # Call UI Helper
             self.playback_service.crossfade_enabled = current_enabled
             
        elif type_str == 'fade':
            # Force Fade Duration logic
            self.playback_service.crossfade_duration = duration_ms
            self._play_next() # Call UI Helper

    def _get_selected_song_object(self, proxy_index):
        """Helper to get a real Song object from a table selection."""
        # Get path from column (standard Yellberus index)
        path_idx = self.library_widget.field_indices.get('path', -1)
        if path_idx == -1: return None
        
        # Get the row from the proxy index
        source_index = self.library_widget.proxy_model.mapToSource(proxy_index)
        
        # We need the path to fetch the real model from the repo/service
        path_item = self.library_widget.library_model.item(source_index.row(), path_idx)
        
        if not path_item: return None
        
        path = path_item.text()
        return self.library_service.get_song_by_path(path)

    def _toggle_surgical_mode(self, enabled: bool) -> None:
        """Reveal the Metadata Editor."""
        self._surgical_mode_enabled = enabled
        sizes = self.right_splitter.sizes()
        sizes[1] = 700 if enabled else 0
        # If opening surgery, maybe hide jingles/history to save space
        if enabled:
            sizes[0] = 0
            sizes[2] = 0
        self.right_splitter.setSizes(sizes)

    def _toggle_jingle_bay(self, enabled: bool) -> None:
        """Reveal the Jingle/Chip Bay."""
        sizes = self.right_splitter.sizes()
        sizes[0] = 250 if enabled else 0
        self.right_splitter.setSizes(sizes)

    def _toggle_history_log(self, enabled: bool) -> None:
        """Reveal the Historical 'As Played' Log."""
        sizes = self.right_splitter.sizes()
        sizes[2] = 400 if enabled else 0
        self.right_splitter.setSizes(sizes)

    def _on_side_panel_save_requested(self, staged_changes: dict) -> None:
        """Commit all staged changes to DB and ID3 tags."""
        successful_ids = []
        songs_to_check = []
        
        for song_id, changes in staged_changes.items():
            # 1. Fetch current song model
            song = self.library_service.song_repository.get_by_id(song_id)
            if not song: continue
            
            # 2. Apply changes to the model with type coercion
            for field_name, value in changes.items():
                field_def = self._get_yellberus_field(field_name)
                if not field_def: continue
                
                # Coerce types based on Yellberus definition
                from ...core import yellberus
                value = yellberus.cast_from_string(field_def, value)
                
                # Map field name to model attribute
                attr = field_def.model_attr or field_def.name
                
                if hasattr(song, attr):
                    setattr(song, attr, value)
                else:
                    from ...core import yellberus
                    yellberus.yell(f"SidePanel save: Song model missing attribute '{attr}' for field '{field_name}'")
            
            
            # 3. Save to ID3 First (Pessimistic: Ensure file is writable)
            id3_success = self.metadata_service.write_tags(song)
            
            # 4. If ID3 succeeds (or is skipped/non-fatal), Save to DB
            # Note: We consider ID3 failure fatal for consistency in this "Editor" context.
            if id3_success:
                if self.library_service.update_song(song):
                    successful_ids.append(song_id)
                    songs_to_check.append(song)
            else:
                QMessageBox.warning(self, "Save Failed", f"Could not write tags to file:\n{song.source}\n\nCheck if file is read-only or in use.")
                
        # Cleanup
        if successful_ids:
            # 1. Capture current selection (Source IDs) to preserve across reload
            selected_ids = set()
            id_col = self.library_widget.field_indices.get('file_id', -1)
            
            # We need QItemSelectionModel for flags
            from PyQt6.QtCore import QItemSelectionModel
            
            if id_col != -1:
                selection_model = self.library_widget.table_view.selectionModel()
                # Get selected rows from proxy
                for proxy_idx in selection_model.selectedRows():
                     # Map to source
                     source_idx = self.library_widget.proxy_model.mapToSource(proxy_idx)
                     # Get ID from source model
                     item = self.library_widget.library_model.item(source_idx.row(), id_col)
                     if item:
                         # Store as string for easy comparison
                         selected_ids.add(str(item.data(Qt.ItemDataRole.UserRole)))
            
            # 2. Clear staged for successful saves
            self.right_panel.editor_widget.clear_staged(successful_ids)
            
            # 3. Reload Library (This clears the model and selection)
            self.library_widget.load_library(refresh_filters=False)
            
            # 4. Restore Selection
            if selected_ids and id_col != -1:
                new_selection_model = self.library_widget.table_view.selectionModel()
                source_model = self.library_widget.library_model
                proxy_model = self.library_widget.proxy_model
                
                # Iterate rows to find matches
                for row in range(source_model.rowCount()):
                    item = source_model.item(row, id_col)
                    if item and str(item.data(Qt.ItemDataRole.UserRole)) in selected_ids:
                        # Map source row back to proxy index (column 0 for full row selection)
                        source_idx = source_model.index(row, 0)
                        proxy_idx = proxy_model.mapFromSource(source_idx)
                        if proxy_idx.isValid():
                            new_selection_model.select(
                                proxy_idx, 
                                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
                            )
            
            # 5. Refresh Side Panel manually (ensure it shows clean data)
            self._on_library_selection_changed(None, None)
            
            # Removed Auto-Advance per user request
            
            self.statusBar().showMessage(f"Successfully saved {len(successful_ids)} songs.", 3000)

            # 6. Check for Auto-Rename Candidates (Rule: Done + Path Changed)
            rename_needed = False
            for song in songs_to_check:
                if song.is_done:
                    try:
                        target = self.renaming_service.calculate_target_path(song)
                        if song.path:
                             current_norm = os.path.normcase(os.path.normpath(song.path))
                             target_norm = os.path.normcase(os.path.normpath(target))
                             if current_norm != target_norm:
                                 rename_needed = True
                                 break
                    except Exception:
                        continue
            
            if rename_needed:
                self.library_widget.rename_selection()

    def _auto_advance_selection(self):
        """Move selection to the next row in the library table."""
        view = self.library_widget.table_view
        selection_model = view.selectionModel()
        current_indexes = selection_model.selectedRows()
        
        if not current_indexes:
            return
            
        last_index = current_indexes[-1]
        next_row = last_index.row() + 1
        
        if next_row < self.library_widget.proxy_model.rowCount():
            next_index = self.library_widget.proxy_model.index(next_row, 0)
            selection_model.clearSelection()
            selection_model.select(next_index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)
            view.scrollTo(next_index)

    def _get_yellberus_field(self, name: str):
        """Helper to find a field definition by name."""
        from ...core import yellberus
        return next((f for f in yellberus.FIELDS if f.name == name), None)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def resizeEvent(self, event):
        """Keep size grip in bottom-right corner"""
        super().resizeEvent(event)
        # Position grip in bottom-right corner
        grip_size = self.size_grip.size()
        self.size_grip.move(
            self.width() - grip_size.width(),
            self.height() - grip_size.height()
        )
