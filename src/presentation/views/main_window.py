"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QMenu, QMessageBox,
    QSizeGrip, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QAction

from ..widgets import (
    PlaylistWidget, PlaybackControlWidget, LibraryWidget, 
    SidePanelWidget, CustomTitleBar, JingleCurtain, SystemIsland, ToastOverlay
)
from ..dialogs import SettingsDialog, LogViewerDialog
from ...business.services import LibraryService, MetadataService, PlaybackService, SettingsManager, RenamingService, DuplicateScannerService, ConversionService, SpotifyParsingService
from ...resources import constants
from PyQt6.QtWidgets import (
    QPushButton, QFrame
)
from ..widgets.glow import GlowLED
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import pyqtSignal, QSize, QItemSelectionModel, QEvent

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
        pen = QPen(QColor(constants.COLOR_BORDER_LIGHT), 2.0)
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
        # Style moved to theme.qss
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        # 1. Spacer (replaces Dots)
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
        # Style moved to theme.qss
        
        self.prep_btn.toggled.connect(self.prep_toggled.emit)
        layout.addWidget(self.prep_btn)
        
        layout.addStretch()
        
        # 4. THE LED (Status)
        self.status_led = GlowLED(color="#FFC66D", size=8)
        self.status_led.setObjectName("StatusLed")
        # Style moved to theme.qss
        
        layout.addWidget(self.status_led)
        
        self.prep_btn.toggled.connect(self._on_prep_toggled)

    def _create_toggle(self, text, signal):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedSize(50, 22)
        btn.setObjectName(f"TerminalToggle_{text}")
        # Style moved to theme.qss
        
        btn.toggled.connect(signal.emit)
        return btn

    def _on_prep_toggled(self, checked):
        self.status_led.setActive(checked)

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        # 1. Initialize Settings First (Required for Hardware Unlocking)
        self.settings_manager = SettingsManager()
        db_path = self.settings_manager.get_database_path()

        # 2. Initialize Data Access Layer with injected path
        from ...data.repositories import SongRepository, AlbumRepository, PublisherRepository, TagRepository
        self.song_repository = SongRepository(db_path)
        self.album_repository = AlbumRepository(db_path)
        self.publisher_repository = PublisherRepository(db_path)
        self.tag_repository = TagRepository(db_path)

        # 3. Initialize Business Services
        from ...business.services.song_service import SongService
        from ...business.services.contributor_service import ContributorService
        from ...business.services.album_service import AlbumService
        from ...business.services.publisher_service import PublisherService
        from ...business.services.tag_service import TagService
        from ...business.services.audit_service import AuditService

        self.song_service = SongService(self.song_repository)
        self.contributor_service = ContributorService(db_path=db_path)
        self.album_service = AlbumService(self.album_repository)
        self.publisher_service = PublisherService(self.publisher_repository)
        self.tag_service = TagService(self.tag_repository)
        
        from ...business.services.search_service import SearchService
        self.search_service = SearchService()
        
        # Initialize Audit Repository and Service
        from ...data.repositories.audit_repository import AuditRepository
        self.audit_repository = AuditRepository(db_path)
        self.audit_service = AuditService(self.audit_repository)
        self.spotify_parsing_service = SpotifyParsingService()

        self.library_service = LibraryService(
            self.song_service, 
            self.contributor_service, 
            self.album_service,
            self.publisher_service,
            self.tag_service,
            self.search_service,
            self.spotify_parsing_service
        )
        self.metadata_service = MetadataService()
        self.playback_service = PlaybackService(self.settings_manager)
        self.renaming_service = RenamingService(self.settings_manager)
        self.duplicate_scanner = DuplicateScannerService(self.library_service)
        self.conversion_service = ConversionService(self.settings_manager)

        from ...business.services.import_service import ImportService
        self.import_service = ImportService(
            self.library_service,
            self.metadata_service,
            self.duplicate_scanner,
            self.settings_manager,
            self.conversion_service
        )

        from ...business.services.export_service import ExportService
        self.export_service = ExportService(
            self.metadata_service,
            self.library_service
        )

        # Initialize UI
        self._init_ui()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Window |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        
        # Hide status bar to prevent automatic size grip
        self.setStatusBar(None)
        
        self._load_window_geometry()
        self._load_splitter_states()
        # Setup Connections
        self._setup_connections()
        self._setup_shortcuts()
        
        self._restore_volume()
        self._restore_playlist()
        
        # T-OPTIMIZATION: Cache selection to prevent lag during filtering
        self._last_selected_paths = []
        
        # Sync edit mode state from right panel's button
        if hasattr(self.right_panel, 'header') and hasattr(self.right_panel.header, 'btn_edit'):
            initial_edit_mode = self.right_panel.header.btn_edit.isChecked()
            self.library_widget.set_edit_mode(initial_edit_mode)

    def _init_ui(self) -> None:
        """Initialize the user interface"""
        self.setWindowTitle("Gosling2 Music Player")
        self.setMinimumSize(1080, 640) # Prevent "Trash Compactor" squashing of panels

        # Create central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) # We control spacing with explicit separator widgets
        
        # Global Industrial Amber Theme
        # Hardcoded styles removed; relying on src/resources/theme.qss
        # This prevents duplicate definitions and "ghost" overrides.

        
        # 0. Integrated Title Area
        title_area_container = QWidget()
        title_area_layout = QHBoxLayout(title_area_container)
        title_area_layout.setContentsMargins(0, 0, 0, 0)
        title_area_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.title_bar.maximize_requested.connect(self._toggle_maximize)
        title_area_layout.addWidget(self.title_bar, 1)
        
        # Floating System controls (The Island)
        self.system_island = SystemIsland(self)
        self.system_island.minimize_requested.connect(self.showMinimized)
        self.system_island.maximize_requested.connect(self._toggle_maximize)
        self.system_island.close_requested.connect(self.close)
        
        title_area_layout.addWidget(self.system_island, 0, Qt.AlignmentFlag.AlignTop)
        
        main_layout.addWidget(title_area_container)
        
        # --- TOP SEPARATOR (7px Black) ---
        top_separator = QWidget()
        top_separator.setObjectName("SeparatorLine")

        main_layout.addWidget(top_separator)

        # === THE MAIN SPLITTER (Left/Center Block | Right Panel) ===
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("MainRootSplitter")

        # --- LEFT+CENTER BLOCK (Archive + Library + Scrubber) ---
        lc_container = QWidget()
        lc_layout = QVBoxLayout(lc_container)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setSpacing(0)  # No spacing - strictly separator widgets
        
        # LC Splitter (Archive | Library)
        self.lc_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Archive/Library (Currently just LibraryWidget acting as both)
        self.library_widget = LibraryWidget(
            self.library_service, 
            self.metadata_service,
            self.settings_manager,
            self.renaming_service,
            self.duplicate_scanner,
            self.conversion_service,
            self.import_service
        )
        self.lc_splitter.addWidget(self.library_widget)
        
        lc_layout.addWidget(self.lc_splitter, 1)
        
        # --- NO SEPARATOR HERE ---
        # (Moved to main layout below)
        
        # 2. FOOTER (Scrubber) - MOVED
        self.playback_widget = PlaybackControlWidget(
            self.playback_service,
            self.settings_manager
        )
        self.playback_widget.setObjectName("PlaybackDeck")
        # Do not add to lc_layout yet
        
        # Add LC Block to Main Splitter
        self.main_splitter.addWidget(lc_container)

        # --- RIGHT PANEL (Command Deck) ---
        from ..widgets.right_panel_widget import RightPanelWidget
        self.right_panel = RightPanelWidget(
            self.library_service,
            self.metadata_service,
            self.renaming_service,
            self.duplicate_scanner,
            self.settings_manager,
            self.spotify_parsing_service
        )
        self.main_splitter.addWidget(self.right_panel)
        main_layout.addWidget(self.main_splitter, 1)
        
        # --- BOTTOM SEPARATOR (7px Black) ---
        bottom_separator = QWidget()
        bottom_separator.setObjectName("SeparatorLine")

        main_layout.addWidget(bottom_separator)
        
        # Add Playback at the very bottom
        main_layout.addWidget(self.playback_widget)
        
        # COMPATIBILITY ALIAS: Mapping legacy self.playlist_widget to the new nested instance
        # This prevents crashes in _play_next, _toggle_play_pause, etc.
        self.playlist_widget = self.right_panel.playlist_widget
        
        # Stretches: LC=0 (Rigid - Mid Squeezes Side), R=1 (Fluid - Side gets squeezed)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        
        # Prevent Center (Library) from collapsing to 0
        self.main_splitter.setCollapsible(0, False)
        # Prevent Right Panel from collapsing to 0 (Hard Stop)
        self.main_splitter.setCollapsible(1, False)

        # Add resize grip to bottom-right corner (for frameless window)
        self.size_grip = ResizeGrip(self)
        # Position it in the bottom-right corner
        self.size_grip.raise_()

        # Feedback Toast (Independent of Layout)
        self.toast = ToastOverlay(self)


    def _setup_connections(self) -> None:
        """Setup signal/slot connections"""
        # --- Library Signals ---
        self.library_widget.add_to_playlist.connect(self._add_to_playlist)
        self.library_widget.remove_from_playlist.connect(self._remove_from_playlist)
        self.library_widget.play_immediately.connect(self._play_path_now)
        
        # Connect Selection -> Right Panel Facade
        self.library_widget.table_view.selectionModel().selectionChanged.connect(self._on_library_selection_changed)

        # --- Playback Controls (Global Footer / Command Deck) ---
        self.playback_widget.transport_command.connect(self._handle_transport_command)
        self.playback_widget.transition_command.connect(self._handle_transition_command)
        self.playback_widget.volume_changed.connect(self._on_volume_changed)
        
        # --- Editor Signals (Transient Wiring) ---
        # Direct access to inner widget until SidePanel refactor is complete
        editor = self.right_panel.editor_widget
        editor.save_requested.connect(self._on_side_panel_save_requested)
        editor.staging_changed.connect(self.library_widget.update_dirty_rows)

        editor.filter_refresh_requested.connect(lambda: self.library_widget.load_library(refresh_filters=True))
        
        # T-Feature: Sync Side Panel when Scrubber updates tags
        self.library_widget.metadata_changed.connect(lambda: editor.refresh_content())

        # T-Fix: Ensure Side Panel refreshes when Library reloads (e.g. after "Parse from Filename")
        # Forces re-fetch from DB to get updated relationships (Artists, Tags)
        self.library_widget.library_reloaded.connect(self._on_library_reloaded)
        
        # T-Feature: Dynamic Width Persistence
        self.right_panel.editor_mode_changed.connect(self._on_editor_mode_changed)
        # T-Feature: Edit mode enables scrubber dialog on double-click
        self.right_panel.editor_mode_changed.connect(self.library_widget.set_edit_mode)
        
        # --- Playlist Signals (Transient Wiring) ---
        # Access inner Playlist widget
        playlist = self.right_panel.playlist_widget
        playlist.itemDoubleClicked.connect(self._on_playlist_double_click)
        playlist.playlist_changed.connect(self._sync_playlist_to_service)
        # Initial sync
        self._sync_playlist_to_service()

        # Legacy signals (if still emitted, but now covered by transport_command)
        self.playback_widget.play_pause_clicked.connect(self._toggle_play_pause)
        self.playback_widget.prev_clicked.connect(self._play_prev)
        self.playback_widget.next_clicked.connect(self._play_next)
        
        # --- Media Status (Auto-Advance) ---
        self.playback_service.media_status_changed.connect(self._on_media_status_changed)
        self.playback_service.position_changed.connect(self._on_playback_position_changed)
        
        # T-OPTIMIZATION: Auto-save main splitter layout
        self.main_splitter.splitterMoved.connect(lambda p, i: self._save_splitter_states())
        
        # --- Global Search & Intake Wiring ---
        self.title_bar.search_text_changed.connect(self.library_widget.set_search_text)
        self.title_bar.import_requested.connect(self.library_widget._import_files)
        self.library_widget.focus_search_requested.connect(lambda: self.title_bar.search_box.setFocus())
        
        # --- T-57: Global Settings Trigger ---
        self.title_bar.settings_requested.connect(self._open_settings)
        self.title_bar.logs_requested.connect(self._open_logs)
        self.title_bar.history_requested.connect(self._open_audit_history)
        self.title_bar.tools_requested.connect(self._open_tools)
        
        # --- T-Feedback: Toast Routing ---
        self.library_widget.status_message_requested.connect(self.toast.show_message)
        editor.status_message_requested.connect(self.toast.show_message)


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

        # Ctrl+Space - Trigger Metadata Search Menu (Side Panel)
        self.action_search_meta = QAction(self)
        self.action_search_meta.setShortcut("Ctrl+Space")
        self.action_search_meta.triggered.connect(self.right_panel.editor_widget.trigger_search)
        self.addAction(self.action_search_meta)

        # Ctrl+T – Open Library Tools (T-Tools)
        self.action_open_tools = QAction(self)
        self.action_open_tools.setShortcut("Ctrl+T")
        self.action_open_tools.triggered.connect(self._open_tools)
        self.addAction(self.action_open_tools)

    def _on_playlist_changed(self, parent, start, end):
        # Update widget with new count
        self.playback_widget.set_playlist_count(self.playlist_widget.count())

    def _sync_playlist_to_service(self):
        """Sync the playback service playlist with the UI playlist"""
        paths = []
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and "path" in data:
                paths.append(data["path"])

        # Check if current playing song is still in playlist
        current_index = self.playback_service.get_current_index()
        if current_index >= 0 and current_index < len(paths):
            current_path = self.playback_service.get_playlist()[current_index]
            if current_path not in paths:
                # Current song was removed, stop playback
                self.playback_service.stop()
                self.playback_service.active_player.setSource(QUrl())
                self._update_song_label("NO MEDIA ARMED")
        elif not paths:
            # Playlist is now empty, stop and clear
            self.playback_service.stop()
            self.playback_service.active_player.setSource(QUrl())
            self._update_song_label("NO MEDIA ARMED")

        self.playback_service.set_playlist(paths)

    def _add_to_playlist(self, items) -> None:
        """Add items from library to playlist"""
        from PyQt6.QtWidgets import QListWidgetItem
        for item_data in items:
            path = item_data["path"]
            performer = item_data["performer"]
            title = item_data["title"]
            duration = item_data.get("duration", 0)
            
            list_item = QListWidgetItem(f"{performer} | {title}")
            list_item.setData(Qt.ItemDataRole.UserRole, {
                "path": path,
                "duration": duration
            })
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
            row = self.playlist_widget.row(item)
            self.playback_service.play_at_index(row)  # This sets current_index and loads/plays
            self._update_song_label(path)
            # Sync active row for visual sweep
            self.playlist_widget._active_row = row

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
                # After deletion, the new top is row 0
                self.playlist_widget._active_row = 0

    def _play_prev(self) -> None:
        """Play previous (Placeholder/Simple: Re-play current or top)"""
        # For now, just seek to start or re-trigger current
        self.playback_service.seek(0)

    def _on_volume_changed(self, value):
        self.playback_service.set_volume(value / 100.0)

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Reset visual sweep before moving to next
            self.playlist_widget.update_playback_progress(-1, 0)
            self._play_next()

    def _on_playback_position_changed(self, pos_ms: int) -> None:
        """Relay playback position to playlist for visual sweep."""
        active_row = getattr(self.playlist_widget, '_active_row', -1)
        if active_row >= 0:
            self.playlist_widget.update_playback_progress(active_row, pos_ms)

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
        self.playlist_widget._active_row = -1

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
            # T-Fix: Never start maximized (User Request)
            if self.isMaximized():
                self.showNormal()
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
        """Restore last playlist efficiently (No Disk Probing)"""
        playlist_data = self.settings_manager.get_last_playlist()
        if not playlist_data:
            return

        from PyQt6.QtWidgets import QListWidgetItem
        playlist_widget = self.right_panel.playlist_widget
        
        # Resolve metadata from database in one efficient bulk fetch
        songs = self.library_service.get_songs_by_paths(playlist_data) or []
        song_map = {song.path: song for song in songs}
        
        for path in playlist_data:
            display_text = os.path.basename(path)
            duration = 0
            if path in song_map:
                song = song_map[path]
                display_text = f"{song.get_display_performers()} | {song.get_display_title()}"
                duration = song.duration or 0
            
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, {
                "path": path,
                "duration": duration
            })
            playlist_widget.addItem(list_item)
    
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
        # Get selected rows from the view
        selection_model = self.library_widget.table_view.selectionModel()
        indexes = selection_model.selectedRows()
        
        if not indexes:
            if self._last_selected_paths:
                self._last_selected_paths = []
                self.right_panel.update_selection([])
            return

        # 1. Collect paths without hitting the DB (Memory operation)
        path_idx = self.library_widget.field_indices.get('path', -1)
        if path_idx == -1: return

        paths = []
        for proxy_idx in indexes:
             source_idx = self.library_widget.proxy_model.mapToSource(proxy_idx)
             path_item = self.library_widget.library_model.item(source_idx.row(), path_idx)
             if path_item:
                 paths.append(path_item.text())

        # T-OPTIMIZATION: Early return if selection hasn't changed
        if paths == self._last_selected_paths:
            return
            
        self._last_selected_paths = paths

        # 2. Bulk fetch all song objects in ONE database trip
        # This eliminates the 3-second freeze during multi-selection!
        songs = self.library_service.get_songs_by_paths(paths)
            
        # 3. Facade Pattern: Pass data to Right Panel
        # 3. Facade Pattern: Pass data to Right Panel
        self.right_panel.update_selection(songs)

    def _on_library_reloaded(self):
        """
        Handle library reload (e.g. after 'Parse from Filename').
        Forces a fresh fetch of the current selection to ensure SidePanel receives updated metadata.
        """
        # Invalidate cache to force update even if file path hasn't changed
        self._last_selected_paths = [] 
        
        # Manually trigger selection update with current selection
        selection = self.library_widget.table_view.selectionModel().selection()
        # Pass dummy deselected (empty)
        from PyQt6.QtCore import QItemSelection
        self._on_library_selection_changed(selection, QItemSelection())

    def _handle_transport_command(self, cmd: str) -> None:
        """Route transport commands with Tape Recorder logic."""
        state = self.playback_service.active_player.playbackState()
        
        if cmd == 'play':
            # Tape Logic: Play ONLY starts from stop. 
            if state == QMediaPlayer.PlaybackState.StoppedState:
                self._toggle_play_pause() 
                
        elif cmd == 'pause':
            # Tape Logic: Pause is the ONLY movement toggle.
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.playback_service.pause()
            elif state == QMediaPlayer.PlaybackState.PausedState:
                self.playback_service.play()
                
        elif cmd == 'stop':
            self.playback_service.stop()
            self.playlist_widget.update_playback_progress(-1, 0)
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

    def _on_editor_mode_changed(self, enabled: bool) -> None:
        """
        Resize right panel based on mode, saving/restoring width for each state.
        Normal: Compact (e.g. 350px)
        Editor: Wide (e.g. 500-700px)
        """
        # Unlock constraints for Editor Mode
        self.right_panel.setMaximumWidth(900 if enabled else 550)
        self.right_panel.setMinimumWidth(350)
        
        sizes = self.main_splitter.sizes()
        if len(sizes) < 2: return
        
        current_width = sizes[1]
        
        if enabled:
            # Switching TO Editor Mode
            # Save the width we are leaving (Normal Mode)
            self.settings_manager.set_right_panel_width_normal(current_width)
            
            # Load Editor Width
            target = self.settings_manager.get_right_panel_width_editor()
        else:
            # Switching FROM Editor Mode
            # Save the width we are leaving (Editor Mode)
            self.settings_manager.set_right_panel_width_editor(current_width)
            
            # Load Normal Width
            target = self.settings_manager.get_right_panel_width_normal()
            
        # Apply Logic
        total = sum(sizes)
        # Safety clamp
        if target < 350: target = 350
        
        new_sizes = [total - target, target]
        self.main_splitter.setSizes(new_sizes)

    def _on_side_panel_save_requested(self, staged_changes: dict, staged_album_deletions: set = None) -> None:
        """Commit all staged changes to DB and ID3 tags."""
        from ...core import logger, yellberus
        logger.info(f"Save requested for {len(staged_changes)} songs.")
        successful_ids = []
        songs_to_check = []
        albums_to_check = set()
        
        # T-70: Smart Filter Refresh
        # Only rebuild the expensive filter tree if a "Filter-Critical" field changed.
        needs_filter_refresh = False
        filter_triggers = {
            'performers', 'groups', 'unified_artist', 
            'album', 'composers', 'publisher', 
            'recording_year', 'year', 
            'genre', 'genre_list', 'mood', 'mood_list', 
            'bpm', 'energy', 'initial_key', 
            'is_done'
        }
        
        try:
            # Generate a Batch ID for this multi-song save operation
            from ...core.audit_logger import AuditLogger
            batch_id = AuditLogger.generate_batch_id()

            for song_id, changes in staged_changes.items():
                song = self.library_service.get_song_by_id(song_id)
                if not song: continue
                
                # Metadata Editing Logic (T-46): Tracking Orphans
                if 'album_id' in changes or 'album' in changes:
                    if song.album_id:
                        if isinstance(song.album_id, list):
                            albums_to_check.update(song.album_id)
                        else:
                            albums_to_check.add(song.album_id)
                
                # Apply changes with type coercion
                for field_name, value in changes.items():
                    if field_name in filter_triggers:
                        needs_filter_refresh = True
                    
                    # T-Fix: Explicitly handle album_id (not in Yellberus)
                    if field_name == 'album_id':
                        song.album_id = value
                        # If we are clearing the ID, we MUST also clear the album title (to [])
                        # to ensure SongRepository.update triggers _sync_album (which skips None).
                        if value is None and 'album' not in changes:
                            song.album = []
                        
                        # T-Fix: Update album_artist for ID3 export (TPE2) based on new Primary Album
                        # If we changed the album, the old album_artist on 'song' is stale.
                        # We must fetch the artist of the new primary album.
                        try:
                            primary_id = None
                            if isinstance(value, list) and value:
                                primary_id = value[0]
                            elif isinstance(value, int):
                                primary_id = value
                            
                            if primary_id:
                                # We need access to AlbumRepo
                                album_obj = self.library_service.get_album_by_id(primary_id)
                                if album_obj and album_obj.album_artist:
                                    song.album_artist = album_obj.album_artist
                                else:
                                    # Fallback: If no AlbumArtist set on album, maybe clear it?
                                    # Or keep existing? Usually clearing is safer if explicit change.
                                    # But let's assume if it returns None, we might fallback to Performer?
                                    # For now, let's just update if we found one.
                                    pass
                        except Exception as e:
                            logger.error(f"Failed to update album_artist for ID3: {e}")

                        continue

                    try:
                        field_def = self._get_yellberus_field(field_name)
                        if not field_def: continue
                        value = yellberus.cast_from_string(field_def, value)
                        attr = field_def.model_attr or field_def.name
                        if hasattr(song, attr):
                            setattr(song, attr, value)
                    except Exception as e:
                        logger.error(f"Error applying change {field_name}: {e}")
                
                # Orchestration Layer: Delegate save to ExportService, but tell it our preference.
                write_tags = self.settings_manager.get_write_tags()
                album_type = self.settings_manager.get_default_album_type()
                result = self.export_service.export_song(song, write_tags=write_tags, batch_id=batch_id, album_type=album_type)
                
                if result.success:
                    successful_ids.append(song_id)
                    songs_to_check.append(song)
                else:
                    QMessageBox.warning(self, "Save Failed", f"Metadata could not be persisted:\n{result.error}")
            
            # NOTE: Orphan album handling removed - belongs in Album Editor, not save flow
                    
            if successful_ids:
                # Capture current selection by SourceID
                selected_ids = []
                id_col = self.library_widget.field_indices.get('file_id', -1)
                if id_col != -1:
                    for proxy_idx in self.library_widget.table_view.selectionModel().selectedRows():
                         src_idx = self.library_widget.proxy_model.mapToSource(proxy_idx)
                         item = self.library_widget.library_model.item(src_idx.row(), id_col)
                         if item: selected_ids.append(str(item.data(Qt.ItemDataRole.UserRole)))
                
                self.right_panel.editor_widget.clear_staged(successful_ids)
                
                # Trigger rename (which now handles its own pre-check, settings, and confirmation)
                self.library_widget.rename_selection(refresh=False)
                
                self.library_widget.load_library(refresh_filters=needs_filter_refresh)
                
                # Restore Selection
                if selected_ids:
                    sm = self.library_widget.table_view.selectionModel()
                    m = self.library_widget.library_model
                    pm = self.library_widget.proxy_model
                    from PyQt6.QtCore import QItemSelectionModel
                    for row in range(m.rowCount()):
                        item = m.item(row, id_col)
                        if item and str(item.data(Qt.ItemDataRole.UserRole)) in selected_ids:
                            idx = pm.mapFromSource(m.index(row, 0))
                            if idx.isValid():
                                sm.select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
                
                self._on_library_selection_changed(None, None)
                # T-Fix: Do NOT use self.statusBar() as it recreates the hidden bar and breaks layout.
                self.toast.show_message(f"Successfully saved {len(successful_ids)} songs", "success")
                logger.info(f"Successfully saved {len(successful_ids)} songs.")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Save process crashed: {e}")

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

    def _open_settings(self):
        """Open the Settings Dialog (T-52 MVP)."""
        dlg = SettingsDialog(self.settings_manager, self.renaming_service, self)
        if dlg.exec():
            # Refresh components that might depend on root path or rules
            self.library_widget.load_library()
            # Renaming service is already linked to settings_manager

    def _open_logs(self):
        """Open the Diagnostic Log Viewer."""
        dlg = LogViewerDialog(self.settings_manager, self)
        dlg.exec()

    def _open_audit_history(self):
        """Open the Audit History Flight Recorder."""
        from ..dialogs.audit_history_dialog import AuditHistoryDialog
        dlg = AuditHistoryDialog(
            self.audit_service,
            resolver=self.library_service.get_human_name,
            parent=self
        )
        dlg.exec()

    def _open_tools(self):
        """Open the Library Tools Window (T-Tools)."""
        from ..windows import ToolsWindow

        # Single instance pattern - reuse if already open
        if hasattr(self, '_tools_window') and self._tools_window is not None:
            try:
                self._tools_window.show()
                self._tools_window.raise_()
                self._tools_window.activateWindow()
                return
            except RuntimeError:
                # Window was deleted, create new one
                pass

        self._tools_window = ToolsWindow(
            tag_service=self.library_service.tag_service,
            settings_manager=self.settings_manager,
            contributor_service=self.contributor_service,
            publisher_service=self.publisher_service,
            album_service=self.album_service,
            parent=None  # Independent window, not parented to main
        )
        # Connect data_changed to refresh library if needed
        self._tools_window.data_changed.connect(self._on_tools_data_changed)
        self._tools_window.show()

    def _on_tools_data_changed(self):
        """Handle data changes from Tools window - refresh relevant UI."""
        # Refresh library to reflect any tag/entity changes
        self.library_widget.load_library(refresh_filters=True)

    def changeEvent(self, event):
        """Handle window state changes (Maximize/Restore) from OS or Buttons."""
        if event.type() == QEvent.Type.WindowStateChange:
            if hasattr(self, 'system_island'):
                self.system_island.update_maximize_icon(self.isMaximized())
        super().changeEvent(event)

    def resizeEvent(self, event):
        """Keep size grip in bottom-right corner"""
        super().resizeEvent(event)
        # Position grip in bottom-right corner
        grip_size = self.size_grip.size()
        self.size_grip.move(
            self.width() - grip_size.width(),
            self.height() - grip_size.height()
        )
