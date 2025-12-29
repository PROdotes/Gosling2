from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QSplitter,
    QFrame, QMessageBox, QComboBox, QWidget, QMenu, QCheckBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton
from .publisher_manager_dialog import PublisherPickerWidget

class AlbumManagerDialog(QDialog):
    """
    T-46: Proper Album Editor (The Workstation)
    A 4-pane console for managing albums, their metadata, and publishers.
    Layout: [Context (Songs)] | [Vault (Albums)] | [Inspector (Edit)] | [Sidecar (Publisher)]
    """
    
    # Returns the selected/created Album ID and Name
    album_selected = pyqtSignal(int, str) 
    save_and_select_requested = pyqtSignal(int, str)
    album_deleted = pyqtSignal(int)
    
    def __init__(self, album_repository, initial_data=None, parent=None, staged_deletions=None):
        super().__init__(parent)
        self.album_repo = album_repository
        self.initial_data = initial_data or {}
        self.staged_deletions = staged_deletions or set()
        
        # Determine if the initial title is valid (exists in DB)
        # If I open the dialog on a song that says "Wheels", but the DB knows "Wheels" 
        # was renamed to "Greatest Hits", searching "Wheels" will yield nothing (or the wrong thing).
        # Wait, if "Wheels" was renamed efficiently, the song's metadata in the SidePanel 
        # might still say "Wheels" (stale UI), so we pass "Wheels" in.
        # But "Wheels" album doesn't exist anymore.
        # So we should probably check if this search term yields results. If not, clear it.
        
        # T-46 Fix: Prefer ID lookup to prevent Stale Title Ghosting
        # If we have an ID, we trust the DB's current title for that ID, ignoring whatever text was passed.
        aid = self.initial_data.get('album_id')
        if aid:
             fresh_album = self.album_repo.get_by_id(aid)
             if fresh_album:
                  self.initial_data['title'] = fresh_album.title
                  # Also helpful:
                  self.current_album = fresh_album

        target = self.initial_data.get('title', '')
        if target:
             # Quick check: Does this title exist?
             hits = self.album_repo.search(target)
             if not hits:
                 pass

        # State
        self.current_album = None # The album object currently loaded in Inspector
        self.is_creating_new = False # Flag for "Create New" mode
        self.selected_pub_name = "" 
        
        self.setWindowTitle("Album Manager Workstation")
        self.setFixedSize(1300, 650) # Widescreen Console
        self.setModal(True)
        self.setObjectName("AlbumManagerDialog")
        
        self._init_ui()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0,0,0,0)
        
        # --- TOP HEADER ---
        header = QFrame()
        header.setFixedHeight(50)
        header.setObjectName("DialogHeader") # Add styling later if needed
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20,0,20,0)
        
        self.lbl_title = QLabel("ALBUM CONSOLE")
        self.lbl_title.setObjectName("DialogHeaderTitle") # Use existing style
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        self.btn_create_new = GlowButton("Create New Album (+)")
        self.btn_create_new.setFixedWidth(160) # Prevent clipping due to GlowButton empty-text layout issue
        self.btn_create_new.clicked.connect(self._start_create_new)
        header_layout.addWidget(self.btn_create_new)
        
        main_layout.addWidget(header)
        
        # --- MAIN SPLITTER (The Workstation) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(2)
        
        # 1. PANE Z: Context (Songs)
        self.pane_context = self._build_context_pane()
        self.splitter.addWidget(self.pane_context)
        
        # 2. PANE A: Vault (Albums)
        self.pane_vault = self._build_vault_pane()
        self.splitter.addWidget(self.pane_vault)
        
        # 3. PANE B: Inspector (Editor)
        self.pane_inspector = self._build_inspector_pane()
        self.splitter.addWidget(self.pane_inspector)
        
        # 4. PANE C: Sidecar (Publisher)
        self.pane_sidecar = self._build_sidecar_pane()
        self.splitter.addWidget(self.pane_sidecar)
        
        # Set initial stretch factors (20, 25, 30, 25)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 4)
        self.splitter.setStretchFactor(3, 3)
        
        main_layout.addWidget(self.splitter)
        
        # --- FOOTER ---
        footer = QFrame()
        footer.setFixedHeight(60)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20,10,20,10)
        
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        # Save Button (Moved to Global Footer for Stability)
        self.btn_save_inspector = GlowButton("Save Changes")
        self.btn_save_inspector.setObjectName("Primary")
        self.btn_save_inspector.setFixedWidth(140)
        self.btn_save_inspector.setEnabled(False) # Initially disabled
        self.btn_save_inspector.clicked.connect(self._save_inspector)

        self.btn_select = GlowButton("Select Album")
        self.btn_select.setObjectName("Primary")
        self.btn_select.setFixedWidth(140) # Fix clipping
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self._on_select_clicked)
        
        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_save_inspector)
        footer_layout.addWidget(self.btn_select)
        
        main_layout.addWidget(footer)
        
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
        lbl.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; background: #080808; border-bottom: 1px solid #111;")
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
        search_box.setStyleSheet("background: #0b0b0b; padding: 6px;")
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
        layout.setSpacing(15)
        
        # Form Fields
        self.inp_title = self._add_field(layout, "Album Title *")
        self.inp_artist = self._add_field(layout, "Album Artist")
        self.inp_year = self._add_field(layout, "Release Year")
        
        # Publisher Trigger
        lbl_pub = QLabel("PUBLISHER")
        lbl_pub.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl_pub)
        
        self.btn_pub_trigger = GlowButton("(None)")
        self.btn_pub_trigger.setObjectName("PublisherPickerButton")
        self.btn_pub_trigger.clicked.connect(self._toggle_sidecar)
        layout.addWidget(self.btn_pub_trigger)
        
        # Type Dropdown
        lbl_type = QLabel("RELEASE TYPE")
        lbl_type.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl_type)
        
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Album", "EP", "Single", "Compilation", "Anthology"])
        layout.addWidget(self.cmb_type)
        
        layout.addStretch()
        
        # Save Actions moved to Footer
        # btn_bar = QHBoxLayout()
        # ... removed ...
        # layout.addLayout(btn_bar)
        
        # Disable by default
        container.setEnabled(False)
        
        return container
        
    def _build_sidecar_pane(self):
        container = QFrame()
        container.setObjectName("PublisherSidecar")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        from ...data.repositories.publisher_repository import PublisherRepository
        pub_repo = PublisherRepository(self.album_repo.db_path)
        
        self.publisher_picker = PublisherPickerWidget(pub_repo, self)
        self.publisher_picker.publisher_selected.connect(self._on_publisher_selected)
        
        layout.addWidget(self.publisher_picker)
        
        # Initially Hidden in logic? No, just hidden via collapse or width?
        # For this design, let's keep it visible but maybe collapsible later.
        # Or start with simple visibility toggle.
        container.hide() # Hidden until trigger clicked
        
        return container

    def _add_field(self, layout, label):
        lbl = QLabel(label.upper())
        lbl.setObjectName("DialogFieldLabel")
        inp = GlowLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(inp)
        return inp

    # --- LOGIC ---

    def _start_create_new(self):
        self.is_creating_new = True
        self.current_album = None
        
        # Clear Selection
        self.list_vault.clearSelection()
        
        # Clear Inspector
        self.inp_title.clear()
        self.inp_artist.clear()
        self.inp_year.clear()
        self.cmb_type.setCurrentIndex(0)
        self.btn_pub_trigger.setText("(None)")
        self.selected_pub_name = ""
        
        # Clear Context
        self.list_context.clear()
        
        # Enable Inspector
        self.pane_inspector.setEnabled(True)
        self.btn_save_inspector.setEnabled(True)
        self.pane_inspector.setStyleSheet("border: 1px solid #ffaa00;") # Visual cue
        self.inp_title.setFocus()
        
        # Smart Fill
        if self.initial_data.get('title'):
            self.inp_title.setText(self.initial_data.get('title'))
        
        self.btn_select.setEnabled(False) # Can't select valid album yet
        self.lbl_title.setText("CREATING NEW ALBUM")

    def _on_vault_item_clicked(self, item):
        self.is_creating_new = False
        album_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_album = self.album_repo.get_by_id(album_id)
        
        if not self.current_album:
            return
            
        # 1. Populate Inspector
        self.inp_title.setText(self.current_album.title or "")
        self.inp_artist.setText(self.current_album.album_artist or "")
        self.inp_year.setText(str(self.current_album.release_year) if self.current_album.release_year else "")
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
        self.pane_inspector.setStyleSheet("") # Clear create cue
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
        # Always prefer current search text if query is not explicitly provided
        # Or even if it is? The issue described ("it was still saying wheels") implies 
        # the list didn't update to reflect the NEW title because the search query 
        # (old title) was still filtering it?
        
        # If we just saved "Wheels" -> "Greatest Hits", but the search box still says "Wheels",
        # the list will show nothing (or the old cached view?).
        
        # Let's trust the search box.
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
        else:
            self.pane_sidecar.show()
            self.publisher_picker._refresh_list() # Ensure fresh data
            # Restore splitter size preference if needed

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
        # Reuse existing delete logic if needed, simplified for brevity here
        pass
