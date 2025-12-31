from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QSplitter,
    QFrame, QMessageBox, QComboBox, QWidget, QMenu, QCheckBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox
from .publisher_manager_dialog import PublisherPickerWidget
from ...data.repositories.publisher_repository import PublisherRepository

class AlbumManagerDialog(QDialog):
    """
    T-46: Proper Album Editor (The Workstation)
    A 4-pane console for managing albums, their metadata, and publishers.
    Layout: [Context (Songs)] | [Vault (Albums)] | [Inspector (Edit)] | [Sidecar (Publisher)]
    
    Refactor T-63: Layout split into HBox[MainContainer, Sidecar] to prevent button jumping.
    """
    
    # Returns the selected/created Album ID and Name
    album_selected = pyqtSignal(int, str) 
    save_and_select_requested = pyqtSignal(int, str)
    album_deleted = pyqtSignal(int)
    
    # Geometry (The Workstation Dimensions)
    BASE_WIDTH = 950
    BASE_HEIGHT = 650
    SIDECAR_WIDTH = 300
    EXPANDED_WIDTH = BASE_WIDTH + SIDECAR_WIDTH
    PANE_MIN_WIDTH = 250
    
    def __init__(self, album_repository, initial_data=None, parent=None, staged_deletions=None):
        super().__init__(parent)
        self.album_repo = album_repository
        self.initial_data = initial_data or {}
        self.staged_deletions = staged_deletions or set()
        
        # Determine if the initial title is valid (exists in DB)
        aid = self.initial_data.get('album_id')
        if aid:
             fresh_album = self.album_repo.get_by_id(aid)
             if fresh_album:
                  self.initial_data['title'] = fresh_album.title
                  self.current_album = fresh_album

        target = self.initial_data.get('title', '')
        if target:
             hits = self.album_repo.search(target)

        # State
        if not hasattr(self, 'current_album'):
            self.current_album = None # The album object currently loaded in Inspector
        self.is_creating_new = False # Flag for "Create New" mode
        self.selected_pub_name = "" 
        
        self.setWindowTitle("Album Manager Workstation")
        self.setMinimumSize(self.BASE_WIDTH, self.BASE_HEIGHT)
        self.setModal(True)
        self.setObjectName("AlbumManagerDialog")
        
        self._init_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        # T-83: Auto-Focus Publisher if requested (The Jump)
        if self.initial_data.get('focus_publisher'):
            # Defer slightly to ensure layout is done
            QTimer.singleShot(100, self._trigger_publisher_jump)
            
    def _trigger_publisher_jump(self):
        if hasattr(self, 'btn_pub_trigger'):
            self.btn_pub_trigger.setFocus()
            # Optional: auto-expand the sidecar? 
            # If we click it, it expands. User said "Selects the publisher".
            self.btn_pub_trigger.click()
        
    def _init_ui(self):
        # ROOT LAYOUT: HBox [MainContainer] [SidecarContainer]
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0,0,0,0)
        self.root_layout.setSpacing(0)
        
        # --- LEFT: MAIN CONTAINER ---
        self.main_container = QFrame()
        self.main_container.setMinimumWidth(self.BASE_WIDTH)
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0,0,0,0)
        
        # --- TOP HEADER ---
        header = QFrame()
        header.setFixedHeight(50)
        header.setMaximumWidth(self.BASE_WIDTH) # Lock width to prevent jump
        header.setObjectName("DialogHeader") 
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20,0,20,0)
        header_layout.setSpacing(10) 
        
        self.lbl_title = QLabel("ALBUM CONSOLE")
        self.lbl_title.setObjectName("DialogHeaderTitle") 
        self.lbl_title.setFixedWidth(200) # Compact fixed width
        header_layout.addWidget(self.lbl_title)
        
        # Context Display (Song currently being worked on)
        song_display = self.initial_data.get('song_display')
        if song_display:
            parts = song_display.split(" - ", 1)
            sep = QLabel("|")
            sep.setObjectName("HeaderContextSep")
            header_layout.addWidget(sep)
            
            if len(parts) == 2:
                artist, title = parts
                lbl_artist = QLabel(artist)
                lbl_artist.setObjectName("HeaderArtistLabel")
                header_layout.addWidget(lbl_artist)
                lbl_dash = QLabel("-") 
                lbl_dash.setObjectName("HeaderDash")
                header_layout.addWidget(lbl_dash)
                lbl_title_song = QLabel(title)
                lbl_title_song.setObjectName("HeaderTitleLabel") 
                header_layout.addWidget(lbl_title_song)
            else:
                lbl_full = QLabel(song_display)
                lbl_full.setObjectName("HeaderTitleLabel")
                header_layout.addWidget(lbl_full)

        header_layout.addStretch()
        
        self.btn_create_new = GlowButton("Create New Album (+)")
        self.btn_create_new.clicked.connect(self._toggle_create_mode)
        header_layout.addWidget(self.btn_create_new)
        
        main_layout.addWidget(header)
        
        # --- MAIN SPLITTER (The Workstation) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(2)
        
        # 1. PANE Z: Context (Songs)
        self.pane_context = self._build_context_pane()
        self.pane_context.setMinimumWidth(self.PANE_MIN_WIDTH)
        self.splitter.addWidget(self.pane_context)
        
        # 2. PANE A: Vault (Albums)
        self.pane_vault = self._build_vault_pane()
        self.pane_vault.setMinimumWidth(self.PANE_MIN_WIDTH)
        self.splitter.addWidget(self.pane_vault)
        
        # 3. PANE B: Inspector (Editor)
        self.pane_inspector = self._build_inspector_pane()
        self.splitter.addWidget(self.pane_inspector)
        
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(self.splitter)
        
        # --- FOOTER ---
        footer = QFrame()
        footer.setObjectName("DialogFooter")
        footer.setFixedHeight(60)
        footer.setMaximumWidth(self.BASE_WIDTH) # Lock width to prevent jump
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20,10,20,10)
        footer_layout.setSpacing(10) 
        
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save_inspector = GlowButton("Save Changes")
        self.btn_save_inspector.setObjectName("Primary")
        self.btn_save_inspector.setEnabled(False) # Initially disabled
        self.btn_save_inspector.clicked.connect(self._save_inspector)

        self.btn_select = GlowButton("Accept Changes")
        self.btn_select.setObjectName("Primary")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self._on_select_clicked)
        
        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_save_inspector)
        footer_layout.addWidget(self.btn_select)
        
        main_layout.addWidget(footer)
        
        # Add Main to Root
        self.root_layout.addWidget(self.main_container, 1) # Stretch factor 1
        
        # --- RIGHT: SIDECAR CONTAINER ---
        self.pane_sidecar = self._build_sidecar_pane()
        self.pane_sidecar.hide() # Hidden by default
        self.root_layout.addWidget(self.pane_sidecar, 0) # Fixed width
        
        
        # Initial Load
        title_to_find = self.initial_data.get('title', '')
        if title_to_find:
            self.txt_search.setText(title_to_find)
        else:
            self._refresh_vault()

    # --- PANE BUILDERS ---
    
    def _build_context_pane(self):
        container = QFrame()
        container.setObjectName("DialogContextPane")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # Header
        lbl = QLabel("  ALBUM CONTEXT")
        lbl.setFixedHeight(30)
        lbl.setObjectName("PaneHeaderLabel")
        layout.addWidget(lbl)
        
        self.list_context = QListWidget()
        self.list_context.setObjectName("DialogContextList")
        self.list_context.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Non-interactive
        layout.addWidget(self.list_context)
        
        return container

    def _build_vault_pane(self):
        container = QFrame()
        container.setObjectName("DialogVault")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        # Search Bar Area
        search_box = QFrame()
        search_box.setObjectName("VaultSearchBox")
        sb_layout = QVBoxLayout(search_box)
        sb_layout.setContentsMargins(0,0,0,0)
        
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Search Albums...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        sb_layout.addWidget(self.txt_search)
        
        layout.addWidget(search_box)
        
        self.list_vault = QListWidget()
        self.list_vault.setObjectName("DialogVaultList") # Will inherit QListWidget styles
        self.list_vault.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_vault.customContextMenuRequested.connect(self._show_vault_context_menu)
        self.list_vault.itemClicked.connect(self._on_vault_item_clicked)
        self.list_vault.itemDoubleClicked.connect(self._on_select_clicked)
        
        layout.addWidget(self.list_vault)
        return container

    def _build_inspector_pane(self):
        container = QFrame()
        container.setObjectName("DialogInspector")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(0)  # Zero spacing - manual control like side panel
        
        # Form Fields (use FieldLabel for tight label-to-input proximity)
        self.inp_title = self._add_field(layout, "Album Title *")
        layout.addSpacing(12)  # Consistent gap between field groups
        self.inp_artist = self._add_field(layout, "Album Artist")
        layout.addSpacing(12)
        self.inp_year = self._add_field(layout, "Release Year")
        layout.addSpacing(12)
        
        # Publisher Trigger
        lbl_pub = QLabel("PUBLISHER")
        lbl_pub.setObjectName("FieldLabel")  # Use same class as side panel
        layout.addWidget(lbl_pub)
        
        self.btn_pub_trigger = GlowButton("(None)")
        self.btn_pub_trigger.setObjectName("PublisherPickerButton")
        self.btn_pub_trigger.clicked.connect(self._toggle_sidecar)
        layout.addWidget(self.btn_pub_trigger)
        layout.addSpacing(12)  # Consistent gap between field groups
        
        # Type Dropdown
        lbl_type = QLabel("RELEASE TYPE")
        lbl_type.setObjectName("FieldLabel")  # Use same class as side panel
        layout.addWidget(lbl_type)
        
        self.cmb_type = GlowComboBox()
        self.cmb_type.setEditable(False)  # Fixed list, not searchable
        self.cmb_type.addItems(["Album", "EP", "Single", "Compilation", "Anthology"])
        layout.addWidget(self.cmb_type)
        
        layout.addStretch()
        
        # Disable by default
        container.setEnabled(False)
        
        return container
        
    def _build_sidecar_pane(self):
        container = QFrame()
        container.setObjectName("PublisherSidecar")
        container.setFixedWidth(self.SIDECAR_WIDTH)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        # from ...data.repositories.publisher_repository import PublisherRepository
        pub_repo = PublisherRepository(self.album_repo.db_path)
        
        self.publisher_picker = PublisherPickerWidget(pub_repo, self)
        self.publisher_picker.publisher_selected.connect(self._on_publisher_selected)
        
        layout.addWidget(self.publisher_picker)
        
        return container

    def _add_field(self, layout, label):
        lbl = QLabel(label.upper())
        lbl.setObjectName("FieldLabel")  # Same as side panel for tight proximity
        inp = GlowLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(inp)
        return inp

    # --- LOGIC ---

    def _toggle_create_mode(self):
        if self.is_creating_new:
            self._cancel_create_new()
        else:
            self._start_create_new()

    def _start_create_new(self):
        # Save state
        curr = self.list_vault.currentItem()
        self.last_selected_id = curr.data(Qt.ItemDataRole.UserRole) if curr else None
        
        self.is_creating_new = True
        self.current_album = None
        self.btn_create_new.setText("Cancel Creating (x)")
        self.btn_create_new.setObjectName("CancelButton") 
        self.btn_create_new.style().unpolish(self.btn_create_new)
        self.btn_create_new.style().polish(self.btn_create_new)
        
        # Clear Selection
        self.list_vault.clearSelection()
        
        # Clear Context
        self.list_context.clear()
        
        # Enable Inspector
        self.pane_inspector.setEnabled(True)
        self.btn_save_inspector.setEnabled(True)
        self.pane_inspector.setProperty("state", "creating")
        self.pane_inspector.style().unpolish(self.pane_inspector)
        self.pane_inspector.style().polish(self.pane_inspector)
        
        # Reset Fields Logic + Ghost Styling
        inputs = [self.inp_title, self.inp_artist, self.inp_year]
        for inp in inputs:
            inp.clear()
            inp.edit.setStyleSheet("color: #666;") # Ghost color (Darker)
            # Disconnect previous temporary slots if any (complex in PyQt, simple approach: unique connection)
            try: inp.edit.textEdited.disconnect(self._ungrey_text)
            except: pass
            inp.edit.textEdited.connect(self._ungrey_text)

        # Smart Fill
        if self.initial_data.get('title'):
            self.inp_title.setText(self.initial_data.get('title'))
        if self.initial_data.get('artist'):
            self.inp_artist.setText(self.initial_data.get('artist'))
        if self.initial_data.get('year'):
            self.inp_year.setText(str(self.initial_data.get('year')))
            
        self.cmb_type.setCurrentText("Single")
        self.btn_pub_trigger.setText("(None)")
        self.selected_pub_name = ""
        
        self.inp_title.setFocus()
        self.btn_select.setEnabled(False) 
        self.lbl_title.setText("CREATING ALBUM")

    def _cancel_create_new(self):
        self.is_creating_new = False
        self.btn_create_new.setText("Create New Album (+)")
        self.btn_create_new.setObjectName("GlowButton") # Reset style
        self.btn_create_new.style().unpolish(self.btn_create_new)
        self.btn_create_new.style().polish(self.btn_create_new)
        
        # Ungrey fields
        inputs = [self.inp_title, self.inp_artist, self.inp_year]
        for inp in inputs:
            inp.edit.setStyleSheet("")
            try: inp.edit.textEdited.disconnect(self._ungrey_text)
            except: pass

        if self.last_selected_id:
            # Restore selection
            self._refresh_vault() # Ensure list is fresh
            # Find item
            for i in range(self.list_vault.count()):
                item = self.list_vault.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.last_selected_id:
                    self.list_vault.setCurrentItem(item)
                    self._on_vault_item_clicked(item)
                    return
        
        # If no previous selection, just disable inspector
        self.pane_inspector.setEnabled(False)
        self.lbl_title.setText("ALBUM CONSOLE")
        
    def _ungrey_text(self):
        sender = self.sender()
        if sender:
            sender.setStyleSheet("")

    def _on_vault_item_clicked(self, item):
        # Reset Create Button if we were creating
        if self.is_creating_new:
             self.is_creating_new = False
             self.btn_create_new.setText("Create New Album (+)")
             # Reset ghost styling
             for inp in [self.inp_title, self.inp_artist, self.inp_year]:
                 inp.edit.setStyleSheet("")
        
        album_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_album = self.album_repo.get_by_id(album_id)
        
        if not self.current_album:
            return
            
        # 1. Populate Inspector
        self.inp_title.setText(self.current_album.title or "")
        
        # Smart Fill for Existing: If DB has no artist, suggest from song context
        db_artist = self.current_album.album_artist
        if not db_artist and self.initial_data.get('artist'):
            db_artist = self.initial_data.get('artist')
        self.inp_artist.setText(db_artist or "")
        # Smart Fill Year
        db_year = self.current_album.release_year
        if not db_year and self.initial_data.get('year'):
            db_year = self.initial_data.get('year')
        self.inp_year.setText(str(db_year) if db_year else "")
        self.cmb_type.setCurrentText(self.current_album.album_type or "Album")
        
        # Publisher
        pub_name = self.album_repo.get_publisher(self.current_album.album_id)
        self.selected_pub_name = pub_name or ""
        self.btn_pub_trigger.setText(pub_name if pub_name else "(None)")
        
        # 2. Populate Context (Songs)
        self._refresh_context(album_id)
        
        # 3. Enable UI
        self.pane_inspector.setEnabled(True)
        self.btn_save_inspector.setEnabled(True)
        self.pane_inspector.setProperty("state", "") # Clear create cue
        self.pane_inspector.style().unpolish(self.pane_inspector)
        self.pane_inspector.style().polish(self.pane_inspector)
        self.btn_select.setEnabled(True)
        self.lbl_title.setText("EDITING ALBUM")

    def _refresh_context(self, album_id):
        self.list_context.clear()
        songs = self.album_repo.get_songs_in_album(album_id)
        
        if not songs:
            item = QListWidgetItem(" (No Songs) ")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_context.addItem(item)
            return

        for song in songs:
            # Format: Track - Title (Artist) or just Title
            display = f"{song['title']}"
            if song['artist'] != 'Unknown':
                 # Only show artist if it differs from album artist? Too complex for now.
                 display += f" - {song['artist']}"
            
            self.list_context.addItem(display)

    def _refresh_vault(self, query=None):
        if query is None:
            query = self.txt_search.text()
            
        self.list_vault.clear()
        results = self.album_repo.search(query)
        
        target_id = None
        if self.current_album:
            target_id = self.current_album.album_id
        elif self.initial_data.get('album_id'):
            # Fallback: If we have an ID but haven't loaded the object yet
            target_id = self.initial_data.get('album_id')
        
        for alb in results:
            if alb.album_id in self.staged_deletions: continue
            
            # Format: (Year) Title [Artist]
            display = f"{alb.title}"
            if alb.release_year: display = f"({alb.release_year}) " + display
            if alb.album_artist: display += f" - {alb.album_artist}"
            
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, alb.album_id)
            self.list_vault.addItem(item)
            
            if target_id and alb.album_id == target_id:
                item.setSelected(True)
                self.list_vault.setCurrentItem(item)
                # Manually trigger the click logic to populate the Inspector!
                self._on_vault_item_clicked(item)

    def _on_search_text_changed(self, text):
        self._refresh_vault(text)
        
    def _toggle_sidecar(self):
        if self.pane_sidecar.isVisible():
            self.pane_sidecar.hide()
            self.setMinimumWidth(self.BASE_WIDTH)
            self.resize(self.BASE_WIDTH, self.height())
        else:
            self.pane_sidecar.show()
            self.setMinimumWidth(self.EXPANDED_WIDTH)
            self.resize(self.EXPANDED_WIDTH, self.height())
            self.publisher_picker._refresh_list()
            self.publisher_picker.select_publisher_by_name(self.selected_pub_name)
            
    def _on_publisher_selected(self, pub_id, pub_name):
        self.selected_pub_name = pub_name
        self.btn_pub_trigger.setText(pub_name)
        # Auto-save publisher? Or wait for save button?
        # Logic says: wait for save button for atomic commit.

    def _save_inspector(self, silent=False):
        # Gather Data
        title = self.inp_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Title cannot be empty")
            return False
            
        artist = self.inp_artist.text().strip()
        year_str = self.inp_year.text().strip()
        year = int(year_str) if year_str.isdigit() else None
        alb_type = self.cmb_type.currentText()
        
        success = False
        try:
            if self.is_creating_new:
                # Create
                album, created = self.album_repo.get_or_create(title, artist, year)
                album.album_type = alb_type
                self.album_repo.update(album)
                self.album_repo.set_publisher(album.album_id, self.selected_pub_name)
                
                self.current_album = album
                self.is_creating_new = False
                
                # Clear search so we see the new item
                self.txt_search.blockSignals(True)
                self.txt_search.clear() 
                self.txt_search.blockSignals(False)
                
                self._refresh_vault() 
                if not silent: 
                    QMessageBox.information(self, "Success", "Album Created")
                success = True
            else:
                # Update
                if not self.current_album: return False
                
                self.current_album.title = title
                self.current_album.album_artist = artist
                self.current_album.release_year = year
                self.current_album.album_type = alb_type
                
                self.album_repo.update(self.current_album)
                self.album_repo.set_publisher(self.current_album.album_id, self.selected_pub_name)
                
                # Clear search so we see the updated item (if renamed out of search scope)
                self.txt_search.blockSignals(True)
                self.txt_search.clear() 
                self.txt_search.blockSignals(False)

                self._refresh_vault() 
                if not silent:
                    QMessageBox.information(self, "Success", "Album Updated")
                success = True
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
            success = False
            
        return success

    def _on_select_clicked(self):
        # Auto-save current edits if inspector is active
        if self.pane_inspector.isEnabled():
            if not self._save_inspector(silent=True):
                return # Abort if save failed (e.g. invalid title)

        if not self.current_album: return
        self.album_selected.emit(self.current_album.album_id, self.current_album.title)
        self.accept()

    def _show_vault_context_menu(self, pos):
        item = self.list_vault.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        del_act = QAction("Delete Album", self)
        del_act.triggered.connect(self._on_delete)
        menu.addAction(del_act)
        
        menu.exec(self.list_vault.mapToGlobal(pos))

    def _on_delete(self):
        item = self.list_vault.currentItem()
        if not item: return
        
        album_id = item.data(Qt.ItemDataRole.UserRole)
        album = self.album_repo.get_by_id(album_id)
        if not album: return
        
        if QMessageBox.question(self, "Delete Album", 
                                f"Are you sure you want to delete '{album.title}'?\nThis will unlink all songs.") == QMessageBox.StandardButton.Yes:
            if self.album_repo.delete_album(album_id):
                # If we deleted the current one, clear inspector
                if self.current_album and self.current_album.album_id == album_id:
                    self.current_album = None
                    self.current_id = None
                    self.inp_title.clear()
                    self.inp_artist.clear()
                    self.inp_year.clear()
                    self.btn_pub_trigger.setText("(None)")
                    self.pane_inspector.setEnabled(False)
                
                self._refresh_vault()
