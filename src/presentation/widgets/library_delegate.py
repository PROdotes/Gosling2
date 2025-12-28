from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QHeaderView
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient
from ...resources import constants

class WorkstationDelegate(QStyledItemDelegate):
    """
    Rhythmic Workstation Delegate for Gosling2.
    Reads dynamic palette values from the parent widget's properties (pushed from QSS).
    """
    
    def __init__(self, field_indices, table_view, parent=None):
        super().__init__(parent)
        self.field_indices = field_indices
        self.table_view = table_view
        
        # Semantic mapping to QSS property names
        self._zone_map = {
            1: "paletteAmber",
            2: "paletteMagenta",
            3: "paletteMutedAmber",
            4: "paletteGray",
            5: "paletteGray",
            6: "paletteGray"
        }

    def _get_qss_color(self, prop_name: str, fallback_hex: str) -> QColor:
        """Fetch color pushed by QSS 'qproperty-propName'"""
        color = self.table_view.property(prop_name)
        if isinstance(color, QColor):
            return color
        return QColor(fallback_hex)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Base Setup
        self.initStyleOption(option, index)
        model = index.model()
        row = index.row()
        rect = option.rect
        
        # Kill Focus Rect
        option.state &= ~QStyle.StateFlag.State_HasFocus
        
        # Determine Far Left Blade
        is_far_left = False
        if self.table_view:
            first_col_logical = self.table_view.horizontalHeader().logicalIndex(0)
            is_far_left = (index.column() == first_col_logical)

        # 2. COLOR DISPATCH (Read from QSS Bridge)
        type_idx = self.field_indices.get('type_id', -1)
        type_id = 1
        if type_idx != -1:
            val = model.index(row, type_idx).data(Qt.ItemDataRole.DisplayRole)
            try: type_id = int(val) 
            except: pass
        
        category_prop = self._zone_map.get(type_id, "paletteAmber")
        category_color = self._get_qss_color(category_prop, constants.COLOR_AMBER)

        # 3. BACKGROUND RENDERING
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(category_color, 1))
            painter.drawLine(rect.topLeft(), rect.topRight())
            painter.drawLine(rect.bottomLeft() + QPoint(0, -1), rect.bottomRight() + QPoint(0, -1))
            
            highlight_fill = QColor(category_color)
            highlight_fill.setAlpha(15)
            painter.fillRect(rect, highlight_fill)
        else:
            is_alt = option.features & QStyleOptionViewItem.ViewItemFeature.Alternate
            base_color = self._get_qss_color("paletteVoid" if is_alt else "paletteBlack", constants.COLOR_BLACK)
            painter.fillRect(rect, base_color)
            
            # Subtle Category Tint
            tint = QColor(category_color)
            tint.setAlpha(8) 
            painter.fillRect(rect, tint)

        # 4. PHYSICAL SEPARATION
        painter.setPen(self._get_qss_color("paletteBlack", constants.COLOR_BLACK))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 5. CYLINDRICAL BLADE (Far Left)
        if is_far_left:
            blade_rect = QRect(rect.left(), rect.top(), 7, rect.height() - 1)
            blade_grad = QLinearGradient(float(blade_rect.left()), 0, float(blade_rect.right()), 0)
            blade_grad.setColorAt(0.0, category_color.darker(150))
            blade_grad.setColorAt(0.4, category_color)
            blade_grad.setColorAt(0.6, category_color)
            blade_grad.setColorAt(1.0, category_color.darker(150))
            painter.fillRect(blade_rect, blade_grad)

        # 6. CONTENT
        column_name = self._get_column_name_by_index(index.column())
        if column_name == "is_done":
            self._draw_status_badge(painter, option, index, category_color)
        else:
            text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            font = painter.font()
            if column_name in ("bpm", "recording_year", "duration", "initial_key"):
                font.setFamily("Consolas")
                font.setPointSize(9)
            else:
                font.setFamily("Bahnschrift Condensed")

            painter.setFont(font)
            text_rect = rect.adjusted(18 if is_far_left else 10, 0, -4, 0)
            
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(self._get_qss_color("paletteWhite", constants.COLOR_WHITE))
            else:
                painter.setPen(self._get_qss_color("paletteGray", constants.COLOR_GRAY))
                
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        painter.restore()

    def _draw_status_badge(self, painter, option, index, category_color):
        model = index.model()
        row = index.row()
        val = model.index(row, self.field_indices.get('is_done', -1)).data(Qt.ItemDataRole.DisplayRole)
        is_done = str(val).lower() in ('true', '1')
        
        badge_rect = option.rect.adjusted(10, 5, -10, -6)
        
        if is_done:
            bg = self._get_qss_color("paletteMagenta", constants.COLOR_MAGENTA)
            txt = self._get_qss_color("paletteBlack", constants.COLOR_BLACK)
        else:
            bg = self._get_qss_color("paletteVoid", constants.COLOR_VOID)
            txt = self._get_qss_color("paletteGray", constants.COLOR_GRAY)
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(badge_rect, 4, 4)
        
        painter.setPen(txt)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "READY" if is_done else "AIR")

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 48)

    def _get_column_name_by_index(self, index_val):
        for name, col in self.field_indices.items():
            if col == index_val:
                return name
        return ""
