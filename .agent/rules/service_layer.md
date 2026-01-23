---
trigger: always_on
---

# Service Layer Orchestration & Business Logic

## 1. Service Responsibilities (The Orchestration Layer)
*   **Business Logic**: Services contain ALL business rules, validation, and orchestration logic
*   **Repository Coordination**: Services coordinate multiple repositories for complex operations
*   **Transaction Boundaries**: Services define and manage transaction scope
*   **NO UI CODE**: Services MUST NOT import or reference PyQt widgets (signals/slots are OK)
*   **NO SQL**: Services NEVER write SQL queries - delegate to repositories

## 2. Service Architecture Patterns

### Single Responsibility
Each service should manage ONE domain:
*   `LibraryService` - Song CRUD, library operations
*   `MetadataService` - ID3 tag reading/writing
*   `PlaybackService` - Audio playback control
*   `ImportService` - File import orchestration
*   `ExportService` - File export operations

### Dependency Injection
Services receive dependencies via constructor:
```python
class LibraryService:
    def __init__(
        self,
        song_repo: SongRepository,
        artist_repo: ArtistRepository,
        metadata_service: MetadataService
    ):
        self._song_repo = song_repo
        self._artist_repo = artist_repo
        self._metadata = metadata_service
```

## 3. Method Design Principles

### Input Validation
Validate ALL inputs before processing:
```python
def update_song_title(self, song_id: int, new_title: str) -> bool:
    # Validate inputs
    if not new_title or not new_title.strip():
        raise ValueError("Title cannot be empty")
    if len(new_title) > 255:
        raise ValueError("Title too long (max 255 characters)")

    # Business logic
    song = self._song_repo.get_by_id(song_id)
    if not song:
        raise SongNotFoundError(f"Song {song_id} not found")

    # Execute operation
    song.title = new_title.strip()
    return self._song_repo.update(song)
```

### Return Types
*   **Success/Failure**: Return `bool` for operations that can only succeed or fail
*   **Entity Results**: Return domain objects (Song, Artist) or `None` if not found
*   **Lists**: Return `List[T]`, never `None` (return empty list instead)
*   **Complex Results**: Use dataclasses for multi-value returns
    ```python
    @dataclass
    class ImportResult:
        success: bool
        imported_count: int
        failed_files: List[str]
        errors: List[str]
    ```

### Error Handling
*   **Domain Exceptions**: Create specific exceptions for business rule violations
    ```python
    class DuplicateSongError(Exception):
        pass

    class InvalidMetadataError(Exception):
        pass
    ```
*   **Propagate Database Errors**: Let repository errors bubble up, or wrap in domain exceptions
*   **Never Swallow Exceptions**: Always log and re-raise or return error result

## 4. Transaction Management Patterns

### Atomic Operations
Wrap multi-step operations in transactions:
```python
def merge_artists(self, source_id: int, target_id: int) -> bool:
    """Merge source artist into target, moving all songs"""
    cursor = self._db.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")

        # 1. Move all songs
        self._song_repo.update_artist(source_id, target_id, cursor)

        # 2. Move aliases
        self._alias_repo.reassign(source_id, target_id, cursor)

        # 3. Delete source artist
        self._artist_repo.delete(source_id, cursor)

        cursor.execute("COMMIT")
        return True
    except Exception as e:
        cursor.execute("ROLLBACK")
        logger.error(f"Artist merge failed: {e}")
        raise
```

### Compensation Logic
For operations that can't be rolled back (external APIs, file operations):
```python
def import_with_metadata_fetch(self, file_path: str) -> ImportResult:
    """Import file and fetch metadata from external API"""
    song_id = None
    try:
        # 1. Import file (can rollback)
        song_id = self._import_file(file_path)

        # 2. Fetch metadata (external - can't rollback)
        metadata = self._fetch_external_metadata(song_id)

        # 3. Update song (can rollback)
        self._update_song_metadata(song_id, metadata)

        return ImportResult(success=True, song_id=song_id)
    except Exception as e:
        # Compensate: Delete partially imported song
        if song_id:
            self._song_repo.delete(song_id)
        return ImportResult(success=False, error=str(e))
```

## 5. Signal-Based Communication

### Signals for State Changes
Emit signals when state changes occur (UI can listen):
```python
from PyQt6.QtCore import QObject, pyqtSignal

class LibraryService(QObject):
    song_added = pyqtSignal(int)  # song_id
    song_updated = pyqtSignal(int)  # song_id
    song_deleted = pyqtSignal(int)  # song_id
    library_reloaded = pyqtSignal()

    def add_song(self, song: Song) -> int:
        song_id = self._song_repo.insert(song)
        self.song_added.emit(song_id)
        return song_id
```

### Signal Naming Conventions
*   Past tense for completed actions: `songAdded`, `artistDeleted`
*   Present tense for requests: `saveRequested`, `exportRequested`
*   Changed suffix for property updates: `filterChanged`, `selectionChanged`

