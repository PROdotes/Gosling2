import datetime


class Logger:
    """Simple v3 bootstrap logger with file persistence."""

    def __init__(self, log_file="gosling.log"):
        self.log_file = log_file

    def _log(self, level: str, msg: str):
        timestamp = datetime.datetime.now().isoformat()
        line = f"{timestamp} [{level}] {msg}"
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

    def error(self, msg: str):
        self._log("ERROR", msg)

    def warning(self, msg: str):
        self._log("WARNING", msg)


logger = Logger()
