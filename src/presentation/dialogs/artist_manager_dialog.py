from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QWidget, QMenu, 
    QComboBox, QRadioButton, QButtonGroup, QSizePolicy, QInputDialog, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox

class IdentityCollisionDialog(QDialog):
    """
    Human-friendly resolver for name conflicts. 
    No technical jargon, no scary boxes.
    """
    def __init__(self, target_name, song_count=0, has_context_song=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Artist Exists")
        self.setObjectName("CollisionDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("CollisionLayout")
        
        # 1. Human-Readable Explanation
        layout.addStretch(1)
        
        self.lbl_header = QLabel("IDENTITY CONFLICT")
        self.lbl_header.setObjectName("CollisionHeader")
        self.lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_header)

        self.lbl_msg = QLabel(f'"{target_name}" is already in your library.')
        self.lbl_msg.setObjectName("CollisionMessage")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_msg)
        
        if has_context_song:
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
            self.btn_this = GlowButton("LINK THIS SONG")
            self.btn_this.setObjectName("ActionPill")
            self.btn_this.setProperty("action_role", "primary")
            self.btn_this.clicked.connect(lambda: self.done(3))
            self.btn_this.setDefault(True) 
            btns.addWidget(self.btn_this)
            
        # OPTION B: Merge
        # Show if multiple songs exist, OR if we are in a Global context (no specific song to link)
        show_all = (song_count > 1) or (not has_context_song)
        if show_all:
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





