from PyQt6.QtWidgets import QLineEdit, QPushButton
from PyQt6.QtCore import Qt, QEvent, QTimer, QSize
from PyQt6.QtGui import QIcon
from .base import GlowWidget
from .tooltip import ReviewTooltip

class GlowLineEdit(GlowWidget):
    """Workstation Input with Amber Halo on focus."""
    def __init__(self, parent=None):
        self.edit = QLineEdit()
        self.edit.setObjectName("GlowInput")
        super().__init__(self.edit, trigger_mode="focus", parent=parent)
        
        # Override Base: Inputs MUST have StrongFocus for tabbing between fields
        self.edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Preview capability
        self._preview_tip = None
        self._use_preview = False 
        self._inline_tool = None # The optional button

    def add_inline_tool(self, icon_normal: QIcon, callback, tooltip="", icon_hover: QIcon = None):
        """Add a clickable tool button inside the widget (Right side)."""
        if self._inline_tool: return # One tool max for now
        
        btn = QPushButton()
        btn.setIcon(icon_normal)
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        btn.setFixedWidth(24)
        
        # Style: Transparent (No Box)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        
        btn.clicked.connect(callback)
        
        # Manual Hover Logic for Icon Swapping
        if icon_hover:
            # We must keep references to prevent GC? No, local is fine if captured
            # But safer to store them on the button
            btn._icon_normal = icon_normal
            btn._icon_hover = icon_hover
            
            def on_enter(e):
                btn.setIcon(btn._icon_hover)
                
            def on_leave(e):
                btn.setIcon(btn._icon_normal)
                
            # Monkey Patch events (Simplest for dynamic widget)
            # Alternatively use eventFilter, but this is direct
            btn.enterEvent = on_enter
            btn.leaveEvent = on_leave
        
        # Add to layout (After the edit)
        # Note: GlowWidget uses QHBoxLayout. 
        self.layout.addWidget(btn, 0)
        self._inline_tool = btn
        
        # Auto-hide logic (Default: Show only when empty)
        self.edit.textChanged.connect(self._check_tool_visibility)
        # Check initial
        self._check_tool_visibility(self.edit.text())
        
    def _check_tool_visibility(self, text):
        if self._inline_tool:
            self._inline_tool.setVisible(text == "") 

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
    def setAlignment(self, a): self.edit.setAlignment(a)
    def setCursor(self, c): self.edit.setCursor(c)
    def clear(self): self.edit.clear()
    
    # Expose signals
    @property
    def textChanged(self): return self.edit.textChanged
    @property
    def returnPressed(self): return self.edit.returnPressed
