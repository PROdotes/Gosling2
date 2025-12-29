from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QMessageBox, QWidget, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton

class PublisherCreatorDialog(QDialog):
    """Tiny nested window for creating a new publisher."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Publisher")
        self.setFixedSize(350, 150)
        self.setObjectName("PublisherCreatorDialog")
        
        layout = QVBoxLayout(self)
        lbl = QLabel("PUBLISHER NAME")
        lbl.setObjectName("DialogFieldLabel")
        self.inp_name = GlowLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(self.inp_name)
        
        btns = QHBoxLayout()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = GlowButton("Create")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.accept)
        
        btns.addWidget(self.btn_cancel)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)
        self.inp_name.setFocus()

    def get_name(self):
        return self.inp_name.text().strip()

class PublisherPickerWidget(QWidget):
    """
    Searchable Picker Widget for Publishers.
    Integrated into the Album Manager Sidecar.
    """
    publisher_selected = pyqtSignal(int, str)

    def __init__(self, publisher_repository, parent=None):
        super().__init__(parent)
        self.pub_repo = publisher_repository
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Header
        lbl = QLabel("SELECT OR CREATE PUBLISHER")
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)

        # 2. Search Box
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Find Label...")
        self.txt_search.textChanged.connect(self._refresh_list)
        layout.addWidget(self.txt_search)

        # 3. List
        self.list_pubs = QListWidget()
        self.list_pubs.setObjectName("AlbumManagerList") 
        self.list_pubs.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_pubs)

        # 4. Quick Add (Inline)
        self.btn_quick_add = GlowButton("Add New Label (+)")
        self.btn_quick_add.setObjectName("Secondary")
        self.btn_quick_add.clicked.connect(self._on_quick_add)
        self.btn_quick_add.hide() # Only show if no matches
        layout.addWidget(self.btn_quick_add)

    def _refresh_list(self, query=""):
        self.list_pubs.clear()
        results = self.pub_repo.search(query)
        
        for pub in results:
            item = QListWidgetItem(pub.publisher_name)
            item.setData(Qt.ItemDataRole.UserRole, pub.publisher_id)
            self.list_pubs.addItem(item)
        
        # UI Polish: If no matches and we have a query, show Quick Add
        has_results = len(results) > 0
        self.btn_quick_add.setVisible(not has_results and len(query) > 1)
        if not has_results and len(query) > 1:
            self.btn_quick_add.setText(f"Add '{query}' (+)")

    def _on_item_clicked(self, item):
        self.publisher_selected.emit(
            item.data(Qt.ItemDataRole.UserRole),
            item.text()
        )

    def _on_quick_add(self):
        name = self.txt_search.text().strip()
        if not name: return
        
        pub, created = self.pub_repo.get_or_create(name)
        self._refresh_list()
        self.publisher_selected.emit(pub.publisher_id, pub.publisher_name)

class PublisherManagerDialog(QDialog):
    """Refactored legacy bridge (Optional)."""
    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 500)
        layout = QVBoxLayout(self)
        self.picker = PublisherPickerWidget(repo, self)
        layout.addWidget(self.picker)
        self.picker.publisher_selected.connect(lambda i, n: self.accept())
