from PyQt6.QtWidgets import QFrame, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from .glow_factory import GlowButton

class SystemIsland(QFrame):
    """
    Floating system controls (Min/Max/Close).
    Encapsulated in a separate 'Island' widget for layout flexibility.
    """
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBarIsland")
        self.setFixedSize(130, 40)
        
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addStretch()
        
        # Sequence: [ - ] [ ▢ ] [ X ]
        self.btn_min = self._create_btn("－", "MinimizeButton")
        self.btn_min.clicked.connect(self.minimize_requested.emit)
        
        self.btn_max = self._create_btn("▢", "MaximizeButton")
        self.btn_max.clicked.connect(self.maximize_requested.emit)
        
        self.btn_close = self._create_btn("✕", "CloseButton")
        self.btn_close.clicked.connect(self.close_requested.emit)
        
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def _create_btn(self, text, obj_name):
        btn = GlowButton(text)
        btn.setObjectName(obj_name)
        btn.setProperty("class", "SystemButton")
        btn.setGlowRadius(6)
        return btn

    def update_maximize_icon(self, is_maximized: bool):
        """Update the maximize button icon based on window state."""
        if is_maximized:
            self.btn_max.setText("❐") # Restore (Overlapping Squares)
            self.btn_max.setToolTip("Restore Down")
        else:
            self.btn_max.setText("▢") # Maximize (Single Square)
            self.btn_max.setToolTip("Maximize")
