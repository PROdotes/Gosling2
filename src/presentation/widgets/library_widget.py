import os
import zipfile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableView, QPushButton, QLineEdit, QFileDialog, QMessageBox, QMenu, QStyle, QLabel,
    QCheckBox
)
import json
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QAction, 
    QPainter, QColor, QPixmap, QIcon, QImage, QDragEnterEvent, QDropEvent
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, QEvent

from .filter_widget import FilterWidget

class LibraryWidget(QWidget):
    """Widget for managing and displaying the music library"""

    # Column indices for library table
    COL_FILE_ID = 0
    COL_PERFORMER = 1
    COL_TITLE = 2
    COL_DURATION = 3
    COL_PATH = 4
    COL_COMPOSER = 5
    COL_BPM = 6
    COL_YEAR = 7

    # Map Column Index -> Field Name for criteria checking
    COL_TO_FIELD = {
        COL_FILE_ID: 'file_id',
        COL_PERFORMER: 'performers',
        COL_TITLE: 'title',
        COL_DURATION: 'duration',
        COL_PATH: 'path',
        COL_COMPOSER: 'composers',
        COL_BPM: 'bpm',
        COL_YEAR: 'recording_year'
    }

    # Signals
    add_to_playlist = pyqtSignal(list) # List of dicts {path, performer, title}

    def __init__(self, library_service, metadata_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.settings_manager = settings_manager
        
        self._init_ui()
        self._load_criteria()
        self._setup_connections()
        self.load_library()

    def _load_criteria(self) -> None:
        """Load completeness criteria from JSON"""
        try:
            criteria_path = os.path.join(
                os.path.dirname(__file__), 
                '../../completeness_criteria.json'
            )
            criteria_path = os.path.normpath(criteria_path)
            with open(criteria_path, 'r') as f:
                self.completeness_criteria = json.load(f).get('fields', {})
        except Exception as e:
            print(f"Error loading criteria: {e}")
            self.completeness_criteria = {}

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
        self.proxy_model.setFilterKeyColumn(-1) # Search all columns
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setSortRole(Qt.ItemDataRole.UserRole) # Use UserRole for sorting
        
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.setSortingEnabled(True)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        
        # Enable Drag & Drop
        self.table_view.setAcceptDrops(True)
        self.table_view.installEventFilter(self)
        
        # Empty State Label
        self.empty_label = QLabel("Drag audio files here to import", self.table_view)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("QLabel { color: gray; font-size: 14pt; font-weight: bold; }")
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_label.hide()
        
        center_layout.addWidget(self.search_box)
        center_layout.addWidget(self.table_view)
        
        self.splitter.addWidget(self.filter_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.splitter)

    def eventFilter(self, source, event):
        """Handle events for the table view (Drag & Drop + Resize)"""
        if source == self.table_view:
            if event.type() == QEvent.Type.Resize:
                # Center the empty label
                self._update_empty_label_position()
            elif event.type() == QEvent.Type.DragEnter:
                self.dragEnterEvent(event)
                return True
            elif event.type() == QEvent.Type.DragMove:
                # Necessary to accept move for drop to work
                event.acceptProposedAction()
                return True
            elif event.type() == QEvent.Type.DragLeave:
                self.dragLeaveEvent(event)
                return True # Optional, but good to handle
            elif event.type() == QEvent.Type.Drop:
                self.dropEvent(event)
                return True
        return super().eventFilter(source, event)

    def _update_empty_label_position(self):
        """Center the empty label in the table view"""
        if self.empty_label.isVisible():
            self.empty_label.resize(self.table_view.size())
            self.empty_label.move(0, 0)

    def dragEnterEvent(self, event):
        """Validate dragged files (MP3 or ZIP)"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = path.lower().split('.')[-1]
                    if ext in ['mp3', 'zip']:
                        event.acceptProposedAction()
                        # Visual Feedback: Highlight Border
                        self.table_view.setStyleSheet("QTableView { border: 2px solid #4CAF50; }")
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Reset visual feedback"""
        self.table_view.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        """Handle dropped files"""
        # Reset visual feedback immediately
        self.table_view.setStyleSheet("")
        
        if not event.mimeData().hasUrls():
            event.ignore()
            return
            
        file_paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                ext = path.lower().split('.')[-1]
                if ext == 'mp3':
                    file_paths.append(path)
                elif ext == 'zip':
                    # Extract zip and add valid mp3s to list
                    extracted = self._process_zip_file(path)
                    file_paths.extend(extracted)
        
        if file_paths:
            event.acceptProposedAction()
            count = self.import_files_list(file_paths)
            QMessageBox.information(self, "Import Result", f"Imported {count} file(s)")
        else:
            event.ignore()

    def _process_zip_file(self, zip_path):
        """Extract valid MP3s from zip to the same folder.
        
        Logic:
        1. Check if ANY of the mp3s in the zip already exist in destination.
        2. If YES: Warn user and abort (do nothing).
        3. If NO: Extract all mp3s, verify they are there, then DELETE the zip file.
        
        Returns list of absolute paths to the extracted MP3s.
        """
        extracted_paths = []
        base_dir = os.path.dirname(zip_path)
        mp3_members = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 1. Identify MP3s
                for member in zip_ref.namelist():
                    if member.lower().endswith('.mp3'):
                        # Security check: prevent Zip Slip
                        if '..' not in member:
                            mp3_members.append(member)
                
                if not mp3_members:
                    return []

                # 2. Check Collisions
                for member in mp3_members:
                    target_path = os.path.join(base_dir, member)
                    if os.path.exists(target_path):
                        # Collision detected!
                        QMessageBox.warning(
                            self, 
                            "Import Aborted", 
                            f"The file '{member}' already exists in the destination folder.\n\nAborting import to prevent overwriting."
                        )
                        return []

                # 3. Extract All
                for member in mp3_members:
                    zip_ref.extract(member, base_dir)
                    target_path = os.path.join(base_dir, member)
                    extracted_paths.append(os.path.abspath(target_path))
                    
            # 4. Delete Zip (only if we reached here successfully)
            try:
                os.remove(zip_path)
            except OSError as e:
                print(f"Error deleting zip file {zip_path}: {e}")
                
        except zipfile.BadZipFile:
            print(f"Error: {zip_path} is not a valid zip file")
            
        return extracted_paths

    def _setup_top_controls(self, parent_layout) -> None:
        layout = QHBoxLayout()
        self.btn_import = QPushButton("Import File(s)")
        self.btn_scan_folder = QPushButton("Scan Folder")
        self.btn_refresh = QPushButton("Refresh Library")
        
        self.chk_show_incomplete = QCheckBox("Show Incomplete Only")
        
        layout.addWidget(self.btn_import)
        layout.addWidget(self.btn_scan_folder)
        layout.addWidget(self.btn_refresh)
        layout.addSpacing(20)
        layout.addWidget(self.chk_show_incomplete)
        layout.addStretch()
        
        parent_layout.addLayout(layout)

    def _setup_connections(self) -> None:
        self.btn_import.clicked.connect(self._import_files)
        self.btn_scan_folder.clicked.connect(self._scan_folder)
        self.btn_refresh.clicked.connect(self.load_library)
        self.chk_show_incomplete.toggled.connect(self.load_library)
        self.search_box.textChanged.connect(self._on_search)
        
        self.filter_widget.filter_by_performer.connect(self._filter_by_performer)
        self.filter_widget.filter_by_composer.connect(self._filter_by_composer)
        self.filter_widget.filter_by_year.connect(self._filter_by_year)
        self.filter_widget.reset_filter.connect(self.load_library)
        
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(self._on_table_double_click)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._show_column_context_menu)

    def load_library(self) -> None:
        """Load library from database"""
        headers, data = self.library_service.get_all_songs()
        
        if self.chk_show_incomplete.isChecked():
            data = [
                row for row in data 
                if self._get_incomplete_fields(row)
            ]
            
        self._populate_table(headers, data)

        if self.chk_show_incomplete.isChecked():
            self._apply_incomplete_view_columns()
        else:
            self._load_column_visibility_states()

        self.filter_widget.populate()
        self.table_view.resizeColumnsToContents()

    def _apply_incomplete_view_columns(self) -> None:
        """Show only columns that are required by the criteria."""
        for col in range(self.library_model.columnCount()):
            field = self.COL_TO_FIELD.get(col)
            is_required = False
            if field:
                # Check if this field is marked as required in criteria
                rules = self.completeness_criteria.get(field, {})
                if rules.get('required', False):
                    is_required = True
            
            # Show if required, Hide if not required (or unknown)
            self.table_view.setColumnHidden(col, not is_required)

    def _populate_table(self, headers, data) -> None:
        self.library_model.clear()
        
        # Update Empty State
        if not data:
            self.empty_label.show()
            self._update_empty_label_position()
        else:
            self.empty_label.hide()
            
        if headers:
            self.library_model.setHorizontalHeaderLabels(headers)
        
        show_incomplete = self.chk_show_incomplete.isChecked()

        for row_data in data:
            failing_fields = set()
            if show_incomplete:
                failing_fields = self._get_incomplete_fields(row_data)

            items = []
            for col_idx, cell in enumerate(row_data):
                display_text = str(cell) if cell is not None else ""
                sort_value = cell
                
                # Special handling for specific columns
                if col_idx == self.COL_DURATION and isinstance(cell, (int, float)):
                    display_text = self._format_duration(cell)
                    sort_value = float(cell)
                elif col_idx in (self.COL_BPM, self.COL_FILE_ID, self.COL_YEAR) and isinstance(cell, (int, float)):
                    # Display as string, sort as number
                    sort_value = float(cell)
                else:
                    # For non-numeric columns, sort value is same as display text
                    # We ensure sort_value is set to something non-None for stable sorting
                    sort_value = display_text
                
                item = QStandardItem(display_text)
                item.setData(sort_value, Qt.ItemDataRole.UserRole)
                item.setEditable(False) # Ensure items are not editable by default
                
                # Visual Indicator for Incomplete Fields
                if show_incomplete:
                    field_name = self.COL_TO_FIELD.get(col_idx)
                    if field_name and field_name in failing_fields:
                        # Light Red Background
                        item.setBackground(QColor("#FFCDD2"))
                        item.setToolTip(f"{field_name} is incomplete")

                items.append(item)
            
            self.library_model.appendRow(items)
            
    def _format_duration(self, seconds: float) -> str:
        """Format seconds into mm:ss"""
        try:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02d}:{s:02d}"
        except Exception:
            return "00:00"

    def _filter_by_performer(self, performer_name) -> None:
        headers, data = self.library_service.get_songs_by_performer(performer_name)
        self._populate_table(headers, data)

    def _filter_by_composer(self, composer_name) -> None:
        headers, data = self.library_service.get_songs_by_composer(composer_name)
        self._populate_table(headers, data)

    def _filter_by_year(self, year: int) -> None:
        headers, data = self.library_service.get_songs_by_year(year)
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

    def import_files_list(self, files: list) -> int:
        """Import a list of files and return the count of successfully imported ones."""
        imported_count = sum(1 for file_path in files if self._import_file(file_path))
        if imported_count > 0:
            self.load_library()
        return imported_count

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
            
        imported_count = self.import_files_list(files)
                
        QMessageBox.information(
            self, 
            "Import Result", 
            f"Imported {imported_count} file(s)"
        )

    def scan_directory(self, folder: str) -> int:
        """Scan a directory recursively and import audio files."""
        imported_count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.flac', '.wav', '.m4a')):
                    file_path = os.path.join(root, file)
                    if self._import_file(file_path):
                        imported_count += 1
        
        if imported_count > 0:
            self.load_library()
        return imported_count

    def _scan_folder(self) -> None:
        # Get last used directory or default to empty string
        last_dir = self.settings_manager.get_last_import_directory() or ""
        
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", last_dir)
        if not folder:
            return
        
        # Save the directory for next time
        self.settings_manager.set_last_import_directory(folder)
            
        imported_count = self.scan_directory(folder)
                        
        QMessageBox.information(
            self, 
            "Scan Result", 
            f"Imported {imported_count} file(s)"
        )

    def _on_search(self, text) -> None:
        self.proxy_model.setFilterRegularExpression(text)

    def _get_colored_icon(self, standard_pixmap) -> QIcon:
        """Helper to invert icon colors for visibility on dark backgrounds"""
        icon = self.style().standardIcon(standard_pixmap)
        pixmap = icon.pixmap(16, 16)
        
        if pixmap.isNull():
            return icon

        img = pixmap.toImage()
        img = img.convertToFormat(QImage.Format.Format_ARGB32)
        
        for x in range(img.width()):
            for y in range(img.height()):
                color = img.pixelColor(x, y)
                # Only invert sufficiently opaque pixels
                if color.alpha() > 0:
                    # Invert RGB channels
                    new_color = QColor(
                        255 - color.red(),
                        255 - color.green(),
                        255 - color.blue(),
                        color.alpha()
                    )
                    img.setPixelColor(x, y, new_color)
        
        return QIcon(QPixmap.fromImage(img))

    def _show_table_context_menu(self, position) -> None:
        menu = QMenu()
        
        # 1. Playback / Primary Actions
        add_to_playlist_action = QAction("Add to Playlist", self)
        add_to_playlist_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_MediaPlay))
        add_to_playlist_action.triggered.connect(self._emit_add_to_playlist)
        menu.addAction(add_to_playlist_action)
        
        menu.addSeparator()

        # 2. Information / Tools
        show_id3_action = QAction("Show ID3 Data", self)
        show_id3_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        show_id3_action.triggered.connect(self._show_id3_tags)
        menu.addAction(show_id3_action)
        
        menu.addSeparator()
        
        # 3. Destructive Actions
        delete_action = QAction("Delete from Library", self)
        delete_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)
        
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
        # Do not save visibility states if we are in "Incomplete View" mode
        # as this mode temporarily hides/shows columns programmatically.
        if self.chk_show_incomplete.isChecked():
            return

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
            performer_item = self.library_model.item(source_index.row(), self.COL_PERFORMER)
            title_item = self.library_model.item(source_index.row(), self.COL_TITLE)
            
            if path_item:
                items.append({
                    "path": path_item.text(),
                    "performer": performer_item.text() if performer_item else "Unknown",
                    "title": title_item.text() if title_item else "Unknown"
                })
        
        if items:
            self.add_to_playlist.emit(items)

    def _show_id3_tags(self) -> None:
        """Shows the ID3 tags comparison dialog."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        # Use the first selected row (simpler for dialog)
        index = indexes[0]
        source_index = self.proxy_model.mapToSource(index)
        path_item = self.library_model.item(source_index.row(), self.COL_PATH)
        
        if not path_item or not path_item.text():
            return
            
        file_path = path_item.text()
        file_name = os.path.basename(file_path)
        
        try:
            # 1. Fetch File Metadata (Fresh)
            file_song = self.metadata_service.extract_from_mp3(file_path)
            raw_tags = self.metadata_service.get_raw_tags(file_path)
            
            # 2. Fetch DB Metadata (Stored)
            db_song = self.library_service.get_song_by_path(file_path)
            
            # 3. Show Dialog
            from .metadata_viewer_dialog import MetadataViewerDialog
            dialog = MetadataViewerDialog(file_song, db_song, raw_tags, self)
            dialog.exec()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Metadata Error", f"Could not read metadata for {file_name}:\n{e}")

    def _get_incomplete_fields(self, row_data) -> set:
        """Identify which fields are incomplete based on criteria.
        Returns a set of field names that failed validation.
        """
        failed_fields = set()
        
        # Map table columns to criteria keys
        # Map table columns to criteria keys dynamically
        val_map = {}
        for col_idx, field_name in self.COL_TO_FIELD.items():
            if col_idx < len(row_data):
                val_map[field_name] = row_data[col_idx]
        
        for field, rules in self.completeness_criteria.items():
            # Skip fields not present in our table view mapping
            if field not in val_map:
                continue
                
            value = val_map[field]
            is_valid = True
            
            # Check Required
            if rules.get('required', False):
                if value is None or (isinstance(value, str) and not value.strip()):
                    is_valid = False
                    
            # Check List (Performers, Composers come as strings "A, B" or None)
            if is_valid and rules.get('type') == 'list':
                if rules.get('required', False) and not value:
                     is_valid = False
                
                # If we have content, check min_length if specified (e.g. at least 1)
                if is_valid and value:
                    # Naively split by comma
                    items = [x.strip() for x in value.split(',') if x.strip()]
                    if len(items) < rules.get('min_length', 0):
                        is_valid = False
            
            # Check Number (Duration, BPM)
            if is_valid and rules.get('type') == 'number':
                if value is not None:
                    try:
                        num_val = float(value)
                        if num_val < rules.get('min_value', float('-inf')):
                            is_valid = False
                    except ValueError:
                        pass # Should be number but isn't?
            
            if not is_valid:
                failed_fields.add(field)
                        
        return failed_fields
