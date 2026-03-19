import datetime
import os


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
        # Set default level to INFO, but allow override via env
        env_level = os.getenv("GOSLING_LOG_LEVEL", "INFO").upper()
        self.current_level = self.LEVELS.get(env_level, 20)

    def _log(self, level: str, msg: str):
        level_val = self.LEVELS.get(level, 20)
        if level_val < self.current_level:
            return

        timestamp = datetime.datetime.now().isoformat()
        line = f"{timestamp} [{level:8}] {msg}"
        print(line)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def debug(self, msg: str):
        self._log("DEBUG", msg)

    def info(self, msg: str):
        self._log("INFO", msg)

    def warning(self, msg: str):
        self._log("WARNING", msg)

    def error(self, msg: str):
        self._log("ERROR", msg)


logger = Logger()
