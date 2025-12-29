"""
GlowFactory - Unified workstation halo effects for various widgets.
Supports 'focus' triggers (for inputs) and 'hover' triggers (for buttons).
"""
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QFrame, QGraphicsBlurEffect, QHBoxLayout, QLabel, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, pyqtProperty


class GlowWidget(QWidget):
    """
    Generic wrapper that applies a blurred amber halo to a child widget.
    trigger_mode: "focus" or "hover"
    """
    def __init__(self, child_widget, trigger_mode="focus", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Balanced margin for the halo
        # 5px is the sweet spot: exactly enough for 4px blur without clipping,
        # and lets the 26px buttons fit into the 36px Title Bar.
        self.glow_margin = 5
        self.trigger_mode = trigger_mode
        self.child = child_widget
        self.glow_color = "#FFC66D" # Default workstation amber
        
        # Main layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(self.glow_margin, self.glow_margin, self.glow_margin, self.glow_margin)
        self.layout.setSpacing(0)
        # Removed strict AlignCenter to allow children to expand based on their SizePolicy
        
        # 1. THE GLOW FRAME
        self.glow_frame = QFrame(self)
        self.glow_frame.setObjectName("GlowFocusFrame")
        self.glow_frame.setStyleSheet("""
            #GlowFocusFrame {
                background-color: {self.glow_color};
                border-radius: 10px;
            }
        """)
        
        self.glow_blur = QGraphicsBlurEffect()
        self.glow_blur.setBlurRadius(4) # Toned down to 4 as per final preference
        self.glow_frame.setGraphicsEffect(self.glow_blur)
        self.glow_frame.hide()
        
        # Consistent radius for the glow
        self.glow_radius = 8
        self._update_glow_style()
        
        # 2. THE CHILD
        self.layout.addWidget(self.child)
        self.child.installEventFilter(self)
        
        # Ensure glow is behind
        self.glow_frame.lower()

    def _update_glow_style(self):
        self.glow_frame.setStyleSheet(f"""
            #GlowFocusFrame {{
                background-color: {self.glow_color};
                border-radius: {self.glow_radius}px;
            }}
        """)

    def setGlowRadius(self, r):
        self.glow_radius = r
        self._update_glow_style()

    def setGlowColor(self, color):
        """Dynamic color support (e.g. blue for Music, red for System)"""
        self.glow_color = color
        self._update_glow_style()

    @pyqtProperty(str)
    def glowColor(self): return self.glow_color
    @glowColor.setter
    def glowColor(self, c): self.setGlowColor(c)

    @pyqtProperty(int)
    def glowRadius(self): return self.glow_radius
    @glowRadius.setter
    def glowRadius(self, r): self.setGlowRadius(r)

    def eventFilter(self, obj, event):
        if obj is self.child:
            if self.trigger_mode == "focus":
                if event.type() == QEvent.Type.FocusIn:
                    self._show_glow()
                elif event.type() == QEvent.Type.FocusOut:
                    self._hide_glow()
            elif self.trigger_mode == "hover":
                # ONLY show glow if the button is actually active/enabled
                if not self.child.isEnabled():
                    return super().eventFilter(obj, event)

                # Only hide if NOT checked (Underlight Logic)
                is_checked = getattr(self.child, "isChecked", lambda: False)()
                
                if event.type() == QEvent.Type.Enter:
                    self._show_glow()
                elif event.type() == QEvent.Type.Leave:
                    if not is_checked:
                        self._hide_glow()
        return super().eventFilter(obj, event)

    def _show_glow(self):
        self.glow_frame.show()
        self.glow_frame.raise_()
        self.child.raise_()
        
    def _hide_glow(self):
        self.glow_frame.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.glow_frame.setGeometry(self.child.geometry())

    def blockSignals(self, b):
        """Recursively block signals on child to prevent leaks (Fixes SidePanel ghost edits)."""
        self.child.blockSignals(b)
        return super().blockSignals(b)


class GlowLineEdit(GlowWidget):
    """Workstation Input with Amber Halo on focus."""
    def __init__(self, parent=None):
        self.edit = QLineEdit()
        self.edit.setObjectName("GlowInput")
        super().__init__(self.edit, trigger_mode="focus", parent=parent)
        
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


class GlowButton(GlowWidget):
    """
    Workstation Button with Amber Halo on hover.
    Supports 'Backlit Text' system: Stacked labels in a centered grid.
    """
    clicked = pyqtSignal()
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", parent=None):
        self.btn = QPushButton()
        # Ensure the native button doesn't render its own text
        self.btn.setText("") 
        
        super().__init__(self.btn, trigger_mode="hover", parent=parent)
        policy = self.btn.sizePolicy()
        self.setSizePolicy(policy.horizontalPolicy(), policy.verticalPolicy())
        
        # Backlit Text System (Stacked Labels)
        # Use a Grid Layout to force perfect, unit-synced stacking
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
        
        # Stack them in the same grid cell
        self.btn_grid.addWidget(self.lbl_glow, 0, 0)
        self.btn_grid.addWidget(self.lbl_main, 0, 0)
        
        self._update_text_styles()
        
        # Connections
        self.btn.clicked.connect(self.clicked.emit)
        self.btn.toggled.connect(self.toggled.emit)
        # Sync color state on check changes for toggle buttons
        self.btn.toggled.connect(self._on_toggled)

    def changeEvent(self, event):
        """Auto-update styles when enabled state changes (e.g. via parent)."""
        if event.type() == QEvent.Type.EnabledChange:
            self._update_text_styles()
        super().changeEvent(event)

    def showEvent(self, event):
        """Sync initial state on first show (handles startup states with blocked signals)."""
        super().showEvent(event)
        self._on_toggled(self.btn.isChecked())

    def _on_toggled(self, checked):
        if checked:
            self._show_glow()
            self.lbl_glow.show()
        else:
            # Only hide if mouse isn't currently hovering
            if not self.btn.underMouse():
                self._hide_glow()
                self.lbl_glow.hide()
        self._update_text_styles()

    def _update_text_styles(self):
        """Sync label colors with the glow color logic"""
        is_checked = self.btn.isChecked()
        is_hovered = self.btn.underMouse()
        is_enabled = self.btn.isEnabled()
        
        # 1. Main Text Color
        if not is_enabled:
            # Dead State: Ghosted Gray
            color = "#444444"
        elif is_checked:
            # Active/Locked: Amber (or Signature Color)
            color = self.glow_color
        elif is_hovered:
            # Hover: Sharp White (tactile hint)
            color = "#FFFFFF"
        else:
            # Idle: Muted Gray
            color = "#DDDDDD"
            
        self.lbl_main.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.lbl_glow.setStyleSheet(f"color: {self.glow_color}; background: transparent; font-weight: bold;")
        
        # 2. Text Glow (Bleed) visibility
        # ONLY show text glow if checked
        if is_checked:
            self.lbl_glow.show()
        else:
            self.lbl_glow.hide()

    def _show_glow(self):
        super()._show_glow()
        # Z-ORDER FIX
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
        """Update the backlit labels and keep native text empty to prevent ghosting."""
        self.lbl_glow.setText(text)
        self.lbl_main.setText(text)
        self.btn.setText("") # Ensure native text is never shown
        self._update_text_styles() # Refresh color state immediately

    def setFont(self, f): 
        self.btn.setFont(f)
        self.lbl_main.setFont(f)
        self.lbl_glow.setFont(f)
    def setVisible(self, v):
        super().setVisible(v)
        self.btn.setVisible(v)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Layout handles the grid stacking automatically
        pass
    # Proxy methods
    def isChecked(self): return self.btn.isChecked()
    def isCheckable(self): return self.btn.isCheckable()
    def isEnabled(self): return self.btn.isEnabled()
    def isVisible(self): return self.btn.isVisible()
    def text(self): return self.lbl_main.text()
    def setCheckable(self, c): self.btn.setCheckable(c)
    def setChecked(self, c): self.btn.setChecked(c)
    def setIcon(self, i): 
        self.btn.setIcon(i)
        # Icons don't work with backlit text currently, so we hide main label if icon set?
        # For now, just fix the proxy issue.
    def setIconSize(self, s): self.btn.setIconSize(s)
    def setToolTip(self, t): self.btn.setToolTip(t)
    def setObjectName(self, n):
        super().setObjectName(n)
        self.btn.setObjectName(n)
        
    def setProperty(self, n, v):
        super().setProperty(n, v)
        self.btn.setProperty(n, v)
        # Force a style refresh if the property might affect QSS
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
        # Support both (h, v) and (QSizePolicy)
        if len(args) == 1:
            super().setSizePolicy(args[0])
            self.btn.setSizePolicy(args[0])
        elif len(args) == 2:
            super().setSizePolicy(args[0], args[1])
            self.btn.setSizePolicy(args[0], args[1])

    def setEnabled(self, e): 
        self.btn.setEnabled(e)
        self._update_text_styles()
        
    def setCursor(self, c): self.btn.setCursor(c)
    def setFocusPolicy(self, p): self.btn.setFocusPolicy(p)
