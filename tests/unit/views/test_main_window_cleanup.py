"""Tests for MainWindow cleanup on close"""
import pytest
from unittest.mock import Mock, patch
from PyQt6.QtGui import QCloseEvent
from src.presentation.views.main_window import MainWindow


class TestMainWindowCleanup:
    """Test resource cleanup when MainWindow closes"""

    def test_close_event_calls_playback_cleanup(self, qtbot):
        """Test that closeEvent calls playback_service.cleanup()"""
        window = MainWindow()
        qtbot.addWidget(window)
        
        # Mock the cleanup method
        window.playback_service.cleanup = Mock()
        
        # Create a close event
        event = QCloseEvent()
        
        # Call closeEvent
        window.closeEvent(event)
        
        # Verify cleanup was called
        window.playback_service.cleanup.assert_called_once()
        
        # Verify event was accepted
        assert event.isAccepted()

    def test_close_event_saves_geometry_after_cleanup(self, qtbot):
        """Test that window geometry is saved after cleanup"""
        window = MainWindow()
        qtbot.addWidget(window)
        
        # Mock methods
        window.playback_service.cleanup = Mock()
        window._save_window_geometry = Mock()
        window._save_splitter_states = Mock()
        
        # Create a close event
        event = QCloseEvent()
        
        # Call closeEvent
        window.closeEvent(event)
        
        # Verify cleanup was called before saving
        window.playback_service.cleanup.assert_called_once()
        window._save_window_geometry.assert_called_once()
        window._save_splitter_states.assert_called_once()
