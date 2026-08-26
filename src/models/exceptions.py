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
        notes: str = None,
    ):
        self.ghost_id = ghost_id
        self.title = title
        self.duration_s = duration_s
        self.year = year
        self.isrc = isrc
        self.notes = notes
        # User requested specific message format
        message = f"song with that hash already exists, {title}, {duration_s}"
        super().__init__(message, status_code=409)


class MergeRequiredError(Exception):
    """Raised when a rename collides with an existing entity and the user must confirm a merge."""

    def __init__(self, entity_type: str, collision_id: int):
        self.entity_type = entity_type
        self.collision_id = collision_id
        super().__init__(f"Merge required: {entity_type} {collision_id}")


class DuplicateConflictError(IngestionError):
    """Error raised when a file matches an ACTIVE record."""

    def __init__(self, existing_id: int, title: str):
        self.existing_id = existing_id
        self.title = title
        message = f"Song already exists in library: {title} (ID: {existing_id})"
        super().__init__(message, status_code=409)


class AuditIntegrityError(RuntimeError):
    """Raised when ChangeLog holds rows with NULL batch_id, meaning a write path
    bypassed write_connection(). Writes stay locked until it is resolved.

    Subclasses RuntimeError so existing handlers keep their current behaviour."""

    def __init__(self, null_batch_rows: int):
        self.null_batch_rows = null_batch_rows
        super().__init__(
            f"Audit integrity violation: {null_batch_rows} ChangeLog rows committed "
            f"with NULL batch_id. A write path bypassed write_connection(). "
            f"Fix before continuing."
        )
