from PyQt6.QtWidgets import QWidget, QFrame, QGraphicsBlurEffect, QHBoxLayout
from PyQt6.QtCore import Qt, QEvent, pyqtProperty

class GlowWidget(QWidget):
    """
    Generic wrapper that applies a blurred amber halo to a child widget.
    trigger_mode: "focus" or "hover"
    """
    def __init__(self, child_widget, trigger_mode="focus", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Balanced margin for the halo
        self._glow_margin = 5
        self.trigger_mode = trigger_mode
        self.child = child_widget
        self.glow_color = "#FFC66D" # Default workstation amber
        
        # Main layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(self._glow_margin, self._glow_margin, self._glow_margin, self._glow_margin)
        self.layout.setSpacing(0)
        
        # 1. THE GLOW FRAME
        self.glow_frame = QFrame(self)
        self.glow_frame.setObjectName("GlowFocusFrame")
        
        self.glow_blur = QGraphicsBlurEffect()
        self.glow_blur.setBlurRadius(4) 
        self.glow_frame.setGraphicsEffect(self.glow_blur)
        self.glow_frame.hide()
        
        # Consistent radius for the glow
        self.glow_radius = 8
        self._update_glow_style()
        
        # 2. THE CHILD
        self.layout.addWidget(self.child, 1)
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

    def setGlowBlur(self, b):
        self.glow_blur.setBlurRadius(b)

    def setGlowMargin(self, m):
        self._glow_margin = m
        self.layout.setContentsMargins(m, m, m, m)
        # Update geometry if we have fixed sizes
        if self.child:
            self.updateGeometry()

    @pyqtProperty(int)
    def glowBlur(self): return int(self.glow_blur.blurRadius())
    @glowBlur.setter
    def glowBlur(self, b): self.setGlowBlur(b)

    @pyqtProperty(int)
    def glowMargin(self): return self._glow_margin
    @glowMargin.setter
    def glowMargin(self, m): self.setGlowMargin(m)

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
                if not self.child.isEnabled():
                    return super().eventFilter(obj, event)

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
        self.child.blockSignals(b)
        return super().blockSignals(b)
