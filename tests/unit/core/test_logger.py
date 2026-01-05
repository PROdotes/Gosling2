import pytest
import logging
import threading
from unittest.mock import MagicMock
from src.core import logger

class TestLogger:
    """Tests for core logging infrastructure."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset global logger state before each test."""
        # Setup: Take lock, swap state, release lock
        with logger._LOGGER_LOCK:
            old_logger = logger._LOGGER
            old_observers = set(logger._USER_OBSERVERS)
            
            logger._LOGGER = None
            logger._USER_OBSERVERS.clear()
            
        yield
        
        # Teardown: Take lock, restore state, release lock
        with logger._LOGGER_LOCK:
            logger._LOGGER = old_logger
            logger._USER_OBSERVERS = old_observers

    class TestLoggerCore:
        """Tests for singleton and basic logging levels."""

        def test_setup_singleton(self):
            """Ensure logger is set up once and returns same instance."""
            log1 = logger._setup()
            log2 = logger.get()
            assert log1 is log2
            assert log1.name == "Gosling2"
            assert len(log1.handlers) >= 1

        def test_dev_warning(self, caplog):
            """Test dev warning format."""
            with caplog.at_level(logging.WARNING):
                logger.dev_warning("Schema Bad")
                
            assert "[DEV] Schema Bad" in caplog.text

        def test_formatted_methods(self, caplog):
            """Test info/error/debug wrappers include correct icons/prefix."""
            with caplog.at_level(logging.DEBUG):
                logger.info("Info Msg")
                logger.debug("Debug Msg")
                logger.error("Error Msg")
                
            assert "Info Msg" in caplog.text
            assert "Debug Msg" in caplog.text
            assert "[ERROR] Error Msg" in caplog.text

    class TestObserverLogic:
        """Tests for warning subscription and notifications."""

        def test_user_warning_notification(self):
            """Test that user_warning notifies subscribers."""
            mock_callback = MagicMock()
            logger.subscribe_to_user_warnings(mock_callback)
            
            logger.user_warning("Disk Full")
            mock_callback.assert_called_once_with("Disk Full")

        def test_duplicate_subscription_prevented(self):
            """Test that same callback is only registered once (Set behavior)."""
            mock_callback = MagicMock()
            logger.subscribe_to_user_warnings(mock_callback)
            logger.subscribe_to_user_warnings(mock_callback)
            
            logger.user_warning("Warning")
            assert mock_callback.call_count == 1

        def test_unsubscribe(self):
            """Test unregistering an observer."""
            mock_callback = MagicMock()
            logger.subscribe_to_user_warnings(mock_callback)
            logger.unsubscribe_from_user_warnings(mock_callback)
            
            logger.user_warning("Silent")
            assert mock_callback.call_count == 0

        def test_observer_exception_safety(self):
            """If a subscriber crashes, logger should not fail."""
            bad_callback = MagicMock(side_effect=Exception("Boom"))
            good_callback = MagicMock()
            
            logger.subscribe_to_user_warnings(bad_callback)
            logger.subscribe_to_user_warnings(good_callback)
            
            # Should not raise exception
            logger.user_warning("Test")
            
            # Good callback should still run
            good_callback.assert_called_once()

    class TestThreadSafety:
        """Robustness tests for concurrent operations."""

        def test_concurrent_subscription(self):
            """Verify that multiple threads can subscribe/unsubscribe safely."""
            def worker():
                cb = lambda x: None
                for _ in range(100):
                    logger.subscribe_to_user_warnings(cb)
                    logger.unsubscribe_from_user_warnings(cb)

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()
            
            # Should be empty at the end
            assert len(logger._USER_OBSERVERS) == 0
