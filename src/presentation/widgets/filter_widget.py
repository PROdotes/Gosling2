from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

class FilterWidget(QWidget):
    """Widget for filtering the library (e.g. by Artist)"""
    
    # Signals
    filter_by_artist = pyqtSignal(str) # Emitted when an artist is selected
    reset_filter = pyqtSignal()        # Emitted when "Artists" root is clicked (show all)

    def __init__(self, library_service, parent=None):
        super().__init__(parent)
        self.library_service = library_service
        self._init_ui()
        self.populate()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree_model = QStandardItemModel()
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.clicked.connect(self._on_tree_clicked)
        
        layout.addWidget(self.tree_view)

    def populate(self):
        """Populate the filter tree with a hierarchy"""
        artist_list_tuple = self.library_service.get_contributors_by_role("Performer")
        artist_list = [artist_name for _, artist_name in artist_list_tuple]
        
        self.tree_model.clear()
        
        artist_root_item = QStandardItem("Artists")
        artist_root_item.setFlags(artist_root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        # Group by first letter
        first_chars = set()
        for artist_name in artist_list:
            if artist_name:
                first_chars.add(artist_name[0].upper())
        
        sorted_chars = sorted(first_chars)
        alpha_map = {}
        
        for char in sorted_chars:
            letter_item = QStandardItem(char)
            letter_item.setFlags(letter_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alpha_map[char] = letter_item
            artist_root_item.appendRow(letter_item)
            
        for artist_name in artist_list:
            if not artist_name:
                continue
            first_letter = artist_name[0].upper()
            parent_item = alpha_map.get(first_letter)
            if parent_item:
                artist_item = QStandardItem(artist_name)
                artist_item.setFlags(artist_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                artist_item.setData(artist_name, Qt.ItemDataRole.UserRole)
                parent_item.appendRow(artist_item)
                
        self.tree_model.appendRow(artist_root_item)
        self.tree_view.expand(artist_root_item.index())

    def _on_tree_clicked(self, index):
        """Handle click in the filter tree"""
        item = self.tree_model.itemFromIndex(index)
        artist_name = item.data(Qt.ItemDataRole.UserRole)
        
        if artist_name:
            self.filter_by_artist.emit(artist_name)
        elif item.text() == "Artists":
            self.reset_filter.emit()
