from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QCheckBox, QComboBox, QScrollArea,
    QFrame, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from .glow_factory import GlowLineEdit, GlowButton
import copy
import os
from ...core import yellberus
from ..dialogs.album_manager_dialog import AlbumManagerDialog

class SidePanelWidget(QFrame):
    """
    Metadata Editor (Stage) driven by Yellberus Field Registry.
    Implements a validation-gated 'Done' workflow and staging buffer.
    """
    
    # Signals
    # Emitted when the user clicks 'SAVE ALL'. MainWindow will handle the actual DB/ID3 write.
    save_requested = pyqtSignal(dict) # _staged_changes
    staging_changed = pyqtSignal(list) # list of song_ids in staging
    
    def __init__(self, library_service, metadata_service, renaming_service, duplicate_scanner, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.renaming_service = renaming_service
        self.renaming_service = renaming_service
        self.duplicate_scanner = duplicate_scanner
        
        # QSS Styling Support
        self.setObjectName("SidePanelEditor")
        
        # Dependency Injection for Dialogs
        # We need access to the album repository. Assuming library service has access or can provide it.
        # For strict DI, we should pass it, but for now we'll reach through library_service if needed
        # or assume library_service acts as the repository provider.
        self.album_repo = library_service.album_repo # Assuming exposed
        
        self.isrc_collision = False
        
        self.current_songs = [] # List of Song objects
        self._staged_changes = {} # {song_id: {field_name: value}}
        self._field_widgets = {} # {field_name: QWidget} - Public for testing
        
        # Debounce timer for expensive projected path calculations
        from PyQt6.QtCore import QTimer
        self._projected_timer = QTimer(self)
        self._projected_timer.setSingleShot(True)
        self._projected_timer.timeout.connect(self._do_update_projected_path)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0) # Slammed to the top
        
        # 1. Header Area
        self.header_label = QLabel("No Selection")
        self.header_label.setObjectName("SidePanelHeader")
        self.header_label.setWordWrap(True)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header_label)
        
        
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

        # 4. Footer Actions (Save / Discard)
        footer_frame = QFrame()
        footer_frame.setObjectName("Footer")

        # We'll use a vertical layout for the footer to stack the status pill above the buttons
        footer_main_layout = QVBoxLayout(footer_frame)
        footer_main_layout.setContentsMargins(0, 10, 0, 0)
        footer_main_layout.setSpacing(8)

        # 2. Workflow State (STATUS PILL) - Grouped with LED
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        self.btn_status = GlowButton("PENDING")
        self.btn_status.setObjectName("StatusPill")
        self.btn_status.setCheckable(True)
        self.btn_status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_status.setFixedHeight(32)
        self.btn_status.setMinimumWidth(180) # Force physical weight
        self.btn_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_status.clicked.connect(self._on_status_toggled)
        self.btn_status.installEventFilter(self)

        # The Status LED (indicates Rename/Move pending) - Moved next to READY
        self.save_led = QFrame()
        self.save_led.setObjectName("StatusLED")
        self.save_led.setProperty("state", "off")
        self.save_led.setToolTip("Rename/Move detected")

        # 1b. Projected Path Feedback (Hidden by default, reveal on hover)
        self.lbl_projected_path = QLabel("")
        self.lbl_projected_path.setObjectName("SidePanelProjectedPath")
        self.lbl_projected_path.setWordWrap(True)
        self.lbl_projected_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_projected_path.setVisible(False)
        
        status_layout.addWidget(self.btn_status, 1)
        status_layout.addWidget(self.save_led)

        # Styling via QSS: QPushButton#StatusPill and QPushButton#StatusPill[state="ready"]
        self.btn_status.setEnabled(False)
        footer_main_layout.addWidget(self.lbl_projected_path) # Above status
        footer_main_layout.addWidget(status_row)

        # Button Row (Discard / Save)
        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.btn_discard = GlowButton("Discard")
        self.btn_discard.setObjectName("DiscardButton")
        self.btn_discard.setFixedWidth(80)  # Keep discard small
        self.btn_discard.clicked.connect(self._on_discard_clicked)

        self.btn_save = GlowButton("SAVE")
        self.btn_save.setObjectName("SaveAllButton")
        self.btn_save.setFixedHeight(32)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_save.setEnabled(False)

        button_layout.addWidget(self.btn_discard)
        button_layout.addWidget(self.btn_save)

        footer_main_layout.addWidget(button_row)
        layout.addWidget(footer_frame)

        self._clear_fields()
        self._update_save_state()

    def set_songs(self, songs):
        """Update the editor with fresh song selection."""
        # Capture scroll if specific update (same ID set)
        scroll_pos = 0
        same_selection = False
        if self.current_songs and songs:
             old_ids = sorted([s.source_id for s in self.current_songs])
             new_ids = sorted([s.source_id for s in songs])
             same_selection = (old_ids == new_ids)

        if same_selection:
             scroll_pos = self.scroll.verticalScrollBar().value()

        # Performance: Skip expensive UI rebuild if selection hasn't actually changed
        # This fixes 3-second lag in PyCharm when clicking the same song repeatedly
        if same_selection:
            self.scroll.verticalScrollBar().setValue(scroll_pos)
            return

        # Note: We do NOT clear _staged_changes here.
        # Persistence on selection loss is a key spec.

        # Performance: Only rebuild UI if song count changes (single→bulk or vice versa)
        # For same-count selections, just update widget values
        old_count = len(self.current_songs) if self.current_songs else 0
        new_count = len(songs) if songs else 0
        needs_rebuild = (old_count == 0 or new_count == 0 or
                        (old_count == 1) != (new_count == 1))  # 1 vs many

        self.current_songs = songs
        self._update_header()

        if needs_rebuild:
            self._build_fields()
        else:
            # Just refresh field values without rebuilding widgets
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
            self.btn_status.setEnabled(False)
            self._update_status_visuals(False)
        elif len(self.current_songs) == 1:
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
            
            # Sync Done state
            is_done = self._get_effective_value(song.source_id, "is_done", song.is_done)
            self.btn_status.setChecked(bool(is_done))
            self._update_status_visuals(bool(is_done))
            self.btn_status.setEnabled(True)
        else:
            self.header_label.setText(f"Editing {len(self.current_songs)} Items")
            self.btn_status.setEnabled(True) # In Bulk, MARK DONE applies to all
            self._update_status_visuals(False) # Default look for bulk

    def _build_fields(self):
        """Dynamic UI Factory driven by Yellberus with Grouping."""
        self._clear_fields()
        if not self.current_songs:
            return

        # Separate into Core (Required + Key Identity) and Advanced
        # We explicitly promote performers/groups to Core for better UX, even if technically optional
        all_visible = {f.name: f for f in yellberus.FIELDS if f.visible and f.editable}
        
        # Define Explicit Core Layout (Order Matters)
        core_ordered_names = [
            'performers', 'title', 'album', 'composers', 'publisher', 
            ['recording_year', 'genre'] # CLUSTER ROW
        ]
        
        # Build Core List based on layout, filtering out any that might be invisible/disabled
        core_layout_struct = []
        core_names_flat = set()
        
        for item in core_ordered_names:
            if isinstance(item, list):
                # Cluster
                cluster = [all_visible[n] for n in item if n in all_visible]
                if cluster:
                    core_layout_struct.append(cluster)
                    for c in cluster: core_names_flat.add(c.name)
            elif item in all_visible:
                core_layout_struct.append(all_visible[item])
                core_names_flat.add(item)
                
        # Advanced is everything else
        adv_fields = [f for f in yellberus.FIELDS if f.name in all_visible and f.name not in core_names_flat]

        def add_group(fields, title, show_line=True):
            if not fields: return
            
            if show_line:
                self.field_layout.addSpacing(1) # Gap before line
                # Replace Label with a 555555 Line (2px)
                line = QFrame()
                line.setFixedHeight(2)
                line.setObjectName("FieldGroupLine")
                self.field_layout.addWidget(line)
                self.field_layout.addSpacing(18) # Room before the next field (e.g. ISRC)
            
            for item in fields:
                # Handle Cluster (List of Fields)
                if isinstance(item, list):
                    # Horizontal Row Container
                    h_container = QWidget()
                    h_layout = QHBoxLayout(h_container)
                    h_layout.setContentsMargins(0, 0, 0, 4)
                    h_layout.setSpacing(10) # Gutters between Clustered Fields (Year | Genre)
                    
                    for field in item:
                        # Re-use creation logic (Inline for now to access self)
                        col = QWidget()
                        v_col = QVBoxLayout(col)
                        v_col.setContentsMargins(0,0,0,0)
                        v_col.setSpacing(0) # Slammed
                        
                        label_text = field.ui_header
                        lbl = QLabel(label_text)
                        lbl.setObjectName("FieldLabel")
                        # Styling via QSS: QLabel#FieldLabel
                        
                        eff_val, is_mult = self._calculate_bulk_value(field)
                        widget = self._create_field_widget(field, eff_val, is_mult)
                        self._field_widgets[field.name] = widget
                        
                        v_col.addWidget(lbl)
                        v_col.addWidget(widget)
                        
                        # Set width ratios: Year narrower (1), Genre wider (2)
                        if field.name == 'recording_year':
                            h_layout.addWidget(col, 1)  # 1 part
                        elif field.name == 'genre':
                            h_layout.addWidget(col, 2)  # 2 parts (double width)
                        else:
                            h_layout.addWidget(col)  # Default equal
                        
                    self.field_layout.addWidget(h_container)
                    self.field_layout.addSpacing(8) # Consistent gap
                    continue

                # Handle Single Field (Normal)
                field = item
                
                # Skip Title/Path in Bulk Mode (Spec Alpha)
                if len(self.current_songs) > 1 and field.name in ["Title", "Path"]:
                    continue
                
                # Skip 'is_done' (Status) because we have the big MARK DONE button
                if field.name == "is_done":
                    continue

                container = QWidget()
                row = QVBoxLayout(container)
                row.setContentsMargins(0, 0, 0, 4) # Tighter vertical rhythm
                row.setSpacing(0) # Slammed to input
                
                # Label
                label_text = field.ui_header
                label = QLabel(label_text)
                label.setObjectName("FieldLabel")
                # Styling via QSS: QLabel#FieldLabel
                
                # Determine Current Effective Value
                effective_val, is_multiple = self._calculate_bulk_value(field)
                
                # Create Widget
                edit_widget = self._create_field_widget(field, effective_val, is_multiple)
                self._field_widgets[field.name] = edit_widget
                
                row.addWidget(label)
                row.addWidget(edit_widget)
                self.field_layout.addWidget(container)
                self.field_layout.addSpacing(8) # Consistent gap between fields

        add_group(core_layout_struct, "Core Metadata", show_line=False)
        add_group(adv_fields, "Advanced Details", show_line=True)

    def _refresh_field_values(self):
        """Update existing widget values without rebuilding UI (performance optimization)."""
        if not self.current_songs:
            return

        for field_name, widget in self._field_widgets.items():
            # Find the field definition
            field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
            if not field_def:
                continue

            # Calculate new value
            effective_val, is_multiple = self._calculate_bulk_value(field_def)

            # CRITICAL: Block signals to prevent triggering _on_field_changed
            # This prevents false "unsaved changes" when switching between songs
            widget.blockSignals(True)
            try:
                # Update widget based on type
                if isinstance(widget, QCheckBox):
                    if is_multiple:
                        widget.setCheckState(Qt.CheckState.PartiallyChecked)
                    else:
                        val_bool = str(effective_val).lower() in ("true", "1", "yes") if isinstance(effective_val, str) else bool(effective_val)
                        widget.setChecked(val_bool if effective_val is not None else False)

                elif isinstance(widget, QPushButton):  # Album picker
                    if is_multiple:
                        widget.setText("(Multiple Values)")
                    else:
                        widget.setText(str(effective_val) if effective_val else "(No Album)")

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
            finally:
                # Always restore signals
                widget.blockSignals(False)

    def _create_field_widget(self, field_def, value, is_multiple):
        # Determine strict type or strategy
        is_bool = (field_def.strategy and field_def.strategy.upper() == "BOOLEAN") or \
                  (field_def.field_type.name == "BOOLEAN")

        if is_bool:
            cb = QCheckBox()
            # Handle string 'True'/'False' from some legacy paths just in case
            val_bool = str(value).lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
            
            cb.setChecked(val_bool if value is not None else False)
            if is_multiple: cb.setTristate(True); cb.setCheckState(Qt.CheckState.PartiallyChecked)
            cb.stateChanged.connect(lambda state: self._on_field_changed(field_def.name, bool(state)))
            return cb
            
        # T-46: Album Picker (Special Handling)
        if field_def.name == 'album':
            btn = GlowButton()
            btn.setObjectName("AlbumPickerButton")  # Styling via QSS
            
            # Display Value Logic
            if is_multiple:
                btn.setText("(Multiple Values)")
            else:
                # If value is numeric (ID), we need to resolve it to a name? 
                # Or does 'value' come in as the name? 
                # In current schema, song.album is a string name (Legacy) or ID?
                # We assume we are transitioning. If it's a string, display it.
                btn.setText(str(value) if value else "(No Album)")

            btn.clicked.connect(self._open_album_manager)
            return btn

        # Default: Line Edit for Alpha
        edit = GlowLineEdit()
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
            
        edit.textChanged.connect(lambda text: self._on_field_changed(field_def.name, text))
        
        # Add ISRC validation (real-time text color feedback)
        if field_def.name == 'isrc':
            edit.textChanged.connect(lambda text: self._validate_isrc_field(edit, text))
        
        # Escape to revert
        edit.installEventFilter(self)
        return edit

    def _open_album_manager(self, checked=False):
        """Open the T-46 Album Selector."""
        # Gather initial data from current selection to auto-populate "Create New"
        initial_data = {}
        if self.current_songs:
            song = self.current_songs[0]
            initial_data = {
                'title': song.album or "", # Default title guess
                'artist': song.album_artist or (song.performers[0] if song.performers else ""),
                'year': song.recording_year or "",
                'publisher': song.publisher or ""
            }

        dlg = AlbumManagerDialog(self.album_repo, initial_data, self)
        dlg.album_selected.connect(self._on_album_picked)
        dlg.exec()

    def _on_album_picked(self, album_id, album_name):
        """Callback from Dialog."""
        # Update the UI Button
        if 'album' in self._field_widgets:
            self._field_widgets['album'].setText(album_name)
            
        # Stage the changes
        # Note: We are staging the Name for display/legacy, but ideally should stage ID.
        # But for now, let's stage the 'album' field as the NAMe (to match current schema behavior)
        # AND stage a hidden 'album_id' if the model supports it?
        # Re-reading constraints: spec says "App updates Song.AlbumID".
        
        # We will stage BOTH to be safe during transition
        # 'album' (str) -> For legacy string field
        self._on_field_changed("album", album_name)
        # 'album_id' (int) -> For new relation
        self._on_field_changed("album_id", album_id) 
        
        # Also Auto-Fill Publisher if possible? (Future optimization)

    def _validate_isrc_field(self, widget, text):
        """
        Validate ISRC field and update text color in real-time.
        Checks for both format validity and duplicates.
        """
        from ...utils.validation import validate_isrc
        
        # Empty is valid (ISRC is optional)
        if not text or not text.strip():
            widget.setProperty("invalid", False)
            widget.setToolTip("")
        
        # 1. Validate Format
        elif not validate_isrc(text):
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
                    widget.setProperty("invalid", False)
                    widget.setProperty("warning", False)
                    widget.setToolTip("")
            else:
                widget.setProperty("invalid", False)
                widget.setProperty("warning", False)
                widget.setToolTip("")

        widget.style().unpolish(widget)
        widget.style().polish(widget)
        self._update_save_state()
    
    def _calculate_bulk_value(self, field_def):
        """Determine what to show when 1 or many songs are selected."""
        attr = field_def.model_attr or field_def.name
        
        # Start with first song
        s0 = self.current_songs[0]
        v0 = self._get_effective_value(s0.source_id, field_def.name, getattr(s0, attr, ""))
        
        if len(self.current_songs) == 1:
            return v0, False
            
        # Bulk Mode: Compare values
        is_multiple = False
        for song in self.current_songs[1:]:
            v_other = self._get_effective_value(song.source_id, field_def.name, getattr(song, attr, ""))
            if v_other != v0:
                is_multiple = True
                break
        
        return v0 if not is_multiple else None, is_multiple

    def _get_effective_value(self, song_id, field_name, db_value):
        """Lookup staged value, fallback to DB."""
        if song_id in self._staged_changes and field_name in self._staged_changes[song_id]:
            return self._staged_changes[song_id][field_name]
        return db_value

    def _on_field_changed(self, field_name, value):
        """Stage the change for the current selection."""
        for song in self.current_songs:
            if song.source_id not in self._staged_changes:
                self._staged_changes[song.source_id] = {}
            self._staged_changes[song.source_id][field_name] = value
            
        self._update_header()
        self._update_save_state()
        self._validate_done_gate()
        self.staging_changed.emit(list(self._staged_changes.keys()))

    def _on_status_toggled(self, checked):
        val = 1 if checked else 0
        self._on_field_changed("is_done", val)
        self._update_status_visuals(checked)

    def _on_status_toggled(self, checked=False):
        """Toggle the ready/pending state."""
        # Fix: GlowButton signal might drop arg, check state directly
        is_ready = self.btn_status.isChecked()
        # Value 1 = Done, 0 = Pending
        val = 1 if is_ready else 0
        self._on_field_changed("is_done", val)
        self._update_status_visuals(is_ready)

    def _update_status_visuals(self, is_done):
        """Apply Pro Radio styling: Green for AIR, Gray for PENDING via QSS dynamic property."""
        if is_done:
            self.btn_status.setText("READY [AIR]")
            self.btn_status.setProperty("state", "ready")
        else:
            self.btn_status.setText("PENDING")
            self.btn_status.setProperty("state", "pending")
        
        # Force style refresh for dynamic property change
        self.btn_status.style().unpolish(self.btn_status)
        self.btn_status.style().polish(self.btn_status)

    def _validate_done_gate(self):
        """Disable MARK DONE if required fields are missing in selection."""
        if not self.current_songs:
            self.btn_status.setEnabled(False)
            return

        valid = True
        for song in self.current_songs:
            for field in yellberus.FIELDS:
                if field.required:
                    val = self._get_effective_value(song.source_id, field.name, getattr(song, field.model_attr or field.name, ""))
                    if val is None or str(val).strip() == "":
                        valid = False
                        break
            if valid:
            # Check Cross-Field Validation Groups (e.g. Unified Artist: Performer OR Group)
                for group in yellberus.VALIDATION_GROUPS:
                    if group.get("rule") == "at_least_one":
                        fields = group.get("fields", [])
                        has_any = False
                        for field_name in fields:
                            field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
                            if not field_def: continue
                            
                            attr = field_def.model_attr or field_def.name
                            val = self._get_effective_value(song.source_id, field_name, getattr(song, attr, ""))
                            
                            # Check for non-empty value (handle list and string)
                            if val:
                                if isinstance(val, list) and len(val) > 0: has_any = True
                                elif isinstance(val, str) and val.strip(): has_any = True
                                elif isinstance(val, (int, float, bool)): has_any = True
                            
                            if has_any: break
                        
                        if not has_any:
                            valid = False
                            break
            if not valid: break
            
        self.btn_status.setEnabled(valid)
        if not valid:
             self.btn_status.setToolTip("Required fields or validation rules are missing.")
             # Force visually disabled state if needed, but setEnabled handles most
        else:
             self.btn_status.setToolTip("Mark as Ready for Air")

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

    def _on_save_clicked(self, checked=False):
        """Emit the entire staged buffer for the MainWindow to commit."""
        # Allow saving even if no fields changed (e.g. to trigger rename)
        changes_to_emit = self._staged_changes.copy()
        
        if not changes_to_emit and self.current_songs:
            # Force inclusion of current songs if button was clicked but no edits made
            for song in self.current_songs:
                changes_to_emit[song.source_id] = {} # Empty dict implies "Save Current State"
        
        # Auto-fill Year logic (User Request)
        from datetime import datetime
        import re
        current_year = datetime.now().year
        
        for song_id in list(changes_to_emit.keys()):
            # Ensure sub-dict exists
            if song_id not in changes_to_emit:
                 changes_to_emit[song_id] = {}
                 
            changes = changes_to_emit[song_id]
            
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
                changes['recording_year'] = current_year

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
        
        self.save_requested.emit(changes_to_emit)
        
        # Optimistic UI update or wait for refresh?
        # Usually Main Window refreshes us.
        self._staged_changes.clear()
        self._update_save_state()

    def trigger_save(self):
        """Public slot to trigger save (e.g. from Ctrl+S shortcut)."""
        if self.btn_save.isEnabled():
            self._on_save_clicked()

    def _on_discard_clicked(self, checked=False):
        self._staged_changes = {}
        self.set_songs(self.current_songs)
        self.staging_changed.emit([]) # Clear highlights in library

    def clear_staged(self, song_ids=None):
        """Remove IDs from staging (post-save cleanup)."""
        if song_ids is None:
            self._staged_changes = {}
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
        from PyQt6.QtCore import QEvent
        if source == self.btn_status:
            if event.type() == QEvent.Type.Enter:
                # Reveal path on hover if it exists
                if self.lbl_projected_path.text():
                    self.lbl_projected_path.setVisible(True)
            elif event.type() == QEvent.Type.Leave:
                # Always hide on leave. The LED handles the persistent alert now.
                self.lbl_projected_path.setVisible(False)
        return super().eventFilter(source, event)

    def _get_staged_song(self, original_song):
        """Return a copy of the song with staged changes applied."""
        song = copy.copy(original_song)
        sid = original_song.source_id
        
        if sid in self._staged_changes:
            staged = self._staged_changes[sid]
            # Apply known attributes logic
            for field_name, value in staged.items():
                field_def = next((f for f in yellberus.FIELDS if f.name == field_name), None)
                if field_def:
                    attr = field_def.model_attr or field_def.name
                    # NEW: Cast string from UI to proper Python type (e.g. List, Int)
                    casted_value = yellberus.cast_from_string(field_def, value)
                    setattr(song, attr, casted_value)
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
            self.save_led.setProperty("state", "alert")
        else:
            # Clean display: normpath fixes the \ / mix
            display_path = os.path.normpath(target)
            self.lbl_projected_path.setText(display_path)
            
            # User Req: LED Red/Bold if path is different from DB (has_changed) or is a conflict
            is_alert = has_changed or has_conflict
            
            # The path is now strictly HOVER-ONLY to reclaim vertical space
            self.lbl_projected_path.setVisible(False)
            
            self.lbl_projected_path.setProperty("conflict", "true" if is_alert else "false")
            self.save_led.setProperty("state", "alert" if is_alert else "off")
            self.btn_save.setProperty("alert", is_alert)
            
        self.lbl_projected_path.style().unpolish(self.lbl_projected_path)
        self.lbl_projected_path.style().polish(self.lbl_projected_path)
        self.save_led.style().unpolish(self.save_led)
        self.save_led.style().polish(self.save_led)
        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)
