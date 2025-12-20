"""
Field Registry Editor - Tools for editing Yellberus field definitions.

A PyQt6 application for viewing, editing, and synchronizing field definitions
between yellberus.py and FIELD_REGISTRY.md.

See: design/proposals/FIELD_EDITOR_SPEC.md
"""

import sys
from pathlib import Path

# Add project root to path for imports when running as script
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QGroupBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from tools.yellberus_parser import parse_yellberus, FieldSpec, FIELD_DEFAULTS

# Field type options for dropdown
FIELD_TYPES = ["TEXT", "INTEGER", "REAL", "BOOLEAN", "LIST", "DURATION", "DATETIME"]

# Column definitions for the Defaults table
DEFAULTS_COLUMNS = ["visible", "editable", "filterable", "searchable", "required", "portable"]

# Column definitions for the Fields table
FIELDS_COLUMNS = [
    "Name", "UI Header", "DB Column", "Type", 
    "Vis", "Filt", "Search", "Req", "Port", "ID3 Tag"
]

# Tooltips for column headers (for Grandma)
COLUMN_TOOLTIPS = {
    0: "Name - Internal field identifier (Python variable name)",
    1: "UI Header - Display name shown in the application",
    2: "DB Column - Database table.column reference",
    3: "Type - Data type (TEXT, INTEGER, LIST, etc.)",
    4: "Visible - Show this field in the main table",
    5: "Filterable - Can filter by this field in the sidebar",
    6: "Searchable - Include in global search",
    7: "Required - Must be filled for 'Done' status",
    8: "Portable - Sync to ID3 tags in audio files",
    9: "ID3 Tag - The ID3 frame code (e.g., TIT2 for title)",
}


