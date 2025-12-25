"""Main application window"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel, QMenu, QMessageBox,
    QStackedWidget, QTabBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QAction

from ..widgets import PlaylistWidget, PlaybackControlWidget, LibraryWidget, SidePanelWidget
from ...business.services import LibraryService, MetadataService, PlaybackService, SettingsManager, RenamingService, DuplicateScannerService

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        # Initialize Data Access Layer
        from ...data.repositories import SongRepository, ContributorRepository, AlbumRepository
        self.song_repository = SongRepository()
        self.contributor_repository = ContributorRepository()
        self.album_repository = AlbumRepository()

        # Initialize Services
        self.settings_manager = SettingsManager()
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
        self._load_window_geometry()
        self._load_splitter_states()
        self._setup_connections()
        self._setup_shortcuts()
        
        self._restore_volume()
        self._restore_playlist()
        self._restore_right_panel_tab()

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
            self.settings_manager,
            self.renaming_service,
            self.duplicate_scanner
        )
        
        # Right Panel Container (Stacked: Playlist | Editor)
        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(0)
        
        # Mode Selector (Tabs)
        self.right_tabs = QTabBar()
        self.right_tabs.addTab("Playlist")
        self.right_tabs.addTab("Editor")
        self.right_tabs.setExpanding(True)
        self.right_tabs.currentChanged.connect(self._on_right_tab_changed)
        
        self.right_stack = QStackedWidget()
        
        # Content Widgets
        self.playlist_widget = PlaylistWidget()
        self.side_panel = SidePanelWidget(
            self.library_service, 
            self.metadata_service, 
            self.renaming_service,
            self.duplicate_scanner
        )
        
        self.right_stack.addWidget(self.playlist_widget)
        self.right_stack.addWidget(self.side_panel)
        
        right_panel_layout.addWidget(self.right_tabs)
        right_panel_layout.addWidget(self.right_stack)

        self.splitter.addWidget(self.library_widget)
        self.splitter.addWidget(right_panel)
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
        self.library_widget.remove_from_playlist.connect(self._remove_from_playlist)
        
        # Playlist interactions
        # Double-click disabled by user request (prevent accidental play)
        # self.playlist_widget.itemDoubleClicked.connect(self._on_playlist_double_click)

        # Playback Controls
        self.playback_widget.play_pause_clicked.connect(self._toggle_play_pause)
        self.playback_widget.next_clicked.connect(self._play_next)
        self.playback_widget.volume_changed.connect(self._on_volume_changed)
        
        # Connect Library Selection to Side Panel
        # Connect Library Selection to Side Panel (Phase 2 Link)
        self.library_widget.table_view.selectionModel().selectionChanged.connect(self._on_library_selection_changed)
        
        # Connect Side Panel Signals
        self.side_panel.save_requested.connect(self._on_side_panel_save_requested)
        self.side_panel.staging_changed.connect(self.library_widget.update_dirty_rows)

    def _setup_shortcuts(self) -> None:
        """Setup global keyboard shortcuts (T-31 legacy shortcuts)."""
        # Ctrl+S – Save staged changes (Side Panel)
        self.action_save_selected = QAction(self)
        self.action_save_selected.setShortcut("Ctrl+S")
        self.action_save_selected.triggered.connect(self.side_panel.trigger_save)
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

    def _restore_right_panel_tab(self) -> None:
        """Restore last selected right panel tab"""
        index = self.settings_manager.get_right_panel_tab()
        self.right_tabs.setCurrentIndex(index)
        self.right_stack.setCurrentIndex(index)

    def _on_right_tab_changed(self, index: int) -> None:
        """Switch between Playlist and Editor."""
        self.right_stack.setCurrentIndex(index)
        self.settings_manager.set_right_panel_tab(index)

    def _on_library_selection_changed(self, selected, deselected) -> None:
        """Load selected song(s) into the Side Panel."""
        # Get selected songs from the model
        selection_model = self.library_widget.table_view.selectionModel()
        indexes = selection_model.selectedRows()
        
        if not indexes:
            self.side_panel.set_songs([])
            return
            
        songs = []
        for idx in indexes:
            song = self._get_selected_song_object(idx)
            if song:
                songs.append(song)
            
        self.side_panel.set_songs(songs)

    def _get_selected_song_object(self, proxy_index):
        """Helper to get a real Song object from a table selection."""
        # Get path from column (standard Yellberus index)
        path_idx = self.library_widget.field_indices.get('path', -1)
        if path_idx == -1: return None
        
        # Get the row from the proxy index
        source_index = self.library_widget.proxy_model.mapToSource(proxy_index)
        
        # We need the path to fetch the real model from the repo/service
        # (Assuming the model stores the path string in the 'path' column)
        path_column_index = self.library_widget.field_indices.get('path')
        path_item = self.library_widget.library_model.item(source_index.row(), path_column_index)
        
        if not path_item: return None
        
        path = path_item.text()
        return self.library_service.get_song_by_path(path)
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
            self.side_panel.clear_staged(successful_ids)
            
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
