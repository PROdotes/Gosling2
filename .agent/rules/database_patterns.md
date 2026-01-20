---
trigger: always_on
---

# Database & Repository Patterns

## 1. Repository Responsibilities (The Sacred Contract)
*   **CRUD Only**: Repositories handle Create, Read, Update, Delete operations. NO business logic.
*   **Single Entity**: Each repository manages ONE entity type (Song, Artist, Album, etc.)
*   **SQL Containment**: ALL SQL queries MUST live in repositories. NEVER in services or UI.
*   **Return DTOs**: Return dataclass instances (Song, Contributor), not raw tuples or dicts

## 2. Transaction Management
*   **Service Layer Owns Transactions**: Services decide transaction boundaries, not repositories
*   **Context Manager Pattern**: Use `with db.cursor() as cursor:` for automatic cleanup
*   **Rollback Strategy**:
    ```python
    try:
        cursor.execute("BEGIN TRANSACTION")
        # Multiple repository calls
        cursor.execute("COMMIT")
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise
    ```
*   **Read-Only Queries**: Do NOT use transactions for simple SELECT queries

## 3. SQL Best Practices
*   **Parameterized Queries**: ALWAYS use `?` placeholders, NEVER string concatenation
    ```python
    # GOOD
    cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))

    # BAD - SQL Injection Risk!
    cursor.execute(f"SELECT * FROM songs WHERE id = {song_id}")
    ```
*   **Column Whitelisting**: When building dynamic queries, validate column names against a whitelist
*   **JOIN Efficiency**:
    *   Use INNER JOIN for required relationships
    *   Use LEFT JOIN for optional relationships
    *   Avoid excessive joins (> 4 tables) - consider breaking into multiple queries
*   **Indexing**: Columns used in WHERE, JOIN, ORDER BY should be indexed

## 4. Repository Method Patterns
### Standard CRUD Methods
```python
class SongRepository:
    def get_by_id(self, song_id: int) -> Optional[Song]:
        """Fetch single entity by primary key"""

    def get_all(self) -> List[Song]:
        """Fetch all entities (use with caution for large tables)"""

    def find_by(self, **filters) -> List[Song]:
        """Fetch entities matching criteria"""

    def insert(self, song: Song) -> int:
        """Insert entity, return new ID"""

    def update(self, song: Song) -> bool:
        """Update entity, return success status"""

    def delete(self, song_id: int) -> bool:
        """Delete entity, return success status"""

    def exists(self, song_id: int) -> bool:
        """Check existence without loading full entity"""
```

### Specialized Query Methods
*   Name methods descriptively: `find_songs_by_artist()`, `get_duplicate_titles()`
*   Accept specific parameters, not generic dicts
*   Return typed results (List[Song], not List[Any])

## 5. Data Mapping (DTO Pattern)
*   **Row to Model**: Convert database rows to dataclass instances
    ```python
    def _row_to_song(self, row: sqlite3.Row) -> Song:
        return Song(
            id=row["id"],
            title=row["title"],
            artist_id=row["artist_id"],
            # ... map all fields
        )
    ```
*   **Model to Row**: Convert dataclass to SQL parameters
    ```python
    def _song_to_params(self, song: Song) -> tuple:
        return (
            song.title,
            song.artist_id,
            song.year,
            # ... all fields
        )
    ```

## 6. Handling Relationships
*   **Lazy Loading**: Return entity with IDs, let service layer fetch related entities if needed
    ```python
    # Repository returns Song with artist_id
    song = song_repo.get_by_id(123)
    # Service fetches artist separately if needed
    artist = artist_repo.get_by_id(song.artist_id)
    ```
*   **Eager Loading**: Provide separate methods that JOIN and return complete data
    ```python
    def get_song_with_artist(self, song_id: int) -> Tuple[Song, Artist]:
        """Fetch song and artist in one query"""
    ```
*   **Many-to-Many**: Use junction table repositories (e.g., `CreditRepository` for song-contributor)

## 7. Error Handling in Repositories
*   **Database Errors**: Catch and wrap in domain-specific exceptions
    ```python
    try:
        cursor.execute(query, params)
    except sqlite3.IntegrityError as e:
        raise DuplicateSongError(f"Song already exists: {e}")
    except sqlite3.Error as e:
        raise DatabaseError(f"Database operation failed: {e}")
    ```
*   **Not Found**: Return `None` or empty list, do NOT raise exceptions for missing data
*   **Constraint Violations**: Raise descriptive exceptions (DuplicateError, ForeignKeyError)

## 8. Database Schema Evolution
*   **Migration Scripts**: Store in `migrations/` directory, numbered sequentially
    ```
    migrations/
        001_initial_schema.sql
        002_add_publisher_table.sql
        003_add_album_index.sql
    ```
*   **Version Tracking**: Store schema version in database
    ```sql
    CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
    ```
*   **Backwards Compatibility**: Add columns with DEFAULT values, never drop columns without migration plan

## 9. Testing Repositories
*   **In-Memory Database**: Use `:memory:` for fast, isolated tests
    ```python
    @pytest.fixture
    def db():
        conn = sqlite3.connect(":memory:")
        # Load schema
        return conn
    ```
*   **Test Data Builders**: Create helper functions for common test data
*   **Test Transactions**: Verify rollback behavior
*   **Test Constraints**: Verify foreign keys, unique constraints work

## 10. Performance Guidelines
*   **Batch Operations**: Provide `insert_many()`, `update_many()` for bulk operations
    ```python
    def insert_many(self, songs: List[Song]) -> List[int]:
        cursor.executemany(INSERT_QUERY, [self._song_to_params(s) for s in songs])
    ```
*   **Pagination**: For large result sets, provide limit/offset parameters
    ```python
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Song]:
    ```
*   **COUNT Queries**: Provide separate count methods instead of `len(get_all())`
    ```python
    def count(self, **filters) -> int:
        """Return count without loading all rows"""
    ```
*   **Connection Pooling**: Reuse database connections, don't create per-query

## 11. SQLite-Specific Considerations
*   **Row Factory**: Use `sqlite3.Row` for dict-like access
    ```python
    conn.row_factory = sqlite3.Row
    ```
*   **Foreign Keys**: Enable explicitly (disabled by default in SQLite)
    ```python
    cursor.execute("PRAGMA foreign_keys = ON")
    ```
*   **Write-Ahead Logging**: Enable for better concurrency
    ```python
    cursor.execute("PRAGMA journal_mode = WAL")
    ```
*   **Type Affinity**: Be aware of SQLite's dynamic typing, use constraints