class FieldEditorWindow(QMainWindow):
    """Main window for the Field Registry Editor."""
    
    # Color coding for cell states (per spec)
    COLOR_MATCH = None
    COLOR_DIFFERS_CODE = "#3a2020"    # Soft Red - differs from yellberus.py (UNSAVED)
    COLOR_DIFFERS_MD = "#20203a"      # Soft Blue - differs from FIELD_REGISTRY.md (DOC DRIFT)
    COLOR_DIFFERS_BOTH = "#302030"    # Soft Purple - differs from both
    COLOR_NEW_FIELD = "#203a20"       # Soft Green - new field
    COLOR_DISABLED = "#1a1a1a"        # Dark/Black - N/A (e.g., ID3 Tag when not portable)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Field Registry Editor")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)
        
        # Storage for original values (for color comparison)
        self._code_fields: dict = {}  # name -> FieldSpec from yellberus.py
        self._md_fields: dict = {}    # name -> FieldSpec from FIELD_REGISTRY.md
        self._loaded_defaults: dict = {} # attribute -> bool (from FieldDef class)
        self._field_order: dict = {}  # name -> original index (for preserving BASE_QUERY order)
        self._dirty: bool = False  # Track unsaved changes
        self._test_mode: bool = False  # Skip dialogs in test mode

        self._setup_central_widget()  # Must come first (creates save_btn)
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Load ID3 frames for validation
        self._load_id3_defs()

        # Auto-load on startup (sets _dirty=False after load)
        self._on_load_clicked()

    def _load_id3_defs(self):
        import json
        try:
            path = Path(__file__).parent.parent / "src" / "resources" / "id3_frames.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._id3_frames = json.load(f)
            else:
                 self._id3_frames = {}
        except Exception as e:
            print(f"Warning: Could not load ID3 frames: {e}")
            self._id3_frames = {}

    def _lookup_id3_tag(self, field_name: str) -> str:
        """Look up ID3 frame code for a field name from id3_frames.json."""
        # JSON structure: {"TIT2": {"field": "title", ...}, ...}
        for frame_code, info in self._id3_frames.items():
            if isinstance(info, dict) and info.get("field") == field_name:
                return frame_code
        return ""

    def _setup_central_widget(self):
        """Create the main content area with tables."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Defaults row (horizontal checkboxes, not a table)
        defaults_group = QGroupBox("Defaults (applied to new fields)")
        defaults_row = QHBoxLayout(defaults_group)
        defaults_row.setContentsMargins(8, 4, 8, 4)
        defaults_row.setSpacing(16)
        
        self.default_checkboxes = {}
        for col_name in DEFAULTS_COLUMNS:
            cb = QCheckBox(col_name)
            cb.setChecked(FIELD_DEFAULTS.get(col_name, False))
            # Pass column name to handler for bulk updates
            cb.toggled.connect(lambda checked, name=col_name: self._on_defaults_changed(name, checked))
            self.default_checkboxes[col_name] = cb
            defaults_row.addWidget(cb)
        defaults_row.addStretch()
        layout.addWidget(defaults_group)

        # Fields table (main area)
        fields_group = QGroupBox("Fields")
        fields_layout = QVBoxLayout(fields_group)
        fields_layout.setContentsMargins(4, 4, 4, 4)
        self.fields_table = QTableWidget(0, len(FIELDS_COLUMNS))
        self.fields_table.setHorizontalHeaderLabels(FIELDS_COLUMNS)
        self.fields_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fields_table.setSortingEnabled(True)  # Enable Sorting
        self.fields_table.verticalHeader().setVisible(False)  # Hide row numbers
        self.fields_table.verticalHeader().setDefaultSectionSize(26)  # Compact rows
        self.fields_table.itemChanged.connect(self._on_item_changed)
        
        # Set column widths: text columns stretch, boolean columns fixed
        header = self.fields_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)   # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)   # UI Header
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)   # DB Column
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)     # Type
        self.fields_table.setColumnWidth(3, 100)  # Wide enough for "DURATION"
        for col in range(4, 9):  # Boolean columns
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.fields_table.setColumnWidth(col, 50)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)   # ID3 Tag
        
        # Add tooltips to abbreviated column headers (for Grandma)
        for col, tooltip in COLUMN_TOOLTIPS.items():
            self.fields_table.horizontalHeaderItem(col).setToolTip(tooltip)
        
        fields_layout.addWidget(self.fields_table)

        # Buttons below fields table
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 8, 0, 0)
        
        self.add_field_btn = QPushButton("+ Add Field")
        self.add_field_btn.clicked.connect(self._on_add_field)
        self.add_field_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                color: white;
                border: 1px solid #3d7a3d;
                padding: 6px 16px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3d7a3d;
            }
        """)
        
        self.delete_field_btn = QPushButton("Delete Selected")
        self.delete_field_btn.clicked.connect(self._on_delete_field)
        self.delete_field_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a2d2d;
                color: white;
                border: 1px solid #7a3d3d;
                padding: 6px 16px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #7a3d3d;
            }
        """)
        
        button_row.addWidget(self.add_field_btn)
        button_row.addStretch()
        button_row.addWidget(self.delete_field_btn)
        
        # Spacer
        spacer_label = QLabel("")
        spacer_label.setFixedWidth(16)
        button_row.addWidget(spacer_label)

        # Save button (Moved from toolbar)
        self.save_btn = QPushButton("Save All")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a2d;
                color: white;
                border: 1px solid #6a6a3d;
                padding: 6px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a6a3d;
            }
        """)
        button_row.addWidget(self.save_btn)
        
        fields_layout.addLayout(button_row)

        layout.addWidget(fields_group)

        # Legend Row
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(4, 0, 4, 0)
        legend_layout.setSpacing(12)
        
        def add_legend_item(color, text):
            # Color swatch
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            if color:
                swatch.setStyleSheet(f"background-color: {color}; border: 1px solid #555;")
            else:
                swatch.setStyleSheet("border: 1px dashed #555;")
            
            # Label
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #aaa; font-size: 11pt;")
            
            item_layout = QHBoxLayout()
            item_layout.setSpacing(6)
            item_layout.addWidget(swatch)
            item_layout.addWidget(lbl)
            legend_layout.addLayout(item_layout)

        add_legend_item(self.COLOR_DIFFERS_CODE, "Unsaved Code Change")
        add_legend_item(self.COLOR_DIFFERS_MD, "Doc Drift")
        add_legend_item(self.COLOR_DIFFERS_BOTH, "Both Changed")
        add_legend_item(self.COLOR_NEW_FIELD, "New Field")
        add_legend_item(self.COLOR_DISABLED, "N/A")
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

    def _setup_statusbar(self):
        """Create the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _setup_toolbar(self):
        """Create the main toolbar with action buttons."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 8px; padding: 4px; }")

        # Load button
        self.load_btn = QPushButton("Load from Code")
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d4a5a;
                color: white;
                border: 1px solid #3d6a7a;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3d6a7a;
            }
        """)
        toolbar.addWidget(self.load_btn)
        
        # For verification compatibility
        self.load_action = self.load_btn

        # For verification compatibility
        self.load_action = self.load_btn
        
        # Save button moved to bottom row (self.save_btn created in _setup_central_widget)
        # We can keep self.save_action pointing to it if needed for external tests, 
        # but the button isn't created here anymore.
        # Ideally, we should initialize self.save_btn in __init__ or handle order dependency.
        # _setup_central_widget is called BEFORE _setup_toolbar in __init__.
        # So self.save_btn exists now.
        if hasattr(self, 'save_btn'):
            self.save_action = self.save_btn

    def _on_load_clicked(self):
        """Load field definitions from yellberus.py and FIELD_REGISTRY.md."""
        from tools.yellberus_parser import parse_field_registry_md, extract_class_defaults
        
        yellberus_path = Path(__file__).parent.parent / "src" / "core" / "yellberus.py"
        md_path = Path(__file__).parent.parent / "design" / "FIELD_REGISTRY.md"
        
        if not yellberus_path.exists():
            self.status_bar.showMessage(f"Error: {yellberus_path} not found")
            return
            
        # 1. Parse Class Defaults (The Source of Truth)
        real_defaults = extract_class_defaults(yellberus_path)
        self._loaded_defaults = real_defaults
        
        # Update UI Checkboxes to match reality
        for col_name, cb in self.default_checkboxes.items():
            if col_name in real_defaults:
                val = real_defaults[col_name]
                cb.blockSignals(True)
                cb.setChecked(val)
                cb.blockSignals(False)
        
        # Parse both sources
        code_fields = parse_yellberus(yellberus_path)
        self._code_fields = {f.name: f for f in code_fields}
        
        # Store original order (critical for BASE_QUERY alignment)
        self._field_order = {f.name: idx for idx, f in enumerate(code_fields)}
        
        if md_path.exists():
            md_fields = parse_field_registry_md(md_path)
            self._md_fields = {f.name: f for f in md_fields}
        else:
            self._md_fields = {}
        
        # Populate table
        self._populate_fields_table(code_fields)
        
        # Apply initial color coding
        self._apply_all_colors()
        
        self._dirty = False  # Clean state after load
        self.status_bar.showMessage(
            f"Loaded {len(code_fields)} fields from code, {len(self._md_fields)} from MD"
        )

    def _populate_fields_table(self, fields: list):
        """Populate the Fields table with FieldSpec objects."""
        # CRITICAL: Disable sorting while populating to prevent rows from jumping 
        # mid-write (the "Data Gobling" bug).
        sorting_was_enabled = self.fields_table.isSortingEnabled()
        self.fields_table.setSortingEnabled(False)
        
        self.fields_table.setRowCount(len(fields))
        
        for row, field in enumerate(fields):
            # Name
            self.fields_table.setItem(row, 0, QTableWidgetItem(field.name))
            # UI Header
            self.fields_table.setItem(row, 1, QTableWidgetItem(field.ui_header))
            # DB Column
            self.fields_table.setItem(row, 2, QTableWidgetItem(field.db_column))
            # Type (dropdown)
            self._set_type_dropdown(row, 3, field.field_type)
            # Boolean columns: Vis, Filt, Search, Req, Port (columns 4-8)
            self._set_checkbox_cell(row, 4, field.visible)
            self._set_checkbox_cell(row, 5, field.filterable)
            self._set_checkbox_cell(row, 6, field.searchable)
            self._set_checkbox_cell(row, 7, field.required)
            self._set_checkbox_cell(row, 8, field.portable)
            # ID3 Tag - lookup from id3_frames.json
            id3_tag = self._lookup_id3_tag(field.name)
            self.fields_table.setItem(row, 9, QTableWidgetItem(id3_tag or ""))
            
        # Restore sorting state
        self.fields_table.setSortingEnabled(sorting_was_enabled)

    def _on_item_changed(self, item):
        """Handle item changes (text edits) to trigger color updates and auto-populate."""
        row = item.row()
        col = item.column()
        
        # 8.1-8.4: Auto-populate when Name column changes
        if col == 0:  # Name column
            name = item.text().strip()
            if name:
                self._auto_populate_from_name(row, name)
        
        self._dirty = True  # Mark as having unsaved changes
        self._apply_row_colors(row)
        self._update_status()

    def _auto_populate_from_name(self, row: int, name: str):
        """Auto-populate db_column and ui_header based on field name."""
        # 8.3: Auto-suggest ui_header as Title Case
        ui_header = name.replace("_", " ").title()
        ui_item = self.fields_table.item(row, 1)
        if ui_item and not ui_item.text():  # Only if empty
            self.fields_table.blockSignals(True)
            ui_item.setText(ui_header)
            self.fields_table.blockSignals(False)
        
        # 8.1: Auto-lookup db_column from existing fields or schema
        db_column = self._lookup_db_column(name)
        if db_column:
            db_item = self.fields_table.item(row, 2)
            if db_item and not db_item.text():  # Only if empty
                self.fields_table.blockSignals(True)
                db_item.setText(db_column)
                self.fields_table.blockSignals(False)
                
        # 8.2: Auto-lookup ID3 Tag
        id3_tag = self._lookup_id3_tag(name)
        if id3_tag:
            tag_item = self.fields_table.item(row, 9)
            if tag_item and not tag_item.text(): # Only if empty
                self.fields_table.blockSignals(True)
                tag_item.setText(id3_tag)
                self.fields_table.blockSignals(False)

    def _lookup_db_column(self, field_name: str) -> str:
        """Look up db_column for a field name from existing fields or common patterns."""
        # First, check if we have this field in our loaded cache
        if field_name in self._code_fields:
            return self._code_fields[field_name].db_column
        
        # Common patterns based on table prefixes
        # MS = MediaSources, S = Songs
        common_mappings = {
            # MediaSources table
            "file_id": "MS.SourceID",
            "source_id": "MS.SourceID",
            "type_id": "MS.TypeID",
            "title": "MS.Name",
            "name": "MS.Name",
            "path": "MS.Source",
            "source": "MS.Source",
            "duration": "MS.Duration",
            "notes": "MS.Notes",
            "is_active": "MS.IsActive",
            # Songs table
            "recording_year": "S.RecordingYear",
            "year": "S.RecordingYear",
            "bpm": "S.TempoBPM",
            "tempo": "S.TempoBPM",
            "is_done": "S.IsDone",
            "done": "S.IsDone",
            "isrc": "S.ISRC",
            "groups": "S.Groups",
            "album": "S.Album",
            "genre": "S.Genre",
            "publisher": "S.Publisher",
        }
        
        if field_name.lower() in common_mappings:
            return common_mappings[field_name.lower()]
        
        # Fallback: try to guess based on naming convention
        # Assume Songs table for unknown fields
        pascal_name = "".join(word.title() for word in field_name.split("_"))
        return f"S.{pascal_name}"

    def _on_defaults_changed(self, col_name: str, checked: bool):
        """Handle changes to default checkboxes (triggers re-coloring, NOT bulk edit)."""
        self._apply_all_colors()

    def _set_checkbox_cell(self, row: int, col: int, checked: bool):
        """Create a centered checkbox widget in a table cell."""
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        
        # Special handling for portable column (col 8)
        # Special handling for portable column (col 8)
        if col == 8:
            checkbox.toggled.connect(lambda chk: self._handle_checkbox_toggle(checkbox, is_portable=True))
        else:
            checkbox.toggled.connect(lambda chk: self._handle_checkbox_toggle(checkbox))
        
        # Center the checkbox in the cell
        widget = QWidget()
        widget.setObjectName("cell_wrapper")  # Name requires for precise styling
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setAutoFillBackground(True) # Force paint
        
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add a hidden item for sorting purposes (0 or 1)
        sort_item = QTableWidgetItem()
        sort_item.setData(Qt.ItemDataRole.DisplayRole, "") # Visible text empty
        sort_item.setData(Qt.ItemDataRole.UserRole, int(checked)) # Sort value
        # We cheat and put the sort value in display text too, but made invisible? 
        # Actually easier: just set the text to "0" or "1" and set foreground color to transparent.
        sort_item.setText("1" if checked else "0")
        sort_item.setForeground(QColor(0,0,0,0)) # Transparent text
        
        self.fields_table.setItem(row, col, sort_item)
        self.fields_table.setCellWidget(row, col, widget)

    def _handle_checkbox_toggle(self, checkbox, is_portable=False):
        """Helper to find row dynamically (sorting safe) and trigger logic."""
        # Checkbox is inside QWidget (wrapper) inside Cell
        # We need the position of the wrapper relative to the table viewport
        wrapper = checkbox.parentWidget()
        if not wrapper: return
        
        # indexAt uses coordinates relative to the viewport
        pos = wrapper.pos() 
        # CAUTION: wrapper.pos() might be 0,0 if layout weirdness? 
        # Better: mapToParent? wrapper is child of table's scroll area...
        # Actually, indexAt(wrapper.pos()) usually works for cell widgets.
        
        index = self.fields_table.indexAt(pos)
        if index.isValid():
            row = index.row()
            if is_portable:
                self._on_portable_toggled(row, checkbox.isChecked())
            else:
                self._on_checkbox_toggled(row)

    def _on_checkbox_toggled(self, row: int):
        """Handle generic checkbox toggle - mark dirty and recolor."""
        # Update the underlying sort item so sorting respects the new value
        # We need to find which column triggered this. 
        # Since we bound the lambda only with 'row', we have to infer or check all checkbox cols?
        # Better: iterate checkable columns for this row and update their sort items.
        for col in range(4, 9): # Boolean columns
            widget = self.fields_table.cellWidget(row, col)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    item = self.fields_table.item(row, col)
                    if item:
                         item.setText("1" if cb.isChecked() else "0")

        self._dirty = True # Will be re-evaluated by _update_status
        self._apply_row_colors(row)
        self._update_status()

    def _on_portable_toggled(self, row: int, checked: bool):
        """Handle portable checkbox toggle - auto-lookup ID3 tag."""
        if checked:
            # Get field name from row
            name_item = self.fields_table.item(row, 0)
            if name_item:
                field_name = name_item.text()
                id3_tag = self._lookup_id3_tag(field_name)
                # Update ID3 Tag cell (column 9)
                id3_item = self.fields_table.item(row, 9)
                if id3_item:
                    id3_item.setText(id3_tag)
                else:
                    self.fields_table.setItem(row, 9, QTableWidgetItem(id3_tag))
        
        self._dirty = True
        self._apply_row_colors(row)
        self._update_status()

    def _on_dropdown_changed(self, row: int):
        """Handle dropdown change - mark dirty and recolor."""
        self._dirty = True
        self._apply_row_colors(row)
        self._update_status()

    def _set_type_dropdown(self, row: int, col: int, current_type: str):
        """Create a dropdown (combo box) for the Type column."""
        combo = QComboBox()
        combo.setObjectName("type_combo") # Name for styling
        combo.addItems(FIELD_TYPES)
        # Set current value
        index = combo.findText(current_type)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            # Unknown type - add it to the list
            combo.addItem(current_type)
            combo.setCurrentText(current_type)
            
        combo.currentIndexChanged.connect(lambda idx: self._on_dropdown_changed(row))
        
        self.fields_table.setCellWidget(row, col, combo)

    def _set_cell_bg(self, row: int, col: int, color_hex: str):
        """Set background for a specific cell/widget."""
        from PyQt6.QtGui import QColor, QPalette
        
        qcolor = QColor(color_hex) if color_hex else QColor(0,0,0,0)
        
        # Standard Item
        item = self.fields_table.item(row, col)
        if item:
            # Prevent infinite recursion since setting background triggers itemChanged
            self.fields_table.blockSignals(True)
            item.setBackground(qcolor)
            self.fields_table.blockSignals(False)
        
        # Widget (ComboBox or CheckBox wrapper)
        widget = self.fields_table.cellWidget(row, col)
        if widget:
            # Check object name
            obj_name = widget.objectName()
            
            if color_hex:
                 if obj_name == "cell_wrapper":
                     # Apply to wrapper AND ensure checkbox is transparent so we see it
                     # SOLID RED BORDER + FILL
                     style = f"#cell_wrapper {{ background-color: {color_hex}; border: 2px solid {color_hex}; }} QCheckBox {{ background-color: transparent; }}"
                     widget.setStyleSheet(style)
                 else:
                     # Fallback for combo or others
                     widget.setStyleSheet(f"background-color: {color_hex};")
            else:
                 widget.setStyleSheet("background-color: transparent;")
            
            widget.update()
            # if color_hex: print(f"DEBUG: Painted {row},{col} {color_hex}")

    def _on_add_field(self):
        """Add a new field row with default values."""
        # Disable sorting to keep the new row at the bottom while we populate it
        sorting_was_enabled = self.fields_table.isSortingEnabled()
        self.fields_table.setSortingEnabled(False)
        
        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        
        # Populate with defaults from top UI
        self.fields_table.setItem(row, 0, QTableWidgetItem(""))  # Name (empty, needs input)
        self.fields_table.setItem(row, 1, QTableWidgetItem(""))  # UI Header
        self.fields_table.setItem(row, 2, QTableWidgetItem(""))  # DB Column
        self._set_type_dropdown(row, 3, FIELD_DEFAULTS.get("field_type", "TEXT"))
        
        # Read bool defaults from UI checkboxes
        def get_default(name):
            return self.default_checkboxes[name].isChecked() if name in self.default_checkboxes else False

        self._set_checkbox_cell(row, 4, get_default("visible"))
        self._set_checkbox_cell(row, 5, get_default("filterable"))
        self._set_checkbox_cell(row, 6, get_default("searchable"))
        self._set_checkbox_cell(row, 7, get_default("required"))
        self._set_checkbox_cell(row, 8, get_default("portable"))
        self.fields_table.setItem(row, 9, QTableWidgetItem(""))  # ID3 Tag
        
        # Restore sorting and focus
        self.fields_table.setSortingEnabled(sorting_was_enabled)
        
        # If we just re-enabled sorting, the empty name might have jumped to the top.
        # We need to find the row with empty name to focus it.
        # Iterate to find the empty row
        target_row = row
        for r in range(self.fields_table.rowCount()):
             item = self.fields_table.item(r, 0)
             if item and not item.text():
                 target_row = r
                 break
        
        self.fields_table.setCurrentCell(target_row, 0)
        self.fields_table.editItem(self.fields_table.item(target_row, 0))
        
        self._update_status()
    
    def _on_delete_field(self):
        """Delete selected field rows with confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        
        selected_rows = set(item.row() for item in self.fields_table.selectedItems())
        if not selected_rows:
            return
        
        # Get names of selected fields
        names = []
        for row in selected_rows:
            item = self.fields_table.item(row, 0)
            if item:
                names.append(item.text() or f"(row {row})")
        
        # Confirm deletion
        msg = QMessageBox()
        msg.setWindowTitle("Delete Fields?")
        msg.setText(f"Delete {len(selected_rows)} field(s)?")
        msg.setInformativeText("Fields to delete:\n" + "\n".join(f"  - {n}" for n in names))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Delete in reverse order to preserve row indices
            for row in sorted(selected_rows, reverse=True):
                self.fields_table.removeRow(row)
            self._update_status()
    
    def _update_status(self):
        """Update the status bar with field count and change counts."""
        count = self.fields_table.rowCount()
        
        # Count changes
        code_diffs = 0
        md_diffs = 0
        conflicts = 0
        new_fields = 0
        
        col_map = {
            0: 'name', 1: 'ui_header', 2: 'db_column', 3: 'field_type',
            4: 'visible', 5: 'filterable', 6: 'searchable', 7: 'required', 8: 'portable',
            9: 'id3_tag'
        }
        
        for row in range(count):
            spec = self._get_field_spec_from_row(row)
            name = spec.name
            
            if not name:
                continue
                
            code_orig = self._code_fields.get(name)
            md_orig = self._md_fields.get(name)
            
            # 1. Existence check
            if not code_orig and not md_orig:
                new_fields += 1
                continue
                
            # 2. Value check
            row_code_diff = False
            row_md_diff = False
            
            if not code_orig:
                row_code_diff = True
            else:
                for col, attr in col_map.items():
                    # yellberus.py doesn't store id3_tag, so ignore it for code diffs
                    if attr == 'id3_tag':
                        continue
                        
                    val = getattr(spec, attr)
                    orig = getattr(code_orig, attr)
                    if isinstance(val, str):
                        if (val or "") != (orig or ""):
                            row_code_diff = True; break
                    elif val != orig:
                        row_code_diff = True; break
            
            if not md_orig:
                row_md_diff = True
            else:
                for col, attr in col_map.items():
                    val = getattr(spec, attr)
                    orig = getattr(md_orig, attr)
                    if isinstance(val, str):
                        if (val or "") != (orig or ""):
                            row_md_diff = True; break
                    elif val != orig:
                        row_md_diff = True; break
            
            if row_code_diff and row_md_diff:
                conflicts += 1
            elif row_code_diff:
                code_diffs += 1
            elif row_md_diff:
                md_diffs += 1
        
        msg = f"{count} fields"
        parts = []
        if code_diffs: parts.append(f"{code_diffs} changed from code")
        if md_diffs: parts.append(f"{md_diffs} differ from MD")
        if conflicts: parts.append(f"{conflicts} differ from both")
        if new_fields: parts.append(f"{new_fields} new")
        
        if parts:
            msg += f" ({', '.join(parts)})"
        
        self.status_bar.showMessage(msg)
        
        # Smart Dirty Check: If any diffs exist, we are dirty.
        # If user toggled On -> Off (back to orig), diffs will be 0, so NOT dirty.
        # EXCEPTION: We ignore 'md_diffs' (Doc Drift). If the code matches but MD differs, 
        # that's a pre-existing condition, not a user change to save.
        self._dirty = (code_diffs + conflicts + new_fields) > 0

    def _get_field_spec_from_row(self, row: int) -> FieldSpec:
        """Construct a FieldSpec object from the current UI state of a row."""
        from tools.yellberus_parser import FieldSpec
        
        # safely get text
        def txt(col):
            item = self.fields_table.item(row, col)
            return item.text().strip() if item else ""
        
        # safely get combobox
        def combo(col):
            widget = self.fields_table.cellWidget(row, col)
            return widget.currentText() if isinstance(widget, QComboBox) else "TEXT"
            
        # safely get checkbox
        def check(col):
            widget = self.fields_table.cellWidget(row, col)
            if widget:
                # The widget is a wrapper QWidget with a QHBoxLayout containing the QCheckBox
                cb = widget.findChild(QCheckBox)
                return cb.isChecked() if cb else False
            return False

        return FieldSpec(
            name=txt(0),
            ui_header=txt(1),
            db_column=txt(2),
            field_type=combo(3),
            visible=check(4),
            filterable=check(5),
            searchable=check(6),
            required=check(7),
            portable=check(8),
            id3_tag=txt(9) or None
        )

    def _apply_row_colors(self, row: int):
        """Re-evaluate and apply colors for a specific row based on values."""
        from PyQt6.QtGui import QColor
        
        current_spec = self._get_field_spec_from_row(row)
        name = current_spec.name
        
        # Look up originals (empty name won't be found, which is correct -> New Field)
        code_orig = self._code_fields.get(name)
        md_orig = self._md_fields.get(name)
        
        # Map cols back to attribute names for source checking
        col_map = {
            0: 'name', 1: 'ui_header', 2: 'db_column', 3: 'field_type',
            4: 'visible', 5: 'filterable', 6: 'searchable', 7: 'required', 8: 'portable',
            9: 'id3_tag'
        }
        for col in range(self.fields_table.columnCount()):
            attr = col_map.get(col)
            if not attr: 
                continue # specific buttons or spacers? (Columns are fixed 0-9)
            
            final_color = None
            
            current_val = getattr(current_spec, attr)

            # Compare to original sources
            cell_code_diff = False
            cell_md_diff = False
            
            if code_orig:
                # yellberus.py doesn't store id3_tag
                if attr != 'id3_tag':
                    orig_val = getattr(code_orig, attr)
                    if isinstance(current_val, str):
                       if (current_val or "") != (orig_val or ""): cell_code_diff = True
                    elif current_val != orig_val: 
                        cell_code_diff = True
                        
                    # For default-columns: check if representation will change
                    # (implicit <-> explicit flip due to default change)
                    if attr in self.default_checkboxes and attr in self._loaded_defaults:
                        orig_default = self._loaded_defaults.get(attr)
                        ui_default = self.default_checkboxes[attr].isChecked()
                        if orig_default != ui_default:
                            # Default changed. Representation flips if:
                            # - Was implicit (matched orig_default) -> will be explicit (differs from new)
                            # - Was explicit (differed from orig) -> will be implicit (matches new)
                            was_implicit = (current_val == orig_default)
                            will_be_implicit = (current_val == ui_default)
                            if was_implicit != will_be_implicit:
                                cell_code_diff = True
            elif not code_orig:
                cell_code_diff = True # Entirely missing from code
                
            if md_orig:
                orig_val = getattr(md_orig, attr)
                if isinstance(current_val, str):
                   if (current_val or "") != (orig_val or ""): cell_md_diff = True
                elif current_val != orig_val: cell_md_diff = True
            elif not md_orig:
                cell_md_diff = True

            # C. Determine Priority
            # Special case: ID3 Tag column (9) when portable=False -> disabled/black
            if col == 9:
                portable_val = current_spec.portable
                if not portable_val:
                    final_color = self.COLOR_DISABLED
                elif not code_orig and not md_orig:
                    final_color = self.COLOR_NEW_FIELD
                elif cell_code_diff and cell_md_diff:
                    final_color = self.COLOR_DIFFERS_BOTH
                elif cell_code_diff:
                    final_color = self.COLOR_DIFFERS_CODE
                elif cell_md_diff:
                    final_color = self.COLOR_DIFFERS_MD
            elif not code_orig and not md_orig:
                # New field -> Always Green
                final_color = self.COLOR_NEW_FIELD
            elif cell_code_diff and cell_md_diff:
                final_color = self.COLOR_DIFFERS_BOTH
            elif cell_code_diff:
                final_color = self.COLOR_DIFFERS_CODE
            elif cell_md_diff:
                final_color = self.COLOR_DIFFERS_MD
            
            # Apply ONE final decision
            self._set_cell_bg(row, col, final_color)

    def _set_row_bg(self, row: int, color_hex: str):
        """Set background for entire row."""
        for col in range(self.fields_table.columnCount()):
            self._set_cell_bg(row, col, color_hex)


    def _apply_all_colors(self):
        """Re-scan all rows and apply colors."""
        for row in range(self.fields_table.rowCount()):
            self._apply_row_colors(row)
        self._update_status()

    def _on_save_clicked(self):
        """Save changes to yellberus.py and FIELD_REGISTRY.md."""
        from tools.yellberus_parser import write_yellberus, write_field_registry_md
        from PyQt6.QtWidgets import QMessageBox
        
        # 1. Gather all fields from UI
        fields_by_name = {}
        for row in range(self.fields_table.rowCount()):
            # Get UI representation
            ui_spec = self._get_field_spec_from_row(row)
            if not ui_spec.name:
                continue
                
            # Merge with original if exists (to preserve hidden attributes like min_value)
            original = self._code_fields.get(ui_spec.name) or self._md_fields.get(ui_spec.name)
            
            if original:
                from dataclasses import replace
                merged = replace(original,
                    name=ui_spec.name,
                    ui_header=ui_spec.ui_header,
                    db_column=ui_spec.db_column,
                    field_type=ui_spec.field_type,
                    visible=ui_spec.visible,
                    filterable=ui_spec.filterable,
                    searchable=ui_spec.searchable,
                    required=ui_spec.required,
                    portable=ui_spec.portable,
                    id3_tag=ui_spec.id3_tag
                )
                fields_by_name[ui_spec.name] = merged
            else:
                # New field - assign next available order index
                if ui_spec.name not in self._field_order:
                    self._field_order[ui_spec.name] = max(self._field_order.values(), default=-1) + 1
                fields_by_name[ui_spec.name] = ui_spec
        
        # 2. Sort fields by original order to maintain BASE_QUERY alignment
        fields_to_save = sorted(
            fields_by_name.values(),
            key=lambda f: self._field_order.get(f.name, 9999)
        )
        
        # Validate ID3 tags
        unknown_tags = []
        missing_tags = []
        for f in fields_to_save:
            if f.portable:
                if not f.id3_tag:
                    # Portable but no ID3 tag mapping
                    missing_tags.append(f.name)
                elif f.id3_tag not in self._id3_frames:
                    # Tag specified but not in JSON
                    unknown_tags.append(f"{f.name} ('{f.id3_tag}')")
        
        if missing_tags or unknown_tags:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("ID3 Tag Issues")
            
            issues = []
            if missing_tags:
                issues.append("Missing ID3 mapping (portable but no tag):\n" + "\n".join(f"  - {t}" for t in missing_tags))
            if unknown_tags:
                issues.append("Unknown ID3 tags (not in id3_frames.json):\n" + "\n".join(f"  - {t}" for t in unknown_tags))
            
            msg.setText("ID3 tag issues found:")
            msg.setInformativeText("\n\n".join(issues) + "\n\nSave anyway?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if msg.exec() == QMessageBox.StandardButton.Cancel:
                return

        # 2. Write to files
        yellberus_path = Path(__file__).parent.parent / "src" / "core" / "yellberus.py"
        md_path = Path(__file__).parent.parent / "design" / "FIELD_REGISTRY.md"
        
        # Gather current UI defaults to update class definition
        current_defaults = {}
        for col_name, cb in self.default_checkboxes.items():
            current_defaults[col_name] = cb.isChecked()
        
        success_code = write_yellberus(yellberus_path, fields_to_save, defaults=current_defaults)
        success_md = write_field_registry_md(md_path, fields_to_save)
        
        if success_code and success_md:
            self.status_bar.showMessage("Saved successfully to both files!")
            self._dirty = False  # Reset dirty flag
            # Reload to refresh colors and original caches
            self._on_load_clicked()
        elif success_code:
            self.status_bar.showMessage("Saved to Code but MD failed!")
            QMessageBox.warning(self, "Save Warning", "Saved to yellberus.py but failed to write FIELD_REGISTRY.md")
        elif success_md:
            self.status_bar.showMessage("Saved to MD but Code failed!")
            QMessageBox.warning(self, "Save Warning", "Saved to FIELD_REGISTRY.md but failed to write yellberus.py")
        else:
            self.status_bar.showMessage("Save Failed!")
            QMessageBox.critical(self, "Save Error", "Failed to write to both files.")

    def closeEvent(self, event):
        """8.7: Warn about unsaved changes on close."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Skip dialog in test mode
        if self._test_mode:
            event.accept()
            return
        
        if self._dirty:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Unsaved Changes")
            msg.setText("You have unsaved changes.")
            msg.setInformativeText("Do you want to save before closing?")
            msg.setStandardButtons(
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Save)
            
            result = msg.exec()
            
            if result == QMessageBox.StandardButton.Save:
                self._on_save_clicked()
                event.accept()
            elif result == QMessageBox.StandardButton.Discard:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()


def main():
    """Entry point for the Field Registry Editor."""
    app = QApplication(sys.argv)
    window = FieldEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
