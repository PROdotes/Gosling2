import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, 
    QLabel, QFrame, QHeaderView, QAbstractItemView,
    QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QDir, QSize
from PyQt6.QtGui import QColor, QFont, QFileSystemModel

from ..widgets.glow import GlowButton

class UniversalImportDialog(QDialog):
    """
    T-90: Universal Import Dialog
    A fully navigable 'Pro' File Browser for mass intake.
    """
    
    # Signals
    import_requested = pyqtSignal(list)

    def __init__(self, start_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UNIVERSAL INTAKE")
        self.setMinimumSize(950, 650)
        self.setObjectName("UniversalImportDialog")
        
        # Default to Home if no last_dir is provided
        self.start_dir = start_dir if (start_dir and os.path.exists(start_dir)) else QDir.homePath()
        
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HEADER (Mission Control)
        header = QFrame()
        header.setObjectName("DialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("UNIVERSAL INTAKE")
        lbl_title.setObjectName("DialogTitleLarge")
        lbl_hint = QLabel("MULTI-SELECT FILES OR FOLDERS FOR BATCH PROCESSING")
        lbl_hint.setObjectName("DialogHint")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_hint)
        header_layout.addLayout(title_box)
        
        header_layout.addStretch()
        
        # Path Bar / Navigation
        self.btn_up = GlowButton("↑ UP")
        self.btn_up.setFixedSize(60, 32)
        self.btn_up.clicked.connect(self._go_up)
        header_layout.addWidget(self.btn_up)
        
        main_layout.addWidget(header)

        # 2. BROWSER DECK (Sidebar + Tree)
        browser_deck = QHBoxLayout()
        browser_deck.setSpacing(0)

        # A. Navigation Rail (Sidebar)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("ImportSidebar")
        self.sidebar.setFixedWidth(140)
        self._populate_sidebar()
        self.sidebar.itemClicked.connect(self._on_sidebar_clicked)
        browser_deck.addWidget(self.sidebar)

        # B. The Main Tree
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath()) # Necessary for watcher
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.model.setNameFilters(["*.mp3", "*.wav", "*.flac", "*.m4a", "*.zip"])
        self.model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.start_dir))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setAnimated(True)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree.setObjectName("ImportTreeView")
        
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        browser_deck.addWidget(self.tree, 1)
        main_layout.addLayout(browser_deck)

        # 3. ACTION BAR (The Landing)
        footer = QFrame()
        footer.setObjectName("DialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 15, 20, 20)
        
        self.btn_cancel = GlowButton("CANCEL")
        self.btn_cancel.setFixedSize(110, 36)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_import = GlowButton("IMPORT SELECTION")
        self.btn_import.setObjectName("ActionPillPrimary")
        self.btn_import.setFixedSize(180, 36)
        self.btn_import.clicked.connect(self._on_import_clicked)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addWidget(self.btn_import)
        
        main_layout.addWidget(footer)

    def _populate_sidebar(self):
        """Add quick access bookmarks."""
        bookmarks = [
            ("Home", QDir.homePath()),
            ("Desktop", QDir(QDir.homePath()).filePath("Desktop")),
            ("Music", QDir(QDir.homePath()).filePath("Music")),
            ("Downloads", QDir(QDir.homePath()).filePath("Downloads")),
            ("Root (C:)", QDir.rootPath())
        ]
        for name, path in bookmarks:
            if os.path.exists(path):
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.sidebar.addItem(item)

    def _on_sidebar_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.tree.setRootIndex(self.model.index(path))

    def _go_up(self):
        curr_root = self.tree.rootIndex()
        parent_index = curr_root.parent()
        if parent_index.isValid():
            self.tree.setRootIndex(parent_index)

    def _on_import_clicked(self):
        indexes = self.tree.selectionModel().selectedRows()
        paths = [self.model.filePath(idx) for idx in indexes]
        
        if paths:
            self.import_requested.emit(paths)
            self.accept()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Empty Selection", "Target selection is empty. Select files or folders to proceed.")

    @staticmethod
    def get_import_paths(start_dir=None, parent=None):
        dlg = UniversalImportDialog(start_dir, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pass
        return []
