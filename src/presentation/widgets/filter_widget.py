from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTreeView,
    QScrollArea, QPushButton, QLabel, QStyledItemDelegate, QStyle, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPainter, QColor, QBrush, QPen
from ...core import yellberus
from ...core.registries.id3_registry import ID3Registry
from ...resources import constants
from .glow_factory import GlowButton, GlowLED
from .flow_layout import FlowLayout

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
    user_interaction = False

    def mousePressEvent(self, event):
        self.user_interaction = True
        try:
            super().mousePressEvent(event)
        finally:
            self.user_interaction = False

    def keyPressEvent(self, event):
        self.user_interaction = True
        try:
            super().keyPressEvent(event)
        finally:
            self.user_interaction = False

class FilterTreeDelegate(QStyledItemDelegate):
    """Delegate for drawing hierarchical filter tree items.
    Uses Pro Audio Console colors directly for consistency.
    """

    # Zone to color constant mapping
    ZONE_COLORS = {
        "amber": constants.COLOR_AMBER,
        "muted_amber": constants.COLOR_MUTED_AMBER,
        "magenta": constants.COLOR_MAGENTA,
        "gray": constants.COLOR_GRAY
    }
    
    # Pro Console colors (matching theme.qss)
    COLOR_BG_TRANSPARENT = QColor(0, 0, 0, 0)
    COLOR_BG_HOVER = QColor("#1A1A1A")
    COLOR_BG_ROOT = QColor("#0A0A0A")
    COLOR_BG_BRANCH = QColor("#111111")
    COLOR_TEXT_ROOT = QColor("#9A8A70")  # Warm amber labels
    COLOR_TEXT_BRANCH = QColor("#888888")
    COLOR_TEXT_LEAF = QColor("#999999")
    COLOR_TEXT_SELECTED = QColor("#FFC66D")  # Full amber
    COLOR_DIVIDER = QColor("#1A1A1A")

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
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
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hovered = option.state & QStyle.StateFlag.State_MouseOver
        
        # Background painting (transparent by default)
        if is_hovered:
            painter.fillRect(full_row_rect, self.COLOR_BG_HOVER)
        elif hint == "root":
            painter.fillRect(full_row_rect, self.COLOR_BG_ROOT)
        elif hint == "branch":
            painter.fillRect(full_row_rect, self.COLOR_BG_BRANCH)
        # Leaves get transparent background
            
        # Signal rail (left border) - wider when selected
        strip_width = 4 if is_selected else 2
        painter.fillRect(0, option.rect.y(), strip_width, option.rect.height(), sig_color)
            
        # Divider line under roots
        if hint == "root":
            painter.setPen(self.COLOR_DIVIDER)
            painter.drawLine(full_row_rect.bottomLeft(), full_row_rect.bottomRight())

        painter.restore()
        
        root_x, branch_x, child_x = 30, 35, 55
        
        # Root items (section headers)
        if hint == "root":
            painter.save()
            font = option.font
            font.setBold(True)
            font.setPointSize(11)
            painter.setFont(font)
            text_color = self.COLOR_TEXT_SELECTED if is_selected else self.COLOR_TEXT_ROOT
            painter.setPen(text_color)
            text_rect = option.rect.adjusted(root_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
            
        # Branch items (groups like "2020s", "People", etc.)
        elif hint == "branch":
            painter.save()
            text_color = self.COLOR_TEXT_SELECTED if is_selected else self.COLOR_TEXT_BRANCH
            painter.setPen(text_color)
            text_rect = option.rect.adjusted(branch_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
            
        # Leaf items (actual filter values)
        else:
            painter.save()
            
            # Determine indent based on parent type
            parent_hint = index.parent().data(Qt.ItemDataRole.AccessibleTextRole) if index.parent().isValid() else None
            if parent_hint == "root":
                item_x = branch_x
            else:
                item_x = child_x
            
            # LED indicator
            led_size = 8
            led_rect = QRect(item_x, option.rect.y() + (option.rect.height() - led_size)//2, led_size, led_size)
            check_val = index.data(Qt.ItemDataRole.CheckStateRole)
            is_checked = (check_val == Qt.CheckState.Checked or check_val == 2)
            
            ring_col = self.COLOR_BG_BRANCH
            max_r = min((option.rect.height() / 2) - 1, led_size * 2) 
            GlowLED.draw_led(painter, led_rect, sig_color, is_checked, led_size, ring_color=ring_col, max_radius=max_r)
            
            # Text
            text_color = self.COLOR_TEXT_SELECTED if is_selected else self.COLOR_TEXT_LEAF
            painter.setPen(text_color)
            text_rect = option.rect.adjusted(item_x + 18, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()


class FilterWidget(QFrame):
    """Widget for filtering the library using Yellberus registry."""
    
    # Signals
    filter_changed = pyqtSignal(str, object)
    filter_mode_changed = pyqtSignal(str)
    multicheck_filter_changed = pyqtSignal(dict)
    reset_filter = pyqtSignal()
    
    def __init__(self, library_service, settings_manager=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FilterWidget")
        self.library_service = library_service
        self._active_filters = {}
        self._block_signals = False
        self._filter_match_mode = "AND"
        self.settings_manager = settings_manager
        
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
        
        # Connect expansion signals for state persistence
        self.tree_view.expanded.connect(self._on_tree_expanded)
        self.tree_view.collapsed.connect(self._on_tree_collapsed)
        
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
        
        self.btn_match_mode = GlowButton("ALL")
        self.btn_match_mode.setObjectName("CommandButton")
        self.btn_match_mode.setCheckable(True)
        self.btn_match_mode.setChecked(True) 
        self.btn_match_mode.clicked.connect(self._on_toggle_match_mode)
        rail_layout.addWidget(self.btn_match_mode)
        
        layout.addLayout(rail_layout)
        
        # 3. PRIMARY VIEWPORT
        layout.addWidget(self.tree_view, 1)

        # 4. CHIP BAY (Active Filters)
        # Persistent Footer (No Layout Jumps)
        self.chip_bay_scroll = QScrollArea()
        self.chip_bay_scroll.setObjectName("ChipBayScroll")
        self.chip_bay_scroll.setWidgetResizable(True)
        self.chip_bay_scroll.setMinimumHeight(110)
        self.chip_bay_scroll.setMaximumHeight(200)
        self.chip_bay_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chip_bay_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Always Visible
        self.chip_bay_scroll.setVisible(True)
        
        self.chip_container = QWidget()
        self.chip_container.setObjectName("ChipContainer")
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

        # T-71/Req 4: All Contributors (Virtual Filter)
        # This aggregates all roles into one master list
        self._add_all_contributors_filter()
        
        # Virtual Decade Filter (derived from years)
        self._add_decade_filter()
        
        # T-83: Unified Tags Filter (Dynamic Categories)
        self._add_unified_tags_filter()
        
        self._block_signals = False
        
        # Restore saved expansion state
        self.restore_expansion_state()
        
        # Initialize Chip Bay (Show placeholder)
        self._sync_chip_bay()

    def _add_list_filter(self, field: yellberus.FieldDef) -> None:
        values = self._get_field_values(field)
        if not values:
            return
        
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)

        # T-70/User Req 3: Type Grouping for Performers
        if field.name == 'performers':
             self._add_type_grouped_items(root_item, field, values)
        else:
            grouper_fn = yellberus.GROUPERS.get(field.strategy)
            if grouper_fn:
                self._add_grouped_items(root_item, field, values, grouper_fn)
            else:
                for value in values:
                    self._add_leaf_item(root_item, field, value)
        
        self.tree_model.appendRow(root_item)

    def _add_type_grouped_items(self, root, field, values):
        """Group items by Person/Group type."""
        # Fetch types
        # Note: values contains strings.
        from src.core import logger
        
        try:
             type_map = self.library_service.get_types_for_names(values)
        except Exception:
             type_map = {}
             
        bins = {
            'group': [],
            'person': [], 
            'unknown': []
        }
        
        for val in values:
            t = type_map.get(val, 'unknown')
            bins[t].append(val)
            
        # Helper to create a branch
        def add_branch(header, items):
            if not items: return
            branch = QStandardItem(header)
            branch.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
            branch.setCheckState(Qt.CheckState.Unchecked)
            branch.setData("branch", Qt.ItemDataRole.AccessibleTextRole)
            items.sort(key=lambda x: str(x).lower())
            
            for item_val in items:
                self._add_leaf_item(branch, field, item_val)
            
            root.appendRow(branch)

        add_branch("Groups 👥", bins['group'])
        add_branch("People 👤", bins['person'])
        
        # For unknown, add directly to root or branch? 
        # "Unclassified" branch is cleaner.
        add_branch("Unclassified / Aliases", bins['unknown'])

    def _add_grouped_items(self, root_item, field, values, grouper_fn):
        groups = {}
        for value in values:
            group_name = grouper_fn(value)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(value)
        
        for group_name in sorted(groups.keys()):
            group_item = QStandardItem(group_name)
            group_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
            group_item.setCheckState(Qt.CheckState.Unchecked)
            group_item.setData("branch", Qt.ItemDataRole.AccessibleTextRole)
            group_item.setData(field.name, Qt.ItemDataRole.UserRole + 1) # Pass field down

            for value in sorted(groups[group_name]):
                self._add_leaf_item(group_item, field, value)
            
            root_item.appendRow(group_item)

    def _add_all_contributors_filter(self):
        """Add virtual 'All Contributors' filter node."""
        all_names = set()
        
        # Aggregate from actual Song metadata (Source of Truth for Filter)
        # We scan the columns used by the relevant fields.
        target_fields = ['performers', 'composers', 'producers', 'lyricists', 'album_artist']
        
        from src.core import logger
        
        try:
            # We must use the Junction Table logic because columns like 'Performers' 
            # are virtual aggregates, not real columns in the Songs table.
            
            # Use Service methods to fetch contributors and aliases
            all_names = set(self.library_service.get_all_contributor_names())
            
        except Exception as e:
            logger.error(f"Error populating All Contributors filter: {e}")
            
        values = sorted(list(all_names))

        if not values: return

        # Create pseudo-field
        field = yellberus.FieldDef(
            name='all_contributors',
            ui_header='All Contributors',
            db_column='Virtual',
            strategy='list'
        )
        
        root_item = QStandardItem(field.ui_header)
        root_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable) # Root not checkable or editable
        root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
        root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)

        # Reuse Type Grouping logic
        self._add_type_grouped_items(root_item, field, values)
        
        self.tree_model.appendRow(root_item)

    def _add_decade_filter(self):
        """Add virtual Decade filter derived from years."""
        from src.core import logger
        
        try:
            decades = set()
            
            years = self.library_service.get_all_years()
            for year in years:
                if year:
                    try:
                        decade = (int(year) // 10) * 10
                        decades.add(f"{decade}s")
                    except (ValueError, TypeError):
                        pass
            
            if not decades:
                return
            
            # Create pseudo-field
            field = yellberus.FieldDef(
                name='decade',
                ui_header='📅 Decade',
                db_column='Virtual',
                strategy='list'
            )
            
            root_item = QStandardItem(field.ui_header)
            root_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            root_item.setData(field.name, Qt.ItemDataRole.UserRole + 1)
            root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)
            
            # Add decades in reverse order (newest first)
            for decade in sorted(decades, reverse=True):
                self._add_leaf_item(root_item, field, decade)
            
            self.tree_model.appendRow(root_item)
            
        except Exception as e:
            logger.error(f"Error populating decade filter: {e}")

    def _add_unified_tags_filter(self):
        """T-83: Add dynamic Tags filter with categories from database."""
        from src.core import logger
        
        try:
            # Query all tags grouped by category
            # Query all tags grouped by category via Service
            if hasattr(self.library_service, 'tag_service') and self.library_service.tag_service:
                categories = self.library_service.tag_service.get_active_tags()
            else:
                categories = {}
            
            if not categories:
                return  # No tags in use
            
            # Create root: "Tags"
            root_item = QStandardItem("🏷️ Tags")
            root_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            root_item.setData('tags', Qt.ItemDataRole.UserRole + 1)
            root_item.setData("root", Qt.ItemDataRole.AccessibleTextRole)
            
            # Create branches for each category
            for cat_name in sorted(categories.keys()):
                tag_list = categories[cat_name]
                # Get icon from ID3Registry
                icon = ID3Registry.get_category_icon(cat_name, default="📦")
                
                branch = QStandardItem(f"{icon} {cat_name}")
                branch.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                branch.setCheckState(Qt.CheckState.Unchecked)
                branch.setData("branch", Qt.ItemDataRole.AccessibleTextRole)
                branch.setData('tags', Qt.ItemDataRole.UserRole + 1)
                
                # Add leaf items for each tag
                for tag_name in sorted(tag_list):
                    leaf = QStandardItem(tag_name)
                    leaf.setFlags(leaf.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
                    leaf.setCheckState(Qt.CheckState.Unchecked)
                    # Store: "Category:TagName" for filtering
                    leaf.setData(f"{cat_name}:{tag_name}", Qt.ItemDataRole.UserRole)
                    leaf.setData('tags', Qt.ItemDataRole.UserRole + 1)
                    branch.appendRow(leaf)
                
                root_item.appendRow(branch)
            
            self.tree_model.appendRow(root_item)
            
        except Exception as e:
            logger.error(f"Error populating unified tags filter: {e}")

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

            item_incomplete = QStandardItem("Incomplete")
            item_incomplete.setFlags(item_incomplete.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
            item_incomplete.setCheckState(Qt.CheckState.Unchecked)
            item_incomplete.setData("INCOMPLETE", Qt.ItemDataRole.UserRole)
            item_incomplete.setData(field.name, Qt.ItemDataRole.UserRole + 1)
            root_item.appendRow(item_incomplete)

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
            raw_values = self.library_service.get_distinct_filter_values(field.name)
            # T-70: Strip Payload for UI display
            cleaned_values = []
            for v in raw_values:
                if v and isinstance(v, str) and " ::: " in v:
                    cleaned_values.append(v.split(" ::: ")[0].strip())
                else:
                    cleaned_values.append(v)
            return sorted(list(set(cleaned_values))) # Unique and sorted
        except Exception:
            return []

    # --- INTERACTION LOGIC ---

    def _on_tree_clicked(self, index) -> None:
        item = self.tree_model.itemFromIndex(index)
        if not item: return

        is_branch = item.data(Qt.ItemDataRole.AccessibleTextRole) == "branch"

        # IMPORTANT: Click handling (The Switchboard)
        # Even single clicks on the row (not just the checkbox) should toggle checkable items, BUT:
        # If it's a BRANCH, users expect expansion on click, not check toggling (unless on the box).
        # Since we can't easily detect "click on box" vs "click on text" here without QMouseEvent...
        # We will prioritize EXPANSION for branches.
        
        if is_branch:
             self.tree_view.user_interaction = True
             try:
                 if self.tree_view.isExpanded(index):
                     self.tree_view.collapse(index)
                 else:
                     self.tree_view.expand(index)
             finally:
                 self.tree_view.user_interaction = False
        elif item.isCheckable():
            new_state = Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            item.setCheckState(new_state)
        else:
            # Fallback for non-checkable non-branches (Roots?)
            self.tree_view.user_interaction = True
            try:
                if self.tree_view.isExpanded(index):
                    self.tree_view.collapse(index)
                else:
                    self.tree_view.expand(index)
            finally:
                self.tree_view.user_interaction = False

    def _on_tree_double_clicked(self, index) -> None:
        if not index.isValid(): return
        item = self.tree_model.itemFromIndex(index)
        if not item: return
        
        # Reset filter on root doubleclick if it's a root
        if item.parent() is None:
            self.reset_filter.emit()
        # T-70: "Turbo Click" Fix
        # If user clicks fast on a checkable item (leaf), Qt sees it as DoubleClick.
        # We process this as a second toggle to support rapid-fire filtering.
        elif item.isCheckable():
             new_state = Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
             item.setCheckState(new_state)

    def _on_item_changed(self, item):
        if self._block_signals: return
        
        field_name = item.data(Qt.ItemDataRole.UserRole + 1)
        val = item.data(Qt.ItemDataRole.UserRole)
        is_branch = item.data(Qt.ItemDataRole.AccessibleTextRole) == "branch"
        
        is_checked = item.checkState() == Qt.CheckState.Checked
        
        # Branch Logic: Toggle children
        if is_branch:
            self._block_signals = True
            try:
                for i in range(item.rowCount()):
                    child = item.child(i)
                    if child.isCheckable():
                        child.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            finally:
                self._block_signals = False
            # Branches themselves don't usually carry filter values, 
            # OR they do if they represent a Group?
            # In our case, branches are categorical containers (Groups, People), 
            # they don't have a value to filter by in _active_filters.
            # So we don't add them to _active_filters directly.
            # But the recursive update of children will trigger _on_item_changed for THEM.
            # Wait, self._block_signals = True prevents that.
            
            # We must manually update _active_filters for children
            if field_name:
                if field_name not in self._active_filters: self._active_filters[field_name] = set()
                for i in range(item.rowCount()):
                    child = item.child(i)
                    c_val = child.data(Qt.ItemDataRole.UserRole)
                    if c_val is not None:
                        if is_checked: self._active_filters[field_name].add(c_val)
                        else: self._active_filters[field_name].discard(c_val)

        # Leaf Logic
        elif field_name and val is not None:
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
                    elif val == "INCOMPLETE": display_val = "Incomplete"
                    elif val is False: display_val = "Not Done"
                    elif val is True: display_val = "Done"
                elif "active" in field_name.lower():
                    if val is False: display_val = "No"
                    elif val is True: display_val = "Yes"
                
                if field_name == 'all_contributors': header = 'Contributor'
                
                # T-83: Unified Tags Display Logic
                if field_name == 'tags' and ':' in display_val:
                    try:
                        cat, name = display_val.split(':', 1)
                        header = cat.strip()
                        display_val = name.strip()
                        # Get icon from ID3Registry
                        icon = ID3Registry.get_category_icon(header)
                        if icon: header = f"{icon} {header}"
                    except ValueError:
                        pass
                
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
                
        # Always visible (Persistent Footer)
        self.chip_bay_scroll.setVisible(True)
        
        # Add Placeholder if empty
        if total_chips == 0:
             from PyQt6.QtWidgets import QLabel
             lbl = QLabel("No Active Filters")
             lbl.setObjectName("ChipPlaceholder")
             # lbl.setStyleSheet("color: #666666; font-style: italic; margin-left: 4px;") # QSS: #ChipPlaceholder
             self.chip_layout.addWidget(lbl)

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
            self.btn_match_mode.setText("ANY")
            self.btn_match_mode.setChecked(False)
        else:
            self._filter_match_mode = "AND"
            self.btn_match_mode.setText("ALL")
            self.btn_match_mode.setChecked(True)
        self.filter_mode_changed.emit(self._filter_match_mode)

    # ===== Expansion State Persistence =====
    

    
    def restore_expansion_state(self):
        """Restore saved expansion state after populating tree."""
        if not self.settings_manager:
            return
        
        saved_state = self.settings_manager.get_filter_tree_expansion_state()
        if not saved_state:
            return
        
        # Build set of items that actually exist in current tree
        existing_items = {}  # {item_name: QModelIndex}
        for row in range(self.tree_model.rowCount()):
            root_item = self.tree_model.item(row)
            if root_item:
                self._collect_items(root_item, existing_items)
        
        # Block signals during restore to avoid triggering saves
        self.tree_view.blockSignals(True)
        try:
            # print(f"DEBUG: Restore State called. Saved: {len(saved_state)} items. Existing Tree Items: {len(existing_items)}")
            # Apply state only for items that exist
            for item_name, is_expanded in saved_state.items():
                if item_name in existing_items:
                    # print(f"DEBUG: Restoring {item_name} -> {is_expanded}")
                    self.tree_view.setExpanded(existing_items[item_name], is_expanded)
        finally:
            self.tree_view.blockSignals(False)
    
    def _collect_items(self, item, items_dict):
        """Recursively collect all parent/branch items in the tree."""
        # Include if it IS a branch (checkable or not) or a root (not checkable)
        is_branch = item.data(Qt.ItemDataRole.AccessibleTextRole) == "branch"
        is_root = item.data(Qt.ItemDataRole.AccessibleTextRole) == "root"
        
        if is_branch or is_root:
            key = self._get_item_key(item)
            
            # Save using the unique key
            index = self.tree_model.indexFromItem(item)
            items_dict[key] = index
            # print(f"DEBUG: Collected Item Key: {key}")
        
        for child_row in range(item.rowCount()):
            child = item.child(child_row)
            if child:
                self._collect_items(child, items_dict)

    def _on_tree_expanded(self, index):
        # Only save if user interaction is flagged
        if self._block_signals or not self.tree_view.user_interaction: return
        
        item = self.tree_model.itemFromIndex(index)
        if item:
            key = self._get_item_key(item)
            # print(f"DEBUG: Saving Expansion -> {key}: True")
            self._save_expansion_state(key, True)

    def _on_tree_collapsed(self, index):
        # Only save if user interaction is flagged
        if self._block_signals or not self.tree_view.user_interaction: return

        item = self.tree_model.itemFromIndex(index)
        if item:
            key = self._get_item_key(item)
            # print(f"DEBUG: Saving Collapse -> {key}: False")
            self._save_expansion_state(key, False)

    def _get_item_key(self, item) -> str:
        """Get unique key for expansion state. Uses item text."""
        return item.text()

    def _save_expansion_state(self, key, is_expanded):
        if not self.settings_manager: return
        state = self.settings_manager.get_filter_tree_expansion_state()
        state[key] = is_expanded
        self.settings_manager.set_filter_tree_expansion_state(state)
