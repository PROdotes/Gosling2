import os
import zipfile
import weakref
from typing import Optional, List, Set, Union
from ...data.models.song import Song
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableView, QLineEdit, QFileDialog, QMessageBox, QMenu, QStyle, QLabel,
    QCheckBox, QHeaderView, QButtonGroup, QSizePolicy, QStackedWidget, QFrame,
    QAbstractItemView, QTableWidgetItem, QPushButton, QProgressBar
)
import json
import subprocess
from ...resources import constants
from ...resources.constants import ROLE_HEALTH_STATUS
from .filter_widget import FilterWidget
from ...core import yellberus
from ...core.yellberus import HealthStatus
from ...core.vfs import VFS
from .library_delegate import WorkstationDelegate
from .history_drawer import HistoryDrawer
from .jingle_curtain import JingleCurtain
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, QEvent, QObject, QPropertyAnimation, QEasingCurve, pyqtProperty, QParallelAnimationGroup, QMimeData, QPoint, QModelIndex, QRect, QLine, QSize
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QAction, 
    QPainter, QColor, QPixmap, QIcon, QImage, QPen, QDrag, QFont
)
from .glow_factory import GlowButton
from ..workers.import_worker import ImportWorker
from ..dialogs.universal_import_dialog import UniversalImportDialog


