from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal
from src.core import yellberus

class FilterWidget(QWidget):
    """Widget for filtering the library using Yellberus registry."""
    
    # Signals - one generic signal with (field_name, value)
    filter_changed = pyqtSignal(str, object)  # (field_name, value)
    reset_filter = pyqtSignal()
    
    # Legacy signals for backward compatibility
    filter_by_performer = pyqtSignal(str)
    filter_by_unified_artist = pyqtSignal(str)  # T-17
    filter_by_composer = pyqtSignal(str)
    filter_by_year = pyqtSignal(int)
    filter_by_status = pyqtSignal(bool)

    def __init__(self, library_service, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self._init_ui()
        self.populate()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree_model = QStandardItemModel()
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.clicked.connect(self._on_tree_clicked)
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.doubleClicked.connect(self._on_tree_double_clicked)
        
        layout.addWidget(self.tree_view)

    def populate(self) -> None:
        """Populate the filter tree from Yellberus registry."""
        self.tree_model.clear()
        
        # Get filterable fields from Yellberus
        filterable_fields = yellberus.get_filterable_fields()
        
        # T-17 Refinement: Sort categories alphabetically by UI Header
        sorted_fields = sorted(filterable_fields, key=lambda f: f.ui_header.lower())
        
        for field in sorted_fields:
            if field.strategy in ("list", "decade_grouper", "first_letter_grouper"):
                self._add_list_filter(field)
            elif field.strategy == "boolean":
                self._add_boolean_filter(field)
            elif field.strategy == "range":
                self._add_range_filter(field)

    def _add_list_filter(self, field: yellberus.FieldDef) -> None:
        """Add a list-type filter (performers, years, etc.)."""
        # Get values based on field name
        values = self._get_field_values(field)
        if not values:
            return
        
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        
        # Check if field has a grouping strategy
        grouper_fn = yellberus.GROUPERS.get(field.strategy)
        if grouper_fn:
            self._add_grouped_items(root_item, field, values, grouper_fn)
        else:
            # Simple list (no grouping)
            for value in values:
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                root_item.appendRow(item)
        
        self.tree_model.appendRow(root_item)
        
    def _add_grouped_items(self, root_item, field, values, grouper_fn):
        """Add items grouped by grouper function (e.g., decade)."""
        groups = {}
        for value in values:
            group_name = grouper_fn(value)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(value)
        
        # Sort groups (e.g., "2020s", "2010s" - reverse for years)
        for group_name in sorted(groups.keys(), reverse=True):
            group_item = QStandardItem(group_name)
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            for value in sorted(groups[group_name], reverse=True):
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                group_item.appendRow(item)
            
            root_item.appendRow(group_item)

    def _add_alpha_grouped_items(self, root_item, field, values):
        """Add items grouped by first letter (A-Z)."""
        # Get unique first letters
        first_chars = set()
        for value in values:
            if value:
                first_chars.add(str(value)[0].upper())
        
        alpha_map = {}
        for char in sorted(first_chars):
            letter_item = QStandardItem(char)
            letter_item.setFlags(letter_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alpha_map[char] = letter_item
            root_item.appendRow(letter_item)
        
        for value in values:
            if not value:
                continue
            first_letter = str(value)[0].upper()
            parent_item = alpha_map.get(first_letter)
            if parent_item:
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                parent_item.appendRow(item)
        
        self.tree_view.expand(root_item.index())

    def _add_boolean_filter(self, field: yellberus.FieldDef) -> None:
        """Add a boolean filter (done/not done)."""
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        
        # Not Done option
        not_done = QStandardItem("Not Done (Pending)")
        not_done.setFlags(not_done.flags() & ~Qt.ItemFlag.ItemIsEditable)
        not_done.setData(False, Qt.ItemDataRole.UserRole)
        not_done.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(not_done)
        
        # Done option
        done = QStandardItem("Done (Complete)")
        done.setFlags(done.flags() & ~Qt.ItemFlag.ItemIsEditable)
        done.setData(True, Qt.ItemDataRole.UserRole)
        done.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(done)
        
        self.tree_model.appendRow(root_item)
        self.tree_view.expand(root_item.index())

    def _add_range_filter(self, field: yellberus.FieldDef) -> None:
        """Add a range filter (BPM, etc.) - placeholder for future."""
        # TODO: Implement range slider or input
        pass

    def _get_field_values(self, field: yellberus.FieldDef):
        """Get unique values for a field from the library service."""
        # Map field names to library service methods
        if field.name == "performers":
            return [name for _, name in self.library_service.get_contributors_by_role("Performer")]
        elif field.name == "composers":
            return [name for _, name in self.library_service.get_contributors_by_role("Composer")]
        elif field.name == "lyricists":
            return [name for _, name in self.library_service.get_contributors_by_role("Lyricist")]
        elif field.name == "producers":
            return [name for _, name in self.library_service.get_contributors_by_role("Producer")]
        elif field.name == "unified_artist":
            # T-17: Combine performers and groups into a unified artist list
            artists = set()
            # Get performers
            for _, name in self.library_service.get_contributors_by_role("Performer"):
                if name:
                    artists.add(name)
            # Get groups
            for group in self.library_service.get_all_groups():
                if group:
                    artists.add(group)
            return sorted(list(artists))
        elif field.name == "recording_year":
            return self.library_service.get_all_years()
        elif field.name == "type_id":
            # TODO: Get types from service
            return []
        else:
            return []

    def _on_tree_clicked(self, index) -> None:
        """Handle click in the filter tree."""
        item = self.tree_model.itemFromIndex(index)
        value = item.data(Qt.ItemDataRole.UserRole)
        field_name = item.data(Qt.ItemDataRole.UserRole + 1)
        
        if value is not None and field_name:
            # Emit generic signal
            self.filter_changed.emit(field_name, value)
            
            # Emit legacy signals for backward compatibility
            if field_name == "performers":
                self.filter_by_performer.emit(value)
            elif field_name == "unified_artist":
                # T-17: unified_artist uses unified filter
                self.filter_by_unified_artist.emit(value)
            elif field_name == "composers":
                self.filter_by_composer.emit(value)
            elif field_name == "recording_year":
                self.filter_by_year.emit(value)
            elif field_name == "is_done":
                self.filter_by_status.emit(value)
        # T-17 Refinement: Removed single-click reset on root nodes to prevent accidental resets
    
    def _on_tree_double_clicked(self, index) -> None:
        """Handle double-click in the filter tree."""
        if not index.isValid():
            return
            
        item = self.tree_model.itemFromIndex(index)
        if not item:
            return

        # 1. Root-only: Reset Filter
        if item.parent() is None:
            self.reset_filter.emit()
            
        # 2. Universal: Toggle expansion (Fixes T-17 expansion bug)
        # Works for both root categories and branches (future-proofing)
        if self.tree_view.isExpanded(index):
            self.tree_view.collapse(index)
        else:
            self.tree_view.expand(index)
