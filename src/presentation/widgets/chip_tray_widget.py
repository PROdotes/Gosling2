"""
ChipTrayWidget - Horizontal wrapping tray of interactive chips.
Generic and reusable for Artists, Albums, and Tags.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont
from .flow_layout import FlowLayout
from .glow_factory import GlowButton

class ElidingLabel(QLabel):
    """
    A QLabel that automatically elides text to fit within its width.
    """
    def __init__(self, text="", parent=None, mode=Qt.TextElideMode.ElideRight):
        super().__init__(text, parent)
        self.elide_mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def paintEvent(self, event):
        painter = tile = None
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self.text(), self.elide_mode, self.width())
        
        # Center vertically, align left (or follow alignment)
        # Using basic drawText for simplicity and speed
        rect = self.rect()
        painter.drawText(rect, self.alignment(), elided)

class Chip(QFrame):
    """
    A single interactive chip with an icon, label, and removal button.
    """
    clicked = pyqtSignal(int, str)
    remove_requested = pyqtSignal(int, str)
    context_menu_requested = pyqtSignal(int, str, object) # id, label, global_pos

    def __init__(self, entity_id, label, icon_char="", is_mixed=False, is_primary=False, parent=None):
        super().__init__(parent)
        self.entity_id = entity_id
        self.label_text = label
        self.is_mixed = is_mixed
        self.is_primary = is_primary
        
        # Use objectName starting with Chip_ to pick up QSS styles from theme.qss
        self.setObjectName(f"Chip_Entity") 
        if is_mixed:
            self.setProperty("state", "mixed")
        elif is_primary:
            self.setProperty("state", "primary")
        
        # New: Zone/Category property for color coding
        self.setProperty("zone", "default")
            
        self._init_ui(icon_char)

    def _init_ui(self, icon_char):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 4, 0) # Reduced right margin to 4px
        layout.setSpacing(2)
        
        display_text = self.label_text
        if self.is_primary and not self.is_mixed:
             display_text = f"★ {display_text}"
             
        self.lbl = ElidingLabel(display_text)
        self.lbl.setObjectName("ChipLabel")
        self.lbl.setToolTip(f"{display_text} (Ctrl+Click to remove)") # Always tooltip full text with hint
        
        # Remove artificial width limit so chips can expand
        # self.lbl.setMaximumWidth(140) 
        
        if icon_char:
            self.icon_lbl = QLabel(icon_char)
            self.icon_lbl.setObjectName("ChipIcon")
            layout.addWidget(self.icon_lbl)
            
        layout.addWidget(self.lbl)
        
        # 3. Remove Button -> REMOVED in favor of Ctrl+Click
        # (This keeps layout simple and prevents accidental deletions)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Click = Remove
                self.remove_requested.emit(self.entity_id, self.label_text)
            else:
                # Normal Click = Action/Expand
                self.clicked.emit(self.entity_id, self.label_text)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self.entity_id, self.label_text, event.globalPos())

class ChipTrayWidget(QWidget):
    """
    Wrapping tray of chips with an Add button.
    """
    chip_clicked = pyqtSignal(int, str)
    chip_remove_requested = pyqtSignal(int, str)
    chip_context_menu_requested = pyqtSignal(int, str, object)
    add_requested = pyqtSignal()

    def __init__(self, 
                 confirm_removal=True, 
                 confirm_template="Remove '{label}' from this song?",
                 add_tooltip="Add",
                 show_add=True,
                 parent=None):
        super().__init__(parent)
        self.confirm_removal = confirm_removal
        self.confirm_template = confirm_template
        self.is_add_visible = show_add
        
        self._init_ui(add_tooltip)

    def resizeEvent(self, event):
        """
        T-Overflow: Constrain chips to the available width to force elision.
        FlowLayout uses sizeHint() which is huge for long text. 
        We must enforce maximumWidth on the chips so setGeometry() clamps them.
        """
        super().resizeEvent(event)
        
        # Calculate max width for a single chip (container width - margins)
        # Margin 8 * 2 = 16. Buffer 20 for safety.
        max_w = self.width() - 20
        if max_w < 50: max_w = 50 # Minimum sanity
        
        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setMaximumWidth(max_w)
                
    def _init_ui(self, add_tooltip):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Container for the flow layout
        self.container = QWidget()
        self.container.setObjectName("ChipTrayContainer")
        
        # Use our extracted FlowLayout with comfortable margin (8px breathing room)
        self.flow_layout = FlowLayout(self.container, margin=8, hspacing=6, vspacing=6)
        self.main_layout.addWidget(self.container)
        
        # Add Button - Using GlowButton for the hardware "outset" look
        self.btn_add = GlowButton("")
        self.btn_add.setParent(self.container)
        self.btn_add.setObjectName("AddInlineButton")
        self.btn_add.setToolTip(add_tooltip)
        self.btn_add.setAutoDefault(False)
        self.btn_add.clicked.connect(self.add_requested.emit)
        
        if self.is_add_visible:
            self.btn_add.show()
            self.flow_layout.addWidget(self.btn_add)
        else:
            self.btn_add.hide()

    def add_chip(self, entity_id, label, icon_char="", is_mixed=False, is_inherited=False, tooltip="", move_add_button=True, zone="default", is_primary=False, index=-1):
        """Add a new chip to the tray."""
        chip = Chip(entity_id, label, icon_char, is_mixed, is_primary=is_primary, parent=self.container)
        
        if zone:
            chip.setProperty("zone", zone)
            
        if is_inherited:
            chip.setProperty("state", "inherited")
            if hasattr(chip, 'btn_remove'):
                chip.btn_remove.hide() # Locked
            # chip.lbl.setStyleSheet("color: #777; font-style: italic;") # Handled by QSS [state="inherited"]
            if tooltip:
                chip.setToolTip(tooltip)
        
        chip.clicked.connect(self.chip_clicked.emit)
        chip.remove_requested.connect(self._on_remove_requested)
        chip.context_menu_requested.connect(self.chip_context_menu_requested.emit)
        
        # Insert
        if index >= 0:
            self.flow_layout.insertWidget(index, chip)
        else:
            self.flow_layout.addWidget(chip)
        
        if move_add_button and self.is_add_visible:
            self._move_add_to_end()

    def get_insertion_index(self, new_label: str) -> int:
        """Calculate the alphabetical insertion index for a new chip."""
        new_label = new_label.lower()
        cnt = self.flow_layout.count()
        
        for i in range(cnt):
            item = self.flow_layout.itemAt(i)
            widget = item.widget()
            
            # If we hit the add button, we MUST insert here (pushing button to end)
            if widget == self.btn_add:
                return i
                
            # If we hit a chip that is "larger", insert here
            if isinstance(widget, Chip):
                if new_label < widget.label_text.lower():
                    return i
                    
        return cnt # Fallback (append)
            
        chip.show()
        # Refresh style for property change
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        
        # Initial constraint (in case we are already visible)
        current_max = self.width() - 20
        if current_max > 50:
            chip.setMaximumWidth(current_max)
        
        self.container.updateGeometry()
        self.flow_layout.activate()

    def _move_add_to_end(self):
        # Safely move btn_add to the end using the layout API
        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i)
            if item.widget() == self.btn_add:
                taken_item = self.flow_layout.takeAt(i)
                self.flow_layout.addItem(taken_item)
                break
        self.container.updateGeometry()
        self.flow_layout.activate()
        self.container.update()

    def remove_chip(self, entity_id):
        """Remove chip by ID."""
        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, Chip) and widget.entity_id == entity_id:
                taken_item = self.flow_layout.takeAt(i)
                if taken_item.widget():
                    taken_item.widget().hide() # Hide immediately to prevent ghosting
                    taken_item.widget().deleteLater()
                break
        self.container.updateGeometry()
        self.flow_layout.activate()
        self.container.update()

    def clear(self):
        """Remove all chips except the add button."""
        i = 0
        while i < self.flow_layout.count():
            item = self.flow_layout.itemAt(i)
            widget = item.widget()
            if widget != self.btn_add:
                taken_item = self.flow_layout.takeAt(i)
                if taken_item.widget():
                    taken_item.widget().hide() # Hide immediately to prevent ghosting
                    taken_item.widget().deleteLater()
            else:
                i += 1
        self.container.updateGeometry()
        self.flow_layout.activate()
        self.container.update()

    def _on_remove_requested(self, entity_id, label):
        # T-User: Removed confirmation prompt since Ctrl+Click is explicit enough
        # if self.confirm_removal:
        #     msg = self.confirm_template.format(label=label)
        #     reply = QMessageBox.question(
        #         self, "Confirm Removal", msg,
        #         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        #         QMessageBox.StandardButton.No
        #     )
        #     if reply != QMessageBox.StandardButton.Yes:
        #         return
        
        self.chip_remove_requested.emit(entity_id, label)

    def set_chips(self, items):
        """
        Bulk set chips. 
        items: List of (id, label, icon_char, is_mixed, is_inherited, tooltip, zone)
        Only the first 4 are required.
        """
        self.clear()
        for item in items:
            # Pad the tuple if it's short
            args = list(item)
            while len(args) < 8: args.append(None)
            
            # Don't move the add button until the end
            self.add_chip(args[0], args[1], args[2], args[3], args[4], args[5], move_add_button=False, zone=args[6], is_primary=args[7])
            
        # Ensure ADD button state is respected
        if self.is_add_visible:
            self.btn_add.show()
            self._move_add_to_end()
        else:
            self.btn_add.hide()
        self.container.updateGeometry()
        self.flow_layout.activate()

    def get_names(self) -> list[str]:
        """Return a simple list of names for all current chips."""
        names = []
        for i in range(self.flow_layout.count()):
            widget = self.flow_layout.itemAt(i).widget()
            if isinstance(widget, Chip):
                names.append(widget.label_text)
        return names

    def get_entity_id_by_name(self, name: str) -> int | None:
        """Find entity ID for a given label/name."""
        for i in range(self.flow_layout.count()):
            widget = self.flow_layout.itemAt(i).widget()
            if isinstance(widget, Chip) and widget.label_text == name:
                return widget.entity_id
        return None
