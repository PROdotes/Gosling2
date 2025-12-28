from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QScrollArea, QFrame, QPushButton, QSizePolicy, QLayout, QLayoutItem, QStyle, QStyledItemDelegate
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont, QPainter, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize, pyqtProperty
from typing import Any
from ...core import yellberus
from ...resources import constants

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
    """Tree view for filters with formal bridge properties."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._paletteAmber = QColor(constants.COLOR_AMBER)
        self._paletteMutedAmber = QColor(constants.COLOR_MUTED_AMBER)
        self._paletteMagenta = QColor(constants.COLOR_MAGENTA)
        self._paletteBlack = QColor(constants.COLOR_BLACK)
        self._paletteGray = QColor(constants.COLOR_GRAY)
        self._paletteWhite = QColor(constants.COLOR_WHITE)
        self._paletteVoid = QColor(constants.COLOR_VOID)

    @pyqtProperty(QColor)
    def paletteAmber(self): return self._paletteAmber
    @paletteAmber.setter
    def paletteAmber(self, c): self._paletteAmber = c

    @pyqtProperty(QColor)
    def paletteMutedAmber(self): return self._paletteMutedAmber
    @paletteMutedAmber.setter
    def paletteMutedAmber(self, c): self._paletteMutedAmber = c

    @pyqtProperty(QColor)
    def paletteMagenta(self): return self._paletteMagenta
    @paletteMagenta.setter
    def paletteMagenta(self, c): self._paletteMagenta = c

    @pyqtProperty(QColor)
    def paletteBlack(self): return self._paletteBlack
    @paletteBlack.setter
    def paletteBlack(self, c): self._paletteBlack = c

    @pyqtProperty(QColor)
    def paletteGray(self): return self._paletteGray
    @paletteGray.setter
    def paletteGray(self, c): self._paletteGray = c

    @pyqtProperty(QColor)
    def paletteWhite(self): return self._paletteWhite
    @paletteWhite.setter
    def paletteWhite(self, c): self._paletteWhite = c

    @pyqtProperty(QColor)
    def paletteVoid(self): return self._paletteVoid
    @paletteVoid.setter
    def paletteVoid(self, c): self._paletteVoid = c

class FilterTreeDelegate(QStyledItemDelegate):
    """Delegate for drawing hierarchical backgrounds using the Property Bridge."""

    def _get_prop(self, widget, name, fallback=constants.COLOR_GRAY):
        if hasattr(widget, name): return getattr(widget, name)
        return QColor(fallback)

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
        
        zone_to_prop = {
            "amber": "paletteAmber",
            "muted_amber": "paletteMutedAmber",
            "magenta": "paletteMagenta",
            "gray": "paletteGray"
        }
        prop_name = zone_to_prop.get(zone, "paletteAmber")
        sig_color = self._get_prop(option.widget, prop_name, constants.COLOR_AMBER)
            
        full_row_rect = QRect(0, option.rect.y(), option.widget.width(), option.rect.height())
        
        if hint == "root":
            painter.fillRect(full_row_rect, self._get_prop(option.widget, "paletteBlack", constants.COLOR_BLACK))
        elif hint == "branch":
            painter.fillRect(full_row_rect, self._get_prop(option.widget, "paletteVoid", constants.COLOR_VOID))
            
        strip_width = 4 if (option.state & QStyle.StateFlag.State_Selected) else 2
        painter.fillRect(0, option.rect.y(), strip_width, option.rect.height(), sig_color)
            
        if hint == "root":
            painter.setPen(self._get_prop(option.widget, "paletteVoid", constants.COLOR_VOID))
            painter.drawLine(full_row_rect.bottomLeft(), full_row_rect.bottomRight())

        painter.restore()
        
        root_x, branch_x, child_x = 30, 45, 60
        
        if hint == "root":
            painter.save()
            font = option.font
            font.setBold(True); font.setPointSize(11)
            painter.setFont(font)
            painter.setPen(self._get_prop(option.widget, "paletteWhite", constants.COLOR_WHITE))
            text_rect = option.rect.adjusted(root_x, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()
        elif hint == "branch":
            painter.save()
            painter.setPen(self._get_prop(option.widget, "paletteGray", constants.COLOR_GRAY))
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
                painter.setPen(QPen(self._get_prop(option.widget, "paletteVoid", constants.COLOR_VOID), 1))
                painter.drawEllipse(led_rect)
            painter.setPen(self._get_prop(option.widget, "paletteGray", constants.COLOR_GRAY))
            text_rect = option.rect.adjusted(child_x + 18, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
            painter.restore()

class FilterWidget(QWidget):
    """Widget for filtering the library using Yellberus registry."""
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
        self.tree_model = QStandardItemModel()
        self.tree_model.itemChanged.connect(self._on_item_changed)
        self.tree_view = FilterTree()
        self.tree_view.setObjectName("FilterTree")
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(0)
        self.tree_view.setItemDelegate(FilterTreeDelegate())
        layout.addWidget(self.tree_view)

    def populate(self):
        self._block_signals = True
        self.tree_model.clear()
        for field in yellberus.FIELDS:
            if not field.filterable: continue
            root = QStandardItem(field.ui_header)
            root.setData("root", Qt.ItemDataRole.AccessibleTextRole)
            root.setData(field.name, Qt.ItemDataRole.UserRole + 1)
            root.setEditable(False); root.setSelectable(False)
            self.tree_model.appendRow(root)
            values = self.library_service.get_distinct_filter_values(field.name)
            for val in values:
                if val is None or val == "": continue
                child = QStandardItem(str(val))
                child.setData(field.name, Qt.ItemDataRole.UserRole + 1)
                child.setData(val, Qt.ItemDataRole.UserRole)
                child.setCheckable(True)
                child.setEditable(False)
                root.appendRow(child)
        self.tree_view.expandAll()
        self._block_signals = False

    def _on_item_changed(self, item):
        if self._block_signals: return
        field_name = item.data(Qt.ItemDataRole.UserRole + 1)
        val = item.data(Qt.ItemDataRole.UserRole)
        if field_name not in self._active_filters: self._active_filters[field_name] = set()
        if item.checkState() == Qt.CheckState.Checked: self._active_filters[field_name].add(val)
        else: self._active_filters[field_name].discard(val)
        self.multicheck_filter_changed.emit(self._active_filters)
