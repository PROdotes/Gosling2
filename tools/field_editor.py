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
    QGroupBox, QCheckBox, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from tools.yellberus_parser import parse_yellberus, FieldSpec, FIELD_DEFAULTS

# Field type options for dropdown
FIELD_TYPES = ["TEXT", "INTEGER", "REAL", "BOOLEAN", "LIST", "DURATION", "DATETIME"]

# Strategy options (Filter or Grouping)
STRATEGY_OPTIONS = ["", "Range Filter", "Boolean Toggle", "Decade Grouping", "First Letter"]

# Column definitions for the Defaults table
DEFAULTS_COLUMNS = ["visible", "editable", "filterable", "searchable", "required", "portable"]

# Column definitions for the Fields table
FIELDS_COLUMNS = [
    "Name", "UI Header", "DB Column", "Type", "Strategy",
    "Vis", "Edit", "Filt", "Search", "Req", "Port", "ID3 Tag", "Validation"
]

# Tooltips for column headers (for Grandma)
COLUMN_TOOLTIPS = {
    0: "Name - Internal field identifier (Python variable name)",
    1: "UI Header - Display name shown in the application",
    2: "DB Column - Database table.column reference",
    3: "Type - Data type (TEXT, INTEGER, LIST, etc.)",
    4: "Strategy - Filter or Grouping logic (Range, Decade, First Letter)",
    5: "Visible - Show this field in the main table",
    6: "Editable - Allow user to edit this field",
    7: "Filterable - Can filter by this field in the sidebar",
    8: "Searchable - Include in global search",
    9: "Required - Must be filled for 'Done' status",
    10: "Portable - Sync to ID3 tags in audio files",
    11: "ID3 Tag - The ID3 frame code (e.g., TIT2 for title)",
    12: "Validation - Cross-field validation rules (e.g. One-or-Other)",
}

