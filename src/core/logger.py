import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Callable, Set
from PyQt6.QtCore import QSettings

# Global State
_LOGGER: Optional[logging.Logger] = None
_LOGGER_LOCK = threading.Lock()
_LOGGER_PATH: Optional[Path] = None
_USER_OBSERVERS: Set[Callable[[str], None]] = set()

def subscribe_to_user_warnings(callback: Callable[[str], None]) -> None:
    """
    Register a function to be called when a user_warning occurs.
    Callback signature: func(msg: str) -> None
    """
    with _LOGGER_LOCK:
        _USER_OBSERVERS.add(callback)

def unsubscribe_from_user_warnings(callback: Callable[[str], None]) -> None:
    """Unregister a warning observer."""
    with _LOGGER_LOCK:
        if callback in _USER_OBSERVERS:
            _USER_OBSERVERS.remove(callback)

def _setup(custom_path: Optional[str] = None) -> logging.Logger:
    global _LOGGER, _LOGGER_PATH
    with _LOGGER_LOCK:
        if _LOGGER:
            return _LOGGER
            
        if not _LOGGER_PATH and not custom_path:
            # Try to pull from QSettings directly to avoid circular dependency
            settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Prodo", "Gosling2")
            stored_path = settings.value("library/logPath")
            if stored_path:
                _LOGGER_PATH = Path(stored_path)

        if custom_path:
            _LOGGER_PATH = Path(custom_path)
            
        logger = logging.getLogger("Gosling2")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            # 1. Rotating File Handler (Level 3 Integrity)
            # Keeps 5 files of 1MB each to prevent infinite growth
            try:
                # Use custom path if provided, else project root
                if not _LOGGER_PATH:
                    log_dir = Path(__file__).parent.parent.parent
                    _LOGGER_PATH = log_dir / "gosling.log"
                
                log_file = _LOGGER_PATH
                
                fh = RotatingFileHandler(
                    log_file, 
                    maxBytes=1024 * 1024, # 1MB
                    backupCount=5,
                    encoding='utf-8'
                )
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
                logger.addHandler(fh)
            except Exception:
                # Fallback to console only if file fails
                pass

            # 2. Console Handler (Level 1 Logic)
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
            logger.addHandler(ch)
            
        _LOGGER = logger
        return logger

def initialize(custom_path: Optional[str] = None) -> None:
    """
    Early initialization of the logger with a specific path.
    Call this before any other logger.get() calls.
    """
    _setup(custom_path)

def get() -> logging.Logger:
    """Access the singleton logger instance."""
    if _LOGGER:
        return _LOGGER
    return _setup()

def dev_warning(msg: str):
    """Log a warning relevant to developers (Schema mismatch, Internal logic)."""
    get().warning(f"[DEV] {msg}")

def user_warning(msg: str):
    """Log a warning relevant to users (Invalid ID3, File missing, Config issue)."""
    get().warning(f"[USER] {msg}")
    
    # Notify UI or other listeners (thread-safe copy)
    with _LOGGER_LOCK:
        observers = list(_USER_OBSERVERS)
        
    for cb in observers:
        try:
            cb(msg)
        except Exception as e:
            get().error(f"Failed to notify warning observer: {e}")

def info(msg: str):
    """Log general application progress."""
    get().info(msg)

def debug(msg: str):
    """Log high-verbosity diagnostic information."""
    get().debug(msg)

def error(msg: str, exc_info=False):
    """Log a failure with optional traceback."""
    get().error(f"[ERROR] {msg}", exc_info=exc_info)
