from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QButtonGroup)
from PyQt6.QtCore import Qt, pyqtProperty

class JingleButton(QPushButton):
    """
    High-vibrancy hot-key button for the Jingle Bay.
    """
    def __init__(self, label, subtext, category, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 58) 
        self.setCheckable(True)
        # Identity ONLY. QSS handles the rest.
        self.setObjectName(f"JingleButton_{category}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8) # Extra left margin for the LED strip
        layout.setSpacing(1)
        
        title = QLabel(label)
        title.setObjectName("JingleButtonTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        info = QLabel(subtext)
        info.setObjectName("JingleButtonInfo")
        info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, 0, Qt.AlignmentFlag.AlignCenter)

class JinglePip(QPushButton):
    """
    Small tactical circular LED indicators for switching jingle banks.
    """
    def __init__(self, number, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.setCheckable(True)
        self.setObjectName("JinglePip")
        # Storing the bank number for later signal handling
        self.bank_index = number

class JingleCurtain(QFrame):
    """
    Top-sliding shelf for quick-fire jingles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("JingleCurtain")
        self.setFixedHeight(0)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel("QUICK-FIRE JINGLE BAYS")
        title.setObjectName("JingleCurtainTitle")
        main_layout.addWidget(title)
        
        # --- ASSEMBLY DECK (Preset Rail | Button Grid) ---
        deck_layout = QHBoxLayout()
        deck_layout.setSpacing(25)
        
        # A. PRESET RAIL (Tactical Sidebar)
        self.rail = QVBoxLayout()
        self.rail.setSpacing(8)
        self.rail.addStretch()
        
        self.pip_group = QButtonGroup(self)
        self.pip_group.setExclusive(True)
        
        # 8 Pips (Banks 1-8)
        for i in range(8):
            pip = JinglePip(i)
            self.pip_group.addButton(pip, i)
            if i == 0: pip.setChecked(True) # Bank 1 active by default
            self.rail.addWidget(pip, 0, Qt.AlignmentFlag.AlignCenter)
            
        # Preset Management Button
        self.btn_presets = QPushButton("PRST")
        self.btn_presets.setObjectName("PresetUtilButton")
        self.btn_presets.setFixedSize(32, 22)
        self.rail.addWidget(self.btn_presets, 0, Qt.AlignmentFlag.AlignCenter)
        self.rail.addStretch()
        
        deck_layout.addLayout(self.rail)

        # B. THE BUTTON GRID (Hot Keys)
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Dummy Data for v0.2
        bays = [
            ("STATION ID", "00:05", "id"),
            ("TRANSITION", "00:03", "transition"),
            ("SWEEPER A",  "00:08", "sweeper"),
            ("VOICEOVER",  "00:12", "voice"),
            ("AD SPOT 1",  "00:30", "ads"),
            ("AD SPOT 2",  "00:30", "ads"),
            ("LEGAL ID",   "00:10", "legal"),
            ("MORNING B",  "00:05", "promo"),
        ]
        
        for i, (label, dur, cat) in enumerate(bays):
            btn = JingleButton(label, dur, cat)
            grid.addWidget(btn, i // 4, i % 4)
            
        deck_layout.addLayout(grid)
        deck_layout.addStretch()
        
        main_layout.addLayout(deck_layout)
        main_layout.addStretch()

    @pyqtProperty(int)
    def curtainHeight(self): return self.height()

    @curtainHeight.setter
    def curtainHeight(self, h): self.setFixedHeight(h)
