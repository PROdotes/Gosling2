from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import Qt
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SymphonyDB - Music Tagging & Library")
        # Define initial geometry: x, y, width, height
        self.setGeometry(100, 100, 800, 600)

        label = QLabel("Hello, SymphonyDB!", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()  # Makes the window visible

    sys.exit(app.exec())