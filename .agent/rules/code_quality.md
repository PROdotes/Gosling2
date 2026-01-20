---
trigger: always_on
---

# Code Quality & Clean Code Standards

## 1. Naming Conventions

### Variables & Functions
*   **Descriptive Over Concise**: `selected_song_ids` not `ids`
*   **Boolean Prefixes**: `is_valid`, `has_metadata`, `can_delete`, `should_update`
*   **Action Verbs for Functions**: `get_`, `fetch_`, `load_`, `save_`, `update_`, `delete_`, `create_`
*   **Private Methods**: Prefix with `_` (e.g., `_validate_input()`, `_init_ui()`)
*   **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`, `DEFAULT_TIMEOUT`)

### Classes
*   **Nouns for Entities**: `Song`, `Artist`, `Album`
*   **Service Suffix**: `LibraryService`, `MetadataService`
*   **Repository Suffix**: `SongRepository`, `ArtistRepository`
*   **Widget Suffix**: `LibraryWidget`, `FilterWidget`
*   **Dialog Suffix**: `ImportDialog`, `SettingsDialog`

### Files
*   **Match Class Name**: `library_service.py` contains `LibraryService`
*   **Utilities**: `{domain}_utils.py` (e.g., `string_utils.py`, `audio_utils.py`)
*   **Tests Mirror Source**: `src/data/song.py` → `tests/unit/data/test_song.py`

## 2. Function Design

### Single Responsibility
Each function should do ONE thing:
```python
# BAD - Does too much
def process_song(self, file_path: str) -> Song:
    song = self.parse_file(file_path)
    self.validate_metadata(song)
    song_id = self.save_to_database(song)
    self.update_ui(song_id)
    self.log_import(song_id)
    return song

# GOOD - Delegated responsibilities
def import_song(self, file_path: str) -> ImportResult:
    song = self._metadata_service.parse_file(file_path)
    self._validate(song)
    song_id = self._song_repo.insert(song)
    return ImportResult(success=True, song_id=song_id)
```

### Parameter Count
*   **Max 4 Parameters**: If more needed, use a dataclass or dict
    ```python
    # BAD
    def create_song(self, title, artist, year, genre, bpm, key, isrc):
        pass

    # GOOD
    @dataclass
    class SongData:
        title: str
        artist: str
        year: Optional[int] = None
        genre: Optional[str] = None
        # ...

    def create_song(self, data: SongData) -> Song:
        pass
    ```

### Function Length
*   **Max 50 Lines**: If longer, extract helper methods
*   **Early Returns**: Avoid deep nesting with guard clauses
    ```python
    # BAD
    def process(self, song_id: int):
        song = self.get_song(song_id)
        if song:
            if song.is_valid():
                if self.can_update(song):
                    self.update(song)

    # GOOD
    def process(self, song_id: int):
        song = self.get_song(song_id)
        if not song:
            return
        if not song.is_valid():
            return
        if not self.can_update(song):
            return
        self.update(song)
    ```

## 3. Class Design

### Cohesion
All methods should relate to the class's purpose:
```python
# BAD
class SongRepository:
    def get_song(self): ...
    def format_datetime(self): ...  # Unrelated - move to utils
    def send_email(self): ...  # Unrelated - move to EmailService
```

### Encapsulation
*   **Hide Implementation**: Make attributes private, expose via methods/properties
    ```python
    class Song:
        def __init__(self, title: str):
            self._title = title  # Private

        @property
        def title(self) -> str:
            return self._title

        @title.setter
        def title(self, value: str):
            if not value.strip():
                raise ValueError("Title cannot be empty")
            self._title = value.strip()
    ```

### Composition Over Inheritance
Prefer composition except for clear IS-A relationships:
```python
# BAD
class SongWithMetadata(Song):  # Song IS-NOT-A metadata
    def __init__(self):
        super().__init__()
        self.metadata = {}

# GOOD
class Song:
    def __init__(self):
        self._metadata_service = MetadataService()  # HAS-A
```

## 4. Error Handling

### Specific Exceptions
Catch specific exceptions, not bare `except:`:
```python
# BAD
try:
    song = self.parse_file(path)
except:  # Too broad!
    pass

