from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import pyqtProperty
from .base import GlowWidget

class GlowLED(GlowWidget):
    """
    Indication LED (Status Light) with Amber Halo.
    Can be toggled active/inactive.
    """
    def __init__(self, color="#FFC66D", size=8, parent=None):
        self.led = QFrame()
        self.led.setFixedSize(size, size)
        self.led.setObjectName("StatusLed") # Hook for QSS base style
        
        super().__init__(self.led, trigger_mode="manual", parent=parent)
        self.setGlowColor(color)
        
        # Center the LED in the GlowWidget
        self.layout.addStretch()
        self.layout.addWidget(self.led)
        self.layout.addStretch()
        
        self._active = False

    def setActive(self, active: bool):
        self._active = active
        self.led.setProperty("active", active)
        self.led.style().unpolish(self.led)
        self.led.style().polish(self.led)
        
        if active:
            self._show_glow()
        else:
            self._hide_glow()

    @pyqtProperty(bool)
    def active(self): return self._active
    
    @active.setter
    def active(self, val): self.setActive(val)
