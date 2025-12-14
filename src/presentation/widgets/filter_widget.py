from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

class FilterWidget(QWidget):
    """Widget for filtering the library (e.g. by Artist)"""
    
    # Signals
    filter_by_performer = pyqtSignal(str)
    filter_by_composer = pyqtSignal(str)
    reset_filter = pyqtSignal()

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

    def _on_tree_clicked(self, index) -> None:
        """Handle click in the filter tree"""
        item = self.tree_model.itemFromIndex(index)
        name = item.data(Qt.ItemDataRole.UserRole)
        role = item.data(Qt.ItemDataRole.UserRole + 1)
        
        if name and role:
            if role == "Performer":
                self.filter_by_performer.emit(name)
            elif role == "Composer":
                self.filter_by_composer.emit(name)
            elif role in ["Lyricist", "Producer"]:
                print(f"Filter requested for {role}: {name}")
        elif item.text() in ["Performers", "Composers", "Lyricists", "Producers"]:
             # Or if role is set on root items too
             self.reset_filter.emit()
