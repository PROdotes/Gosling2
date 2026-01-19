from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QMenu
from PyQt6.QtGui import QAction
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
    import_requested = pyqtSignal()
    logs_requested = pyqtSignal()
    history_requested = pyqtSignal()

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
        
        # Setup System Menu
        self.system_menu = QMenu(self)
        self.system_menu.setObjectName("SystemDropdownMenu")
        
        act_settings = QAction("⚙️ SYSTEM SETTINGS", self)
        act_settings.triggered.connect(self.settings_requested.emit)
        
        act_logs = QAction("📋 DIAGNOSTIC CONSOLE", self)
        act_logs.triggered.connect(self.logs_requested.emit)
        
        act_history = QAction("🕰️ LOG HISTORY (AUDIT)", self)
        act_history.triggered.connect(self.history_requested.emit)
        
        self.system_menu.addAction(act_settings)
        self.system_menu.addSeparator()
        self.system_menu.addAction(act_logs)
        self.system_menu.addAction(act_history)
        
        self.btn_logo_icon.clicked.connect(self._show_system_menu)
        
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
        
        # 4. Import Button (T-84) - Right Aligned with Safety Buffer
        self.btn_import = GlowButton("IMPORT")
        self.btn_import.setObjectName("PrimaryImportButton")
        self.btn_import.setFixedWidth(80)
        self.btn_import.setContentsMargins(0, 3, 0, 4)
        self.btn_import.clicked.connect(self.import_requested.emit)
        
        # Assemble Left-to-Right
        layout.addWidget(self.btn_logo_icon)
        layout.addSpacing(10)
        layout.addWidget(title_container)
        layout.addSpacing(20)
        layout.addWidget(self.search_box)
        layout.addWidget(self.draggable_area, 1) # Force it to swallow the rest with stretch factor 1
        layout.addWidget(self.btn_import)
        layout.addSpacing(40) # Safety buffer against SystemIsland (X button)

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
            if self.window().isMaximized():
                # T-Fix: Restore on drag (User Request)
                # Calculate grab ratio to keep mouse in same relative spot on narrower title bar
                old_width = self.window().width()
                local_x = self._drag_pos.x()
                ratio = local_x / max(1, old_width)
                
                self.window().showNormal()
                
                # Update drag offset for the restored size
                new_width = self.window().width()
                new_local_x = int(new_width * ratio)
                # Keep original Y offset (vertical grab point)
                self._drag_pos = QPoint(new_local_x, self._drag_pos.y())

            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _show_system_menu(self):
        """Display the system menu below the logo button."""
        # Calculate position to show the menu aligned with the button
        pos = self.btn_logo_icon.mapToGlobal(self.btn_logo_icon.rect().bottomLeft())
        self.system_menu.exec(pos)
