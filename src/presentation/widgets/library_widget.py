import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableView, QPushButton, QLineEdit, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal

from .filter_widget import FilterWidget

class LibraryWidget(QWidget):
    """Widget for managing and displaying the music library"""

    # Column indices for library table
    COL_FILE_ID = 0
    COL_ARTIST = 1
    COL_TITLE = 2
    COL_DURATION = 3
    COL_PATH = 4
    COL_COMPOSER = 5
    COL_BPM = 6

    # Signals
    play_song = pyqtSignal(str) # Path
    add_to_playlist = pyqtSignal(list) # List of dicts {path, artist, title}

    def __init__(self, library_service, metadata_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.settings_manager = settings_manager
        
        self._init_ui()
        self._setup_connections()
        self.load_library() # Public method calling internal logic? Or just calls internal load

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top Controls
        self._setup_top_controls(main_layout)

        # Splitter for Filter + Table
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Filter Widget
        self.filter_widget = FilterWidget(self.library_service)
        
        # Center Panel (Search + Table)
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
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        
        center_layout.addWidget(self.search_box)
        center_layout.addWidget(self.table_view)
        
        self.splitter.addWidget(self.filter_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.splitter)

    def _setup_top_controls(self, parent_layout) -> None:
        layout = QHBoxLayout()
        self.btn_import = QPushButton("Import File(s)")
        self.btn_scan_folder = QPushButton("Scan Folder")
        self.btn_refresh = QPushButton("Refresh Library")
        
        layout.addWidget(self.btn_import)
        layout.addWidget(self.btn_scan_folder)
        layout.addWidget(self.btn_refresh)
        layout.addStretch()
        
        parent_layout.addLayout(layout)

    def _setup_connections(self) -> None:
        self.btn_import.clicked.connect(self._import_files)
        self.btn_scan_folder.clicked.connect(self._scan_folder)
        self.btn_refresh.clicked.connect(self.load_library)
        self.search_box.textChanged.connect(self._on_search)
        
        self.filter_widget.filter_by_artist.connect(self._filter_by_artist)
        self.filter_widget.reset_filter.connect(self.load_library)
        
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(self._on_table_double_click)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._show_column_context_menu)

    def load_library(self) -> None:
        """Load library from database"""
        headers, data = self.library_service.get_all_songs()
        self._populate_table(headers, data)
        self._load_column_visibility_states()
        self.filter_widget.populate()
        self.table_view.resizeColumnsToContents()

    def _populate_table(self, headers, data) -> None:
        self.library_model.clear()
        if headers:
            self.library_model.setHorizontalHeaderLabels(headers)
        for row_data in data:
            items = [QStandardItem(str(cell) if cell else "") for cell in row_data]
            self.library_model.appendRow(items)

    def _filter_by_artist(self, artist_name) -> None:
        headers, data = self.library_service.get_songs_by_artist(artist_name)
        self._populate_table(headers, data)

    def _import_file(self, file_path: str) -> bool:
        """Import a single file, return True on success"""
        try:
            file_id = self.library_service.add_file(file_path)
            if file_id:
                song = self.metadata_service.extract_from_mp3(file_path, file_id)
                self.library_service.update_song(song)
                return True
        except Exception as e:
            print(f"Error importing {file_path}: {e}")
        return False

    def _import_files(self) -> None:
        # Get last used directory or default to empty string
        last_dir = self.settings_manager.get_last_import_directory() or ""
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", last_dir, "Audio Files (*.mp3 *.flac *.wav *.m4a)"
        )
        if not files:
            return
        
        # Save the directory for next time
        self.settings_manager.set_last_import_directory(os.path.dirname(files[0]))
            
        imported_count = sum(1 for file_path in files if self._import_file(file_path))
                
        if imported_count > 0:
            QMessageBox.information(self, "Import Complete", f"Imported {imported_count} file(s)")
            self.load_library()

    def _scan_folder(self) -> None:
        # Get last used directory or default to empty string
        last_dir = self.settings_manager.get_last_import_directory() or ""
        
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", last_dir)
        if not folder:
            return
        
        # Save the directory for next time
        self.settings_manager.set_last_import_directory(folder)
            
        imported_count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.flac', '.wav', '.m4a')):
                    file_path = os.path.join(root, file)
                    if self._import_file(file_path):
                        imported_count += 1
                        
        if imported_count > 0:
            QMessageBox.information(self, "Scan Complete", f"Imported {imported_count} file(s)")
            self.load_library()

    def _on_search(self, text) -> None:
        self.proxy_model.setFilterWildcard(f"*{text}*")

    def _show_table_context_menu(self, position) -> None:
        menu = QMenu()
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)
        
        add_to_playlist_action = QAction("Add to Playlist", self)
        add_to_playlist_action.triggered.connect(self._emit_add_to_playlist)
        menu.addAction(add_to_playlist_action)
        
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _show_column_context_menu(self, position) -> None:
        menu = QMenu(self)
        for col in range(self.library_model.columnCount()):
            header_text = self.library_model.headerData(col, Qt.Orientation.Horizontal)
            action = QAction(str(header_text), self)
            action.setCheckable(True)
            action.setChecked(not self.table_view.isColumnHidden(col))
            action.setData(col)
            action.toggled.connect(self._toggle_column_visibility)
            menu.addAction(action)
        menu.exec(self.table_view.horizontalHeader().mapToGlobal(position))

    def _toggle_column_visibility(self, checked) -> None:
        action = self.sender()
        if action:
            column = action.data()
            self.table_view.setColumnHidden(column, not checked)
            self._save_column_visibility_states()

    def _load_column_visibility_states(self) -> None:
        visibility_states = self.settings_manager.get_column_visibility()
        if isinstance(visibility_states, dict):
            for col_str, visible in visibility_states.items():
                if isinstance(col_str, str) and col_str.isdigit():
                    self.table_view.setColumnHidden(int(col_str), not visible)

    def _save_column_visibility_states(self) -> None:
        visibility_states = {}
        for col in range(self.library_model.columnCount()):
            visible = not self.table_view.isColumnHidden(col)
            visibility_states[str(col)] = visible
        self.settings_manager.set_column_visibility(visibility_states)

    def _delete_selected(self) -> None:
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete {len(indexes)} song(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for index in indexes:
                source_index = self.proxy_model.mapToSource(index)
                file_id_item = self.library_model.item(source_index.row(), self.COL_FILE_ID)
                if file_id_item:
                    file_id = int(file_id_item.text())
                    self.library_service.delete_song(file_id)
            self.load_library()

    def _on_table_double_click(self, index) -> None:
        """Double click adds to playlist (as per original behavior)"""
        self._emit_add_to_playlist()

    def _emit_add_to_playlist(self) -> None:
        """Gather selected items and emit signal"""
        indexes = self.table_view.selectionModel().selectedRows()
        items = []
        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            path_item = self.library_model.item(source_index.row(), self.COL_PATH)
            artist_item = self.library_model.item(source_index.row(), self.COL_ARTIST)
            title_item = self.library_model.item(source_index.row(), self.COL_TITLE)
            
            if path_item:
                items.append({
                    "path": path_item.text(),
                    "artist": artist_item.text() if artist_item else "Unknown",
                    "title": title_item.text() if title_item else "Unknown"
                })
        
        if items:
            self.add_to_playlist.emit(items)
