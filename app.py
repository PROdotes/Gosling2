"""
Gosling2 Music Library and Player
Main application entry point
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.presentation.views import MainWindow


def main() -> None:
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Gosling2")
    app.setOrganizationName("Prodo")

    # Set App Icon
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "app_icon.png")
    app.setWindowIcon(QIcon(icon_path))
    
    # Apply Theme
    try:
        theme_path = os.path.join(os.path.dirname(__file__), "src", "resources", "theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Failed to load theme: {e}")

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()