## 6. Caching & State Management

### When to Cache
*   **Static Reference Data**: Types, roles, constants
*   **Expensive Computations**: Aggregations, statistics
*   **External API Results**: Metadata lookups, web services

### Cache Invalidation
```python
class LibraryService:
    def __init__(self):
        self._artist_cache: Dict[int, Artist] = {}

    def get_artist(self, artist_id: int) -> Artist:
        if artist_id not in self._artist_cache:
            self._artist_cache[artist_id] = self._artist_repo.get_by_id(artist_id)
        return self._artist_cache[artist_id]

    def update_artist(self, artist: Artist) -> bool:
        success = self._artist_repo.update(artist)
        if success:
            # Invalidate cache
            self._artist_cache.pop(artist.id, None)
        return success
```

### State Pattern
For services with complex state (playback, import):
```python
class PlaybackService:
    class State(Enum):
        STOPPED = "stopped"
        PLAYING = "playing"
        PAUSED = "paused"

    def __init__(self):
        self._state = PlaybackService.State.STOPPED

    def play(self):
        if self._state == PlaybackService.State.PLAYING:
            return  # Already playing
        # ...
        self._state = PlaybackService.State.PLAYING
```

## 7. Service Testing

### Mock Dependencies
Use mocks for repository dependencies:
```python
def test_add_song():
    mock_repo = Mock(spec=SongRepository)
    mock_repo.insert.return_value = 42

    service = LibraryService(song_repo=mock_repo)
    song_id = service.add_song(Song(...))

    assert song_id == 42
    mock_repo.insert.assert_called_once()
```

### Test Business Logic
Focus on business rules, not infrastructure:
```python
def test_cannot_merge_artist_into_self():
    service = LibraryService(...)
    with pytest.raises(ValueError, match="Cannot merge artist into itself"):
        service.merge_artists(source_id=123, target_id=123)
```

### Test Transactions
Verify rollback on error:
```python
def test_merge_rollback_on_error():
    # Setup: Repository that fails on delete
    mock_repo = Mock()
    mock_repo.delete.side_effect = DatabaseError("Delete failed")

    service = LibraryService(artist_repo=mock_repo)

    with pytest.raises(DatabaseError):
        service.merge_artists(1, 2)

    # Verify: No partial state changes
```

## 8. Service Anti-Patterns to Avoid

### ❌ Anemic Services
Don't create services that just forward to repositories:
```python
# BAD
class SongService:
    def get_song(self, song_id: int) -> Song:
        return self._repo.get_by_id(song_id)  # No value added
```

### ❌ God Services
Don't create services that do everything:
```python
# BAD
class LibraryService:
    def add_song(self): ...
    def play_audio(self): ...  # Should be PlaybackService
    def export_to_csv(self): ...  # Should be ExportService
    def fetch_from_spotify(self): ...  # Should be MetadataService
```

### ❌ Service-to-Service Circular Dependencies
```python
# BAD
class LibraryService:
    def __init__(self, metadata_service: MetadataService):
        self._metadata = metadata_service

class MetadataService:
    def __init__(self, library_service: LibraryService):  # CIRCULAR!
        self._library = library_service
```
**Fix**: Extract shared logic to a new service, or use events/signals

### ❌ Storing Widget References
```python
# BAD
class LibraryService:
    def set_table_widget(self, table: QTableWidget):
        self._table = table  # NEVER do this!
```

## 9. Logging & Observability

### Log Key Operations
```python
import logging
logger = logging.getLogger(__name__)

def merge_artists(self, source_id: int, target_id: int) -> bool:
    logger.info(f"Merging artist {source_id} into {target_id}")
    try:
        # ... operation
        logger.info(f"Successfully merged artists")
        return True
    except Exception as e:
        logger.error(f"Artist merge failed: {e}", exc_info=True)
        raise
```

### Performance Tracking
```python
import time

def expensive_operation(self):
    start = time.time()
    # ... operation
    duration = time.time() - start
    logger.debug(f"Operation completed in {duration:.2f}s")
```

## 10. Async Operations (Future Consideration)

For long-running operations, consider async pattern:
```python
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class ImportService(QObject):
    progress = pyqtSignal(int)  # Progress percentage
    completed = pyqtSignal(object)  # ImportResult
    error = pyqtSignal(str)

    def import_async(self, files: List[str]):
        """Run import in background thread"""
        worker = ImportWorker(files, self._song_repo)
        worker.progress.connect(self.progress)
        worker.completed.connect(self.completed)
        # ... setup thread
```
## 11. Facade Integrity (The Orchestrator Rule)
*   **Completeness**: Facade services (e.g., `ContributorService`) MUST expose all necessary operations from their underlying domain services (`IdentityService`, `ArtistNameService`) if the UI requires them.
*   **Delegation**: Always prefer delegating to an existing domain service method over re-implementing logic in the facade.
*   **Consistency**: Ensure method signatures in the facade align with the domain service to maintain predictable behavior.
