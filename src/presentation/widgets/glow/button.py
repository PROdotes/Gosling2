from PyQt6.QtWidgets import QPushButton, QGridLayout, QLabel, QGraphicsBlurEffect
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from .base import GlowWidget

class GlowButton(GlowWidget):
    """
    Workstation Button with Amber Halo on hover.
    Supports 'Backlit Text' system: Stacked labels in a centered grid.
    """
    clicked = pyqtSignal()
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", parent=None):
        self.btn = QPushButton()
        self.btn.setText("") # Ensure native text is never shown
        
        super().__init__(self.btn, trigger_mode="hover", parent=parent)
        self.glow_blur.setBlurRadius(4) # Boost glow for buttons (opaque body blocks more light)
        policy = self.btn.sizePolicy()
        self.setSizePolicy(policy.horizontalPolicy(), policy.verticalPolicy())
        
        # Backlit Text System (Stacked Labels)
        self.btn_grid = QGridLayout(self.btn)
        self.btn_grid.setContentsMargins(0, 0, 0, 0)
        self.btn_grid.setSpacing(0)
        
        # 1. Text Glow (Behind)
        self.lbl_glow = QLabel(text, self.btn)
        self.lbl_glow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_glow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_glow_blur = QGraphicsBlurEffect()
        self.lbl_glow_blur.setBlurRadius(6)
        self.lbl_glow.setGraphicsEffect(self.lbl_glow_blur)
        self.lbl_glow.hide() 
        
        # 2. Main Text (Front)
        self.lbl_main = QLabel(text, self.btn)
        self.lbl_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_main.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.btn_grid.addWidget(self.lbl_glow, 0, 0)
        self.btn_grid.addWidget(self.lbl_main, 0, 0)
        
        self._update_text_styles()
        
        self.btn.clicked.connect(self.clicked.emit)
        self.btn.toggled.connect(self.toggled.emit)
        self.btn.toggled.connect(self._on_toggled)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self._update_text_styles()
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._on_toggled(self.btn.isChecked())

    def _on_toggled(self, checked):
        if checked:
            self._show_glow()
            self.lbl_glow.show()
        else:
            if not self.btn.underMouse():
                self._hide_glow()
                self.lbl_glow.hide()
        self._update_text_styles()

    def _update_text_styles(self):
        is_checked = self.btn.isChecked()
        is_hovered = self.btn.underMouse()
        is_enabled = self.btn.isEnabled()
        
        if not is_enabled:
            color = "#444444"
            border_col = "#444444"
        elif is_checked:
            color = self.glow_color
            border_col = self.glow_color
        elif is_hovered:
            color = "#FFFFFF"
            border_col = self.glow_color # Inherit button color on hover
        else:
            color = "#DDDDDD"
            border_col = "#000000"
            
        self.lbl_main.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.lbl_glow.setStyleSheet(f"color: {self.glow_color}; background: transparent; font-weight: bold;")
        
        # Dynamic Border with preserved rounded corners
        self.btn.setStyleSheet(f"border: 1px solid {border_col}; border-radius: 10px;")
        
        if is_checked:
            self.lbl_glow.show()
        else:
            self.lbl_glow.hide()

    def _show_glow(self):
        super()._show_glow()
        self.lbl_glow.raise_()
        self.lbl_main.raise_()
        self._update_text_styles()

    def _hide_glow(self):
        if not self.btn.isChecked():
            super()._hide_glow()
            self.lbl_glow.hide()
        self._update_text_styles()

    def setGlowColor(self, color):
        super().setGlowColor(color)
        self._update_text_styles()

    def setText(self, text):
        self.lbl_glow.setText(text)
        self.lbl_main.setText(text)
        self.btn.setText("")
        self._update_text_styles()

    def setFont(self, f): 
        self.btn.setFont(f)
        self.lbl_main.setFont(f)
        self.lbl_glow.setFont(f)
    def setVisible(self, v):
        super().setVisible(v)
        self.btn.setVisible(v)

    # Proxy methods
    def isChecked(self): return self.btn.isChecked()
    def isCheckable(self): return self.btn.isCheckable()
    def isEnabled(self): return self.btn.isEnabled()
    def isVisible(self): return self.btn.isVisible()
    def text(self): return self.lbl_main.text()
    def setCheckable(self, c): self.btn.setCheckable(c)
    def setChecked(self, c): self.btn.setChecked(c)
    def setIcon(self, i): self.btn.setIcon(i)
    def setIconSize(self, s): self.btn.setIconSize(s)
    def setToolTip(self, t): self.btn.setToolTip(t)
    def setObjectName(self, n):
        super().setObjectName(n)
        self.btn.setObjectName(n)
        
    def setProperty(self, n, v):
        super().setProperty(n, v)
        self.btn.setProperty(n, v)
        self.style().unpolish(self)
        self.style().polish(self)
        
    def setStyleSheet(self, s):
        super().setStyleSheet(s)
        self.btn.setStyleSheet(s)
    def setMinimumWidth(self, w): 
        self.btn.setMinimumWidth(w)
        super().setMinimumWidth(w + (self.glow_margin * 2))
    def setMinimumHeight(self, h):
        self.btn.setMinimumHeight(h)
        super().setMinimumHeight(h + (self.glow_margin * 2))
    def setMaximumWidth(self, w):
        self.btn.setMaximumWidth(w)
        super().setMaximumWidth(w + (self.glow_margin * 2))
    def setMaximumHeight(self, h):
        self.btn.setMaximumHeight(h)
        super().setMaximumHeight(h + (self.glow_margin * 2))
    def setFixedSize(self, w, h):
        self.btn.setFixedSize(w, h)
        super().setFixedSize(w + (self.glow_margin * 2), h + (self.glow_margin * 2))
    def setFixedWidth(self, w): 
        self.btn.setFixedWidth(w)
        super().setFixedWidth(w + (self.glow_margin * 2))
    def setFixedHeight(self, h): 
        self.btn.setFixedHeight(h)
        super().setFixedHeight(h + (self.glow_margin * 2))
    def setSizePolicy(self, *args):
        if len(args) == 1:
            super().setSizePolicy(args[0])
            self.btn.setSizePolicy(args[0])
        elif len(args) == 2:
            super().setSizePolicy(args[0], args[1])
            self.btn.setSizePolicy(args[0], args[1])
    def setEnabled(self, e): 
        self.btn.setEnabled(e)
        if not e:
            self._hide_glow()
        self._update_text_styles()
    def setCursor(self, c): self.btn.setCursor(c)
    def setFocusPolicy(self, p): self.btn.setFocusPolicy(p)
