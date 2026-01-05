from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QWidget, QMenu, 
    QComboBox, QRadioButton, QButtonGroup, QSizePolicy, QInputDialog, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox
from ..widgets.entity_list_widget import EntityListWidget, LayoutMode
from src.core.entity_registry import EntityType
from src.core.context_adapters import ArtistMemberAdapter, ArtistAliasAdapter

class IdentityCollisionDialog(QDialog):
    """
    Human-friendly resolver for name conflicts. 
    No technical jargon, no scary boxes.
    """
    def __init__(
        self, target_name, song_count=0, has_context_song=False,
        title="Conflict Detected", header="IDENTITY CONFLICT", 
        primary_label=None, secondary_label=None, description=None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("CollisionDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("CollisionLayout")
        
        # 1. Human-Readable Explanation
        layout.addStretch(1)
        
        self.lbl_header = QLabel(header)
        self.lbl_header.setObjectName("CollisionHeader")
        self.lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_header)

        self.lbl_msg = QLabel(f'"{target_name}" is already in your library.')
        self.lbl_msg.setObjectName("CollisionMessage")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_msg)
        
        if description:
            desc = description
        elif has_context_song:
            desc = f"Link this song to the existing entry or all {song_count} songs?" if song_count > 1 else "Link this song to the existing entry?"
        else:
            desc = f"Merge all {song_count} songs into the existing identity?" if song_count > 1 else "Merge into the existing identity?"

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setObjectName("CollisionDescription")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_desc)

        layout.addStretch(1)
        
        # 2. Sequential Options (Safest to Broadest)
        btns = QVBoxLayout()
        btns.setObjectName("CollisionButtonLayout")
        
        # OPTION A: Link
        if has_context_song:
            label = primary_label or "LINK THIS SONG"
            self.btn_this = GlowButton(label)
            self.btn_this.setObjectName("ActionPill")
            self.btn_this.setProperty("action_role", "primary")
            self.btn_this.clicked.connect(lambda: self.done(3))
            self.btn_this.setDefault(True) 
            btns.addWidget(self.btn_this)
            
        # OPTION B: Merge
        # Show if multiple songs exist, OR if we are in a Global context (no specific song to link)
        show_all = (song_count > 1) or (not has_context_song)
        if show_all:
            if secondary_label:
                label = secondary_label
            else:
                label = f"ALL {song_count} SONGS" if song_count > 1 else "MERGE GLOBALLY"
            self.btn_all = GlowButton(label)
            self.btn_all.setObjectName("ActionPill")
            self.btn_all.setProperty("action_role", "secondary")
            self.btn_all.clicked.connect(lambda: self.done(1))
            btns.addWidget(self.btn_all)
            
        # OPTION C: Cancel (The "I made a mistake" exit)
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "ghost")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        layout.addLayout(btns)
        layout.addStretch(1)
        
        # Initial Focus
        if has_context_song:
            self.btn_this.setFocus()
        else:
            self.btn_all.setFocus()







