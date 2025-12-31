from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt, QEvent, QTimer
from .base import GlowWidget
from .tooltip import ReviewTooltip

class GlowLineEdit(GlowWidget):
    """Workstation Input with Amber Halo on focus."""
    def __init__(self, parent=None):
        self.edit = QLineEdit()
        self.edit.setObjectName("GlowInput")
        super().__init__(self.edit, trigger_mode="focus", parent=parent)
        
        # Preview capability
        self._preview_tip = None
        self._use_preview = False 

    def enable_overlay(self):
        """Turn on the Passive Preview mode."""
        self._use_preview = True
        self.edit.textChanged.connect(self._update_preview)
        self.edit.cursorPositionChanged.connect(lambda old, new: self._update_preview())
        
    def _update_preview(self, force_show=False):
        if self._preview_tip:
             if force_show or self._preview_tip.isVisible():
                 self._preview_tip.update_with_cursor(self.edit)

    def eventFilter(self, obj, event):
        if self._use_preview and obj is self.edit:
            if event.type() == QEvent.Type.FocusIn:
                if not self._preview_tip:
                    self._preview_tip = ReviewTooltip(self.window())
                QTimer.singleShot(50, lambda: self._update_preview(force_show=True))
            elif event.type() == QEvent.Type.FocusOut:
                if self._preview_tip:
                    self._preview_tip.hide()
        return super().eventFilter(obj, event)

    # Proxy methods for direct access
    def text(self): return self.edit.text()
    def setText(self, t): self.edit.setText(t)
    def setPlaceholderText(self, t): self.edit.setPlaceholderText(t)
    def setReadOnly(self, r): self.edit.setReadOnly(r)
    def setEnabled(self, e): self.edit.setEnabled(e)
    def setValidator(self, v): self.edit.setValidator(v)
    def setObjectName(self, n): self.edit.setObjectName(n)
    def setProperty(self, n, v): 
        self.edit.setProperty(n, v)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)    
    def setFocusPolicy(self, p): self.edit.setFocusPolicy(p)
    def clear(self): self.edit.clear()
    
    # Expose signals
    @property
    def textChanged(self): return self.edit.textChanged
    @property
    def returnPressed(self): return self.edit.returnPressed
