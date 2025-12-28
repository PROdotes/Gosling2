from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QScrollArea, QFrame, 
    QFrame, QSizePolicy, QLayout, QLayoutItem, QStyle, QStyledItemDelegate
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont, QPainter, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from typing import Any
from ...core import yellberus
from ...resources import constants
from .glow_factory import GlowButton

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
        return self.smartSpacing(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vspacing >= 0:
            return self._vspacing
        return self.smartSpacing(QStyle.PixelMetric.PM_LayoutVerticalSpacing)

    def count(self): return len(self._items)
    def itemAt(self, index): 
        if 0 <= index < len(self._items): return self._items[index]
        return None
    def takeAt(self, index):
        if 0 <= index < len(self._items): return self._items.pop(index)
        return None

    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self._items: size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent: return -1
        elif parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
        else: return parent.spacing()

    def doLayout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
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

            if not test_only: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom

class FilterTree(QTreeView):
    """Tree view for filters."""
    pass

class FilterTreeDelegate(QStyledItemDelegate):
    """Delegate for drawing hierarchical filter tree items.
    Reads colors from QPalette (controlled by QSS), falls back to constants.
    """

    # Zone to color constant mapping (fallbacks)
    ZONE_COLORS = {
        "amber": constants.COLOR_AMBER,
        "muted_amber": constants.COLOR_MUTED_AMBER,
        "magenta": constants.COLOR_MAGENTA,
        "gray": constants.COLOR_GRAY
    }

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Read colors from palette (QSS-controlled)
        palette = option.palette
        text_color = palette.color(palette.ColorRole.Text)
        base_color = palette.color(palette.ColorRole.Base)
        alt_color = palette.color(palette.ColorRole.AlternateBase)
        highlight_color = palette.color(palette.ColorRole.Highlight)
        
        hint = index.data(Qt.ItemDataRole.AccessibleTextRole)
        field_name = index.data(Qt.ItemDataRole.UserRole + 1)
        if not field_name:
            p = index.parent()
            while p.isValid():
                field_name = p.data(Qt.ItemDataRole.UserRole + 1)
                if field_name: break
                p = p.parent()
        
        field_def = yellberus.get_field(field_name)
        zone = field_def.zone if field_def else "amber"
        sig_color = QColor(self.ZONE_COLORS.get(zone, constants.COLOR_AMBER))
            
        full_row_rect = QRect(0, option.rect.y(), option.widget.width(), option.rect.height())
        
        # Backgrounds - use palette colors
        if option.state & QStyle.StateFlag.State_MouseOver:
            hover_color = alt_color if alt_color.isValid() else QColor(constants.COLOR_VOID)
            painter.fillRect(full_row_rect, hover_color)
        elif hint == "root":
            root_bg = base_color if base_color.isValid() else QColor(constants.COLOR_BLACK)
            painter.fillRect(full_row_rect, root_bg)
        elif hint == "branch":
            branch_bg = alt_color if alt_color.isValid() else QColor(constants.COLOR_VOID)
            painter.fillRect(full_row_rect, branch_bg)
            
        strip_width = 4 if (option.state & QStyle.StateFlag.State_Selected) else 2
        painter.fillRect(0, option.rect.y(), strip_width, option.rect.height(), sig_color)
            
        if hint == "root":
            divider_color = alt_color if alt_color.isValid() else QColor(constants.COLOR_VOID)
            painter.setPen(divider_color)
            painter.drawLine(full_row_rect.bottomLeft(), full_row_rect.bottomRight())

        painter.restore()
        
        root_x, branch_x, child_x = 30, 45, 60
        
        if hint == "root":
            painter.save()
            font = option.font
            font.setBold(True); font.setPointSize(11)
            painter.setFont(font)
            root_text = highlight_color if highlight_color.isValid() else QColor(constants.COLOR_WHITE)
            painter.setPen(root_text)
            text_rect = option.rect.adjusted(root_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
        elif hint == "branch":
            painter.save()
            branch_text = text_color if text_color.isValid() else QColor(constants.COLOR_GRAY)
            painter.setPen(branch_text)
            text_rect = option.rect.adjusted(branch_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
        else:
            painter.save()
            led_size = 8
            led_rect = QRect(child_x, option.rect.y() + (option.rect.height() - led_size)//2, led_size, led_size)
            check_val = index.data(Qt.ItemDataRole.CheckStateRole)
            is_checked = (check_val == Qt.CheckState.Checked or check_val == 2)
            if is_checked:
                painter.setBrush(sig_color); painter.setPen(QPen(sig_color, 1))
                painter.drawEllipse(led_rect)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                unchecked_border = alt_color if alt_color.isValid() else QColor(constants.COLOR_VOID)
                painter.setPen(QPen(unchecked_border, 1))
                painter.drawEllipse(led_rect)
            child_text = text_color if text_color.isValid() else QColor(constants.COLOR_GRAY)
            painter.setPen(child_text)
            text_rect = option.rect.adjusted(child_x + 18, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()


class FilterWidget(QFrame):
    """Widget for filtering the library using Yellberus registry."""
    
    # Signals
    filter_changed = pyqtSignal(str, object)
    filter_mode_changed = pyqtSignal(str)
    multicheck_filter_changed = pyqtSignal(dict)
    reset_filter = pyqtSignal()
    
    def __init__(self, library_service, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FilterWidget")
        self.library_service = library_service
        self._active_filters = {}
        self._block_signals = False
        self._filter_match_mode = "AND"
        
        self._init_ui()
        self.populate()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 1. THE DATA ENGINE (Model & View)
        self.tree_model = QStandardItemModel()
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        self.tree_view = FilterTree()
        self.tree_view.setObjectName("FilterTree")
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.setIndentation(0)
        self.tree_view.clicked.connect(self._on_tree_clicked)
        self.tree_view.doubleClicked.connect(self._on_tree_double_clicked)
        self.tree_view.setItemDelegate(FilterTreeDelegate())
        
        # 2. COMMAND RAIL (HUD Level Control)
        rail_layout = QHBoxLayout()
        rail_layout.setSpacing(4)
        
        btn_expand = GlowButton("ALL +")
        btn_expand.setObjectName("CommandButton")
        btn_expand.clicked.connect(self.tree_view.expandAll)
        rail_layout.addWidget(btn_expand)
        
        btn_collapse = GlowButton("ALL -")
        btn_collapse.setObjectName("CommandButton")
        btn_collapse.clicked.connect(self.tree_view.collapseAll)
        rail_layout.addWidget(btn_collapse)
        
        rail_layout.addStretch()
        
        self.btn_match_mode = GlowButton("MATCH: ALL")
        self.btn_match_mode.setObjectName("CommandButton")
        self.btn_match_mode.setCheckable(True)
        self.btn_match_mode.setChecked(True) 
        self.btn_match_mode.clicked.connect(self._on_toggle_match_mode)
        rail_layout.addWidget(self.btn_match_mode)
        
        layout.addLayout(rail_layout)
        
        # 3. PRIMARY VIEWPORT
        layout.addWidget(self.tree_view, 1)

        # 4. CHIP BAY
        self.chip_bay_scroll = QScrollArea()
        self.chip_bay_scroll.setObjectName("ChipBayScroll")
        self.chip_bay_scroll.setWidgetResizable(True)
        self.chip_bay_scroll.setMinimumHeight(85)
        self.chip_bay_scroll.setMaximumHeight(150)
        self.chip_bay_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chip_bay_scroll.setVisible(False)
        
        self.chip_container = QWidget()
        self.chip_container.setObjectName("ChipContainer") # Ensure transparent background via CSS if needed
        self.chip_layout = FlowLayout(self.chip_container, margin=4, hspacing=6, vspacing=6)
        self.chip_bay_scroll.setWidget(self.chip_container)
        
        layout.addWidget(self.chip_bay_scroll)

    def populate(self) -> None:
        """Populate the filter tree from Yellberus registry."""
        self._block_signals = True
        self.tree_model.clear()
        
        filterable_fields = yellberus.get_filterable_fields()
        
        # Group by Color Zone per legacy priority logic if desired, 
        # or just sort by name. Re-using simple sort for now to match recent cleanup.
        sorted_fields = sorted(filterable_fields, key=lambda f: f.ui_header)
        
        for field in sorted_fields:
            if field.strategy in ("list", "decade_grouper", "first_letter_grouper"):
                self._add_list_filter(field)
            elif field.strategy == "boolean":
                self._add_boolean_filter(field)
            elif field.strategy == "range":
                self._add_range_filter(field)
                
        self.tree_view.collapseAll()
        self._block_signals = False

    def _add_list_filter(self, field: yellberus.FieldDef) -> None:
        values = self._get_field_values(field)
        if not values:
            return
        
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)

        grouper_fn = yellberus.GROUPERS.get(field.strategy)
        if grouper_fn:
            self._add_grouped_items(root_item, field, values, grouper_fn)
        else:
            for value in values:
                self._add_leaf_item(root_item, field, value)
        
        self.tree_model.appendRow(root_item)

    def _add_grouped_items(self, root_item, field, values, grouper_fn):
        groups = {}
        for value in values:
            group_name = grouper_fn(value)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(value)
        
        for group_name in sorted(groups.keys(), reverse=True):
            group_item = QStandardItem(group_name)
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            group_item.setData("branch", Qt.ItemDataRole.AccessibleTextRole)
            group_item.setData(field.name, Qt.ItemDataRole.UserRole + 1) # Pass field down

            for value in sorted(groups[group_name], reverse=True):
                self._add_leaf_item(group_item, field, value)
            
            root_item.appendRow(group_item)

    def _add_leaf_item(self, parent, field, value):
        item = QStandardItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setData(value, Qt.ItemDataRole.UserRole)
        item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        parent.appendRow(item)

    def _add_boolean_filter(self, field: yellberus.FieldDef) -> None:
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)
        
        # Context Labels
        label_false, label_true = "False", "True"
        if field.name == "is_done":
            label_false, label_true = "Not Done", "Done"
        elif "active" in field.name.lower():
            label_false, label_true = "No", "Yes"
            
        # False option
        item_false = QStandardItem(label_false)
        item_false.setFlags(item_false.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item_false.setCheckState(Qt.CheckState.Unchecked)
        item_false.setData(False, Qt.ItemDataRole.UserRole)
        item_false.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.appendRow(item_false)

        # Procedural: READY option (Valid but Not Done)
        if field.name == "is_done":
            item_ready = QStandardItem("Pending")
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

    def _add_range_filter(self, field):
        # Placeholder
        pass

    def _get_field_values(self, field: yellberus.FieldDef):
        if field.name == "unified_artist":
            # Merge logic for Unified Artist
            artists = set()
            for _, name in self.library_service.get_contributors_by_role("Performer"):
                if name: artists.add(name)
            for alias in self.library_service.get_all_aliases():
                if alias: artists.add(alias)
            return sorted(list(artists))
        
        expression = field.query_expression or field.db_column
        if not expression: return []
        try:
            return self.library_service.get_distinct_filter_values(field.name)
        except Exception:
            return []

    # --- INTERACTION LOGIC ---

    def _on_tree_clicked(self, index) -> None:
        item = self.tree_model.itemFromIndex(index)
        if not item: return

        # IMPORTANT: Click handling (The Switchboard)
        # Even single clicks on the row (not just the checkbox) should toggle checkable items
        if item.isCheckable():
            new_state = Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            item.setCheckState(new_state)
        else:
            # For non-checkable items (headers/branches), toggle expansion
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def _on_tree_double_clicked(self, index) -> None:
        if not index.isValid(): return
        item = self.tree_model.itemFromIndex(index)
        if not item: return
        
        # Reset filter on root doubleclick if it's a root
        if item.parent() is None:
            self.reset_filter.emit()

    def _on_item_changed(self, item):
        if self._block_signals: return
        
        field_name = item.data(Qt.ItemDataRole.UserRole + 1)
        val = item.data(Qt.ItemDataRole.UserRole)
        
        if field_name and val is not None:
             is_checked = item.checkState() == Qt.CheckState.Checked
             if field_name not in self._active_filters: self._active_filters[field_name] = set()
             
             if is_checked: self._active_filters[field_name].add(val)
             else: self._active_filters[field_name].discard(val)
             
             self.multicheck_filter_changed.emit(self._active_filters)
             self._sync_chip_bay()

    def _sync_chip_bay(self):
        # Clear
        while self.chip_layout.count():
            child = self.chip_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        total_chips = 0
        for field_name, values in self._active_filters.items():
            field_def = yellberus.get_field(field_name)
            header = field_def.ui_header if field_def else field_name
            zone = field_def.zone if field_def else "amber"
            
            for val in values:
                display_val = str(val)
                if field_name == "is_done":
                    if val == "READY": display_val = "Pending"
                    elif val is False: display_val = "Not Done"
                    elif val is True: display_val = "Done"
                elif "active" in field_name.lower():
                    if val is False: display_val = "No"
                    elif val is True: display_val = "Yes"
                
                label = f"{header}: {display_val}"
                chip = QPushButton(f"{label} \u00D7")
                # Clean identifier for QSS without hardcoding style
                chip.setObjectName(f"Chip_{field_name}") 
                chip.setProperty("field", field_name); chip.setProperty("value", val)
                
                # Dynamic visual hint from QSS via Property
                chip.setProperty("zone", zone)
                
                chip.clicked.connect(self._on_chip_clicked)
                self.chip_layout.addWidget(chip)
                total_chips += 1
                
        self.chip_bay_scroll.setVisible(total_chips > 0)

    def _on_chip_clicked(self):
        btn = self.sender()
        field = btn.property("field")
        val = btn.property("value")
        self._set_item_check_state(field, val, Qt.CheckState.Unchecked)

    def _set_item_check_state(self, field_name, value, state):
        self._block_signals = True
        try:
             # DFS to find item
             for row in range(self.tree_model.rowCount()):
                 if self._traverse_and_set(self.tree_model.item(row), field_name, value, state):
                     break
        finally:
            self._block_signals = False
            # Manual trigger
            if field_name in self._active_filters:
                if state == Qt.CheckState.Unchecked: self._active_filters[field_name].discard(value)
            self.multicheck_filter_changed.emit(self._active_filters)
            self._sync_chip_bay()

    def _traverse_and_set(self, item, field_name, value, state):
        if item.data(Qt.ItemDataRole.UserRole + 1) == field_name and item.data(Qt.ItemDataRole.UserRole) == value:
            item.setCheckState(state)
            return True
        for row in range(item.rowCount()):
            if self._traverse_and_set(item.child(row), field_name, value, state): return True
        return False

    def _on_toggle_match_mode(self):
        if self._filter_match_mode == "AND":
            self._filter_match_mode = "OR"
            self.btn_match_mode.setText("MATCH: ANY")
            self.btn_match_mode.setChecked(False)
        else:
            self._filter_match_mode = "AND"
            self.btn_match_mode.setText("MATCH: ALL")
            self.btn_match_mode.setChecked(True)
        self.filter_mode_changed.emit(self._filter_match_mode)