class ArtistCreatorDialog(QDialog):
    """
    Quick dialog for creating a new artist with Name and Type.
    """
    def __init__(self, initial_name="", button_text="Create Artist", parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Artist")
        self.setObjectName("ArtistCreatorDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("ArtistCreatorLayout")
        
        # 1. Name Field
        lbl_name = QLabel("ARTIST NAME")
        lbl_name.setObjectName("DialogFieldLabel")
        self.inp_name = GlowLineEdit()
        self.inp_name.setText(initial_name)
        
        layout.addWidget(lbl_name)
        layout.addWidget(self.inp_name)
        
        # 2. Type Selection (Person/Group Buttons)
        lbl_type = QLabel("ARTIST TYPE")
        lbl_type.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl_type)
        
        type_layout = QHBoxLayout()
        type_layout.setSpacing(4)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.radio_person = GlowButton("PERSON")
        self.radio_person.setObjectName("IdentityTypeButton")
        self.radio_person.setCheckable(True)
        self.radio_person.setChecked(True)
        self.btn_group.addButton(self.radio_person.btn, 0)
        
        self.radio_group = GlowButton("GROUP")
        self.radio_group.setObjectName("IdentityTypeButton")
        self.radio_group.setCheckable(True)
        self.btn_group.addButton(self.radio_group.btn, 1)
        
        type_layout.addStretch()
        type_layout.addWidget(self.radio_person)
        type_layout.addWidget(self.radio_group)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        layout.addStretch()
        
        # 3. Actions
        btns = QHBoxLayout()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = GlowButton(button_text)
        self.btn_save.setObjectName("ActionPill")
        self.btn_save.setProperty("action_role", "primary")
        self.btn_save.setDefault(True) # Snappy: Press Enter to create
        self.btn_save.clicked.connect(self.accept)
        
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        btns.addStretch()
        
        layout.addStretch(1) # Anchor to bottom
        layout.addLayout(btns)
        
        self.inp_name.setFocus()
        self.inp_name.edit.returnPressed.connect(self.accept) # Snappy: Enter to Create
        if initial_name:
            self.inp_name.edit.selectAll()

    def get_data(self):
        """Returns (name, type_string)"""
        name = self.inp_name.text().strip()
        type_str = "group" if self.radio_group.isChecked() else "person"
        return name, type_str


class ArtistPickerDialog(QDialog):
    """
    Smart Search & Create dialog for Artists.
    Allows selecting existing OR creating new on the fly.
    """
    def __init__(self, repo, filter_type=None, exclude_ids=None, parent=None):
        super().__init__(parent)
        self.repo = repo
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
        exact_match = self.repo.get_by_name(text)
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
        results = self.repo.search("")
        for a in results:
            if self.filter_type and a.type != self.filter_type:
                continue
            if a.contributor_id in self.exclude_ids:
                continue
            
            display_name = a.name
            target_name = a.name
            if a.matched_alias:
                display_name += f" (AKA: {a.matched_alias})"
                target_name = a.matched_alias
                
            # Store tuple of (ID, SpecificName, Type) to help logic
            # Note: We append Type to helping auto-toggle
            self.cmb.addItem(display_name, (a.contributor_id, target_name, a.type))
        
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
            selected = self.repo.get_by_id(artist_id)
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
                        a, _ = self.repo.get_or_create(t, target_type)
                        # Fix: Use the typed name 't' (alias) instead of forcing Primary Name
                        a.name = t
                        self._selected_artists.append(a)
                    except Exception as e:
                        print(f"Error creating '{t}': {e}")
                
                self.accept()
                return

        # 3. Fallback: Exact Name Match
        exact_match = self.repo.get_by_name(current_text)
        if exact_match:
            # Fix: Use the typed name (alias) instead of forcing Primary Name
            exact_match.name = current_text
            self._selected_artists = [exact_match]
            self.accept()
            return
            
        # 4. Create New Single
        target_type = "group" if self.radio_group.isChecked() else "person"
        try:
            new_artist = self.repo.create(current_text, target_type)
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

    def __init__(self, contributor_repository, parent=None):
        super().__init__(parent)
        self.repo = contributor_repository
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
        
        results = self.repo.search(query)
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
                artist, created = self.repo.get_or_create(new_name, new_type)
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
        diag = ArtistPickerDialog(self.repo, exclude_ids=[source_id], parent=self)
        diag.setWindowTitle(f"Consolidate '{source_name}' into...")
        if diag.exec():
            # Handle List Return (take first)
            result = diag.get_selected()
            if isinstance(result, list):
                target = result[0] if result else None
            else:
                target = result

            if target:
                msg = f"This will move ALL songs, aliases, and relationships from '{source_name}' to '{target.name}'.\n\n"
                msg += f"'{source_name}' will be DELETED and added as an alias for '{target.name}'.\n\n"
                msg += "Are you sure you want to perform this heavy-lifting merge?"
                
                if QMessageBox.question(self, "Confirm Consolidation", msg,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                    if self.repo.merge(source_id, target.contributor_id):
                        self._refresh_list(self.txt_search.text())
                        self.artist_selected.emit(target.contributor_id, target.name)
                    else:
                        QMessageBox.warning(self, "Error", "Consolidation failed.")

    def _delete_artist(self, artist_id, name):
        # 1. Check for usage/impact
        # Since ContributorRepository doesn't have a direct get_song_count, we can look at member counts
        impact_count = self.repo.get_member_count(artist_id)
        
        msg = f"Are you sure you want to PERMANENTLY delete '{name}'?\n\n"
        msg += "This will:\n"
        msg += "• Orphan any songs currently using this artist identity.\n"
        msg += f"• Clean up {impact_count} membership/group relationship(s).\n"
        msg += "• Purge all associated aliases."
        
        if QMessageBox.question(self, "Confirm Full Delete", msg, 
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.repo.delete(artist_id):
                self._refresh_list(self.txt_search.text())
                self.artist_selected.emit(0, "") # Signal clear

    def _open_details(self, artist_id):
        artist = self.repo.get_by_id(artist_id)
        if not artist: return
        # Global Manager: No specific context song
        diag = ArtistDetailsDialog(artist, self.repo, context_song=None, parent=self)
        if diag.exec():

            self._refresh_list(self.txt_search.text())

class ArtistDetailsDialog(QDialog):
    """
    Full Artist Editor with Memberships, Aliases, etc.
    """
    def __init__(self, artist, repo, context_song=None, allow_remove_from_context=False, parent=None):
        super().__init__(parent)
        self.artist = artist
        self.context_song = context_song
        self.original_type = artist.type
        self.repo = repo
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
        t_row.setSpacing(4)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.radio_person = GlowButton("PERSON")
        self.radio_person.setObjectName("IdentityTypeButton")
        self.radio_person.setCheckable(True)
        self.btn_group.addButton(self.radio_person.btn, 0)
        
        self.radio_group = GlowButton("GROUP")
        self.radio_group.setObjectName("IdentityTypeButton")
        self.radio_group.setCheckable(True)
        self.btn_group.addButton(self.radio_group.btn, 1)
        
        # UI Refresh logic (Safe-Toggle)
        self.radio_person.toggled.connect(lambda checked: self._on_type_toggled("person") if checked else None)
        self.radio_group.toggled.connect(lambda checked: self._on_type_toggled("group") if checked else None)

        t_row.addWidget(self.radio_person)
        t_row.addWidget(self.radio_group)
        t_row.addStretch()
        layout.addLayout(t_row)
        
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        line.setFixedHeight(2)
        layout.addWidget(line)
        
        # Aliases
        h_alias = QHBoxLayout()
        lbl_alias = QLabel("ALIASES")
        lbl_alias.setObjectName("DialogFieldLabel")
        h_alias.addWidget(lbl_alias)
        
        h_alias.addStretch()
        
        btn_add_alias = GlowButton("")
        btn_add_alias.setObjectName("AddInlineButton")
        # Size handled by QSS relative to icon
        btn_add_alias.clicked.connect(self._add_alias)
        h_alias.addWidget(btn_add_alias)
        layout.addLayout(h_alias)
        
        self.list_aliases = QListWidget()
        self.list_aliases.setObjectName("ArtistSubList")
        self.list_aliases.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_aliases.customContextMenuRequested.connect(self._show_alias_menu)
        layout.addWidget(self.list_aliases)
        
        # Membership
        h_member = QHBoxLayout()
        self.lbl_member = QLabel("MEMBERS")
        self.lbl_member.setObjectName("DialogFieldLabel")
        h_member.addWidget(self.lbl_member)
        
        h_member.addStretch()
        
        self.btn_add_member = GlowButton("")
        self.btn_add_member.setObjectName("AddInlineButton")
        # Size handled by QSS
        self.btn_add_member.clicked.connect(self._add_member)
        h_member.addWidget(self.btn_add_member)
        
        layout.addLayout(h_member)
        
        self.list_members = QListWidget()
        self.list_members.setObjectName("ArtistSubList")
        self.list_members.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_members.customContextMenuRequested.connect(self._show_member_menu)
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
            
        # Aliases
        self.list_aliases.clear()
        for alias_id, alias_name in self.repo.get_aliases(self.artist.contributor_id):
            item = QListWidgetItem(alias_name)
            item.setData(Qt.ItemDataRole.UserRole, alias_id)
            self.list_aliases.addItem(item)
            
        # Memberships
        self.list_members.clear()
        if self.artist.type == "group":
            members = self.repo.get_members(self.artist.contributor_id)
        else:
            members = self.repo.get_groups(self.artist.contributor_id)
            
        for m in members:
            item = QListWidgetItem(m.name)
            item.setData(Qt.ItemDataRole.UserRole, m.contributor_id)
            self.list_members.addItem(item)

    def _on_type_toggled(self, new_type):
        """Update local model and refresh context labels."""
        if self.artist.type == new_type:
            return
        self.artist.type = new_type
        self._refresh_data()

    def _add_alias(self):
        # UNIFY: Use an editable combo so user can either type a new name
        # OR pick an existing artist to "claim" them as an alias (merging them).
        diag = QDialog(self)
        diag.setWindowTitle("Add Alias")
        diag.setFixedSize(380, 160)
        
        vbox = QVBoxLayout(diag)
        lbl = QLabel("ENTER ALIAS OR SELECT EXISTING ARTIST")
        lbl.setObjectName("DialogFieldLabel")
        vbox.addWidget(lbl)
        
        cmb = GlowComboBox()
        cmb.setEditable(True)
        cmb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Populate with existing artists to help "claiming" identities
        all_artists = self.repo.search("")
        for a in all_artists:
            # Filter: Strict Type Matching
            # "Groups shouldn't even be in that list" when editing a Person.
            if a.contributor_id != self.artist.contributor_id and a.type == self.artist.type:
                cmb.addItem(a.name, a.contributor_id)
        cmb.clearEditText()
        vbox.addWidget(cmb)
        
        vbox.addStretch()
        btns = QHBoxLayout()
        btn_cancel = GlowButton("Cancel")
        btn_cancel.clicked.connect(diag.reject)
        btn_add = GlowButton("ADD")
        btn_add.setObjectName("Primary")
        btn_add.btn.setDefault(True) # Enable Enter Key
        btn_add.clicked.connect(diag.accept)
        
        # Connect Return Key from Line Edit
        cmb.lineEdit().returnPressed.connect(diag.accept)
        
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_add)
        vbox.addLayout(btns)
        
        cmb.setFocus()
        
        if diag.exec():
            name = cmb.currentText().strip()
            if name:
                conflict_id, msg = self.repo.validate_identity(name, exclude_id=self.artist.contributor_id)
                if conflict_id:
                    # Smart Linking Logic:
                    # 1. Tracing the "Real" Owner
                    # If 'name' is an alias for someone else, we want to merge into THAT owner.
                    # e.g. Adding "Sasha Fierce" (owned by Beyonce) to "Queen B" -> Merge Queen B into Beyonce.
                    
                    real_owner_id = conflict_id
                    
                    # Check if conflict_id is actually the same as self (already owned).
                    # validate_identity returns conflict ID which IS the owner ID for aliases.
                    if real_owner_id == self.artist.contributor_id:
                         # It's already yours, do nothing.
                         cmb.clearEditText()
                         return

                    # Proceed with Auto-Merge Logic
                    # SAFETY CHECK: Do types match?
                    real_owner = self.repo.get_by_id(real_owner_id)
                    if real_owner and real_owner.type != self.artist.type:
                         QMessageBox.warning(self, "Type Mismatch", 
                                           f"Cannot auto-merge '{self.artist.name}' ({self.artist.type}) into '{real_owner.name}' ({real_owner.type}).\n\n"
                                           "Please resolve this manually.")
                         cmb.clearEditText()
                         return

                    # DECISION: Absorb or Consolidate?
                    # If the name we typed IS the Primary Name of the other artist, we "Eat" them (Absorb).
                    # If the name we typed is just an ALIAS of the other artist, we "Join" them (Consolidate).
                    
                    is_absorbing = (name.lower() == real_owner.name.lower())
                    
                    if is_absorbing:
                        # Absorb: Merge THE OTHER GUY into ME.
                        if self.repo.merge(real_owner_id, self.artist.contributor_id):
                            from src.core import logger
                            logger.info(f"Identity Absorbed: '{real_owner.name}' merged into '{self.artist.name}'.")
                            self._refresh_data() # I am still alive, just richer.
                            cmb.clearEditText()
                        else:
                            QMessageBox.warning(self, "Error", "Failed to absorb identity.")
                    else:
                        # Consolidate: Merge ME into THEM.
                        if self.repo.merge(self.artist.contributor_id, real_owner_id):
                            # CRITICAL: We just merged OURSELF into someone else.
                            # Signal merge (Code 3) to prompt UI refresh of the NEW ID.
                            self.merged_target = real_owner
                            self.done(3)
                            
                            from src.core import logger
                            logger.info(f"Identity Consolidated: '{self.artist.name}' merged into '{real_owner.name}'.")
                        else:
                            QMessageBox.warning(self, "Error", "Failed to link identities.")
                    return

                self.repo.add_alias(self.artist.contributor_id, name)
                self._refresh_data()
                cmb.clearEditText()

    def _show_alias_menu(self, pos):
        item = self.list_aliases.itemAt(pos)
        if not item: return
        alias_id = item.data(Qt.ItemDataRole.UserRole)
        alias_name = item.text()
        
        menu = QMenu(self)
        
        promote_act = QAction("Set as Primary", self)
        promote_act.triggered.connect(lambda: self._promote_alias(alias_id, alias_name))
        menu.addAction(promote_act)
        
        menu.addSeparator()

        edit_act = QAction("Rename", self)
        edit_act.triggered.connect(lambda: self._edit_alias(alias_id, alias_name))
        menu.addAction(edit_act)
        
        del_act = QAction("Delete Alias", self)
        del_act.triggered.connect(lambda: self._confirm_delete_alias(alias_id, alias_name))
        menu.addAction(del_act)
        menu.exec(self.list_aliases.mapToGlobal(pos))

    def _confirm_delete_alias(self, alias_id, name):
        if QMessageBox.question(self, "Remove Alias", f"Are you sure you want to remove the alias '{name}'?") == QMessageBox.StandardButton.Yes:
            if self.repo.delete_alias(alias_id):
                self._refresh_data()

    def _promote_alias(self, alias_id, name):
        msg = f"This will swap the primary identity '{self.artist.name}' with the alias '{name}'.\n\n"
        msg += f"'{name}' will become the MASTER name for all songs, and '{self.artist.name}' will be kept as an alias.\n\n"
        msg += "Proceed with this Hot Swap?"
        
        if QMessageBox.question(self, "Promote to Primary", msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.repo.promote_alias(self.artist.contributor_id, alias_id):
                # We need to reload the whole artist object because the name changed
                self.artist = self.repo.get_by_id(self.artist.contributor_id)
                self.setWindowTitle(f"Manager: {self.artist.name}")
                self._refresh_data()

    def _edit_alias(self, alias_id, old_name):
        diag = ArtistCreatorDialog(initial_name=old_name, button_text="UPDATE", parent=self)
        diag.setWindowTitle("Rename Alias")
        diag.radio_person.hide(); diag.radio_group.hide()
        if diag.exec():
            new_name, _ = diag.get_data()
            if new_name and new_name != old_name:
                self.repo.update_alias(alias_id, new_name)
                self._refresh_data()

    def _delete_alias(self, alias_id):
        # Unused now, replaced by confirm version
        pass

    def _add_member(self):
        # If I am a Group, I want to add Persons.
        # If I am a Person, I want to add Groups.
        target_type = "person" if self.radio_group.isChecked() else "group"
        
        # Exclude self and current members
        exclude = {self.artist.contributor_id}
        for i in range(self.list_members.count()):
            exclude.add(self.list_members.item(i).data(Qt.ItemDataRole.UserRole))

        diag = ArtistPickerDialog(self.repo, filter_type=target_type, exclude_ids=exclude, parent=self)
        if diag.exec():
            result = diag.get_selected()
            if result:
                targets = result if isinstance(result, list) else [result]
                
                for selected in targets:
                    if self.radio_group.isChecked():
                        self.repo.add_member(self.artist.contributor_id, selected.contributor_id)
                    else:
                        self.repo.add_member(selected.contributor_id, self.artist.contributor_id)
                self._refresh_data()

    def _show_member_menu(self, pos):
        item = self.list_members.itemAt(pos)
        if not item: return
        other_id = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        remove_act = QAction("Remove Link", self)
        remove_act.triggered.connect(lambda: self._remove_member(other_id))
        menu.addAction(remove_act)
        menu.exec(self.list_members.mapToGlobal(pos))

    def _remove_member(self, other_id):
        # Get name for the prompt
        item = self.list_members.currentItem()
        name = item.text() if item else "this artist"
        
        if QMessageBox.question(self, "Remove Relationship", f"Are you sure you want to remove the link between {self.artist.name} and {name}?") == QMessageBox.StandardButton.Yes:
            if self.radio_group.isChecked():
                self.repo.remove_member(self.artist.contributor_id, other_id)
            else:
                self.repo.remove_member(other_id, self.artist.contributor_id)
            self._refresh_data()

    def _save(self):
        new_name = self.txt_name.text().strip()
        if not new_name: return
        
        new_type = "group" if self.radio_group.isChecked() else "person"
        
        # Validation for name change
        if new_name != self.artist.name:
            conflict_id, msg = self.repo.validate_identity(new_name, exclude_id=self.artist.contributor_id)
            if conflict_id:
                # HUMAN RESOLVER: Just ask the simple question
                usage_count = self.repo.get_usage_count(self.artist.contributor_id)
                resolver = IdentityCollisionDialog(
                    target_name=new_name,
                    song_count=usage_count,
                    has_context_song=(self.context_song is not None),
                    parent=self
                )

                
                res = resolver.exec()
                if res == 0: # Cancel
                    return

                if res == 1: # Fix Typo (Clean Merge)
                    if self.repo.merge(self.artist.contributor_id, conflict_id, create_alias=False):
                        self.done(3) # Signal 3: Data Changed (Sync Required)
                        return
                    else:
                        QMessageBox.warning(self, "Error", "Merge failed.")
                        return


                if res == 3 and self.context_song: # Fix This Song Only
                    if self.repo.swap_song_contributor(self.context_song.source_id, self.artist.contributor_id, conflict_id):
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
                count = len(self.repo.get_members(self.artist.contributor_id))
                relation = "member"
            else:
                # Losing 'Parents'
                count = len(self.repo.get_groups(self.artist.contributor_id))
                relation = "group membership"

            if count > 0:
                msg = f"Changing this {self.original_type.capitalize()} to a {new_type.capitalize()} will remove {count} existing {relation}(s). Are you sure?"
                if QMessageBox.warning(self, "Confirm Type Change", msg, 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
        
        self.artist.name = new_name
        self.artist.sort_name = self.txt_sort.text().strip()
        self.artist.type = new_type
        
        if self.repo.update(self.artist):
            self.done(3) # Signal 3: Data Changed (Sync Required)
        else:
            QMessageBox.warning(self, "Error", "Failed to save artist changes.")

