import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, 
    QLabel, QFrame, QHeaderView, QAbstractItemView,
    QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QDir, QSize
from PyQt6.QtGui import QColor, QFont, QFileSystemModel

from ..widgets.glow_factory import GlowButton

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
        self.selected_paths = []
        
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
        self.model.setNameFilters(["*.mp3", "*.wav", "*.zip"])
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
        
        # Connect selection change for inspector
        self.tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        browser_deck.addWidget(self.tree, 1)

        # C. ZIP INSPECTOR (The Right Deck)
        self.inspector_pane = QFrame()
        self.inspector_pane.setObjectName("ImportInspector")
        self.inspector_pane.setFixedWidth(280)
        self.inspector_pane.hide() # Hidden until a ZIP is clicked
        
        inspector_layout = QVBoxLayout(self.inspector_pane)
        inspector_layout.setContentsMargins(15, 15, 15, 15)
        inspector_layout.setSpacing(10)
        
        # Header
        lbl_insp_title = QLabel("ZIP INSPECTOR")
        lbl_insp_title.setObjectName("DialogFieldLabel")
        inspector_layout.addWidget(lbl_insp_title)
        
        # Summary Area
        self.lbl_zip_name = QLabel("No ZIP Selected")
        self.lbl_zip_name.setWordWrap(True)
        self.lbl_zip_name.setStyleSheet("font-weight: bold; color: #CCC;")
        inspector_layout.addWidget(self.lbl_zip_name)
        
        self.lbl_zip_stats = QLabel("")
        self.lbl_zip_stats.setStyleSheet("color: #888; font-size: 11px;")
        inspector_layout.addWidget(self.lbl_zip_stats)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #333;")
        inspector_layout.addWidget(line)
        
        # Content List
        label_contents = QLabel("CONTAINS:")
        label_contents.setStyleSheet("color: #666; font-size: 10px; font-weight: bold;")
        inspector_layout.addWidget(label_contents)
        
        self.list_contents = QListWidget()
        self.list_contents.setObjectName("InspectorContentList")
        self.list_contents.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        inspector_layout.addWidget(self.list_contents, 1)
        
        browser_deck.addWidget(self.inspector_pane)
        
        main_layout.addLayout(browser_deck)

        # 3. ACTION BAR (The Landing)
        footer = QFrame()
        footer.setObjectName("DialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 15, 20, 20)
        
        self.btn_cancel = GlowButton("CANCEL")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.setFixedSize(110, 36)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_import = GlowButton("IMPORT SELECTION")
        self.btn_import.setObjectName("ActionPill")
        self.btn_import.setProperty("action_role", "primary")
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
            self.selected_paths = paths
            self.import_requested.emit(paths)
            self.accept()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Empty Selection", "Target selection is empty. Select files or folders to proceed.")

    def _on_selection_changed(self, selected, deselected):
        """Handle selection change in the tree."""
        indexes = self.tree.selectionModel().selectedRows()
        
        # We only inspect if exactly ONE item is selected and it's a ZIP
        if len(indexes) == 1:
            path = self.model.filePath(indexes[0])
            if path.lower().endswith(".zip") and os.path.isfile(path):
                self._peek_into_zip(path)
                return
        
        # Otherwise, hide inspector
        self.inspector_pane.hide()

    def _peek_into_zip(self, path):
        """Read ZIP headers and show contents preview."""
        import zipfile
        self.list_contents.clear()
        self.lbl_zip_name.setText(os.path.basename(path))
        
        try:
            if not zipfile.is_zipfile(path):
                self.lbl_zip_stats.setText("INVALID ZIP FILE")
                self.inspector_pane.show()
                return
                
            with zipfile.ZipFile(path, 'r') as zr:
                namelist = zr.namelist()
                
                audio_exts = ('.mp3', '.wav')
                audio_count = sum(1 for f in namelist if f.lower().endswith(audio_exts))
                
                size_mb = os.path.getsize(path) / (1024 * 1024)
                self.lbl_zip_stats.setText(f"{len(namelist)} FILES | {audio_count} TRACKS | {size_mb:.1f} MB")
                
                # Show first 50 items to keep UI snappy
                for name in namelist[:50]:
                    icon = "📁" if name.endswith("/") else "📄"
                    if name.lower().endswith(audio_exts): icon = "🎵"
                    
                    item = QListWidgetItem(f"{icon} {name}")
                    self.list_contents.addItem(item)
                
                if len(namelist) > 50:
                    self.list_contents.addItem(QListWidgetItem(f"... and {len(namelist)-50} more"))
            
            self.inspector_pane.show()
            
        except Exception as e:
            from ...core import logger
            logger.error(f"Failed to peek into zip {path}: {e}")
            self.lbl_zip_stats.setText("ERROR READING ZIP")
            self.inspector_pane.show()

    def get_selected(self):
        """Return the list of paths selected by the user."""
        return self.selected_paths

    @staticmethod
    def get_import_paths(start_dir=None, parent=None):
        dlg = UniversalImportDialog(start_dir, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_selected()
        return []