class DropIndicatorHeaderView(QHeaderView):
    """
    Custom header that prevents moving the Status Deck (Col 0)
    and shows drop indicator for others.
    """
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._drop_indicator_pos = -1
        self._dragging = False
    
    def mousePressEvent(self, event):
        # Prevent dragging the Status Deck (Logical Index 0)
        idx = self.logicalIndexAt(event.pos())
        if idx != 0:
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
        """Calculate drop pos, ensuring we can't drop BEFORE the Status Deck."""
        if self.count() == 0:
            return -1

        # Determine safety barrier (Right edge of Status Deck)
        # We assume Logical 0 is the Status Deck.
        deck_idx = 0
        deck_width = self.sectionSize(deck_idx)
        deck_pos = self.sectionPosition(deck_idx) 
        barrier = deck_pos + deck_width

        # If cursor is within the deck,snap to barrier
        if x < barrier:
             return barrier

        for visual_idx in range(self.count()):
            logical_idx = self.logicalIndex(visual_idx)
            
            # Skip Status Deck itself
            if logical_idx == 0:
                continue

            section_pos = self.sectionPosition(logical_idx)
            section_size = self.sectionSize(logical_idx)
            section_mid = section_pos + section_size // 2
            
            if x < section_mid:
                # Ensure we don't return a position before the barrier
                return max(section_pos, barrier)
        
        # After last column
        last_logical = self.logicalIndex(self.count() - 1)
        return self.sectionPosition(last_logical) + self.sectionSize(last_logical)
    
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
    
    def __init__(self, contributor_service=None, parent=None):
        super().__init__(parent)
        self.contributor_service = contributor_service
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
        # Clear high-frequency caches
        if hasattr(self, '_filter_cache'):
            self._filter_cache = {}
        # T-83: Clear tag cache when filters change
        if hasattr(self, '_tag_cache'):
            self._tag_cache = {}

        # T-70 Identity Awareness: Expand performers to include aliases/related names
        processed_filters = filters.copy()
        if self.contributor_service and 'performers' in processed_filters:
            perf_set = processed_filters['performers']
            if perf_set:
                expanded = set()
                for name in perf_set:
                    # Resolve identity graph via Service
                    expanded.update(self.contributor_service.resolve_identity_graph(name))
                processed_filters['performers'] = expanded

        self._active_filters = processed_filters
        self._field_indices = field_indices
        self.invalidateFilter()

    def setFilterMatchMode(self, mode: str):
        """Set cross-category logic: 'AND' or 'OR'."""
        self._filter_match_mode = mode
        if hasattr(self, '_filter_cache'):
            self._filter_cache = {}
        self.invalidateFilter()

    def _check_value_match(self, model, row, parent, field_name, required_val) -> bool:
        """Surgical Match: Handles metadata, lists, procedural commands, and virtual filters."""
        
        # Virtual Decade Filter: Match year against decade range
        if field_name == 'decade':
            # required_val is like "1990s" - extract the decade start
            decade_str = str(required_val).replace('s', '')
            try:
                decade_start = int(decade_str)
                decade_end = decade_start + 9
            except (ValueError, TypeError):
                return False
            
            # Get the year from the row
            year_col = self._field_indices.get('recording_year', -1)
            if year_col < 0:
                return False
            
            year_val = model.data(model.index(row, year_col, parent), Qt.ItemDataRole.UserRole)
            try:
                year = int(float(year_val)) if year_val is not None else None
            except (ValueError, TypeError):
                return False
            
            if year is None:
                return False
            
            return decade_start <= year <= decade_end
        
        # T-83: Special handling for unified Tags filter
        if field_name == 'tags':
            # required_val is "Category:TagName" e.g. "Instrument:Guitar"
            if ':' not in str(required_val):
                return False
            
            category, tag_name = str(required_val).split(':', 1)
            
            # Get source_id from the row
            id_col = self._field_indices.get('file_id', -1)
            if id_col < 0:
                return False
            
            source_id_val = model.data(model.index(row, id_col, parent), Qt.ItemDataRole.UserRole)
            try:
                source_id = int(float(source_id_val)) if source_id_val is not None else None
            except (ValueError, TypeError):
                source_id = None
            
            if source_id is None:
                return False
            
            # Check tag cache first, build if needed
            if not hasattr(self, '_tag_cache'):
                self._tag_cache = {}
            
            cache_key = f"{source_id}"
            if cache_key not in self._tag_cache:
                # Query TagService for this song's tags
                source_widget = self.parent()
                if hasattr(source_widget, 'library_service'):
                    svc = source_widget.library_service
                    tags = svc.tag_service.get_tags_for_source(source_id)
                    self._tag_cache[cache_key] = {f"{t.category}:{t.tag_name}" for t in tags}
                else:
                    self._tag_cache[cache_key] = set()
            
            return required_val in self._tag_cache[cache_key]
        



        # 1. Identify Target Columns
        target_indices = []
        if field_name == 'all_contributors':
             # T-71 Virtual Filter: Scan all contributor columns
             contrib_fields = ['performers', 'composers', 'producers', 'lyricists', 'album_artist']
             for c_field in contrib_fields:
                 idx = self._field_indices.get(c_field, -1)
                 if idx >= 0: target_indices.append(idx)
        else:
            col_idx = self._field_indices.get(field_name, -1)
            if col_idx >= 0: target_indices.append(col_idx)
            
        if not target_indices: return False
        
        req_str = str(required_val).lower()
        
        # Prepare candidates for "All Contributors" (Group Logic)
        # If user selects "Paul McCartney", we also want to match rows with "The Beatles"
        match_candidates = {req_str}
        
        # T-70: Apply Identity Graph Expansion to Artist fields
        if field_name in ('all_contributors', 'unified_artist', 'performers'):
            if not hasattr(self, '_group_membership_cache'): self._group_membership_cache = {}
            if req_str not in self._group_membership_cache:
                source_widget = self.parent()
                if hasattr(source_widget, 'library_service'):
                    # Find all identities (Aliases + Groups)
                    # Use resolve_identity_graph to get aliases and group memberships via service
                    expanded = source_widget.library_service.contributor_service.resolve_identity_graph(str(required_val))
                    self._group_membership_cache[req_str] = {e.lower() for e in expanded}
                else:
                    self._group_membership_cache[req_str] = set()
            match_candidates.update(self._group_membership_cache[req_str])
        
        # 2. Iterate Target Columns (Unified Logic)
        for col_idx in target_indices:
            row_val = model.data(model.index(row, col_idx, parent), Qt.ItemDataRole.UserRole)

            # A. Special Case: Status Workflow (Done, Not Done, Pending, Incomplete)
            if field_name == 'is_done':
                 # T-89: "Done" is determined by the absence of ANY 'Status' category tags.
                 # 1. Identify if item carries any 'Status' tags
                 id_col = self._field_indices.get('file_id', -1)
                 source_id_val = model.data(model.index(row, id_col, parent), Qt.ItemDataRole.UserRole)
                 try: source_id = int(float(source_id_val)) if source_id_val is not None else None
                 except: source_id = None
                 
                 if source_id is None: return False
                 
                 # Check tag cache
                 if not hasattr(self, '_tag_cache'): self._tag_cache = {}
                 cache_key = f"{source_id}"
                 if cache_key not in self._tag_cache:
                     source_widget = self.parent() # The LibraryWidget
                     if source_widget and hasattr(source_widget, 'library_service'):
                         tags = source_widget.library_service.tag_service.get_tags_for_source(source_id)
                         self._tag_cache[cache_key] = {f"{t.category}:{t.tag_name}" for t in tags}
                     else:
                         self._tag_cache[cache_key] = set()
                 
                 # Logic change: Check for ANY tag in the Status category
                 has_status_tag = any(t.startswith("Status:") for t in self._tag_cache[cache_key])
                 
                 # 2. Match based on required_val
                 if required_val is True: # "Done"
                     return not has_status_tag
                 elif required_val is False: # "Not Done"
                     return has_status_tag
                 
                 # Check Row Completeness (only required fields)
                 completeness_row = []
                 for f in yellberus.FIELDS:
                     f_idx = self._field_indices.get(f.name, -1)
                     val = model.data(model.index(row, f_idx, parent), Qt.ItemDataRole.UserRole) if f_idx >= 0 else None
                     completeness_row.append(val)
                 
                 incomplete_fields = yellberus.check_completeness(completeness_row)
                 incomplete_count = len(incomplete_fields)
                 
                 # "Missing Data" - Shows songs missing REQUIRED data
                 if required_val == "INCOMPLETE":
                     return incomplete_count > 0
                 
                 # "Ready to Finalize" - Complete data AND has Unprocessed tag
                 if required_val == "READY":
                     return has_status_tag and incomplete_count == 0

            # B. Normalize Row Data (Handle Lists and CSV Strings)
            if isinstance(row_val, str) and ',' in row_val:
                row_items = [s.strip() for s in row_val.split(',')]
            elif isinstance(row_val, (list, tuple)):
                row_items = list(row_val)
            else:
                row_items = [row_val]

            # C. Match Against Items
            for item in row_items:
                # T-70: Strip Payload for matching
                if isinstance(item, str) and " ::: " in item:
                    item = item.split(" ::: ")[0].strip()
                
                # 1. Exact Match
                if item == required_val: return True
                
                # 2. Boolean Impedance Match
                if isinstance(required_val, bool):
                     bool_item = None
                     if isinstance(item, bool): bool_item = item
                     elif isinstance(item, (int, float)): bool_item = bool(item)
                     elif isinstance(item, str):
                         if item == "0" or item.lower() == "false": bool_item = False
                         elif item == "1" or item.lower() == "true": bool_item = True
                     if bool_item is not None and bool_item == required_val: return True

                # 3. String / Candidate Match (includes Group logic)
                item_lower = str(item).lower()
                if item_lower in match_candidates: return True
                
                # 4. Hierarchical Publisher Logic (T-70)
                if field_name == 'publisher':
                    if not hasattr(self, '_publisher_hierarchy_cache'): self._publisher_hierarchy_cache = {}
                    if not hasattr(self, '_filter_cache'): self._filter_cache = {}
                    
                    cache_key = f"pub_descendants_{required_val}"
                    if cache_key not in self._filter_cache:
                        source_widget = self.parent()
                        if hasattr(source_widget, 'library_service'):
                             svc = source_widget.library_service
                             pub, _ = svc.publisher_service.get_or_create(str(required_val))
                             # Usage: Delegated through Service Layer (Correct SOA)
                             descendants = svc.publisher_service.get_with_descendants(pub.publisher_id)
                             self._filter_cache[cache_key] = {d.publisher_name.lower() for d in descendants}
                         
                    valid_names = self._filter_cache.get(cache_key, set())
                    if str(item).lower() in valid_names:
                        return True

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
        
        # 5. Search Text (Extended to include tags)
        # Check if standard column search matches first
        standard_match = super().filterAcceptsRow(source_row, source_parent)
        if standard_match:
            return True
        
        # T-83: Also search tags if search text is set
        search_text = self.filterRegularExpression().pattern()
        if search_text:
            search_text_clean = search_text.strip().lower()
            
            # --- T-70: Semantic Identity Search ---
            # Resolve the search term to alias graph (e.g. "Farrokh" -> "Queen", "Freddie")
            if not hasattr(self, '_search_alias_cache'): self._search_alias_cache = {}
            
            # Key by the actual text
            if search_text_clean not in self._search_alias_cache:
                if self.contributor_service:
                    # Resolve aliases
                    resolved = self.contributor_service.resolve_identity_graph(search_text_clean)
                    self._search_alias_cache[search_text_clean] = {r.lower() for r in resolved}
                else:
                    self._search_alias_cache[search_text_clean] = {search_text_clean}
            
            search_aliases = self._search_alias_cache[search_text_clean]
            
            # Check Artist/Performer columns against these aliases
            # Columns to check for artist match:
            artist_cols = []
            for field in ['performers', 'album_artist', 'composers', 'producers']:
                idx = self._field_indices.get(field, -1)
                if idx >= 0: artist_cols.append(idx)
                
            for col in artist_cols:
                raw_val = model.data(model.index(source_row, col, source_parent), Qt.ItemDataRole.UserRole)
                if raw_val:
                    # Normalized check
                    val_str = str(raw_val).lower()
                    # Check if any alias is IN the value (fuzzy) or exact match
                    # Optimization: Iterate aliases
                    for alias in search_aliases:
                         if alias in val_str:
                             return True
            # -------------------------------------

            # Check tag cache
            if not hasattr(self, '_tag_cache'):
                self._tag_cache = {}

            # Get source_id for this row (Field name is 'file_id' in Yellberus)
            id_col = self._field_indices.get('file_id', -1)
            if id_col >= 0:
                source_id_val = model.data(model.index(source_row, id_col, source_parent), Qt.ItemDataRole.UserRole)
                try:
                    source_id = int(float(source_id_val)) if source_id_val is not None else None
                except (ValueError, TypeError):
                    source_id = None
                
                if source_id is not None:
                    
                    cache_key = f"{source_id}"
                    if cache_key not in self._tag_cache:
                        source_widget = self.parent()
                        if hasattr(source_widget, 'library_service'):
                            svc = source_widget.library_service
                            tags = svc.tag_service.get_tags_for_source(source_id)
                            # Use consistent format {Category}:{TagName}
                            self._tag_cache[cache_key] = {f"{t.category}:{t.tag_name}" for t in tags}
                        else:
                            self._tag_cache[cache_key] = set()
                    
                    # Check if any tag matches search text (check full Category:Tag for fuzzy matching)
                    search_lower = search_text.lower()
                    for tag_full in self._tag_cache[cache_key]:
                        if search_lower in tag_full.lower():
                            return True
                            
        # Smart Decade Search (T-83 follow-up)
        # If user searches "1990s" or "90s", we should match years in that range
        if search_text:
            import re
            # Match 1990s, 90s, 1990's, 90's (Require 's' to distinguish from specific year)
            match = re.match(r'^((?:19|20)?(\d)0)\'?[sS]$', search_text.strip())
            if match:
                # Group 1 is usually the full prefix part, e.g. 1990 or 90
                # But cleaner to parse the full match for logic
                try:
                    raw_str = search_text.strip().lower().replace("'", "").replace("s", "")
                    if len(raw_str) == 2:
                        raw_str = "19" + raw_str if int(raw_str) >= 30 else "20" + raw_str
                    
                    decade_start = int(raw_str)
                    # Round down to nearest 10 just in case
                    decade_start = (decade_start // 10) * 10
                    decade_end = decade_start + 9
                    
                    year_col = self._field_indices.get('recording_year', -1)
                    if year_col >= 0:
                        year_val = model.data(model.index(source_row, year_col, source_parent), Qt.ItemDataRole.UserRole)
                        if year_val:
                            try:
                                year = int(float(year_val))
                                if decade_start <= year <= decade_end:
                                    return True
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    pass
        
        return False


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

    def __init__(self, library_service, metadata_service, settings_manager, renaming_service, duplicate_scanner, conversion_service=None, import_service=None, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.settings_manager = settings_manager
        self.renaming_service = renaming_service
        self.duplicate_scanner = duplicate_scanner
        self.conversion_service = conversion_service
        self.import_service = import_service
        
        # Cache Yellberus Indices
        self.field_indices = {f.name: i for i, f in enumerate(yellberus.FIELDS)}
        
        # Flags
        self._show_incomplete = False
        
        # Flag to suppress auto-save during programmatic resize
        self._suppress_layout_save = False
        self._dirty_ids = set() # Store IDs with unsaved changes
        
        # Proxy for event filtering to avoid reference cycles
        self._event_filter_proxy = EventFilterProxy(self)
        
        # Threading (T-68)
        self._import_worker = None
        
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
            
        # State Tracking
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.load_library()

    def update_dirty_rows(self, ids: list):
        """Update the list of IDs with unsaved changes for visual feedback."""
        self._dirty_ids = set(ids)
        # Force the table to repaint to reflect new amber glows
        if hasattr(self, 'table_view') and self.table_view:
            self.table_view.viewport().update()

    def _handle_sort_request(self, logicalIndex):
        """Handle header clicks for tri-state sorting (Asc -> Desc -> Reset) using explicit state."""
        header = self.table_view.horizontalHeader()
        
        # 1. New Column or currently Reset -> Ascending
        if self._sort_column != logicalIndex:
            self._sort_column = logicalIndex
            self._sort_order = Qt.SortOrder.AscendingOrder
            
            header.setSortIndicatorShown(True)
            header.setSortIndicator(logicalIndex, self._sort_order)
            self.proxy_model.sort(logicalIndex, self._sort_order)
            
        # 2. Same Column: Asc -> Desc
        elif self._sort_order == Qt.SortOrder.AscendingOrder:
            self._sort_order = Qt.SortOrder.DescendingOrder
            
            header.setSortIndicator(logicalIndex, self._sort_order)
            self.proxy_model.sort(logicalIndex, self._sort_order)
            
        # 3. Same Column: Desc -> Reset
        else:
            self._sort_column = -1
            self._sort_order = Qt.SortOrder.AscendingOrder
            
            header.setSortIndicatorShown(False)
            self.proxy_model.sort(-1)


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
        self.filter_widget = FilterWidget(self.library_service, self.settings_manager)
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
        
        # T-68: LCD for background operations
        self.status_lcd = QFrame()
        self.status_lcd.setObjectName("ImportStatusLCD")
        self.status_lcd.setFixedHeight(30)
        lcd_layout = QHBoxLayout(self.status_lcd)
        lcd_layout.setContentsMargins(10, 0, 10, 0)
        lcd_layout.setSpacing(10)
        
        self.import_label = QLabel("READY")
        self.import_label.setObjectName("LCDLabel")
        self.import_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.import_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.import_progress = QProgressBar()
        self.import_progress.setObjectName("ImportProgressBar")
        self.import_progress.setTextVisible(False)
        self.import_progress.setFixedSize(100, 10)
        
        self.import_count_label = QLabel("0/0")
        self.import_count_label.setObjectName("LCDLabelCompact")
        self.import_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        lcd_layout.addWidget(self.import_label)
        lcd_layout.addWidget(self.import_progress)
        lcd_layout.addWidget(self.import_count_label)
        
        self.status_lcd.hide() # Initially hidden
        header_layout.addWidget(self.status_lcd)
        
        header_layout.addStretch()
        
        center_layout.addWidget(header_container)
        
        # Digital Filter Brain
        self.library_model = QStandardItemModel()
        self.proxy_model = LibraryFilterProxyModel(self.library_service.contributor_service, parent=self)
        self.proxy_model._field_indices = self.field_indices # Crucial for Tag Search
        self.proxy_model.setSourceModel(self.library_model)
        self.proxy_model.setFilterKeyColumn(-1) # Search all columns
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setSortRole(Qt.ItemDataRole.UserRole) # Use UserRole for sorting
        
        self.table_view = LibraryTable()
        self.table_view.setObjectName("LibraryTable")
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.setSortingEnabled(False) # Disable default 2-state sort (we want tri-state)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setMouseTracking(True) # Enable hover effects in delegate
        self.table_view.setShowGrid(False)  # Blade-Edge: No vertical lines
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        self.table_view.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        
        # T-92: Industrial Safety - Take the table off the TAB path to avoid accidental key triggers.
        # ClickFocus allows navigation if clicked, but Tab skips it.
        self.table_view.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
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
        
        # Tri-State Sorting (Asc -> Desc -> Reset)
        header.setSortIndicatorShown(True) # Force indicator since sortingEnabled is False
        header.sectionClicked.connect(self._handle_sort_request)
        # T-70: "Turbo Sort" - Treat double-click as second sort toggle
        header.sectionDoubleClicked.connect(self._handle_sort_request)
        
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
        center_layout.addWidget(self.table_view, 1) # Table takes priority space
        
        # --- JINGLE TRAY HANDLING (T-90) ---
        # The 'Handle' is an interactive border that slides the tray UP
        self.jingle_handle = QPushButton("▼  QUICK-FIRE JINGLE BAYS  ▼")
        self.jingle_handle.setObjectName("JingleHandle")
        self.jingle_handle.setCheckable(True)
        self.jingle_handle.setCursor(Qt.CursorShape.PointingHandCursor)
        center_layout.addWidget(self.jingle_handle)
        
        self.jingle_curtain = JingleCurtain() # Initially 0 height
        center_layout.addWidget(self.jingle_curtain)
        
        # Animation: Bottom-Up expansion
        self.jingle_anim = QPropertyAnimation(self.jingle_curtain, b"curtainHeight")
        self.jingle_anim.setDuration(400)
        self.jingle_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        
        self.jingle_handle.clicked.connect(self.toggle_jingle_curtain)
        
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
        duration_col = self.field_indices.get('duration', -1)
        
        for idx in indexes:
            source_row = self.proxy_model.mapToSource(idx).row()
            item_path = self.library_model.item(source_row, path_col)
            item_perf = self.library_model.item(source_row, performer_col)
            item_title = self.library_model.item(source_row, title_col)
            item_duration = self.library_model.item(source_row, duration_col)
            
            if not item_path: continue
            
            path = item_path.data(Qt.ItemDataRole.DisplayRole)
            performer = item_perf.data(Qt.ItemDataRole.DisplayRole) if item_perf else ""
            title = item_title.data(Qt.ItemDataRole.DisplayRole) if item_title else ""
            
            # Extract raw duration (seconds) if available, otherwise 0
            duration = 0
            if item_duration:
                # IMPORTANT: In _populate_table, we store the raw numeric duration 
                # in UserRole. Use that instead of EditRole.
                raw_dur = item_duration.data(Qt.ItemDataRole.UserRole)
                if isinstance(raw_dur, (int, float)):
                    duration = raw_dur

            if isinstance(performer, (list, tuple)):
                performer = ", ".join(performer)
            
            songs_to_drag.append({
                'path': path,
                'performer': performer or "Unknown Artist",
                'title': title or "Unknown Title",
                'duration': duration
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
        """Handle dropped files/folders by delegating to ImportService."""
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

        # 1. Harvest Paths
        initial_paths = []
        for url in mime.urls():
            if url.isLocalFile():
                initial_paths.append(os.path.abspath(url.toLocalFile()))
        
        if not initial_paths:
            event.ignore()
            return

        event.acceptProposedAction()
        
        # 2. Delegate Discovery (Folders -> Files, ZIPs -> Virtual Paths)
        # The ImportService handles recursion and VFS indexing
        final_list = self.import_service.collect_import_list(initial_paths)
        
        # 3. Start Background Import
        if final_list:
            self.import_files_list(final_list)

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
        
        # T-87: Force viewport update on selection change to purge render artifacts (Ghost Hover)
        self.table_view.selectionModel().selectionChanged.connect(lambda: self.table_view.viewport().update())
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self._show_column_context_menu)

    # Method moved to top of class (near init) for state tracking


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
        
        # T-89: Clear Proxy Cache to ensure tag filters are fresh
        if hasattr(self.proxy_model, '_tag_cache'):
            self.proxy_model._tag_cache.clear()
            
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
        """
        Show ONLY columns that are marked required=True in the schema.
        This focuses the user on missing data entry.
        """
        for col_idx in range(self.library_model.columnCount()):
            if col_idx < len(yellberus.FIELDS):
                field_def = yellberus.FIELDS[col_idx]
                
                # T-106: Show ONLY if required AND normally visible (don't show hidden IDs)
                should_show = field_def.required and field_def.visible
                
                self.table_view.setColumnHidden(col_idx, not should_show)
            else:
                self.table_view.setColumnHidden(col_idx, True)

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
                # T-92: Override Status Deck header for table view (keep it empty even if Yellberus has label)
                ui_headers = [("" if f.name == 'is_active' else f.ui_header) for f in yellberus.FIELDS]
                self.library_model.setHorizontalHeaderLabels(ui_headers)
            
            show_incomplete = self._show_incomplete

            for row_data in data:
                # Always calculate completeness for validation
                failing_fields = self._get_incomplete_fields(row_data)

                # Determine Health Status (T-104)
                # Priority: INVALID > UNPROCESSED > READY
                health = HealthStatus.READY
                if failing_fields:
                    health = HealthStatus.INVALID
                else:
                    # Check is_done column for "Unprocessed" state
                    try:
                        is_done_idx = self.field_indices['is_done']
                        is_done_val = row_data[is_done_idx]
                        is_done = bool(is_done_val) if is_done_val is not None else False
                        if not is_done:
                            health = HealthStatus.UNPROCESSED
                    except (KeyError, IndexError):
                        pass

                items = []
                for col_idx, cell in enumerate(row_data):
                    display_text = str(cell) if cell is not None else ""
                    
                    # T-91: Format multi-value fields (||| -> , ) for display
                    if '|||' in display_text:
                        display_text = display_text.replace('|||', ', ')
                        
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
                    
                    # Status Deck (IsActive) - No Checkbox, just Data
                    if col_idx == self.field_indices.get('is_active'):
                        item.setEditable(False)
                        item.setCheckable(False)
                        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                        
                        is_active_bool = bool(cell) if cell is not None else False
                        item.setData(is_active_bool, Qt.ItemDataRole.UserRole)
                        # Store Health Status for Delegate
                        item.setData(int(health), ROLE_HEALTH_STATUS)
                        
                        item.setToolTip("Status: ACTIVE" if is_active_bool else "Status: INACTIVE")
                        item.setText("")

                    if col_idx == self.field_indices['is_done']:
                        item.setCheckable(False) # Legacy Field: View Only
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

            # T-92 Status Deck Enforcement (Must be First & Fixed)
            h_header = self.table_view.horizontalHeader()
            
            # 1. Force Logical 0 to Visual 0
            current_visual = h_header.visualIndex(0)
            if current_visual != 0:
                 h_header.moveSection(current_visual, 0)
                
            # 2. Lock Width
            h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            h_header.resizeSection(0, 32) # Standard Icon Width

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
        if False in status_filters or "READY" in status_filters or "INCOMPLETE" in status_filters:
            needs_triage_view = True
            
        if needs_triage_view != self._show_incomplete:
            self._show_incomplete = needs_triage_view
            if needs_triage_view:
                self._apply_incomplete_view_columns()
            else:
                self._load_column_layout()

    def _on_filter_reset(self) -> None:
        """Reset all filtering state."""
        # Must refresh filters (populate) to restore expansion state and update counts
        self.load_library(refresh_filters=True) 
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

                # T-83: Primary Migration Point - Mark new imports as Unprocessed via Service
                if hasattr(self.library_service, 'tag_service'):
                    self.library_service.tag_service.add_tag_to_source(file_id, "Unprocessed", category="Status")
                
                return True
        except Exception as e:
            from ...core import logger
            logger.error(f"Error importing {file_path}: {e}", exc_info=True)
        return False

    def import_files_list(self, files: list) -> None:
        """Start a background worker to import a list of files."""
        if not files or not self.import_service:
            return

        # If a worker is already running, block new import
        if self._import_worker and self._import_worker.isRunning():
            QMessageBox.warning(self, "Terminal Busy", "A background operation is currently active.")
            return

        # Initialize LCD UI
        self.status_lcd.show()
        self.import_label.setText("INITIALIZING...")
        self.import_progress.setValue(0)
        self.import_count_label.setText(f"0/{len(files)}")

        # Create and start worker
        self._import_worker = ImportWorker(self.import_service, files)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.finished_batch.connect(self._on_import_finished)
        self._import_worker.error.connect(lambda err: QMessageBox.critical(self, "Critial Import Error", err))
        self._import_worker.start()

    def _on_import_progress(self, current: int, total: int, file_path: str, success: bool) -> None:
        """Update LCD UI with background progress."""
        file_name = os.path.basename(file_path)
        self.import_progress.setValue(int((current / total) * 100))
        self.import_count_label.setText(f"{current}/{total}")
        
        status_text = "IMPORTING: " + file_name
        if not success:
            status_text = "SKIPPED: " + file_name
        self.import_label.setText(status_text[:50])

    def _on_import_finished(self, success_count: int, error_count: int) -> None:
        """Cleanup LCD and refresh library after background import."""
        self.status_lcd.hide()
        self.load_library()
        
        if success_count > 0 or error_count > 0:
            msg = f"Import Finished.\nSuccess: {success_count}\nDuplicates Skipped: {error_count}"
            QMessageBox.information(self, "Operation Complete", msg)

    def _import_files(self) -> None:
        """
        Unified Smart Intake: Replaces the standard folder picker with a 
        Universal Import Dialog that handles both files and folders.
        """
        last_dir = self.settings_manager.get_last_import_directory() or ""
        
        dlg = UniversalImportDialog(start_dir=last_dir, parent=self)
        if dlg.exec():
            paths = dlg.get_selected()
            
            if paths:
                # Save the first dir as last_dir
                first_path = paths[0]
                if os.path.isfile(first_path):
                    self.settings_manager.set_last_import_directory(os.path.dirname(first_path))
                else:
                    self.settings_manager.set_last_import_directory(first_path)

                self.status_lcd.show()
                self.import_label.setText("DISCOVERING DATA...")
                
                # Discovery: Use ImportService to turn paths into a flat file list
                files = self.import_service.collect_import_list(paths)
                
                if not files:
                    self.status_lcd.hide()
                    QMessageBox.information(self, "No Results", "No valid audio files found in targeted sectors.")
                    return
                    
                self.import_files_list(files)

    def scan_directory(self, folder: str) -> None:
        """Discovery phase: Find files and then pass to worker."""
        if not self.import_service:
            return
            
        self.status_lcd.show()
        self.import_label.setText("DISCOVERING DATA...")
        
        # Discovery remains on UI thread as it's typically very fast (os.walk)
        files = self.import_service.scan_directory_recursive(folder)
        
        if not files:
            self.status_lcd.hide()
            QMessageBox.information(self, "No Results", "No valid audio files found in targeted sector.")
            return
            
        self.import_files_list(files)

    def _scan_folder(self) -> None:
        # Get last used directory or default to empty string
        last_dir = self.settings_manager.get_last_import_directory() or ""
        
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", last_dir)
        if not folder:
            return
        
        # Save the directory for next time
        self.settings_manager.set_last_import_directory(folder)
            
        self.scan_directory(folder)

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

    def _reveal_in_explorer(self, path: str) -> None:
        """Reveal the file in Windows Explorer. If path is virtual (in a ZIP), reveal the ZIP itself."""
        if not path:
            return
        if VFS.is_virtual(path):
            zip_path, _ = VFS.split_path(path)
            target = zip_path
        else:
            target = path
        if os.name != 'nt':
            return
        target = os.path.normpath(target)
        try:
            subprocess.Popen(f'explorer /select,"{target}"', shell=True)
        except Exception:
            pass

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

        # T-92: Active Toggle Action (Obvious Path)
        active_col = self.field_indices.get('is_active', -1)
        if active_col != -1 and indexes:
             actives = []
             for idx in indexes:
                 source_idx = self.proxy_model.mapToSource(idx)
                 item = self.library_model.item(source_idx.row(), active_col)
                 if item:
                    val = item.data(Qt.ItemDataRole.UserRole)
                    actives.append(str(val).lower() in ('true', '1'))
             
             all_active = all(actives)
             all_inactive = all(not a for a in actives)
             
             active_action = QAction(self)
             if all_active:
                 active_action.setText("Set Inactive")
                 active_action.triggered.connect(lambda: self._toggle_active(False))
             elif all_inactive:
                 active_action.setText("Set Active")
                 active_action.triggered.connect(lambda: self._toggle_active(True))
             else:
                 # Mixed: Default to Promoting to Active
                 active_action.setText("Set Active")
                 active_action.triggered.connect(lambda: self._toggle_active(True))
            
             menu.addAction(active_action)
        
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
        
        # 2c. Audit History (T-82)
        if len(indexes) == 1:
            menu.addSeparator()
            audit_action = QAction("Show Audit History", self)
            audit_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileDialogInfoView))
            audit_action.triggered.connect(self._show_selected_audit_history)
            menu.addAction(audit_action)
        
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

        # T-107: Filename Parser Action
        menu.addSeparator()
        parse_action = QAction("Parse Metadata from Filename...", self)
        parse_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        parse_action.triggered.connect(self._open_filename_parser)
        menu.addAction(parse_action)

        delete_action = QAction("Delete from Library", self)
        delete_action.setIcon(self._get_colored_icon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        if indexes:
            path_col = self.field_indices.get('path', -1)
            if path_col >= 0:
                source_idx = self.proxy_model.mapToSource(indexes[0])
                item_path = self.library_model.item(source_idx.row(), path_col)
                if item_path:
                    reveal_path = item_path.data(Qt.ItemDataRole.DisplayRole)
                    if reveal_path:
                        reveal_action = QAction("Reveal in Explorer", self)
                        reveal_action.triggered.connect(lambda: self._reveal_in_explorer(str(reveal_path)))
                        menu.addAction(reveal_action)

        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _show_column_context_menu(self, position) -> None:
        menu = QMenu(self)
        header = self.table_view.horizontalHeader()
        
        # Iterate by visual order so menu matches displayed column order
        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            
            # Prevent hiding the Status Deck (Column 0)
            # This column is mandatory for system feedback
            if logical_idx == 0:
                continue

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

                # 3) TODO: When RenamingService exists, rename if song is NOT unprocessed (tag absent)
                saved += 1
            except Exception as e:
                errors.append((path, str(e)))

        # Basic feedback via console for now; UI can be wired to status bar later.
        if saved == 0 and errors:
            print(f"[Save] Failed to save {len(errors)} song(s)")
        elif saved > 0:
            print(f"[Save] Saved {saved} song(s); {len(errors)} failures")

    def toggle_jingle_curtain(self):
        """Triggers the bottom-up expansion of the Jingle Tray."""
        is_opening = self.jingle_handle.isChecked()
        
        if is_opening:
            self.jingle_handle.setText("▲  QUICK-FIRE JINGLE BAYS  ▲")
            self.jingle_anim.setStartValue(0)
            self.jingle_anim.setEndValue(220) # Tactical Height
        else:
            self.jingle_handle.setText("▼  QUICK-FIRE JINGLE BAYS  ▼")
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
        
        # Also filter the filter tree
        if hasattr(self, 'filter_widget') and self.filter_widget:
            # We used to call self.filter_widget.populate() on empty text,
            # but that nukes the tree and visual check states.
            # Recursive filtering with empty text unhides everything efficiently.
            self._filter_tree_items(text)

    def _filter_tree_items(self, search_text: str) -> None:
        """Filter filter tree items based on search text. Hides leaf items that don't match,
        and hides parent/branch nodes if all their children are hidden."""
        if not hasattr(self.filter_widget, 'tree_model') or not self.filter_widget.tree_model:
            return
        
        search_lower = search_text.lower().strip()
        tree_view = self.filter_widget.tree_view
        model = self.filter_widget.tree_model
        
        # Recursively filter items
        for row in range(model.rowCount()):
            root_item = model.item(row)
            if root_item:
                self._filter_tree_item_recursive(root_item, search_lower, tree_view, model)
        
        # After filtering, restore expansion state for items that are now visible
        self.filter_widget.restore_expansion_state()
    
    def _filter_tree_item_recursive(self, item, search_text, tree_view, model) -> bool:
        """Recursively filter tree items. Returns True if item or any child matches."""
        item_text = item.text().lower()
        self_matches = not search_text or search_text in item_text
        
        has_visible_child = False
        for child_row in range(item.rowCount()):
            child_item = item.child(child_row)
            if child_item:
                if self._filter_tree_item_recursive(child_item, search_text, tree_view, model):
                    has_visible_child = True
        
        should_show = self_matches or has_visible_child
        
        # Apply visibility
        index = model.indexFromItem(item)
        if index.isValid():
            tree_view.setRowHidden(index.row(), index.parent(), not should_show)
            if should_show and search_text:
                tree_view.setExpanded(index, True)
        
        return should_show

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



    def _toggle_active(self, new_state: bool) -> None:
        """Bulk toggle 'Active' state for selected rows (T-92)."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return
            
        count = 0
        active_col = self.field_indices.get('is_active', -1)
        
        for index in indexes:
            # 1. Update DB
            song = self._get_song_from_index(index)
            if song:
                song.is_active = new_state
                self.library_service.update_song(song)
                count += 1
            
            # 2. Update UI Model (Instant Feedback)
            if active_col != -1:
                source_index = self.proxy_model.mapToSource(index)
                item = self.library_model.item(source_index.row(), active_col)
                if item:
                    item.setData(new_state, Qt.ItemDataRole.UserRole)
        
        if count > 0:
            self.table_view.viewport().update()

    def _delete_selected(self) -> None:
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete {len(indexes)} song(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Explicitly clear selection to notify listeners (SidePanel) that these items are gone.
            self.table_view.selectionModel().clearSelection()
            
            # Track containers for potential cleanup (VFS)
            potential_empty_zips = set()
            from ...core.vfs import VFS

            for index in indexes:
                source_index = self.proxy_model.mapToSource(index)
                file_id_item = self.library_model.item(source_index.row(), self.field_indices['file_id'])
                # Get path to check for virtual content
                path_item = self.library_model.item(source_index.row(), self.field_indices['path'])
                
                if file_id_item:
                    file_id = int(file_id_item.text())
                    
                    if path_item:
                        path_str = path_item.text()
                        if VFS.is_virtual(path_str):
                            zip_path, _ = VFS.split_path(path_str)
                            potential_empty_zips.add(zip_path)
                            
                    self.library_service.delete_song(file_id)
            
            self.load_library()
            
            # Post-delete: Check for empty containers (T-Cleanup)
            # Post-delete: Check for empty containers (T-Cleanup)
            self._check_and_cleanup_zips(potential_empty_zips)

    def _check_and_cleanup_zips(self, zip_paths: set) -> None:
        """Check provided ZIP paths for emptiness and prompt user to delete."""
        from ...core.vfs import VFS
        
        for zip_path in zip_paths:
            # 1. Check Library Usage (Are any songs still using this?)
            lib_count = self.library_service.get_virtual_member_count(zip_path)
            if lib_count > 0:
                continue
                
            # 2. Check Physical Content (Are there non-audio leftovers?)
            physical_count = VFS.get_physical_member_count(zip_path)
            zip_name = os.path.basename(zip_path)
            
            message = ""
            if physical_count == 0:
                message = f"The archive '{zip_name}' is empty and no longer used.\nDelete it from disk?"
            else:
                message = (f"You have extracted/removed all audio from '{zip_name}'.\n"
                           f"However, it still contains {physical_count} other file(s) (likely artwork/promo/nfo).\n\n"
                           f"Delete the ZIP file anyway?")
                           
            reply = QMessageBox.question(
                self, "Clean Up Archive?", message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(zip_path)
                except Exception as e:
                    QMessageBox.warning(self, "Delete Failed", f"Could not delete archive: {e}")

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

        wav_songs = []

        for idx in indexes:
            song = self._get_song_from_index(idx)
            if song and song.path and song.path.lower().endswith(".wav"):
                wav_songs.append(song)

        if not wav_songs:
            return

        reply = QMessageBox.question(
            self, "Confirm Conversion",
            f"Convert {len(wav_songs)} WAV file(s) to MP3?\n\n"
            "YES: Convert and REPLACE original entries\n"
            "NO: Convert but KEEP originals (Duplicates)\n"
            "CANCEL: Abort operation",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return

        should_replace = (reply == QMessageBox.StandardButton.Yes)

        success_count = 0
        from ...core.vfs import VFS

        for song in wav_songs:
            # 1. Convert
            mp3_path = self.conversion_service.convert_wav_to_mp3(song.path)
            if mp3_path:
                # 2. Sync Tags
                self.conversion_service.sync_tags(song, mp3_path)
                
                # 3. Import New MP3
                if self._import_file(mp3_path):
                    success_count += 1
                    
                    # 4. Handle Cleanup (Replace/Unstage)
                    if should_replace:
                        self.library_service.delete_song(song.id)
                        
                        if not VFS.is_virtual(song.path):
                             try: os.remove(song.path)
                             except: pass

        if success_count > 0:
            self.load_library()
            status = "converted and replaced" if should_replace else "converted"
            QMessageBox.information(self, "Conversion Finished", f"Successfully {status} {success_count} file(s).")
        else:
            QMessageBox.warning(self, "Conversion Failed", "Conversion failed. Check log or FFmpeg path in settings.")

    def _on_table_double_click(self, index) -> None:
        """Double click adds to playlist, but intercepts WAVs for conversion."""
        song = self._get_song_from_index(index)
        
        # Intercept WAV files
        if song and song.path and song.path.lower().endswith(".wav"):
            reply = QMessageBox.question(
                self, "WAV Detected",
                "This file is a WAV and cannot be streamed efficiently.\n\n"
                "Would you like to convert it to MP3 now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._on_convert_selected()
            return

        # Standard behavior
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
            dur_item = self.library_model.item(row, self.field_indices['duration'])
            
            if path_item:
                duration = 0
                if dur_item:
                    # IMPORTANT: In _populate_table, we store the raw numeric duration 
                    # in UserRole. Use that instead of EditRole.
                    raw_dur = dur_item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(raw_dur, (int, float)):
                        duration = raw_dur

                items.append({
                    "path": path_item.text(),
                    "performer": perf_item.text() if perf_item else "Unknown",
                    "title": title_item.text() if title_item else "Unknown",
                    "duration": duration
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

    def _show_selected_audit_history(self):
        """Open Audit History dialog for the selected song."""
        indexes = self.table_view.selectionModel().selectedRows()
        if len(indexes) != 1: return
        
        idx = indexes[0]
        source_idx = self.proxy_model.mapToSource(idx)
        id_col = self.field_indices.get('file_id', -1)
        item = self.library_model.item(source_idx.row(), id_col)
        if not item: return
        
        raw_val = item.data(Qt.ItemDataRole.UserRole)
        # Safe extraction
        try:
            source_id = int(float(raw_val)) if raw_val is not None else 0
        except:
            source_id = 0
            
        if source_id > 0:
            from ..dialogs.audit_history_dialog import AuditHistoryDialog
            from ...business.services.audit_service import AuditService
            
            # Use same DB path as library
            service = AuditService() 
            # Resolver: Map IDs to Names for display
            resolver = self.library_service.get_human_name
            
            dlg = AuditHistoryDialog(service, resolver=resolver, parent=self, initial_query=str(source_id))
            dlg.exec()

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
        # Gate 0: Check if auto-renaming is enabled in settings
        if not self.settings_manager.get_rename_enabled():
            return
        
        try:
            indexes = self.table_view.selectionModel().selectedRows()
            if not indexes:
                return
    
            # Double-check Gate 2 (Cleanliness) - Prevent Ctrl+R bypass
            if self._dirty_ids:
                 QMessageBox.warning(self, "Unsaved Changes", "Please save all changes before renaming.")
                 return
    
            # Pre-check: Determine if any files actually need renaming
            id_col = self.field_indices.get('file_id', -1)
            rename_needed = False
            
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
                        
                        # Check if song is processed (not unprocessed)
                        tag_service = self.library_service.tag_service if hasattr(self.library_service, 'tag_service') else None
                        is_unprocessed = tag_service.is_unprocessed(sid) if tag_service else True
                        if not is_unprocessed:
                            # Check if path differs from target
                            target = self.renaming_service.calculate_target_path(song)
                            if song.path:
                                if os.path.normcase(os.path.normpath(song.path)) != os.path.normcase(os.path.normpath(target)):
                                    rename_needed = True
                                    break
                except Exception:
                    pass
            
            # If no files need renaming, silently return
            if not rename_needed:
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
            
            # T-90: Track Zips for cleanup if files are extracted away
            potential_empty_zips = set()
            from ...core.vfs import VFS

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

                        # Gate 1: Status Check (The Tag is the Law) via Service
                        tag_service = self.library_service.tag_service if hasattr(self.library_service, 'tag_service') else None
                        is_unprocessed = tag_service.is_unprocessed(sid) if tag_service else True
                        if is_unprocessed: 
                            errors.append(f"{song.title}: Not marked as Ready (has Unprocessed tag)")
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
                            
                            # Capture old path for VFS Clean Check
                            old_path = song.path

                        if self.renaming_service.rename_song(song, target_path=target):
                            # Success! Persist new path to DB
                            self.library_service.update_song(song)
                            success_count += 1
                            
                            # T-90: Check if we moved OUT of a virtual file
                            if old_path and VFS.is_virtual(old_path) and not VFS.is_virtual(song.path):
                                zp, _ = VFS.split_path(old_path)
                                potential_empty_zips.add(zp)
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
                # Run Cleanup Check
                if potential_empty_zips:
                    self._check_and_cleanup_zips(potential_empty_zips)

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Rename Error", f"Critical error during rename: {e}")


    def _get_incomplete_fields(self, row_data: list) -> set:
        """Identify which fields are incomplete based on Yellberus registry.
        Returns a set of field names that failed validation.
        """
        return yellberus.check_completeness(row_data)

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

    def _open_filename_parser(self):
        """Open the Filename -> Metadata parser dialog (T-107)."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes: return
        
        selected_songs = []
        for index in indexes:
            song = self._get_song_from_index(index)
            if song and song.path:
                selected_songs.append(song)
        
        if not selected_songs: return
        
        from ..dialogs.filename_parser_dialog import FilenameParserDialog
        dlg = FilenameParserDialog(selected_songs, self)
        if dlg.exec():
            results = dlg.get_parsed_data()
            if results:
                self._apply_parsed_metadata(results)

    def _apply_parsed_metadata(self, results: dict):
        """
        Apply parsed metadata to songs and save.
        results: {source_id: {field: value}}
        """
        updated_count = 0
        
        for source_id, data in results.items():
            song = self.library_service.get_song_by_id(source_id)
            if not song: continue
            
            changed = False
            
            # 1. Update Song Object
            # Mapping from PatternEngine tokens to Song attributes
            
            # Title
            if "title" in data:
                if song.title != data["title"]:
                    song.title = data["title"]
                    changed = True
            
            # Artist (Unified / Performers)
            if "performers" in data:
                val = data["performers"]
                if not song.performers or (len(song.performers) == 1 and song.performers[0] != val):
                    song.performers = [val]
                    song.unified_artist = val
                    changed = True
            
            # Album
            if "album" in data:
                 val = data["album"]
                 # Just set the string/list if different?
                 current = song.album if isinstance(song.album, str) else (song.album[0] if song.album else "")
                 if current != val:
                     song.album = val 
                     changed = True

            # Year
            if "recording_year" in data:
                try:
                    y = int(data["recording_year"])
                    if song.recording_year != y:
                        song.recording_year = y
                        changed = True
                except: pass

            # BPM
            if "bpm" in data:
                try:
                    b = int(data["bpm"])
                    if song.bpm != b:
                        song.bpm = b
                        changed = True
                except: pass
                
            # Genre (Tag)
            if "genre" in data:
                genre = data["genre"]
                tag_str = f"Genre:{genre}"
                if tag_str not in song.tags:
                    song.tags.append(tag_str)
                    changed = True

            if changed:
                # 2. Persist to DB
                self.library_service.update_song(song)
                
                # 3. Persist to File (ID3) - Immediate write
                self.metadata_service.write_tags(song)
                updated_count += 1

        if updated_count > 0:
            self.load_library()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Metadata Parsed", f"Successfully updated {updated_count} songs from filenames.")
