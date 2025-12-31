from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer

class ReviewTooltip(QLabel):
    """Passive dropdown preview for long fields."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.WindowDoesNotAcceptFocus) 
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #0c0c0c;
                color: #C0C0C0;
                border: 1px solid #FFC66D;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
        """)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.linkActivated.connect(self._on_link_clicked)
        self._current_indices = [] 
        self._target_edit = None

    def _on_link_clicked(self, link):
        if not self._target_edit or not link.startswith("idx_"):
            return
            
        try:
            idx = int(link.split("_")[1])
            if 0 <= idx < len(self._current_indices):
                start_pos = self._current_indices[idx]
                self._target_edit.setCursorPosition(len(self._target_edit.text()))
                QTimer.singleShot(10, lambda: self._finish_jump(start_pos))
        except:
            pass

    def _finish_jump(self, pos):
        if self._target_edit:
            self._target_edit.setCursorPosition(pos)
            self._target_edit.setFocus()

    def update_with_cursor(self, edit_widget):
        self._target_edit = edit_widget
        text = edit_widget.text()
        cursor_pos = edit_widget.cursorPosition()
        
        if not text:
            self.hide()
            return

        has_list = "," in text
        display_html = ""
        self._current_indices = []
        
        if has_list:
            parts = text.split(',')
            current_idx = 0
            active_part_index = -1
            
            for i, part in enumerate(parts):
                part_len = len(part)
                start_pos = current_idx
                end_pos = current_idx + part_len
                
                if start_pos <= cursor_pos <= end_pos + 1: 
                    active_part_index = i
                
                ws_len = len(part) - len(part.lstrip())
                click_target = start_pos + ws_len
                self._current_indices.append(click_target)
                current_idx += part_len + 1 
            
            if active_part_index == -1: active_part_index = len(parts)-1

            lines = []
            for i, part in enumerate(parts):
                clean_part = part.strip()
                style = "color: #999999; text-decoration: none;"
                if i == active_part_index:
                    style = "color: #FFC66D; font-weight: bold; text-decoration: none;"
                lines.append(f"<a href='idx_{i}' style='{style}'>{clean_part}</a>")
            
            display_html = "<br>".join(lines)
        else:
            display_html = text
            
        fm = edit_widget.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        visible_width = edit_widget.width() - 8 
        is_truncated = text_width > visible_width
        
        if not is_truncated and not has_list:
             self.hide()
             return
            
        base_geo = edit_widget.rect()
        global_pos = edit_widget.mapToGlobal(base_geo.bottomLeft())
        w = base_geo.width() 
        self.setFixedWidth(w)
        self.setText(display_html)
        self.adjustSize()
        self.move(global_pos.x(), global_pos.y() + 4)
        self.show()
