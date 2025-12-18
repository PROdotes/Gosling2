from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

class FilterWidget(QWidget):
    """Widget for filtering the library (e.g. by Artist)"""
    
    # Signals
    filter_by_performer = pyqtSignal(str)
    filter_by_composer = pyqtSignal(str)
    filter_by_year = pyqtSignal(int)
    filter_by_status = pyqtSignal(bool)
    reset_filter = pyqtSignal()

    # STRICT SCHEMA: Explicitly list DB columns from 'Files' that are NOT used for filtering.
    # If a new column is added to 'Files', it must be either used (implemented) or added here.
    IGNORED_DB_COLUMNS = {
        "FileID",       # Internal ID, not useful for grouping
        "Path",         # Unique per file
        "Title",        # Unique per file (mostly)
        "Duration",     # Continuous value
        "TempoBPM",     # Continuous value (could be ranged later, but currently ignored)
        "ISRC",         # Metadata identifier, not for grouping
    }

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
        
        layout.addWidget(self.tree_view)

    def populate(self) -> None:
        """Populate the filter tree with a hierarchy"""
        self.tree_model.clear()
        
        # Standard Roles (Ordered for generic consistency)
        self._add_category_to_tree("Performer", "Performers")
        self._add_category_to_tree("Composer", "Composers")
        self._add_category_to_tree("Lyricist", "Lyricists")
        self._add_category_to_tree("Producer", "Producers")
        self._add_years_to_tree()
        self._add_status_to_tree()

    def _add_category_to_tree(self, role_name: str, display_name: str) -> None:
        """Helper to add a category (role) and its contributors to the tree"""
        # Fetch data
        contributors_tuple = self.library_service.get_contributors_by_role(role_name)
        # Extract names from tuples (id, name)
        names = [name for _, name in contributors_tuple]
        
        # Create Root Item
        root_item = QStandardItem(display_name)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        # Store role name in data for click handling
        root_item.setData(role_name, Qt.ItemDataRole.UserRole + 1) 
        
        # Group by first letter
        first_chars = set()
        for name in names:
            if name:
                first_chars.add(name[0].upper())
        
        sorted_chars = sorted(first_chars)
        alpha_map = {}
        
        # Create A-Z sub-nodes
        for char in sorted_chars:
            letter_item = QStandardItem(char)
            letter_item.setFlags(letter_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alpha_map[char] = letter_item
            root_item.appendRow(letter_item)
            
        # Add contributors to A-Z nodes
        for name in names:
            if not name:
                continue
            first_letter = name[0].upper()
            parent_item = alpha_map.get(first_letter)
            if parent_item:
                item = QStandardItem(name)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(name, Qt.ItemDataRole.UserRole)
                item.setData(role_name, Qt.ItemDataRole.UserRole + 1)
                parent_item.appendRow(item)
                
        self.tree_model.appendRow(root_item)
        self.tree_view.expand(root_item.index())

    def _add_years_to_tree(self) -> None:
        """Add years to the tree view."""
        years = self.library_service.get_all_years()
        if not years:
            return

        root_item = QStandardItem("Years")
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData("Year", Qt.ItemDataRole.UserRole + 1)
        
        # Group by Decade
        decades = {}
        for year in years:
            decade = (year // 10) * 10
            if decade not in decades:
                decades[decade] = []
            decades[decade].append(year)
            
        for decade in sorted(decades.keys(), reverse=True):
            decade_item = QStandardItem(f"{decade}s")
            decade_item.setFlags(decade_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Make decade click distinct if we want to filter by decade, for now just container
            
            for year in decades[decade]:
                year_item = QStandardItem(str(year))
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                year_item.setData(year, Qt.ItemDataRole.UserRole)
                year_item.setData("Year", Qt.ItemDataRole.UserRole + 1)
                decade_item.appendRow(year_item)
                
            root_item.appendRow(decade_item)
            
        self.tree_model.appendRow(root_item)

    def _add_status_to_tree(self) -> None:
        """Add Status (Ready/Not Ready) to tree"""
        root_item = QStandardItem("Workflow Status")
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData("Status", Qt.ItemDataRole.UserRole + 1)
        
        # Not Done
        not_done = QStandardItem("Not Done (Pending)")
        not_done.setFlags(not_done.flags() & ~Qt.ItemFlag.ItemIsEditable)
        not_done.setData(False, Qt.ItemDataRole.UserRole)
        not_done.setData("Status", Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(not_done)
        
        self.tree_model.appendRow(root_item)
        self.tree_view.expand(root_item.index())

    def _on_tree_clicked(self, index) -> None:
        """Handle click in the filter tree"""
        item = self.tree_model.itemFromIndex(index)
        name = item.data(Qt.ItemDataRole.UserRole)
        role = item.data(Qt.ItemDataRole.UserRole + 1)
        
        if name is not None and role:
            if role == "Performer":
                self.filter_by_performer.emit(name)
            elif role == "Composer":
                self.filter_by_composer.emit(name)
            elif role in ["Lyricist", "Producer"]:
                print(f"Filter requested for {role}: {name}")
            elif role == "Year":
                # Name is stored as int in UserRole for years
                self.filter_by_year.emit(name)
            elif role == "Status":
                # Name is boolean
                self.filter_by_status.emit(name)
        elif item.text() in ["Performers", "Composers", "Lyricists", "Producers", "Years", "Workflow Status"]:
             # Or if role is set on root items too
             self.reset_filter.emit()
