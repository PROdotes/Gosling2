from PyQt6.QtWidgets import QComboBox, QFrame, QGraphicsBlurEffect, QHBoxLayout
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from .base import GlowWidget

class GlowComboBox(GlowWidget):
    """
    Editable ComboBox with focus glow effect.
    Uses a hybrid approach: Base logic from GlowWidget but specialized for ComboBox.
    """
    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        self.combo = QComboBox()
        self.combo.setEditable(True)
        super().__init__(self.combo, trigger_mode="focus", parent=parent)
        
        # Forward signals
        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        self.combo.currentTextChanged.connect(self.currentTextChanged.emit)
    
    def eventFilter(self, obj, event):
        if obj is self.combo:
            if event.type() == QEvent.Type.FocusIn:
                self._show_glow()
                return super().eventFilter(obj, event)
            elif event.type() == QEvent.Type.FocusOut:
                # Don't hide glow if dropdown popup is open
                if not self.combo.view().isVisible():
                    self._hide_glow()
                # Return standard processing but SKIP base class hiding logic
                # The base class GlowWidget would blindly hide it on FocusOut.
                return False 
        return super().eventFilter(obj, event)
    
    def _show_glow(self):
        # Position glow behind combo
        self.glow_frame.setGeometry(self.combo.geometry())
        self.glow_frame.show()
        self.glow_frame.lower()
        self.combo.raise_()
        
        # Sticky Glow: Force QSS to keep the border "active"
        self.combo.setProperty("glowing", True)
        self.combo.style().unpolish(self.combo)
        self.combo.style().polish(self.combo)
    
    def _hide_glow(self):
        self.glow_frame.hide()
        
        # Remove Sticky Glow
        self.combo.setProperty("glowing", False)
        self.combo.style().unpolish(self.combo)
        self.combo.style().polish(self.combo)
    
    # Proxy methods for QComboBox API
    def setInsertPolicy(self, p): self.combo.setInsertPolicy(p)
    def completer(self): return self.combo.completer()
    def setObjectName(self, n): 
        super().setObjectName(n)
        self.combo.setObjectName(n)
    def addItem(self, text, data=None): self.combo.addItem(text, data)
    def addItems(self, items): self.combo.addItems(items)
    def clear(self): self.combo.clear()
    def count(self): return self.combo.count()
    def currentIndex(self): return self.combo.currentIndex()
    def currentText(self): return self.combo.currentText()
    def currentData(self, role=Qt.ItemDataRole.UserRole): return self.combo.currentData(role)
    def setCurrentIndex(self, i): self.combo.setCurrentIndex(i)
    def setCurrentText(self, t): self.combo.setCurrentText(t)
    def findData(self, data): return self.combo.findData(data)
    def findText(self, text): return self.combo.findText(text)
    def itemData(self, i, role=Qt.ItemDataRole.UserRole): return self.combo.itemData(i, role)
    def setItemData(self, i, data, role=Qt.ItemDataRole.UserRole): self.combo.setItemData(i, data, role)
    def blockSignals(self, b): return self.combo.blockSignals(b)
    def setFocus(self): self.combo.setFocus()
    def setEnabled(self, e): self.combo.setEnabled(e)
    def setEditable(self, e): self.combo.setEditable(e)
    def itemText(self, i): return self.combo.itemText(i)
    def clearEditText(self): self.combo.clearEditText()
    def lineEdit(self): return self.combo.lineEdit()
