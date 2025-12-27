from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QHeaderView
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient

class WorkstationDelegate(QStyledItemDelegate):
    """
    Rhythmic Workstation Delegate for Gosling2.
    - Uniform Carbon Gradient for a high-end physical deck feel.
    - 1px 'Trough' Shadow for rhythmic row separation (No pairing).
    - Top-edge illumination on every row.
    - Pinned indicators and tactical bolding.
    """
    
    TYPE_COLORS = {
        1: QColor("#2979FF"), # Music (Electric Blue)
        2: QColor("#D81B60"), # Jingles (Magenta)
        3: QColor("#43A047"), # Ads (Green)
        4: QColor("#FFC66D"), # Speech (Warm Amber)
        5: QColor("#FFC66D"), # Speech
        6: QColor("#7E57C2")  # Streams (Purple)
    }

    def __init__(self, field_indices, table_view, parent=None):
        super().__init__(parent)
        self.field_indices = field_indices
        self.table_view = table_view

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Base Setup
        self.initStyleOption(option, index)
        model = index.model()
        row = index.row()
        rect = option.rect
        
        # Kill the OS Focus Rect (The Ghost)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        
        # Determine Visual Coordinate (Far Left Lock)
        is_far_left = False
        if self.table_view:
            first_col_logical = self.table_view.horizontalHeader().logicalIndex(0)
            is_far_left = (index.column() == first_col_logical)

        # Retrieve Staged (Dirty) Status
        is_dirty = False
        id_idx = self.field_indices.get('file_id', -1)
        if id_idx != -1 and hasattr(self.parent(), "_dirty_ids"):
            raw_id = model.index(row, id_idx).data(Qt.ItemDataRole.UserRole)
            try:
                sid = str(int(float(raw_id))) if raw_id is not None else ""
                is_dirty = sid in self.parent()._dirty_ids
            except: pass

        # Determine Row Hover State
        is_row_hovered = False
        if hasattr(self.parent(), "_hovered_row"):
            is_row_hovered = (row == self.parent()._hovered_row)

        # 2. DRAW BACKGROUND (Uniform Rhythmic Deck + Category Wash)
        type_idx = self.field_indices.get('type_id', -1)
        type_id = 1
        if type_idx != -1:
            val = model.index(row, type_idx).data(Qt.ItemDataRole.DisplayRole)
            try: type_id = int(val) 
            except: pass
        category_color = self.TYPE_COLORS.get(type_id, QColor("#121212"))

        grad = QLinearGradient(float(rect.left()), float(rect.top()), float(rect.left()), float(rect.bottom()))
        
        if option.state & QStyle.StateFlag.State_Selected:
            # DYNAMIC SIGNAL SELECTION - Matches the track's 'Soul' color
            # We fetch the color for this specific type instead of a generic orange focus
            type_id = index.model().data(index.model().index(index.row(), self.field_indices.get('type_id', 0)), Qt.ItemDataRole.UserRole)
            try:
                type_id = int(float(type_id)) if type_id is not None else 1
            except (ValueError, TypeError):
                type_id = 1
                
            sig_color = self.TYPE_COLORS.get(type_id, QColor("#FF8C00"))
            
            rail_pen = QPen(sig_color, 1)
            painter.setPen(rail_pen)
            painter.drawLine(rect.topLeft(), rect.topRight())
            painter.drawLine(rect.bottomLeft() + QPoint(0, -1), rect.bottomRight() + QPoint(0, -1))
            
            # Very subtle contrast boost (Matte)
            painter.fillRect(rect, QColor(sig_color.red(), sig_color.green(), sig_color.blue(), 15))
            
            
            
        elif is_dirty:
            grad.setColorAt(0, QColor("#221D0A"))
            grad.setColorAt(1, QColor("#1A1405"))
            painter.fillRect(rect, grad)
            painter.setPen(QColor(255, 165, 0, 40))
            painter.drawLine(rect.topLeft(), rect.topRight())
            
        elif is_row_hovered:
            grad.setColorAt(0, QColor("#222222"))
            grad.setColorAt(1, QColor("#1A1A1A"))
            painter.fillRect(rect, grad)
            painter.setPen(QColor(255, 255, 255, 12))
            painter.drawLine(rect.topLeft(), rect.topRight())
            
        else:
            # UNIFORM RYTHMIC DECK + AMBIENT CATEGORY WASH
            is_alt = option.features & QStyleOptionViewItem.ViewItemFeature.Alternate
            base_color = QColor("#121212") if not is_alt else QColor("#151515")
            
            # Subtle Ambient Tint (Very faint)
            tint = QColor(category_color)
            tint.setAlpha(12) 
            
            grad.setColorAt(0, base_color)
            grad.setColorAt(1, base_color.darker(110))
            painter.fillRect(rect, grad)
            painter.fillRect(rect, tint) # The Wash
            
            # Sublte consistent top-line glow on all rows
            painter.setPen(QColor(255, 255, 255, 5))
            painter.drawLine(rect.topLeft(), rect.topRight())

        # 3. THE "TROUGH" SHADOW (Physical Separation)
        painter.setPen(QColor("#050505"))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 4. DRAW INDICATORS (Pinned to Left Edge)
        if is_far_left:
            # THE GLASS CYLINDRICAL BLADE (7px Professional Profile)
            blade_rect = QRect(rect.left(), rect.top(), 7, rect.height() - 1)
            
            # Cylindrical Neon Gradient
            blade_grad = QLinearGradient(float(blade_rect.left()), 0, float(blade_rect.right()), 0)
            c_deep = QColor(category_color).darker(150)
            c_vibrant = QColor(category_color)
            
            blade_grad.setColorAt(0.0, c_deep)
            blade_grad.setColorAt(0.4, c_vibrant) # Core Light
            blade_grad.setColorAt(0.6, c_vibrant)
            blade_grad.setColorAt(1.0, c_deep)
            
            painter.fillRect(blade_rect, blade_grad)
            
            # Specular Glint Line (Surface Reflection)
            painter.setPen(QPen(QColor(255,255,255,40), 1))
            painter.drawLine(blade_rect.left() + 1, blade_rect.top(), blade_rect.left() + 1, blade_rect.bottom())
            
            # Staged Neon Strip (Orange Pulse) - Offset for the wider blade
            if is_dirty:
                dirty_rect = QRect(rect.left() + 7, rect.top(), 2, rect.height() - 1)
                painter.fillRect(dirty_rect, QColor("#FFA500"))

        # 5. CONTENT
        column_name = self._get_column_name_by_index(index.column())
        if column_name == "is_done":
            self._draw_status_badge(painter, option, index)
        else:
            text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            font = painter.font()
            
            # TYPOGRAPHIC HIERARCHY: Technical Data vs Content
            is_technical = column_name in ("bpm", "recording_year", "duration", "initial_key", "is_done")
            if is_technical:
                font.setFamily("Consolas")
                font.setWeight(QFont.Weight.Normal)
                font.setPointSize(9) # Precision data is slightly smaller
            else:
                font.setFamily("Bahnschrift Condensed")
                font.setWeight(QFont.Weight.Normal)

            if is_dirty:
                font.setWeight(QFont.Weight.DemiBold)
            
            painter.setFont(font)
            
            text_rect = rect.adjusted(18 if is_far_left else 10, 0, -4, 0)
            
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor("#FFFFFF")) # Bright white on selected
                font.setWeight(QFont.Weight.DemiBold)
            else:
                painter.setPen(QColor("#999999") if not is_dirty else QColor("#BBBBBB"))
                
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        painter.restore()

    def _draw_status_badge(self, painter, option, index):
        model = index.model()
        row = index.row()
        val = model.index(row, self.field_indices.get('is_done', -1)).data(Qt.ItemDataRole.DisplayRole)
        is_done = str(val).lower() in ('true', '1')
        
        badge_rect = option.rect.adjusted(10, 5, -10, -6) # Adjusted for trough
        bg_grad = QLinearGradient(float(badge_rect.left()), float(badge_rect.top()), float(badge_rect.left()), float(badge_rect.bottom()))
        if is_done:
            bg_grad.setColorAt(0, QColor("#2E7D32"))
            bg_grad.setColorAt(1, QColor("#1B5E20"))
        else:
            bg_grad.setColorAt(0, QColor("#3D3D3D"))
            bg_grad.setColorAt(1, QColor("#262626"))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_grad))
        painter.drawRoundedRect(badge_rect, 6, 6)
        
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "READY" if is_done else "AIR")

    def sizeHint(self, option, index):
        """Provide a dynamic size based on font height + vertical padding."""
        self.initStyleOption(option, index)
        # Bumping to 20 for 'Pro Deck' vertical breathing room
        h = option.fontMetrics.height() + 20 
        return QSize(option.rect.width(), h)

    def _get_column_name_by_index(self, index_val):
        for name, col in self.field_indices.items():
            if col == index_val:
                return name
        return ""
