import os
import zipfile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableView, QPushButton, QLineEdit, QFileDialog, QMessageBox, QMenu, QStyle, QLabel,
    QCheckBox, QHeaderView, QTabBar
)
import json
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QAction, 
    QPainter, QColor, QPixmap, QIcon, QImage, QDragEnterEvent, QDropEvent, QPen
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, QEvent, QPoint

from .filter_widget import FilterWidget
from ...core import yellberus


class DropIndicatorHeaderView(QHeaderView):
    """Custom header view that shows a drop indicator line when reordering columns."""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._drop_indicator_pos = -1
        self._dragging = False
    
    def mousePressEvent(self, event):
        self._dragging = True
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drop_indicator_pos = -1
        self.viewport().update()
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            # Calculate drop position
            pos = event.position().toPoint()
            self._drop_indicator_pos = self._calculate_drop_position(pos.x())
            self.viewport().update()
        super().mouseMoveEvent(event)
    
    def _calculate_drop_position(self, x: int) -> int:
        """Calculate the x position for the drop indicator line."""
        for visual_idx in range(self.count()):
            logical_idx = self.logicalIndex(visual_idx)
            section_pos = self.sectionPosition(logical_idx)
            section_size = self.sectionSize(logical_idx)
            section_mid = section_pos + section_size // 2
            
            if x < section_mid:
                return section_pos
        
        # After last column
        if self.count() > 0:
            last_logical = self.logicalIndex(self.count() - 1)
            return self.sectionPosition(last_logical) + self.sectionSize(last_logical)
        return -1
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw drop indicator line
        if self._dragging and self._drop_indicator_pos >= 0:
            painter = QPainter(self.viewport())
            pen = QPen(QColor("#00FF00"), 4)  # Bright lime green, 4px wide
            painter.setPen(pen)
            
            x = self._drop_indicator_pos - self.offset()
            painter.drawLine(x, 0, x, self.height())
            painter.end()


