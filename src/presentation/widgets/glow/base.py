from PyQt6.QtWidgets import QWidget, QFrame, QGraphicsBlurEffect, QHBoxLayout
from PyQt6.QtCore import Qt, QEvent, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen

class GlowOutline(QFrame):
    """Custom painter to ensure smooth, anti-aliased chassis rims."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.color = QColor("#FFC66D")
        self.radius = 8
        self.radius_css = ""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw the "Satin Rim" - darkened for depth
        border_color = self.color.darker(180)
        # T-93: Optimization - Use a slightly thicker pen for a more physical feel
        painter.setPen(QPen(border_color, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Calculate rect from fixed radius or CSS parts
        # Since we use setGeometry(match_child), we use our own rect
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, self.radius, self.radius)

class GlowWidget(QWidget):
    """
    Generic wrapper that applies a blurred amber halo to a child widget.
    trigger_mode: "focus" or "hover"
    """
    def __init__(self, child_widget, trigger_mode="focus", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Balanced margin for the halo
        self._glow_margins = (5, 5, 5, 5)
        self.trigger_mode = trigger_mode
        self.child = child_widget
        self.glow_color = "#FFC66D" # Default workstation amber
        
        # Main layout
        self.layout = QHBoxLayout(self)
        l, t, r, b = self._glow_margins
        self.layout.setContentsMargins(l, t, r, b)
        self.layout.setSpacing(0)
        
        # 1. THE GLOW FRAME (Halo)
        self.glow_frame = QFrame(self)
        self.glow_frame.setObjectName("GlowFocusFrame")
        
        self.glow_blur = QGraphicsBlurEffect()
        self.glow_blur.setBlurRadius(4) 
        self.glow_frame.setGraphicsEffect(self.glow_blur)
        self.glow_frame.hide()

        # 1b. THE OUTLINE OVERLAY (The 'Chassis' edge) - High Fidelity Painter
        self.outline_frame = GlowOutline(self)
        self.outline_frame.hide()
        
        # Consistent radius
        self.glow_radius = 8
        self._update_glow_style()
        
        # 2. THE CHILD
        self.layout.addWidget(child_widget, 1)
        self.child.installEventFilter(self)
        
        # Default behavior: Mouse clicks work, but Tab respects standard flow
        self.child.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        # Layering: Glow behind, Outline over
        self.glow_frame.lower()

    def _update_glow_style(self):
        radius_part = getattr(self, "_custom_radius_css", None)
        if not radius_part:
            radius_part = f"border-radius: {self.glow_radius}px;"
            
        self.glow_frame.setStyleSheet(f"""
            #GlowFocusFrame {{
                background-color: {self.glow_color};
                {radius_part}
            }}
        """)
        
        # T-93: Pre-render Cache Invalidation
        # Forces QGraphicsBlurEffect to discard its internal cache and redraw with the new color.
        # This fixes the "old color persists" issue reported during selection changes.
        if hasattr(self, "glow_blur"):
            self.glow_blur.setEnabled(False)
            self.glow_blur.setEnabled(True)
        
        # Sync the High-Fidelity Outline
        if hasattr(self, "outline_frame"):
            self.outline_frame.color = QColor(self.glow_color)
            self.outline_frame.radius = self.glow_radius
            self.outline_frame.update()

    def setGlowShape(self, css):
        """Allow passing complex border-radius strings."""
        self._custom_radius_css = css
        
        # T-93: Try to extract radius for the painter
        if "border-radius:" in css:
            try:
                # Basic parser for "border-radius: 10px;"
                val = css.split("border-radius:")[1].split("px")[0].strip()
                self.glow_radius = int(val)
            except:
                pass

        self._update_glow_style()

    def setGlowRadius(self, r):
        self.glow_radius = r
        self._update_glow_style()

    def setGlowColor(self, color):
        """Dynamic color support. Both Halo and Outline follow this color."""
        self.glow_color = color
        self._update_glow_style()

    def setGlowBlur(self, b):
        self.glow_blur.setBlurRadius(b)

    def setGlowMargins(self, left, top, right, bottom):
        self._glow_margins = (left, top, right, bottom)
        self.layout.setContentsMargins(left, top, right, bottom)
        if hasattr(self, "child") and self.child:
            self.updateGeometry()

    def setGlowMargin(self, m):
        self.setGlowMargins(m, m, m, m)

    @pyqtProperty(int)
    def glowBlur(self): return int(self.glow_blur.blurRadius())
    @glowBlur.setter
    def glowBlur(self, b): self.setGlowBlur(b)

    @pyqtProperty(int)
    def glowMargin(self): return self._glow_margins[0] # Return left margin as approximation
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

    def setObjectName(self, name):
        """
        Proper Decorator Pattern: 
        1. The wrapper (GlowWidget) gets 'name_Glow' ID for themeing the halo.
        2. The child (wrapped widget) gets 'name' ID for core styling.
        This prevents QSS properties (like icons/sizes) from crushing the wrapper.
        """
        super().setObjectName(name + "_Glow")
        if hasattr(self, "child") and self.child:
            self.child.setObjectName(name)

    def _show_glow(self):
        self.glow_frame.show()
        self.outline_frame.show()
        
        self.glow_frame.lower()
        self.child.raise_()
        self.outline_frame.raise_()
        
    def _hide_glow(self):
        self.glow_frame.hide()
        self.outline_frame.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_glow_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        # Defer geometry sync to after layout settles
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._sync_glow_geometry)

    def _sync_glow_geometry(self):
        """Sync both glow and outline frames to child widget geometry."""
        if hasattr(self, "child") and self.child:
            geom = self.child.geometry()
            self.glow_frame.setGeometry(geom)
            self.outline_frame.setGeometry(geom)

    def blockSignals(self, b):
        if hasattr(self, "child"):
            self.child.blockSignals(b)
        return super().blockSignals(b)
