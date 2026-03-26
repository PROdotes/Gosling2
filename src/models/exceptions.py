

class IngestionError(Exception):
    """Base class for all ingestion-related errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ReingestionConflictError(IngestionError):
    """
    Error raised when a file matches a soft-deleted record.
    Carries the metadata needed for the frontend's comparison popup.
    """

    def __init__(
        self,
        ghost_id: int,
        title: str,
        duration_s: float,
        year: int = None,
        isrc: str = None,
    ):
        self.ghost_id = ghost_id
        self.title = title
        self.duration_s = duration_s
        self.year = year
        self.isrc = isrc
        # User requested specific message format
        message = f"song with that hash already exists, {title}, {duration_s}"
        super().__init__(message, status_code=409)


class DuplicateConflictError(IngestionError):
    """Error raised when a file matches an ACTIVE record."""

    def __init__(self, existing_id: int, title: str):
        self.existing_id = existing_id
        self.title = title
        message = f"Song already exists in library: {title} (ID: {existing_id})"
        super().__init__(message, status_code=409)
