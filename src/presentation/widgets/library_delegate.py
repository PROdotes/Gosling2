from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QHeaderView
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient
from ...resources import constants
from .glow.led import GlowLED


class WorkstationDelegate(QStyledItemDelegate):
    """
    Rhythmic Workstation Delegate for Gosling2.
    Reads colors from QPalette (QSS-controlled), falls back to constants.
    """
    
    def __init__(self, field_indices, table_view, parent=None):
        super().__init__(parent)
        self.field_indices = field_indices
        self.table_view = table_view
        
        # Semantic mapping to color constants (fallbacks)
        self._zone_colors = {
            1: constants.COLOR_AMBER,
            2: constants.COLOR_MAGENTA,
            3: constants.COLOR_MUTED_AMBER,
            4: constants.COLOR_GRAY,
            5: constants.COLOR_GRAY,
            6: constants.COLOR_GRAY
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Read colors from palette (QSS-controlled)
        palette = option.palette
        text_color = palette.color(palette.ColorRole.Text)
        base_color = palette.color(palette.ColorRole.Base)
        alt_color = palette.color(palette.ColorRole.AlternateBase)
        highlight_text = palette.color(palette.ColorRole.HighlightedText)
        
        # 1. Base Setup
        self.initStyleOption(option, index)
        model = index.model()
        row = index.row()
        rect = option.rect
        
        # Kill Focus & Active State visuals (prevents fragmented boxes)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        option.state &= ~QStyle.StateFlag.State_Active
        option.state &= ~QStyle.StateFlag.State_MouseOver
        
        # Determine Far Left Blade
        is_far_left = False
        if self.table_view:
            first_col_logical = self.table_view.horizontalHeader().logicalIndex(0)
            is_far_left = (index.column() == first_col_logical)

        # 2. COLOR DISPATCH (Category Zone)
        type_idx = self.field_indices.get('type_id', -1)
        type_id = 1
        if type_idx != -1:
            val = model.index(row, type_idx).data(Qt.ItemDataRole.DisplayRole)
            try: type_id = int(val) 
            except: pass
        
        category_color = QColor(self._zone_colors.get(type_id, constants.COLOR_AMBER))

        # 3. DIRTY STATE DETECTION
        id_col = self.field_indices.get('file_id', -1)
        item_id = -1
        if id_col != -1:
            idx_id = index.model().index(index.row(), id_col)
            val = index.model().data(idx_id, Qt.ItemDataRole.UserRole)
            try:
                if val is not None:
                    item_id = int(float(val))
            except (ValueError, TypeError):
                pass

        dirty_ids = getattr(self.parent(), '_dirty_ids', set())
        is_dirty = (item_id != -1 and (item_id in dirty_ids or str(item_id) in dirty_ids))

        # 4. BACKGROUND RENDERING
        if option.state & QStyle.StateFlag.State_Selected:
            # T-87: Disable AA for borders to prevent sub-pixel bleed into adjacent rows
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            
            # Fill the interior with a deep, neutral Onyx base (no colored bleed)
            painter.fillRect(rect.adjusted(0, 1, 0, -1), QColor("#0D0D0D"))
            
            # Draw Selection Border (Surgical Horizontal Etching)
            border_pen = QPen(category_color, 1)
            edge_color = QColor(category_color)
            edge_color.setAlpha(80) # Very fine, etched look (30% opacity)
            border_pen.setColor(edge_color)
            
            painter.setPen(border_pen)
            # Top edge: continuous across cells
            painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())
            # Bottom edge: floor line
            painter.drawLine(rect.left(), rect.bottom() - 1, rect.right(), rect.bottom() - 1)
            
            # Restore AA for text/badges
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        else:
            # Determine base background
            is_alt = option.features & QStyleOptionViewItem.ViewItemFeature.Alternate
            bg = alt_color if (is_alt and alt_color.isValid()) else base_color
            if not bg.isValid():
                bg = QColor(constants.COLOR_VOID if is_alt else constants.COLOR_BLACK)
            
            # 1. Base Fill
            painter.fillRect(rect, bg)
            
            # T-Feature: Highlight missing required fields during Incomplete/Validation workflows
            highlight_mode = getattr(self.parent(), '_show_incomplete', False)
            if highlight_mode:
                 text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
                 if not text.strip(): # Empty Check
                      col_name = self._get_column_name_by_index(index.column())
                      if col_name and col_name not in ('is_active'): # Skip technical cols
                           from ...core import yellberus
                           field = yellberus.get_field(col_name)
                           if field and field.required:
                                # Subtle Red Warning Tint
                                warn = QColor("#FF0000")
                                warn.setAlpha(25)
                                painter.fillRect(rect, warn)

            # 2. Row-Level Hover Handling
            # T-90: Use the delegate's parent (LibraryWidget) for state tracking
            hovered_row = getattr(self.parent(), '_hovered_row', -1)
            if row == hovered_row:
                # Ghostly Hover: A tactical lift (felt, not seen)
                hover_fill = QColor("#FFFFFF")
                hover_fill.setAlpha(18) 
                painter.fillRect(rect, hover_fill)
            else:
                # Subtle Category Tint (Ambient Glow)
                tint = QColor(category_color)
                tint.setAlpha(5) 
                painter.fillRect(rect, tint)

        # 5. PHYSICAL SEPARATION (Bottom Border)
        sep_color = base_color if base_color.isValid() else QColor(constants.COLOR_BLACK)
        painter.setPen(sep_color)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 6. [REMOVED] CYLINDRICAL BLADE (Unreliable with column reordering)
        
        # 7. CONTENT RENDERING
        column_name = self._get_column_name_by_index(index.column())
        
        # Determine Status for Pip (Only show on Title column)
        show_pip = False
        pip_color = QColor()
        
        if column_name == 'title':
            # Clean Title Logic (Pips moved to Status Deck T-92)
            pass
        
        if column_name == "is_active":
            self._draw_status_deck(painter, option, index, is_dirty)
        else:
            text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            # T-70: Strip "Secret Payload" (Identity Bubble search data) using separator
            if " ::: " in text:
                text = text.split(" ::: ")[0].strip()
            
            font = painter.font()
            if column_name in ("bpm", "recording_year", "duration", "initial_key"):
                font.setFamily("Consolas")
                font.setPointSize(9)
            else:
                font.setFamily("Bahnschrift Condensed")

            if is_dirty:
                font.setBold(True)
            
            painter.setFont(font)
            
            padding_left = 10
            text_rect = rect.adjusted(padding_left, 0, -4, 0)

            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor("#FFFFFF")) # Force crisp white on selection
            elif is_dirty:
                painter.setPen(QColor(constants.COLOR_AMBER))
            else:
                norm_text = text_color if text_color.isValid() else QColor("#BBBBBB")
                painter.setPen(norm_text)
                
            # Use AlignVCenter with the full cell rect for perfect centering
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        painter.restore()

    def _draw_status_deck(self, painter, option, index, is_dirty):
        """Render the T-92 Status Deck (Shape + Glow Logic)"""
        model = index.model()
        row = index.row()
        
        # 1. Determine Props
        path_idx = self.field_indices.get('path', -1)
        active_col = self.field_indices.get('is_active', -1)
        
        is_active = False
        if active_col != -1:
             val = model.index(row, active_col).data(Qt.ItemDataRole.UserRole)
             # Handle bool or string "1"/"True"
             is_active = str(val).lower() in ('true', '1')
             
        path_val = ""
        if path_idx != -1:
            path_val = str(model.index(row, path_idx).data(Qt.ItemDataRole.UserRole) or "")
            
        is_virtual = "|" in path_val
        is_wav = path_val.lower().endswith('.wav')
        
        # 2. Determine Shape
        shape = GlowLED.SHAPE_CIRCLE
        if is_wav:
            shape = GlowLED.SHAPE_TRIANGLE
        elif is_virtual:
            shape = GlowLED.SHAPE_SQUARE
            
        # 3. Determine Color (Priority: Dirty > Wav > Virtual > Standard)
        color = QColor(constants.COLOR_AMBER)
        if is_dirty:
            color = QColor(constants.COLOR_MAGENTA)
        elif is_wav:
            color = QColor(constants.COLOR_RED)
        elif is_virtual:
            color = QColor(constants.COLOR_CYAN)
            
        # 4. Draw
        GlowLED.draw_led(
            painter, 
            option.rect,
            color,
            is_active,
            size=10, 
            shape=shape
        )

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 48)

    def _get_column_name_by_index(self, index_val):
        for name, col in self.field_indices.items():
            if col == index_val:
                return name
        return ""
