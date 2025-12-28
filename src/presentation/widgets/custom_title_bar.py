from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
import os

class CustomTitleBar(QWidget):
    """
    Workstation Title Bar Replacement.
    Features: Draggable area, App Logo, and System Controls (Min/Max/Close).
    """
    
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    search_text_changed = pyqtSignal(str)
    settings_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._drag_pos = QPoint()
        
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Logo/Settings Button (Icon Only)
        self.btn_logo_icon = QPushButton()
        self.btn_logo_icon.setObjectName("AppLogoIcon")
        # Use absolute path to ensure resource loading
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "resources", "app_icon.svg")
        self.btn_logo_icon.setIcon(QIcon(icon_path))
        self.btn_logo_icon.setIconSize(QSize(24, 24))
        self.btn_logo_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logo_icon.clicked.connect(self.settings_requested.emit)
        
        # 1b. Title Label with Glow Effect (stacked labels)
        from PyQt6.QtWidgets import QGraphicsBlurEffect
        
        title_text = "GOSLING // WORKSTATION"
        
        # Container for stacked labels
        title_container = QWidget()
        title_container.setFixedSize(300, 36)  # Wider container
        
        # Vertical center offset
        v_center = 3
        h_margin = 2  # Left margin for glow clearance
        
        # Glow label (behind, blurred)
        self.lbl_title_glow = QLabel(title_text, title_container)
        self.lbl_title_glow.setObjectName("AppTitleGlow")
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(8)
        self.lbl_title_glow.setGraphicsEffect(blur)
        self.lbl_title_glow.move(h_margin + 2, v_center + 2)  # Slight offset for halo
        
        # Main label (on top, crisp)
        self.lbl_title = QLabel(title_text, title_container)
        self.lbl_title.setObjectName("AppTitleLabel")
        self.lbl_title.move(h_margin, v_center)
        self.lbl_title.raise_()  # Ensure on top
        
        layout.addWidget(self.btn_logo_icon)
        layout.addSpacing(8)  # Space between icon and title
        layout.addWidget(title_container)
        
        # 2. Search Section (The Draggable Search Strip)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search Library...")
        self.search_box.setMaximumWidth(400)
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        
        # 2b. Draggable Area (Padding)
        self.draggable_area = QWidget()
        self.draggable_area.setObjectName("SystemDraggableArea")
        self.draggable_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # layout.addWidget(self.logo_label) # Removed
        layout.addSpacing(10)
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
