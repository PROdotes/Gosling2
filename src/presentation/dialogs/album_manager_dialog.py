from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QMessageBox, QComboBox, QWidget, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton
from .publisher_manager_dialog import PublisherPickerWidget

class AlbumManagerDialog(QDialog):
    """
    T-46: Proper Album Editor (The Inspector)
    Allows searching existing albums or creating new ones with proper hierarchy.
    """
    
    # Returns the selected/created Album ID and Name
    album_selected = pyqtSignal(int, str) 
    save_and_select_requested = pyqtSignal(int, str)
    album_deleted = pyqtSignal(int) # Emitted with ID before deletion starts
    def __init__(self, album_repository, initial_data=None, parent=None, staged_deletions=None):
        super().__init__(parent)
        self.album_repo = album_repository
        self.initial_data = initial_data or {}
        self.selected_album = None
        self.staged_deletions = staged_deletions or set()
        self.editing_album = None # Track if we are editing vs creating
        self.selected_pub_id = None # Track selected publisher ID
        self.selected_pub_name = "" # Track selected publisher Name
        
        self.setWindowTitle("Album Manager")
        self.setFixedSize(900, 500) # Increased width for the 'Sidecar'
        self.setModal(True)
        
        # Styling moved to theme.qss
        self.setObjectName("AlbumManagerDialog")
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. Header (Mode Switcher)
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("SELECT ALBUM")
        self.lbl_title.setObjectName("DialogHeaderTitle")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        self.btn_mode_toggle = GlowButton("Create New (+)")
        self.btn_mode_toggle.clicked.connect(self._toggle_mode)
        header_layout.addWidget(self.btn_mode_toggle)
        
        layout.addLayout(header_layout)
        
        # 2. Stacked Content (Search vs Create)
        self.stack = QStackedWidget()
        
        # --- PAGE 1: SEARCH ---
        self.page_search = QWidget()
        search_layout = QVBoxLayout(self.page_search)
        search_layout.setContentsMargins(0,0,0,0)
        
        # Top Row: Search + Filter
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0,0,0,0)
        
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Search Albums...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        top_bar.addWidget(self.txt_search, 1) # Expand
        
        self.chk_empty = QCheckBox("Empty Only")
        self.chk_empty.setToolTip("Show only albums with 0 songs")
        # Refresh on toggle (pass current search text)
        self.chk_empty.stateChanged.connect(lambda: self._refresh_list(self.txt_search.text()))
        top_bar.addWidget(self.chk_empty)
        
        search_layout.addLayout(top_bar)
        
        self.list_albums = QListWidget()
        self.list_albums.setObjectName("AlbumManagerList") # Added for QSS styling
        self.list_albums.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_albums.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_albums.customContextMenuRequested.connect(self._show_context_menu)
        self.list_albums.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_albums.itemSelectionChanged.connect(self._on_selection_changed)
        search_layout.addWidget(self.list_albums)
        
        self.stack.addWidget(self.page_search)
        
        # --- PAGE 2: CREATE/EDIT ---
        self.page_create = QWidget()
        page_h_layout = QHBoxLayout(self.page_create)
        page_h_layout.setContentsMargins(0,0,0,0)
        page_h_layout.setSpacing(0)
        
        # Left Side: Form Container
        form_container = QWidget()
        create_layout = QVBoxLayout(form_container)
        create_layout.setContentsMargins(0,0,0,0)
        create_layout.setSpacing(15)
        
        # Form Box
        form_frame = QFrame()
        form_frame.setObjectName("DialogFormContainer")
        form_layout = QVBoxLayout(form_frame)
        
        self.inp_title = self._add_field(form_layout, "Album Title *")
        self.inp_artist = self._add_field(form_layout, "Album Artist")
        self.inp_year = self._add_field(form_layout, "Release Year")
        
        # Publisher Picker (T-69)
        lbl_pub = QLabel("PUBLISHER")
        lbl_pub.setObjectName("DialogFieldLabel")
        self.btn_pub_picker = GlowButton("(None)")
        self.btn_pub_picker.setObjectName("PublisherPickerButton")
        self.btn_pub_picker.clicked.connect(self._open_publisher_manager)
        form_layout.addWidget(lbl_pub)
        form_layout.addWidget(self.btn_pub_picker)
        
        # Type Dropdown
        lbl_type = QLabel("Release Type")
        lbl_type.setObjectName("DialogFieldLabel")
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Album", "EP", "Single", "Compilation", "Anthology"])
        
        form_layout.addWidget(lbl_type)
        form_layout.addWidget(self.cmb_type)
        
        create_layout.addWidget(form_frame)
        create_layout.addStretch()
        
        # Right Side: SIDECAR (T-69: Integrated Picker)
        from ...data.repositories.publisher_repository import PublisherRepository
        pub_repo = PublisherRepository(self.album_repo.db_path)
        
        self.pub_picker = PublisherPickerWidget(pub_repo, self)
        self.pub_picker.publisher_selected.connect(self._on_publisher_picked)
        self.pub_picker.hide() # Hidden until button clicked
        
        # Assemble Page 2
        page_h_layout.addWidget(form_container, 1) 
        page_h_layout.addWidget(self.pub_picker, 1) # Equal split or adjusted ratio
        
        self.stack.addWidget(self.page_create)
        
        layout.addWidget(self.stack)
        
        # 3. Footer actions
        footer = QHBoxLayout()
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = GlowButton("Select")
        self.btn_confirm.setObjectName("Primary")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)
        
        self.btn_save_confirm = GlowButton("Select & Save")
        self.btn_save_confirm.setObjectName("Primary")
        self.btn_save_confirm.setEnabled(False)
        self.btn_save_confirm.clicked.connect(self._on_save_confirm_clicked)
        
        footer.addWidget(self.btn_cancel)
        footer.addStretch()
        footer.addWidget(self.btn_save_confirm)
        footer.addWidget(self.btn_confirm)
        
        layout.addLayout(footer)
        
        # Initial Population & Autoselect
        title_to_find = self.initial_data.get('title', '')
        if title_to_find:
             self.txt_search.setText(title_to_find)
        else:
             self._refresh_list()

    def _add_field(self, layout, label_text):
        lbl = QLabel(label_text.upper())
        lbl.setObjectName("DialogFieldLabel")
        inp = GlowLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(inp)
        return inp

    def _toggle_mode(self, checked=False, edit_album=None):
        if self.stack.currentIndex() == 0 or edit_album:
            # === SWITCH TO EDITOR MODE ===
            self.editing_album = edit_album
            search_text = self.txt_search.text().strip()
            
            self.stack.setCurrentIndex(1)
            self.btn_mode_toggle.setText("Back to Search")
            
            if self.editing_album:
                self.lbl_title.setText("EDIT ALBUM")
                self.btn_confirm.setText("Update & Select")
                self.btn_confirm.setEnabled(True)
                self.btn_save_confirm.setText("Update & Save")
                self.btn_save_confirm.setEnabled(True)
                
                # Fill from Album Object
                self.inp_title.setText(self.editing_album.title or "")
                self.inp_artist.setText(self.editing_album.album_artist or "")
                self.inp_year.setText(str(self.editing_album.release_year) if self.editing_album.release_year else "")
                self.cmb_type.setCurrentText(self.editing_album.album_type or "Album")
                
                # Fetch Publisher
                pub_name = self.album_repo.get_publisher(self.editing_album.album_id)
                self.selected_pub_name = pub_name or ""
                self.btn_pub_picker.setText(pub_name if pub_name else "(None)")
            else:
                self.lbl_title.setText("NEW ALBUM")
                self.btn_confirm.setText("Create & Select")
                self.btn_confirm.setEnabled(True)
                self.btn_save_confirm.setText("Create & Save")
                self.btn_save_confirm.setEnabled(True)
                
                # Smart Populate
                target_title = search_text or self.initial_data.get('title', '')
                target_artist = self.initial_data.get('artist', '')
                target_year = self.initial_data.get('year', '')
                target_publisher = self.initial_data.get('publisher', '')

                self.inp_title.setText(target_title)
                self.inp_artist.setText(target_artist)
                self.inp_year.setText(str(target_year) if target_year else "")
                self.selected_pub_name = target_publisher
                self.btn_pub_picker.setText(target_publisher if target_publisher else "(None)")

            # Clear search
            self.txt_search.clear()
            self.inp_title.setFocus()
        else:
             # Switch back to Search
            self.stack.setCurrentIndex(0)
            self.editing_album = None
            self.lbl_title.setText("SELECT ALBUM")
            self.btn_mode_toggle.setText("Create New (+)")
            self.btn_confirm.setText("Select")
            self.btn_save_confirm.setText("Select & Save")
            self._on_selection_changed() # Re-validate button

    def _show_context_menu(self, pos):
        selected_items = self.list_albums.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu(self)
        
        # Edit Action
        action_edit = QAction("Edit Album Details", self)
        action_edit.triggered.connect(lambda: self._edit_selected_album(selected_items[0]))
        menu.addAction(action_edit)
        
        menu.addSeparator()

        # Determine label based on count
        label = f"Delete {len(selected_items)} Albums" if len(selected_items) > 1 else "Delete Album"
        
        action_delete = QAction(label, self)
        action_delete.triggered.connect(lambda: self._delete_albums(selected_items))
        menu.addAction(action_delete)
        
        menu.exec(self.list_albums.mapToGlobal(pos))

    def _edit_selected_album(self, item):
        alb_id = item.data(Qt.ItemDataRole.UserRole)
        alb = self.album_repo.get_by_id(alb_id)
        if alb:
            self._toggle_mode(edit_album=alb)

    def _delete_albums(self, items):
        if not items: return
        
        count = len(items)
        total_songs = 0
        album_ids = []
        
        for item in items:
            alb_id = item.data(Qt.ItemDataRole.UserRole)
            album_ids.append(alb_id)
            total_songs += self.album_repo.get_song_count(alb_id)

        # Build Message
        if count == 1:
            name = items[0].data(Qt.ItemDataRole.UserRole + 1)
            if total_songs > 0:
                msg = f"Album contains {total_songs} songs.\nDeleting it will UNLINK them.\n\nAre you sure?"
                icon = QMessageBox.Icon.Warning
            else:
                msg = f"Are you sure you want to delete '{name}'?"
                icon = QMessageBox.Icon.Question
        else:
            if total_songs > 0:
                msg = f"You are about to delete {count} albums.\nWarning: {total_songs} song links will be REMOVED.\n\nAre you sure?"
                icon = QMessageBox.Icon.Warning
            else:
                msg = f"Are you sure you want to delete {count} empty albums?"
                icon = QMessageBox.Icon.Question

        reply = QMessageBox.question(
            self, 
            "Confirm Batch Delete", 
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # NON-LAZY UX: We do NOT delete from DB yet.
            # We just signal the intent so the Side Panel can stage it.
            for alb_id in album_ids:
                self.staged_deletions.add(alb_id) # Immediate local update
                self.album_deleted.emit(alb_id)
            
            # Refresh using current search term
            self._on_search_text_changed(self.txt_search.text())

    def _refresh_list(self, query=""):
        self.list_albums.clear()
        
        # Determine filter state
        empty_only = False
        if hasattr(self, 'chk_empty'): # Safety check
            empty_only = self.chk_empty.isChecked()

        if self.album_repo:
             results = self.album_repo.search(query, empty_only=empty_only)
        else:
             results = [] 
        
        if not results and not query:
             # Show 'recent' or 'all'?
             pass
             
        target_title = self.initial_data.get('title', '').strip().lower()

        for alb in results:
            # Ghosting: Skip albums staged for deletion in the Side Panel
            if alb.album_id in self.staged_deletions:
                continue
                
            # Replaced alb.id with alb.album_id, alb.year with alb.release_year, alb.artist with alb.album_artist
            # Format: (Year) Title - Artist (N songs)
            year_part = f"({alb.release_year}) " if alb.release_year else ""
            artist_part = f" - {alb.album_artist}" if alb.album_artist else ""
            
            s_label = "song" if alb.song_count == 1 else "songs"
            count_part = f" ({alb.song_count} {s_label})"

            display_str = f"{year_part}{alb.title}{artist_part}{count_part}"
            
            item = QListWidgetItem(display_str)
            item.setData(Qt.ItemDataRole.UserRole, alb.album_id)
            # Store raw title to avoid parsing the formatted string later
            item.setData(Qt.ItemDataRole.UserRole + 1, alb.title) 
            self.list_albums.addItem(item)
            
            # Autoselect if exact title match
            if target_title and alb.title.strip().lower() == target_title:
                item.setSelected(True)
                self.list_albums.setCurrentItem(item)
                self.list_albums.scrollToItem(item)
            
    def _on_search_text_changed(self, text):
        self._refresh_list(text)
        
    def _on_selection_changed(self):
        has_sel = len(self.list_albums.selectedItems()) > 0
        self.btn_confirm.setEnabled(has_sel)
        self.btn_save_confirm.setEnabled(has_sel)
        
    def _on_item_double_clicked(self, item):
        self._edit_selected_album(item)
        
    def _on_confirm_clicked(self, checked=False):
        if self.stack.currentIndex() == 0:
            self._confirm_selection(save_after=False)
        else:
            self._save_editor_and_select(save_after=False)

    def _on_save_confirm_clicked(self, checked=False):
        if self.stack.currentIndex() == 0:
            self._confirm_selection(save_after=True)
        else:
            self._save_editor_and_select(save_after=True)
            
    def _confirm_selection(self, save_after=False):
        items = self.list_albums.selectedItems()
        if not items: return
        
        alb_id = items[0].data(Qt.ItemDataRole.UserRole)
        alb_name = items[0].data(Qt.ItemDataRole.UserRole + 1)
        
        if save_after:
             self.save_and_select_requested.emit(alb_id, alb_name)
        else:
             self.album_selected.emit(alb_id, alb_name)
             
        self.accept()
        
    def _open_publisher_manager(self):
        """Toggle sidecar instead of opening a new window (Inception Reduction)."""
        if self.pub_picker.isVisible():
            self.pub_picker.hide()
        else:
            self.pub_picker.show()
            self.pub_picker.txt_search.setFocus()
            self.pub_picker._refresh_list() # Ensure current data

    def _on_publisher_picked(self, pub_id, pub_name):
        self.selected_pub_id = pub_id
        self.selected_pub_name = pub_name
        self.btn_pub_picker.setText(pub_name)

    def _save_editor_and_select(self, save_after=False):
        # Validate
        title = self.inp_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Album Title is required.")
            return
            
        try:
            # Parse Year
            year_val = self.inp_year.text().strip()
            year_int = int(year_val) if year_val and year_val.isdigit() else None
            artist_val = self.inp_artist.text().strip()
            type_val = self.cmb_type.currentText()

            if self.editing_album:
                # UPDATE MODE
                self.editing_album.title = title
                self.editing_album.album_artist = artist_val
                self.editing_album.release_year = year_int
                self.editing_album.album_type = type_val
                
                self.album_repo.update(self.editing_album)
                album_obj = self.editing_album
            else:
                # CREATE MODE
                album_obj, created = self.album_repo.get_or_create(
                    title=title,
                    album_artist=artist_val,
                    release_year=year_int
                )
                album_obj.album_type = type_val
                self.album_repo.update(album_obj)

            # Link/Unlink Publisher (Atomic on Update)
            self.album_repo.set_publisher(album_obj.album_id, self.selected_pub_name)
            
            if save_after:
                 self.save_and_select_requested.emit(album_obj.album_id, album_obj.title)
            else:
                 self.album_selected.emit(album_obj.album_id, album_obj.title)
            self.accept()
            
        except Exception as e:
            from src.core import logger
            logger.error(f"Could not save album: {e}")
            QMessageBox.critical(self, "Database Error", f"Could not save album: {e}")
