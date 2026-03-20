import datetime
import os
import sys
from typing import Optional, TextIO


class Logger:
    """Simple v3 bootstrap logger with file persistence and level filtering."""

    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, log_file="gosling.log"):
        self.log_file = log_file
        # Set level from env at init
        env_level = os.getenv("GOSLING_LOG_LEVEL", "INFO").upper()
        self.current_level = self.LEVELS.get(env_level, 20)
        self._f: Optional[TextIO] = None

    def _get_file(self) -> Optional[TextIO]:
        """Lazy file handle acquisition with stderr fallback on failure."""
        if self._f:
            return self._f

        try:
            self._f = open(self.log_file, "a", encoding="utf-8")
            return self._f
        except Exception as e:
            # Audit #13: Don't swallow logging failures silently.
            sys.stderr.write(
                f"CRITICAL: Failed to open log file {self.log_file}: {e}\n"
            )
            return None

    def _log(self, level: str, msg: str):
        level_val = self.LEVELS.get(level, 20)
        if level_val < self.current_level:
            return

        timestamp = datetime.datetime.now().isoformat()
        line = f"{timestamp} [{level:8}] {msg}"

        # Always output to console
        print(line)

        # Try persisted logging
        f = self._get_file()
        if f:
            try:
                f.write(line + "\n")
                f.flush()  # Ensure it hits disk
            except Exception as e:
                sys.stderr.write(f"ERROR: Failed to write to log file: {e}\n")

    def debug(self, msg: str):
        self._log("DEBUG", msg)

    def info(self, msg: str):
        self._log("INFO", msg)

    def warning(self, msg: str):
        self._log("WARNING", msg)

    def error(self, msg: str):
        self._log("ERROR", msg)

    def critical(self, msg: str):
        self._log("CRITICAL", msg)


# Default instance
logger = Logger()
