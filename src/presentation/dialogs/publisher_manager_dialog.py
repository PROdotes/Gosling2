from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QMessageBox, QWidget, QMenu, QComboBox, QInputDialog,
    QCompleter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox

class PublisherCreatorDialog(QDialog):
    """Tiny nested window for creating/naming a publisher."""
    def __init__(self, initial_name="", title="New Publisher", button_text="Create", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        self.setObjectName("PublisherCreatorDialog")
        
        layout = QVBoxLayout(self)
        lbl = QLabel("PUBLISHER NAME")
        lbl.setObjectName("DialogFieldLabel")
        self.inp_name = GlowLineEdit()
        self.inp_name.setText(initial_name)
        layout.addWidget(lbl)
        layout.addWidget(self.inp_name)
        
        btns = QHBoxLayout()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = GlowButton(button_text)
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.accept)
        
        btns.addWidget(self.btn_cancel)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)
        self.inp_name.setFocus()
        if initial_name:
            self.inp_name.edit.selectAll()

    def get_name(self):
        return self.inp_name.text().strip()


class PublisherPickerDialog(QDialog):
    """
    Searchable combo dialog for selecting an existing publisher.
    Now supports Smart Creation (matching Artist workflow).
    """
    def __init__(self, repo, exclude_ids=None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.exclude_ids = exclude_ids or set()
        self.selected_pub = None
        
        self.setWindowTitle("Select or Add Publisher")
        self.setFixedSize(380, 180)
        self.setObjectName("PublisherPickerDialog")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        lbl = QLabel("SELECT OR CREATE PUBLISHER")
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)
        
        # Searchable combo (same as parent selector)
        h_row = QHBoxLayout()
        h_row.setSpacing(10)
        
        self.cmb = GlowComboBox()
        self.cmb.setEditable(True) # ENABLE EDITING
        self.cmb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.cmb.setObjectName("PublisherParentCombo")
        h_row.addWidget(self.cmb)
        
        layout.addLayout(h_row)
        layout.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        self.btn_select = GlowButton("Select / Create")
        self.btn_select.setObjectName("Primary")
        self.btn_select.btn.setDefault(True) # Make Enter trigger this button
        self.btn_select.clicked.connect(self._on_select)
        
        # Connect Enter key in the editable line edit to submission
        self.cmb.lineEdit().returnPressed.connect(self._on_select)
        btns.addWidget(self.btn_select)
        btns.addStretch()
        
        layout.addLayout(btns)
        
        self._populate()
        self.cmb.setFocus()
    
    def _populate(self):
        self.cmb.blockSignals(True)
        self.cmb.clear()
        all_pubs = self.repo.search("")
        for p in all_pubs:
            if p.publisher_id not in self.exclude_ids:
                self.cmb.addItem(p.publisher_name, p.publisher_id)
        
        self.cmb.setCurrentIndex(-1)
        self.cmb.blockSignals(False)
    
    def _on_select(self):
        pub_id = self.cmb.currentData()
        current_text = self.cmb.currentText().strip()

        if not current_text:
            return

        # Case A: Selection from list
        if pub_id:
            self.selected_pub = self.repo.get_by_id(pub_id)
            self.accept()
            return

        # Case B: Direct typed but matches existing?
        existing = self.repo.find_by_name(current_text)
        if existing:
            self.selected_pub = existing
            self.accept()
            return

        # Case C: Fast Create
        reply = QMessageBox.question(
            self,
            "Create Publisher?",
            f"Publisher '{current_text}' not found.\n\nCreate new record?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                new_pub, _ = self.repo.get_or_create(current_text)
                self.selected_pub = new_pub
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create publisher: {e}")

    def get_selected(self):
        return self.selected_pub

class PublisherDetailsDialog(QDialog):
    """
    T-63: Publisher Relationship Editor.
    Small modal to manage Parent/Child relationships.
    """
    def __init__(self, publisher, repo, parent=None):
        super().__init__(parent)
        self.pub = publisher
        self.repo = repo
        self.setWindowTitle(f"Manager: {publisher.publisher_name}")
        self.setFixedSize(360, 450)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)  # Zero spacing - manual control like side panel
        
        self._init_ui()
        self._refresh_data()
        
    def _init_ui(self):
        # 1. Identity
        lbl_name = QLabel("PUBLISHER NAME")
        lbl_name.setObjectName("FieldLabel")  # Same as side panel for tight proximity
        self.txt_name = GlowLineEdit()
        self.txt_name.setText(self.pub.publisher_name)
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
        
        # Use GlowButton for consistent workstation look
        self.btn_new_parent = GlowButton("NEW")
        self.btn_new_parent.setFixedSize(60, 26)
        self.btn_new_parent.setToolTip("Create New Parent")
        self.btn_new_parent.clicked.connect(self._create_new_parent)
        h_parent.addWidget(self.btn_new_parent)
        
        self.layout.addLayout(h_parent)
        self.layout.addSpacing(15)
        
        # Separator Line
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        line.setFixedHeight(2)
        self.layout.addWidget(line)
        self.layout.addSpacing(20)
        
        # 3. Children List (Subsidiaries) with Add button
        h_children_header = QHBoxLayout()
        h_children_header.setContentsMargins(0, 0, 0, 0)
        
        lbl_children = QLabel("SUBSIDIARIES (CHILDREN)")
        lbl_children.setObjectName("FieldLabel")
        h_children_header.addWidget(lbl_children)
        h_children_header.addStretch()
        
        btn_add_child = GlowButton("ADD")
        btn_add_child.setFixedSize(60, 26)
        btn_add_child.setToolTip("Link existing publisher as child")
        btn_add_child.clicked.connect(self._add_child)
        h_children_header.addWidget(btn_add_child)
        
        self.layout.addLayout(h_children_header)
        
        self.list_children = QListWidget()
        self.list_children.setObjectName("AlbumManagerList") # Reuse style
        self.list_children.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_children.customContextMenuRequested.connect(self._show_child_context_menu)
        self.list_children.itemDoubleClicked.connect(self._on_child_double_clicked)
        self.layout.addWidget(self.list_children)
        
        # 4. Actions (centered)
        btn_box = QHBoxLayout()
        btn_save = GlowButton("Save Changes")
        btn_save.setObjectName("Primary")
        btn_save.clicked.connect(self._save)
        
        btn_cancel = GlowButton("Close")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        btn_box.addStretch()  # Center the buttons
        self.layout.addLayout(btn_box)

    def _refresh_data(self):
        # Load all publishers for Parent Combo (except self)
        all_pubs = self.repo.search("")
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
            
        # Load Children
        self.list_children.clear()
        for p in all_pubs:
            if p.parent_publisher_id == self.pub.publisher_id:
                item = QListWidgetItem(p.publisher_name)
                item.setText(f"↳ {p.publisher_name}")
                item.setData(Qt.ItemDataRole.UserRole, p.publisher_id)
                self.list_children.addItem(item)

    def _create_new_parent(self):
        diag = PublisherCreatorDialog(parent=self)
        if diag.exec():
            name = diag.get_name()
            if name:
                new_pub, created = self.repo.get_or_create(name)
                self._refresh_data()
                # Auto-select the newly created parent
                idx = self.cmb_parent.findData(new_pub.publisher_id)
                if idx >= 0: 
                    self.cmb_parent.setCurrentIndex(idx)
                    self.cmb_parent.setFocus() # Focus on the selected parent

    def _on_child_double_clicked(self, item):
        """Rename the double-clicked child."""
        child_id = item.data(Qt.ItemDataRole.UserRole)
        child_pub = self.repo.get_by_id(child_id)
        if not child_pub: return
        
        diag = PublisherCreatorDialog(
            initial_name=child_pub.publisher_name,
            title=f"Rename: {child_pub.publisher_name}",
            button_text="Rename",
            parent=self
        )
        if diag.exec():
            new_name = diag.get_name()
            if new_name and new_name != child_pub.publisher_name:
                child_pub.publisher_name = new_name
                if self.repo.update(child_pub):
                    self._refresh_data()

    def _show_child_context_menu(self, pos):
        item = self.list_children.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        
        rename_act = QAction("Rename", self)
        rename_act.triggered.connect(lambda: self._on_child_double_clicked(item))
        menu.addAction(rename_act)
        
        remove_act = QAction("Remove Child Link", self)
        remove_act.triggered.connect(lambda: self._remove_child_link(item))
        menu.addAction(remove_act)
        
        menu.exec(self.list_children.mapToGlobal(pos))

    def _remove_child_link(self, item):
        """Sever the parent->child relationship."""
        child_id = item.data(Qt.ItemDataRole.UserRole)
        child_pub = self.repo.get_by_id(child_id)
        if not child_pub: return
        
        if QMessageBox.question(self, "Remove Link", 
                                f"Are you sure you want to remove '{child_pub.publisher_name}' from being a subsidiary?") == QMessageBox.StandardButton.Yes:
            child_pub.parent_publisher_id = None
            if self.repo.update(child_pub):
                self._refresh_data()

    def _add_child(self):
        """Link an existing publisher as a child of this one."""
        # Exclude self and all ancestors to prevent circularity
        exclude = {self.pub.publisher_id}
        
        # Walk up to get all ancestors
        current = self.pub
        while current.parent_publisher_id:
            exclude.add(current.parent_publisher_id)
            current = self.repo.get_by_id(current.parent_publisher_id)
            if not current:
                break
        
        diag = PublisherPickerDialog(self.repo, exclude_ids=exclude, parent=self)
        if diag.exec():
            child_pub = diag.get_selected()
            if child_pub:
                # Double-check: would this create a cycle?
                # (child becoming parent of self via its descendants)
                if self._would_create_cycle(child_pub.publisher_id, self.pub.publisher_id):
                    QMessageBox.warning(self, "Circular Link Detected",
                                       "Cannot add this publisher - it would create a circular relationship.")
                    return
                
                # Set its parent to this publisher
                child_pub.parent_publisher_id = self.pub.publisher_id
                self.repo.update(child_pub)
                
                # Refresh the children list
                self._refresh_data()

    def _would_create_cycle(self, child_id, proposed_parent_id):
        """Check if setting proposed_parent_id as parent of child_id would create a cycle."""
        if not proposed_parent_id:
            return False
        if proposed_parent_id == child_id:
            return True  # Can't be your own parent
        
        # Walk up the parent chain from proposed_parent
        visited = {child_id}
        current_id = proposed_parent_id
        
        while current_id:
            if current_id in visited:
                return True  # Found a cycle!
            visited.add(current_id)
            
            parent_obj = self.repo.get_by_id(current_id)
            if not parent_obj:
                break
            current_id = parent_obj.parent_publisher_id
        
        return False

    def _save(self):
        new_name = self.txt_name.text().strip()
        if not new_name: return
        
        parent_id = self.cmb_parent.currentData()
        
        # Full circularity check (walks entire parent chain)
        if self._would_create_cycle(self.pub.publisher_id, parent_id):
            QMessageBox.warning(self, "Circular Link Detected", 
                               "Cannot set this parent - it would create a circular relationship.")
            return

        self.pub.publisher_name = new_name
        self.pub.parent_publisher_id = parent_id
        
        if self.repo.update(self.pub):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to update publisher.")


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
        self._refresh_list() # Initial load

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)

        # 1. Header
        lbl = QLabel("SELECT OR CREATE PUBLISHER")
        lbl.setObjectName("SidecarHeaderLabel") # Specific ID for styling
        layout.addWidget(lbl)

        # 2. Search Box
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Find Label...")
        self.txt_search.textChanged.connect(lambda: self._refresh_list(self.txt_search.text()))
        layout.addWidget(self.txt_search)

        # 5. Unified Action Button (Moved UP to decouple from Save button reflex)
        # Position: Between Search and List
        self.btn_action = GlowButton("Create New Label (+)")
        self.btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.btn_action)

        # 3. List
        self.list_pubs = QListWidget()
        self.list_pubs.setObjectName("AlbumManagerList") 
        self.list_pubs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_pubs.customContextMenuRequested.connect(self._show_context_menu)
        self.list_pubs.itemClicked.connect(self._on_item_clicked)
        self.list_pubs.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_pubs)

    def _refresh_list(self, query=""):
        self.list_pubs.clear()
        
        # Reset Action Button to Create Mode
        self.btn_action.setText("Create New Label (+)")
        self.btn_action.setProperty("mode", "create")
        
        results = self.pub_repo.search(query)
        
        for pub in results:
            item = QListWidgetItem(pub.publisher_name)
            item.setData(Qt.ItemDataRole.UserRole, pub.publisher_id)
            if pub.parent_publisher_id:
                item.setToolTip("Has Parent")
            self.list_pubs.addItem(item)

    def _on_item_clicked(self, item):
        self.btn_action.setText("Edit Selected Label")
        self.btn_action.setProperty("mode", "edit")
        self.publisher_selected.emit(
            item.data(Qt.ItemDataRole.UserRole),
            item.text()
        )

    def select_publisher_by_name(self, name):
        if not name or name == "(None)": return
        # Ensure exact match
        items = self.list_pubs.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            item = items[0]
            self.list_pubs.setCurrentItem(item)
            self.list_pubs.scrollToItem(item)
            self._on_item_clicked(item) # Sync button state

    def _on_item_double_clicked(self, item):
        self._open_manager(item.data(Qt.ItemDataRole.UserRole))

    def _on_action_clicked(self):
        mode = self.btn_action.property("mode")
        
        if mode == "edit":
            item = self.list_pubs.currentItem()
            if not item: return
            self._open_manager(item.data(Qt.ItemDataRole.UserRole))
        else:
            # Create Mode
            self._on_quick_add() # Reuse logic

    def _on_quick_add(self):
        # ... logic reused ...
        name = self.txt_search.text().strip()
        # If blank, prompt logic handled by dialog or fail?
        # Better: Open Creator Dialog with pre-filled text
        diag = PublisherCreatorDialog(parent=self)
        diag.inp_name.setText(name)
        
        if diag.exec():
            new_name = diag.get_name()
            if new_name:
                pub, created = self.pub_repo.get_or_create(new_name)
                self._refresh_list(new_name)
                # Auto-select the new item!
                for i in range(self.list_pubs.count()):
                    item = self.list_pubs.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == pub.publisher_id:
                        self.list_pubs.setCurrentItem(item)
                        self._on_item_clicked(item)
                        break
                
                self.publisher_selected.emit(pub.publisher_id, pub.publisher_name)

     # ... context menu ...

    def _show_context_menu(self, pos):
        item = self.list_pubs.itemAt(pos)
        if not item: return
        
        # Ensure UI and logic sync with the right-clicked item
        self.list_pubs.setCurrentItem(item)
        self._on_item_clicked(item) 

        pub_id = item.data(Qt.ItemDataRole.UserRole)
        pub_name = item.text()
        menu = QMenu(self)
        action_manage = QAction(f"Manage '{pub_name}'...", self)
        action_manage.triggered.connect(lambda: self._open_manager(pub_id))
        menu.addAction(action_manage)
        
        action_delete = QAction(f"Delete '{pub_name}'", self)
        action_delete.triggered.connect(lambda: self._delete_publisher(pub_id, pub_name))
        menu.addAction(action_delete)
        
        menu.exec(self.list_pubs.mapToGlobal(pos))

    def _delete_publisher(self, pub_id, pub_name):
        # Safety Check
        album_count = self.pub_repo.get_album_count(pub_id)
        child_count = self.pub_repo.get_child_count(pub_id)
        
        # Check Parent Status
        pub = self.pub_repo.get_by_id(pub_id)
        parent_name = None
        if pub and pub.parent_publisher_id:
            parent = self.pub_repo.get_by_id(pub.parent_publisher_id)
            if parent: parent_name = parent.publisher_name

        msg = f"Are you sure you want to delete '{pub_name}'?"
        details = []
        if album_count > 0:
            details.append(f"• Used by {album_count} album(s) (links will be removed)")
        if child_count > 0:
            details.append(f"• Has {child_count} subsidiarie(s) (will be orphaned)")
        if parent_name:
            details.append(f"• Is a subsidiary of '{parent_name}'")
        
        if details:
            msg += "\n\nWARNING:\n" + "\n".join(details)
            
        rv = QMessageBox.question(self, "Confirm Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if rv == QMessageBox.StandardButton.Yes:
            if self.pub_repo.delete(pub_id):
                self.btn_action.setText("Create New Label (+)") # Reset UI state
                self.btn_action.setProperty("mode", "create")
                self.publisher_selected.emit(0, "") # Signal clear
                self._refresh_list(self.txt_search.text())
            else:
                 QMessageBox.warning(self, "Error", "Failed to delete publisher.")

    def _on_edit_clicked(self):
        # Deprecated by _on_action_clicked but kept for safety if called elsewhere? 
        # No, removing.
        pass

    def _open_manager(self, pub_id):
        pub = self.pub_repo.get_by_id(pub_id)
        if not pub: return
        
        diag = PublisherDetailsDialog(pub, self.pub_repo, self)
        if diag.exec():
            # Refresh list to show changes (like renames)
            self._refresh_list(self.txt_search.text()) 


class PublisherManagerDialog(QDialog):
    """Refactored legacy bridge (Optional)."""
    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 500)
        layout = QVBoxLayout(self)
        self.picker = PublisherPickerWidget(repo, self)
        layout.addWidget(self.picker)
        self.picker.publisher_selected.connect(lambda i, n: self.accept())
