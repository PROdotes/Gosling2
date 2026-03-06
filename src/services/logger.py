class Logger:
    """Simple v3 bootstrap logger."""
    def debug(self, msg: str): print(f"DEBUG: {msg}")
    def info(self, msg: str): print(f"INFO: {msg}")
    def error(self, msg: str): print(f"ERROR: {msg}")
    def warning(self, msg: str): print(f"WARNING: {msg}")

logger = Logger()
