from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QFrame, QMessageBox, QComboBox, QWidget, QMenu, QCheckBox,
    QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox
from ..widgets.entity_list_widget import EntityListWidget, LayoutMode
from ...core.entity_registry import EntityType
from ...core.context_adapters import AlbumContributorAdapter, AlbumPublisherAdapter
from .entity_picker_dialog import EntityPickerDialog
from src.core.picker_config import get_artist_picker_config, get_publisher_picker_config


class AlbumManagerDialog(QDialog):
    """
    T-46: Proper Album Editor (The Workstation)
    A 4-pane console for managing albums, their metadata, and publishers.
    Layout: [Context (Songs)] | [Vault (Albums)] | [Inspector (Edit)] | [Sidecar (Publisher)]
    
    Refactor T-63: Layout split into HBox[MainContainer, Sidecar] to prevent button jumping.
    """
    
    album_selected = pyqtSignal(list) 
    save_and_select_requested = pyqtSignal(list)
    album_deleted = pyqtSignal(int)
    
    # Geometry (The Workstation Dimensions)
    BASE_WIDTH = 950
    BASE_HEIGHT = 650
    PANE_MIN_WIDTH = 250
    
    class DummyAlbum:
        """Helper for 'Create New' staging."""
        def __init__(self):
            self.album_id = 0
            self.album_artist = ""
            self.publisher_id = 0
            self.title = ""
            self.release_year = None
            self.album_type = "Album"

    def __init__(self, album_service, publisher_service, contributor_service, settings_manager, initial_data=None, parent=None, staged_deletions=None):
        super().__init__(parent)
        self.album_service = album_service
        self.publisher_service = publisher_service
        self.contributor_service = contributor_service
        self.settings_manager = settings_manager
        self.initial_data = initial_data or {}
        self.staged_deletions = staged_deletions or set()
        
        # Determine if the initial title is valid (exists in DB)
        aid = self.initial_data.get('album_id')
        if aid:
             fresh_album = self.album_service.get_by_id(aid)
             if fresh_album:
                  self.initial_data['title'] = fresh_album.title or ""
                  self.current_album = fresh_album

        target = self.initial_data.get('title', '')
        if target:
             hits = self.album_service.search(target)

        # State
        if not hasattr(self, 'current_album'):
            self.current_album = None # The album object currently loaded in Inspector
        
        self._current_context_songs = [] # T-Suggestions
            
        # T-Multi: Persistence for Search Refreshes
        init_ids = self.initial_data.get('album_id')
        if isinstance(init_ids, list):
             self.selected_ids = set(init_ids)
        elif init_ids:
             self.selected_ids = {init_ids}
        else:
             self.selected_ids = set()
             
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
        # Open Publisher Picker immediately (T-63)
        self._on_search_publisher()
        
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
        
        # T-46: View Toggle (Expert vs Focused)
        self.btn_view_toggle = GlowButton("View: Full")
        self.btn_view_toggle.setCheckable(True)
        self.btn_view_toggle.setChecked(True) # Default to Full
        self.btn_view_toggle.setFixedWidth(100)
        self.btn_view_toggle.toggled.connect(self._toggle_view_mode)
        header_layout.addWidget(self.btn_view_toggle)
        
        self.btn_create_new = GlowButton("Create New Album (+)")
        self.btn_create_new.clicked.connect(self._toggle_create_mode)
        self.btn_create_new.setFixedWidth(160) # Ensure text fits
        header_layout.addWidget(self.btn_create_new)
        
        main_layout.addWidget(header)
        
        # --- MAIN SPLITTER (The Workstation) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(7) # Void Style (T-63)
        
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
        self.pane_inspector.setMinimumWidth(self.PANE_MIN_WIDTH)
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
        btns = QHBoxLayout(footer)
        btns.setContentsMargins(20,10,20,10)
        btns.setSpacing(10)
        btns.addStretch()
        
        # 1. Destructive (Left)
        self.btn_remove = GlowButton("Remove Link")
        self.btn_remove.setObjectName("ActionPill")
        self.btn_remove.setProperty("action_role", "destructive")
        self.btn_remove.setToolTip("Unlink this album from the current song(s)")
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        self.btn_remove.setEnabled(False) # Only if an actual link exists
        btns.addWidget(self.btn_remove)
        
        # 2. Neutral (Middle)
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        # 3. Primary (Right)
        self.btn_save_inspector = GlowButton("Save & Assign")
        self.btn_save_inspector.setObjectName("ActionPill")
        self.btn_save_inspector.setProperty("action_role", "primary")
        self.btn_save_inspector.setEnabled(False) # Initially disabled
        self.btn_save_inspector.clicked.connect(lambda: self._save_inspector(close_on_success=True))
        btns.addWidget(self.btn_save_inspector)

        btns.addStretch()
        main_layout.addWidget(footer)
        
        # Add Main to Root
        self.root_layout.addWidget(self.main_container, 1) # Stretch factor 1
        
        # --- RIGHT: SIDECAR CONTAINER (REMOVED) ---
        # Sidecar logic refactored to Modal Dialog triggered by Processor ChipTray # Fixed width
        
        
        # Initial Load
        title_to_find = self.initial_data.get('title', '')
        if title_to_find:
            self.txt_search.setText(title_to_find or "")
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
        self.list_context.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Allow interaction
        self.list_context.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_context.customContextMenuRequested.connect(self._show_context_pane_menu)
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
        # Mode-based Selection Logic
        self.list_vault.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_vault.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_vault.customContextMenuRequested.connect(self._show_vault_context_menu)
        self.list_vault.itemClicked.connect(self._on_vault_item_clicked)
        self.list_vault.itemDoubleClicked.connect(self._on_select_clicked)
        self.list_vault.itemSelectionChanged.connect(self._on_vault_selection_changed)
        
        layout.addWidget(self.list_vault)
        return container

    def _build_inspector_pane(self):
        container = QFrame()
        container.setObjectName("DialogInspector")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0,0,0,0)
        container_layout.setSpacing(0)
        
        # Scroll Area (matching side panel structure for proper widget expansion)
        scroll = QScrollArea()
        scroll.setObjectName("EditorScroll")
        scroll.setWidgetResizable(True)  # KEY: Forces child to expand to fill width
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content widget inside scroll
        content = QFrame()
        content.setObjectName("FieldContainer")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(0)  # Zero spacing - manual control like side panel
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Form Fields (use FieldLabel for tight label-to-input proximity)
        # Form Fields (use FieldLabel for tight label-to-input proximity)
        # Form Fields
        self.inp_title = self._add_field(layout, "Album Title *")
        layout.addSpacing(12)
        
        # Artist Chip Tray - EXACT side panel structure
        field_module_art = QWidget()
        field_module_art.setObjectName("FieldModule")
        module_layout_art = QVBoxLayout(field_module_art)
        module_layout_art.setContentsMargins(0, 0, 0, 0)
        module_layout_art.setSpacing(0)
        
        # Header Row (Label only for now)
        header_row_art = QWidget()
        header_layout_art = QHBoxLayout(header_row_art)
        header_layout_art.setContentsMargins(0, 0, 0, 0)
        header_layout_art.setSpacing(4)
        lbl_art = QLabel("ALBUM ARTIST")
        lbl_art.setObjectName("DialogFieldLabel")
        header_layout_art.addWidget(lbl_art, 1)
        module_layout_art.addWidget(header_row_art)
        
        # Input Row
        input_row_art = QWidget()
        input_row_art.setObjectName("FieldRow")
        input_layout_art = QHBoxLayout(input_row_art)
        input_layout_art.setContentsMargins(0, 0, 0, 0)
        input_layout_art.setSpacing(6)
        
        self.tray_artist = EntityListWidget(
            service_provider=self,
            entity_type=EntityType.ARTIST,
            layout_mode=LayoutMode.CLOUD,
            allow_add=True,
            parent=self
        )
        self.tray_artist.set_suggestion_provider(self._get_artist_suggestions)
        input_layout_art.addWidget(self.tray_artist, 1)
        
        module_layout_art.addWidget(input_row_art)
        layout.addWidget(field_module_art)
        
        layout.addSpacing(12)
        self.inp_year = self._add_field(layout, "Release Year")
        layout.addSpacing(12)
        
        # Publisher Chip Tray - EXACT side panel structure
        field_module_pub = QWidget()
        field_module_pub.setObjectName("FieldModule")
        module_layout_pub = QVBoxLayout(field_module_pub)
        module_layout_pub.setContentsMargins(0, 0, 0, 0)
        module_layout_pub.setSpacing(0)
        
        # Header Row
        header_row_pub = QWidget()
        header_layout_pub = QHBoxLayout(header_row_pub)
        header_layout_pub.setContentsMargins(0, 0, 0, 0)
        header_layout_pub.setSpacing(4)
        lbl_pub = QLabel("PUBLISHER")
        lbl_pub.setObjectName("DialogFieldLabel")
        header_layout_pub.addWidget(lbl_pub, 1)
        module_layout_pub.addWidget(header_row_pub)
        
        # Input Row
        input_row_pub = QWidget()
        input_row_pub.setObjectName("FieldRow")
        input_layout_pub = QHBoxLayout(input_row_pub)
        input_layout_pub.setContentsMargins(0, 0, 0, 0)
        input_layout_pub.setSpacing(6)
        
        self.tray_publisher = EntityListWidget(
            service_provider=self,
            entity_type=EntityType.PUBLISHER,
            layout_mode=LayoutMode.CLOUD,
            allow_add=True,
            parent=self
        )
        self.tray_publisher.set_suggestion_provider(self._get_publisher_suggestions)
        input_layout_pub.addWidget(self.tray_publisher, 1)
        
        module_layout_pub.addWidget(input_row_pub)
        layout.addWidget(field_module_pub)
        
        layout.addSpacing(12)
        
        # Type Dropdown
        lbl_type = QLabel("RELEASE TYPE")
        lbl_type.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl_type)
        
        self.cmb_type = GlowComboBox()
        self.cmb_type.setEditable(False)
        self.cmb_type.addItems(["Album", "EP", "Single", "Compilation", "Anthology"])
        layout.addWidget(self.cmb_type)
        
        layout.addStretch()
        
        # Complete scroll area setup
        scroll.setWidget(content)
        container_layout.addWidget(scroll)
        
        # Disable by default
        container.setEnabled(False)
        
        return container
        
    # _build_sidecar_pane REMOVED

    def _add_field(self, layout, label):
        lbl = QLabel(label.upper())
        lbl.setObjectName("DialogFieldLabel")  # Match other dialogs' styling
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
        
        self.btn_create_new.style().polish(self.btn_create_new)
        
        # Clean Slate restored
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
        inputs = [self.inp_title, self.inp_year] # Removed inp_artist as it's now a tray
        for inp in inputs:
            inp.clear()
            inp.edit.setProperty("ghost", True)
            # Disconnect previous temporary slots if any (complex in PyQt, simple approach: unique connection)
            try: inp.edit.textEdited.disconnect(self._ungrey_text)
            except: pass
            inp.edit.textEdited.connect(self._ungrey_text)

        # T-Adapter: Create DummyAlbum for Staging so adapters have a target
        self.current_album = self.DummyAlbum()
        
        # Pre-fill from initial data
        if self.initial_data.get('title'):
             self.current_album.title = self.initial_data.get('title')
        elif self.initial_data.get('song_display'):
             parts = self.initial_data.get('song_display').split(" - ", 1)
             self.current_album.title = parts[1] if len(parts) == 2 else parts[0]

        if self.initial_data.get('artist'):
            self.current_album.album_artist = self.initial_data.get('artist')
            
        if self.initial_data.get('year'):
            self.current_album.release_year = self.initial_data.get('year')
        
        # Set Up Adapters
        self.tray_artist.set_context_adapter(
            AlbumContributorAdapter(self.current_album, self.contributor_service, stage_change_fn=self._stage_inspector_change)
        )
        self.tray_publisher.set_context_adapter(
             AlbumPublisherAdapter(self.current_album, self.publisher_service, stage_change_fn=self._stage_inspector_change)
        )
        
        # Populate Trays from Initial Data (New Feature Fix)
        # Populate Trays from Initial Data (New Feature Fix)
        if self.initial_data.get('artist'):
            art_val = self.initial_data.get('artist')
            # If string, resolve or wrap
            if isinstance(art_val, str):
                art_obj = self.contributor_service.get_by_name(art_val)
                if art_obj:
                    self.tray_artist.set_items([art_obj])
                else:
                    # Ghost Chip
                    self.tray_artist.set_items([(0, art_val, "👤", False, False, "New Artist", "amber", False)])
            elif isinstance(art_val, list):
                 self.tray_artist.set_items(art_val)
            
        if self.initial_data.get('publisher'):
            pub_val = self.initial_data.get('publisher')
            if isinstance(pub_val, str):
                # Publisher lookup by name not exposed directly on service usually, assume new or use id
                # But here we only have name string from SidePanel
                # Try to find ID?
                # For now, just show as ghost chip
                 self.tray_publisher.set_items([(0, pub_val, "🏢", False, False, "New Publisher", "amber", False)])
            else:
                 self.tray_publisher.set_items([pub_val] if not isinstance(pub_val, list) else pub_val)
        
        # Populate UI
        self.inp_title.setText(self.current_album.title)
        self.inp_year.setText(str(self.current_album.release_year) if self.current_album.release_year else "")
            
        if self.settings_manager:
            self.cmb_type.setCurrentText(self.settings_manager.get_default_album_type())
        else:
            self.cmb_type.setCurrentText("Single")
        self.selected_pub_name = ""
        
        self.inp_title.setFocus()
        self.lbl_title.setText("CREATING ALBUM")

    def _cancel_create_new(self):
        self.is_creating_new = False
        self.btn_create_new.setText("Create New Album (+)")
        self.btn_create_new.setObjectName("GlowButton") # Reset style
        self.btn_create_new.style().unpolish(self.btn_create_new)
        self.btn_create_new.style().polish(self.btn_create_new)
        
        # Ungrey fields
        inputs = [self.inp_title, self.inp_year] # Removed inp_artist
        for inp in inputs:
            inp.edit.setProperty("ghost", False)
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
            sender.setProperty("ghost", False)

    def _stage_inspector_change(self, field, value):
        """Callback for context adapters to stage changes."""
        self.btn_save_inspector.setProperty("dirty", True)
        self.btn_save_inspector.style().unpolish(self.btn_save_inspector)
        self.btn_save_inspector.style().polish(self.btn_save_inspector)

    def _on_vault_item_clicked(self, item):
        # Reset Create Button if we were creating
        if self.is_creating_new:
             self.is_creating_new = False
             self.btn_create_new.setText("Create New Album (+)")
             # Reset ghost styling
             self.inp_title.edit.setProperty("ghost", False)
             self.inp_year.edit.setProperty("ghost", False)
             # self.inp_artist removed (now tray)
        
        album_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_album = self.album_service.get_by_id(album_id)
        
        if not self.current_album:
            return
            
        # 1. Populate Inspector
        self.inp_title.setText(self.current_album.title or "")
        self.inp_year.setText(str(self.current_album.release_year) if self.current_album.release_year else "")
        self.cmb_type.setCurrentText(self.current_album.album_type or "Album")
        
        # Smart Fill for Existing: If DB has no artist/year/type, suggest from song context
        if not self.current_album.album_artist and self.initial_data.get('artist'):
            self.current_album.album_artist = self.initial_data.get('artist')
            
        if not self.current_album.release_year and self.initial_data.get('year'):
            self.inp_year.setText(str(self.initial_data.get('year')))
            # Also stage it on the object so it's ready for saving
            try:
                self.current_album.release_year = int(self.initial_data.get('year'))
            except: pass
            
        # T-Adapter: Connect EntityListWidgets to the current album (Immediate Save Mode)
        self.tray_artist.set_context_adapter(
            AlbumContributorAdapter(self.current_album, self.contributor_service)
        )
        
        self.tray_publisher.set_context_adapter(
            AlbumPublisherAdapter(self.current_album, self.publisher_service)
        )
        
        # 2. Populate Context (Songs)
        self._refresh_context(album_id)
        
        # 3. Enable UI
        self.pane_inspector.setEnabled(True)
        self.btn_save_inspector.setEnabled(True)
        # Update Remove button state
        self.btn_remove.setEnabled(album_id in self.selected_ids)
        self.pane_inspector.setProperty("state", "") # Clear create cue
        self.pane_inspector.style().unpolish(self.pane_inspector)
        self.pane_inspector.style().polish(self.pane_inspector)
        self.lbl_title.setText("EDITING ALBUM")

    def _refresh_context(self, album_id):
        self.list_context.clear()
        songs = self.album_service.get_songs_in_album(album_id)
        self._current_context_songs = songs # Store for suggestions
        
        if not songs:
            item = QListWidgetItem(" (No Songs) ")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_context.addItem(item)
            return

        for song in songs:
            # Format: [★] Track - Title (Artist)
            is_primary = song.get('is_primary', 0)
            star = "★ " if is_primary else "   "
            
            display = f"{star}{song['title']}"
            if song['artist'] != 'Unknown':
                 display += f" - {song['artist']}"
            
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, song['source_id']) # Store SourceID
            
            # Highlight primary
            if is_primary:
                item.setForeground(Qt.GlobalColor.yellow) # Or use a QSS class if possible
                item.setToolTip("Primary Album (Metadata Source)")
                
            self.list_context.addItem(item)

    def _show_context_pane_menu(self, pos):
        item = self.list_context.itemAt(pos)
        if not item: return
        
        source_id = item.data(Qt.ItemDataRole.UserRole)
        if not source_id or not self.current_album: return
        
        menu = QMenu(self)
        mk_primary = QAction("Set as Primary Album", self)
        mk_primary.triggered.connect(lambda: self._set_as_primary(source_id))
        menu.addAction(mk_primary)
        
        menu.exec(self.list_context.mapToGlobal(pos))

    def _set_as_primary(self, source_id):
        if not self.current_album: return
        self.album_service.set_primary_album(source_id, self.current_album.album_id)
        self._refresh_context(self.current_album.album_id)

    def _get_artist_suggestions(self) -> list:
        """Provide artist suggestions from context songs."""
        if not self._current_context_songs:
            return []
        
        suggestions = set()
        for song in self._current_context_songs:
            art = song.get('artist')
            if art and art != 'Unknown':
                suggestions.add(art)
        
        return sorted(list(suggestions))

    def _get_publisher_suggestions(self) -> list:
        """Provide publisher suggestions from context songs."""
        if not self._current_context_songs:
            return []
            
        suggestions = set()
        for song in self._current_context_songs:
            source_id = song.get('source_id')
            if not source_id: continue
            
            # Use service to fetch publisher for this song
            # Assuming AlbumService has a helper or we can get it via other means
            # Since I don't see the service code, I'll try a likely method name based on convention
            # or try to get metadata.
            try:
                if hasattr(self.album_service, 'get_song_publisher'):
                    pub = self.album_service.get_song_publisher(source_id)
                    if pub: suggestions.add(pub)
            except:
                pass
                
        return sorted(list(suggestions))

    def _on_vault_selection_changed(self):
        # T-Multi: Capture state to persist across searches
        self.selected_ids.clear()
        for item in self.list_vault.selectedItems():
            self.selected_ids.add(item.data(Qt.ItemDataRole.UserRole))

    def _refresh_vault(self, query=None):
        if query is None:
            query = self.txt_search.text()
        
        # T-Multi: Block signals to prevent clearing our persistent set during rebuild
        self.list_vault.blockSignals(True)
        self.list_vault.clear()
        
        results = self.album_service.search(query)
        
        # Ensure targets are present in the list (Preserve existing selection)
        if self.selected_ids:
            result_ids = {r.album_id for r in results}
            missing_ids = [tid for tid in self.selected_ids if tid not in result_ids]
            
            for mid in missing_ids:
                obj = self.album_service.get_by_id(mid)
                if obj: results.append(obj)
                
            # Optional: Sort purely to keep order sanity?
            # results.sort(key=lambda x: x.title or "")

        target_set = self.selected_ids
        # Primary focus: Keep current if selected, else pick arbitrary
        primary_id = self.current_album.album_id if self.current_album else None
        if not primary_id and target_set:
             primary_id = next(iter(target_set))
        
        for alb in results:
            if alb.album_id in self.staged_deletions: continue
            
            # Format: (Year) Title [Artist]
            display = f"{alb.title}"
            if alb.release_year: display = f"({alb.release_year}) " + display
            if alb.album_artist: display += f" - {alb.album_artist}"
            
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, alb.album_id)
            self.list_vault.addItem(item)
            
            if alb.album_id in target_set:
                item.setSelected(True)
                
                # Focus Primary to populate Inspector
                # (Inspector logic is triggered by Click. If we just setSelected(True), 
                # signal handler handles persistence. CurrentItem handles focus.)
                if alb.album_id == primary_id:
                    self.list_vault.setCurrentItem(item)
                    # We might need to manually trigger inspector update if this is initial load?
                    # But _on_vault_item_clicked is connected to Click.
                    # setCurrentItem does NOT trigger ItemClicked.
                    # It changes CurrentRow.
                    # So we might need explicit call if we want Inspector to load.
                    # But calling it here inside loop is OK if only once.
                    self._on_vault_item_clicked(item)
        
        self.list_vault.blockSignals(False)

    def _on_search_text_changed(self, text):
        self._refresh_vault(text)
        
    def _on_search_publisher(self):
        """Use universal EntityPickerDialog for publishers."""
        diag = EntityPickerDialog(
            service_provider=self,
            config=get_publisher_picker_config(),
            parent=self
        )
        if diag.exec() == 1:
            pub = diag.get_selected()
            if pub:
                self.tray_publisher.set_items([(0, pub.publisher_name, "")])
            


            


                 
    def _save_inspector(self, silent=False, close_on_success=False):
        # Gather Data
        title = self.inp_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Title cannot be empty")
            return False
            
        # Get Artist from Tray (M2M aware)
        artist_names = self.tray_artist.get_names()
        artist = ", ".join(artist_names) if artist_names else ""
        
        year_str = self.inp_year.text().strip()
        
        # Default to configured year if empty
        if not year_str:
            sm = self.settings_manager
            def_year = sm.get_default_year() if sm else 0
            if def_year > 0:
                year_str = str(def_year)
            # Else leave empty (No default year)
            
        year = int(year_str) if year_str.isdigit() else None
        alb_type = self.cmb_type.currentText()
        
        success = False
        try:
            if self.is_creating_new:
                # Create
                album, created = self.album_service.get_or_create(title, artist, year, album_type=alb_type)
                # album.album_type = alb_type # No longer needed if passed to get_or_create
                # self.album_service.update(album)
                
                # Save Publishers (M2M)
                pub_names = self.tray_publisher.get_names()
                from src.data.repositories.album_repository import AlbumRepository
                repo = AlbumRepository()
                repo.sync_publishers(album.album_id, pub_names)
                
                # Save Artists (M2M) from Staged Adapter or Tray
                # For Create Mode, we likely relied on staging or reading from tray names if adapter failed to stage
                if hasattr(self.current_album, '_staged_contributors'):
                     repo.sync_contributors(album.album_id, self.current_album._staged_contributors)
                else:
                    # Fallback if no staging happened (e.g. manual text entry)
                    artists = []
                    for art_name in artist_names:
                        artist_obj, _ = self.contributor_service.get_or_create(art_name)
                        if artist_obj:
                            artists.append(artist_obj)
                    repo.sync_contributors(album.album_id, artists)
                
                # ... 
                self.current_album = album
                self.is_creating_new = False
                
                # Clean up
                self.btn_save_inspector.setProperty("dirty", False)
                self.btn_save_inspector.style().unpolish(self.btn_save_inspector)
                self.btn_save_inspector.style().polish(self.btn_save_inspector)
                
                self.txt_search.blockSignals(True)
                self.txt_search.clear() 
                self.txt_search.blockSignals(False)
                
                self._refresh_vault() 
                if not silent: 
                    QMessageBox.information(self, "Success", "Album Created")
                success = True
            else:
                # Update (Edit Mode)
                if not self.current_album: return False
                
                self.current_album.title = title
                # self.current_album.album_artist = artist # Don't overwrite display string if M2M handles it, but maybe keep for legacy?
                # Actually, if we use M2M, 'album_artist' legacy field might be derived.
                # But for now, let's keep it sync.
                self.current_album.album_artist = artist 
                self.current_album.release_year = year
                self.current_album.album_type = alb_type
                
                self.album_service.update(self.current_album)
                
                # IMMEDIATE SAVE PROTOCOL: 
                # Chips (Publishers/Contributors) are already saved by the adapters.
                # We DO NOT sync them here.
                
                # Clear Dirty State
                self.btn_save_inspector.setProperty("dirty", False)
                self.btn_save_inspector.style().unpolish(self.btn_save_inspector)
                self.btn_save_inspector.style().polish(self.btn_save_inspector)
                
                # Clear search
                self.txt_search.blockSignals(True)
                self.txt_search.clear() 
                self.txt_search.blockSignals(False)
                
                self._refresh_vault() 
                if not silent and not close_on_success: 
                    QMessageBox.information(self, "Success", "Album Updated")
                success = True
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
            success = False

        if success and close_on_success:
             # Atomic Save: Tell Side Panel to commit everything immediately
             data = self._gather_selection()
             self.save_and_select_requested.emit(data)
             self.accept()
             
        return success

    def _on_select_clicked(self):
        # Auto-save current edits if inspector is active (but only if we aren't already returning from a save)
        if self.pane_inspector.isEnabled() and self.is_creating_new:
            if not self._save_inspector(silent=True):
                return # Abort if save failed (e.g. invalid title)

        data = self._gather_selection()
        if not data: return
        self.album_selected.emit(data)
        self.accept()

    def _gather_selection(self):
        """Collects all selected albums from the vault list as objects."""
        selection = []
        seen_ids = set()
        
        # 1. Gather from List (Legacy/Multi)
        items = self.list_vault.selectedItems()
        for idx, item in enumerate(items):
            aid = item.data(Qt.ItemDataRole.UserRole)
            if aid in seen_ids: continue
            
            alb = self.album_service.get_by_id(aid)
            if alb:
                selection.append({
                    'id': alb.album_id,
                    'title': alb.title,
                    'primary': False # Set later
                })
                seen_ids.add(alb.album_id)
                
        # 2. Add Current (New/Edited) if not present
        if self.current_album:
             aid = self.current_album.album_id
             if aid and aid not in seen_ids:
                 selection.append({
                    'id': aid,
                    'title': self.current_album.title,
                    'primary': False
                 })
                 seen_ids.add(aid)
                 
        # 3. Determine Primary (First in list = Primary)
        if selection:
            selection[0]['primary'] = True
            
        return selection

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
        album = self.album_service.get_by_id(album_id)
        if not album: return
        
        if QMessageBox.question(self, "Delete Album", 
                                f"Are you sure you want to delete '{album.title}'?\nThis will unlink all songs.") == QMessageBox.StandardButton.Yes:
            if self.album_service.delete(album_id):
                # If we deleted the current one, clear inspector
                if self.current_album and self.current_album.album_id == album_id:
                    self.current_album = None
                    self.current_id = None
                    self.inp_title.clear()
                    self.tray_artist.set_items([]) # Clear artist tray
                    self.tray_publisher.set_items([]) # Clear publisher tray
                    self.inp_year.clear()
                    self.pane_inspector.setEnabled(False)
                
                self._refresh_vault()

    def _on_remove_clicked(self):
        """Unlink selected album from current song(s). (Returns Code 2 to caller)"""
        # If we have a current album, we are asking to remove the link to THIS specific identity.
        if self.current_album:
            self.done(2)
        else:
            # Fallback for general unlinking if no specific one is targeted?
            # For now, matching Artist: requires a target.
            pass

    def _toggle_view_mode(self, checked):
        """Toggle between Full (Expert) and Focused (Editor) modes."""
        # ... (rest of method) ...
        if checked:
            self.btn_view_toggle.setText("View: Full")
            self.pane_context.show()
            self.pane_vault.show()
        else:
            self.btn_view_toggle.setText("View: Edit")
            self.pane_context.hide()
            self.pane_vault.hide()

    def get_selected(self):
        """Adapter method for EntityClickRouter compatibility."""
        return self._gather_selection()
