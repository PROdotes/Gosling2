from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QScrollArea, QFrame, QPushButton, QSizePolicy, QLayout, QLayoutItem, QStyle, QStyledItemDelegate
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont, QPainter, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from typing import Any
from src.core import yellberus

class FlowLayout(QLayout):
    """Layout that arranges items horizontally and wraps them to the next line."""
    def __init__(self, parent=None, margin=-1, hspacing=-1, vspacing=-1):
        super().__init__(parent)
        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        del self._items

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hspacing >= 0:
            return self._hspacing
        else:
            return self.smartSpacing(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vspacing >= 0:
            return self._vspacing
        else:
            return self.smartSpacing(QStyle.PixelMetric.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()

    def doLayout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            wid = item.widget()
            space_x = self.horizontalSpacing()
            if space_x == -1: space_x = 0
            space_y = self.verticalSpacing()
            if space_y == -1: space_y = 0
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom

class FilterTreeDelegate(QStyledItemDelegate):
    """Delegate for drawing hierarchical backgrounds without hardcoding in the model."""

    def paint(self, painter: QPainter, option, index):

        # 1. Base Setup
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        hint = index.data(Qt.ItemDataRole.AccessibleTextRole)
        field_name = index.data(Qt.ItemDataRole.UserRole + 1)
        if not field_name: # Climb up to find the root's field
            p = index.parent()
            while p.isValid():
                field_name = p.data(Qt.ItemDataRole.UserRole + 1)
                if field_name: break
                p = p.parent()
        
        # Pull semantic color from Yellberus Registry (Surgical Rule)
        field_def = yellberus.get_field(field_name)
        if field_def:
            sig_color = QColor(field_def.color)
        else:
            sig_color = QColor("#FFC66D") # System Default
            
        full_row_rect = QRect(0, option.rect.y(), option.widget.width(), option.rect.height())
        
        # 2. Draw Background & Hover (Physical Chassis)
        if option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(full_row_rect, QColor("#333333")) # Mechanical Lift
        elif hint == "root":
            painter.fillRect(full_row_rect, QColor("#1A1A1A"))
        elif hint == "branch":
            painter.fillRect(full_row_rect, QColor("#111111"))
            
        # 3. Draw THE CHANNEL STRIP (The Continuity Rule)
        # We draw the strip at absolute x=0 to create the flush left edge
        strip_width = 4 if (option.state & QStyle.StateFlag.State_Selected) else 2
        painter.fillRect(0, option.rect.y(), strip_width, option.rect.height(), sig_color)
            
        # 4. Root Divider
        if hint == "root":
            painter.setPen(QColor("#222222"))
            painter.drawLine(full_row_rect.bottomLeft(), full_row_rect.bottomRight())

        painter.restore()
        
        # 5. Typographic Hierarchy (Mechanical Stepping)
        # We restore the 'Inside' relationship with fixed 15px offsets.
        root_x = 30
        branch_x = 45
        child_x = 60
        
        if hint == "root":
            painter.save()
            font = option.font
            font.setBold(True)
            font.setPointSize(11)
            painter.setFont(font)
            painter.setPen(QColor("#FFFFFF"))
            text_rect = option.rect.adjusted(root_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
        
        elif hint == "branch":
            painter.save()
            painter.setPen(QColor("#AAAAAA"))
            text_rect = option.rect.adjusted(branch_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()

        else:
            # DATA CHILD: Manual LED Drawing (Stepped to child_x)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 1. Draw Indicator LED
            led_size = 8
            led_rect = QRect(child_x, option.rect.y() + (option.rect.height() - led_size)//2, led_size, led_size)
            
            # Rock-Solid Check Detection (Handles PyQt Enum vs Int ambiguity)
            check_val = index.data(Qt.ItemDataRole.CheckStateRole)
            is_checked = (check_val == Qt.CheckState.Checked or check_val == 2)
            
            if is_checked:
                # GLOWING CORE: Use sig_color with high saturation
                painter.setBrush(sig_color)
                painter.setPen(QPen(sig_color, 1)) # Subtle glow border
                painter.drawEllipse(led_rect)
            else:
                # DIM VOID: Low-poly ring
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#444444"), 1))
                painter.drawEllipse(led_rect)
            
            # 2. Draw Data Text
            painter.setPen(QColor("#888888"))
            text_rect = option.rect.adjusted(child_x + 18, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()




class FilterWidget(QWidget):
    """Widget for filtering the library using Yellberus registry."""
    
    # Signals - one generic signal with (field_name, value)
    filter_changed = pyqtSignal(str, object)  # (field_name, value)
    filter_mode_changed = pyqtSignal(str)     # "AND" or "OR"
    multicheck_filter_changed = pyqtSignal(dict) # {field_name: set(values)}
    reset_filter = pyqtSignal()
    
    # Legacy signals for backward compatibility
    filter_by_performer = pyqtSignal(str)
    filter_by_unified_artist = pyqtSignal(str)  # T-17
    filter_by_composer = pyqtSignal(str)
    filter_by_year = pyqtSignal(int)
    filter_by_status = pyqtSignal(bool)

    def __init__(self, library_service, parent=None) -> None:
        super().__init__(parent)
        self.library_service = library_service
        self._active_filters = {} # {field_name: set(values)}
        self._block_signals = False
        self._filter_match_mode = "AND"
        
        self._init_ui()
        self.populate()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        from PyQt6.QtWidgets import QCheckBox, QHBoxLayout
        
        # 1. THE DATA ENGINE (Model & View)
        # Create these first so Command Rail can connect signals
        self.tree_model = QStandardItemModel()
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        self.tree_view = QTreeView()
        self.tree_view.setObjectName("FilterTree")
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True) # Hide "1" column header
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.setIndentation(0) # KILL THE ZIG-ZAG (Surgical Rule)
        self.tree_view.clicked.connect(self._on_tree_clicked) # Row-level toggling
        self.tree_view.doubleClicked.connect(self._on_tree_double_clicked)
        self.tree_view.setItemDelegate(FilterTreeDelegate())

        # 2. COMMAND RAIL (HUD Level Control)
        rail_layout = QHBoxLayout()
        rail_layout.setSpacing(4)
        
        btn_expand = QPushButton("ALL +")
        btn_expand.setObjectName("CommandButton")
        btn_expand.clicked.connect(self.tree_view.expandAll)
        rail_layout.addWidget(btn_expand)
        
        btn_collapse = QPushButton("ALL -")
        btn_collapse.setObjectName("CommandButton")
        btn_collapse.clicked.connect(self.tree_view.collapseAll)
        rail_layout.addWidget(btn_collapse)
        
        rail_layout.addStretch()
        
        self.btn_match_mode = QPushButton("MATCH: ALL")
        self.btn_match_mode.setObjectName("CommandButton")
        self.btn_match_mode.setCheckable(True)
        # Arm the button visually at launch (matches default 'AND' logic)
        self.btn_match_mode.setChecked(True) 
        self.btn_match_mode.clicked.connect(self._on_toggle_match_mode)
        rail_layout.addWidget(self.btn_match_mode)
        
        layout.addLayout(rail_layout)
        
        # 4. PRIMARY VIEWPORT
        layout.addWidget(self.tree_view, 1) # Give tree the space

        # 5. CHIP BAY (T-55)
        self.chip_bay_scroll = QScrollArea()
        self.chip_bay_scroll.setObjectName("ChipBayScroll")
        self.chip_bay_scroll.setWidgetResizable(True)
        self.chip_bay_scroll.setMinimumHeight(85)
        self.chip_bay_scroll.setMaximumHeight(150)
        self.chip_bay_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chip_bay_scroll.setVisible(False)
        
        self.chip_container = QWidget()
        self.chip_layout = FlowLayout(self.chip_container, margin=4, hspacing=6, vspacing=6)
        self.chip_bay_scroll.setWidget(self.chip_container)
        
        layout.addWidget(self.chip_bay_scroll)



    def populate(self) -> None:
        """Populate the filter tree from Yellberus registry."""
        self.tree_model.clear()
        
        # Get filterable fields from Yellberus
        filterable_fields = yellberus.get_filterable_fields()
        
        # CATEGORY STRATEGY: Group by Color Zone (SYSTEM -> IDENTITY -> ATTRIBUTE)
        # Priority: Green (#43A047), Blue (#2979FF), Amber (#FFC66D)
        zone_priority = {
            "#43A047": 1, # SYSTEM (Green)
            "#2979FF": 2, # IDENTITY (Blue)
            "#FFC66D": 3, # ATTRIBUTE (Amber)
            "#AAAAAA": 4  # RECESSED (Gray)
        }
        
        sorted_fields = sorted(filterable_fields, key=lambda f: (
            zone_priority.get(f.color, 99),
            f.ui_header.lower()
        ))
        
        for field in sorted_fields:
            if field.strategy in ("list", "decade_grouper", "first_letter_grouper"):
                self._add_list_filter(field)
            elif field.strategy == "boolean":
                self._add_boolean_filter(field)
            elif field.strategy == "range":
                self._add_range_filter(field)

    def _add_list_filter(self, field: yellberus.FieldDef) -> None:
        """Add a list-type filter (performers, years, etc.)."""
        # Get values based on field name
        values = self._get_field_values(field)
        if not values:
            return
        
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole) # Structural hint

        
        # Check if field has a grouping strategy
        grouper_fn = yellberus.GROUPERS.get(field.strategy)
        if grouper_fn:
            self._add_grouped_items(root_item, field, values, grouper_fn)
        else:
            # Simple list (no grouping)
            for value in values:
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                root_item.appendRow(item)
        
        self.tree_model.appendRow(root_item)
        
    def _add_grouped_items(self, root_item, field, values, grouper_fn):
        """Add items grouped by grouper function (e.g., decade)."""
        groups = {}
        for value in values:
            group_name = grouper_fn(value)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(value)
        
        # Sort groups (e.g., "2020s", "2010s" - reverse for years)
        for group_name in sorted(groups.keys(), reverse=True):
            group_item = QStandardItem(group_name)
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            group_item.setData("branch", Qt.ItemDataRole.AccessibleTextRole)

            
            for value in sorted(groups[group_name], reverse=True):
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                group_item.appendRow(item)
            
            root_item.appendRow(group_item)

    def _add_alpha_grouped_items(self, root_item, field, values):
        """Add items grouped by first letter (A-Z)."""
        # Get unique first letters
        first_chars = set()
        for value in values:
            if value:
                first_chars.add(str(value)[0].upper())
        
        alpha_map = {}
        for char in sorted(first_chars):
            letter_item = QStandardItem(char)
            letter_item.setFlags(letter_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            letter_item.setData("branch", Qt.ItemDataRole.AccessibleTextRole)
            
            alpha_map[char] = letter_item
            root_item.appendRow(letter_item)
        
        for value in values:
            if not value:
                continue
            first_letter = str(value)[0].upper()
            parent_item = alpha_map.get(first_letter)
            if parent_item:
                item = QStandardItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(value, Qt.ItemDataRole.UserRole)
                item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                parent_item.appendRow(item)
        
        # Expansion removed for Surgical Launch Consistency

    def _add_boolean_filter(self, field: yellberus.FieldDef) -> None:
        """Add a boolean filter (done/not done)."""
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole) # Structural hint

        
        # Context-Aware Labels (Surgical HUD Precision)
        if field.name == "is_done":
            label_false = "Not Done (Pending)"
            label_true  = "Done (Complete)"
        elif "active" in field.name.lower():
            label_false = "Inactive (Disabled)"
            label_true  = "Active (Live)"
        else:
            label_false = "False"
            label_true  = "True"

        # False option
        item_false = QStandardItem(label_false)
        item_false.setFlags(item_false.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item_false.setCheckState(Qt.CheckState.Unchecked)
        item_false.setData(False, Qt.ItemDataRole.UserRole)
        item_false.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(item_false)

        # Procedural: READY option (Valid but Not Done)
        if field.name == "is_done":
            item_ready = QStandardItem("Ready (Complete/Unchecked)")
            item_ready.setFlags(item_ready.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
            item_ready.setCheckState(Qt.CheckState.Unchecked)
            item_ready.setData("READY", Qt.ItemDataRole.UserRole)
            item_ready.setData(field.name, Qt.ItemDataRole.UserRole + 1)
            root_item.appendRow(item_ready)
        
        # True option
        item_true = QStandardItem(label_true)
        item_true.setFlags(item_true.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item_true.setCheckState(Qt.CheckState.Unchecked)
        item_true.setData(True, Qt.ItemDataRole.UserRole)
        item_true.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(item_true)
        
        self.tree_model.appendRow(root_item)
        




    def _add_range_filter(self, field: yellberus.FieldDef) -> None:
        """Add a range filter (BPM, etc.) - placeholder for future."""
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole) # Structural hint
        self.tree_model.appendRow(root_item)


    def _get_display_label(self, field: yellberus.FieldDef, value: Any) -> str:
        """Get human-readable label for a value (e.g., True -> Live)."""
        if field.strategy == "boolean":
            if field.name == "is_done":
                if value == "READY": return "Ready"
                return "Complete" if value else "Pending"
            elif "active" in field.name.lower():
                return "Live" if value else "Disabled"
            return str(value)
        return str(value)

    def _get_field_values(self, field: yellberus.FieldDef):
        """Get unique values for a field - dynamically from Yellberus."""
        
        # Special case: unified_artist needs alias handling (Identity Graph)
        if field.name == "unified_artist":
            artists = set()
            # Get performers
            for _, name in self.library_service.get_contributors_by_role("Performer"):
                if name:
                    artists.add(name)
            # Get aliases (Fix for "No Nixon in list")
            for alias in self.library_service.get_all_aliases():
                if alias:
                    artists.add(alias)
            return sorted(list(artists))
        
        # Dynamic: Use field's query_expression or db_column
        expression = field.query_expression or field.db_column
        if not expression:
            return []
        
        try:
            return self.library_service.get_distinct_filter_values(expression)
        except Exception as e:
            # Log but don't crash - filter just won't show
            print(f"[FilterWidget] Failed to get values for {field.name}: {e}")
            return []

    def _on_item_changed(self, item) -> None:
        """Handle checkbox state change in the tree."""
        if self._block_signals: return
        
        field_name = item.data(Qt.ItemDataRole.UserRole + 1)
        value = item.data(Qt.ItemDataRole.UserRole)
        
        if field_name and value is not None:
             is_checked = item.checkState() == Qt.CheckState.Checked
             
             if field_name not in self._active_filters:
                 self._active_filters[field_name] = set()
             
             if is_checked:
                 self._active_filters[field_name].add(value)
             else:
                 self._active_filters[field_name].discard(value)
             
             self.multicheck_filter_changed.emit(self._active_filters)
             self._sync_chip_bay()

    def _sync_chip_bay(self):
        """Update neon chips based on active filters."""
        # Clear Bay
        while self.chip_layout.count():
            child = self.chip_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        total_chips = 0
        for field_name, values in self._active_filters.items():
            field_def = yellberus.get_field(field_name)
            header = field_def.ui_header if field_def else field_name
            
            for val in values:
                # Get human-readable label
                display_val = self._get_display_label(field_def, val) if field_def else str(val)
                label = f"{header}: {display_val}"
                
                # \u2003 is an Em Space (approx width of capital M) - cleaner separation
                chip = QPushButton(f"{label}\u2003×")
                chip.setObjectName("NeonChip")
                # Store enough info to find and uncheck in the tree
                chip.setProperty("field", field_name)
                chip.setProperty("value", val)
                
                # Pull semantic color from Yellberus Registry (Total Unity)
                sig_color = field_def.color if field_def else "#FFC66D"
                chip.setStyleSheet(f"QPushButton#NeonChip {{ border-bottom: 3px solid {sig_color}; }}")

                
                chip.clicked.connect(self._on_chip_clicked)
                self.chip_layout.addWidget(chip)
                total_chips += 1
        
        self.chip_bay_scroll.setVisible(total_chips > 0)

    def _on_chip_clicked(self):
        """Uncheck item in tree when chip is closed."""
        btn = self.sender()
        field_name = btn.property("field")
        val = btn.property("value")
        
        # Find item in tree and uncheck it
        self._set_item_check_state(field_name, val, Qt.CheckState.Unchecked)

    def _set_item_check_state(self, field_name, value, state):
        """Traverse tree to find a specific field/value item and update check state."""
        self._block_signals = True
        try:
            for row in range(self.tree_model.rowCount()):
                root = self.tree_model.item(row)
                if self._traverse_and_set(root, field_name, value, state):
                    break
        finally:
            self._block_signals = False
            # Manually trigger filter update since signals were blocked
            if field_name in self._active_filters:
                if state == Qt.CheckState.Checked:
                    self._active_filters[field_name].add(value)
                else:
                    self._active_filters[field_name].discard(value)
            self.multicheck_filter_changed.emit(self._active_filters)
            self._sync_chip_bay()

    def _traverse_and_set(self, item, field_name, value, state):
        """Recursive helper for _set_item_check_state."""
        if item.data(Qt.ItemDataRole.UserRole + 1) == field_name and item.data(Qt.ItemDataRole.UserRole) == value:
            item.setCheckState(state)
            return True
        
        for row in range(item.rowCount()):
            if self._traverse_and_set(item.child(row), field_name, value, state):
                return True
        return False
    
    def _on_tree_clicked(self, index) -> None:
        """Surgical Navigation: Toggle Data, Expand Headers."""
        item = self.tree_model.itemFromIndex(index)
        if not item: return

        # 1. DATA ITEMS: Single-click toggle (The Switchboard)
        if item.isCheckable():
            new_state = Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            item.setCheckState(new_state)
        
        # 2. HEADERS: Toggle Expansion (The Navigation)
        else:
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    
    def _on_tree_double_clicked(self, index) -> None:
        """Handle double-click in the filter tree."""
        if not index.isValid():
            return
            
        item = self.tree_model.itemFromIndex(index)
        if not item:
            return

        # 1. Root-only: Reset Filter
        if item.parent() is None:
            self.reset_filter.emit()
            
        # 2. Checkable items: Toggle CheckState (QOL)
        if item.isCheckable():
            new_state = Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            item.setCheckState(new_state)
            # _on_item_changed will handle the rest
            return # Don't toggle expansion on checkable items to avoid jumpiness

        # 3. Universal: Toggle expansion (Fixes T-17 expansion bug)
        if self.tree_view.isExpanded(index):
            self.tree_view.collapse(index)
        else:
            self.tree_view.expand(index)

    def _on_toggle_match_mode(self):
        """Toggle between AND/OR logic for across-category filtering."""
        # Flip state manually to ensure sync with Checked state
        if self._filter_match_mode == "AND":
            self._filter_match_mode = "OR"
            self.btn_match_mode.setText("MATCH: ANY")
            self.btn_match_mode.setChecked(False) # Off/Gray
        else:
            self._filter_match_mode = "AND"
            self.btn_match_mode.setText("MATCH: ALL")
            self.btn_match_mode.setChecked(True) # Armed/Amber
            
        self.filter_mode_changed.emit(self._filter_match_mode)

