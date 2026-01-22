from typing import List, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QScrollArea, QFrame, QSizePolicy, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QSize
from PyQt6.QtGui import QFont, QDesktopServices, QAction, QIcon
from ...core import yellberus
from ...core.registries.id3_registry import ID3Registry
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowLED, GlowToggle
from ..widgets.entity_list_widget import EntityListWidget, LayoutMode
from ...core.entity_registry import EntityType
from ...core.entity_click_router import ClickResult, ClickAction
from ...core.context_adapters import SongFieldAdapter
from ..dialogs.entity_picker_dialog import EntityPickerDialog
from ...core.picker_config import get_tag_picker_config, get_artist_picker_config

import copy
import os
import logging

logger = logging.getLogger(__name__)
# from ..dialogs.album_manager_dialog import AlbumManagerDialog  # Moved to _open_album_manager to break cycle

class SidePanelWidget(QFrame):
    """
    Metadata Editor (Stage) driven by Yellberus Field Registry.
    Implements a validation-gated 'Done' workflow and staging buffer.
    """
    
    # Signalling (dict = changes, set = album_deletions)
    save_requested = pyqtSignal(dict, set) 
    staging_changed = pyqtSignal(list) # list of song_ids in staging
    filter_refresh_requested = pyqtSignal() # Request rebuild of sidebar filters
    status_message_requested = pyqtSignal(str, str) # Emitted for user feedback (message, type)
    
    def __init__(self, library_service, metadata_service, renaming_service, duplicate_scanner, settings_manager, spotify_parsing_service=None, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.settings_manager = settings_manager
        
        # Initialize search provider immediately so UI builds with correct tooltip/state
        self._search_provider = "Google"
        if self.settings_manager:
            self._search_provider = self.settings_manager.get_search_provider()
        self.metadata_service = metadata_service
        self.renaming_service = renaming_service
        self.renaming_service = renaming_service
        self.duplicate_scanner = duplicate_scanner
        self.spotify_parsing_service = spotify_parsing_service
        
        # QSS Styling Support
        self.setObjectName("SidePanelEditor")
        
        # Dependency Injection for Dialogs
        self.album_service = library_service.album_service
        self.publisher_service = library_service.publisher_service
        self.tag_service = library_service.tag_service
        self.contributor_service = library_service.contributor_service
        
        self.isrc_collision = False
        
        self.current_songs = [] # List of Song objects
        self._staged_changes = {} # {song_id: {field_name: value}}
        self._hidden_album_ids = set() # {album_id, ...} - Hidden from picker search
        self._field_widgets = {} # {field_name: QWidget} - Public for testing
        
        # Debounce timer for expensive projected path calculations
        from PyQt6.QtCore import QTimer
        self._projected_timer = QTimer(self)
        self._projected_timer.setSingleShot(True)
        self._projected_timer.timeout.connect(self._do_update_projected_path)
        
        self._init_ui()
        
    def showEvent(self, event):
        """T-70: Ensure layout is correct when panel is first shown."""
        super().showEvent(event)
        # Force a refresh of visibility and layout for all trays
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._refresh_field_values)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0) # Slammed to the top
        
        # 1. Header Area
        # 1. Header Area (Just the label, parse button moved to Title field)
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 5, 0, 5)

        self.header_label = QLabel("No Selection")
        self.header_label.setObjectName("SidePanelHeader")
        self.header_label.setWordWrap(True)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.installEventFilter(self)  # For left-click parse
        
        # T-108: Context menu for Artist Stats
        self.header_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header_label.customContextMenuRequested.connect(self._show_header_context_menu)

        header_layout.addWidget(self.header_label, 1)
        
        layout.addWidget(header_container)
        
        
        # 3. Scroll Area for Fields
        self.scroll = QScrollArea()
        self.scroll.setObjectName("EditorScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.field_container = QFrame()
        self.field_container.setObjectName("FieldContainer")
        self.field_layout = QVBoxLayout(self.field_container)
        self.field_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.field_layout.setSpacing(0) # Programmatic spacing control
        
        self.scroll.setWidget(self.field_container)
        layout.addWidget(self.scroll, 1)


        # 4. Footer Actions - Single Row: LED | Search | Discard | Save
        footer_frame = QFrame()
        footer_frame.setObjectName("Footer")

        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(8, 8, 8, 4)
        footer_layout.setSpacing(8)

        # The Status LED (indicates Rename/Move pending)
        # Hover shows projected path overlay
        self.save_led = GlowLED(size=10, color="#FF4444")  # Red default
        self.save_led.setFixedSize(30, 30)  # Ensure space for glow radius
        self.save_led.setToolTip("Rename/Move detected")
        self.save_led.installEventFilter(self)  # For projected path hover

        # Projected Path Feedback (Hidden by default, reveal on LED hover)
        self.lbl_projected_path = QLabel("", self)
        self.lbl_projected_path.setObjectName("SidePanelProjectedPath")
        self.lbl_projected_path.setWordWrap(True)
        self.lbl_projected_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_projected_path.setVisible(False)

        # Split-Search Module (Magnifier + Dropdown)
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)

        self.btn_search_action = GlowButton("🔍")
        self.btn_search_action.setObjectName("WebSearchAction")
        self.btn_search_action.setFixedWidth(36)
        self.btn_search_action.setFixedHeight(28)
        self.btn_search_action.set_radius_style(
            "border-top-left-radius: 8px; border-bottom-left-radius: 8px; border-top-right-radius: 2px; border-bottom-right-radius: 2px;"
        )
        self.btn_search_action.setToolTip("Search Metadata")
        self.btn_search_action.setGlowMargins(5, 5, 0, 5) # No right margin for split effect
        self.btn_search_action.clicked.connect(self._on_web_search)
        self.btn_search_action.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_search_action.customContextMenuRequested.connect(self._show_search_menu)

        self.btn_search_menu = GlowButton("▼")
        self.btn_search_menu.setObjectName("WebSearchMenu")
        self.btn_search_menu.setFixedWidth(20)
        self.btn_search_menu.setFixedHeight(28)
        self.btn_search_menu.set_radius_style(
            "border-top-left-radius: 2px; border-bottom-left-radius: 2px; border-top-right-radius: 8px; border-bottom-right-radius: 8px;"
        )
        self.btn_search_menu.setToolTip("Select Search Provider")
        self.btn_search_menu.setGlowMargins(0, 5, 5, 5) # No left margin for split effect
        self.btn_search_menu.clicked.connect(self._show_search_menu_btn)

        search_layout.addWidget(self.btn_search_action)
        search_layout.addWidget(self.btn_search_menu)

        # Load saved search provider
        self._search_provider = "Google"
        if hasattr(self.library_service, 'settings_manager'):
            self._search_provider = self.library_service.settings_manager.get_search_provider()
            self.btn_search_action.setToolTip(f"Search Metadata via {self._search_provider}")

        # Discard button (compact)
        self.btn_discard = GlowButton("Discard")
        self.btn_discard.setObjectName("DiscardButton")
        self.btn_discard.setFixedHeight(28)
        self.btn_discard.clicked.connect(self._on_discard_clicked)

        # Save button (primary action, expands)
        self.btn_save = GlowButton("Save")
        self.btn_save.setObjectName("SaveAllButton")
        self.btn_save.setFixedHeight(28)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_save.setEnabled(False)

        # Status button (REMOVED - now handled via Status chip in Tag tray for cleaner UI)
        self.btn_status = None

        # Layout: LED | Search | Discard | Save
        footer_layout.addWidget(self.save_led)
        footer_layout.addWidget(search_container)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.btn_discard)
        footer_layout.addWidget(self.btn_save)

        layout.addWidget(footer_frame)

        self._clear_fields()
        self._update_save_state()

    def set_songs(self, songs: List[Any], force: bool = False):
        """Update the editor with fresh song selection."""
        # T-OPTIMIZATION: If hidden, do NOT rebuild UI or refresh fields.
        # This prevents search lag when a song is selected but editor is closed.
        if not self.isVisible() and not force:
            self.current_songs = songs
            return

        # Capture scroll if specific update (same ID set)
        scroll_pos = 0
        same_selection = False
        if self.current_songs and songs:
             old_ids = sorted([s.source_id for s in self.current_songs])
             new_ids = sorted([s.source_id for s in songs])
             same_selection = (old_ids == new_ids)

        if same_selection:
             scroll_pos = self.scroll.verticalScrollBar().value()

        # Performance: Only rebuild UI if song count changes (single→bulk or vice versa)
        # For same-count selections, just update widget values
        old_count = len(self.current_songs) if self.current_songs else 0
        new_count = len(songs) if songs else 0
        needs_rebuild = (old_count == 0 or new_count == 0 or
                        (old_count == 1) != (new_count == 1))  # 1 vs many

        self.current_songs = songs
        self._update_header()

        if same_selection and not force and not needs_rebuild:
             # Just refresh values (data update) without destroying widgets
             self._refresh_field_values()
             self.scroll.verticalScrollBar().setValue(scroll_pos)
             self._validate_done_gate()
             self._update_save_state()
             return

        if needs_rebuild or force:
            self._build_fields()
        else:
            # Should be covered by above, but safe fallback
            self._refresh_field_values()

        self._validate_done_gate()
        self._update_save_state()
        self._projected_timer.start(500)

        # Restore scroll
        if same_selection:
             self.scroll.verticalScrollBar().setValue(scroll_pos)

    def _update_header(self):
        if not self.current_songs:
            self.header_label.setText("No Selection")
            self.header_label.setToolTip("")
            self.header_label.setCursor(Qt.CursorShape.ArrowCursor)
            self._update_status_visuals(False)
            return

        if len(self.current_songs) > 1:
            self.header_label.setText(f"{len(self.current_songs)} Songs Selected")
            self.header_label.setToolTip("Click to parse metadata from filename")
            self.header_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._update_status_visuals(False)
            return

        # Single Song
        song = self.current_songs[0]
        # Priority: Staged Performers > Staged Unified Artist > DB Unified Artist
        p_val = self._get_effective_value(song.source_id, "performers", song.performers)
        if isinstance(p_val, list) and p_val:
            artist = p_val[0]
        elif isinstance(p_val, str) and p_val:
            artist = p_val
        else:
            artist = self._get_effective_value(song.source_id, "unified_artist", song.unified_artist)
        
        artist = artist or "Unknown Artist"
        self.header_label.setText(f"{artist} - {song.title}")
        self.header_label.setToolTip("Click to parse metadata from filename")
        self.header_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # Determine current state: READY if ProcessingStatus=1
        try:
            is_ready = song.is_done
            self._update_status_visuals(is_ready)
            
        except Exception as e:
            logger.error(f"Error updating status visuals: {e}")

    def _configure_micro_button(self, btn):
        """Helper to enforce styling on tiny 22x18 buttons."""
        btn.setFixedSize(22, 18)
        btn.setGlowRadius(2)
        # Force padding/radius via Python to survive GlowButton's dynamic stylesheet updates
        # 9px radius is mathematically perfect for 18px height (Pill Shape)
        btn.set_radius_style("border-radius: 9px; padding: 0px;")

    def _update_playback_state(self, is_playing):
        if hasattr(self.parent(), 'playback_deck'):
             self.parent().playback_deck.set_playing(is_playing)
                



    def _build_fields(self):
        """Dynamic UI Factory driven by Yellberus with Grouping."""
        self._clear_fields()
        if not self.current_songs:
            return

        # Separate into Core (Required + Key Identity) and Advanced
        # We explicitly promote performers/groups to Core for better UX, even if technically optional
        all_visible = {f.name: f for f in yellberus.FIELDS if f.visible and f.editable}
        
        # Define Explicit Layout Sections (Order Matters)
        # Define Explicit Layout Sections (Order Matters)
        identity_names_top = ['title', 'performers']
        identity_names_bottom = ['publisher', 'album', 'composers', ['recording_year', 'isrc']]
        attribute_names = ['tags', 'is_active'] # Virtual field merging Genre & Mood + Toggle
        
        core_names_flat = set() # Track handled fields
        
        def build_struct(names):
            struct = []
            for item in names:
                if item == 'tags':
                    if item in all_visible:
                        struct.append(all_visible[item])
                        core_names_flat.add(item)
                    continue

                if isinstance(item, list):
                    # Cluster row
                    cluster = [all_visible[n] for n in item if n in all_visible]
                    if cluster:
                        struct.append(cluster)
                        for c in cluster: core_names_flat.add(c.name)
                elif item in all_visible:
                    struct.append(all_visible[item])
                    core_names_flat.add(item)
            return struct

        identity_struct_top = build_struct(identity_names_top)
        identity_struct_bottom = build_struct(identity_names_bottom)
        attribute_struct = build_struct(attribute_names)
                
        # Advanced is everything else
        adv_fields = [f for f in yellberus.FIELDS if f.name in all_visible and f.name not in core_names_flat]

        def add_group(fields, title, show_line=True, compact=False):
            """Build a section of fields. Compact mode reduces spacing for 'bonus' data."""
            if not fields: return
            
            if show_line:
                # Replace Label with a 333333 Line (1px)
                # Spacing is now handled via QSS #FieldGroupLine { margin: ... }
                line = QFrame()
                line.setObjectName("FieldGroupLineCompact" if compact else "FieldGroupLine")
                self.field_layout.addWidget(line)
            
            for item in fields:
                # Handle Cluster (List of Fields)
                if isinstance(item, list):
                    # NEW: All clusters get the same Field Module chassis
                    field_module = QWidget()
                    field_module.setObjectName("FieldModuleCompact" if compact else "FieldModule")
                    module_layout = QVBoxLayout(field_module)
                    module_layout.setContentsMargins(0, 0, 0, 0)
                    module_layout.setSpacing(0) # Tightened from 4

                    # Horizontal Row Container for the actual inputs
                    h_row = QWidget()
                    h_row.setObjectName("FieldRow")
                    h_layout = QHBoxLayout(h_row)
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    h_layout.setSpacing(10) # Gutters between Clustered Fields (Year | Genre)
                    
                    for field in item:
                        col = QWidget()
                        v_col = QVBoxLayout(col)
                        v_col.setContentsMargins(0, 0, 0, 0)
                        v_col.setSpacing(0)
                        
                        # 1. Header Row (Label + Search Icon)
                        item_header = QWidget()
                        item_h_layout = QHBoxLayout(item_header)
                        item_h_layout.setContentsMargins(0, 0, 0, 0)
                        item_h_layout.setSpacing(4)

                        if field.ui_search:
                            btn_search = GlowButton("")
                            btn_search.setObjectName("SearchInlineButton")
                            self._configure_micro_button(btn_search)
                            # Left Click: Instant Search
                            btn_search.clicked.connect(lambda f=field: self._on_web_search(f))
                            # Right Click: Provider Menu
                            btn_search.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                            btn_search.customContextMenuRequested.connect(lambda pos, f=field, b=btn_search: self._show_search_menu_internal(b.mapToGlobal(pos), f))
                            item_h_layout.addWidget(btn_search)

                        lbl = QLabel(field.ui_header)
                        lbl.setObjectName("FieldLabelCompact" if compact else "FieldLabel")
                        item_h_layout.addWidget(lbl, 1)
                        
                        v_col.addWidget(item_header)

                        # 2. Input Row (Widget + optional Add button)
                        eff_val, is_mult, mixed_count = self._calculate_bulk_value(field)
                        widget = self._create_field_widget(field, eff_val, is_mult)
                        self._field_widgets[field.name] = widget


                        input_row = QWidget()
                        input_layout = QHBoxLayout(input_row)
                        input_layout.setContentsMargins(0, 0, 0, 0)
                        input_layout.setSpacing(4)
                        input_layout.addWidget(widget, 1)

                        # External + button removed in favor of EntityListWidget's internal tray button
                        
                        v_col.addWidget(input_row)
                        
                        # Alignment & Constraints
                        if field.name == 'recording_year':
                            widget.setFixedWidth(85)
                            if hasattr(widget, 'setAlignment'):
                                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        elif field.name == 'isrc':
                            widget.setMinimumWidth(120)
                            if hasattr(widget, 'setAlignment'):
                                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

                        stretch = 1 if field.name == 'recording_year' else 2
                        h_layout.addWidget(col, stretch)
                    
                    module_layout.addWidget(h_row)
                    self.field_layout.addWidget(field_module)
                    continue

                # Handle Single Field (Normal)
                field = item
                
                # Skip Title/Path in Bulk Mode (Spec Alpha)
                if len(self.current_songs) > 1 and field.name in ["title", "source"]:
                    continue
                
                # Skip 'is_done' (Status) because we have the big MARK DONE button
                if field.name == "is_done":
                    continue

                # NEW: All fields get the same 'Unit Stack' chassis
                field_module = QWidget()
                field_module.setObjectName("FieldModuleCompact" if compact else "FieldModule")
                module_layout = QVBoxLayout(field_module)
                module_layout.setContentsMargins(0, 0, 0, 0)
                module_layout.setSpacing(0)

                # Determine Type
                effective_val, is_multiple, mixed_count = self._calculate_bulk_value(field)
                is_bool = (field.strategy and field.strategy.upper() == "BOOLEAN") or \
                          (field.field_type == yellberus.FieldType.BOOLEAN)

                # Input Row (Input + optional label for bools)
                input_row = QWidget()
                input_row.setObjectName("FieldRow")
                input_layout = QHBoxLayout(input_row)
                input_layout.setContentsMargins(0, 0, 0, 0)
                input_layout.setSpacing(6)

                # 1. Header Row (Only for non-booleans)
                label = QLabel(field.ui_header)
                label.setObjectName("FieldLabelCompact" if compact else "FieldLabel")

                if not is_bool:
                    header_row = QWidget()
                    header_layout = QHBoxLayout(header_row)
                    header_layout.setContentsMargins(0, 0, 0, 0)
                    header_layout.setSpacing(4)

                    if field.name == 'tags':
                        btn_music = GlowButton("🎵")
                        btn_music.setObjectName("MusicInlineButton")
                        # Match Title Parse / Footer Search button size
                        btn_music.setFixedSize(36, 28)
                        btn_music.setToolTip("Open Scrubber")
                        btn_music.clicked.connect(self._open_scrubber)
                        header_layout.addWidget(btn_music)
                    elif field.ui_search:
                        # Other fields keep their search button
                        btn_search = GlowButton("")
                        btn_search.setObjectName("SearchInlineButton")
                        self._configure_micro_button(btn_search)
                        btn_search.clicked.connect(lambda f=field: self._on_web_search(f))
                        header_layout.addWidget(btn_search)

                    header_layout.addWidget(label, 1)
                    
                    # TITLE TOOLS: Casing Buttons (Right Side)
                    if field.name == 'title':
                        # Title Case (Abc Abc)
                        btn_title = GlowButton("Abc Abc")
                        btn_title.setFixedSize(50, 20)
                        btn_title.setCursor(Qt.CursorShape.PointingHandCursor)
                        btn_title.set_radius_style("border-radius: 4px;")
                        btn_title.set_font_size(8)
                        btn_title.set_font_weight("bold")
                        btn_title.setToolTip("To Title Case")
                        btn_title.clicked.connect(self._title_case_title)
                        header_layout.addWidget(btn_title)

                        # Sentence Case (Abc abc)
                        btn_sentence = GlowButton("Abc abc")
                        btn_sentence.setFixedSize(50, 20)
                        btn_sentence.setCursor(Qt.CursorShape.PointingHandCursor)
                        btn_sentence.set_radius_style("border-radius: 4px;")
                        btn_sentence.set_font_size(8)
                        btn_sentence.set_font_weight("bold")
                        btn_sentence.setToolTip("To Sentence Case")
                        btn_sentence.clicked.connect(self._sentence_case_title)
                        header_layout.addWidget(btn_sentence)

                    module_layout.addWidget(header_row)
                else:
                    # Boolean layout: [Label] [Toggle] [Stretch]
                    # We keep the label inside the input row for a consolidated hardware look
                    label.setFixedWidth(100) # Increased from 80 to prevent cropping of "TOGGLE LIVE"
                    input_layout.addWidget(label, 0)
                    input_layout.addSpacing(12)

                # 2. Edit Widget
                edit_widget = self._create_field_widget(field, effective_val, is_multiple)
                self._field_widgets[field.name] = edit_widget
                
                if is_bool:
                    input_layout.addWidget(edit_widget, 0)
                    input_layout.addStretch(1)
                else:
                    input_layout.addWidget(edit_widget, 1)

                module_layout.addWidget(input_row)
                self.field_layout.addWidget(field_module)
                continue
                # Spacing handled via CSS margin-bottom

        add_group(identity_struct_top, "Identity", show_line=False)
        add_group(identity_struct_bottom, "Identity Extended", show_line=True)
        add_group(attribute_struct, "Tags", show_line=True)
        add_group(adv_fields, "Advanced Details", show_line=True, compact=True)
        
        # T-70: Populate values for the first time after building the UI
        self._refresh_field_values()

    def _get_actual_widget(self, field_name):
        """Unwrap a widget if it's inside a search container."""
        w = self._field_widgets.get(field_name)
        if not w: return None
        
        # Only unwrap if it's a dedicated search container (tagged in _create_field_widget)
        if w.property("IsSearchContainer"):
            layout = w.layout()
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        # Skip the designated search button to find the actual input
                        if not widget.property("IsSearchButton"):
                            return widget
        return w

    def _refresh_field_values(self):
        """Update existing widget values without rebuilding UI (performance optimization)."""
        if not self.current_songs:
            return

        refresh_queue = list(yellberus.FIELDS)

        for field_def in refresh_queue:
            field_name = field_def.name
            widget = self._get_actual_widget(field_name)
            if not widget:
                continue

            # Calculate new value
            effective_val, is_multiple, mixed_count = self._calculate_bulk_value(field_def)

            # CRITICAL: Block signals to prevent triggering _on_field_changed
            # This prevents false "unsaved changes" when switching between songs
            widget.blockSignals(True)
            try:
                # Update widget based on type
                if isinstance(widget, (QCheckBox, GlowToggle)):
                    if is_multiple and isinstance(widget, QCheckBox):
                        widget.setCheckState(Qt.CheckState.PartiallyChecked)
                    else:
                        val_bool = str(effective_val).lower() in ("true", "1", "yes") if isinstance(effective_val, str) else bool(effective_val)
                        widget.setChecked(val_bool if effective_val is not None else False)

                elif isinstance(widget, (QPushButton, GlowButton)):  # Legacy Album picker (if any)
                    if is_multiple:
                        widget.setText("(Multiple Values)")
                    else:
                        # Fix T-Bug: Avoid str(None) -> "None" trap. 
                        display_text = str(effective_val) if (effective_val and str(effective_val).strip()) else "(No Album)"
                        widget.setText(display_text)

                elif isinstance(widget, EntityListWidget):
                    # T-Fix: Update Adapter reference because self.current_songs object changed!
                    if isinstance(widget.context_adapter, SongFieldAdapter):
                        widget.context_adapter.songs = self.current_songs

                    # T-Fix: Force update from SidePanel's "Latest Chips" logic which respects Staged Changes.
                    # This ensures that when we pick an album, "ghost" changes appear immediately.
                    # Bypassing adapter.refresh_from_db because we are in Draft Mode.
                    try:
                        chips = self._get_latest_chips(field_def.name)
                        widget.set_items(chips)
                    except Exception:
                        # Fallback to adapter if staging logic fails
                        widget.refresh_from_adapter()

                elif isinstance(widget, (QLineEdit, GlowLineEdit)):
                    if is_multiple:
                        widget.setPlaceholderText("(Multiple Values)")
                        widget.setText("")
                    else:
                        # Format lists properly
                        if isinstance(effective_val, list):
                            text_val = ", ".join(str(v) for v in effective_val) if effective_val else ""
                        else:
                            text_val = str(effective_val) if effective_val is not None else ""
                        widget.setText(text_val)

                    # LineEdit logic (Cleaned)
                    pass
            finally:
                # Always restore signals
                widget.blockSignals(False)



    def _handle_tag_click(self, field_name, entity_id, name):
        """Open editor to rename a tag globally."""
        
        # Parse display name if it's from the unified tray (e.g. "Genre: Pop")
        display_name = name
        actual_name = name
        category = None
        
        if field_name == 'tags' and ': ' in name:
            category, actual_name = name.split(': ', 1)
        
        # T-89: Status Tags are locked and informational.
        # Clicking them shows a Metadata Audit instead of Rename.
        if category == "Status" or entity_id == -99:
            if not self.current_songs:
                return ClickResult(ClickAction.CANCELLED, entity_id)

            # Calculate current state
            statuses = []
            for song in self.current_songs:
                st = self._get_effective_value(song.source_id, 'is_done', song.processing_status)
                statuses.append(bool(st) if st is not None else True)
            all_done = all(statuses)

            # 1. If currently READY, toggle back to PENDING immediately
            if all_done:
                self._on_status_toggled()
                return ClickResult(ClickAction.DATA_CHANGED, entity_id)

            # 2. If PENDING, run validation check
            errors = self._get_validation_errors()
            from PyQt6.QtWidgets import QMessageBox
            
            if not errors:
                # Validation Passed: Ask to Mark Ready
                reply = QMessageBox.question(
                    self, 
                    "Validation Passed", 
                    "✅ All metadata requirements are met.\n\nMark as READY for broadcast?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_status_toggled() # Toggle to READY
                    return ClickResult(ClickAction.DATA_CHANGED, entity_id)
                else:
                    return ClickResult(ClickAction.CANCELLED, entity_id)
            else:
                # Validation Failed: Show Audit report
                lines = ["❌ Requirements missing for 'READY' status:"]
                for e in errors:
                    lines.append(f"• {e}")
                
                lines.append("")
                lines.append("Current Metadata used for Validation:")
                if len(self.current_songs) == 1:
                    s = self.current_songs[0]
                    for field in yellberus.get_required_fields():
                        val = getattr(s, field.model_attr or field.name, "")
                        lines.append(f"[{field.ui_header}]: {val if val else '<EMPTY>'}")
                
                QMessageBox.warning(self, "Metadata Audit", "\n".join(lines))
                return ClickResult(ClickAction.CANCELLED, entity_id)


            
            # Single song context is easiest for labels

        
        # If we have an entity ID (best case)
        if entity_id and entity_id > 0:
            tag = self.tag_service.get_by_id(entity_id)
        else:
            # Fallback to name search via Service
            tag = self.tag_service.find_by_name(actual_name, category)
            
        if not tag:
            return

        diag = EntityPickerDialog(
            service_provider=self,
            config=get_tag_picker_config(),
            target_entity=tag,
            parent=self
        )
        res = diag.exec()
        if res == 1:
            selected_tag = diag.get_selected()
            
            # --- 🛑 CASE 1: Silent Selection Swap ---
            if selected_tag and selected_tag.tag_id != tag.tag_id:
                for song in self.current_songs:
                    self.tag_service.remove_tag_from_source(song.source_id, tag.tag_id)
                    self.tag_service.add_tag_to_source(song.source_id, selected_tag.tag_id)
                self._refresh_field_values()
                self.filter_refresh_requested.emit()
                return ClickResult(ClickAction.DATA_CHANGED, selected_tag.tag_id)

            # --- CASE 2: Global Rename / Merge ---
            if diag.is_rename_requested():
                new_name, new_category = diag.get_rename_info()
                
                # Let the service handle the rename (including merges if the name is taken)
                if self.tag_service.rename_tag(tag.tag_name, new_name, new_category):
                    self._refresh_field_values()
                    self.filter_refresh_requested.emit()
                    
                    # Try to find the tag again (it might have a new ID if it was merged)
                    final_tag = self.tag_service.find_by_name(new_name, new_category)
                    return ClickResult(ClickAction.UPDATED, final_tag.tag_id if final_tag else tag.tag_id)
                
                return ClickResult(ClickAction.CANCELLED, tag.tag_id)
            return ClickResult(ClickAction.CANCELLED, tag.tag_id)

        elif res == 2:
            # REMOVE REQUEST (Contextual Unlink)
            return ClickResult(ClickAction.REMOVED, tag.tag_id)
        
        return ClickResult(ClickAction.CANCELLED, entity_id)

    def _handle_publisher_click(self, entity_id, name):
        """
        Intercept Publisher clicks to handle 'Jump to Album Manager'.
        Returns True if handled (Jumped), False to let Router open standard Dialog.
        """
        if not self.publisher_service: return False
        pub = self.publisher_service.get_by_id(entity_id)
        if not pub: return False

        # T-180: If the publisher is explicitly linked to the song, manage it here.
        # Don't jump to the album if it is a direct recording-level owner.
        # BUG FIX: Query DB directly instead of relying on stale song.publisher_id attribute
        if self.current_songs:
            song = self.current_songs[0]
            # Query DB for actual direct links (RecordingPublishers junction table)
            direct_publishers = self.publisher_service.get_for_song(song.source_id)
            direct_pub_ids = [p.publisher_id for p in direct_publishers]
            if entity_id in direct_pub_ids:
                return False  # Direct link exists - open standard editor.

        # Check Inherited Status for Deep Link
        is_inherited = False
        if self.current_songs and getattr(self.current_songs[0], 'album_id', None):
            alb_id = self.current_songs[0].album_id
            if isinstance(alb_id, list):
                 alb_id = alb_id[0] if alb_id else None
            
            if alb_id:
                alb_pub_str = self.album_service.get_publisher(alb_id) or ""
                if pub.publisher_name in [p.strip() for p in alb_pub_str.split(',')]:
                    is_inherited = True
        
        if is_inherited:
            alb = self.album_service.get_by_id(alb_id)
            if alb:
                self._open_album_manager(initial_album=alb, focus_publisher=True)
            return True # Handled custom action
        
        return False # Fallback to Standard Router (PublisherDetailsDialog)

    def _handle_album_click(self, entity_id, name):
        if self.album_service:
            alb = self.album_service.get_by_id(entity_id)
            if alb:
                self._open_album_manager(initial_album=alb)





    def _on_chip_removed(self, field_name, entity_id, name):
        """T-70: Generic chip removal handling."""

        if field_name == 'tags':
            # Tags use the entity_id which is the tag_id
            if entity_id and entity_id > 0:
                for song in self.current_songs:
                    self.tag_service.remove_tag_from_source(song.source_id, entity_id)
                self._refresh_field_values()
                self.filter_refresh_requested.emit()
                return
            else:
                # Fallback: parse the name "Category: Tag" and find the tag ID
                if ': ' in name:
                    cat, actual_name = name.split(': ', 1)
                    tag = self.tag_service.find_by_name(actual_name, cat)
                    if tag:
                        for song in self.current_songs:
                            self.tag_service.remove_tag_from_source(song.source_id, tag.tag_id)
                        self._refresh_field_values()
                        self.filter_refresh_requested.emit()
                return

        for song in self.current_songs:
            current = self._get_effective_value(song.source_id, field_name, getattr(song, field_name, []))
            # Normalize to list
            if not isinstance(current, list):
                # T-Policy: Prevent splitting for atomic fields like Album/Publisher
                if field_name in ['album', 'publisher']:
                    current = [str(current)] if current else []
                else:
                    delims = r',|;| & '
                    if field_name == 'composers': delims += r'|/'
                    import re
                if field_name in ['album', 'publisher']:
                    current = [str(current)] if current else []
                else:
                    # T-Fix: Do NOT split on punctuation. Respect DB/Staging.
                    # delimiters = r',|;| & ' (REMOVED)
                    current = [current] if current and isinstance(current, str) else (current or [])
            
            if name in current:
                new_list = [p for p in current if p != name]
                
                # Special Case: Album IDs must stay in sync with Names
                if field_name == 'album':
                    curr_ids = self._get_effective_value(song.source_id, 'album_id', getattr(song, 'album_id', []))
                    if isinstance(curr_ids, int): curr_ids = [curr_ids]
                    if not curr_ids: curr_ids = []
                    
                    if entity_id in curr_ids:
                        new_ids = [x for x in curr_ids if x != entity_id]
                        # Consistent storage: Int if single, List if multiple, None if empty
                        final_ids = new_ids if len(new_ids) > 1 else (new_ids[0] if new_ids else None)
                        self._on_field_changed('album_id', final_ids)
                    
                self._on_field_changed(field_name, new_list)
        
        self._refresh_field_values()
        self.filter_refresh_requested.emit()
        
        self._refresh_field_values()

    def _on_add_button_clicked(self, field_name, origin=None):
        """Generic 'Add' button handler."""
        
        # Legacy / Special Handling (e.g. Album Manager direct invocation)
        # MUST come before delegation because Album field IS an EntityListWidget 
        # but the generic picker doesn't support AlbumManagerDialog's complexity yet.
        if field_name == 'album':
            # Clean Slate for Add, Merge logic handled in callback
            self._open_album_manager(clean_slate=True, mode='add')
            return

        # T-Refactor: Delegate to EntityListWidget if applicable
        if field_name in self._field_widgets:
             widget = self._field_widgets[field_name]
             if isinstance(widget, EntityListWidget):
                 widget.add_item_interactive()
                 return
        elif field_name == 'tags':
            # Unified tag picker - use universal EntityPickerDialog
            from ..dialogs.entity_picker_dialog import EntityPickerDialog
            from src.core.picker_config import get_tag_picker_config
            diag = EntityPickerDialog(
                service_provider=self,
                config=get_tag_picker_config(),
                parent=self
            )
            if diag.exec() == 1:
                selected = diag.get_selected()
                if selected:
                    # Add tag to all selected songs via TagService
                    for song in self.current_songs:
                        self.tag_service.add_tag_to_source(song.source_id, selected.tag_id)
                    # Refresh to show new tag
                    self._refresh_field_values()
                    self.filter_refresh_requested.emit()
        else:
            # Artists / Contributors - use universal EntityPickerDialog
            from ..dialogs.entity_picker_dialog import EntityPickerDialog
            from src.core.picker_config import get_artist_picker_config
            diag = EntityPickerDialog(
                service_provider=self,
                config=get_artist_picker_config(),
                parent=self
            )
            
            if diag.exec() == 1:
                selected = diag.get_selected()
                if selected:
                    # Support both List (Smart Split) and Single Item (Legacy)
                    if isinstance(selected, list):
                        for item in selected:
                            self._add_name_to_selection(field_name, item.name if hasattr(item, 'name') else str(item))
                    else:
                        self._add_name_to_selection(field_name, selected.name if hasattr(selected, 'name') else str(selected))

    def _add_name_to_selection(self, field_name, name):
        """T-70: Add a name to the specified field for all selected songs."""
        for song in self.current_songs:
            current = self._get_effective_value(song.source_id, field_name, getattr(song, field_name, []))
            if not isinstance(current, list):
                if field_name in ['album', 'publisher']:
                    current = [str(current)] if current else []
                else:
                    delims = r',|;| & '
                    if field_name == 'composers': delims += r'|/'
                    import re
                if field_name in ['album', 'publisher']:
                    current = [str(current)] if current else []
                else:
                    # T-Fix: Do NOT split on punctuation. Respect DB/Staging.
                    current = [current] if current and isinstance(current, str) else (current or [])
            
            if name not in current:
                new_list = list(current)
                new_list.append(name)
                self._on_field_changed(field_name, new_list)
        
        self._refresh_field_values()

    def _on_chip_context_menu(self, field_name, entity_id, name, global_pos):
        """T-82: Direct Right-Click action (Skip Menu) - ONLY for Genre category."""
        if field_name == 'album':
            self._on_chip_primary_requested(field_name, entity_id, name)
        elif field_name == 'tags' and ': ' in name:
            # Virtual 'tags' field - only act if it's a Genre tag (TCON frame)
            cat, _ = name.split(': ', 1)
            if ID3Registry.get_id3_frame(cat) == 'TCON':
                self._on_chip_primary_requested(field_name, entity_id, name)

    def _on_chip_primary_requested(self, field_name, entity_id, name):
        """T-82: Atomic re-order via Adapter (Immediate Save, bypassing SidePanel staging)."""
        widget = self._get_actual_widget(field_name)
        if isinstance(widget, EntityListWidget) and widget.context_adapter:
            if widget.context_adapter.set_primary(entity_id):
                # Success - the adapter triggers on_data_changed() which calls self._refresh_field_values()
                return

        # Fallback for legacy fields not yet unified via EntityListWidget (e.g. title)
        # (Currently tags and albums already use EntityListWidget)

    def _on_field_changed_and_save(self, field_name: str, value: Any, song_id=None):
        """Helper to stage a change and immediately commit it (Auto-Save)."""
        self._on_field_changed(field_name, value, song_id=song_id)
        # Trigger immediate save of all staged changes
        # Trigger immediate save of all staged changes using existing handler
        self._on_save_clicked()

    def _on_active_toggled_atomic(self, checked: bool):
        """Atomic save for IsActive toggle (T-92 fix). Bypass staging."""
        if not self.current_songs:
            return
            
        # 1. Update DB directly
        for song in self.current_songs:
            song.is_active = checked
            self.library_service.update_song(song)
            
        # 2. Trigger Refresh to update Table View
        # This will reload the library but preserve SidePanel staging via selection persistance
        self.filter_refresh_requested.emit()

    def _on_entity_data_changed(self):
        """Called when EntityListWidget reports a data change (e.g. rename/edit)."""
        
        # T-Fix: Identify the field that changed and clear its staging
        # We deduce the field name by finding which widget sent the signal
        sender = self.sender()
        target_field = None
        if sender:
            for name, widget in self._field_widgets.items():
                if widget == sender:
                    target_field = name
                    break
        
        # Clear staging for this field to ensure we display/save fresh DB data
        if target_field and self.current_songs:
             for song in self.current_songs:
                  sid = song.source_id
                  if sid in self._staged_changes:
                       self._staged_changes[sid].pop(target_field, None)
                       # Also clear potential ID companion (e.g. publisher -> publisher_id)
                       self._staged_changes[sid].pop(f"{target_field}_id", None)
                       
                       if not self._staged_changes[sid]:
                            del self._staged_changes[sid]
             
             self._update_save_state()
             self.staging_changed.emit(list(self._staged_changes.keys()))

        # Reload current songs to reflect potential renames (e.g. cached 'performers' string)
        if self.current_songs:
             updated_songs = []
             for s in self.current_songs:
                 new_s = self.library_service.song_service.get_by_id(s.source_id)
                 if new_s: updated_songs.append(new_s)
             
             if updated_songs:
                 self.current_songs = updated_songs
                 
                 # UPDATE ADAPTERS: Propagate new song list to all EntityListWidgets
                 # This prevents them from using stale references during refresh_from_adapter()
                 for f_name, widget in self._field_widgets.items():
                    if isinstance(widget, EntityListWidget):
                        # Duck-type check for SongFieldAdapter or compatible
                        if hasattr(widget, 'context_adapter') and hasattr(widget.context_adapter, 'songs'):
                            widget.context_adapter.songs = self.current_songs
        
        self._refresh_field_values()
        
        # BROADCAST: Ensure Library Refresh to prevent re-seeding stale names from memory
        try:
            win = self.window()
            if hasattr(win, 'library_widget'):
                win.library_widget.refresh(refresh_filters=False)
        except:
            pass

    def _create_field_widget(self, field_def, value, is_multiple):
        # Determine strict type or strategy
        is_bool = (field_def.strategy and field_def.strategy.upper() == "BOOLEAN") or \
                  (field_def.field_type.name == "BOOLEAN")

        if is_bool:
            tg = GlowToggle()
            
            # T-93: Contextual Labels for Boolean Toggles
            if field_def.name == 'is_active':
                tg.set_labels("ON", "OFF")
                tg.setToolTip("Determines if this song is enabled for library playback and rotation.")
            else:
                tg.set_labels("YES", "NO")

            # Handle string 'True'/'False' from some legacy paths just in case
            val_bool = str(value).lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
            
            tg.setChecked(val_bool if value is not None else False)
            # is_multiple partially checked not yet supported by GlowToggle, default to False
            # T-92: Atomic Save for "Live" Toggle per user request
            if field_def.name == 'is_active':
                tg.toggled.connect(self._on_active_toggled_atomic)
            else:
                tg.toggled.connect(lambda checked, f=field_def.name: self._on_field_changed(f, checked))
            return tg
            
        if field_def.name == 'album_REMOVE_OLD_BUTTON_LOGIC':
            pass # Removed

        if field_def.name in ['performers', 'composers', 'producers', 'lyricists', 'publisher', 'album', 'tags']:
            # Determine EntityType
            e_type = EntityType.ARTIST
            if field_def.name == 'publisher': e_type = EntityType.PUBLISHER
            elif field_def.name == 'album': e_type = EntityType.ALBUM
            elif field_def.name == 'tags': e_type = EntityType.TAG
            
            # Select Service
            from ...core.entity_registry import ENTITY_REGISTRY
            config = ENTITY_REGISTRY[e_type]
            service = getattr(self, config.service_attr)
            
            # Create Adapter for the Song Field
            adapter = SongFieldAdapter(
                self.current_songs, 
                field_def.name, 
                service,
                stage_change_fn=self._on_field_changed_and_save,
                get_child_data_fn=lambda f=field_def.name: self._get_latest_chips(f),
                get_value_fn=self._get_effective_value,
                refresh_fn=self._refresh_field_values
            )
            
            # Create the Unified Component
            ew = EntityListWidget(
                service_provider=self,
                entity_type=e_type,
                layout_mode=LayoutMode.CLOUD,
                context_adapter=adapter,
                allow_add=True, # SidePanel always allows adding via exterior button or tray
                allow_remove=True,
                allow_edit=True,
                add_tooltip=f"Add {field_def.ui_header}",
                parent=self
            ) 
            
            # Register SidePanel custom handlers on the internal router
            # Wrap in lambda to curry 'field_def.name' since router only passes (id, label)
            ew.click_router.register_custom_handler(
                "handle_tag_click", 
                lambda eid, name: self._handle_tag_click(field_def.name, eid, name)
            )
            
            if field_def.name == 'album':
                # Signals full handling to router to prevent double dialogs
                ew.click_router.register_custom_handler(
                    "handle_album_click",
                    lambda eid, name: self._handle_album_click(eid, name) or True
                )
                
                # T-Fix: Override generic Add button to use SidePanel's context-aware launcher
                ew.set_custom_add_handler(lambda: self._open_album_manager(mode='add', clean_slate=False))

            if field_def.name == 'publisher':
                ew.click_router.register_custom_handler(
                    "handle_publisher_click",
                    lambda eid, name: self._handle_publisher_click(eid, name)
                )
            
            # Connect Context Menu
            ew.chip_context_menu_requested.connect(lambda eid, n, p, f=field_def.name: self._on_chip_context_menu(f, eid, n, p))
            
            # Connect Data Changed (e.g. Rename from Dialog) to Reload
            ew.data_changed.connect(self._on_entity_data_changed)
            
            return ew

        edit = GlowLineEdit()
        
        # User Req: Enable Multi-line Overlay for long fields
        if field_def.name in ['lyrics', 'comment']:
            edit.enable_overlay()
            
        if is_multiple:
            edit.setPlaceholderText("(Multiple Values)")
        else:
            # Format lists properly (no [])
            if isinstance(value, list):
                if not value:
                    text_val = ""
                else:
                    text_val = ", ".join(str(v) for v in value)
            else:
                text_val = str(value) if value is not None else ""
            edit.setText(text_val)
            
        # Add ISRC validation (real-time text color feedback)
        if field_def.name == 'isrc':
            # T-Sanity: Sanitize input for Staging so that strict validation passes
            # (Visual validation is handled separately by _validate_isrc_field)
            from ...utils.validation import sanitize_isrc
            edit.textChanged.connect(lambda text: self._on_field_changed(field_def.name, sanitize_isrc(text)))
            
            # Visual Feedback on the Widget itself (Red/Amber/Green)
            edit.textChanged.connect(lambda text: self._validate_isrc_field(edit, text))
        else:
             # Standard Field
             edit.textChanged.connect(lambda text: self._on_field_changed(field_def.name, text))
        
        # Escape to revert
        edit.installEventFilter(self)
        return edit

    def _open_album_manager(self, checked=False, focus_publisher=False, initial_album=None, clean_slate=False, mode='edit'):
        """Open the T-46 Album Selector."""
        # Gather initial data from current selection to auto-populate "Create New"
        initial_data = {}
        
        if initial_album:
             initial_data = {
                 'title': initial_album.title,
                 'artist': initial_album.album_artist,
                 'year': initial_album.release_year,
                 'publisher': self.album_service.get_publisher(initial_album.album_id),
                 'album_id': initial_album.album_id,
                 'song_display': "Deep Link Selection",
                 'focus_publisher': focus_publisher
             }
        elif self.current_songs:
            song = self.current_songs[0]
            sid = song.source_id
            
            # T-70: Use Effective Values (Staged or Persisted) to ensure we capture "Just Typed" edits
            # This ensures "Create New Album" sees the corrected Artist/Title
            eff_performers = self._get_effective_value(sid, 'performers', song.performers)
            eff_title = self._get_effective_value(sid, 'title', song.name)
            
            # Helper: Get performers (all or primary)
            if isinstance(eff_performers, list):
                d_artist = eff_performers
                disp_artist = ", ".join(d_artist) if d_artist else "Unknown"
            else:
                d_artist = str(eff_performers) if eff_performers else "Unknown"
                disp_artist = d_artist
            
            # Determine initial values based on Clean Slate request
            init_title = "" if clean_slate else (self._get_effective_value(sid, 'album', song.album) or "")
            init_id = None if clean_slate else self._get_effective_value(sid, 'album_id', getattr(song, 'album_id', None))
            
            # T-Fix: If Creating New ('add'), do NOT pre-select the existing album ID. 
            # We want the context strings (Artist/Title) but not the ID link.
            if mode == 'add':
                init_id = None
                init_title = "" # Also clear title so we don't search for 'Unknown Album' or current context
            
            initial_data = {
                'title': init_title,
                'artist': self._get_effective_value(sid, 'album_artist', song.album_artist) or d_artist,
                'year': self._get_effective_value(sid, 'recording_year', song.recording_year) or "",
                'publisher': self._get_effective_value(sid, 'publisher', song.publisher) or "",
                'album_id': init_id,
                'song_display': f"{disp_artist} - {eff_title}",
                'focus_publisher': focus_publisher
            }
            
        initial_data['mode'] = mode
        
        from ..dialogs.album_manager_dialog import AlbumManagerDialog
        dlg = AlbumManagerDialog(
            self.album_service, 
            self.publisher_service,
            self.contributor_service,
            self.settings_manager,
            initial_data, 
            self, 
            staged_deletions=self._hidden_album_ids
        )
        # Context-Aware Callback
        target_id = initial_album.album_id if initial_album else None
        dlg.album_selected.connect(lambda data: self._on_album_picked_context(data, mode, target_id))
        
        dlg.save_and_select_requested.connect(lambda data: self._on_album_picked_context(data, mode, target_id))
        dlg.album_deleted.connect(self._on_album_deleted_externally)
        
        if dlg.exec() == 2:
             # T-Fix: Handle 'Remove Link' request (Matched to Artist workflow)
             if initial_album:
                 self._on_chip_removed('album', initial_album.album_id, initial_album.title)
             return
        
        # Sync: Re-fetch current selection to ensure memory matches DB (e.g. if album was deleted)
        if self.current_songs:
             from ...data.models.song import Song
             refreshed = []
             dirty_found = False
             for s in self.current_songs:
                  old_album_id = getattr(s, 'album_id', None)
                  song_data = self.library_service.get_song_by_id(s.source_id)
                  if song_data:
                       # If DB album is now different (e.g. deleted), STAGE the change to trip the Amber Alert
                       new_album_id = getattr(song_data, 'album_id', None)
                       if new_album_id != old_album_id:
                            # Use _on_field_changed to ensure it hits the staging buffer and emits the signal
                            self._on_field_changed("album", song_data.album)
                            self._on_field_changed("album_id", new_album_id)
                            dirty_found = True
                       refreshed.append(song_data)
             
             self.current_songs = refreshed
             self.set_songs(self.current_songs, force=True)
             
             # Force Library Refresh to clear the text column
             if hasattr(self, 'parent') and self.parent():
                  try:
                      win = self.window()
                      if hasattr(win, 'library_widget'):
                          win.library_widget.refresh(refresh_filters=False)
                  except:
                      pass

    def _on_album_deleted_externally(self, album_id):
        """Handle album deletion from Manager by staging it for ALL affected songs."""
        if not self.library_service:
            return
            
        # 1. Find every song in the library that belongs to this album via Service
        headers, data = self.library_service.song_service.get_all()
        try:
             alb_id_idx = -1
             for i, h in enumerate(headers):
                 if h in ('SA.AlbumID', 'AlbumID'):
                     alb_id_idx = i
                     break
                     
             source_id_idx = -1
             for i, h in enumerate(headers):
                 if h in ('MS.SourceID', 'SourceID'):
                     source_id_idx = i
                     break
                     
             if alb_id_idx == -1 or source_id_idx == -1:
                 return
        except:
             return
             
        affected_ids = []
        for row in data:
             if row[alb_id_idx] == album_id:
                  affected_ids.append(row[source_id_idx])
                  
        if not affected_ids:
             return
             
        # 2. Stage the removal for all of them
        for sid in affected_ids:
             if sid not in self._staged_changes:
                  self._staged_changes[sid] = {}
             
             self._staged_changes[sid]['album'] = None
             self._staged_changes[sid]['album_id'] = None
        
        # 3. Mark as Hidden (UX only, the Save prompt handles actual DB delete)
        self._hidden_album_ids.add(album_id)
             
        # 4. Broadcast to Library
        self.staging_changed.emit(list(self._staged_changes.keys()))
        self._update_save_state()
        self._refresh_field_values()

    def _on_album_picked(self, album_data):
        """Called when user selects albums from the manager.
        Expecting list of dicts: [{'id': int, 'title': str, 'primary': bool}]
        """
        # Safety / Legacy Fallback
        if not album_data: return
        if isinstance(album_data, int): return # Should not occur with new signal signature

        # 1. Parse Data
        # Ensure we treat it as a list
        if not isinstance(album_data, list): album_data = [album_data]
        
        primary = album_data[0] # First is Primary by convention
        names = [x['title'] for x in album_data]
        ids = [x['id'] for x in album_data]
        
        # 2. Update Hidden Set (If we picked them, they shouldn't be hidden)
        for x in album_data:
            self._hidden_album_ids.discard(x['id'])
            
        # 3. Update UI Chips
        if 'album' in self._field_widgets:
            w = self._field_widgets['album']
            if hasattr(w, 'set_chips'):
                 # Chip Tuple: (id, label, icon, is_user, is_inherit, tooltip, color)
                 chips = []
                 for x in album_data:
                     is_p = x.get('primary', False)
                     color = "amber" if is_p else ""
                     label = x['title']
                     # Visual indicator for primary if multiple
                     if len(album_data) > 1 and is_p:
                         label = f"★ {label}"
                         
                     chips.append((x['id'], label, "💿", False, False, "", color, is_p))
                 w.set_chips(chips)
            elif hasattr(w, 'setText'):
                 w.setText(", ".join(names))

        # 4. Stage Changes
        print(f"DEBUG: Staging Multi-Album Pick: {names} (IDs: {ids})")
        self._on_field_changed("album", names)
        # Store complex objects? No, just names for display. IDs for link.
        self._on_field_changed("album_id", ids)
        
    def _on_album_picked_context(self, data, mode, target_id=None):
        if not data: return
        
        # T-Atomic: Write directly to DB via Service (No Staging) to prevent side-effects on other fields
        new_ids = {item['id'] for item in data}
        
        # Apply to ALL selected songs
        for song in self.current_songs:
            sid = song.source_id
            
            # 1. Get current state (DB Truth)
            curr_albums = self.album_service.get_albums_for_song(sid)
            curr_ids = {a.album_id for a in curr_albums}
            
            # 2. Add New Items
            for nid in new_ids:
                if nid not in curr_ids:
                    self.album_service.link_song_to_album(sid, nid)
            
            # 3. Remove/Replace Logic
            if mode != 'add':
                if target_id and target_id in curr_ids:
                     # Targeted Replace
                     if target_id not in new_ids:
                          self.album_service.remove_song_from_album(sid, target_id)
                elif not target_id:
                    # Global Replace (replace all old with new)
                    for oid in curr_ids:
                        if oid not in new_ids:
                            self.album_service.remove_song_from_album(sid, oid)
        
        # 4. Metadata Update (Artist/Year) - Keep this STAGED (Side Effect behavior)
        if data:
            primary_id = data[0]['id']
            full_album = self.album_service.get_by_id(primary_id)
            if full_album:
                 if full_album.album_artist:
                     self._on_field_changed("album_artist", full_album.album_artist)
                 if full_album.release_year:
                     self._on_field_changed("recording_year", full_album.release_year)
        
        # 5. Refresh UI (Reload from DB to show new links)
        self.set_songs(self.current_songs, force=True)

    def _on_save_select_picked(self, album_data):
        """Callback from Dialog requesting an immediate atomic save."""
        self._on_album_picked(album_data)
        # Surgical Shortcut: Just commit metadata
        self.trigger_save() # ensure save logic reads staged album_id

    def _validate_isrc_field(self, widget, text):
        """
        Validate ISRC field and update text color in real-time.
        Checks for both format validity and duplicates.
        """
        from ...utils.validation import validate_isrc
        
        # Empty is valid (ISRC is optional)
        if not text or not text.strip():
            self.isrc_collision = False
            widget.setProperty("invalid", False)
            widget.setToolTip("")
        
        # 1. Validate Format
        elif not validate_isrc(text):
            self.isrc_collision = False
            widget.setProperty("invalid", True)
            widget.setToolTip("Invalid ISRC Format")
        
        # 2. Check Duplicates (Phase 3)
        else:
            duplicate = self.duplicate_scanner.check_isrc_duplicate(text)
            if duplicate:
                # Check if self-match
                is_self_match = False
                if self.current_songs and len(self.current_songs) == 1:
                    if str(self.current_songs[0].source_id) == str(duplicate.source_id):
                        is_self_match = True
                
                if not is_self_match:
                    self.isrc_collision = True
                    widget.setProperty("warning", True)
                    widget.setToolTip(f"Duplicate ISRC found: {duplicate.name}")
                else:
                    self.isrc_collision = False
                    widget.setProperty("invalid", False)
                    widget.setProperty("warning", False)
                    widget.setToolTip("")
            else:
                self.isrc_collision = False
                widget.setProperty("invalid", False)
                widget.setProperty("warning", False)
                widget.setToolTip("")

        widget.style().unpolish(widget)
        widget.style().polish(widget)
        self._update_save_state()
    
    def _calculate_bulk_value(self, field_def):
        """Determine what to show when 1 or many songs are selected."""
        if not self.current_songs: return None, False, 0

        if field_def.name == 'tags':
            # Unified Tags: Intersection logic using effective values (staging-aware)
            
            # CASE A: Single Song - Preserve Order & Enforce Single Primary Genre (T-82)
            if len(self.current_songs) == 1:
                song = self.current_songs[0]
                # 1. Get DB tags (Used for fallback, but we rely on Staging mostly)
                db_tags = self.tag_service.get_tags_for_source(song.source_id)
                db_tag_strings = [f"{t.category}:{t.tag_name}" for t in db_tags]
                
                # 2. Get Ordered Effective Values
                effective_tags = self._get_effective_value(song.source_id, 'tags', db_tag_strings)
                if not isinstance(effective_tags, list):
                     effective_tags = [effective_tags] if effective_tags else []
                
                chips = []
                found_primary_genre = False
                
                for tag_str in effective_tags:
                     if ':' in tag_str:
                          cat, name = tag_str.split(':', 1)
                     else:
                          cat, name = "Genre", tag_str
                     
                     # Lookup ID
                     tag_obj = self.tag_service.find_by_name(name, cat)
                     tid = tag_obj.tag_id if tag_obj else -1
                     
                     icon = self._get_tag_category_icon(cat)
                     zone = self._get_tag_category_zone(cat)
                     
                     # Logic: Only the FIRST Genre (TCON) is Primary
                     is_tcon = (ID3Registry.get_id3_frame(cat) == "TCON")
                     is_primary = False
                     if is_tcon and not found_primary_genre:
                         is_primary = True
                         found_primary_genre = True
                     
                     chips.append((tid, f"{cat}: {name}", icon, False, False, "", zone, is_primary))
                
                # 3. Add Virtual Status Chip (T-89)
                is_done_eff = self._get_effective_value(song.source_id, 'is_done', song.processing_status)
                is_done = bool(is_done_eff) if is_done_eff is not None else True
                
                # TRANSIENT: Only show the "Pending" task chip. Once marked READY, it disappears.
                if not is_done:
                    status_chip = (-99, "Status: PENDING", "⏳", False, False, 
                                   "Click to toggle processing status", "amber", False)
                    chips.insert(0, status_chip)
                
                return chips, False, 0

            # CASE B: Bulk Selection - Intersection Logic (Sorting enforced, no Primary)
            all_tag_sets = []
            for song in self.current_songs:
                 db_tags = self.tag_service.get_tags_for_source(song.source_id)
                 db_tag_strings = [f"{t.category}:{t.tag_name}" for t in db_tags]
                 
                 effective_tags = self._get_effective_value(song.source_id, 'tags', db_tag_strings)
                 if not isinstance(effective_tags, list):
                      effective_tags = [effective_tags] if effective_tags else []
                 
                 all_tag_sets.append(set(effective_tags))
            
            common_strings = set.intersection(*all_tag_sets) if all_tag_sets else set()
            union_strings = set.union(*all_tag_sets) if all_tag_sets else set()
            
            # Resolve chips (Alphabetical Sort, No Primary in Bulk to avoid confusion)
            chips = []
            for tag_str in sorted(list(common_strings)):
                 if ':' in tag_str:
                      cat, name = tag_str.split(':', 1)
                 else:
                      cat, name = "Genre", tag_str
                 
                 tag_obj = self.tag_service.find_by_name(name, cat)
                 tid = tag_obj.tag_id if tag_obj else -1
                 
                 icon = self._get_tag_category_icon(cat)
                 zone = self._get_tag_category_zone(cat)
                 # In bulk mode, we don't show primary stars to avoid implying specific order
                 
                 chips.append((tid, f"{cat}: {name}", icon, False, False, "", zone, False))
            
            # 3. Add Virtual Status Chip (Bulk)
            statuses = []
            for song in self.current_songs:
                st = self._get_effective_value(song.source_id, 'is_done', song.processing_status)
                statuses.append(bool(st) if st is not None else True)
            
            all_done = all(statuses)
            none_done = not any(statuses)
            
            # TRANSIENT: If everything is READY, don't clutter the tray.
            if not all_done:
                if none_done:
                    status_chip = (-99, "Status: PENDING", "⏳", False, False, "All songs PENDING", "amber", False)
                else:
                    status_chip = (-99, "Status: MIXED", "🔀", True, False, "Mixed processing states", "gray", False)
                chips.insert(0, status_chip)
            
            mixed_count = len(union_strings - common_strings)
            return chips, (mixed_count > 0), mixed_count

        # Handle regular fields
        s0 = self.current_songs[0]
        attr = field_def.model_attr or field_def.name
        v0 = self._get_effective_value(s0.source_id, field_def.name, getattr(s0, attr, ""))
        
        if len(self.current_songs) == 1:
            return v0, False, 0
            
        # T-69: Publisher (Refactored to ID-based Intersection - T-180)
        if field_def.name == 'publisher':
            all_sets = []
            for song in self.current_songs:
                # 1. Get IDs from effective values (staging-aware)
                ids = self._get_effective_value(song.source_id, 'publisher_id', getattr(song, 'publisher_id', []))
                if isinstance(ids, (int, str)) and str(ids).isdigit():
                    ids = [int(ids)]
                elif not isinstance(ids, list):
                    ids = []
                
                # 2. Fallback to names if no IDs yet (Sync)
                if not ids:
                    names_val = self._get_effective_value(song.source_id, 'publisher', getattr(song, 'publisher', []))
                    if isinstance(names_val, str):
                        import re
                        names_val = [names_val] if names_val.strip() else []
                    elif not isinstance(names_val, list):
                        names_val = []
                    
                    for name in names_val:
                        pub = self.publisher_service.find_by_name(name)
                        if pub:
                            ids.append(pub.publisher_id)
                
                all_sets.append(set(ids or []))
            
            common_ids = set.intersection(*all_sets) if all_sets else set()
            union_ids = set.union(*all_sets) if all_sets else set()
            mixed_count = len(union_ids - common_ids)
            
            return list(sorted(list(common_ids))), (mixed_count > 0), mixed_count

        # Bulk Mode: Field Type Specific Logic
        if field_def.field_type == yellberus.FieldType.LIST:
             all_sets = []
             import re
             # T-Fix: Only split on internal delimiter |||, never on text content.
             delimiters = r'\|\|\|'

             for song in self.current_songs:
                  val = self._get_effective_value(song.source_id, field_def.name, getattr(song, attr, ""))
                  if isinstance(val, list):
                       items = [str(x).strip() for x in val if str(x).strip()]
                  elif isinstance(val, str):
                       items = [x.strip() for x in re.split(delimiters, val) if x.strip()]
                  else:
                       items = []
                  all_sets.append(set(items))
             
             common = set.intersection(*all_sets) if all_sets else set()
             union = set.union(*all_sets) if all_sets else set()
             is_multiple = len(common) != len(union) if all_sets else False
             return list(sorted(list(common))), is_multiple, len(union - common)

        # Standard scalar comparison
        is_multiple = False
        for song in self.current_songs[1:]:
            v_other = self._get_effective_value(song.source_id, field_def.name, getattr(song, attr, ""))
            if v_other != v0:
                is_multiple = True
                break
        
        return v0 if not is_multiple else None, is_multiple, (1 if is_multiple else 0)

    def _get_effective_value(self, song_id, field_name, db_value):
        """Lookup staged value, fallback to DB."""
        if song_id in self._staged_changes and field_name in self._staged_changes[song_id]:
            return self._staged_changes[song_id][field_name]
        return db_value

    def _get_tag_category_icon(self, category):
        """Get icon emoji for a tag category."""
        return ID3Registry.get_category_icon(category, default="📦")

    def _get_tag_category_zone(self, category):
        """Get color zone for a tag category."""
        # Map ID3Registry colors to zones
        # This is a simplified mapping - you might want to enhance this
        color = ID3Registry.get_category_color(category, default="#888888")
        # Simple color to zone mapping
        color_to_zone = {
            "#FFB84D": "amber",  # Genre
            "#32A8FF": "blue",   # Mood
            "#888888": "gray",   # Default
        }
        return color_to_zone.get(color, "gray")

    def _on_field_changed(self, field_name, value, song_id=None):
        """Stage the change for the current selection."""
        if song_id is not None:
             # Targeted Stage (Differential Edit)
             if song_id not in self._staged_changes:
                  self._staged_changes[song_id] = {}
             self._staged_changes[song_id][field_name] = value
        else:
             # Bulk Stage
             for song in self.current_songs:
                 if song.source_id not in self._staged_changes:
                     self._staged_changes[song.source_id] = {}
                 self._staged_changes[song.source_id][field_name] = value
            
        self._update_header()
        self._update_save_state()
        self._validate_done_gate()
        self._projected_timer.start(500)
        self.staging_changed.emit(list(self._staged_changes.keys()))

    def _get_latest_chips(self, field_name: str) -> List[tuple]:
        """Unified method to get chip data (tuples) for a field, considering staged changes."""
        field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
        if not field_def: return []
        
        effective_val, is_multiple, mixed_count = self._calculate_bulk_value(field_def)
        
        if field_name == 'tags':
            # Tags handle their own complex chip formatting in _calculate_bulk_value
            chips = effective_val or []
            if mixed_count > 0:
                # Add "X Mixed" dummy chip
                chips.append((-1, f"{mixed_count} Mixed", "🔀", True, False, "", "gray", False))
            return chips

        # T-Clean: Fetch LIVE from DB for Album (Atomic Attribute)
        if field_name == 'album':
            if not self.current_songs: return []
            # Atomic Fetch from DB
            live_albums = self.album_service.get_albums_for_song(self.current_songs[0].source_id)
            chips = []
            for i, alb in enumerate(live_albums):
                chips.append((alb.album_id, alb.title, "💿", False, False, alb.title, field_def.zone or "amber", i==0))
            return chips
            
        # Convert to identities for the Chip Tray
        chips = []
        # T-Fix: Delimiters removed. Strict List adherence.
            
        raw_names = effective_val if isinstance(effective_val, list) else ([effective_val] if effective_val else [])
        names = []
        for rn in raw_names:
            if not isinstance(rn, str):
                names.append(rn)
                continue
                
            # T-91: Support safe multi-value splitting (|||) for all fields
            if '|||' in rn:
                split_parts = rn.split('|||')
                names.extend([p.strip() for p in split_parts if p.strip()])
                continue

            # T-Fix: Removed legacy splitting logic.
            # We strictly respect the data structure (List vs String).
            # If it's a string, it's ONE chip.
            names.append(rn)

        chips = []
        for i, n in enumerate(names):
            if field_name == 'publisher':
                # ID-based Lookup (T-180)
                pub = None
                pid = 0
                if isinstance(n, int):
                    pid = n
                    pub = self.publisher_service.get_by_id(pid)
                else:
                    # Fallback for legacy staged names (Read-Only)
                    # T-Fix: Use find_by_name to avoid creating duplicates when rendering stale names (e.g. during rename)
                    pub = self.publisher_service.find_by_name(str(n).strip())
                    pid = pub.publisher_id if pub else 0
                
                if pub:
                    display_name = pub.publisher_name
                    if pub.parent_publisher_id:
                        parent = self.publisher_service.get_by_id(pub.parent_publisher_id)
                        if parent:
                            display_name = f"{pub.publisher_name} [{parent.publisher_name}]"
                    
                    chips.append((pid, display_name, "🏢", False, False, "Master Owner (Direct)", field_def.zone or "amber", False))
            else:
                # Standard Contributor (Artist) via Service
                # FIX: Use get_by_name to prevent 'Ghost Creation' when rendering stale 'performers' strings 
                # (e.g. during a rename operation before the refresh completes).
                artist = self.contributor_service.get_by_name(str(n).strip())
                
                if artist:
                    icon = "👤" if artist.type == "person" else "👥"
                    chips.append((artist.contributor_id, str(n), icon, False, False, "", field_def.zone or "amber", False))
                else:
                    # Unresolved reference (stale string or missing identity)
                    chips.append((0, str(n), "⚠️", False, False, "Unresolved Reference", "gray", False))
        
        # Mixed indicator for multi-edit (T-Mixed)
        if mixed_count > 0:
             chips.append((-1, f"{mixed_count} Mixed", "🔀", True, False, "", "gray", False))
             
        return chips

    def _on_status_toggled(self):
        """Toggle the ready/pending state via the staging system (T-89)."""
        # Determine the target state (toggle based on selection)
        statuses = []
        for song in self.current_songs:
            st = self._get_effective_value(song.source_id, 'is_done', song.processing_status)
            statuses.append(bool(st) if st is not None else True)
            
        all_done = all(statuses)
        new_status = not all_done # Toggle: If all are done, make them pending. Else make them all done.
        
        # Stage the change
        self._on_field_changed("is_done", 1 if new_status else 0)

        # 2. Sync legacy column via staging (REMOVED - Field is Legacy)
        # self._on_field_changed("is_done", 1 if is_ready else 0)

        # 3. Update UI
        self._update_status_visuals(new_status)
        self._refresh_field_values() # Update the tag tray
        self._validate_done_gate()   # Re-check if it can be marked done again (safety)
        self.filter_refresh_requested.emit()

    def _update_status_visuals(self, is_done):
        """Visual state is now handled by the Status Chip in the tags tray."""
        pass

    def _get_validation_errors(self) -> List[str]:
        """Centralized validation logic driven by Yellberus Registry."""
        if not self.current_songs:
            return []

        missing_reasons = set()
        
        # Use Official Yellberus Validation (Single Source of Truth)
        for song in self.current_songs:
            # 1. Construct Row Data matching FIELDS order
            validation_row = []
            for field in yellberus.FIELDS:
                attr = field.model_attr or field.name
                val = self._get_effective_value(song.source_id, field.name, getattr(song, attr, ""))
                validation_row.append(val)

            # 2. Check Completeness
            incomplete_fields = yellberus.check_completeness(validation_row)
            for f_name in incomplete_fields:
                field_def = next((f for f in yellberus.FIELDS if f.name == f_name), None)
                if field_def and field_def.ui_header:
                    missing_reasons.add(f"Missing: {field_def.ui_header}")
                else:
                    missing_reasons.add(f"Missing: {f_name}")

            # 3. Call Format Validation
            failed_fields = yellberus.validate_row(validation_row)

            # 4. Format Errors
            for f_name in failed_fields:
                field_def = next((f for f in yellberus.FIELDS if f.name == f_name), None)
                if not field_def: continue

                # Special phrasing for Groups
                if f_name in ['performers', 'groups']:
                    missing_reasons.add("Required: Performers / Groups")
                elif field_def.ui_header:
                    missing_reasons.add(f"Invalid: {field_def.ui_header}")
                else:
                    missing_reasons.add(f"Invalid: {field_def.name}")
            
        # 4. ISRC Collision Check (Global state)
        if getattr(self, 'isrc_collision', False):
            missing_reasons.add("Duplicate ISRC Detected")
            
        return sorted(list(missing_reasons))

    def _validate_done_gate(self):
        """Validation state is now informative via the Status Chip audit."""
        pass

    def _update_save_state(self):
        has_staged = len(self._staged_changes) > 0
        self.btn_discard.setEnabled(has_staged)
        # User Req: Save always active (for renaming triggers, etc.)
        self.btn_save.setEnabled(True)
        
        # Check Collision (Phase 3)
        if self.isrc_collision:
            self.btn_save.setText("ISRC")
            self.btn_save.setProperty("alert", True)
        else:
            self.btn_save.setText("Save")
            self.btn_save.setProperty("alert", False)

        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)

        self._projected_timer.start(500)

    def _on_save_clicked(self, checked=False, commit_deletions=True):
        """Emit the entire staged buffer for the MainWindow to commit."""
        # Allow saving even if no fields changed (e.g. to trigger rename)
        changes_to_emit = self._staged_changes.copy()
        
        # T-Integrity: Validate all staged changes against Yellberus before saving
        # This catches "202" (invalid year) or bad ISRC patterns
        errors = []
        for song_id, changes in changes_to_emit.items():
            for field_name, raw_val in changes.items():
                 if field_name in ('album', 'album_id'): continue # Skip logic fields
                 
                 field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
                 if field_def:
                      try:
                          # Verify cast works (raises ValueError if bad)
                          yellberus.cast_from_string(field_def, raw_val)
                      except ValueError as e:
                          errors.append(str(e))
        
        if errors:
             from PyQt6.QtWidgets import QMessageBox
             QMessageBox.warning(self, "Invalid Data", "\n".join(set(errors)))
             self.btn_save.setChecked(False) # Unlatch if checkable
             return

        if not changes_to_emit and self.current_songs:
            # Force inclusion of current songs if button was clicked but no edits made
            for song in self.current_songs:
                changes_to_emit[song.source_id] = {} # Empty dict implies "Save Current State"
        
        # Auto-fill Year logic (User Request)
        from datetime import datetime
        import re
        from datetime import datetime
        
        # Determine Default Year (Configurable via Settings)
        default_year_setting = 0
        if self.settings_manager:
            default_year_setting = self.settings_manager.get_default_year()
            
        # Only apply auto-fill if a default year is explicitly configured (User Request)
        for song_id in list(changes_to_emit.keys()):
            # Ensure sub-dict exists
            if song_id not in changes_to_emit:
                    changes_to_emit[song_id] = {}
                    
            changes = changes_to_emit[song_id]
            
            # --- Auto-fill Year logic ---
            if default_year_setting > 0:
                # Check if year is valid
                has_year_change = 'recording_year' in changes
                effective_year = None
                
                if has_year_change:
                    val = changes['recording_year']
                    # Treating 0, "", None as empty
                    if val:
                        try:
                            effective_year = int(val)
                        except:
                            effective_year = 0
                else:
                    # Check current selection first (Performance: Avoid DB hit during save loop)
                    song = next((s for s in self.current_songs if s.source_id == song_id), None)
                    if not song:
                        # Fallback to DB if song not in current view (unlikely but safe)
                        song = self.library_service.get_song_by_id(song_id)
                    
                    if song:
                            effective_year = song.recording_year
                
                # If effectively empty, force it
                if not effective_year:
                    changes['recording_year'] = default_year_setting

            # --- Composer Logic (Hardcoded Splitter) ---
            if 'composers' in changes:
                val = changes['composers']
                if val and isinstance(val, str) and val.endswith(','):
                    # 1. Strip trailing comma
                    clean_val = val[:-1]
                    # 2. Inject ", " between lower and UPPER
                    # Regex: Look for [a-z] followed by [A-Z]
                    formatted = re.sub(r'([a-z])([A-Z])', r'\1, \2', clean_val)
                    changes['composers'] = formatted
        
        self.save_requested.emit(changes_to_emit, self._hidden_album_ids)
        
        # Optimistic UI update or wait for refresh?
        # Usually Main Window refreshes us.
        self._staged_changes.clear()
        self._hidden_album_ids.clear()
            
        self._update_save_state()
        
        # Broadcast dirty state (Magenta Alert)
        self.staging_changed.emit(list(self._staged_changes.keys()) if self._staged_changes else [])

    def trigger_save(self):
        """Public slot to trigger save (e.g. from Ctrl+S shortcut)."""
        if self.btn_save.isEnabled():
            self._on_save_clicked()

    def _on_discard_clicked(self, checked=False):
        self._staged_changes = {}
        self._hidden_album_ids.clear()
        
        # Re-fetch from DB to get the original data (restores the labels/links)
        ids = [s.source_id for s in self.current_songs]
        if ids:
            self.current_songs = self.library_service.get_songs_by_ids(ids)
            
        self.set_songs(self.current_songs, force=True)
        self.staging_changed.emit([]) # Clear highlights in library
        self.status_message_requested.emit("Changes discarded", "info")

    def clear_staged(self, song_ids=None):
        """Remove IDs from staging (post-save cleanup)."""
        if song_ids is None:
            self._staged_changes = {}
            self._hidden_album_ids.clear()
        else:
            for sid in song_ids:
                if sid in self._staged_changes:
                    del self._staged_changes[sid]
        self._update_save_state()
        self.staging_changed.emit(list(self._staged_changes.keys()))

    def _clear_fields(self):
        self._field_widgets = {}
        while self.field_layout.count():
            item = self.field_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def eventFilter(self, source, event):
        from PyQt6.QtCore import QEvent, QPoint
        # Handle LED hover for projected path display
        if hasattr(self, 'save_led') and source == self.save_led:
            if event.type() == QEvent.Type.Enter:
                # Reveal path on hover as an Overlay (Absolute Position)
                if self.lbl_projected_path.text():
                    # Calculate coordinates relative to LED
                    led_pos = self.save_led.mapTo(self, QPoint(0, 0))
                    target_width = self.width() - 20
                    
                    self.lbl_projected_path.setFixedWidth(target_width)
                    self.lbl_projected_path.adjustSize()
                    target_height = self.lbl_projected_path.height()
                    
                    # Ensure it didn't collapse (sanity check)
                    if target_height < 30: target_height = 30
                    self.lbl_projected_path.setFixedHeight(target_height)
                    
                    target_y = led_pos.y() - target_height - 5
                    self.lbl_projected_path.move(10, target_y)
                    
                    self.lbl_projected_path.raise_()
                    self.lbl_projected_path.setVisible(True)
                    
            elif event.type() == QEvent.Type.Leave:
                # Always hide on leave
                self.lbl_projected_path.setVisible(False)
        # Handle header left-click for filename parser
        elif hasattr(self, 'header_label') and source == self.header_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                from PyQt6.QtCore import Qt
                if event.button() == Qt.MouseButton.LeftButton:
                    self._open_filename_parser()
                    return True
        return super().eventFilter(source, event)

    def _get_staged_song(self, original_song):
        """Return a copy of the song with staged changes applied."""
        song = copy.copy(original_song)
        sid = original_song.source_id
        
        if sid in self._staged_changes:
            staged = self._staged_changes[sid]
            # Apply known attributes logic
            for field_name, value in staged.items():
                if field_name == 'album_id':
                     song.album_id = value
                     continue
                     
                field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
                if field_def:
                    try:
                        attr = field_def.model_attr or field_def.name
                        # NEW: Cast string from UI to proper Python type (e.g. List, Int)
                        # Wrap in try/except to prevent Preview Crash on invalid input ("202")
                        casted_value = yellberus.cast_from_string(field_def, value)
                        setattr(song, attr, casted_value)
                    except ValueError:
                        pass # Ignore invalid values for path preview
        return song

    def _do_update_projected_path(self):
        """Debounced wrapper for projected path calculation."""
        self._update_projected_path()

    def _update_projected_path(self):
        """Calculate and display where the file will move if saved."""
        if not self.current_songs or len(self.current_songs) != 1:
            self.lbl_projected_path.setVisible(False)
            self.lbl_projected_path.setText("")
            return

        original = self.current_songs[0]
        staged_song = self._get_staged_song(original)
        
        # Optimization: Move disk check to background thread to prevent UI freeze on network paths
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class ConflictCheckWorker(QThread):
            result_ready = pyqtSignal(str, bool, bool, bool) # target, has_conflict, has_changed, is_error
            
            def __init__(self, renaming_service, song, staged_song):
                super().__init__()
                self.renaming_service = renaming_service
                self.song = song
                self.staged_song = staged_song
                
            def run(self):
                try:
                    target = self.renaming_service.calculate_target_path(self.staged_song)
                    
                    is_self = False
                    if self.song.path and os.path.normpath(self.song.path) == os.path.normpath(target):
                        is_self = True
                        
                    has_conflict = not is_self and self.renaming_service.check_conflict(target)
                    has_changed = not is_self
                    self.result_ready.emit(target, has_conflict, has_changed, False)
                except Exception as e:
                    self.result_ready.emit(str(e), True, True, True)

        # Cleanup old worker if any
        if hasattr(self, "_path_worker") and self._path_worker.isRunning():
            self._path_worker.terminate()
            self._path_worker.wait()

        self._path_worker = ConflictCheckWorker(self.renaming_service, original, staged_song)
        self._path_worker.result_ready.connect(self._on_projected_path_result)
        self._path_worker.start()

    def _on_projected_path_result(self, target, has_conflict, has_changed, is_error):
        """Handle background result."""
        if is_error:
            self.lbl_projected_path.setText(target)
            self.lbl_projected_path.setProperty("conflict", "true")
            self.save_led.setGlowColor("#FF0000")
            self.save_led.setActive(True)
        else:
            # Clean display: normpath fixes the \ / mix
            display_path = os.path.normpath(target)
            self.lbl_projected_path.setText(display_path)
            
            # User Req: LED Red/Bold if path is different from DB (has_changed) or is a conflict
            is_alert = has_changed or has_conflict
            
            # The path is now strictly HOVER-ONLY to reclaim vertical space
            self.lbl_projected_path.setVisible(False)
            
            if is_alert:
                 self.lbl_projected_path.setProperty("alert", True)
                 if has_conflict: 
                     self.save_led.setGlowColor("#FF0000") # Red Failure
                     self.save_led.setActive(True)
                 elif has_changed:
                     self.save_led.setGlowColor("#FF4444") # Red Warning
                     self.save_led.setActive(True)
            else:
                 self.lbl_projected_path.setProperty("alert", False)
                 self.save_led.setActive(False)

    def trigger_search(self):
        """Public slot to trigger the search menu (e.g. from shortcuts)."""
        # T-96 Shortcut calls the ACTION, not the MENU
        self._on_web_search()

    def _show_search_menu_btn(self):
        """Handle Left-Click on the Menu Button."""
        # Show menu anchored to bottom-left of the menu button
        p = self.btn_search_menu.mapToGlobal(self.btn_search_menu.rect().bottomLeft())
        self._show_search_menu_internal(p)

    def _show_search_menu(self, pos):
        """Handle Right-Click Context Menu on main button."""
        # Show menu at mouse position (relative to widget)
        p = self.btn_search_action.mapToGlobal(pos)
        self._show_search_menu_internal(p)

    def _show_search_menu_internal(self, global_pos, field_def=None):
        """Shared Menu Builder. field_def: if provided, adds 'Search [Field] on...' action."""
        menu = QMenu(self)
        providers = ["Google", "Spotify", "YouTube", "MusicBrainz", "Discogs", "ZAMP"]
        
        # Get current provider dynamically
        # Get current provider dynamically
        s_mgr = self.settings_manager
        current = "Google"
        if s_mgr:
             current = s_mgr.get_search_provider()
        
        for p in providers:
            action = QAction(p, self)
            action.setCheckable(True)
            action.setChecked(p == current)
            
            def set_provider(checked, name=p):
                if s_mgr:
                    s_mgr.set_search_provider(name)
                    s_mgr.sync()
                self._search_provider = name
                self.btn_search_action.setToolTip(f"Search Metadata via {name}")
                # Update any open menus if needed? No, just close.
                
            action.triggered.connect(set_provider)
            menu.addAction(action)
        
        if field_def:
            menu.addSeparator()
            act_search = QAction(f"Search {field_def.ui_header} on {current}", self)
            act_search.triggered.connect(lambda: self._on_web_search(field_def))
            menu.addAction(act_search)
            
        menu.exec(global_pos)

    def _on_web_search(self, field_def=None):
        """Launch web search using SearchService."""
        if not self.current_songs: return
        song = self.current_songs[0]
        
        # 1. Resolve Search Service
        search_svc = getattr(self.library_service, 'search_service', None)
        if not search_svc: return

        # 2. Determine Provider
        s_mgr = getattr(self, 'settings_manager', None) or getattr(self.library_service, 'settings_manager', None)
        provider = self._search_provider
        if s_mgr:
             provider = s_mgr.get_search_provider() or provider
        
        # 3. Gather Draft State (Pure UI Scraping)
        def get_widget_text(fname):
            w = self._field_widgets.get(fname)
            if not w: return ""
            if hasattr(w, 'get_names'): # ChipTrayWidget
                names = w.get_names()
                return " ".join(names) if names else ""
            if hasattr(w, 'text'): # QLineEdit / GlowLineEdit
                return w.text()
            return ""

        # Dump all relevant fields to draft dict
        # We only really need performers, unified_artist, title, and the target field
        draft_values = {
            'title': get_widget_text('title'),
            'performers': get_widget_text('performers'),
            'unified_artist': get_widget_text('unified_artist'),
        }
        
        if field_def:
            draft_values[field_def.name] = get_widget_text(field_def.name)

        # 4. Delegate to Service (URL Generation + Logic)
        url = search_svc.prepare_search(
            song=song,
            draft_values=draft_values,
            preferred_provider=provider,
            field_def=field_def
        )

        # 5. Launch
        if url:
            QDesktopServices.openUrl(QUrl(url))



    def _get_magnifier_icons(self):
        """Lazy create Start/Hover magnifier icons."""
        if not hasattr(self, '_icons_magnifier'):
            def draw_icon(color_str, glow=False):
                # 20x20 to allow glow spill (icon is centered ~16x16)
                pix = QPixmap(20, 20)
                pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pix)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Center offset
                ox, oy = 2, 2
                
                if glow:
                    # Glow Pass (Thick, Low Opacity)
                    glow_color = QColor(color_str)
                    glow_color.setAlpha(100)
                    painter.setPen(QPen(glow_color, 4)) # Fat pen
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(ox+3, oy+3, 8, 8)
                    painter.drawLine(ox+10, oy+10, ox+14, oy+14)
                
                # Sharp Pass
                painter.setPen(QColor(color_str))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(ox+3, oy+3, 8, 8)
                painter.drawLine(ox+10, oy+10, ox+14, oy+14)
                
                painter.end()
                return QIcon(pix)

            # Return Tuple: (Normal, Hover)
            # Normal: #CCCCCC (Light Grey)
            # Hover: #FFC66D (Amber) with Glow
            self._icons_magnifier = (draw_icon("#CCCCCC", glow=False), draw_icon("#FFC66D", glow=True))
            
        return self._icons_magnifier

    def _open_filename_parser(self):
        """
        Open the Filename -> Metadata parser for CURRENTLY STAGED songs.
        Applies results to STAGING, not DB.
        """
        if not self.current_songs: return
        
        # We pass the original song objects, but we want the parser to 
        # potentially see staged Path changes? 
        # Actually pattern engine reads song.path.
        # If user renamed text in SidePanel (path is read-only usually), it won't affect this.
        # So we just use self.current_songs.
        
        from ..dialogs.filename_parser_dialog import FilenameParserDialog
        dlg = FilenameParserDialog(self.current_songs, self)
        if dlg.exec():
            results = dlg.get_parsed_data()
            if results:
                self._apply_parsed_staging(results)
                # Auto-Save: Commit changes immediately (T-UserRequest)
                self._on_save_clicked()

    def _apply_parsed_staging(self, results: dict):
        """
        Apply parsed metadata to STAGING BUFFER and update UI.
        results: {source_id: {field: value}}
        """
        updates_count = 0
        isrc_conflicts = []  # Track ISRC conflicts for warning

        # Map IDs to Song objects for DB fallback
        song_map = {s.source_id: s for s in self.current_songs}

        for source_id, data in results.items():
            updates_count += 1

            # Helper to stage a value
            def stage(field, new_val):
                if source_id not in self._staged_changes:
                    self._staged_changes[source_id] = {}
                self._staged_changes[source_id][field] = new_val

            # Title
            if "title" in data:
                new_title = data["title"]
                if new_title and str(new_title).strip():
                    stage("title", new_title)

            # Artist (Unified / Performers) - APPEND if not exists
            if "performers" in data:
                val = data["performers"].strip()
                if val:
                    # Get DB value for fallback
                    song_obj = song_map.get(source_id)
                    db_performers = getattr(song_obj, 'performers', []) if song_obj else []

                    # Get effective performers (Staged or DB)
                    current_performers = self._get_effective_value(source_id, "performers", db_performers) or []

                    # Ensure list
                    if not isinstance(current_performers, list):
                        current_performers = list(current_performers) if current_performers else []

                    # Append if not present
                    if val not in current_performers:
                        updated_performers = list(current_performers) + [val]
                        stage("performers", updated_performers)

            # Album - APPEND if not exists
            if "album" in data:
                val = data["album"].strip()
                if val:
                    # Get DB value for fallback
                    song_obj = song_map.get(source_id)
                    db_album = getattr(song_obj, 'album', []) if song_obj else []

                    # Normalize to list
                    if isinstance(db_album, str):
                        db_album = [db_album] if db_album else []

                    # Get effective album (Staged or DB)
                    current_album = self._get_effective_value(source_id, "album", db_album) or []

                    # Ensure list
                    if not isinstance(current_album, list):
                        current_album = [current_album] if current_album else []

                    # Append if not present
                    if val not in current_album:
                        updated_album = list(current_album) + [val]
                        stage("album", updated_album)

            # Publisher - APPEND if not exists (get-or-create)
            if "publisher" in data:
                val = data["publisher"].strip()
                if val:
                    # Get or create publisher entity
                    from ...business.services.publisher_service import PublisherService
                    pub_service = PublisherService()
                    publisher, _ = pub_service.get_or_create(val)

                    # Get DB value for fallback
                    song_obj = song_map.get(source_id)
                    db_publisher = getattr(song_obj, 'publisher', []) if song_obj else []

                    # Normalize to list
                    if isinstance(db_publisher, str):
                        db_publisher = [db_publisher] if db_publisher else []

                    # Get effective publisher (Staged or DB)
                    current_publisher = self._get_effective_value(source_id, "publisher", db_publisher) or []

                    # Ensure list
                    if not isinstance(current_publisher, list):
                        current_publisher = [current_publisher] if current_publisher else []

                    # Append if not present
                    if val not in current_publisher:
                        updated_publisher = list(current_publisher) + [val]
                        stage("publisher", updated_publisher)

                        # Also track publisher_id for precise linking (T-180)
                        db_publisher_id = getattr(song_obj, 'publisher_id', []) if song_obj else []
                        if isinstance(db_publisher_id, int):
                            db_publisher_id = [db_publisher_id]
                        current_publisher_id = self._get_effective_value(source_id, "publisher_id", db_publisher_id) or []
                        if not isinstance(current_publisher_id, list):
                            current_publisher_id = [current_publisher_id] if current_publisher_id else []

                        if publisher.publisher_id not in current_publisher_id:
                            updated_publisher_id = list(current_publisher_id) + [publisher.publisher_id]
                            stage("publisher_id", updated_publisher_id)

            # ISRC - Warn on conflicts
            if "isrc" in data:
                val = data["isrc"].strip().upper()  # ISRC should be uppercase
                if val:
                    # Get DB value for fallback
                    song_obj = song_map.get(source_id)
                    db_isrc = getattr(song_obj, 'isrc', None) if song_obj else None

                    # Get effective ISRC (Staged or DB)
                    current_isrc = self._get_effective_value(source_id, "isrc", db_isrc)

                    if current_isrc and current_isrc != val:
                        # Conflict detected
                        isrc_conflicts.append({
                            'song': song_obj,
                            'source_id': source_id,
                            'existing': current_isrc,
                            'new': val
                        })
                    elif not current_isrc:
                        stage("isrc", val)

            # Year
            if "recording_year" in data:
                try:
                    stage("recording_year", int(data["recording_year"]))
                except: pass

            # BPM
            if "bpm" in data:
                try:
                    stage("bpm", int(data["bpm"]))
                except: pass

            # Genre (Tag)
            if "genre" in data:
                genre = data["genre"]
                new_tag = f"Genre:{genre}"

                # Get DB value for fallback
                song_obj = song_map.get(source_id)
                db_tags = getattr(song_obj, 'tags', []) if song_obj else []

                # Get effective tags (Staged or DB)
                current_tags = self._get_effective_value(source_id, "tags", db_tags) or []

                # Ensure list (safety)
                if not isinstance(current_tags, list):
                    current_tags = list(current_tags) if current_tags else []

                # Append if not present
                if new_tag not in current_tags:
                    updated_tags = list(current_tags) + [new_tag]
                    stage("tags", updated_tags)

        # Handle ISRC conflicts
        if isrc_conflicts:
            self._handle_isrc_conflicts_staging(isrc_conflicts)

        if updates_count > 0:
            # Refresh UI to show new staged values
            self._refresh_field_values()
            self._update_save_state()
            self._validate_done_gate()

            self.staging_changed.emit(list(self._staged_changes.keys()))

    def _handle_isrc_conflicts_staging(self, conflicts: list):
        """
        Handle ISRC conflicts in staging mode by asking user which value to use.
        conflicts: List of dicts with keys: 'song', 'source_id', 'existing', 'new'
        """
        from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox

        if not conflicts:
            return

        # Build summary message
        conflict_count = len(conflicts)
        summary = f"Found {conflict_count} ISRC conflict(s). ISRC codes should be unique identifiers.\n\n"

        for i, conflict in enumerate(conflicts[:5], 1):  # Show first 5
            song_title = conflict['song'].title if conflict['song'] else "Unknown"
            summary += f"{i}. '{song_title}':\n"
            summary += f"   Existing: {conflict['existing']}\n"
            summary += f"   From filename: {conflict['new']}\n\n"

        if conflict_count > 5:
            summary += f"... and {conflict_count - 5} more.\n\n"

        summary += "What would you like to do?"

        # Create choice dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("ISRC Conflicts Detected")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        msg_label = QLabel(summary)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # Options
        keep_existing = QRadioButton("Keep existing ISRC values (recommended)")
        keep_existing.setChecked(True)
        layout.addWidget(keep_existing)

        overwrite = QRadioButton("Overwrite with values from filenames")
        layout.addWidget(overwrite)

        skip = QRadioButton("Skip these songs entirely")
        layout.addWidget(skip)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if overwrite.isChecked():
                # Stage the new ISRC values
                for conflict in conflicts:
                    source_id = conflict['source_id']
                    if source_id not in self._staged_changes:
                        self._staged_changes[source_id] = {}
                    self._staged_changes[source_id]['isrc'] = conflict['new']

                # Refresh UI
                self._refresh_field_values()
                self._update_save_state()
                QMessageBox.information(self, "ISRCs Staged", f"Staged {len(conflicts)} ISRC updates. Click Save to apply.")
            elif skip.isChecked():
                # Do nothing, conflicts are already skipped
                QMessageBox.information(self, "Skipped", f"Skipped {len(conflicts)} songs with ISRC conflicts.")
            # else keep_existing: already handled (nothing done during initial processing)

    def _open_scrubber(self):
        """Open the ScrubberDialog for the current song."""
        if not self.current_songs:
            return
            
        song = self.current_songs[0]
        from ..dialogs.scrubber_dialog import ScrubberDialog
        
        dlg = ScrubberDialog(song, self.settings_manager, self.library_service, parent=self)
        
        # T-Fix: mimic LibraryWidget behavior
        # Ensure genre changes in scrubber immediately update this panel (e.g. status status)
        dlg.genre_changed.connect(lambda _: self.refresh_content())
        
        dlg.exec()
        
        self.refresh_content()
        self.filter_refresh_requested.emit()

    def refresh_content(self):
        """Refetch current songs from DB and update UI to match latest state."""
        if not self.current_songs:
            return
        
        fresh_songs = []
        for s in self.current_songs:
            if s.source_id:
                fresh = self.library_service.get_song_by_id(s.source_id)
                if fresh:
                    fresh_songs.append(fresh)

        # Update reference and refresh UI values
        if fresh_songs:
            self.current_songs = fresh_songs
            self._update_header()
            self._refresh_field_values()

    def _show_header_context_menu(self, pos):
        """Show context menu for Side Panel Header (T-108)."""
        if not self.current_songs:
            return
            
        menu = QMenu(self)
        
        # Add Parse Filename option first
        action_parse = QAction("Parse Metadata from Filename", self)
        action_parse.triggered.connect(self._open_filename_parser)
        menu.addAction(action_parse)
        menu.addSeparator()
        
        # Determine current artist name displayed
        current_text = self.header_label.text()
        if " - " in current_text:
            display_artist = current_text.split(" - ")[0].strip()
        else:
            display_artist = current_text # Fallback
            
        action_stats = QAction(f"View Statistics: {display_artist}", self)
        action_stats.triggered.connect(lambda: self._open_artist_stats(display_artist))
        menu.addAction(action_stats)
        
        menu.exec(self.header_label.mapToGlobal(pos))

    def _show_title_context_menu(self, global_pos):
        """Show tools menu for the Title field."""
        if not self.current_songs: return
        
        menu = QMenu(self)
        
        act_sentence = QAction("To Sentence Case", self)
        act_sentence.triggered.connect(self._sentence_case_title)
        menu.addAction(act_sentence)
        
        act_title = QAction("To Title Case", self)
        act_title.triggered.connect(self._title_case_title)
        menu.addAction(act_title)
        
        menu.exec(global_pos)

    def _sentence_case_title(self):
        """Convert title to Sentence case (First letter upper, rest lower) with protections."""
        w = self._field_widgets.get('title')
        if not w or not hasattr(w, 'text'): return
        
        txt = w.text().strip()
        if not txt: return
        
        # Simple Sentence Case: First char upper, rest lower
        # Protection: Keep known acronyms? For now, simple logic.
        new_text = txt.capitalize()
        
        w.setText(new_text)
        # Manually trigger change since we set programmatically
        self._on_field_changed('title', new_text)

    def _title_case_title(self):
        """Convert title to Title Case."""
        w = self._field_widgets.get('title')
        if not w or not hasattr(w, 'text'): return
        
        txt = w.text().strip()
        if not txt: return
        
        import string
        new_text = string.capwords(txt)
        
        w.setText(new_text)
        self._on_field_changed('title', new_text)
        
    def _open_artist_stats(self, artist_name: str):
        """Open the Genre Pie Chart dialog (T-108)."""
        from ..dialogs.artist_stats_dialog import ArtistStatsDialog
        try:
            dlg = ArtistStatsDialog(artist_name, self.library_service, parent=self)
            dlg.exec()
        except ImportError:
            QMessageBox.warning(self, "Missing Dependency", "Matplotlib is required for statistics features.")
        
        # set_songs triggers _refresh_field_values() which updates all UI fields
        # Refresh UI
        self.refresh_content()
