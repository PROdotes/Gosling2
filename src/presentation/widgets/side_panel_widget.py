from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QCheckBox, QComboBox, QPushButton, QScrollArea,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from ...core import yellberus

class SidePanelWidget(QWidget):
    """
    Metadata Editor (Stage) driven by Yellberus Field Registry.
    Implements a validation-gated 'Done' workflow and staging buffer.
    """
    
    # Signals
    # Emitted when the user clicks 'SAVE ALL'. MainWindow will handle the actual DB/ID3 write.
    save_requested = pyqtSignal(dict) # _staged_changes
    staging_changed = pyqtSignal(list) # list of song_ids in staging
    
    def __init__(self, library_service, metadata_service, parent=None):
        super().__init__(parent)
        self.library_service = library_service
        self.metadata_service = metadata_service
        
        self.current_songs = [] # List of Song objects
        self._staged_changes = {} # {song_id: {field_name: value}}
        self._widgets = {} # {field_name: QWidget}
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. Header Area
        self.header_label = QLabel("No Selection")
        self.header_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #E0E0E0;")
        self.header_label.setWordWrap(True)
        layout.addWidget(self.header_label)
        
        # 2. Workflow State (MARK DONE)
        self.btn_done = QPushButton("✅ MARK DONE")
        self.btn_done.setCheckable(True)
        self.btn_done.setStyleSheet("""
            QPushButton { 
                background-color: #333; 
                color: #888; 
                font-weight: bold; 
                padding: 12px; 
                border: 1px solid #444;
                border-radius: 4px;
            }
            QPushButton:checked { 
                background-color: #2E7D32; 
                color: white; 
                border: 1px solid #4CAF50;
            }
            QPushButton:hover:!checked { background-color: #444; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555; }
        """)
        self.btn_done.clicked.connect(self._on_done_toggled)
        self.btn_done.setEnabled(False) # Default to disabled (No selection)
        layout.addWidget(self.btn_done)
        
        # 3. Scroll Area for Fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.field_container = QWidget()
        self.field_layout = QVBoxLayout(self.field_container)
        self.field_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.field_container)
        layout.addWidget(scroll, 1)
        
        # 4. Footer Actions (Save / Discard)
        footer_frame = QFrame()
        footer_frame.setObjectName("Footer")
        footer_frame.setStyleSheet("QFrame#Footer { border-top: 1px solid #333; }")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        
        self.btn_discard = QPushButton("Discard")
        self.btn_discard.clicked.connect(self._on_discard_clicked)
        
        self.btn_save = QPushButton("SAVE ALL")
        self.btn_save.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                padding: 8px 16px; 
                background-color: #1976D2;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1E88E5; }
            QPushButton:disabled { background-color: #222; color: #666; }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_save.setEnabled(False)
        
        footer_layout.addWidget(self.btn_discard)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_save)
        layout.addWidget(footer_frame)
        
        self._clear_fields()

    def set_songs(self, songs):
        """Update the editor with fresh song selection."""
        # Note: We do NOT clear _staged_changes here. 
        # Persistence on selection loss is a key spec.
        self.current_songs = songs
        self._update_header()
        self._build_fields()
        self._validate_done_gate()
        self._update_save_state()

    def _update_header(self):
        if not self.current_songs:
            self.header_label.setText("No Selection")
            self.btn_done.setEnabled(False)
        elif len(self.current_songs) == 1:
            song = self.current_songs[0]
            artist = song.unified_artist or "Unknown Artist"
            self.header_label.setText(f"{artist} - {song.title}")
            self.btn_done.setEnabled(True)
            # Sync Done state from staging or song
            is_done = self._get_effective_value(song.source_id, "is_done", song.is_done)
            self.btn_done.setChecked(bool(is_done))
        else:
            self.header_label.setText(f"Editing {len(self.current_songs)} Items")
            self.btn_done.setEnabled(True) # In Bulk, MARK DONE applies to all

    def _build_fields(self):
        """Dynamic UI Factory driven by Yellberus with Grouping."""
        self._clear_fields()
        if not self.current_songs:
            return

        # Separate into Core (Required + Key Identity) and Advanced
        # We explicitly promote performers/groups to Core for better UX, even if technically optional
        core_fields = [f for f in yellberus.FIELDS if (f.required or f.name in ['performers', 'groups']) and f.visible and f.editable]
        adv_fields = [f for f in yellberus.FIELDS if not (f.required or f.name in ['performers', 'groups']) and f.visible and f.editable]

        def add_group(fields, title):
            if not fields: return
            
            group_label = QLabel(title.upper())
            group_label.setStyleSheet("color: #555; font-size: 8pt; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #222;")
            self.field_layout.addWidget(group_label)
            
            for field in fields:
                # Skip Title/Path in Bulk Mode (Spec Alpha)
                if len(self.current_songs) > 1 and field.name in ["Title", "Path"]:
                    continue
                
                # Skip 'is_done' (Status) because we have the big MARK DONE button
                if field.name == "is_done":
                    continue

                container = QWidget()
                row = QVBoxLayout(container)
                row.setContentsMargins(0, 0, 0, 8)
                
                # Label
                label_text = field.ui_header
                if field.required:
                    label_text += " *"
                label = QLabel(label_text)
                label.setStyleSheet("color: #999; font-size: 8.5pt; font-weight: bold;")
                
                # Determine Current Effective Value
                effective_val, is_multiple = self._calculate_bulk_value(field)
                
                # Create Widget
                edit_widget = self._create_field_widget(field, effective_val, is_multiple)
                self._widgets[field.name] = edit_widget
                
                row.addWidget(label)
                row.addWidget(edit_widget)
                self.field_layout.addWidget(container)

        add_group(core_fields, "Core Metadata")
        add_group(adv_fields, "Advanced Details")

    def _create_field_widget(self, field_def, value, is_multiple):
        # Determine strict type or strategy
        is_bool = (field_def.strategy and field_def.strategy.upper() == "BOOLEAN") or \
                  (field_def.field_type.name == "BOOLEAN")

        if is_bool:
            cb = QCheckBox()
            cb.setStyleSheet("QCheckBox { font-size: 10pt; spacing: 5px; }")
            # Handle string 'True'/'False' from some legacy paths just in case
            val_bool = str(value).lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
            
            cb.setChecked(val_bool if value is not None else False)
            if is_multiple: cb.setTristate(True); cb.setCheckState(Qt.CheckState.PartiallyChecked)
            cb.stateChanged.connect(lambda state: self._on_field_changed(field_def.name, bool(state)))
            return cb
            
        # Default: Line Edit for Alpha
        edit = QLineEdit()
        edit.setStyleSheet("QLineEdit { font-size: 10pt; padding: 3px; }")
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
        
        # Escape to revert
        edit.installEventFilter(self)
        return edit

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
            
        self._update_save_state()
        self._validate_done_gate()
        self.staging_changed.emit(list(self._staged_changes.keys()))

    def _on_done_toggled(self, checked):
        self._on_field_changed("is_done", 1 if checked else 0)

    def _validate_done_gate(self):
        """Disable MARK DONE if required fields are missing in selection."""
        if not self.current_songs:
            self.btn_done.setEnabled(False)
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
            
        self.btn_done.setEnabled(valid)
        self.btn_done.setToolTip("" if valid else "Required fields or validation rules are missing.")

    def _update_save_state(self):
        has_staged = len(self._staged_changes) > 0
        self.btn_save.setEnabled(has_staged)

    def _on_save_clicked(self):
        """Emit the entire staged buffer for the MainWindow to commit."""
        self.save_requested.emit(self._staged_changes)
        # Note: MainWindow will call self.clear_staged() after successful DB write.

    def trigger_save(self):
        """Public slot to trigger save (e.g. from Ctrl+S shortcut)."""
        if self.btn_save.isEnabled():
            self._on_save_clicked()

    def _on_discard_clicked(self):
        self._staged_changes = {}
        self.set_songs(self.current_songs)

    def clear_staged(self, song_ids=None):
        """Remove IDs from staging (post-save cleanup)."""
        if song_ids is None:
            self._staged_changes = {}
        else:
            for sid in song_ids:
                if sid in self._staged_changes:
                    del self._staged_changes[sid]
        self._update_save_state()

    def _clear_fields(self):
        self._widgets = {}
        while self.field_layout.count():
            item = self.field_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def eventFilter(self, source, event):
        # Escape key handling for revert coming in Phase 4
        return super().eventFilter(source, event)
