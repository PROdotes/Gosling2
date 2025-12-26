from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QVBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, QSize, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

class JingleButton(QPushButton):
    """
    High-vibrancy hot-key button for the Jingle Bay.
    Features a 'Backlit' glow that pulses on hover.
    """
    def __init__(self, label, subtext, color_code="#9C27B0", parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 80)
        self.setCheckable(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)
        
        title = QLabel(label)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title.setStyleSheet(f"color: white; font-family: 'Agency FB'; font-size: 11pt; font-weight: bold;")
        
        info = QLabel(subtext)
        info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info.setStyleSheet(f"color: {color_code}; font-family: 'Segoe UI'; font-size: 7.5pt; font-weight: bold;")
        
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet(f"""
            JingleButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                 stop:0 #2A2A2A, stop:1 #121212);
                border: 2px solid #050505;
                border-radius: 8px;
            }}
            JingleButton:hover {{
                border: 2px solid {color_code};
                background-color: #1A1A1A;
            }}
            JingleButton:checked {{
                background-color: {color_code};
                border: 2px solid white;
            }}
            JingleButton:checked QLabel {{
                color: white;
            }}
        """)

class JingleCurtain(QFrame):
    """
    Top-sliding shelf for quick-fire jingles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("JingleCurtain")
        self.setFixedHeight(0) # Start closed
        
        self.setStyleSheet("""
            #JingleCurtain {
                background-color: #0A0A0A;
                border-bottom: 3px solid #D81B60;
                /* Vertical Machined Gradient for the 'Shelf' */
                background-image: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                 stop:0 #1A1A1A, 
                                                 stop:0.9 #0A0A0A,
                                                 stop:1.0 #000000);
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel("QUICK-FIRE JINGLE BAYS")
        title.setStyleSheet("color: #D81B60; font-family: 'Agency FB'; font-size: 10pt; letter-spacing: 2px; font-weight: bold;")
        main_layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Mock Bays
        bays = [
            ("STATION ID", "00:05", "#9C27B0"),
            ("TRANSITION", "00:03", "#9C27B0"),
            ("SWEEPER A", "00:08", "#9C27B0"),
            ("VOICEOVER", "00:12", "#8BC34A"),
            ("AD SPOT 1", "00:30", "#FF9800"),
            ("AD SPOT 2", "00:30", "#FF9800"),
            ("LEGAL ID", "00:10", "#4A90D9"),
            ("MORNING B", "00:05", "#E91E63"),
        ]
        
        for i, (label, dur, color) in enumerate(bays):
            btn = JingleButton(label, dur, color)
            grid.addWidget(btn, i // 4, i % 4)
            
        main_layout.addLayout(grid)
        main_layout.addStretch()

    @pyqtProperty(int)
    def curtainHeight(self):
        return self.height()

    @curtainHeight.setter
    def curtainHeight(self, h):
        self.setFixedHeight(h)