class FieldEditorWindow(QMainWindow):
    """Main window for the Field Registry Editor."""

    # Color coding for cell states (per spec)
    COLOR_DIFFERS_CODE = "#3a2020"    # Soft Red - differs from yellberus.py (UNSAVED)
    COLOR_DIFFERS_MD = "#20203a"      # Soft Blue - differs from FIELD_REGISTRY.md (DOC DRIFT)
    COLOR_DIFFERS_BOTH = "#3a2040"    # Soft Purple - differs from both (more magenta-ish)
    COLOR_NEW_FIELD = "#203a20"       # Soft Green - new field
    COLOR_DISABLED = "#1a1a1a"        # Dark/Black - N/A (e.g., ID3 Tag when not portable)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Field Registry Editor")
        self.setMinimumSize(1000, 600)
        self.resize(1400, 800)

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
            self.status_bar.showMessage(f"Warning: Could not load ID3 frames: {e}")
            self._id3_frames = {}

    def _lookup_id3_tag(self, field_name: str) -> str:
        """Look up ID3 frame code for a field name from id3_frames.json."""
        for frame_code, info in self._id3_frames.items():
            if isinstance(info, dict) and info.get("field") == field_name:
                return frame_code
        return ""

    def _styled_button(self, text: str, bg: str, hover: str, bold: bool = False) -> QPushButton:
        """Create a styled button with consistent appearance."""
        btn = QPushButton(text)
        weight = "font-weight: bold;" if bold else ""
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: 1px solid {hover};
                padding: 6px 16px;
                border-radius: 3px;
                {weight}
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)
        return btn

    def _mark_row_dirty(self, row: int):
        """Mark a row as dirty, recolor it, and update status."""
        self._dirty = True
        self._apply_row_colors(row)
        self._update_status()

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
        self.fields_table.setSortingEnabled(True)
        self.fields_table.verticalHeader().setVisible(False)
        self.fields_table.verticalHeader().setDefaultSectionSize(26)
        self.fields_table.itemChanged.connect(self._on_item_changed)

        # Set column widths: text columns stretch, boolean columns fixed
        header = self.fields_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)   # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)   # UI Header
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)   # DB Column
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)     # Type
        self.fields_table.setColumnWidth(3, 100)  # Wide enough for "DURATION"
        # Strategy (4)
        self.fields_table.setColumnWidth(4, 100)

        # Boolean columns: Vis(5), Edit(6), Filt(7), Search(8), Req(9), Port(10)
        for col in range(5, 11):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.fields_table.setColumnWidth(col, 50)
        
        # ID3 Tag (11) - Give it space, make it resizeable
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.Interactive)
        self.fields_table.setColumnWidth(11, 150)
        
        # Validation (12) - Stretch remaining space
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.Stretch)

        # Add tooltips to abbreviated column headers (for Grandma)
        for col, tooltip in COLUMN_TOOLTIPS.items():
            self.fields_table.horizontalHeaderItem(col).setToolTip(tooltip)

        fields_layout.addWidget(self.fields_table)

        # Buttons below fields table
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 8, 0, 0)

        self.add_field_btn = self._styled_button("+ Add Field", "#2d5a2d", "#3d7a3d")
        self.add_field_btn.clicked.connect(self._on_add_field)

        self.delete_field_btn = self._styled_button("Delete Selected", "#5a2d2d", "#7a3d3d")
        self.delete_field_btn.clicked.connect(self._on_delete_field)

        button_row.addWidget(self.add_field_btn)
        button_row.addStretch()
        button_row.addWidget(self.delete_field_btn)
        button_row.addSpacing(16)

        self.save_btn = self._styled_button("Save All", "#4a4a2d", "#6a6a3d", bold=True)
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_row.addWidget(self.save_btn)

        fields_layout.addLayout(button_row)

        layout.addWidget(fields_group)

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
        self.load_btn = self._styled_button("Load from Code", "#2d4a5a", "#3d6a7a")
        self.load_btn.clicked.connect(self._on_load_clicked)
        toolbar.addWidget(self.load_btn)

        # For verification compatibility
        self.load_action = self.load_btn
        self.save_action = self.save_btn

    def _on_load_clicked(self):
        """Load field definitions from yellberus.py and FIELD_REGISTRY.md."""
        from tools.yellberus_parser import parse_field_registry_md, extract_class_defaults
        from PyQt6.QtWidgets import QMessageBox

        # Warn about unsaved changes (skip in test mode or on initial load)
        if self._dirty and not self._test_mode:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Unsaved Changes")
            msg.setText("You have unsaved changes that will be lost.")
            msg.setInformativeText("Reload from code anyway?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if msg.exec() != QMessageBox.StandardButton.Yes:
                return

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

        # T-19: Load Validation Groups
        self._validation_map = self._parse_validation_info(yellberus_path)

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
        sorting_was_enabled = self.fields_table.isSortingEnabled()
        self.fields_table.setSortingEnabled(False)

        self.fields_table.setRowCount(len(fields))
        
        # T-19: Get validation info map if available
        validation_map = getattr(self, "_validation_map", {})

        for row, field in enumerate(fields):
            # Name (with Query Tooltip if has custom SQL)
            name_item = QTableWidgetItem(field.name)
            if hasattr(field, 'extra_attributes') and 'query_expression' in field.extra_attributes:
                sql = field.extra_attributes['query_expression']
                name_item.setToolTip(f"Custom SQL:\n{sql}")
                # Bold + italic to indicate custom query
                font = name_item.font()
                font.setBold(True)
                font.setItalic(True)
                name_item.setFont(font)
            self.fields_table.setItem(row, 0, name_item)
            
            # UI Header & DB Column
            self.fields_table.setItem(row, 1, QTableWidgetItem(field.ui_header))
            self.fields_table.setItem(row, 2, QTableWidgetItem(field.db_column))
            
            # Type (dropdown)
            self._set_type_dropdown(row, 3, field.field_type)
            
            # Strategy (4) - Now a single field
            strategy = getattr(field, 'strategy', 'list')
            strategy_display = {
                "range": "Range Filter",
                "boolean": "Boolean Toggle", 
                "decade_grouper": "Decade Grouping",
                "first_letter_grouper": "First Letter",
            }.get(strategy, "")
            
            self._set_editable_combo(row, 4, strategy_display, STRATEGY_OPTIONS)
            
            # Boolean columns: Vis, Edit, Filt, Search, Req, Port (columns 5-10)
            self._set_checkbox_cell(row, 5, field.visible)
            self._set_checkbox_cell(row, 6, field.editable)
            self._set_checkbox_cell(row, 7, field.filterable)
            self._set_checkbox_cell(row, 8, field.searchable)
            self._set_checkbox_cell(row, 9, field.required)
            self._set_checkbox_cell(row, 10, field.portable)
            
            # ID3 Tag (11) - Read Only (derived from id3_frames.json)
            id3_tag = self._lookup_id3_tag(field.name)
            id3_item = QTableWidgetItem(id3_tag or "")
            id3_item.setFlags(id3_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read only
            id3_item.setToolTip("Derived from id3_frames.json. Edit JSON to change mapping.")
            self.fields_table.setItem(row, 11, id3_item)
            
            # Validation (12) - Read Only
            val_info = validation_map.get(field.name, "")
            val_item = QTableWidgetItem(val_info)
            val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read only
            if val_info:
                val_item.setToolTip("From VALIDATION_GROUPS")
            self.fields_table.setItem(row, 12, val_item)

        # Restore sorting state
        self.fields_table.setSortingEnabled(sorting_was_enabled)

    def _on_item_changed(self, item):
        """Handle item changes (text edits) to trigger color updates and auto-populate."""
        row = item.row()
        col = item.column()

        if col == 0:
            name = item.text().strip()
            if name:
                self._auto_populate_from_name(row, name)

        self._dirty = True  # Mark as having unsaved changes
        self._apply_row_colors(row)
        self._update_status()

    def _auto_populate_from_name(self, row: int, name: str):
        """Auto-populate db_column and ui_header based on field name."""
        ui_header = name.replace("_", " ").title()
        ui_item = self.fields_table.item(row, 1)
        if ui_item and not ui_item.text():  # Only if empty
            self.fields_table.blockSignals(True)
            ui_item.setText(ui_header)
            self.fields_table.blockSignals(False)

        db_column = self._lookup_db_column(name)
        if db_column:
            db_item = self.fields_table.item(row, 2)
            if db_item and not db_item.text():  # Only if empty
                self.fields_table.blockSignals(True)
                db_item.setText(db_column)
                self.fields_table.blockSignals(False)

        id3_tag = self._lookup_id3_tag(name)
        if id3_tag:
            tag_item = self.fields_table.item(row, 10)
            if tag_item and not tag_item.text(): # Only if empty
                self.fields_table.blockSignals(True)
                tag_item.setText(id3_tag)
                self.fields_table.blockSignals(False)

    def _lookup_db_column(self, field_name: str) -> str:
        """Look up db_column by parsing DATABASE.md schema, or guess."""
        if field_name in self._code_fields:
            return self._code_fields[field_name].db_column
            
        # 1. Parse DATABASE.md schema (cached)
        if not hasattr(self, "_db_schema_cache"):
            self._db_schema_cache = self._parse_database_md_schema()
            
        # 2. Convert name to PascalCase for lookup
        pascal_name = "".join(word.title() for word in field_name.split("_"))
        
        # 3. Check known tables in priority order
        # Map: TableName -> Alias
        table_aliases = {
            "MediaSources": "MS",
            "Songs": "S",
            "Contributors": "C",
            "Roles": "R"
        }
        
        for table, alias in table_aliases.items():
            if table in self._db_schema_cache:
                if pascal_name in self._db_schema_cache[table]:
                    return f"{alias}.{pascal_name}"
                    
        # 4. Fallback: No guess, leave empty so user must define it
        return ""

    def _parse_database_md_schema(self) -> dict:
        """Parse erDiagram from DATABASE.md to build a schema map."""
        import re
        schema = {}
        
        md_path = Path(__file__).parent.parent / "DATABASE.md"
        if not md_path.exists():
            return {}
            
        try:
            content = md_path.read_text(encoding="utf-8")
        except Exception:
            return {}

        # Regex to find table blocks: TableName { ... }
        # Matches: MediaSources { ...body... }
        block_pattern = re.compile(r'(\w+)\s*\{([^}]+)\}', re.DOTALL)
        
        for match in block_pattern.finditer(content):
            table_name = match.group(1)
            body = match.group(2)
            
            columns = set()
            # Parse lines like: TYPE ColumnName PK/FK...
            # e.g. TEXT Name
            for line in body.split('\n'):
                line = line.strip()
                if not line or line.startswith('%%'): continue
                
                parts = line.split()
                if len(parts) >= 2:
                    # parts[0] is Type (INTEGER, TEXT, etc)
                    # parts[1] is ColumnName
                    col_name = parts[1]
                    columns.add(col_name)
            
            schema[table_name] = columns
            
        return schema

    def _on_defaults_changed(self, col_name: str, checked: bool):
        """Handle changes to default checkboxes (triggers re-coloring, NOT bulk edit)."""
        self._apply_all_colors()

    def _set_checkbox_cell(self, row: int, col: int, checked: bool):
        """Create a centered checkbox widget in a table cell."""
        checkbox = QCheckBox()
        checkbox.setChecked(checked)

        # Special handling for portable column (col 10)
        if col == 10:
            checkbox.toggled.connect(lambda chk: self._handle_checkbox_toggle(checkbox, is_portable=True))
        else:
            checkbox.toggled.connect(lambda chk: self._handle_checkbox_toggle(checkbox))

        # Center the checkbox in the cell
        widget = QWidget()
        widget.setObjectName("cell_wrapper")
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setAutoFillBackground(True)

        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add a hidden item for sorting purposes (0 or 1)
        sort_item = QTableWidgetItem()
        sort_item.setData(Qt.ItemDataRole.DisplayRole, "")
        sort_item.setData(Qt.ItemDataRole.UserRole, int(checked))
        sort_item.setText("1" if checked else "0")
        sort_item.setForeground(QColor(0, 0, 0, 0))

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
        for col in range(5, 11): # Boolean columns (Vis=5 -> Port=10)
            widget = self.fields_table.cellWidget(row, col)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    item = self.fields_table.item(row, col)
                    if item:
                         item.setText("1" if cb.isChecked() else "0")

        self._mark_row_dirty(row)

    def _on_portable_toggled(self, row: int, checked: bool):
        """Handle portable checkbox toggle - auto-lookup ID3 tag."""
        if checked:
            # Get field name from row
            name_item = self.fields_table.item(row, 0)
            if name_item:
                field_name = name_item.text()
                id3_tag = self._lookup_id3_tag(field_name)
                # Update ID3 Tag cell (column 11)
                id3_item = self.fields_table.item(row, 11)
                if id3_item:
                    id3_item.setText(id3_tag)
                else:
                    self.fields_table.setItem(row, 11, QTableWidgetItem(id3_tag))

        self._mark_row_dirty(row)

    def _on_dropdown_changed(self, row: int):
        """Handle dropdown change - mark dirty and recolor."""
        self._mark_row_dirty(row)

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

    def _set_editable_combo(self, row: int, col: int, current_val: str, options: list):
        """Create an editable combo box for Filter/Group columns."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(options)
        combo.setCurrentText(current_val)
        combo.currentTextChanged.connect(lambda t: self._on_dropdown_changed(row))
        self.fields_table.setCellWidget(row, col, combo)

    def _set_cell_bg(self, row: int, col: int, color_hex: str):
        """Set background for a specific cell/widget."""
        qcolor = QColor(color_hex) if color_hex else QColor(0, 0, 0, 0)

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

        # Strategy (4) - Default empty
        self._set_editable_combo(row, 4, "", STRATEGY_OPTIONS)

        self._set_checkbox_cell(row, 5, get_default("visible"))
        self._set_checkbox_cell(row, 6, get_default("editable"))
        self._set_checkbox_cell(row, 7, get_default("filterable"))
        self._set_checkbox_cell(row, 8, get_default("searchable"))
        self._set_checkbox_cell(row, 9, get_default("required"))
        self._set_checkbox_cell(row, 10, get_default("portable"))
        
        
        # ID3 Tag (11) - Read Only (will auto-populate when name is set)
        id3_item = QTableWidgetItem("")
        id3_item.setFlags(id3_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        id3_item.setToolTip("Derived from id3_frames.json. Edit JSON to change mapping.")
        self.fields_table.setItem(row, 11, id3_item)
        
        # Validation (12)
        val_item = QTableWidgetItem("")
        val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.fields_table.setItem(row, 12, val_item)

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
        4: 'strategy',
        5: 'visible', 6: 'editable', 7: 'filterable', 8: 'searchable', 9: 'required', 10: 'portable',
        11: 'id3_tag'
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

        # Parse Strategy (Column 4)
        strategy_display = combo(4)
        strategy = {
            "Range Filter": "range",
            "Boolean Toggle": "boolean",
            "Decade Grouping": "decade_grouper",
            "First Letter": "first_letter_grouper",
        }.get(strategy_display, "list")

        return FieldSpec(
            name=txt(0),
            ui_header=txt(1),
            db_column=txt(2),
            field_type=combo(3),
            strategy=strategy,
            visible=check(5),
            editable=check(6),
            filterable=check(7),
            searchable=check(8),
            required=check(9),
            portable=check(10),
            id3_tag=txt(11) or None
        )

    def _apply_row_colors(self, row: int):
        """Re-evaluate and apply colors for a specific row based on values."""

        current_spec = self._get_field_spec_from_row(row)
        name = current_spec.name

        # Look up originals (empty name won't be found, which is correct -> New Field)
        code_orig = self._code_fields.get(name)
        md_orig = self._md_fields.get(name)

        # Map cols back to attribute names for source checking
        col_map = {
            0: 'name', 1: 'ui_header', 2: 'db_column', 3: 'field_type',
            # 4 is Strategy (Special handling)
            5: 'visible', 6: 'editable', 7: 'filterable', 8: 'searchable', 9: 'required', 10: 'portable',
            11: 'id3_tag', 12: 'validation'
        }
        for col in range(self.fields_table.columnCount()):
            # Name column (0) - never show blue (doc drift), star indicates query_expression
            if col == 0:
                # Only show red (code diff) or green (new), never blue
                final_color = None
                if not code_orig and not md_orig:
                    final_color = self.COLOR_NEW_FIELD
                self._set_cell_bg(row, col, final_color)
                continue
            
            # Handle Strategy (Column 4)
            if col == 4:
                cell_code_diff = False
                cell_md_diff = False
                
                # Check Code
                if code_orig:
                    c_strat = current_spec.strategy or "list"
                    o_strat = code_orig.strategy or "list"
                    if c_strat != o_strat:
                        cell_code_diff = True
                elif not code_orig:
                    cell_code_diff = True

                # Check MD (MD doesn't have strategy, skip blue)
                # cell_md_diff stays False
                
                # Apply Color Logic (Reuse standard logic block? No, easier to set explicit)
                final_color = None
                if cell_code_diff and cell_md_diff: final_color = self.COLOR_DIFFERS_BOTH
                elif cell_code_diff: final_color = self.COLOR_DIFFERS_CODE
                elif cell_md_diff: final_color = self.COLOR_DIFFERS_MD
                elif not code_orig and not md_orig: final_color = self.COLOR_NEW_FIELD
                
                self._set_cell_bg(row, col, final_color)
                continue

            attr = col_map.get(col)
            if not attr:
                continue # specific buttons or spacers?

            # T-19 Check: Validation is not part of FieldSpec
            if attr == 'validation':
                continue

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
                cell_code_diff = True  # Entirely missing from code

            if md_orig:
                orig_val = getattr(md_orig, attr)
                if isinstance(current_val, str):
                   if (current_val or "") != (orig_val or ""): cell_md_diff = True
                elif current_val != orig_val: cell_md_diff = True
            elif not md_orig:
                cell_md_diff = True

            # C. Determine Priority
            # Special case: ID3 Tag column (11) when portable=False -> disabled/black
            if col == 11:
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
    def _apply_all_colors(self):
        """Re-scan all rows and apply colors."""
        for row in range(self.fields_table.rowCount()):
            self._apply_row_colors(row)
        self._update_status()

    def _gather_fields_for_save(self) -> list:
        """Collect fields from UI, merge with originals, sort by order."""
        from dataclasses import replace

        fields_by_name = {}
        for row in range(self.fields_table.rowCount()):
            ui_spec = self._get_field_spec_from_row(row)
            if not ui_spec.name:
                continue

            original = self._code_fields.get(ui_spec.name) or self._md_fields.get(ui_spec.name)

            if original:
                merged = replace(original,
                    name=ui_spec.name,
                    ui_header=ui_spec.ui_header,
                    db_column=ui_spec.db_column,
                    field_type=ui_spec.field_type,
                    strategy=ui_spec.strategy,
                    visible=ui_spec.visible,
                    editable=ui_spec.editable,
                    filterable=ui_spec.filterable,
                    searchable=ui_spec.searchable,
                    required=ui_spec.required,
                    portable=ui_spec.portable,
                    id3_tag=ui_spec.id3_tag
                )
                fields_by_name[ui_spec.name] = merged
            else:
                if ui_spec.name not in self._field_order:
                    self._field_order[ui_spec.name] = max(self._field_order.values(), default=-1) + 1
                fields_by_name[ui_spec.name] = ui_spec

        return sorted(fields_by_name.values(), key=lambda f: self._field_order.get(f.name, 9999))

    def _validate_id3_tags(self, fields: list) -> bool:
        """Check ID3 tags and prompt user if issues found. Returns True to proceed."""
        from PyQt6.QtWidgets import QMessageBox
        import json

        # Find portable fields without ID3 mapping
        missing_tags = [f.name for f in fields if f.portable and not self._lookup_id3_tag(f.name)]
        unknown_tags = [f"{f.name} ('{f.id3_tag}')" for f in fields
                        if f.portable and f.id3_tag and f.id3_tag not in self._id3_frames]

        # Handle unknown tags (separate warning)
        if unknown_tags:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Unknown ID3 Tags")
            msg.setText("Unknown ID3 tags found:")
            msg.setInformativeText("\n".join(f"  - {t}" for t in unknown_tags) + "\n\nSave anyway?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if msg.exec() != QMessageBox.StandardButton.Yes:
                return False

        # Handle missing mappings with auto-add popup
        if missing_tags:
            if self._test_mode:
                # In test mode, auto-add without popup
                self._add_txxx_entries(missing_tags)
                return True
            
            field_list = ", ".join(missing_tags)
            txxx_entries = ", ".join(f"TXXX:{name}" for name in missing_tags)
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Missing ID3 Mapping")
            msg.setText(f"The following portable fields have no ID3 mapping:\n{field_list}")
            msg.setInformativeText(
                f"Should the editor add TXXX entries for you?\n\n"
                f"• Yes: Adds {txxx_entries} to id3_frames.json and continues save.\n"
                f"• No: Cancels save. You'll need to edit the JSON manually."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                if self._add_txxx_entries(missing_tags):
                    # Reload ID3 frames so lookup works for the rest of save
                    self._load_id3_defs()
                    return True
                else:
                    QMessageBox.critical(self, "Error", "Failed to update id3_frames.json")
                    return False
            else:
                self.status_bar.showMessage("Save cancelled - edit id3_frames.json manually")
                return False

        return True

    def _add_txxx_entries(self, field_names: list) -> bool:
        """Add TXXX entries to id3_frames.json for the given field names."""
        import json
        
        json_path = Path(__file__).parent.parent / "src" / "resources" / "id3_frames.json"
        
        try:
            # Create backup
            backup_path = json_path.with_suffix(".json.bak")
            if json_path.exists():
                import shutil
                shutil.copy2(json_path, backup_path)
            
            # Load current JSON
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Add TXXX entries
            for name in field_names:
                key = f"TXXX:{name}"
                if key not in data:
                    data[key] = {
                        "description": f"Custom field: {name}",
                        "field": name,
                        "type": "text"
                    }
            
            # Write back
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error adding TXXX entries: {e}")
            return False

    def _validate_db_columns(self, fields: list) -> bool:
        """Check for missing DB columns and prompt user with auto-generate option."""
        from PyQt6.QtWidgets import QMessageBox

        missing_cols = [f for f in fields if not f.db_column]

        if not missing_cols:
            return True

        field_names = [f.name for f in missing_cols]
        field_list = ", ".join(field_names)
        example_cols = ", ".join(f"{name}" for name in field_names[:3])
        if len(field_names) > 3:
            example_cols += ", ..."

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Missing Database Columns")
        msg.setText(f"The following fields have no Database Column defined:\n{field_list}")
        msg.setInformativeText(
            f"Should the editor generate default column names?\n\n"
            f"• Yes: Sets columns to {{field_name}} (e.g., {example_cols})\n"
            f"• No: Cancels save. You'll need to enter columns manually."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Auto-fill the DB column cells in the table
            for f in missing_cols:
                default_col = f"{f.name}"
                # Find the row for this field and update column 2 (DB Column)
                for row in range(self.fields_table.rowCount()):
                    name_item = self.fields_table.item(row, 0)
                    if name_item and name_item.text() == f.name:
                        self.fields_table.item(row, 2).setText(default_col)
                        break
            self.status_bar.showMessage(f"Auto-generated DB columns for {len(missing_cols)} field(s)")
            return True  # Continue with save (fields list will be re-gathered)
        else:
            self.status_bar.showMessage("Save cancelled - enter DB columns manually")
            return False

    def _on_save_clicked(self):
        """Save changes to yellberus.py and FIELD_REGISTRY.md."""
        from tools.yellberus_parser import write_yellberus, write_field_registry_md
        from PyQt6.QtWidgets import QMessageBox

        fields_to_save = self._gather_fields_for_save()
        if not fields_to_save:
            return

        # Validate DB Columns (may auto-fill UI cells)
        if not self._validate_db_columns(fields_to_save):
            return
        # Re-gather in case UI was modified by auto-fill
        fields_to_save = self._gather_fields_for_save()

        # Validate ID3 Tags (may add TXXX entries to JSON)
        if not self._validate_id3_tags(fields_to_save):
            return

        yellberus_path = Path(__file__).parent.parent / "src" / "core" / "yellberus.py"
        md_path = Path(__file__).parent.parent / "design" / "FIELD_REGISTRY.md"

        current_defaults = {name: cb.isChecked() for name, cb in self.default_checkboxes.items()}

        success_code = write_yellberus(yellberus_path, fields_to_save, defaults=current_defaults)
        success_md = write_field_registry_md(md_path, fields_to_save)

        if success_code and success_md:
            self.status_bar.showMessage("Saved successfully to both files!")
            self._dirty = False
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
        """Warn about unsaved changes on close."""
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

    def _parse_validation_info(self, path: Path) -> dict:
        """Parse VALIDATION_GROUPS from yellberus.py to map fields to rules."""
        import ast
        try:
            if not path.exists():
                return {}

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    return {}
            
            # Find VALIDATION_GROUPS assignment
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "VALIDATION_GROUPS":
                            
                            try:
                                # Use unparse to strip comments, then literal_eval
                                clean_source = ast.unparse(node.value)
                                val_list = ast.literal_eval(clean_source)
                            except (ValueError, TypeError):
                                continue

                            result = {}
                            if isinstance(val_list, list):
                                for group in val_list:
                                    if not isinstance(group, dict): continue
                                    
                                    name = group.get('name', '')
                                    fields = group.get('fields', [])
                                    
                                    if name and isinstance(fields, list):
                                        f_str = ", ".join(str(f) for f in fields)
                                        result[name] = f_str
                            return result
            return {}
        except Exception:
            return {}

def main():
    """Entry point for the Field Registry Editor."""
    app = QApplication(sys.argv)
    window = FieldEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