class LibraryFilterProxyModel(QSortFilterProxyModel):
    """Proxy model that supports both search text and content type filtering."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_filter_id_list = [] # Empty means show all
        self._type_column = -1
        
    def setTypeFilter(self, type_ids: list, column: int):
        self._type_filter_id_list = type_ids
        self._type_column = column
        self.invalidateFilter()
        
    def filterAcceptsRow(self, source_row, source_parent):
        # 1. Type Filter
        if self._type_filter_id_list and self._type_column >= 0:
            model = self.sourceModel()
            index = model.index(source_row, self._type_column, source_parent)
            
            # Use UserRole because it contains the raw ID
            raw_val = model.data(index, Qt.ItemDataRole.UserRole)
            try:
                # Handle potential float/string/None from DB/Model
                type_id = int(float(raw_val)) if raw_val is not None else -1
            except (ValueError, TypeError):
                type_id = -1
                
            if type_id not in self._type_filter_id_list:
                return False
                
        # 2. Search Text (standard behavior)
        return super().filterAcceptsRow(source_row, source_parent)


class LibraryWidget(QWidget):
    """Widget for managing and displaying the music library"""

    # Signals
    add_to_playlist = pyqtSignal(list) # List of dicts {path, performer, title}
    remove_from_playlist = pyqtSignal(list) # List of paths to remove from playlist

    def __init__(self, library_service, metadata_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.settings_manager = settings_manager
        
        # Cache Yellberus Indices
        self.field_indices = {f.name: i for i, f in enumerate(yellberus.FIELDS)}
        
        
        self._init_ui()
        self._setup_connections()
        
        # Restore saved type filter
        saved_index = self.settings_manager.get_type_filter()
        if 0 <= saved_index < self.type_tab_bar.count():
            self.type_tab_bar.setCurrentIndex(saved_index)
            self._on_type_tab_changed(saved_index)
            
        self.load_library()



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
        
        # Type Tabs
        self.type_tab_bar = QTabBar()
        self.type_tab_bar.setExpanding(False)
        self.type_tab_bar.setDrawBase(False)
        self.type_tab_bar.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                background: #2b2b2b;
                border: 1px solid #333;
                border-bottom: none;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3c3c3c;
                border-color: #444;
            }
            QTabBar::tab:hover {
                background: #333;
            }
        """)
        
        # Define Tab Data: (Label, [TypeIDs])
        self.type_tabs = [
            ("All", []),
            ("Music", [1]),
            ("Jingles", [2]),
            ("Commercials", [3]),
            ("Speech", [4, 5]),
            ("Streams", [6]),
        ]
        
        for label, _ in self.type_tabs:
            self.type_tab_bar.addTab(label)
        
        self.library_model = QStandardItemModel()
        self.proxy_model = LibraryFilterProxyModel()
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
        
        # Use custom header with drop indicator
        custom_header = DropIndicatorHeaderView(Qt.Orientation.Horizontal, self.table_view)
        self.table_view.setHorizontalHeader(custom_header)
        
        # Enable column reordering with visual feedback
        header = self.table_view.horizontalHeader()
        header.setSectionsMovable(True)
        header.setHighlightSections(True)  # Highlight section being dragged
        header.setSectionsClickable(True)  # Required for highlight to work
        
        # Style the header with visual feedback
        header.setStyleSheet("""
            QHeaderView::section {
                padding: 4px;
            }
            QHeaderView::section:hover {
                background-color: #3a3a3a;
            }
            QHeaderView::section:pressed {
                background-color: rgba(74, 144, 217, 0.5);
                color: white;
            }
        """)
        
        # Enable Drag & Drop
        self.table_view.setAcceptDrops(True)
        self.table_view.installEventFilter(self)
        self.setAcceptDrops(True) # Allow dropping on the widget itself
        
        # Empty State Label
        self.empty_label = QLabel("Drag audio files here to import", self.table_view.viewport())
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("QLabel { color: gray; font-size: 14pt; font-weight: bold; }")
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_label.hide()
        
        center_layout.addWidget(self.search_box)
        center_layout.addWidget(self.type_tab_bar)
        center_layout.addWidget(self.table_view)
        
        self.splitter.addWidget(self.filter_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.splitter)

        # Install event filters for global drag/drop handling on child widgets
        widgets_to_watch = [
            self.table_view.viewport(), 
            self.search_box, 
            self.filter_widget, 
            self.empty_label
        ]
        if hasattr(self.filter_widget, 'tree_view'):
            widgets_to_watch.append(self.filter_widget.tree_view)
            widgets_to_watch.append(self.filter_widget.tree_view.viewport())
            
        for widget in widgets_to_watch:
            widget.installEventFilter(self)

    def eventFilter(self, source, event):
        """Handle events for the table view and children (Drag & Drop + Resize)"""
        # Handle Resize for Empty Label Position
        if source == self.table_view.viewport() and event.type() == QEvent.Type.Resize:
            self._update_empty_label_position()

        # Handle Drag & Drop for ALL watched widgets
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.DragLeave, QEvent.Type.Drop):
            if event.type() == QEvent.Type.DragEnter:
                self.dragEnterEvent(event)
                if event.isAccepted():
                    return True
            elif event.type() == QEvent.Type.DragMove:
                # Accept if matches our formats
                mime = event.mimeData()
                if mime.hasFormat("application/x-gosling-playlist-rows") or \
                   (mime.hasUrls() and any(u.isLocalFile() for u in mime.urls())):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.DragLeave:
                self.dragLeaveEvent(event)
                # Allow propagation for cleanup
            elif event.type() == QEvent.Type.Drop:
                self.dropEvent(event)
                if event.isAccepted():
                    return True

        return super().eventFilter(source, event)

    def _update_empty_label_position(self):
        """Center the empty label in the table view"""
        if self.empty_label.isVisible():
            self.empty_label.resize(self.table_view.viewport().size())
            self.empty_label.move(0, 0)

    def dragEnterEvent(self, event):
        """Validate dragged files (MP3 or ZIP) or Playlist Items"""
        mime = event.mimeData()
        
        # 1. Custom Playlist Drag (Remove from Playlist)
        if mime.hasFormat("application/x-gosling-playlist-rows"):
            event.acceptProposedAction()
            self.table_view.setStyleSheet("QTableView { border: 2px solid #F44336; }") # Red border for removal
            return

        # 2. File Import
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = path.lower().split('.')[-1]
                    if ext in ['mp3', 'zip']:
                        event.acceptProposedAction()
                        # Visual Feedback: Highlight Border (Green)
                        self.table_view.setStyleSheet("QTableView { border: 2px solid #4CAF50; }")
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Reset visual feedback"""
        self.table_view.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        """Handle dropped files or playlist items"""
        # Reset visual feedback immediately
        self.table_view.setStyleSheet("")
        
        mime = event.mimeData()

        # 1. Handle Playlist Drop (Remove)
        if mime.hasFormat("application/x-gosling-playlist-rows"):
            try:
                data = mime.data("application/x-gosling-playlist-rows")
                rows = json.loads(data.data().decode('utf-8'))
                if rows:
                    self.remove_from_playlist.emit(rows)
                event.acceptProposedAction()
                return
            except Exception as e:
                print(f"Error handling playlist drop: {e}")
                event.ignore()
                return

        # 2. Handle File Drop (Import)
        if not mime.hasUrls():
            event.ignore()
            return
            
        file_paths = []
        for url in mime.urls():
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
        self.type_tab_bar.currentChanged.connect(self._on_type_tab_changed)
        
        self.filter_widget.filter_by_performer.connect(self._filter_by_performer)
        self.filter_widget.filter_by_composer.connect(self._filter_by_composer)
        self.filter_widget.filter_by_year.connect(self._filter_by_year)
        self.filter_widget.filter_by_status.connect(self._filter_by_status)
        self.filter_widget.reset_filter.connect(self.load_library)
        
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(self._on_table_double_click)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._show_column_context_menu)
        self.table_view.horizontalHeader().sectionMoved.connect(self._on_column_moved)

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
        self._update_tab_counts()
        self.table_view.resizeColumnsToContents()

    def _apply_incomplete_view_columns(self) -> None:
        """Show only columns that are required by the criteria."""
        for col in range(self.library_model.columnCount()):
            if col < len(yellberus.FIELDS):
                field_def = yellberus.FIELDS[col]
                # Hide if not visible (e.g. ID, Path)
                self.table_view.setColumnHidden(col, not field_def.visible)
            else:
                self.table_view.setColumnHidden(col, True)

    def _on_type_tab_changed(self, index: int) -> None:
        """Handle type tab change"""
        if 0 <= index < len(self.type_tabs):
            _, type_ids = self.type_tabs[index]
            self.proxy_model.setTypeFilter(type_ids, self.field_indices['type_id'])
            self.settings_manager.set_type_filter(index)

    def _update_tab_counts(self) -> None:
        """Update the item counts on each tab label."""
        # 1. Count items per type from the source model
        # Index 0 is "All", others map to self.type_tabs
        counts = {i: 0 for i in range(len(self.type_tabs))}
        
        type_col = self.field_indices['type_id']
        for row in range(self.library_model.rowCount()):
            item = self.library_model.item(row, type_col)
            if item:
                raw_val = item.data(Qt.ItemDataRole.UserRole)
                try:
                    type_id = int(float(raw_val)) if raw_val is not None else -1
                except (ValueError, TypeError):
                    type_id = -1
                
                # Increment "All"
                counts[0] += 1
                
                # Check which other tabs this belongs to
                for i in range(1, len(self.type_tabs)):
                    _, type_ids = self.type_tabs[i]
                    if type_id in type_ids:
                        counts[i] += 1
        
        # 2. Update Tab Labels
        for i in range(len(self.type_tabs)):
            label, _ = self.type_tabs[i]
            count = counts[i]
            self.type_tab_bar.setTabText(i, f"{label} ({count})")

    def _populate_table(self, headers, data) -> None:
        self.library_model.clear()
        
        # Update Empty State
        if not data:
            self.empty_label.show()
            self._update_empty_label_position()
        else:
            self.empty_label.hide()
            
        if headers:
            # IGNORE SQL headers! Use Yellberus headers for consistency.
            # This ensures "Title" instead of "MS.Name" without aliasing every SQL column.
            ui_headers = [f.ui_header for f in yellberus.FIELDS]
            self.library_model.setHorizontalHeaderLabels(ui_headers)
        
        show_incomplete = self.chk_show_incomplete.isChecked()

        for row_data in data:
            # Always calculate completeness for validation
            failing_fields = self._get_incomplete_fields(row_data)

            items = []
            for col_idx, cell in enumerate(row_data):
                display_text = str(cell) if cell is not None else ""
                sort_value = cell
                
                # Special handling for specific columns
                if col_idx == self.field_indices['duration'] and isinstance(cell, (int, float)):
                    display_text = self._format_duration(cell)
                    sort_value = float(cell)
                elif col_idx in (self.field_indices['bpm'], self.field_indices['file_id'], self.field_indices['recording_year']) and isinstance(cell, (int, float)):
                    # Display as string, sort as number
                    sort_value = float(cell)
                else:
                    sort_value = display_text
                
                item = QStandardItem(display_text)
                item.setData(sort_value, Qt.ItemDataRole.UserRole)
                item.setEditable(False) # Ensure items are not editable by default
                
                # Checkbox for IsDone
                if col_idx == self.field_indices['is_done']:
                    item.setCheckable(True)
                    item.setEditable(False) 
                    
                    # Determine Flags: Selectable always, Enabled only if complete
                    flags = Qt.ItemFlag.ItemIsSelectable
                    if not failing_fields:
                        flags |= Qt.ItemFlag.ItemIsEnabled
                    item.setFlags(flags)
                    
                    # Set State
                    is_done_bool = bool(cell) if cell is not None else False
                    item.setCheckState(Qt.CheckState.Checked if is_done_bool else Qt.CheckState.Unchecked)
                    item.setText("")
                
                # Visual Indicator for Incomplete Fields
                if show_incomplete:
                    if col_idx < len(yellberus.FIELDS):
                        field_name = yellberus.FIELDS[col_idx].name
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

    def _filter_by_status(self, is_done: bool) -> None:
        headers, data = self.library_service.get_songs_by_status(is_done)
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
        
        # Smart Status Toggle
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            statuses = []
            for idx in indexes:
                source_idx = self.proxy_model.mapToSource(idx)
                # COL_IS_DONE is column 9
                item = self.library_model.item(source_idx.row(), self.field_indices['is_done'])
                # Checkbox state: Checked=2, Unchecked=0
                is_done = (item.checkState() == Qt.CheckState.Checked) if item else False
                statuses.append(is_done)
            
            all_done = all(statuses)
            all_not_done = all(not s for s in statuses)
            
            status_action = QAction(self)
            if all_done:
                status_action.setText("Mark as Not Done")
                status_action.triggered.connect(lambda: self._toggle_status(False))
            elif all_not_done:
                status_action.setText("Mark as Done")
                # Check if all selected items are valid (Enabled)
                all_valid = True
                for idx in indexes:
                    source_idx = self.proxy_model.mapToSource(idx)
                    item = self.library_model.item(source_idx.row(), self.field_indices['is_done'])
                    if not item.isEnabled():
                        all_valid = False
                        break
                
                if not all_valid:
                    status_action.setEnabled(False)
                    status_action.setToolTip("Cannot mark as Done: Some selected items are incomplete")
                    status_action.setText("Mark as Done (Fix Errors First)")
                
                status_action.triggered.connect(lambda: self._toggle_status(True))
            else:
                status_action.setText("Mixed Status (Cannot Toggle)")
                status_action.setEnabled(False)
            
            menu.addAction(status_action)
        
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
        header = self.table_view.horizontalHeader()
        
        # Iterate by visual order so menu matches displayed column order
        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            header_text = self.library_model.headerData(logical_idx, Qt.Orientation.Horizontal)
            action = QAction(str(header_text), self)
            action.setCheckable(True)
            action.setChecked(not self.table_view.isColumnHidden(logical_idx))
            action.setData(logical_idx)
            action.toggled.connect(self._toggle_column_visibility)
            menu.addAction(action)
        
        menu.addSeparator()
        reset_action = QAction("Reset to Default", self)
        reset_action.triggered.connect(self._reset_column_layout)
        menu.addAction(reset_action)
        
        menu.exec(header.mapToGlobal(position))

    def _toggle_column_visibility(self, checked) -> None:
        action = self.sender()
        if action:
            column = action.data()
            self.table_view.setColumnHidden(column, not checked)
            self._save_column_layout()

    def _reset_column_layout(self) -> None:
        """Reset columns to default order and visibility."""
        header = self.table_view.horizontalHeader()
        col_count = header.count()
        
        # Reset order: move each column to its logical position
        for logical_idx in range(col_count):
            current_visual = header.visualIndex(logical_idx)
            if current_visual != logical_idx:
                header.moveSection(current_visual, logical_idx)
        
        # Reset visibility: show all columns
        for col in range(col_count):
            self.table_view.setColumnHidden(col, False)
        
        # Clear saved layout
        self.settings_manager.remove_setting("library/layouts")

    def _on_column_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Save column layout when user drags a column."""
        self._save_column_layout()

    def _load_column_layout(self) -> None:
        """Load and apply column layout (order + visibility) from settings."""
        layout = self.settings_manager.get_column_layout("default")
        if not layout:
            return
        
        header = self.table_view.horizontalHeader()
        order = layout.get("order", [])
        hidden = layout.get("hidden", [])
        
        # Restore order: move each column to its saved visual position
        if order:
            for visual_idx, logical_idx in enumerate(order):
                if logical_idx < header.count():
                    current_visual = header.visualIndex(logical_idx)
                    if current_visual != visual_idx:
                        header.moveSection(current_visual, visual_idx)
        
        # Restore visibility
        for col in range(header.count()):
            self.table_view.setColumnHidden(col, col in hidden)

    def _save_column_layout(self) -> None:
        """Save column layout (order + visibility) to settings."""
        # Do not save if we are in "Incomplete View" mode
        if self.chk_show_incomplete.isChecked():
            return
        
        header = self.table_view.horizontalHeader()
        col_count = header.count()
        
        # Order: list of logical indices in visual order (includes ALL columns)
        order = [header.logicalIndex(visual_idx) for visual_idx in range(col_count)]
        
        # Hidden: list of logical indices that are hidden
        hidden = [col for col in range(col_count) if self.table_view.isColumnHidden(col)]
        
        self.settings_manager.set_column_layout(order, hidden, "default")

    # Legacy method for backward compatibility
    def _load_column_visibility_states(self) -> None:
        """Load column layout. Uses new format, falls back to legacy if needed."""
        layout = self.settings_manager.get_column_layout("default")
        if layout:
            self._load_column_layout()
        else:
            # Fallback to legacy format
            visibility_states = self.settings_manager.get_column_visibility()
            if isinstance(visibility_states, dict):
                for col_str, visible in visibility_states.items():
                    if isinstance(col_str, str) and col_str.isdigit():
                        self.table_view.setColumnHidden(int(col_str), not visible)

    def _save_column_visibility_states(self) -> None:
        """Save column layout (wraps new method for compatibility)."""
        self._save_column_layout()

    def _toggle_status(self, new_status: bool) -> None:
        """Bulk update status for selected rows with validation"""
        indexes = self.table_view.selectionModel().selectedRows()
        
        # Validation Check (Only when marking as Done)
        if new_status:
            failed_items = []
            
            for index in indexes:
                source_index = self.proxy_model.mapToSource(index)
                
                # Get full row data for validation
                row_data = []
                for col in range(self.library_model.columnCount()):
                     item = self.library_model.item(source_index.row(), col)
                     row_data.append(item.data(Qt.ItemDataRole.UserRole) if item else None)

                incomplete = self._get_incomplete_fields(row_data)
                if incomplete:
                    title_item = self.library_model.item(source_index.row(), self.field_indices['title'])
                    title = title_item.text() if title_item else "Unknown"
                    failed_items.append(f"- {title}: Missing {', '.join(incomplete)}")
            
            if failed_items:
                msg = "Cannot mark selection as Done because some items are incomplete:\n\n"
                msg += "\n".join(failed_items[:10])
                if len(failed_items) > 10:
                    msg += f"\n...and {len(failed_items)-10} more."
                QMessageBox.warning(self, "Validation Failed", msg)
                return

        # Proceed with update
        count = 0
        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            file_id_item = self.library_model.item(source_index.row(), self.field_indices['file_id'])
            if file_id_item:
                file_id = int(file_id_item.text())
                if self.library_service.update_song_status(file_id, new_status):
                    count += 1
        
        if count > 0:
            self.load_library()

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
                file_id_item = self.library_model.item(source_index.row(), self.field_indices['file_id'])
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
            row = source_index.row()
            
            path_item = self.library_model.item(row, self.field_indices['path'])
            perf_item = self.library_model.item(row, self.field_indices['performers'])
            title_item = self.library_model.item(row, self.field_indices['title'])
            
            if path_item:
                items.append({
                    "path": path_item.text(),
                    "performer": perf_item.text() if perf_item else "Unknown",
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
        path_item = self.library_model.item(source_index.row(), self.field_indices['path'])
        
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
            
            # Connect Actions
            dialog.import_requested.connect(lambda: self._handle_metadata_import(file_song))
            dialog.export_requested.connect(lambda: self._handle_metadata_export(db_song))
            
            dialog.exec()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Metadata Error", f"Could not read metadata for {file_name}:\n{e}")

    def _handle_metadata_import(self, song):
        """Update repository with values from file (Import to DB)"""
        try:
            # If song already exists in DB (checked by path), this updates it.
            # If it's new, we might need add_file logic? 
            # But the viewer is usually opened on existing items.
            # If db_song was None, we definitely need to insert first?
            # library_service.update_song handles updates.
            
            # Ensure it has an ID if it's new?
            # The song object from extract_from_mp3 might not have ID if not passed in.
            
            existing = self.library_service.get_song_by_path(song.path)
            if existing:
                song.file_id = existing.file_id
                self.library_service.update_song(song)
                QMessageBox.information(self, "Success", "Library updated from file metadata.")
            else:
                # New file case
                self.library_service.add_file(song.path)
                # Then update with full metadata
                new_song_ref = self.library_service.get_song_by_path(song.path)
                if new_song_ref:
                    song.file_id = new_song_ref.file_id
                    self.library_service.update_song(song)
                QMessageBox.information(self, "Success", "New song added to library.")
                
            self.load_library()
            
        except Exception as e:
             QMessageBox.critical(self, "Import Error", f"Failed to update library:\n{e}")

    def _handle_metadata_export(self, song):
        """Update file tags from database (Export to File)"""
        try:
           result = self.metadata_service.write_tags(song)
           if result:
               QMessageBox.information(self, "Success", "Metadata export logic triggered (Check console/debug).")
           else:
               QMessageBox.warning(self, "Failure", "Failed to triggered write logic.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to write tags:\n{e}")

    def _get_incomplete_fields(self, row_data: list) -> set:
        """Identify which fields are incomplete based on Yellberus registry.
        Returns a set of field names that failed validation.
        """
        failed_fields = set()
        
        for col_idx, cell_value in enumerate(row_data):
            if col_idx >= len(yellberus.FIELDS):
                break
                
            field_def = yellberus.FIELDS[col_idx]
            is_valid = True
            
            # 1. Check Required
            if field_def.required:
                if cell_value is None or (isinstance(cell_value, str) and not cell_value.strip()):
                    is_valid = False
            
            # 2. Check List Type
            if is_valid and field_def.field_type == yellberus.FieldType.LIST:
                if field_def.required and not cell_value:
                    is_valid = False
                elif cell_value and field_def.min_length is not None:
                    # cell_value from DB for LIST is GROUP_CONCAT string
                    items = [x.strip() for x in str(cell_value).split(',') if x.strip()]
                    if len(items) < field_def.min_length:
                        is_valid = False
            
            # 3. Check Text Min Length
            elif is_valid and field_def.field_type == yellberus.FieldType.TEXT:
                if cell_value and field_def.min_length is not None:
                    if len(str(cell_value).strip()) < field_def.min_length:
                        is_valid = False
            
            # 4. Check Numeric/Duration Min Value
            elif is_valid and field_def.field_type in (yellberus.FieldType.INTEGER, yellberus.FieldType.REAL, yellberus.FieldType.DURATION):
                if cell_value is not None and field_def.min_value is not None:
                    try:
                        num_val = float(cell_value)
                        if num_val < field_def.min_value:
                            is_valid = False
                    except (ValueError, TypeError):
                        # Non-numeric value in numeric field is caught by integrity tests or 'required'
                        pass 
            
            if not is_valid:
                failed_fields.add(field_def.name)
                
        return failed_fields
