"""Integration test for the application"""
import pytest
import tempfile
import os
from PyQt6.QtWidgets import QApplication
from src.presentation.views.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMainWindowIntegration:
    """Integration tests for MainWindow"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            db_path = f.name

        from src.data.database_config import DatabaseConfig
        original_path = DatabaseConfig.get_database_path
        DatabaseConfig.get_database_path = lambda: db_path

        yield db_path

        DatabaseConfig.get_database_path = original_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def window(self, qapp, temp_db):
        """Create a main window instance"""
        window = MainWindow()
        yield window
        window.close()

    def test_window_creation(self, window):
        """Test creating the main window"""
        assert window is not None
        assert window.windowTitle() == "Gosling2 Music Player"

    def test_ui_elements_exist(self, window):
        """Test that all UI elements are created"""
        # Library elements
        assert window.library_widget.table_view is not None
        assert window.library_widget.filter_widget is not None
        
        # Search is in Title Bar
        assert window.title_bar.search_box is not None
        
        # Playlist & Info (Right Panel)
        assert window.playlist_widget is not None
        assert window.right_panel is not None
        
        # Playback elements
        assert window.playback_widget.playback_slider is not None
        assert window.playback_widget.btn_play is not None
        assert window.playback_widget.volume_slider is not None

    def test_services_initialized(self, window):
        """Test that services are initialized"""
        assert window.library_service is not None
        assert window.metadata_service is not None
        assert window.playback_service is not None

    def test_library_model_initialized(self, window):
        """Test that library model is initialized"""
        assert window.library_widget.library_model is not None
        assert window.library_widget.proxy_model is not None

