from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtProperty, Qt, QRect, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPolygonF

class GlowLED(QWidget):
    """
    Indication LED (Status Light) rendered via QPainter.
    Matches FilterTreeDelegate aesthetic (Solid Dot + Halo).
    Supports Shapes: Circle, Square, Triangle.
    """
    SHAPE_CIRCLE = 'CIRCLE'
    SHAPE_SQUARE = 'SQUARE'
    SHAPE_TRIANGLE = 'TRIANGLE'

    def __init__(self, color="#FFC66D", size=8, parent=None, shape='CIRCLE'):
        super().__init__(parent)
        self._color = QColor(color)
        self._led_size = size
        self._active = False
        self._shape = shape
        
        # Calculate size with halo padding. 
        # For gradient, we want a larger, softer falloff.
        # Halo = 100% of size (2x total diameter approx)
        self._halo_padding = int(size * 1.0) 
        total_size = size + (self._halo_padding * 2)
        self.setFixedSize(total_size, total_size)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setActive(self, active: bool):
        self._active = active
        self.update()

    def setGlowColor(self, color):
        self._color = QColor(color)
        self.update()

    def setShape(self, shape):
        self._shape = shape
        self.update()

    @pyqtProperty(bool)
    def active(self): return self._active
    
    @active.setter
    def active(self, val): self.setActive(val)

    RING_COLOR = "#444444"

    @staticmethod
    def draw_led(painter: QPainter, rect: QRect, color: QColor, active: bool, size: int, ring_color: QColor = None, max_radius: float = None, shape='CIRCLE'):
        """
        Shared renderer for all LEDs (Widgets & Delegates).
        """
        if ring_color is None:
             ring_color = QColor(GlowLED.RING_COLOR)

        # Center rect
        center = rect.center()
        cx, cy = center.x(), center.y()
        r = size / 2
        
        # Define LED geometry from center
        led_rect = QRect(int(cx - r), int(cy - r), int(size), int(size))
        
        if active:
            # 1. Halo (Radial Gradient for Gaussian-like look)
            # T-70: Tighter glow for small LEDs (1.2x instead of 1.5x)
            halo_radius = size * 1.2
            
            # Clamp to max_radius if provided (prevent row clipping)
            if max_radius is not None and halo_radius > max_radius:
                halo_radius = max_radius
                
            # Halo is always circular/radial for "Glow" effect
            gradient = QRadialGradient(QPointF(cx, cy), halo_radius)
            
            # Gradient stops
            c_center = QColor(color)
            c_center.setAlpha(180) # Increased pop (was 150)
            
            c_mid = QColor(color)
            c_mid.setAlpha(60) # Slight mid bump (was 50)
            
            c_edge = QColor(color)
            c_edge.setAlpha(0) # Transparent edge
            
            gradient.setColorAt(0.0, c_center)
            gradient.setColorAt(0.5, c_mid)
            gradient.setColorAt(1.0, c_edge)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw gradient rect (larger than led) - always circle for glow
            h = int(halo_radius)
            painter.drawEllipse(center, h, h)
            
            # 2. Core (Solid, No Pen)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            if shape == GlowLED.SHAPE_SQUARE:
                painter.drawRoundedRect(led_rect, 2, 2)
            elif shape == GlowLED.SHAPE_TRIANGLE:
                # Upward Triangle
                p1 = QPointF(cx, cy - r)     # Top
                p2 = QPointF(cx - r, cy + r) # Bottom Left
                p3 = QPointF(cx + r, cy + r) # Bottom Right
                poly = QPolygonF([p1, p2, p3])
                painter.drawPolygon(poly)
            else:
                painter.drawEllipse(led_rect)
            
        else:
            # Inactive State (Dimmed Identity for T-92)
            # Retain color identity but dimmed, no glow.
            
            dim_fill = QColor(color)
            dim_fill.setAlpha(40) # Very subtle fill to show "mass"
            
            dim_stroke = QColor(color)
            dim_stroke.setAlpha(120) # Crisp outline to show "shape" and "type"
            
            painter.setBrush(QBrush(dim_fill))
            painter.setPen(QPen(dim_stroke, 1.5)) 
            
            if shape == GlowLED.SHAPE_SQUARE:
                painter.drawRoundedRect(led_rect, 2, 2)
            elif shape == GlowLED.SHAPE_TRIANGLE:
                # Upward Triangle
                p1 = QPointF(cx, cy - r)
                p2 = QPointF(cx - r, cy + r)
                p3 = QPointF(cx + r, cy + r)
                poly = QPolygonF([p1, p2, p3])
                painter.drawPolygon(poly)
            else:
                painter.drawEllipse(led_rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Delegate painting to shared logic
        GlowLED.draw_led(
            painter, 
            self.rect(), 
            self._color, 
            self._active, 
            self._led_size,
            shape=self._shape
        )
