from PyQt6.QtWidgets import QAbstractButton, QWidget, QSizePolicy
from PyQt6.QtCore import pyqtProperty, Qt, QRect, QSize, QPointF, QPropertyAnimation, pyqtSignal, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient

class GlowToggle(QAbstractButton):
    """
    Pro Audio Hardware style toggle switch.
    Pill-shaped with a sliding handle and amber glow when active.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(45, 20)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self._handle_position = 0.0 # 0.0 to 1.0 (float)
        self._animation = QPropertyAnimation(self, b"handle_position")
        self._animation.setDuration(250)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        self._glow_opacity = 0.0
        self._glow_animation = QPropertyAnimation(self, b"glow_opacity")
        self._glow_animation.setDuration(300)

        self._on_txt = ""
        self._off_txt = ""

    def set_labels(self, on_txt, off_txt):
        self._on_txt = on_txt
        self._off_txt = off_txt
        # Adjust size only if text is genuinely too long for 45px
        if len(on_txt) > 4 or len(off_txt) > 4:
             self.setFixedSize(60, 20)
        self.update()
    
    @pyqtProperty(float)
    def handle_position(self):
        return self._handle_position
        
    @handle_position.setter
    def handle_position(self, pos):
        self._handle_position = pos
        self.update()

    @pyqtProperty(float)
    def glow_opacity(self):
        return self._glow_opacity
        
    @glow_opacity.setter
    def glow_opacity(self, opacity):
        self._glow_opacity = opacity
        self.update()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._handle_position = 1.0 if checked else 0.0
        self._glow_opacity = 1.0 if checked else 0.0
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        checked = self.isChecked()
        
        # Animate handle
        self._animation.stop()
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()
        
        # Animate glow
        self._glow_animation.stop()
        self._glow_animation.setEndValue(1.0 if checked else 0.0)
        self._glow_animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        margin = 2
        pill_rect = rect.adjusted(margin, margin, -margin, -margin)
        
        # 1. Background (Pill)
        # Inactive: Dark Slate
        # Active: Dark Amber/Brown
        if self.isChecked():
            bg_color = QColor("#332200") # Deep Amber shadow
        else:
            bg_color = QColor("#222222") # Industrial Dark
            
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.drawRoundedRect(pill_rect, pill_rect.height() / 2, pill_rect.height() / 2)
        
        # 1b. Labels (Hardware silk-screen look)
        if self._on_txt or self._off_txt:
            font = painter.font()
            font.setPointSize(6)
            font.setBold(True)
            painter.setFont(font)
            
            # Use adjusted rect for internal margin (4px)
            text_rect = pill_rect.adjusted(4, 0, -4, 0)

            # ON Label (Left side) - Visible when toggle is ON
            if self._on_txt:
                painter.setOpacity(self._handle_position)
                painter.setPen(QColor("#FFC66D"))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._on_txt)
            
            # OFF Label (Right side) - Visible when toggle is OFF
            if self._off_txt:
                painter.setOpacity(1.0 - self._handle_position)
                painter.setPen(QColor("#666666"))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self._off_txt)
            
            painter.setOpacity(1.0) # Reset

        # 2. Tracks/Glow (Internal)
        if self._glow_opacity > 0:
            glow_rect = pill_rect.adjusted(2, 2, -2, -2)
            gradient = QLinearGradient(QPointF(glow_rect.topLeft()), QPointF(glow_rect.topRight()))
            c = QColor("#FFC66D")
            c.setAlpha(int(100 * self._glow_opacity))
            gradient.setColorAt(0, QColor(0,0,0,0))
            gradient.setColorAt(self._handle_position, c)
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(glow_rect, glow_rect.height() / 2, glow_rect.height() / 2)

        # 3. Handle (Circular Knob)
        handle_size = pill_rect.height() - 4
        x_range = pill_rect.width() - handle_size - 4
        x_pos = pill_rect.x() + 2 + (x_range * self._handle_position)
        handle_rect = QRect(int(x_pos), int(pill_rect.y() + 2), int(handle_size), int(handle_size))
        
        # Handle Gradient (Metallic/Soft Surface look)
        handle_grad = QLinearGradient(QPointF(handle_rect.topLeft()), QPointF(handle_rect.bottomRight()))
        if self.isChecked():
            handle_grad.setColorAt(0, QColor("#FFD591")) # Bright Amber
            handle_grad.setColorAt(1, QColor("#FFC66D")) # Amber
        else:
            handle_grad.setColorAt(0, QColor("#888888"))
            handle_grad.setColorAt(1, QColor("#555555"))
            
        painter.setBrush(handle_grad)
        
        # Handle Halo (Outer glow for handle when active)
        if self.isChecked() and self._glow_opacity > 0:
            halo_grad = QRadialGradient(QPointF(handle_rect.center()), float(handle_size))
            hc = QColor("#FFC66D")
            hc.setAlpha(int(150 * self._glow_opacity))
            halo_grad.setColorAt(0, hc)
            halo_grad.setColorAt(1, QColor(0,0,0,0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo_grad)
            painter.drawEllipse(handle_rect.center(), int(handle_size), int(handle_size))
            painter.setBrush(handle_grad) # Reset for handle core

        painter.setPen(QPen(QColor("#000000"), 0.5))
        painter.drawEllipse(handle_rect)