class ArtistPickerDialog(QDialog):
    """
    Smart Search & Create dialog for Artists.
    Allows selecting existing OR creating new on the fly.
    """
    def __init__(self, service, filter_type=None, exclude_ids=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.filter_type = filter_type # None, 'person', or 'group'
        self.exclude_ids = exclude_ids or set()
        self._selected_artist = None
        self._selected_artists = [] # T-90: Multi-select support
        
        # Smart Type Tracking
        self._user_intended_type = 'person'  # What the user manually selected
        self._is_type_locked = False  # Whether we have an exact match lock
        
        self.setWindowTitle("Select or Add Artist")
        self.setObjectName("ArtistPickerDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("ArtistPickerLayout")
        
        target_name = filter_type.upper() if filter_type else "ARTIST"
        lbl = QLabel(f"SELECT OR ADD {target_name}")
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)
        
        # --- 1. SEARCH/INPUT ---
        h_row = QHBoxLayout()
        self.cmb = GlowComboBox()
        self.cmb.setEditable(True) # ENABLE EDITING
        self.cmb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        # Connect to auto-update type toggle (for dropdown selection)
        self.cmb.currentIndexChanged.connect(self._on_index_changed)
        # Connect text changes to check for exact matches (for typing)
        self.cmb.lineEdit().textChanged.connect(self._on_text_changed)
        
        h_row.addWidget(self.cmb)
        layout.addLayout(h_row)
        
        # --- 2. TYPE TOGGLES (Person/Group) ---
        type_layout = QHBoxLayout()
        type_layout.setSpacing(4)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.radio_person = GlowButton("PERSON 👤")
        self.radio_person.setObjectName("PickerTypeButton")
        self.radio_person.setCheckable(True)
        self.radio_person.setChecked(True)
        self.btn_group.addButton(self.radio_person.btn, 0)
        # Track user's manual selection
        self.radio_person.clicked.connect(lambda: self._on_user_type_clicked('person'))
        
        self.radio_group = GlowButton("GROUP 👥")
        self.radio_group.setObjectName("PickerTypeButton")
        self.radio_group.setCheckable(True)
        self.btn_group.addButton(self.radio_group.btn, 1)
        # Track user's manual selection  
        self.radio_group.clicked.connect(lambda: self._on_user_type_clicked('group'))
        
        type_layout.addStretch()
        type_layout.addWidget(self.radio_person)
        type_layout.addWidget(self.radio_group)
        type_layout.addStretch()
        
        # If filter_type is strict, lock these permanently
        if self.filter_type == 'person':
            self.radio_person.setChecked(True)
            self.radio_group.setEnabled(False)
            self._user_intended_type = 'person'
        elif self.filter_type == 'group':
            self.radio_group.setChecked(True)
            self.radio_person.setEnabled(False)
            self._user_intended_type = 'group'
            
        layout.addLayout(type_layout)
        
        layout.addStretch()
        
        # --- 3. ACTIONS ---
        btns = QHBoxLayout()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_select = GlowButton("Select / Create")
        self.btn_select.setObjectName("ActionPill")
        self.btn_select.setProperty("action_role", "primary")
        self.btn_select.setDefault(True) # Make Enter trigger this button
        self.btn_select.clicked.connect(self._on_select)
        
        # Connect Enter key in the editable line edit to submission
        self.cmb.lineEdit().returnPressed.connect(self._on_select)
        
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_select)
        btns.addStretch()
        layout.addLayout(btns)
        
        self._populate()
        self.cmb.setFocus() # Focus search

    def _on_user_type_clicked(self, type_str):
        """User manually clicked a type button - remember their intent."""
        if not self._is_type_locked:
            self._user_intended_type = type_str

    def _on_text_changed(self, text):
        """Check if typed text exactly matches an existing artist."""
        text = text.strip()
        if not text:
            self._unlock_type()
            return
            
        # Check for exact match
        exact_match = self.service.get_by_name(text)
        if exact_match:
            self._lock_to_type(exact_match.type)
        else:
            self._unlock_type()

    def _lock_to_type(self, type_str):
        """Lock the type toggle to match an existing artist."""
        if self._is_type_locked and self._get_current_type() == type_str:
            return  # Already locked to this type
            
        self._is_type_locked = True
        
        # Switch to the matched type
        if type_str == 'group':
            self.radio_group.setChecked(True)
        else:
            self.radio_person.setChecked(True)
        
        # Disable both buttons to show "locked" state (unless filter_type is set)
        if not self.filter_type:
            self.radio_person.setEnabled(False)
            self.radio_group.setEnabled(False)

    def _unlock_type(self):
        """Unlock the type toggle and restore user's intended type."""
        if not self._is_type_locked:
            return  # Already unlocked
            
        self._is_type_locked = False
        
        # Re-enable buttons (unless filter_type restricts them)
        if not self.filter_type:
            self.radio_person.setEnabled(True)
            self.radio_group.setEnabled(True)
        elif self.filter_type == 'person':
            self.radio_person.setEnabled(True)
        elif self.filter_type == 'group':
            self.radio_group.setEnabled(True)
        
        # Restore user's original intended type
        if self._user_intended_type == 'group':
            self.radio_group.setChecked(True)
        else:
            self.radio_person.setChecked(True)

    def _get_current_type(self):
        """Get the currently selected type."""
        return 'group' if self.radio_group.isChecked() else 'person'

    def _populate(self):
        self.cmb.blockSignals(True)
        self.cmb.clear()
        results = self.service.search_identities("")
        for c_id, name, c_type, source in results:
            if self.filter_type and c_type != self.filter_type:
                continue
            if c_id in self.exclude_ids:
                continue
            
            display_name = name
            target_name = name
            if source == 'Alias':
                display_name += " (Alias)"
                
            # Store tuple of (ID, SpecificName, Type) to help logic
            # Note: We append Type to helping auto-toggle
            self.cmb.addItem(display_name, (c_id, target_name, c_type))
        
        # Clear any selection initially so user can type
        self.cmb.setCurrentIndex(-1)
        self.cmb.blockSignals(False)

    def _on_index_changed(self, index):
        """Auto-toggle and lock Person/Group based on dropdown selection."""
        if index < 0: 
            self._unlock_type()
            return
        data = self.cmb.itemData(index)
        if data:
            _, _, c_type = data
            self._lock_to_type(c_type)

    def _on_select(self):
        data = self.cmb.currentData()
        current_text = self.cmb.currentText().strip()
        
        if not current_text: return

        # 1. Existing Dropdown Selection
        if data:
            artist_id, name_to_use, _ = data
            selected = self.service.get_by_id(artist_id)
            if selected:
                if name_to_use: selected.name = name_to_use
                self._selected_artists = [selected]
                self.accept()
            return
            
        # 2. Smart Split Logic (T-90)
        import re
        
        # T-Feature: Trailing Comma Heuristic (CamelSplit)
        # Workflow: User types "BobJohnBill," -> Convert to "Bob, John, Bill"
        if current_text.endswith(','):
            raw = current_text.rstrip(',')
            # Insert comma-space before Uppercase letters (unless at start)
            # This splits "BobJohnBill" -> "Bob, John, Bill"
            current_text = re.sub(r'(?<!^)(?=[A-Z])', ', ', raw)

        # Delimiters: comma, semicolon, slash, or " & " (padded ampersand)
        tokens = [t.strip() for t in re.split(r'[,;/]|\s+&+\s+', current_text) if t.strip()]
        
        if len(tokens) > 1:
            msg = "Detected multiple contributors:\n" + "\n".join([f"• {t}" for t in tokens]) + "\n\nSplit into individual entries?"
            if QMessageBox.question(self, "Split Input?", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self._selected_artists = []
                target_type = "group" if self.radio_group.isChecked() else "person"
                
                for t in tokens:
                    try:
                        # Auto-create or Get
                        # Note: We respect target_type for all, which is usually safe for "Prodigy, Pendulum" (Groups) or "A, B" (Persons)
                        a, _ = self.service.get_or_create(t, target_type)
                        # Fix: Use the typed name 't' (alias) instead of forcing Primary Name
                        a.name = t
                        self._selected_artists.append(a)
                    except Exception as e:
                        print(f"Error creating '{t}': {e}")
                
                self.accept()
                return

        # 3. Fallback: Exact Name Match
        exact_match = self.service.get_by_name(current_text)
        if exact_match:
            # Fix: Use the typed name (alias) instead of forcing Primary Name
            exact_match.name = current_text
            self._selected_artists = [exact_match]
            self.accept()
            return
            
        # 4. Create New Single
        target_type = "group" if self.radio_group.isChecked() else "person"
        try:
            new_artist, created = self.service.get_or_create(current_text, target_type)
            self._selected_artists = [new_artist]
            self.accept()
        except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create artist: {e}")

    def get_selected(self):
        # Prefer list if populated
        return self._selected_artists if self._selected_artists else self._selected_artist

class ArtistPickerWidget(QWidget):
    """
    Searchable Picker Widget for Artists.
    Integrated into the Side Panel Artist area.
    """
    artist_selected = pyqtSignal(int, str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Search Box
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Search Artists...")
        self.txt_search.textChanged.connect(lambda: self._refresh_list(self.txt_search.text()))
        layout.addWidget(self.txt_search)

        # 2. List
        self.list_artists = QListWidget()
        self.list_artists.setObjectName("AlbumManagerList") 
        self.list_artists.itemClicked.connect(self._on_item_clicked)
        self.list_artists.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_artists.itemActivated.connect(self._on_item_double_clicked) # Enter key = Double Click
        self.list_artists.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_artists.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_artists)

        # 3. Action Button
        self.btn_action = GlowButton("Create New Artist (+)")
        self.btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.btn_action)

    def _refresh_list(self, query=""):
        self.list_artists.clear()
        self.btn_action.setText("Create New Artist (+)")
        self.btn_action.setProperty("mode", "create")
        
        results = self.service.search(query)
        for artist in results:
            display_name = artist.name
            if artist.matched_alias:
                display_name += f" (AKA: {artist.matched_alias})"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, artist.contributor_id)
            item.setData(Qt.ItemDataRole.DisplayRole, display_name) # Explicit but helpful
            self.list_artists.addItem(item)

    def _on_item_clicked(self, item):
        text = item.text()
        # Extract Primary Name (Strip AKA suffix if present)
        name = text.split(" (AKA: ", 1)[0]
        
        self.btn_action.setText(f"Edit '{name}'")
        self.btn_action.setProperty("mode", "edit")
        self.artist_selected.emit(
            item.data(Qt.ItemDataRole.UserRole),
            name
        )

    def _on_item_double_clicked(self, item):
        self._open_details(item.data(Qt.ItemDataRole.UserRole))

    def _on_action_clicked(self):
        mode = self.btn_action.property("mode")
        if mode == "edit":
            item = self.list_artists.currentItem()
            if item:
                self._open_details(item.data(Qt.ItemDataRole.UserRole))
        else:
            self._on_quick_add()

    def _on_quick_add(self):
        name = self.txt_search.text().strip()
        diag = ArtistCreatorDialog(initial_name=name, parent=self)
        if diag.exec():
            new_name, new_type = diag.get_data()
            if new_name:
                artist, created = self.service.get_or_create(new_name, new_type)
                self._refresh_list(new_name)
                # Select the new artist
                for i in range(self.list_artists.count()):
                    item = self.list_artists.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == artist.contributor_id:
                        self.list_artists.setCurrentItem(item)
                        self._on_item_clicked(item)
                        break
                self.artist_selected.emit(artist.contributor_id, artist.name)

    def _show_context_menu(self, pos):
        item = self.list_artists.itemAt(pos)
        if not item: return
        self.list_artists.setCurrentItem(item)
        artist_id = item.data(Qt.ItemDataRole.UserRole)
        # Handle cases where AKA... is in the display text
        name = item.text().split(" (AKA: ", 1)[0]

        menu = QMenu(self)
        manage_act = QAction(f"Manage '{name}'...", self)
        manage_act.triggered.connect(lambda: self._open_details(artist_id))
        menu.addAction(manage_act)
        
        delete_act = QAction(f"Delete Artist '{name}'", self)
        delete_act.triggered.connect(lambda: self._delete_artist(artist_id, name))
        menu.addAction(delete_act)
        
        menu.addSeparator()
        
        merge_act = QAction(f"Consolidate '{name}' into...", self)
        merge_act.triggered.connect(lambda: self._on_merge_clicked(artist_id, name))
        menu.addAction(merge_act)
        
        menu.exec(self.list_artists.mapToGlobal(pos))

    def _on_merge_clicked(self, source_id, source_name):
        from .entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_artist_picker_config
        
        # Get service provider (need to wrap service for EntityPickerDialog)
        class _ServiceProvider:
            def __init__(self, service):
                self.contributor_service = service
        
        config = get_artist_picker_config()
        config.title_add = f"Consolidate '{source_name}' into..."
        
        diag = EntityPickerDialog(
            service_provider=_ServiceProvider(self.service),
            config=config,
            exclude_ids={source_id},
            parent=self
        )
        
        if diag.exec():
            target = diag.get_selected()

            if target:
                if self.service.merge_contributors(source_id, target.contributor_id):
                    self._refresh_list(self.txt_search.text())
                    self.artist_selected.emit(target.contributor_id, target.name)
                else:
                    QMessageBox.warning(self, "Error", "Consolidation failed.")

    def _delete_artist(self, artist_id, name):
        # 1. Check for usage/impact
        impact_count = self.service.get_member_count(artist_id)
        
        msg = f"Are you sure you want to PERMANENTLY delete '{name}'?\n\n"
        msg += "This will:\n"
        msg += "• Orphan any songs currently using this artist identity.\n"
        msg += f"• Clean up {impact_count} membership/group relationship(s).\n"
        msg += "• Purge all associated aliases."
        
        if QMessageBox.question(self, "Confirm Full Delete", msg, 
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.service.delete(artist_id):
                self._refresh_list(self.txt_search.text())
                self.artist_selected.emit(0, "") # Signal clear

    def _open_details(self, artist_id):
        artist = self.service.get_by_id(artist_id)
        if not artist: return
        # Global Manager: No specific context song
        diag = ArtistDetailsDialog(artist, self.service, context_song=None, parent=self)
        if diag.exec():
            self._refresh_list(self.txt_search.text())

class ArtistDetailsDialog(QDialog):
    """
    Full Artist Editor with Memberships, Aliases, etc.
    """
    def __init__(self, artist, service, context_song=None, allow_remove_from_context=False, parent=None):
        super().__init__(parent)
        self.artist = artist
        self.context_song = context_song
        self.original_type = artist.type
        self.service = service
        self.allow_remove = allow_remove_from_context
        self.setWindowTitle(f"Manager: {artist.name}")
        self.setObjectName("ArtistDetailsDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("ArtistDetailsLayout")
        
        self._init_ui(layout)
        self._refresh_data()

    def _init_ui(self, layout):
        # 1. Identity
        lbl_name = QLabel("ARTIST NAME")
        lbl_name.setObjectName("DialogFieldLabel")
        self.txt_name = GlowLineEdit()
        self.txt_name.edit.setPlaceholderText("Artist Name...")
        self.txt_name.edit.returnPressed.connect(self._save) # Snappy: Enter to Update
        
        layout.addWidget(lbl_name)
        layout.addWidget(self.txt_name)
        
        lbl_sort = QLabel("SORT NAME")
        lbl_sort.setObjectName("DialogFieldLabel")
        self.txt_sort = GlowLineEdit()
        self.txt_sort.edit.returnPressed.connect(self._save) # Snappy: Enter to Update
        layout.addWidget(lbl_sort)
        layout.addWidget(self.txt_sort)
        
        # Type (Buttons)
        t_row = QHBoxLayout()
        t_row.setSpacing(20)  # Extra space for glow margins
        t_row.setContentsMargins(0, 8, 10, 0)  # Removed bottom margin - let the glow breathe
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.radio_person = GlowButton("PERSON")
        self.radio_person.setObjectName("IdentityTypeButton")
        self.radio_person.setCheckable(True)
        self.radio_person.setMinimumHeight(48)  # Extra height for glow
        self.btn_group.addButton(self.radio_person.btn, 0)
        
        self.radio_group = GlowButton("GROUP")
        self.radio_group.setObjectName("IdentityTypeButton")
        self.radio_group.setCheckable(True)
        self.radio_group.setMinimumHeight(48)  # Extra height for glow
        self.btn_group.addButton(self.radio_group.btn, 1)
        
        # UI Refresh logic (Safe-Toggle)
        self.radio_person.toggled.connect(lambda checked: self._on_type_toggled("person") if checked else None)
        self.radio_group.toggled.connect(lambda checked: self._on_type_toggled("group") if checked else None)

        t_row.addWidget(self.radio_person)
        t_row.addWidget(self.radio_group)
        t_row.addStretch()
        layout.addLayout(t_row)
        
        # Spacer for glow to render without clipping
        layout.addSpacing(8)
        
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        line.setFixedHeight(2)
        layout.addWidget(line)
        
        # Aliases - NOW USES EntityListWidget with chips!
        h_alias = QHBoxLayout()
        lbl_alias = QLabel("ALIASES")
        lbl_alias.setObjectName("DialogFieldLabel")
        h_alias.addWidget(lbl_alias)
        h_alias.addStretch()
        layout.addLayout(h_alias)
        
        # Create a mock service provider for EntityListWidgets
        # This is a temporary adapter until we have a real ServiceProvider
        class _ServiceAdapter:
            def __init__(self, service):
                self.contributor_service = service
        
        self._service_adapter = _ServiceAdapter(self.service)
        
        # Create alias adapter
        self._alias_adapter = ArtistAliasAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        
        self.list_aliases = EntityListWidget(
            service_provider=self._service_adapter,
            entity_type=EntityType.ALIAS,
            layout_mode=LayoutMode.CLOUD,  # Chips!
            context_adapter=self._alias_adapter,
            allow_add=True,  # Show the (+) button
            allow_remove=True,
            allow_edit=False,  # Custom context menu instead
            add_tooltip="Add Alias",
            confirm_removal=False,  # Simplified removal
            parent=self
        )
        # Override the add handler to use our custom merge-based alias add
        if self.list_aliases.tray:
            # Disconnect default and connect our custom handler
            self.list_aliases.tray.add_requested.disconnect()
            self.list_aliases.tray.add_requested.connect(self._add_alias)
        # Connect to custom context menu for Promote/Rename actions
        self.list_aliases.chip_context_menu_requested.connect(self._show_alias_chip_menu)
        layout.addWidget(self.list_aliases)
        
        # Membership - NOW USES EntityListWidget!
        h_member = QHBoxLayout()
        self.lbl_member = QLabel("MEMBERS")
        self.lbl_member.setObjectName("DialogFieldLabel")
        h_member.addWidget(self.lbl_member)
        h_member.addStretch()
        layout.addLayout(h_member)
        
        # Create the member adapter (will be recreated on type toggle)
        self._member_adapter = ArtistMemberAdapter(
            self.artist, 
            self.service, 
            refresh_fn=self._refresh_data
        )
        
        self.list_members = EntityListWidget(
            service_provider=self._service_adapter,
            entity_type=EntityType.GROUP_MEMBER,
            layout_mode=LayoutMode.CLOUD,  # Chips instead of list
            context_adapter=self._member_adapter,
            allow_add=True,
            allow_remove=True,
            allow_edit=True,
            add_tooltip="Add Member/Group",
            parent=self
        )
        self.list_members.setObjectName("ArtistSubList")
        
        # Set the picker filter based on artist type
        self.list_members.set_picker_filter(
            lambda: "person" if self.artist.type == "group" else "group"
        )
        
        layout.addWidget(self.list_members)
        
        btns = QHBoxLayout()
        btns.addStretch()
        
        # 1. Destructive (Left) - ONLY if in a context where unlinking makes sense
        if self.allow_remove:
            self.btn_delete = GlowButton("Remove")
            self.btn_delete.setObjectName("ActionPill")
            self.btn_delete.setProperty("action_role", "destructive")
            self.btn_delete.setToolTip("Unlink this artist from the current song(s)")
            self.btn_delete.clicked.connect(lambda: self.done(2)) # Code 2 = Remove Request
            btns.addWidget(self.btn_delete)
        
        # 2. Neutral (Middle)
        btn_cancel = GlowButton("Cancel")
        btn_cancel.setObjectName("ActionPill")
        btn_cancel.setProperty("action_role", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        
        # 3. Primary (Right)
        btn_save = GlowButton("UPDATE")
        btn_save.setObjectName("ActionPill")
        btn_save.setProperty("action_role", "primary")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        btns.addStretch()
        layout.addLayout(btns)

    def _refresh_data(self):
        # Block signals to prevent recursion during programmatic check
        self.radio_person.blockSignals(True)
        self.radio_group.blockSignals(True)
        
        self.txt_name.setText(self.artist.name)
        self.txt_sort.setText(self.artist.sort_name)
        if self.artist.type == "group":
            self.radio_group.setChecked(True)
            self.radio_person.setChecked(False)
            self.lbl_member.setText("GROUP MEMBERS")
        else:
            self.radio_person.setChecked(True)
            self.radio_group.setChecked(False)
            self.lbl_member.setText("BELONGS TO GROUPS")
            
        self.radio_person.blockSignals(False)
        self.radio_group.blockSignals(False)
            
        # Aliases - now uses EntityListWidget!
        # Update the adapter with current artist
        self._alias_adapter = ArtistAliasAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        self.list_aliases.context_adapter = self._alias_adapter
        self.list_aliases.refresh_from_adapter()
            
        # Memberships - now uses EntityListWidget!
        # Update the adapter with current artist (type may have changed)
        self._member_adapter = ArtistMemberAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        self.list_members.context_adapter = self._member_adapter
        self.list_members.refresh_from_adapter()

    def _on_type_toggled(self, new_type):
        """Update local model and refresh context labels."""
        if self.artist.type == new_type:
            return
        self.artist.type = new_type
        self._refresh_data()

    def _add_alias(self):
        # UNIFY: Use the modern EntityPickerDialog (matching "add person" flow)
        # BUT filter to only show same-type artists (person for person, group for group)
        from .entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_artist_picker_config
        
        # Get service provider (need to wrap service for EntityPickerDialog)
        class _ServiceProvider:
            def __init__(self, service):
                self.contributor_service = service
        
        # Get base config and customize for alias-adding
        config = get_artist_picker_config()
        config.title_add = f"Add Alias for {self.artist.name}"
        
        # FILTER: Show same type + Alias, but NOT the opposite type
        # e.g., for Person: show Person + Alias, hide Group
        # e.g., for Group: show Group + Alias, hide Person
        artist_type = self.artist.type.title()  # "person" -> "Person"
        opposite_type = "Group" if artist_type == "Person" else "Person"
        
        # Remove the opposite type from buttons
        config.type_buttons = [t for t in config.type_buttons if t != opposite_type]
        config.type_icons = {k: v for k, v in config.type_icons.items() if k != opposite_type}
        config.type_colors = {k: v for k, v in config.type_colors.items() if k != opposite_type}
        config.default_type = artist_type
        
        diag = EntityPickerDialog(
            service_provider=_ServiceProvider(self.service),
            config=config,
            exclude_ids={self.artist.contributor_id},
            parent=self
        )
        
        if diag.exec():
            target = diag.get_selected()
            
            if not target:
                return
                
            # Check for Self (should be excluded by Picker but safe check)
            if target.contributor_id == self.artist.contributor_id:
                return
            
            # It's an independent artist entity.
            # Since an alias in our schema IS a contributor link, 
            # we are effectively saying "This independent entity IS actually me."
            # This requires a MERGE operation (Absorb).
            
            # Double Check Type Safety
            if target.type != self.artist.type:
                 QMessageBox.warning(self, "Type Mismatch", 
                                   f"Cannot use '{target.name}' ({target.type}) as alias for '{self.artist.name}' ({self.artist.type}).\n\n"
                                   "Aliases must be of the same type.")
                 return
            
            # MERGE: Absorb 'target' into 'self.artist'
            # This moves all of target's songs/roles to self.artist, and deletes target.
            # It also usually adds 'target.name' as an alias of 'self.artist' implicitly via the merge service logic.
            
            confirm_msg = f"'{target.name}' exists as a separate artist.\n\n" \
                          f"Do you want to MERGE '{target.name}' into '{self.artist.name}'?\n" \
                          f"This will make '{target.name}' an alias of '{self.artist.name}' and transfer all songs."
                          
            if QMessageBox.question(self, "Confirm Merge", confirm_msg, 
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                                  
                if self.service.merge(target.contributor_id, self.artist.contributor_id):
                    from src.core import logger
                    logger.info(f"Identity Absorbed via Alias Add: '{target.name}' merged into '{self.artist.name}'.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to merge '{target.name}'.")
            
            self._refresh_data()

    def _show_alias_chip_menu(self, alias_id, alias_name, global_pos):
        """Show context menu for alias chips."""
        menu = QMenu(self)
        
        promote_act = QAction("Set as Primary ★", self)
        promote_act.triggered.connect(lambda: self._promote_alias(alias_id, alias_name))
        menu.addAction(promote_act)
        
        menu.addSeparator()

        edit_act = QAction("Rename", self)
        edit_act.triggered.connect(lambda: self._edit_alias(alias_id, alias_name))
        menu.addAction(edit_act)
        
        del_act = QAction("Unlink Name", self)
        del_act.triggered.connect(lambda: self._confirm_delete_alias(alias_id, alias_name))
        menu.addAction(del_act)
        menu.exec(global_pos)

    def _confirm_delete_alias(self, alias_id, name):
        # Simplified: Just do it. Audit log handles the safety.
        if self.service.delete_alias(alias_id):
            self._refresh_data()

    def _promote_alias(self, alias_id, name):
        msg = f"This will swap the primary identity '{self.artist.name}' with the alias '{name}'.\n\n"
        msg += f"'{name}' will become the MASTER name for all songs, and '{self.artist.name}' will be kept as an alias.\n\n"
        msg += "Proceed with this Hot Swap?"
        
        if QMessageBox.question(self, "Promote to Primary", msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.service.promote_alias(self.artist.contributor_id, alias_id):
                # We need to reload the whole artist object because the name changed
                self.artist = self.service.get_by_id(self.artist.contributor_id)
                self.setWindowTitle(f"Manager: {self.artist.name}")
                self._refresh_data()

    def _edit_alias(self, alias_id, old_name):
        diag = ArtistCreatorDialog(initial_name=old_name, button_text="UPDATE", parent=self)
        diag.setWindowTitle("Rename Alias")
        diag.radio_person.hide(); diag.radio_group.hide()
        if diag.exec():
            new_name, _ = diag.get_data()
            if new_name and new_name != old_name:
                self.service.update_alias(alias_id, new_name)
                self._refresh_data()

    def _delete_alias(self, alias_id):
        # Unused now, replaced by confirm version
        pass

    # NOTE: _add_member, _show_member_menu, _remove_member are now handled by EntityListWidget
    # The old manual implementations have been removed.

    def _save(self):
        new_name = self.txt_name.text().strip()
        if not new_name: return
        
        new_type = "group" if self.radio_group.isChecked() else "person"
        
        # Validation for name change
        if new_name != self.artist.name:
            conflict_id, msg = self.service.validate_identity(new_name, exclude_id=self.artist.contributor_id)
            if conflict_id:
                # HUMAN RESOLVER: Just ask the simple question
                usage_count = self.service.get_usage_count(self.artist.contributor_id)
                resolver = IdentityCollisionDialog(
                    target_name=new_name,
                    song_count=usage_count,
                    has_context_song=(self.context_song is not None),
                    title="Artist Exists",
                    header="IDENTITY CONFLICT",
                    parent=self
                )

                
                res = resolver.exec()
                if res == 0: # Cancel
                    return

                if res == 1: # Fix Typo (Clean Merge)
                    if self.service.merge_contributors(self.artist.contributor_id, conflict_id, create_alias=False):
                        self.done(3) # Signal 3: Data Changed (Sync Required)
                        return
                    else:
                        QMessageBox.warning(self, "Error", "Merge failed.")
                        return


                if res == 3 and self.context_song: # Fix This Song Only
                    if self.service.swap_song_contributor(self.context_song.source_id, self.artist.contributor_id, conflict_id):
                        # Signal Code 3 to trigger UI refresh for the new ID
                        self.done(3)
                        return
                    else:
                        QMessageBox.warning(self, "Error", "Local link failed.")
                        return
                
                return # Halt save, merge/swap handled it.

        # Safety check for type change (Data integrity)
        if self.original_type != new_type:
            if self.original_type == "group":
                # Losing 'Children'
                count = len(self.service.get_members(self.artist.contributor_id))
                relation = "member"
            else:
                # Losing 'Parents'
                count = len(self.service.get_groups(self.artist.contributor_id))
                relation = "group membership"

            if count > 0:
                msg = f"Changing this {self.original_type.capitalize()} to a {new_type.capitalize()} will remove {count} existing {relation}(s). Are you sure?"
                if QMessageBox.warning(self, "Confirm Type Change", msg, 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
        
        self.artist.name = new_name
        self.artist.sort_name = self.txt_sort.text().strip()
        self.artist.type = new_type
        
        if self.service.update(self.artist):
            self.done(3) # Signal 3: Data Changed (Sync Required)
        else:
            QMessageBox.warning(self, "Error", "Failed to save artist changes.")

