from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt
from .base import GlowWidget

class GlowPlainTextEdit(GlowWidget):
    """Multi-line Workstation Input with Amber Halo on focus."""
    def __init__(self, parent=None):
        self.edit = QPlainTextEdit()
        self.edit.setObjectName("GlowInput")
        super().__init__(self.edit, trigger_mode="focus", parent=parent)
        
        # Inputs MUST have StrongFocus for tabbing
        self.edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # Proxy methods
    def toPlainText(self): return self.edit.toPlainText()
    def setPlaceholderText(self, t): self.edit.setPlaceholderText(t)
    def setReadOnly(self, r): self.edit.setReadOnly(r)
    def setEnabled(self, e): self.edit.setEnabled(e)
    def setObjectName(self, n): self.edit.setObjectName(n)
    def setProperty(self, n, v): 
        self.edit.setProperty(n, v)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)
    
    def clear(self): self.edit.clear()
    
    # Expose signals
    @property
    def textChanged(self): return self.edit.textChanged

    def setFocus(self, reason=Qt.FocusReason.OtherFocusReason):
        """Pass focus to the inner QPlainTextEdit."""
        self.edit.setFocus(reason)
