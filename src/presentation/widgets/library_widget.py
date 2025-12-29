import os
import zipfile
import weakref
from typing import Optional, List, Set, Union
from ...data.models.song import Song
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableView, QLineEdit, QFileDialog, QMessageBox, QMenu, QStyle, QLabel,
    QCheckBox, QHeaderView, QButtonGroup, QSizePolicy, QStackedWidget, QFrame
)
import json
from ...resources import constants
from .filter_widget import FilterWidget
from ...core import yellberus
from .library_delegate import WorkstationDelegate
from .history_drawer import HistoryDrawer
from .jingle_curtain import JingleCurtain
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, QEvent, QObject, QPropertyAnimation, QEasingCurve, pyqtProperty, QParallelAnimationGroup, QMimeData, QPoint, QModelIndex
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QAction, 
    QPainter, QColor, QPixmap, QIcon, QImage, QPen, QDrag, QFont
)
from .glow_factory import GlowButton


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
            pen = QPen(QColor(constants.COLOR_DROP_INDICATOR), 4)
            painter.setPen(pen)
            
            x = self._drop_indicator_pos - self.offset()
            painter.drawLine(x, 0, x, self.height())
            painter.end()


class LibraryFilterProxyModel(QSortFilterProxyModel):
    """Proxy model that supports search, type, and advanced multicheck filtering."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_filter_id_list = []
        self._type_column = -1
        
        # T-55: Smart Proxy State
        self._active_filters = {} # {field_name: set(values)}
        self._field_indices = {} # {field_name: col_idx}
        self._filter_match_mode = "AND"
        
    def setTypeFilter(self, type_ids: list, column: int):
        self._type_filter_id_list = type_ids
        self._type_column = column
        self.invalidateFilter()

    def setCheckFilters(self, filters: dict, field_indices: dict):
        """Update multicheck filter state {field_name: set(values)}"""
        self._active_filters = filters
        self._field_indices = field_indices
        self.invalidateFilter()

    def setFilterMatchMode(self, mode: str):
        """Set cross-category logic: 'AND' or 'OR'."""
        self._filter_match_mode = mode
        self.invalidateFilter()

    def _check_value_match(self, model, row, parent, field_name, required_val) -> bool:
        """Surgical Match: Handles metadata, lists, and procedural commands."""
        # Get Column Index
        col_idx = self._field_indices.get(field_name, -1)
        if col_idx < 0: return False
        
        # Get Row Data
        row_val = model.data(model.index(row, col_idx, parent), Qt.ItemDataRole.UserRole)
        
        # 1. Procedural Workflow: "READY" (Valid but NOT Done)
        # 1. Procedural Workflow: "READY" (Valid but NOT Done)
        if field_name == 'is_done' and required_val == "READY":
             is_already_done = bool(row_val)
             # Catch string booleans in row_val (e.g. "1" or "0")
             if isinstance(row_val, str):
                 if row_val == "1" or row_val.lower() == "true": is_already_done = True
                 elif row_val == "0" or row_val.lower() == "false": is_already_done = False
             elif isinstance(row_val, (int, float)):
                 is_already_done = bool(row_val)
                 
             if is_already_done: return False # Ready means NOT Done.
             
             # Construct minimal data row aligned with FIELDS
             # Yellberus expects a list where index I matches FIELDS[I]
             validation_row = []
             for f in yellberus.FIELDS:
                 f_idx = self._field_indices.get(f.name, -1)
                 if f_idx >= 0:
                     val = model.data(model.index(row, f_idx, parent), Qt.ItemDataRole.UserRole)
                     validation_row.append(val)
                 else:
                     validation_row.append(None)
                     
             return len(yellberus.validate_row(validation_row)) == 0

        # 2. Normalize Row Data
        if isinstance(row_val, str) and ',' in row_val:
            row_items = [s.strip() for s in row_val.split(',')]
        elif isinstance(row_val, (list, tuple)):
            row_items = list(row_val)
        else:
            row_items = [row_val]

        # 3. Normalized Matching
        req_str = str(required_val).lower()
        for item in row_items:
            # 1. Exact Match
            if item == required_val: return True
            
            # 2. Boolean Impedance Match (Handling "0" string trap)
            if isinstance(required_val, bool):
                bool_item = None
                if isinstance(item, bool): bool_item = item
                elif isinstance(item, (int, float)): bool_item = bool(item)
                elif isinstance(item, str):
                    # Pitfall: bool("0") is True in Python. Must catch explicitly.
                    if item == "0" or item.lower() == "false": bool_item = False
                    elif item == "1" or item.lower() == "true": bool_item = True
                
                if bool_item is not None and bool_item == required_val:
                    return True

            # 3. String Fallback
            if str(item).lower() == req_str: return True
            
        return False
        
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        
        # 1. Type Filter (AND)
        if self._type_filter_id_list and self._type_column >= 0:
            index = model.index(source_row, self._type_column, source_parent)
            raw_val = model.data(index, Qt.ItemDataRole.UserRole)
            try:
                type_id = int(float(raw_val)) if raw_val is not None else -1
            except (ValueError, TypeError):
                type_id = -1
            if type_id not in self._type_filter_id_list:
                return False
        
        # 3. Multicheck Filters (Universal Logic Gate)
        if self._active_filters:
            # Flatten all active checkboxes into a single requirement list
            all_requirements = []
            for field, values in self._active_filters.items():
                for val in values:
                    all_requirements.append((field, val))
            
            if all_requirements:
                if self._filter_match_mode == "AND":
                    # UNIVERSAL AND: EVERY selected checkbox must be satisfied
                    for field, req_val in all_requirements:
                        if not self._check_value_match(model, source_row, source_parent, field, req_val):
                            return False
                else:
                    # UNIVERSAL ANY: AT LEAST ONE selected checkbox is sufficient
                    match_found = False
                    for field, req_val in all_requirements:
                        if self._check_value_match(model, source_row, source_parent, field, req_val):
                            match_found = True
                            break
                    if not match_found:
                        return False
        
        # 5. Search Text (Standard behavior)
        return super().filterAcceptsRow(source_row, source_parent)


class EventFilterProxy(QObject):
    """Proxy to break reference cycles in event filtering."""
    def __init__(self, target):
        super().__init__()
        self._target = weakref.ref(target)

    def eventFilter(self, source, event):
        target = self._target()
        if target:
            return target.handle_filtered_event(source, event)
        return False


class LibraryTable(QTableView):
    """Table view for the library."""
    pass

class LibraryWidget(QWidget):
    """Widget for managing and displaying the music library"""

    # Signals
    add_to_playlist = pyqtSignal(list) # List of dicts {path, performer, title}
    remove_from_playlist = pyqtSignal(list) # List of paths to remove from playlist
    play_immediately = pyqtSignal(str) # Path to play
    focus_search_requested = pyqtSignal()

    def __init__(self, library_service, metadata_service, settings_manager, renaming_service, duplicate_scanner, conversion_service=None, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.settings_manager = settings_manager
        self.renaming_service = renaming_service
        self.duplicate_scanner = duplicate_scanner
        self.conversion_service = conversion_service
        
        # Cache Yellberus Indices
        self.field_indices = {f.name: i for i, f in enumerate(yellberus.FIELDS)}
        
        # Flags
        self._show_incomplete = False
        
        # Flag to suppress auto-save during programmatic resize
        self._suppress_layout_save = False
        self._dirty_ids = set() # Store IDs with unsaved changes
        
        # Proxy for event filtering to avoid reference cycles
        self._event_filter_proxy = EventFilterProxy(self)
        
        self._init_ui()
        self._setup_connections()
        
        # Drag State
        self._drag_start_pos = QPoint()
        
        # Restore saved type filter
        saved_index = self.settings_manager.get_type_filter()
        btn = self.pill_group.button(saved_index)
        if btn:
            btn.setChecked(True)
            self._on_type_tab_changed(saved_index)
            
        self.load_library()

    def update_dirty_rows(self, ids: list):
        """Update the list of IDs with unsaved changes for visual feedback."""
        self._dirty_ids = set(ids)
        # Force the table to repaint to reflect new amber glows
        if hasattr(self, 'table_view') and self.table_view:
            self.table_view.viewport().update()


    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter for Sidebar + Table Area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("MainSplitter")
        
        # --- SIDEBAR AREA (Mechanical Console) ---
        sidebar_container = QWidget()
        sidebar_layout = QHBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Constraint: Prevent collapse of Filter Deck (Corridor: 180px - 350px)
        sidebar_container.setMinimumWidth(200)
        sidebar_container.setMaximumWidth(350)
        
        # 1. THE FRONT DECK (Filters - Pure Input)
        self.filter_widget = FilterWidget(self.library_service)
        self.filter_widget.setObjectName("FilterWidget")
        sidebar_layout.addWidget(self.filter_widget)
        
        # 2. THE REAR DECK (History/Log is now handled by the Right Terminal)
        # T-55 Synergy: We keep this container for potential future auxiliary tools, 
        # but for now, the 'Log' resides in the main broadcast stack on the right.
        self.history_drawer = HistoryDrawer(self.field_indices, self)
        self.history_drawer.setFixedWidth(0) 
        self.history_drawer.setMinimumWidth(0)
        self.history_drawer.setObjectName("SidebarHistory")
        sidebar_layout.addWidget(self.history_drawer)
        
        self.splitter.addWidget(sidebar_container)
        
        # Prevent Sidebar from collapsing to 0
        self.splitter.setCollapsible(0, False)
        
        # Animation Target Constants
        self._filter_base_width = 250
        self._history_target_width = 350
        self._rail_width = 26
        
        # --- CENTER AREA (The Mission Deck) ---
        center_widget = QFrame()
        center_widget.setObjectName("CenterLibraryPanel")
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # Constraint: Ensure Table has breathing room (Prevents header crunch)
        center_widget.setMinimumWidth(550)
        
        # Header Strip (Pills)
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 4, 0, 6)
        header_layout.setSpacing(6)
        
        # Category Pills
        self.pill_group = QButtonGroup(self)
        self.pill_group.setExclusive(True)
        self.category_glow_btns = [] # Store the wrappers for direct text updates
        self.pill_group.idClicked.connect(self._on_pill_clicked)

        shorthand = {"All": "ALL", "Music": "MUS", "Jingles": "JIN", "Commercials": "COM", "Speech": "SP", "Streams": "STR"}
        self.type_tabs = [("All", []), ("Music", [1]), ("Jingles", [2]), ("Commercials", [3]), ("Speech", [4, 5]), ("Streams", [6])]

        for i, (label, _) in enumerate(self.type_tabs):
            short = shorthand.get(label, label)
            btn = GlowButton(short)
            btn.setCheckable(True)
            btn.setObjectName("CategoryPill")
            btn.setProperty("category", label) # Set the semantic label (Music, Jingles, etc.)
            if i == 0: btn.setChecked(True)
            self.pill_group.addButton(btn.btn, i)
            self.category_glow_btns.append(btn)
            header_layout.addWidget(btn)

        header_layout.addStretch()
        
        header_layout.addStretch()
        
        center_layout.addWidget(header_container)
        
        # The Library Table
        self.library_model = QStandardItemModel()
        self.proxy_model = LibraryFilterProxyModel()
        self.proxy_model.setSourceModel(self.library_model)
        self.proxy_model.setFilterKeyColumn(-1) # Search all columns
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setSortRole(Qt.ItemDataRole.UserRole) # Use UserRole for sorting
        
        self.table_view = LibraryTable()
        self.table_view.setObjectName("LibraryTable")
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.setSortingEnabled(True)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setMouseTracking(True) # Enable hover effects in delegate
        self.table_view.setShowGrid(False)  # Blade-Edge: No vertical lines
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        
        # Use custom header with drop indicator
        custom_header = DropIndicatorHeaderView(Qt.Orientation.Horizontal, self.table_view)
        self.table_view.setHorizontalHeader(custom_header)

        # Workstation Delegate (Visual Life)
        self.delegate = WorkstationDelegate(self.field_indices, self.table_view, self)
        self.table_view.setItemDelegate(self.delegate)
        self._hovered_row = -1
        
        # Connect Hover Tracking
        self.table_view.setMouseTracking(True)
        self.table_view.entered.connect(self._on_item_entered)
        # Clear hover when leaving viewport
        self.table_view.viewport().installEventFilter(self)
        
        # Enable column reordering with visual feedback
        header = self.table_view.horizontalHeader()
        header.setSectionsMovable(True)
        header.setHighlightSections(True)  # Highlight section being dragged
        header.setSectionsClickable(True)  # Required for highlight to work
        
        # T-18: Auto-save layout on move/resize
        header.sectionMoved.connect(self._on_column_moved)
        header.sectionResized.connect(self._on_column_resized)
        
        # Style the header via objectName
        header.setObjectName("LibraryHeader")
        
        # Enable Drag & Drop
        self.table_view.setAcceptDrops(True)
        self.setAcceptDrops(True) # Allow dropping on the widget itself
        
        # Empty State Label
        self.empty_label = QLabel("Drag audio files here to import", self.table_view.viewport())
        self.empty_label.setObjectName("LibraryEmptyLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_label.hide()
        
        # Assemble Center Layout
        center_layout.addWidget(self.table_view)
        
        # Finalize Splitter (Sidebar Container [1] | Center Widget [2])
        self.splitter.addWidget(center_widget)
        
        # State Tracking & Constants
        self._history_open = False
        self._sidebar_base_width = 250
        self._sidebar_expanded_width = 450
        
        # Set Initial Proportions
        # Sidebar (0): Fluid (1) - Acts as sponge/shock absorber
        # Table (1): Rigid (0) - Maintains width priority
        self.splitter.setStretchFactor(0, 1) 
        self.splitter.setStretchFactor(1, 0) 
        self.splitter.setSizes([self._sidebar_base_width + self._rail_width, 900])
        
        main_layout.addWidget(self.splitter)

        # Install event filters for global drag/drop handling on child widgets
        # Note: empty_label is transparent to mouse events, so no filter needed
        widgets_to_watch = [
            self.table_view.viewport(), 
            self.filter_widget
        ]
        if hasattr(self.filter_widget, 'tree_view'):
            widgets_to_watch.append(self.filter_widget.tree_view)
            widgets_to_watch.append(self.filter_widget.tree_view.viewport())
            
            
        for widget in widgets_to_watch:
            widget.installEventFilter(self._event_filter_proxy)

    def handle_filtered_event(self, source, event) -> bool:
        """
        Handle events delegating from EventFilterProxy.
        """
        try:
            # 1. Drag & Drop Initiation (on table_view viewport)
            if source == self.table_view.viewport():
                if event.type() == QEvent.Type.MouseButtonPress:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self._drag_start_pos = event.position().toPoint()
                
                elif event.type() == QEvent.Type.MouseMove:
                    if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_start_pos:
                        # Check threshold
                        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() > (self.style().pixelMetric(QStyle.PixelMetric.PM_LargeIconSize) // 4):
                            self._start_drag()
                            return True # Event handled (drag started)

            # 2. Resize for Empty Label Position
            if source == self.table_view.viewport() and event.type() == QEvent.Type.Resize:
                self._update_empty_label_position()

            # 3. Handle Drag & Drop for ALL watched widgets (Accept/Drop logic)
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.DragLeave, QEvent.Type.Drop):
                if event.type() == QEvent.Type.DragEnter:
                    self.dragEnterEvent(event)
                    if event.isAccepted():
                        return True
                elif event.type() == QEvent.Type.DragMove:
                    mime = event.mimeData()
                    if mime.hasFormat("application/x-gosling-playlist-rows") or \
                       (mime.hasUrls() and any(u.isLocalFile() for u in mime.urls())):
                        event.acceptProposedAction()
                        return True
                elif event.type() == QEvent.Type.DragLeave:
                    self.dragLeaveEvent(event)
                elif event.type() == QEvent.Type.Drop:
                    self.dropEvent(event)
                    if event.isAccepted():
                        return True
        except RuntimeError:
            # Handle case where C++ objects (like table_view) are already deleted during shutdown
            return False
        except Exception:
            pass
            
        return False

    def _start_drag(self):
        """Prepare and start a drag operation for selected items."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        songs_to_drag = []
        path_col = self.field_indices.get('path', -1)
        performer_col = self.field_indices.get('performers', -1)
        title_col = self.field_indices.get('title', -1)
        
        for idx in indexes:
            source_row = self.proxy_model.mapToSource(idx).row()
            item_path = self.library_model.item(source_row, path_col)
            item_perf = self.library_model.item(source_row, performer_col)
            item_title = self.library_model.item(source_row, title_col)
            
            if not item_path: continue
            
            path = item_path.data(Qt.ItemDataRole.DisplayRole)
            performer = item_perf.data(Qt.ItemDataRole.DisplayRole) if item_perf else ""
            title = item_title.data(Qt.ItemDataRole.DisplayRole) if item_title else ""
            
            if isinstance(performer, (list, tuple)):
                performer = ", ".join(performer)
            
            songs_to_drag.append({
                'path': path,
                'performer': performer or "Unknown Artist",
                'title': title or "Unknown Title"
            })

        if not songs_to_drag:
            return

        mime_data = QMimeData()
        mime_data.setData("application/x-gosling-library-rows", json.dumps(songs_to_drag).encode('utf-8'))
        
        # Standard URL list for external drag
        from PyQt6.QtCore import QUrl
        urls = [QUrl.fromLocalFile(s['path']) for s in songs_to_drag if s['path']]
        mime_data.setUrls(urls)

        drag = QDrag(self.table_view)
        drag.setMimeData(mime_data)
        
        # Set a drag icon (AMBER THEME)
        pixmap = QPixmap(140, 36)
        pixmap.fill(QColor(constants.COLOR_MUTED_AMBER))
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.black) # Black on Amber for readability
        painter.setFont(QFont("Bahnschrift Condensed", 10))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"DRAGGING {len(songs_to_drag)} ITEMS")
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(70, 18))
        
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def _update_empty_label_position(self):
        """Center the empty label in the table view"""
        if self.empty_label.isVisible():
            self.empty_label.resize(self.table_view.viewport().size())
            self.empty_label.move(0, 0)

    def dragEnterEvent(self, event):
        """Validate dragged files (MP3 or ZIP) or Playlist Items"""
        # Ignore internal drags from the table itself (e.g. column move or row drag)
        if event.source() == self.table_view:
            event.ignore()
            return

        mime = event.mimeData()
        
        # 1. Custom Playlist Drag (Remove from Playlist)
        if mime.hasFormat("application/x-gosling-playlist-rows"):
            event.acceptProposedAction()
            self.table_view.setProperty("drag_status", "reject")
            self.table_view.style().unpolish(self.table_view)
            self.table_view.style().polish(self.table_view)
            return

        # 2. File Import
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = path.lower().split('.')[-1]
                    if ext in ['mp3', 'zip', 'wav']:
                        event.acceptProposedAction()
                        self.table_view.setProperty("drag_status", "accept")
                        self.table_view.style().unpolish(self.table_view)
                        self.table_view.style().polish(self.table_view)
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Reset visual feedback"""
        self.table_view.setProperty("drag_status", "")
        self.table_view.style().unpolish(self.table_view)
        self.table_view.style().polish(self.table_view)
        event.accept()

    def dropEvent(self, event):
        """Handle dropped files or playlist items with WAV detection and ZIP inspection."""
        if event.source() == self.table_view:
            event.ignore()
            return

        self.table_view.setProperty("drag_status", "")
        self.table_view.style().unpolish(self.table_view)
        self.table_view.style().polish(self.table_view)
        
        mime = event.mimeData()
        if mime.hasFormat("application/x-gosling-playlist-rows"):
            event.acceptProposedAction()
            return

        if not mime.hasUrls():
            event.ignore()
            return

        standalone_mp3s = []
        standalone_wavs = []
        zip_info = {} # path -> {'mp3': [], 'wav': []}
        
        for url in mime.urls():
            if not url.isLocalFile(): continue
            path = os.path.abspath(url.toLocalFile())
            ext = path.lower().split('.')[-1]
            
            if ext == 'mp3':
                standalone_mp3s.append(path)
            elif ext == 'wav':
                standalone_wavs.append(path)
            elif ext == 'zip':
                try:
                    with zipfile.ZipFile(path, 'r') as zr:
                        members = zr.namelist()
                        mp3s = [m for m in members if m.lower().endswith('.mp3') and '..' not in m]
                        wavs = [m for m in members if m.lower().endswith('.wav') and '..' not in m]
                        if mp3s or wavs:
                            zip_info[path] = {'mp3': mp3s, 'wav': wavs}
                except Exception:
                    pass

        total_wavs = len(standalone_wavs) + sum(len(v['wav']) for v in zip_info.values())
        
        convert_choice = False
        delete_wav_choice = False

        if total_wavs > 0:
            if self.conversion_service and self.conversion_service.is_ffmpeg_available():
                reply = QMessageBox.question(
                    self, "WAV Files Detected",
                    f"{total_wavs} WAV file(s) found in the import. Convert them to MP3?\n\n(Lossy collection preference)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                convert_choice = (reply == QMessageBox.StandardButton.Yes)
                
                if convert_choice:
                    # The "Pester" Prompt (Per User Request)
                    del_reply = QMessageBox.question(
                        self, "Cleanup Confirmation",
                        "Delete original WAV files after successful conversion?\n\n(Source files will be removed from disk)",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    delete_wav_choice = (del_reply == QMessageBox.StandardButton.Yes)
            else:
                # FFmpeg missing - User wants to know!
                QMessageBox.warning(self, "Conversion Unavailable", 
                                    "WAV files detected but FFmpeg was not found.\n\nPlease configure FFmpeg in Settings to enable conversion.")
                # We do NOT return here, we allow dropping other files (MP3s) if any.
                # But WAVs will be ignored.

        final_import_list = []
        final_import_list.extend(standalone_mp3s)
        
        failed_conversions = 0
        
        # 1. Standalone WAVs
        if convert_choice:
            for wv in standalone_wavs:
                # Sniff metadata from WAV before it's gone
                wav_song = self.metadata_service.extract_metadata(wv)
                mp3 = self.conversion_service.convert_wav_to_mp3(wv)
                if mp3:
                    # Carry over tags to the new MP3
                    self.conversion_service.sync_tags(wav_song, mp3)
                    final_import_list.append(os.path.abspath(mp3))
                    if delete_wav_choice:
                        try: os.remove(wv) 
                        except: pass
                else:
                    failed_conversions += 1
        
        # 2. Handle ZIPs
        for zp, info in zip_info.items():
            base_dir = os.path.dirname(zp)
            zip_import_list = []
            
            # Extract MP3s always
            with zipfile.ZipFile(zp, 'r') as zr:
                for m in info['mp3']:
                    try:
                        zr.extract(m, base_dir)
                        zip_import_list.append(os.path.abspath(os.path.join(base_dir, m)))
                    except Exception: pass
                
                # Extract and Convert WAVs if user said YES
                if convert_choice:
                    for m in info['wav']:
                        try:
                            zr.extract(m, base_dir)
                            temp_wav = os.path.join(base_dir, m)
                            # Sniff metadata
                            wav_song = self.metadata_service.extract_metadata(temp_wav)
                            new_mp3 = self.conversion_service.convert_wav_to_mp3(temp_wav)
                            if new_mp3:
                                # Carry over tags
                                self.conversion_service.sync_tags(wav_song, new_mp3)
                                zip_import_list.append(os.path.abspath(new_mp3))
                                try: os.remove(temp_wav)
                                except: pass
                            else:
                                failed_conversions += 1
                        except Exception: 
                            failed_conversions += 1
            
            final_import_list.extend(zip_import_list)
            
            # Deletion Logic
            should_delete_zip = False
            if not info['wav']: 
                # Pure MP3 zip, safe to clear
                should_delete_zip = True
            elif convert_choice and delete_wav_choice and failed_conversions == 0:
                # Converted and user explicitly said YES to cleanup (AND NO FAILURES)
                should_delete_zip = True
            
            if should_delete_zip:
                try: os.remove(zp)
                except: pass

        if final_import_list or failed_conversions > 0:
            event.acceptProposedAction()
            count = 0
            if final_import_list:
                count = self.import_files_list(final_import_list)
            
            msg = f"Imported {count} file(s)."
            if failed_conversions > 0:
                msg += f"\n\nWARNING: {failed_conversions} WAV file(s) failed to convert.\nCheck FFmpeg settings."
            
            if failed_conversions > 0:
                 QMessageBox.warning(self, "Import Result", msg)
            else:
                 QMessageBox.information(self, "Import Result", msg)
        else:
            event.ignore()

    def _setup_top_controls(self, parent_layout) -> None:
        pass

    def _setup_connections(self) -> None:
        """Setup internal signal/slot connections"""
        # (Internal model signals, etc.)
        
        # T-55: Smart Proxy Connection
        self.filter_widget.multicheck_filter_changed.connect(self._on_multicheck_filter_changed)
        self.filter_widget.filter_mode_changed.connect(self.proxy_model.setFilterMatchMode)
        self.filter_widget.reset_filter.connect(self._on_filter_reset)
        
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(self._on_table_double_click)
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._show_column_context_menu)
    def load_library(self, refresh_filters=True):
        """Load library from database, preserving selection if possible."""
        # 1. Capture current selection (IDs)
        selected_ids = set()
        id_col = self.field_indices.get('file_id', -1)
        if id_col != -1:
            selection_model = self.table_view.selectionModel()
            for index in selection_model.selectedRows():
                source_index = self.proxy_model.mapToSource(index)
                item = self.library_model.item(source_index.row(), id_col)
                if item:
                    # Retrieve ID safely
                    raw_val = item.data(Qt.ItemDataRole.UserRole)
                    try:
                         val = str(int(float(raw_val))) if raw_val is not None else ""
                         if val: selected_ids.add(val)
                    except ValueError:
                        pass

        # 2. Load Data (Pure Loading, filtering happens in Proxy)
        headers, data = self.library_service.get_all_songs()
        self._populate_table(headers, data)

        if refresh_filters:
            self.filter_widget.populate()
        
        # 3. Apply Dirty Highlights
        if self._dirty_ids:
            self.update_dirty_rows(list(self._dirty_ids))

        # 4. Restore Selection
        if selected_ids and id_col != -1:
            from PyQt6.QtCore import QItemSelectionModel
            selection_model = self.table_view.selectionModel()
            selection_model.clearSelection() # Clean start
            
            # Iterate rows to find matches
            # Optimization: could build a map, but for <10k rows linear scan is usually acceptable for UI refresh
            for row in range(self.library_model.rowCount()):
                item = self.library_model.item(row, id_col)
                if not item: continue
                
                raw_val = item.data(Qt.ItemDataRole.UserRole)
                try:
                    # Same safe extraction
                    current_id = str(int(float(raw_val))) if raw_val is not None else ""
                except ValueError:
                    current_id = ""
                
                if current_id in selected_ids:
                    # Map to Proxy
                    source_idx = self.library_model.index(row, 0)
                    proxy_idx = self.proxy_model.mapFromSource(source_idx)
                    if proxy_idx.isValid():
                        selection_model.select(
                            proxy_idx, 
                            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
                        )

    def update_dirty_rows(self, dirty_ids: list):
        """Highlight rows that have unsaved changes in the side panel."""
        self._dirty_ids = set(str(id) for id in dirty_ids)
        # Notify the view to repaint
        self.table_view.viewport().update()

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
        
        # 2. Update Pill Labels
        shorthand = {
            "All": "ALL",
            "Music": "MUS",
            "Jingles": "JIN",
            "Commercials": "COM",
            "Speech": "SP",
            "Streams": "STR"
        }

        for i in range(len(self.type_tabs)):
            label, _ = self.type_tabs[i]
            count = counts[i]
            if i < len(self.category_glow_btns):
                glow_btn = self.category_glow_btns[i]
                short = shorthand.get(label, label)
                glow_btn.setText(f"{short} ({count})")

    def _populate_table(self, headers, data) -> None:
        """Populate the table with data, preserving layout state."""
        # 1. Suppress all auto-saves during the rebuild process
        self._suppress_layout_save = True
        
        try:
            # 2. Save current layout before clearing (if table is not empty)
            if self.library_model.columnCount() > 0:
                 self._save_column_layout()

            # 3. Rebuild the model
            self.library_model.clear()
            
            if not data:
                self.empty_label.show()
                self._update_empty_label_position()
            else:
                self.empty_label.hide()
            
            if headers:
                ui_headers = [f.ui_header for f in yellberus.FIELDS]
                self.library_model.setHorizontalHeaderLabels(ui_headers)
            
            show_incomplete = self._show_incomplete

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
                    
                    # Checkbox for IsActive
                    if col_idx == self.field_indices.get('is_active'):
                        item.setCheckable(True)
                        item.setEditable(False)
                        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                        
                        is_active_bool = bool(cell) if cell is not None else False
                        item.setCheckState(Qt.CheckState.Checked if is_active_bool else Qt.CheckState.Unchecked)
                        item.setText("")

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
                                item.setToolTip(f"{field_name} is incomplete")

                    items.append(item)
                
                self.library_model.appendRow(items)
                
            # 4. Restore layout (visibility, widths, order)
            # We only auto-resize if there's no layout saved yet
            layout = self.settings_manager.get_column_layout("default")
            if not layout:
                self.table_view.resizeColumnsToContents()

            if self._show_incomplete:
                self._apply_incomplete_view_columns()
            else:
                self._load_column_layout()

            self._update_tab_counts()

        finally:
            # 5. Re-enable layout saving
            self._suppress_layout_save = False

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into mm:ss"""
        try:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02d}:{s:02d}"
        except Exception:
            return "00:00"

    def _on_multicheck_filter_changed(self, active_filters: dict) -> None:
        """Handle multicheck filter state change from Sidebar."""
        self.proxy_model.setCheckFilters(active_filters, self.field_indices)
        
        # SYNC PERSPECTIVE: If anything under "Pending" or "Ready" is checked, 
        # we shift to Incomplete/Triage mode to show the required columns.
        status_filters = active_filters.get('is_done', set())
        needs_triage_view = False
        if False in status_filters or "READY" in status_filters:
            needs_triage_view = True
            
        if needs_triage_view != self._show_incomplete:
            self._show_incomplete = needs_triage_view
            if needs_triage_view:
                self._apply_incomplete_view_columns()
            else:
                self._load_column_layout()

    def _on_filter_reset(self) -> None:
        """Reset all filtering state."""
        self.load_library(refresh_filters=False) 
        self._on_multicheck_filter_changed({})

    def _import_file(self, file_path: str) -> bool:
        """Import a single file, return True on success"""
        try:
            # 1. Calculate Hash & Check Duplicates (Phase 2 Link)
            from ...utils.audio_hash import calculate_audio_hash
            from ...core import logger

            audio_hash = calculate_audio_hash(file_path)
            
            if self.duplicate_scanner.check_audio_duplicate(audio_hash):
                logger.info(f"Skipping import: Duplicate audio found for {file_path}")
                return False

            # 2. Extract Metadata & Check ISRC
            # Extract without ID first to check metadata
            temp_song = self.metadata_service.extract_from_mp3(file_path, source_id=0)
            
            if self.duplicate_scanner.check_isrc_duplicate(temp_song.isrc):
                logger.info(f"Skipping import: Duplicate ISRC found for {file_path}")
                return False

            # 3. Create Database Record
            file_id = self.library_service.add_file(file_path)
            if file_id:
                # Update ID and Hash on the song object
                temp_song.source_id = file_id
                temp_song.audio_hash = audio_hash
                
                # Save full metadata
                self.library_service.update_song(temp_song)
                return True
        except Exception as e:
            from ...core import logger
            logger.error(f"Error importing {file_path}: {e}", exc_info=True)
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

    def _on_pill_clicked(self, index: int) -> None:
        """Handle pill button click"""
        self._on_type_tab_changed(index)

    def _on_incomplete_toggled(self, checked: bool) -> None:
        """Handle incomplete filter toggle"""
        self._show_incomplete = checked
        self.load_library(refresh_filters=False)

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
        
        # 1. Global / Library Actions
        import_action = QAction("Import File(s)", self)
        import_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileIcon))
        import_action.triggered.connect(self._import_files)
        menu.addAction(import_action)

        scan_action = QAction("Scan Folder", self)
        scan_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_DirIcon))
        scan_action.triggered.connect(self._scan_folder)
        menu.addAction(scan_action)

        refresh_action = QAction("Refresh Library", self)
        refresh_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_action.triggered.connect(lambda: self.load_library())
        menu.addAction(refresh_action)

        menu.addSeparator()

        # 2. Playback / Primary Actions
        play_now_action = QAction("Play Now", self)
        play_now_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_MediaPlay))
        play_now_action.triggered.connect(self._on_play_selected_immediately)
        menu.addAction(play_now_action)

        add_to_playlist_action = QAction("Add to Playlist", self)
        add_to_playlist_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileIcon))
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

        # 2b. Converter Surgery (WAV -> MP3)
        if indexes and self.conversion_service:
            # Check if any WAVs are selected
            has_wav = False
            path_col = self.field_indices.get('path', -1)
            for idx in indexes:
                source_idx = self.proxy_model.mapToSource(idx)
                item = self.library_model.item(source_idx.row(), path_col)
                if item and item.text().lower().endswith(".wav"):
                    has_wav = True
                    break
            
            if has_wav:
                menu.addSeparator()
                convert_action = QAction("CONVERT TO MP3", self)
                # Amber themed icon or just standard
                convert_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_MediaPlay)) 
                convert_action.triggered.connect(self._on_convert_selected)
                
                if not self.settings_manager.get_conversion_enabled():
                    convert_action.setEnabled(False)
                    convert_action.setToolTip("Conversion disabled in settings.")
                
                menu.addAction(convert_action)
        
        menu.addSeparator()
        
        # 3. Destructive Actions
        rename_action = QAction("Rename File(s)", self)
        rename_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileIcon))
        
        # Safety Check: Rename requires DONE and CLEAN state
        can_rename = True
        rename_reason = ""
        
        if indexes:
            # 1. Check Completeness (Must be Done)
            if 'all_done' in locals() and not all_done:
                can_rename = False
                rename_reason = "Files must be marked DONE"
            
            # 2. Check Cleanliness (No Unsaved Changes)
            if can_rename:
                id_col = self.field_indices.get('file_id', -1)
                for idx in indexes:
                    source_idx = self.proxy_model.mapToSource(idx)
                    item = self.library_model.item(source_idx.row(), id_col)
                    if item:
                        raw_val = item.data(Qt.ItemDataRole.UserRole)
                        try:
                            sid = str(int(float(raw_val))) if raw_val is not None else ""
                        except ValueError:
                            sid = str(raw_val)
                        
                            if sid in self._dirty_ids:
                                can_rename = False
                                rename_reason = "Unsaved changes pending"
                                break

            # 3. Check Uniqueness (File System Conflict)
            if can_rename:
                # We need to check if target paths exist
                # This requires fetching the Song objects to perform precise calculation
                id_col = self.field_indices.get('file_id', -1)
                
                # Limit check to first 50 items to prevent UI freeze on massive selection
                # (Renaming 1000 items via context menu is an edge case we accept lag for, or we just check first few)
                check_limit = 50
                checked_count = 0
                
                for idx in indexes:
                    if checked_count >= check_limit:
                        break
                        
                    source_idx = self.proxy_model.mapToSource(idx)
                    item = self.library_model.item(source_idx.row(), id_col)
                    if item:
                         raw_val = item.data(Qt.ItemDataRole.UserRole)
                         try:
                            sid = int(float(raw_val)) if raw_val is not None else None
                            if sid is not None:
                                song = self.library_service.get_song_by_id(sid)
                                if song:
                                    target = self.renaming_service.calculate_target_path(song)
                                    # Skip if target is same as current (already renamed)
                                    # Normalize paths for comparison
                                    if song.path and os.path.normpath(song.path) == os.path.normpath(target):
                                        continue
                                        
                                    if self.renaming_service.check_conflict(target):
                                        can_rename = False
                                        rename_reason = f"Target exists: {os.path.basename(target)}"
                                        break
                                        
                            checked_count += 1
                         except Exception:
                            # If we can't fetch or calculate, assume safe? Or fail safe?
                            # Fail safe -> Don't rename what you can't verify
                            pass

        if not can_rename:
            rename_action.setEnabled(False)
            rename_action.setText(f"Rename File(s) ({rename_reason})")
            rename_action.setToolTip(f"Disabled: {rename_reason}")

        rename_action.triggered.connect(self.rename_selection)
        menu.addAction(rename_action)

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
            
            # T-17: Hard-ban columns that Yellberus says are not visible
            if logical_idx < len(yellberus.FIELDS):
                if not yellberus.FIELDS[logical_idx].visible:
                    continue
            else:
                # Any column beyond Yellberus fields (like ID/Path if added manually) should be hidden
                continue

            header_text = self.library_model.headerData(logical_idx, Qt.Orientation.Horizontal)
            action = QAction(str(header_text), self)
            action.setCheckable(True)
            action.setChecked(not self.table_view.isColumnHidden(logical_idx))
            # Use lambda to capture specific column index (safer than sender().data())
            action.toggled.connect(lambda checked, col=logical_idx: self._toggle_column_visibility(col, checked))
            menu.addAction(action)
        
        menu.addSeparator()
        reset_action = QAction("Reset to Default", self)
        reset_action.triggered.connect(self._reset_column_layout)
        menu.addAction(reset_action)
        
        menu.exec(header.mapToGlobal(position))

    def _toggle_column_visibility(self, column: int, checked: bool) -> None:
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
        
        # Reset visibility: respect Yellberus defaults
        for col in range(col_count):
            if col < len(yellberus.FIELDS):
                self.table_view.setColumnHidden(col, not yellberus.FIELDS[col].visible)
            else:
                self.table_view.setColumnHidden(col, True)
        
        # Clear saved layout
        self.settings_manager.remove_setting("library/layouts")

    def _on_column_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Save column layout when user drags a column."""
        if not self._suppress_layout_save:
            self._save_column_layout()

    def _on_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Save column layout when user resizes a column."""
        if not self._suppress_layout_save:
            self._save_column_layout()

    def _load_column_layout(self) -> None:
        """Load and apply column layout (order, visibility, widths) from settings."""
        layout = self.settings_manager.get_column_layout("default")
        if not layout:
            # Fallback: strictly enforce Yellberus baseline if no layout saved
            self._load_column_visibility_states()
            return
        
        header = self.table_view.horizontalHeader()
        order = layout.get("order", [])
        hidden_map = layout.get("hidden", {})
        widths_map = layout.get("widths", {})

        # 1. Restore order (Name-based)
        if order:
            for visual_idx, name in enumerate(order):
                if name in self.field_indices:
                    logical_idx = self.field_indices[name]
                    current_visual = header.visualIndex(logical_idx)
                    if current_visual != visual_idx:
                        header.moveSection(current_visual, visual_idx)

        # 2. Restore visibility and widths (Name-based)
        # We iterate through the actual fields defined in Yellberus
        for field_def in yellberus.FIELDS:
            if field_def.name not in self.field_indices:
                continue
                
            logical_idx = self.field_indices[field_def.name]
            
            # Hard-Ban Protection: Registry visibility takes absolute priority
            if not field_def.visible:
                self.table_view.setColumnHidden(logical_idx, True)
                continue

            # User Preference for visibility
            if field_def.name in hidden_map:
                user_hidden = hidden_map[field_def.name]
                self.table_view.setColumnHidden(logical_idx, user_hidden)
            else:
                # Default to visible if no preference stored
                self.table_view.setColumnHidden(logical_idx, False)

            # User Preference for widths
            if field_def.name in widths_map:
                width = widths_map[field_def.name]
                if width > 0:
                    self.table_view.setColumnWidth(logical_idx, width)
        
        # Hide any columns beyond Yellberus fields
        for col in range(len(yellberus.FIELDS), header.count()):
            self.table_view.setColumnHidden(col, True)

    def _save_column_layout(self) -> None:
        """Save column layout (order, visibility, widths) to settings."""
        # Do not save if we are in "Incomplete View" mode
        if self._show_incomplete:
            return
            
        header = self.table_view.horizontalHeader()
        col_count = header.count()
        if col_count == 0:
            return
            
        # 1. Save Order by Field Name
        order = []
        for visual_idx in range(col_count):
            logical_idx = header.logicalIndex(visual_idx)
            # Find the field name for this logical index
            for name, l_idx in self.field_indices.items():
                if l_idx == logical_idx:
                    order.append(name)
                    break
        
        # 2. Save Hidden Map and Widths Map by Field Name
        hidden_map = {}
        widths_map = {}
        
        for field_def in yellberus.FIELDS:
            if field_def.name in self.field_indices:
                logical_idx = self.field_indices[field_def.name]
                hidden_map[field_def.name] = self.table_view.isColumnHidden(logical_idx)
                widths_map[field_def.name] = self.table_view.columnWidth(logical_idx)

        self.settings_manager.set_column_layout(order, hidden_map, "default", widths=widths_map)

    # Legacy method for backward compatibility
    def _load_column_visibility_states(self) -> None:
        """Load column layout. Always respects Yellberus visibility as baseline."""
        # Step 1: Apply Yellberus visibility defaults FIRST
        for col in range(self.library_model.columnCount()):
            if col < len(yellberus.FIELDS):
                field_def = yellberus.FIELDS[col]
                # Hide columns that Yellberus marks as not visible
                self.table_view.setColumnHidden(col, not field_def.visible)
            else:
                self.table_view.setColumnHidden(col, True)
        
        # Step 2: Load saved layout (order + additional visibility preferences)
        layout = self.settings_manager.get_column_layout("default")
        if layout:
            self._load_column_layout()

    def _save_column_visibility_states(self) -> None:
        """Save column layout (wraps new method for compatibility)."""
        self._save_column_layout()

    # === Public helpers for shortcuts ===

    def mark_selection_done(self) -> None:
        """Mark the current selection as Done using existing validation.

        This reuses _toggle_status(True), which already enforces Yellberus
        completeness rules and shows a warning if some rows are incomplete.
        """
        self._toggle_status(True)

    def save_selected_songs(self) -> None:
        """Save selected songs: DB + ID3.

        For each selected row in the library table:
        - Resolve the song via LibraryService (by path).
        - Persist metadata to the database.
        - Persist metadata to ID3 via MetadataService.write_tags.

        Renaming/moves for Done items will be hooked in later via a
        dedicated RenamingService.
        """
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        saved = 0
        errors = []

        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            row = source_index.row()

            path_item = self.library_model.item(row, self.field_indices['path'])
            if not path_item:
                continue

            path = path_item.text()
            try:
                song = self.library_service.get_song_by_path(path)
                if not song:
                    continue

                # 1) Persist to DB
                self.library_service.update_song(song)

                # 2) Persist to ID3
                self.metadata_service.write_tags(song)

                # 3) TODO: When RenamingService exists, rename if song.is_done is True
                saved += 1
            except Exception as e:
                errors.append((path, str(e)))

        # Basic feedback via console for now; UI can be wired to status bar later.
        if saved == 0 and errors:
            print(f"[Save] Failed to save {len(errors)} song(s)")
        elif saved > 0:
            print(f"[Save] Saved {saved} song(s); {len(errors)} failures")

    def toggle_jingle_curtain(self):
        """Triggers the drop-down animation for the Jingle Bay."""
        if self.jingle_toggle.isChecked():
            self.jingle_anim.setStartValue(0)
            self.jingle_anim.setEndValue(260) # Full Bay height
        else:
            self.jingle_anim.setStartValue(self.jingle_curtain.height())
            self.jingle_anim.setEndValue(0)
            
        self.jingle_anim.start()

    # Mechanical Sidebar Swap Properties
    @pyqtProperty(int)
    def filterWidth(self):
        return self.filter_widget.width()

    @filterWidth.setter
    def filterWidth(self, width):
        self.filter_widget.setFixedWidth(width)

    @pyqtProperty(int)
    def totalSidebarWidth(self):
        return self.splitter.sizes()[0]

    @totalSidebarWidth.setter
    def totalSidebarWidth(self, width):
        # Update the splitter to track the handle during flight
        self.splitter.setSizes([width, self.width() - width])

    def toggle_history_drawer(self):
        """Synchronized Mechanical Swap: Handle pulls Log left, pushing Filter away."""
        if not hasattr(self, "_swap_group"):
            self._swap_group = QParallelAnimationGroup(self)
            
            # Anim A: History Log growth (drawerWidth is a property of HistoryDrawer)
            self._history_anim = QPropertyAnimation(self.history_drawer, b"drawerWidth")
            self._history_anim.setDuration(500)
            self._history_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
            
            # Anim B: Filter Tree shrink (filterWidth is a property of self)
            self._filter_anim = QPropertyAnimation(self, b"filterWidth")
            self._filter_anim.setDuration(500)
            self._filter_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
            
            # Anim C: Total Sidebar Width Adjustment (totalSidebarWidth is a property of self)
            self._splitter_anim = QPropertyAnimation(self, b"totalSidebarWidth")
            self._splitter_anim.setDuration(500)
            self._splitter_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
            
            self._swap_group.addAnimation(self._history_anim)
            self._swap_group.addAnimation(self._filter_anim)
            self._swap_group.addAnimation(self._splitter_anim)

        if self._history_open:
            # Back to Filters (Move handle RIGHT)
            self._history_anim.setStartValue(self._history_target_width)
            self._history_anim.setEndValue(0)
            self._filter_anim.setStartValue(0)
            self._filter_anim.setEndValue(self._filter_base_width)
            self._splitter_anim.setStartValue(self._history_target_width + self._rail_width)
            self._splitter_anim.setEndValue(self._filter_base_width + self._rail_width)
        else:
            # Pull Log Out (Move handle LEFT)
            self._history_anim.setStartValue(0)
            self._history_anim.setEndValue(self._history_target_width)
            self._filter_anim.setStartValue(self._filter_base_width)
            self._filter_anim.setEndValue(0)
            self._splitter_anim.setStartValue(self._filter_base_width + self._rail_width)
            self._splitter_anim.setEndValue(self._history_target_width + self._rail_width)
            
        self._swap_group.start()
        self._history_open = not self._history_open

    def _on_item_entered(self, index) -> None:
        """Track the hovered row for row-wide highlighting."""
        if index.isValid():
            self._hovered_row = index.row()
            self.table_view.viewport().update()

    def eventFilter(self, source, event) -> bool:
        """Clear hovered row when mouse leaves the table viewport."""
        try:
            from PyQt6.QtCore import QEvent
            if source is self.table_view.viewport() and event.type() == QEvent.Type.Leave:
                self._hovered_row = -1
                self.table_view.viewport().update()
        except RuntimeError:
            pass # Object already deleted during shutdown
        return super().eventFilter(source, event)

    def set_search_text(self, text: str) -> None:
        """Public slot for global search box."""
        self.proxy_model.setFilterFixedString(text)

    def focus_search(self) -> None:
        """Request focus for the global search box."""
        # We emit a signal so MainWindow can focus the correct widget
        self.focus_search_requested.emit()

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

    def _on_play_selected_immediately(self):
        """Play the first selected song now."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes: return
        
        idx = indexes[0]
        source_idx = self.proxy_model.mapToSource(idx)
        path_item = self.library_model.item(source_idx.row(), self.field_indices['path'])
        if path_item:
            self.play_immediately.emit(path_item.text())

    def _on_convert_selected(self) -> None:
        """Handle manual conversion of selected WAV files."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        wav_paths = []

        for idx in indexes:
            song = self._get_song_from_index(idx)
            if song and song.path and song.path.lower().endswith(".wav"):
                wav_paths.append(song)

        if not wav_paths:
            return

        reply = QMessageBox.question(
            self, "Confirm Conversion",
            f"Convert {len(wav_paths)} WAV file(s) to MP3?\n\nTags will be preserved and the WAVs will remain in place.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return

        success_count = 0
        for song in wav_paths:
            # 1. Convert
            mp3_path = self.conversion_service.convert_wav_to_mp3(song.path)
            if mp3_path:
                # 2. Sync Tags
                self.conversion_service.sync_tags(song, mp3_path)
                
                # 3. Import New MP3
                if self._import_file(mp3_path):
                    success_count += 1
        
        if success_count > 0:
            self.load_library()
            QMessageBox.information(self, "Conversion Finished", f"Successfully converted and imported {success_count} MP3(s).")
        else:
            QMessageBox.warning(self, "Conversion Failed", "Conversion failed. Check log or FFmpeg path in settings.")

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

    def rename_selection(self, refresh: bool = True) -> None:
        """
        Renames selected files based on metadata using RenamingService.
        Triggers strictly if gates (Done/Clean/Unique) are passed.
        """
        try:
            indexes = self.table_view.selectionModel().selectedRows()
            if not indexes:
                return
    
            # Double-check Gate 2 (Cleanliness) - Prevent Ctrl+R bypass
            if self._dirty_ids:
                 QMessageBox.warning(self, "Unsaved Changes", "Please save all changes before renaming.")
                 return
    
            confirm = QMessageBox.question(
                self, 
                "Rename Files", 
                f"Are you sure you want to rename {len(indexes)} file(s) and move them to their library folders?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

        
            if confirm != QMessageBox.StandardButton.Yes:
                return

            success_count = 0
            error_count = 0
            errors = []

            id_col = self.field_indices.get('file_id', -1)

            for idx in indexes:
                source_idx = self.proxy_model.mapToSource(idx)
                item = self.library_model.item(source_idx.row(), id_col)
                if not item: continue
                
                raw_val = item.data(Qt.ItemDataRole.UserRole)
                try:
                    sid = int(float(raw_val)) if raw_val is not None else None
                    if sid is not None:
                        song = self.library_service.get_song_by_id(sid)
                        if not song: continue

                        # Gate 1: Completeness
                        if not song.is_done: 
                            errors.append(f"{song.title}: Not marked as Done")
                            error_count += 1
                            continue

                        # Gate 3: Conflict (Calculated live)
                        target = self.renaming_service.calculate_target_path(song)
                        
                        # Optimization: If path matches target, skip
                        if song.path:
                            current = os.path.normcase(os.path.normpath(song.path))
                            new_target = os.path.normcase(os.path.normpath(target))
                            if current == new_target:
                                continue

                        if self.renaming_service.rename_song(song, target_path=target):
                            # Success! Persist new path to DB
                            self.library_service.update_song(song)
                            success_count += 1
                        else:
                            errors.append(f"{song.title}: Rename failed (Conflict or Access Denied)")
                            error_count += 1

                except Exception as e:
                    errors.append(f"Error processing item: {e}")
                    error_count += 1

            # Summary Report
            if error_count > 0:
                error_msg = "\n".join(errors[:10])
                if len(errors) > 10: error_msg += "\n...and more."
                QMessageBox.warning(self, "Rename Results", f"Renamed {success_count} files.\n\nErrors:\n{error_msg}")
            elif success_count > 0:
                 QMessageBox.information(self, "Success", f"Successfully renamed and moved {success_count} files.")
            
            # Refresh to show new paths
            if success_count > 0 and refresh:
                self.load_library()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Rename Error", f"Critical error during rename: {e}")


    def _get_incomplete_fields(self, row_data: list) -> set:
        """Identify which fields are incomplete based on Yellberus registry.
        Returns a set of field names that failed validation.
        """
        return yellberus.validate_row(row_data)

    def _get_song_from_index(self, index: QModelIndex) -> Optional[Song]:
        """Helper to fetch a Song object from a TableView index (proxy)."""
        if not index.isValid():
            return None
        source_idx = self.proxy_model.mapToSource(index)
        id_col = self.field_indices.get('file_id', -1)
        id_item = self.library_model.item(source_idx.row(), id_col)
        if not id_item:
            return None
            
        raw_val = id_item.data(Qt.ItemDataRole.UserRole)
        try:
            sid = int(float(raw_val)) if raw_val is not None else None
            if sid is not None:
                return self.library_service.get_song_by_id(sid)
        except (ValueError, TypeError):
            pass
        return None

