from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
import os
from .glow_factory import GlowLineEdit, GlowButton

class CustomTitleBar(QWidget):
    """
    Workstation Title Bar Branding & Search Hub.
    Does NOT contain system controls (see SystemIsland).
    """
    search_text_changed = pyqtSignal(str)
    settings_requested = pyqtSignal()
    maximize_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._drag_pos = QPoint()
        
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 1. Logo
        self.btn_logo_icon = GlowButton()
        self.btn_logo_icon.setObjectName("AppLogoIcon")
        self.btn_logo_icon.setProperty("class", "SystemButton")
        self.btn_logo_icon.setGlowRadius(6)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "resources", "app_icon.svg")
        self.btn_logo_icon.setIcon(QIcon(icon_path))
        self.btn_logo_icon.setIconSize(QSize(22, 28))
        self.btn_logo_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logo_icon.clicked.connect(self.settings_requested.emit)
        
        # 1b. Title (Stacked Labels for Glow)
        from PyQt6.QtWidgets import QGraphicsBlurEffect
        title_text = "GOSLING // WORKSTATION"
        title_container = QWidget()
        title_container.setFixedSize(320, 40) # Increased from 220 to prevent cropping
        v_center, h_margin = 3, 2
        
        self.lbl_title_glow = QLabel(title_text, title_container)
        self.lbl_title_glow.setObjectName("AppTitleGlow")
        self.lbl_title_glow.adjustSize()
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(9)
        self.lbl_title_glow.setGraphicsEffect(blur)
        self.lbl_title_glow.move(h_margin + 2, v_center + 2)
        
        self.lbl_title = QLabel(title_text, title_container)
        self.lbl_title.setObjectName("AppTitleLabel")
        self.lbl_title.adjustSize()
        self.lbl_title.move(h_margin, v_center)
        self.lbl_title.raise_()
        
        # 2. Search
        self.search_box = GlowLineEdit()
        self.search_box.setPlaceholderText("Search Library...")
        self.search_box.setFixedWidth(400) # Fixed width prevents it from pushing Title to center
        self.search_box.setContentsMargins(0, 3, 0, 4)
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        
        # 3. Draggable Area
        self.draggable_area = QWidget()
        self.draggable_area.setObjectName("SystemDraggableArea")
        self.draggable_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Assemble Left-to-Right
        layout.addWidget(self.btn_logo_icon)
        layout.addSpacing(10)
        layout.addWidget(title_container)
        layout.addSpacing(20)
        layout.addWidget(self.search_box)
        layout.addWidget(self.draggable_area, 1) # Force it to swallow the rest with stretch factor 1

    # Draggable logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
