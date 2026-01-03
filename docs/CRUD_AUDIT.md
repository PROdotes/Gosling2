# 🔍 CRUD Audit & Consolidation Plan

This document identifies all data access points in the application to prepare for the generic repository refactor.

## 1. Existing Repositories
The following classes currently handle data persistence. They should be refactored to inherit from `GenericRepository`.

*   **`SongRepository`** (`src/data/repositories/song_repository.py`)
    *   Handles `Songs`, `MediaSources`, and bulk linking.
    *   *Complex*: Contains many legacy named queries.
*   **`ContributorRepository`** (`src/data/repositories/contributor_repository.py`)
    *   Handles `Contributors` (Artists) and identity resolution.
*   **`AlbumRepository`** (`src/data/repositories/album_repository.py`)
    *   Handles `Albums` and song-album linking.
*   **`PublisherRepository`** (`src/data/repositories/publisher_repository.py`)
    *   Simple CRUD for `Publishers`.
*   **`TagRepository`** (`src/data/repositories/tag_repository.py`)
    *   Handles `Tags` and `MediaSourceTags`.

## 2. 🚨 Architecture Violations (Loose SQL)
The following files execute raw SQL queries outside of the Repository layer. These **MUST** be moved to Repositories.

### A. Presentation Layer Violations
*   **`src/presentation/widgets/filter_widget.py`**
    *   executes `SELECT DISTINCT ContributorName...` (Lines 462, 505, 552).
    *   **Goal**: Move these optimized queries to `SongRepository` or `LibraryService` (which calls Repo).

### B. Service Layer Violations
*   **`src/business/services/library_service.py`**
    *   executes `SELECT DISTINCT...` in `get_distinct_filter_values`.
    *   **Goal**: Move to `SongRepository`.

## 3. Common CRUD Patterns
We see repeated patterns that `GenericRepository` can solve:

1.  **Get All**: `SELECT * FROM table ORDER BY ...`
2.  **Get By ID**: `SELECT * FROM table WHERE id = ?`
3.  **Insert**: `INSERT INTO table (...) VALUES (...) RETURNING id`
4.  **Update**: `UPDATE table SET ... WHERE id = ?`
5.  **Delete**: `DELETE FROM table WHERE id = ?`
6.  **Exists**: `SELECT 1 FROM table WHERE ... LIMIT 1`

## 4. Proposed Generic Interface

```python
class GenericRepository(ABC, Generic[T]):
    def __init__(self, connection, table_name: str, id_column: str, model_class: Type[T]):
        ...

    def get_all(self) -> List[T]: ...
    def get_by_id(self, id: int) -> Optional[T]: ...
    def insert(self, entity: T) -> int: ...
    def update(self, entity: T) -> bool: ...
    def delete(self, id: int) -> bool: ...
```

## 5. Audit Log Integration (T-05)
By consolidating all `insert` and `update` calls into `GenericRepository`, we can hook the Audit Log mechanism in **one place**.

```python
    def insert(self, entity: T) -> int:
        # ... perform insert ...
        self.audit_logger.log_insert(self.table_name, new_id, entity.to_dict())
        return new_id
```

This refactor is critical for ensuring that all data changes are tracked without manual instrumentation in every repository.
