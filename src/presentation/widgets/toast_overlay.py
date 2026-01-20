from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer, QEasingCurve, QPoint
from PyQt6.QtGui import QColor, QPalette

class ToastOverlay(QLabel):
    """
    A non-intrusive floating feedback widget (Toast/HUD) with a message queue.
    Ensures multiple messages are shown sequentially rather than interrupting each other.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow) # Keeps it inside parent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Click-through
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Message Queue State
        self._message_queue = []
        self._is_showing = False
        
        # Style
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 0.95);
                border: 1px solid #FFC66D;
                border-radius: 6px;
                color: #FFC66D;
                padding: 10px 20px;
                font-family: 'Bahnschrift', 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # Opacity Effect for Fading
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animation
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Timer to auto-hide
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)
        
        self.hide()
        
    def show_message(self, text: str, type: str = "info", duration: int = 1500):
        """
        Add a message to the queue. If no message is showing, process it immediately.
        """
        self._message_queue.append((text, type, duration))
        if not self._is_showing:
            self._next_message()
            
    def _next_message(self):
        """Show the next message in the queue."""
        if not self._message_queue:
            self._is_showing = False
            return
            
        self._is_showing = True
        text, type, duration = self._message_queue.pop(0)
        
        self.setText(text)
        self.adjustSize()
        
        # Dynamic Styling
        border_color = "#FFC66D" # Amber (Default/Info)
        text_color = "#FFC66D"
        
        if type == "success":
            border_color = "#6A8759" # Green
            text_color = "#A9B7C6"
        elif type == "warning":
            border_color = "#BBB529" # Yellow
            text_color = "#E8C060"
        elif type == "error":
            border_color = "#CC7832" # Red/Orange
            text_color = "#CC7832"
            
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(20, 20, 20, 0.95);
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
                padding: 10px 20px;
                font-family: 'Bahnschrift', 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        
        # Re-center (Parent might have resized)
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 100
            self.move(x, y)
        
        self.raise_()
        self.show()
        
        # Fade In
        try:
            self.anim.finished.disconnect()
        except TypeError:
            pass
            
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(400) # Slightly faster in than out
        self.anim.start()
        
        # Start timer to hide after duration
        self.timer.start(duration)
        
    def hide_toast(self):
        """Trigger the fade out animation."""
        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(0.0)
        self.anim.setDuration(800)
        
        try:
            self.anim.finished.disconnect()
        except TypeError:
            pass
            
        self.anim.finished.connect(self._on_fade_out_finished)
        self.anim.start()
        
    def _on_fade_out_finished(self):
        """Called when fade out finishes, hides widget and checks for next message."""
        self.hide()
        # Small gap between messages
        QTimer.singleShot(100, self._next_message)
