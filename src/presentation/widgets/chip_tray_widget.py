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
        layout.setContentsMargins(6, 0, 10, 0) # Increased right margin to 10 (was 2) to prevent clipping
        layout.setSpacing(2)
        
        display_text = self.label_text
        if self.is_primary and not self.is_mixed:
             display_text = f"★ {display_text}"
             
        self.lbl = QLabel(display_text)
        self.lbl.setObjectName("ChipLabel")
        
        if icon_char:
            self.icon_lbl = QLabel(icon_char)
            self.icon_lbl.setObjectName("ChipIcon")
            layout.addWidget(self.icon_lbl)
            
        self.lbl.setMinimumWidth(20)
        self.lbl.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.lbl)
        
        # 3. Remove Button
        if not self.is_mixed:
            self.btn_remove = QPushButton("\u00D7")
            self.btn_remove.setFixedSize(20, 20)
            self.btn_remove.setObjectName("ChipRemoveButton")
            self.btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Sub-styling for the X button
            self.btn_remove.setStyleSheet("""
                QPushButton#ChipRemoveButton {
                    background: transparent;
                    border: none;
                    color: #888;
                    font-size: 14pt;
                    font-weight: bold;
                    padding: 0;
                    margin: 0;
                }
                QPushButton#ChipRemoveButton:hover {
                    color: #FF5555;
                }
            """)
            self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.entity_id, self.label_text))
            layout.addWidget(self.btn_remove)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we clicked the remove button area (approximate)
            # Actually, standard layout handles this, but let's be safe.
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
        self.btn_add = GlowButton("+")
        self.btn_add.setParent(self.container)
        self.btn_add.setFixedSize(32, 28)
        self.btn_add.setToolTip(add_tooltip)
        self.btn_add.clicked.connect(self.add_requested.emit)
        
        if self.is_add_visible:
            self.btn_add.show()
            self.flow_layout.addWidget(self.btn_add)
        else:
            self.btn_add.hide()

    def add_chip(self, entity_id, label, icon_char="", is_mixed=False, is_inherited=False, tooltip="", move_add_button=True, zone="default", is_primary=False):
        """Add a new chip to the tray."""
        chip = Chip(entity_id, label, icon_char, is_mixed, is_primary=is_primary, parent=self.container)
        
        if zone:
            chip.setProperty("zone", zone)
            
        if is_inherited:
            chip.setProperty("state", "inherited")
            if hasattr(chip, 'btn_remove'):
                chip.btn_remove.hide() # Locked
            chip.lbl.setStyleSheet("color: #777; font-style: italic;") # Inline fallback
            if tooltip:
                chip.setToolTip(tooltip)
        
        chip.clicked.connect(self.chip_clicked.emit)
        chip.remove_requested.connect(self._on_remove_requested)
        chip.context_menu_requested.connect(self.chip_context_menu_requested.emit)
        
        # Insert before the add button (the last item)
        self.flow_layout.addWidget(chip)
        
        if move_add_button and self.is_add_visible:
            self._move_add_to_end()
            
        chip.show()
        # Refresh style for property change
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        
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
                    taken_item.widget().deleteLater()
            else:
                i += 1
        self.container.updateGeometry()
        self.flow_layout.activate()
        self.container.update()

    def _on_remove_requested(self, entity_id, label):
        if self.confirm_removal:
            msg = self.confirm_template.format(label=label)
            reply = QMessageBox.question(
                self, "Confirm Removal", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
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
