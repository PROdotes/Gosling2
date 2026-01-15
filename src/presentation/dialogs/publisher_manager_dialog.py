from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QMessageBox, QWidget, QMenu, QComboBox,
    QCompleter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox
from ..widgets.entity_list_widget import EntityListWidget, LayoutMode
from src.core.entity_registry import EntityType
from src.core.context_adapters import PublisherChildAdapter






class PublisherDetailsDialog(QDialog):
    """
    T-63: Publisher Relationship Editor.
    Small modal to manage Parent/Child relationships.
    """
    def __init__(self, publisher, service, allow_remove_from_context=False, parent=None):
        super().__init__(parent)
        self.pub = publisher
        self.service = service
        self.allow_remove = allow_remove_from_context
        self.setWindowTitle(f"Manager: {publisher.publisher_name}")
        self.setFixedSize(360, 450)
        
        self.layout = QVBoxLayout(self)
        # Create a mock service provider for the EntityListWidget
        class _ServiceAdapter:
            def __init__(self, service):
                self.publisher_service = service
        self.service_provider = _ServiceAdapter(self.service)
        
        self._init_ui()
        self._refresh_data()
        
    def _init_ui(self):
        # 1. Identity
        lbl_name = QLabel("PUBLISHER NAME")
        lbl_name.setObjectName("FieldLabel")  # Same as side panel for tight proximity
        self.txt_name = GlowLineEdit()
        self.txt_name.setText(self.pub.publisher_name)
        self.txt_name.returnPressed.connect(self._save) # Snappy: Enter to Update
        self.layout.addWidget(lbl_name)
        self.layout.addWidget(self.txt_name)
        self.layout.addSpacing(16)  # Gap between field groups
        
        # 2. Parent Selector (horizontal row: combo expands, button stays right)
        lbl_parent = QLabel("PARENT LABEL (OWNER)")
        lbl_parent.setObjectName("FieldLabel")
        self.layout.addWidget(lbl_parent)
        
        h_parent = QHBoxLayout()
        h_parent.setSpacing(10)
        h_parent.setContentsMargins(0, 0, 0, 0)
        
        # Use GlowComboBox for focus glow effect without layout issues
        self.cmb_parent = GlowComboBox()
        self.cmb_parent.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_parent.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb_parent.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.cmb_parent.setObjectName("PublisherParentCombo")
        h_parent.addWidget(self.cmb_parent)
        
        
        self.layout.addLayout(h_parent)
        self.layout.addSpacing(15)
        
        # Separator Line
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        line.setFixedHeight(2)
        self.layout.addWidget(line)
        self.layout.addSpacing(20)
        
        # 3. Children List (Subsidiaries)
        lbl_children = QLabel("SUBSIDIARIES (CHILDREN)")
        lbl_children.setObjectName("FieldLabel")
        self.layout.addWidget(lbl_children)
        
        
        # Subsisiaries - NOW USES EntityListWidget!
        self.list_children = EntityListWidget(
            service_provider=self.service_provider,
            entity_type=EntityType.PUBLISHER,
            layout_mode=LayoutMode.CLOUD,  # Chips instead of list
            context_adapter=PublisherChildAdapter(
                self.pub, 
                self.service, 
                refresh_fn=self._refresh_data
            ),
            allow_add=True,
            allow_remove=True,
            allow_edit=True,
            add_tooltip="Link Subsidiary",
            parent=self
        )
        self.list_children.setObjectName("ArtistSubList") # Reuse style
        self.layout.addWidget(self.list_children)
        
        self.layout.addStretch(1) # Pin actions to bottom
        
        # 4. Actions (Horizontal Row)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setContentsMargins(10, 0, 10, 15)
        
        # Context Aware Remove Button
        if self.allow_remove:
            self.btn_delete = GlowButton("Remove")
            self.btn_delete.setObjectName("PublisherActionPill")
            self.btn_delete.setProperty("action_role", "destructive")
            self.btn_delete.setAutoDefault(False)
            self.btn_delete.clicked.connect(lambda: self.done(2)) 
            btn_box.addWidget(self.btn_delete)
        
        btn_cancel = GlowButton("Cancel")
        btn_cancel.setObjectName("PublisherActionPill")
        btn_cancel.setProperty("action_role", "secondary")
        btn_cancel.setAutoDefault(False)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = GlowButton("UPDATE")
        btn_save.setObjectName("PublisherActionPill")
        btn_save.setProperty("action_role", "primary")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save)
        self.layout.addLayout(btn_box)

    def _refresh_data(self):
        # Load all publishers for Parent Combo (except self)
        all_pubs = self.service.search("")
        self.cmb_parent.blockSignals(True)
        self.cmb_parent.clear()
        self.cmb_parent.addItem("(None)", None)
        
        for p in all_pubs:
            if p.publisher_id == self.pub.publisher_id: continue # Can't be own parent
            self.cmb_parent.addItem(p.publisher_name, p.publisher_id)
            
        self.cmb_parent.blockSignals(False)
            
        # Set current parent
        if self.pub.parent_publisher_id:
            idx = self.cmb_parent.findData(self.pub.parent_publisher_id)
            if idx >= 0: self.cmb_parent.setCurrentIndex(idx)
            
        # Subsidiaries - now uses EntityListWidget!
        self.list_children.refresh_from_adapter()


    def _save(self):
        new_name = self.txt_name.text().strip()
        if not new_name: return
        
        parent_id = self.cmb_parent.currentData()
        
        # Full circularity check (walks entire parent chain)
        if self.service.would_create_cycle(self.pub.publisher_id, parent_id):
            QMessageBox.warning(self, "Circular Link Detected", 
                               "Cannot set this parent - it would create a circular relationship.")
            return

        # Check for potential merge to set merged_target (helps router)
        collision_id = None
        with self.service._repo.get_connection() as conn:
             query = "SELECT PublisherID FROM Publishers WHERE trim(PublisherName) = ? COLLATE UTF8_NOCASE AND PublisherID != ?"
             cursor = conn.execute(query, (new_name, self.pub.publisher_id))
             row = cursor.fetchone()
             if row: collision_id = row[0]

        self.pub.publisher_name = new_name
        self.pub.parent_publisher_id = parent_id
        
        if self.service.update(self.pub):
            if collision_id:
                self.merged_target = collision_id
            self.done(3) # Signal 3: Data Changed (Forces precise re-sync)
        else:
            QMessageBox.warning(self, "Error", "Failed to update publisher.")



