from PyQt6.QtWidgets import QPushButton, QGridLayout, QLabel, QGraphicsBlurEffect
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, pyqtProperty, QSize
from PyQt6.QtGui import QIcon
from .base import GlowWidget

class GlowButton(GlowWidget):
    """
    Workstation Button with Amber Halo on hover.
    Supports 'Backlit Text' system: Stacked labels in a centered grid.
    """
    clicked = pyqtSignal()
    toggled = pyqtSignal(bool)
    
    @pyqtProperty(QIcon)
    def icon(self): return self.btn.icon()
    @icon.setter
    def icon(self, arg): self.btn.setIcon(arg)
    
    def __init__(self, text="", parent=None):
        self.btn = QPushButton()
        self.btn.setText("") # Ensure native text is never shown
        
        super().__init__(self.btn, trigger_mode="hover", parent=parent)
        self._glow_margin = self.glowMargin
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
        
        self._radius_css = "border-radius: 10px;" # Default pill shape
        self._text_align = Qt.AlignmentFlag.AlignCenter
        self._font_weight = "bold"
        self._font_family = None # None = Inherit/Default
        self._font_size = None   # None = Inherit/Default
        
        self._update_text_styles()
        
        self.btn.clicked.connect(self.clicked.emit)
        self.btn.toggled.connect(self.toggled.emit)
        self.btn.toggled.connect(self._on_toggled)
        self._update_size()

    def _update_size(self):
        """Force the internal button to be wide enough for its labels."""
        # T-Fix: If fixed size is set, do NOT auto-resize based on text content
        if self.btn.minimumWidth() == self.btn.maximumWidth() and self.btn.minimumWidth() > 0:
            return

        self.lbl_main.adjustSize()
        hint = self.lbl_main.sizeHint()
        # 24px padding (12px per side) for the pill look
        self.btn.setMinimumWidth(hint.width() + 24)
        # Standard pill height
        self.btn.setMinimumHeight(32)
        self.updateGeometry()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self._update_text_styles()
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._on_toggled(self.btn.isChecked())

    def set_radius_style(self, css_string):
        """Override the default 10px border radius (e.g. for split buttons)."""
        self._radius_css = css_string
        self.setGlowShape(css_string)
        self._update_text_styles()

    def set_text_align(self, alignment):
        self._text_align = alignment
        self.lbl_main.setAlignment(alignment)
        self.lbl_glow.setAlignment(alignment)
        # Add padding if left aligned to match inputs
        if alignment & Qt.AlignmentFlag.AlignLeft:
            self.lbl_main.setIndent(8)
            self.lbl_glow.setIndent(8)
        else:
            self.lbl_main.setIndent(0)
            self.lbl_glow.setIndent(0)

    def set_font_weight(self, weight):
        """e.g. 'bold', 'normal', '100'"""
        self._font_weight = weight
        self._update_text_styles()
        
    def set_font_family(self, family):
        """e.g. 'Consolas'"""
        self._font_family = family
        self._update_text_styles()

    def set_font_size(self, size_pt):
        """e.g. 12"""
        self._font_size = size_pt
        self._update_text_styles()

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
            border_col = "#000000" # Black border for disabled state (recede)
        elif is_checked:
            color = self.glow_color
            border_col = self.glow_color
        elif is_hovered:
            color = "#FFFFFF"
            border_col = self.glow_color # Inherit button color on hover
        else:
            color = "#DDDDDD"
            border_col = "#000000"
            
        font_style = f"font-weight: {self._font_weight};"
        if self._font_family:
            font_style += f" font-family: {self._font_family};"
        if self._font_size:
            font_style += f" font-size: {self._font_size}pt;"
            
        self.lbl_main.setStyleSheet(f"color: {color}; background: transparent; {font_style}")
        self.lbl_glow.setStyleSheet(f"color: {self.glow_color}; background: transparent; {font_style}")
        
        # Dynamic Border with custom or default radius
        self.btn.setStyleSheet(f"border: 1px solid {border_col}; {self._radius_css}")
        
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
        # Disable glow if hidden, unchecked, OR disabled
        if not self.btn.isEnabled() or not self.btn.isChecked():
            super()._hide_glow()
            self.lbl_glow.hide()
        self._update_text_styles()

    def setGlowColor(self, color):
        super().setGlowColor(color)
        self._update_text_styles()

    # Proxy methods for Dialog behavior
    def setAutoDefault(self, auto):
        self.btn.setAutoDefault(auto)

    def setDefault(self, default):
        self.btn.setDefault(default)

    def setText(self, text):
        self.lbl_glow.setText(text)
        self.lbl_main.setText(text)
        self.btn.setToolTip(text) # Tooltip fallback if clipped?den
        self.btn.setText("") # Native text always hidden
        self._update_text_styles()
        self._update_size()

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
    def click(self): self.btn.click()
    def setCheckable(self, c): self.btn.setCheckable(c)
    def setChecked(self, c): self.btn.setChecked(c)
    def setIcon(self, i): self.btn.setIcon(i)
    def setIconSize(self, s): self.btn.setIconSize(s)
    def setToolTip(self, t): self.btn.setToolTip(t)
    def setDefault(self, d): self.btn.setDefault(d)
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
    def setGlowBlur(self, b):
        super().setGlowBlur(b)

    def setGlowMargin(self, m):
        self._glow_margin = m
        super().setGlowMargin(m)

    def setMinimumWidth(self, w): 
        self.btn.setMinimumWidth(w)
        super().setMinimumWidth(w + (self._glow_margin * 2))
    def setMinimumHeight(self, h):
        self.btn.setMinimumHeight(h)
        super().setMinimumHeight(h + (self._glow_margin * 2))
    def setMaximumWidth(self, w):
        self.btn.setMaximumWidth(w)
        super().setMaximumWidth(w + (self._glow_margin * 2))
    def setMaximumHeight(self, h):
        self.btn.setMaximumHeight(h)
        super().setMaximumHeight(h + (self._glow_margin * 2))
    def setFixedSize(self, w, h):
        self.btn.setFixedSize(w, h)
        super().setFixedSize(w + (self._glow_margin * 2), h + (self._glow_margin * 2))
    def setFixedWidth(self, w): 
        self.btn.setFixedWidth(w)
        super().setFixedWidth(w + (self._glow_margin * 2))
    def setFixedHeight(self, h): 
        self.btn.setFixedHeight(h)
        super().setFixedHeight(h + (self._glow_margin * 2))
    def setSizePolicy(self, *args):
        if len(args) == 1:
            super().setSizePolicy(args[0])
            self.btn.setSizePolicy(args[0])
        elif len(args) == 2:
            super().setSizePolicy(args[0], args[1])
            self.btn.setSizePolicy(args[0], args[1])
    def setEnabled(self, e): 
        super().setEnabled(e) # Essential for wrapper state
        self.btn.setEnabled(e)
        if not e:
            self._hide_glow()
        self._update_text_styles()
    def setCursor(self, c): self.btn.setCursor(c)
    def setFocusPolicy(self, p): self.btn.setFocusPolicy(p)
