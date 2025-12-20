
import logging
import sys
import os

_LOGGER = None
_USER_OBSERVERS = []  # List of callbacks: func(msg: str) -> None

def subscribe_to_user_warnings(callback):
    """
    Register a function to be called when a user_warning occurs.
    Callback signature: func(msg: str) -> None
    Useful for showing Toast notifications or Status Bar messages in the UI.
    """
    _USER_OBSERVERS.append(callback)

def _setup():
    global _LOGGER
    if _LOGGER:
        return _LOGGER
        
    logger = logging.getLogger("Gosling2")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        # File Handler: Logs EVERYTHING (DEBUG+)
        try:
            log_file = os.path.join(os.getcwd(), "gosling.log")
            fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            logger.addHandler(fh)
        except Exception as e:
            print(f"Logger Setup Error (File): {e}")

        # Console Handler: Logs INFO+ for User clarity
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
        logger.addHandler(ch)
        
    _LOGGER = logger
    return logger

def get():
    return _setup()

def dev_warning(msg: str):
    """Log a warning relevant to developers (Schema mismatch, Internal logic)"""
    get().warning(f"🔧 [DEV] {msg}")

def user_warning(msg: str):
    """Log a warning relevant to users (Invalid ID3, File missing, Config issue)"""
    get().warning(f"⚠️  [USER] {msg}")
    
    # Notify UI or other listeners
    for cb in _USER_OBSERVERS:
        try:
            cb(msg)
        except Exception as e:
            get().error(f"Failed to notify warning observer: {e}")

def info(msg: str):
    get().info(msg)

def debug(msg: str):
    get().debug(msg)

def error(msg: str, exc_info=False):
    get().error(f"❌ {msg}", exc_info=exc_info)
