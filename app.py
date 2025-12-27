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
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "app_icon.svg")
    app.setWindowIcon(QIcon(icon_path))
    
    # Use Fusion style for consistent QSS rendering (fixes native Windows ghosts)
    app.setStyle("Fusion")
    
    # Apply Theme
    try:
        theme_path = os.path.join(os.path.dirname(__file__), "src", "resources", "theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                qss = f.read()
                # Harden Asset Paths: Ensure URLs are relative to the theme file, not CWD
                # This fixes the fragility of "url(Gosling2/...)" vs "url(src/...)"
                base_dir = os.path.dirname(theme_path).replace("\\", "/")
                # Replace any relative url(...) with absolute path
                # Note: This is a simple replacer. ideally we'd regex, but for now we fix the root.
                # Since we used "Gosling2/src/resources/" in CSS, we need to be careful.
                # Actually, standardizing on "url(filename.svg)" in CSS and prepending path here is best.
                # But to avoid breaking current CSS, we'll leave CSS as is and rely on Qt resolving relative to CWD?
                # No, Qt resolves relative to CWD.
                # BETTER FIX: Use QDir.setSearchPaths?
                # OR: rewriting the QSS is the most robust "Pythonic" way without Qt config.
                
                # Current CSS has "url(Gosling2/src/resources/...)" which matches Outer CWD.
                # If we run from Inner CWD, it breaks.
                # Let's strip the prefix and prepend the absolute base_dir.
                qss = qss.replace("url(Gosling2/src/resources/", f"url({base_dir}/")
                # Also handle simple "url(" just in case
                # qss = qss.replace("url(", f"url({base_dir}/") 
                
                app.setStyleSheet(qss)
    except Exception as e:
        print(f"Failed to load theme: {e}")

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()