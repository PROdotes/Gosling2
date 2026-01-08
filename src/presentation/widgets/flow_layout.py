from PyQt6.QtWidgets import QLayout, QStyle
from PyQt6.QtCore import Qt, QPoint, QRect, QSize

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
        self.invalidate()

    def insertItem(self, index, item):
        self._items.insert(index, item)
        self.invalidate()

    def insertWidget(self, index, widget):
        from PyQt6.QtWidgets import QWidgetItem
        self.insertItem(index, QWidgetItem(widget))

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
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
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
            widget = item.widget()
            # T-70 Fix: Use isHidden() instead of not isVisible()
            # isVisible() returns False if any parent is hidden, which breaks initial layout 
            # when the side panel is hidden at startup. isHidden() only cares if the 
            # widget itself was explicitly hidden.
            if widget and widget.isHidden():
                continue

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
