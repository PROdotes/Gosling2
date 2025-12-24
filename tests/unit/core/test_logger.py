
import pytest
import logging
from unittest.mock import MagicMock, patch
from src.core import logger

class TestLogger:
    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset global logger state before each test."""
        # Save state
        old_logger = logger._LOGGER
        old_observers = list(logger._USER_OBSERVERS)
        
        # Reset
        logger._LOGGER = None
        logger._USER_OBSERVERS.clear()
        
        yield
        
        # Restore
        logger._LOGGER = old_logger
        logger._USER_OBSERVERS = old_observers

    def test_setup_singleton(self):
        """Ensure logger is set up once and returns same instance."""
        log1 = logger._setup()
        log2 = logger.get()
        assert log1 is log2
        assert log1.name == "Gosling2"
        assert len(log1.handlers) >= 1

    def test_user_warning_notification(self):
        """Test that user_warning notifies subscribers."""
        mock_callback = MagicMock()
        logger.subscribe_to_user_warnings(mock_callback)
        
        logger.user_warning("Disk Full")
        
        mock_callback.assert_called_once_with("Disk Full")

    def test_dev_warning(self, caplog):
        """Test dev warning format."""
        with caplog.at_level(logging.WARNING):
            logger.dev_warning("Schema Bad")
            
        assert "🔧 [DEV] Schema Bad" in caplog.text

    def test_formatted_methods(self, caplog):
        """Test info/error/debug wrappers."""
        # Using debug level to catch everything
        with caplog.at_level(logging.DEBUG):
            logger.info("Info Msg")
            logger.debug("Debug Msg")
            logger.error("Error Msg")
            
        assert "Info Msg" in caplog.text
        assert "Debug Msg" in caplog.text
        assert "❌ Error Msg" in caplog.text

    def test_observer_exception_safety(self):
        """If a subscriber crashes, logger should not crash."""
        bad_callback = MagicMock(side_effect=Exception("Boom"))
        good_callback = MagicMock()
        
        logger.subscribe_to_user_warnings(bad_callback)
        logger.subscribe_to_user_warnings(good_callback)
        
        # Should not raise exception
        logger.user_warning("Test")
        
        # Good callback should still run
        good_callback.assert_called_once()
