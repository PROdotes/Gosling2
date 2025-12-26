from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

class CustomTitleBar(QWidget):
    """
    Workstation Title Bar Replacement.
    Features: Draggable area, App Logo, and System Controls (Min/Max/Close).
    """
    
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    search_text_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self._drag_pos = QPoint()
        
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Logo Section
        self.logo_label = QLabel("GOSLING // WORKSTATION")
        self.logo_label.setObjectName("AppLogo")
        layout.addWidget(self.logo_label)
        
        # 2. Search Section (The Draggable Search Strip)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search Library...")
        self.search_box.setMaximumWidth(400)
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        
        # 2b. Draggable Area (Padding)
        self.draggable_area = QWidget()
        self.draggable_area.setObjectName("SystemDraggableArea")
        self.draggable_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.logo_label)
        layout.addSpacing(20)
        layout.addWidget(self.search_box)
        layout.addWidget(self.draggable_area)
        
        # 3. System Controls
        self.btn_min = QPushButton("－")
        self.btn_min.setObjectName("MinimizeButton")
        self.btn_min.clicked.connect(self.minimize_requested.emit)
        
        self.btn_max = QPushButton("▢")
        self.btn_max.setObjectName("MaximizeButton")
        self.btn_max.clicked.connect(self.maximize_requested.emit)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.clicked.connect(self.close_requested.emit)
        
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    # Draggable logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """Standard window behavior: Double-click to maximize/restore."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
