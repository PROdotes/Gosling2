import datetime
import os
import sys
from typing import Optional, TextIO


class Logger:
    """Simple v3 bootstrap logger with file persistence and level filtering."""

    # ---------------------------------------------------------------------------
    # GOSLING2 LOGGING STANDARD
    # ---------------------------------------------------------------------------
    #
    # LEVEL SEMANTICS
    #
    #   DEBUG    Internal plumbing — method entry/exit, query results, counts,
    #            branching decisions. Only useful while actively debugging.
    #            If you'd remove it in production, it's DEBUG.
    #
    #   INFO     Business state changes — anything that mutates data or produces
    #            a meaningful artifact. Song ingested, tag linked, file moved,
    #            entity soft-deleted, bulk import completed.
    #            If it changes the DB or filesystem, it's INFO.
    #
    #   WARNING  Unexpected but recoverable — precondition failures, fallbacks.
    #            NOT_FOUND on an update/delete (expected entity is missing),
    #            rules file missing (using defaults), ambiguous match resolved.
    #            The operation continues, but something was off.
    #
    #   ERROR    Operation failed and was aborted — exception in a catch block,
    #            FK violation, file I/O failure, validation rejection.
    #            Something the user or caller needs to know about.
    #
    #   CRITICAL Application cannot continue — DB unreachable, config invalid.
    #            Reserved for bootstrapping / startup failures only.
    #
    #
    # MESSAGE FORMAT
    #
    #   Method entry:    [ClassName] -> method(key=args)
    #   Method exit:     [ClassName] <- method() result_or_count
    #   Business event:  [ClassName] ENTITY_CREATED id=N 'name'
    #   Error:           [ClassName] method FAILED: {exception}
    #   Warning:         [ClassName] method NOT_FOUND id=N
    #
    #   Rules:
    #     - Always prefix with [ClassName].
    #     - Entry uses ->  Exit uses <-
    #     - Every method that logs entry MUST log exit (including error paths).
    #     - Never log at INFO unless something changed (no "checked X, found Y").
    #     - Never log raw SQL; log the semantic intent instead.
    #     - Include identifying data (id, name) in every message.
    #
    #
    # PER-CLASS EXPECTATIONS
    #
    #   Repository layer (src/data/):
    #     DEBUG  entry/exit on every public method
    #     INFO   write operations (insert, link, soft-delete, reactivate)
    #     ERROR  catch blocks with exception detail
    #
    #   Service layer (src/services/):
    #     DEBUG  entry/exit on orchestrating methods
    #     INFO   every successful mutation (the service is the audit trail)
    #     ERROR  catch blocks; include the upstream method name
    #
    #   Router layer (src/engine/routers/):
    #     DEBUG  entry with request params
    #     ERROR  unhandled exceptions (most should be caught by services)
    #     INFO   not normally used (services log the business events)
    #
    # ---------------------------------------------------------------------------

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
        env_level = os.getenv("GOSLING_LOG_LEVEL", "DEBUG").upper()
        self.current_level = self.LEVELS.get(env_level, 20)
        self.console_enabled = os.getenv("GOSLING_LOG_CONSOLE", "on").lower() != "off"
        self.file_enabled = os.getenv("GOSLING_LOG_FILE", "on").lower() != "off"
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

        if self.console_enabled:
            print(line)

        if self.file_enabled:
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
