"""
Gosling2 Music Library and Player
Main application entry point
"""
import sys
from PyQt6.QtWidgets import QApplication
from src.presentation.views import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Gosling2")
    app.setOrganizationName("Prodo")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

