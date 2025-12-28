from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QVBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtProperty

class JingleButton(QPushButton):
    """
    High-vibrancy hot-key button for the Jingle Bay.
    """
    def __init__(self, label, subtext, category, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 80)
        self.setCheckable(True)
        # Identity ONLY. QSS handles the rest.
        self.setObjectName(f"JingleButton_{category}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)
        
        title = QLabel(label)
        title.setObjectName("JingleButtonTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        info = QLabel(subtext)
        info.setObjectName("JingleButtonInfo")
        info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, 0, Qt.AlignmentFlag.AlignCenter)

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
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Data ONLY. No style info.
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
            
        main_layout.addLayout(grid)
        main_layout.addStretch()

    @pyqtProperty(int)
    def curtainHeight(self): return self.height()

    @curtainHeight.setter
    def curtainHeight(self, h): self.setFixedHeight(h)