# GOOD
try:
    song = self.parse_file(path)
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    raise
except PermissionError:
    logger.error(f"Permission denied: {path}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

### Error Messages
Provide actionable, descriptive error messages:
```python
# BAD
raise ValueError("Invalid input")

# GOOD
raise ValueError(f"Title '{title}' exceeds maximum length of {MAX_TITLE_LENGTH} characters")
```

### Fail Fast
Validate inputs at function entry:
```python
def update_song(self, song_id: int, title: str) -> bool:
    # Validate immediately
    if song_id <= 0:
        raise ValueError(f"Invalid song_id: {song_id}")
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")

    # Proceed with logic
    # ...
```

## 5. Comments & Documentation

### When to Comment
*   **Why, Not What**: Explain reasoning, not obvious code
    ```python
    # BAD
    # Increment counter
    counter += 1

    # GOOD
    # Skip ID3v1 tags as they lack extended metadata support
    if tag_version == 1:
        continue
    ```
*   **Complex Logic**: Algorithms, edge cases, workarounds
*   **Business Rules**: "Per FCC regulations, commercials must be tagged..."
*   **TODOs**: `# TODO: Implement caching for artist lookup`

### Docstrings
Use for public methods/classes:
```python
def merge_artists(self, source_id: int, target_id: int) -> bool:
    """
    Merge source artist into target artist.

    Moves all songs, aliases, and credits from source to target,
    then deletes the source artist. Operation is atomic.

    Args:
        source_id: Artist ID to merge from (will be deleted)
        target_id: Artist ID to merge into (will be kept)

    Returns:
        True if merge successful

    Raises:
        ValueError: If source_id == target_id
        DatabaseError: If transaction fails
    """
```

### Avoid Redundant Comments
```python
# BAD
# Get song by ID
def get_song_by_id(self, song_id: int):
    return self._repo.get_by_id(song_id)

# GOOD (no comment needed - method name is self-documenting)
def get_song_by_id(self, song_id: int):
    return self._repo.get_by_id(song_id)
```

## 6. Code Organization

### Import Order
1. Standard library
2. Third-party (PyQt6, mutagen)
3. Local application
```python
import os
import sys
from typing import List, Optional

from PyQt6.QtWidgets import QWidget
from mutagen.mp3 import MP3

from src.data.models import Song
from src.business.services import MetadataService
```

### File Structure
```python
# 1. Imports
# 2. Constants
# 3. Type aliases / Enums
# 4. Classes
# 5. Module-level functions
```

### Logical Grouping
Group related methods together:
```python
class SongRepository:
    # CRUD Operations
    def insert(self): ...
    def update(self): ...
    def delete(self): ...

    # Query Methods
    def get_by_id(self): ...
    def find_by_artist(self): ...

    # Helper Methods
    def _row_to_song(self): ...
    def _song_to_params(self): ...
```

## 7. Type Hints

### Use Type Hints Everywhere
```python
from typing import List, Optional, Dict, Tuple

def get_songs(
    self,
    artist_id: Optional[int] = None,
    limit: int = 100
) -> List[Song]:
    """Fetch songs with optional filtering"""
    pass
```

### Generic Types
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def get_by_id(self, id: int) -> Optional[T]:
        pass
```

## 8. Magic Numbers & Constants

### Extract to Constants
```python
# BAD
if len(title) > 255:
    raise ValueError("Title too long")

# GOOD
MAX_TITLE_LENGTH = 255

if len(title) > MAX_TITLE_LENGTH:
    raise ValueError(f"Title exceeds {MAX_TITLE_LENGTH} characters")
```

### Configuration
Store in dedicated file or settings:
```python
# constants.py
class LibraryConfig:
    MAX_TITLE_LENGTH = 255
    DEFAULT_SAMPLE_RATE = 44100
    SUPPORTED_FORMATS = [".mp3", ".flac", ".wav"]
```

## 9. Testing Considerations

### Testable Code
*   **Avoid Singletons**: Hard to mock
*   **Inject Dependencies**: Don't hardcode `Database()` in constructor
*   **Avoid Static Methods**: Hard to mock
*   **Separate I/O from Logic**: Test logic without file system

### Test Naming
```python
def test_merge_artists_moves_all_songs():
    """Verify all songs are moved during artist merge"""

def test_merge_artists_with_same_id_raises_error():
    """Verify error when merging artist into itself"""
```

## 10. Performance Best Practices

### Lazy Loading
Don't load data until needed:
```python
# BAD
class LibraryWidget:
    def __init__(self):
        self.all_songs = self.load_all_songs()  # Loads on init

# GOOD
class LibraryWidget:
    def __init__(self):
        self._songs = None

    def get_songs(self):
        if self._songs is None:
            self._songs = self.load_all_songs()
        return self._songs
```

### Avoid Premature Optimization
*   Profile before optimizing
*   Optimize hot paths only
*   Readability > micro-optimizations

### Resource Cleanup
```python
# Use context managers
with open(file_path, 'r') as f:
    data = f.read()

# Or try/finally
cursor = db.cursor()
try:
    cursor.execute(query)
finally:
    cursor.close()
```

## 11. Code Smells to Avoid

### Long Parameter Lists
Use dataclasses or builder pattern

### Duplicate Code
Extract to shared function/class

### Large Classes (God Objects)
Split by responsibility (see 600-line rule)

### Feature Envy
If class A uses class B's data more than its own, move the method to B

### Inappropriate Intimacy
Don't access private members of other classes

### Shotgun Surgery
One change shouldn't require touching many files (indicates poor cohesion)

## 12. Version Control Hygiene

### Commit Messages
```
feat(library): Add batch song import with progress tracking

- Implement ImportWorker for background processing
- Add progress signals for UI updates
- Include rollback on partial failure

Closes #123
```

### Commit Size
*   One logical change per commit
*   Don't mix refactoring with features
*   Don't commit commented-out code

### Branch Naming
*   `feature/artist-merge`
*   `bugfix/playlist-crash`
*   `refactor/service-layer`
