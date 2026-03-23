# TDD & Testing Standard
**Purpose**: Prevent code regression and eliminate LLM assumptions by establishing bulletproof testing contracts.
**Philosophy**: Tests must be exhaustive and reflect physical reality. No room for defaults, guesses, or "reasonable assumptions" about missing data.
---

## Core Principles

### 1. No Mocking (Except When Impossible)
- Use **real test databases** (empty_db, populated_db, edge_case_db) for all repo/service tests
- No mocking repositories, models, or database connections
- Only mock when testing something that cannot be replicated (e.g., "disk full" scenarios)
- **Rationale**: Mocks hide bugs. Real databases catch SQL errors, type mismatches, and schema issues.

### 2. Exhaustive Assertions
- Assert **every field** of returned objects, not just key fields
- Prevents LLM assumptions like:
  - Defaulting to "Composer" when artist is missing
  - Defaulting to "Mood" when genre is missing
  - Setting duration to 0 when NULL
  - Using empty string instead of None for missing text
- **Example**:
  ```python
  song = repo.get_by_id(1)
  assert song.id == 1, f"Expected 1, got {song.id}"
  assert song.title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
  assert song.duration_ms == 200000, f"Expected 200000, got {song.duration_ms}"
  assert song.path == "/path/1", f"Expected '/path/1', got '{song.path}'"
  assert song.audio_hash == "hash_1", f"Expected 'hash_1', got '{song.audio_hash}'"
  assert song.recording_year == 1991, f"Expected 1991, got {song.recording_year}"
  assert song.is_active is True, f"Expected True, got {song.is_active}"
  assert song.processing_status is None, f"Expected None, got {song.processing_status}"
  assert song.credits == [], f"Repo doesn't hydrate, expected [], got {song.credits}"
  assert song.albums == [], f"Repo doesn't hydrate, expected [], got {song.albums}"
  ```

### 3. Assertion Messages
- Use format: `assert x == y, f"Expected {y}, got {x}"`
- Provides immediate context when tests fail
- Makes debugging easier for LLMs and humans

### 4. Test Organization
- **One test per scenario** with descriptive names
- Naming: `test_{method}_{scenario}_{expected_outcome}`
- Examples:
  - `test_get_by_id_existing_song_returns_complete_object`
  - `test_get_by_id_nonexistent_id_returns_none`
  - `test_get_by_ids_partial_results_skips_missing`

---

## Return Value Contracts

### Single-Item Methods
**Pattern**: `get_by_id(id: int) -> Optional[T]`
- Return `None` when not found
- Never return empty object or raise exception for "not found"
- **Example**:
  ```python
  song = repo.get_by_id(999)
  assert song is None, f"Expected None for nonexistent ID, got {song}"
  ```

### Collection Methods
**Pattern**: `search(query: str) -> Optional[List[T]]`
- Return `None` when result set is empty (refactoring from `[]` over time)
- Never return single item when multiple expected
- **Example**:
  ```python
  songs = repo.search("xyz_does_not_exist")
  assert songs is None, f"Expected None for empty results, got {songs}"
  ```

### Batch Methods
**Pattern**: `get_by_ids(ids: List[int]) -> List[T]`
- Return **only found items**, skip missing
- If requesting [1, 2, 999] and only 1, 2 exist → return 2 items
- Tests must verify count and all returned items
- **Example**:
  ```python
  songs = repo.get_by_ids([1, 2, 999])
  assert len(songs) == 2, f"Expected 2 found items, got {len(songs)}"
  # Assert all fields for songs[0]
  # Assert all fields for songs[1]
  ```

### Write Operations (Insert/Update/Delete)
**Pattern**: All write methods return the affected object or `True`/`False` for deletes

#### Insert
- Return the created object with database-assigned ID
- Tests should specify explicit IDs for predictability
- **Example**:
  ```python
  new_song = Song(id=100, title="New Song", duration_ms=150000, path="/new/path")
  created = repo.insert(new_song)
  assert created.id == 100, f"Expected ID 100, got {created.id}"
  assert created.title == "New Song", f"Expected 'New Song', got '{created.title}'"
  # ... assert all fields
  ```

#### Update
- Return the updated object
- Tests must verify changed field **AND** all other fields remain unchanged
- Prevents accidental field resets to NULL/defaults
- **Example**:
  ```python
  updated = repo.update_title(song_id=1, new_title="New Title")
  assert updated.id == 1, f"Expected ID 1, got {updated.id}"
  assert updated.title == "New Title", f"Expected 'New Title', got '{updated.title}'"
  # Assert ALL other fields match original values
  assert updated.duration_ms == 200000, f"Duration should not change, got {updated.duration_ms}"
  assert updated.path == "/path/1", f"Path should not change, got '{updated.path}'"
  # ... all fields
  ```

#### Delete
- Hard deletes only (`IsActive` is unrelated to deletion)
- Return `True` if deleted, `False` if not found
- Tests must verify cascade effects explicitly
- **Example**:
  ```python
  result = repo.delete(song_id=1)
  assert result is True, f"Expected True (deleted), got {result}"

  # Verify song is gone
  song = repo.get_by_id(1)
  assert song is None, f"Expected None (deleted), got {song}"

  # Verify cascades (credits deleted)
  credits = credit_repo.get_credits_for_songs([1])
  assert len(credits) == 0, f"Expected 0 credits after delete, got {len(credits)}"

  # Verify preservation (album not deleted)
  album = album_repo.get_by_id(100)
  assert album is not None, f"Album should not be deleted when song is removed"
  assert album.title == "Nevermind", f"Expected 'Nevermind', got '{album.title}'"
  ```

### NULL/Missing Fields
- Use `None` as default for unset/missing fields (refactoring from empty strings/0 over time)
- Tests must explicitly assert `None` for nullable fields
- **Example**:
  ```python
  assert song.audio_hash is None, f"Expected None for missing hash, got {song.audio_hash}"
  assert song.recording_year is None, f"Expected None for missing year, got {song.recording_year}"
  ```

---

## Test Coverage Strategy

### Repository Layer
**What to test**:
- All public methods (`get_by_id`, `get_by_ids`, `search`, etc.)
- All internal `_row_to_*()` mapper methods directly

**Why test mappers directly**:
- High bug risk: type coercion, NULL handling, unit conversions, field name mismatches
- Example bugs mappers prevent:
  - Duration in seconds → milliseconds conversion errors
  - SQLite boolean (0/1) → Python bool casting
  - NULL fields defaulting to 0/"Unknown" instead of None
  - Wrong column names in row access

**Mapper test approach**:
- Use dict mocks (Pydantic catches type errors)
- Assert all fields including NULL handling
- **Example**:
  ```python
  class TestRowToSong:
      def test_all_fields_present(self, populated_db):
          mock_row = {
              'SourceID': 1,
              'MediaName': 'Test Song',
              'SourceDuration': 200,  # seconds in DB
              'SourcePath': '/path/test',
              'AudioHash': 'hash123',
              'IsActive': 1,
              'RecordingYear': 2024,
              'ProcessingStatus': None
          }
          repo = SongRepository(populated_db)
          song = repo._row_to_song(mock_row)
          assert song.id == 1, f"Expected 1, got {song.id}"
          assert song.title == "Test Song", f"Expected 'Test Song', got '{song.title}'"
          assert song.duration_ms == 200000, f"Expected 200000ms (converted), got {song.duration_ms}"
          assert song.path == "/path/test", f"Expected '/path/test', got '{song.path}'"
          assert song.audio_hash == "hash123", f"Expected 'hash123', got '{song.audio_hash}'"
          assert song.is_active is True, f"Expected True (1→True), got {song.is_active}"
          assert song.recording_year == 2024, f"Expected 2024, got {song.recording_year}"
          assert song.processing_status is None, f"Expected None, got {song.processing_status}"

      def test_null_fields(self, populated_db):
          mock_row = {
              'SourceID': 4,
              'MediaName': 'Song With Nulls',
              'SourceDuration': 120,
              'SourcePath': '/path/4',
              'AudioHash': None,  # NULL
              'IsActive': 1,
              'RecordingYear': None,  # NULL
              'ProcessingStatus': None
          }
          repo = SongRepository(populated_db)
          song = repo._row_to_song(mock_row)
          assert song.id == 4, f"Expected 4, got {song.id}"
          assert song.audio_hash is None, f"Expected None for NULL hash, got {song.audio_hash}"
          assert song.recording_year is None, f"Expected None for NULL year, got {song.recording_year}"
  ```

### Service Layer
**What to test**:
- Public orchestration methods
- Data merge/hydration logic
- Transformation logic

**When to test**:
- If method only calls one repo method with no transformation → **no test needed**
- If method merges data from multiple repos → **test the merge**
- If method transforms data → **test inputs and outputs exhaustively**

**Example** (merge test):
```python
class TestGetSong:
    def test_returns_song_with_credits_and_albums(self, populated_db):
        service = CatalogService(populated_db)
        song = service.get_song(1)

        # Core song fields
        assert song.id == 1, f"Expected 1, got {song.id}"
        assert song.title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
        # ... all song fields

        # Hydrated credits
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"
        assert song.credits[0].name == "Nirvana", f"Expected 'Nirvana', got '{song.credits[0].name}'"
        assert song.credits[0].role == "Performer", f"Expected 'Performer', got '{song.credits[0].role}'"
        # ... all credit fields

        # Hydrated albums
        assert len(song.albums) == 1, f"Expected 1 album, got {len(song.albums)}"
        assert song.albums[0].title == "Nevermind", f"Expected 'Nevermind', got '{song.albums[0].title}'"
        assert song.albums[0].track == 1, f"Expected track 1, got {song.albums[0].track}"
        # ... all album fields
```

### API/Router Layer
**What to test**:
- HTTP status codes for all scenarios (200, 400, 404, 422, 500)
- Request/response serialization
- Complete response shape (exhaustive field validation)

**Use FastAPI TestClient** with real databases:
```python
@pytest.fixture
def client(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)

class TestGetSong:
    def test_existing_song_returns_200_with_complete_data(self, client):
        resp = client.get("/api/v1/catalog/songs/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        data = resp.json()
        assert data["id"] == 1, f"Expected ID 1, got {data['id']}"
        assert data["title"] == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{data['title']}'"
        assert data["duration_ms"] == 200000, f"Expected 200000, got {data['duration_ms']}"
        # ... all song fields

        assert "credits" in data, "Response missing 'credits' field"
        assert len(data["credits"]) == 1, f"Expected 1 credit, got {len(data['credits'])}"
        # ... all credit fields

    def test_nonexistent_song_returns_404(self, client):
        resp = client.get("/api/v1/catalog/songs/999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        data = resp.json()
        assert "detail" in data, "Error response missing 'detail' field"

    def test_invalid_id_returns_422(self, client):
        resp = client.get("/api/v1/catalog/songs/not_an_int")
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
```

**Rationale**: Prevents status code confusion (returning 404 when 400 is correct, etc.)

---

## Edge Case Testing

### When to Test Edge Cases
- Only test edge cases where the method's logic could create **new** edge cases
- If sub-methods already handle edge cases, rely on their tests
- Use `edge_case_db` fixture for:
  - Orphaned references (publisher parent ID 999 doesn't exist)
  - Circular relationships (group A → group B → group A)
  - Identities with no primary name
  - Zero/NULL values
  - Unicode characters
  - Whitespace-only strings

### Example
```python
class TestGetById:
    def test_unicode_title_handled_correctly(self, edge_case_db):
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(103)
        assert song.id == 103, f"Expected 103, got {song.id}"
        assert song.title == "日本語ソング", f"Expected '日本語ソング', got '{song.title}'"
        # ... all fields
```

---

## Test Database Fixtures

### Available Fixtures (from conftest.py)
- **empty_db**: Schema only, no data. For negative/empty tests.
- **populated_db**: Rich "Dave Grohl" scenario with known exact values (see conftest.py comments for data map).
- **edge_case_db**: Orphans, NULLs, unicode, circular references, boundary values.

### Database Selection
- Use whichever fixture makes sense for the scenario
- Don't force every method through all three databases
- **Examples**:
  - `get_by_id(999)` on `populated_db` (nonexistent ID)
  - `get_all()` on `empty_db` (returns None)
  - Unicode titles from `edge_case_db`

### Test Data Values
- Use hard-coded values in assertions (not constants)
- Fixture comments in conftest.py document exact values
- **Example**: Song 1 is "Smells Like Teen Spirit", 200s → 200000ms, credited to Nirvana

### Related-but-Distinct Fixture Rule
**Critical**: Fixtures must contain entities with overlapping/similar names to catch precision bugs.

Tests should prioritize `edge_case_db` or a "messy" `populated_db` that includes:
- **Near-matches**: "Nirvana" vs "The Nirvana" vs "Nirvanatics"
- **Substring overlaps**: "Foo" vs "Foo Fighters" vs "Kung Foo"
- **Case variations**: "NIRVANA" vs "Nirvana" vs "nirvana"
- **Unicode lookalikes**: "Björk" vs "Bjork"

**Rationale**: Proves the code handles high-precision discrimination, not just broad LIKE queries.

**Example Addition to `edge_case_db`**:
```python
# In conftest.py _populate_edge_case_data()
# Add artists with overlapping names
cursor.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (200, 'group')")  # "Nirvana"
cursor.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (201, 'group')")  # "The Nirvana"
cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName) VALUES (500, 200, 'Nirvana')")
cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName) VALUES (501, 201, 'The Nirvana')")
```

Then tests verify:
```python
def test_search_nirvana_exact_excludes_the_nirvana(self, edge_case_db):
    results = service.search_identities("Nirvana")
    assert len(results) == 1, f"Expected 1 exact match, got {len(results)}"
    assert results[0].display_name == "Nirvana", f"Expected 'Nirvana', got '{results[0].display_name}'"
    # Verify "The Nirvana" is NOT included
    names = [r.display_name for r in results]
    assert "The Nirvana" not in names, "'The Nirvana' should not match 'Nirvana' search"
```

---

## Collection Testing

### Exhaustive Assertions on Every Item
When a method returns a list, assert all fields for every item (typically 1-5 items):

```python
class TestGetByIds:
    def test_multiple_songs_returns_all_fields(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 2, 3])
        assert len(songs) == 3, f"Expected 3 songs, got {len(songs)}"

        # Song 1
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert songs[0].title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        assert songs[0].duration_ms == 200000, f"Expected 200000, got {songs[0].duration_ms}"
        # ... all fields for song 1

        # Song 2
        assert songs[1].id == 2, f"Expected 2, got {songs[1].id}"
        assert songs[1].title == "Everlong", f"Expected 'Everlong', got '{songs[1].title}'"
        assert songs[1].duration_ms == 240000, f"Expected 240000, got {songs[1].duration_ms}"
        # ... all fields for song 2

        # Song 3
        assert songs[2].id == 3, f"Expected 3, got {songs[2].id}"
        assert songs[2].title == "Range Rover Bitch", f"Expected 'Range Rover Bitch', got '{songs[2].title}'"
        assert songs[2].duration_ms == 180000, f"Expected 180000, got {songs[2].duration_ms}"
        # ... all fields for song 3
```

### Negative Isolation: Explicitly Exclude Unrelated Entities
**Critical**: Tests must prove that the query returns ONLY the requested data, not extra "haystack" entities.

When searching/filtering, explicitly assert that unrelated entities in the fixture are **excluded**:

```python
class TestSearch:
    def test_search_nirvana_excludes_foo_fighters(self, populated_db):
        repo = SongRepository(populated_db)
        songs = service.search_songs("Nirvana")

        # Positive: Find expected results
        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected song 1, got {songs[0].id}"
        assert songs[0].title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        # ... all fields

        # Negative: Explicitly verify exclusions
        returned_ids = [s.id for s in songs]
        assert 2 not in returned_ids, "Song 2 (Everlong by Foo Fighters) should NOT be in Nirvana search results"
        assert 3 not in returned_ids, "Song 3 (Range Rover Bitch) should NOT be in Nirvana search results"
```

**Rationale**: Catches bugs where:
- LIKE queries are too broad (`%Nir%` matches "Nirvana" and "The Nirvanatics")
- JOINs pull in extra rows
- Filters fail to apply WHERE clauses correctly

**Rule**: If the fixture contains N similar entities, test must verify that N-1 are excluded.

---

## Error Handling

### Current Contract (Do Not Change Without Updating Tests)
- **Not found**: Return `None` (single items) or `None` (empty collections)
- **Missing data**: Return `None` for nullable fields, never default to "Unknown"/0/empty string
- **Validation errors**: Let Pydantic raise `ValidationError` at model construction
- **Database errors**: Let exceptions bubble (connection failures, SQL errors)

### No Exception Handling for "Not Found"
- Methods should NOT raise exceptions for missing records
- Use return value (`None`) to indicate absence
- Only raise exceptions for actual errors (DB connection, SQL syntax, etc.)

---

## File Organization

### Directory Structure
Mirror source structure for easy navigation:

```
tests/
  conftest.py           # Fixtures (empty_db, populated_db, edge_case_db)
  test_data/            # Repository tests
    test_song_repository.py
    test_identity_repository.py
    test_publisher_repository.py
    test_album_repository.py
  test_services/        # Service tests
    test_catalog_service.py
    test_metadata_service.py
    test_audit_service.py
  test_api/             # API/Router tests
    test_catalog_api.py
    test_ingestion_api.py
```

### Test Class Organization
One class per method being tested:

```python
# test_song_repository.py

class TestGetById:
    def test_existing_song_returns_complete_object(self, populated_db):
        # ...

    def test_nonexistent_id_returns_none(self, populated_db):
        # ...

class TestGetByIds:
    def test_all_exist_returns_complete_list(self, populated_db):
        # ...

    def test_partial_results_skips_missing(self, populated_db):
        # ...

class TestRowToSong:
    def test_all_fields_present(self, populated_db):
        # ...

    def test_null_fields_map_to_none(self, populated_db):
        # ...
```

**Rationale**: When `TestGetById::test_nonexistent_id_returns_none` fails, immediately know:
- File: which repository/service
- Class: which method
- Test: which scenario

---

## Test Helpers

### Shared Assertion Functions
To reduce repetition for exhaustive checks, create helper functions:

```python
# In conftest.py or test file
def assert_song_1_complete(song: Song):
    """Assert all fields of Song 1 from populated_db."""
    assert song.id == 1, f"Expected 1, got {song.id}"
    assert song.title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
    assert song.duration_ms == 200000, f"Expected 200000, got {song.duration_ms}"
    assert song.path == "/path/1", f"Expected '/path/1', got '{song.path}'"
    assert song.audio_hash == "hash_1", f"Expected 'hash_1', got '{song.audio_hash}'"
    assert song.recording_year == 1991, f"Expected 1991, got {song.recording_year}"
    assert song.is_active is True, f"Expected True, got {song.is_active}"
    assert song.processing_status is None, f"Expected None, got {song.processing_status}"

# Usage
class TestGetById:
    def test_existing_song(self, populated_db):
        repo = SongRepository(populated_db)
        song = repo.get_by_id(1)
        assert_song_1_complete(song)
```

**Note**: If multiple tests fail using the same helper, the helper is likely at fault.

---

## Refactoring Guidelines

### Moving from `[]` to `None` for Empty Collections
- **Target**: Collection methods should return `None` when empty, not `[]`
- **Current**: Many methods return `[]`
- **Refactor gradually**: Update one method at a time, fixing tests afterward
- When refactoring:
  1. Update method implementation
  2. Update all tests for that method
  3. Update callers that check `if not result:` → `if result is None:`

### Moving from Empty String/0 to `None` for Missing Fields
- **Target**: NULL database values should map to `None`, not `""`/`0`
- **Refactor gradually**: Update `_row_to_*()` mappers one field at a time
- When refactoring:
  1. Update mapper to return `None` for NULL
  2. Update all tests asserting that field
  3. Update callers that check `if field:` → `if field is not None:`

---

## Anti-Patterns (Do NOT Do These)

### ❌ Mocking Repositories
```python
# BAD
@patch('src.data.song_repository.SongRepository.get_by_id')
def test_get_song(mock_get):
    mock_get.return_value = Song(id=1, title="Test")
    # ...
```

**Why**: Misses SQL errors, type mismatches, schema issues.

### ❌ Partial Assertions
```python
# BAD
song = repo.get_by_id(1)
assert song.id == 1
assert song.title == "Smells Like Teen Spirit"
# Missing: duration, path, year, etc.
```

**Why**: LLM might silently reset other fields to defaults.

### ❌ Assuming Defaults
```python
# BAD
assert song.audio_hash == "" or song.audio_hash is None
```

**Why**: Ambiguous. Should be explicit: `assert song.audio_hash is None`

### ❌ No Assertion Messages
```python
# BAD
assert song.duration_ms == 200000
```

**Why**: When it fails, you only see "AssertionError" with no context.

### ❌ Testing Multiple Scenarios in One Test
```python
# BAD
def test_get_by_id(self, populated_db):
    # Test existing
    song = repo.get_by_id(1)
    assert song is not None

    # Test nonexistent
    song = repo.get_by_id(999)
    assert song is None
```

**Why**: If first assertion fails, second never runs. Harder to identify which scenario broke.

---

## TDD Refactor Protocol

### Red → Green → Refactor Cycle
TDD follows: **Red** (write failing test) → **Green** (make it pass) → **Refactor** (clean up).

During the **Green** phase, LLMs often add "vibe-coding" to get tests passing:
- Speculative `try/except` blocks "just in case"
- Defensive type checks that can never trigger (e.g., checking `if isinstance(x, int)` when Pydantic already validates)
- Redundant NULL guards when the field is non-nullable
- Copy-pasted error messages that don't match the actual condition

### Code Cleanup Requirements
Once a test is **green**, audit the implementation and remove:
1. **Unreachable error handlers**: If Pydantic validates the input, don't add try/except for type errors
2. **Defensive guards that duplicate validation**: Don't check `if song_id is None` if the signature is `song_id: int` (not Optional)
3. **Speculative logging**: Only log actual branch decisions, not "just in case" debug spam
4. **Commented-out code**: Delete it (git history preserves it)

**Unnecessary Code Example**:
```python
def get_by_id(self, song_id: int) -> Optional[Song]:
    try:  # REDUNDANT: Pydantic already validates song_id is int
        if song_id is None:  # REDUNDANT: Signature guarantees int, not Optional
            return None
        if not isinstance(song_id, int):  # REDUNDANT
            raise ValueError("song_id must be int")

        # Actual logic
        row = cursor.execute("SELECT * FROM Songs WHERE SourceID = ?", (song_id,)).fetchone()
        return self._row_to_song(row) if row else None
    except Exception as e:  # REDUNDANT: Too broad, hides real errors
        logger.error(f"Something went wrong: {e}")
        return None
```

**Cleaned Version**:
```python
def get_by_id(self, song_id: int) -> Optional[Song]:
    logger.debug(f"[SongRepository] -> get_by_id(id={song_id})")

    with self._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM Songs WHERE SourceID = ?", (song_id,)).fetchone()

    if not row:
        logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) NOT_FOUND")
        return None

    song = self._row_to_song(row)
    logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) '{song.title}'")
    return song
```

**Checklist During Refactor**:
- ✅ Remove try/except unless handling DB connection failures or external I/O
- ✅ Remove isinstance checks when Pydantic already validates
- ✅ Remove None checks when signature is non-Optional
- ✅ Remove broad `except Exception` that swallows real errors
- ✅ Keep only logging that provides traceability (entry, exit, branches)

---

## Traceability: Logging is Part of the Contract

### Pervasive Logging Requirement
A test isn't truly done if the code is a "black box" in the logs. Every method must log:
1. **Entry**: Method name, key parameters
2. **Exit**: Result summary (found/not found, count, key field)
3. **Branch decisions**: Why a conditional took one path vs another

**Example**:
```python
def get_by_id(self, song_id: int) -> Optional[Song]:
    logger.debug(f"[SongRepository] -> get_by_id(id={song_id})")  # ENTRY

    row = cursor.execute("SELECT * FROM Songs WHERE SourceID = ?", (song_id,)).fetchone()

    if not row:
        logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) NOT_FOUND")  # EXIT (not found)
        return None

    song = self._row_to_song(row)
    logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) '{song.title}'")  # EXIT (found)
    return song
```

**Anti-Pattern (No Traceability)**:
```python
def get_by_id(self, song_id: int) -> Optional[Song]:
    row = cursor.execute("SELECT * FROM Songs WHERE SourceID = ?", (song_id,)).fetchone()
    return self._row_to_song(row) if row else None
```

**Why**: When a bug occurs in production, logs should show:
- Which method was called
- What parameters were passed
- What result was returned
- Which conditional branches executed

**Logging Format**:
- Entry: `[ClassName] -> method_name(param1=value1, param2=value2)`
- Exit: `[ClassName] <- method_name() result_summary`
- Branch: `[ClassName] Branch: reason for decision`

---
## Signature Synchronization

### Documentation Integrity is Part of the Test Contract
**Critical**: Any change to a method name or signature during TDD must be **instantly synced** to `docs/lookup/`.

**Synchronization Requirements**:
1. **One method** in the source code
2. **One entry** in `docs/lookup/{layer}.md`
3. **One test class** in the test suite

All three must stay in sync at all times.

**Why**: LLMs rely on `docs/lookup/` to understand the codebase. "AI Ghost" documentation (where docs reference old method names) causes:
- LLMs calling nonexistent methods
- LLMs using wrong parameter types
- Time wasted debugging phantom APIs

**Process**:
1. **Rename/change signature** in source code
2. **Update `docs/lookup/` entry** immediately (before writing tests)
3. **Update test class name** to match new method name
4. **Run tests** to verify

**Example Sync**:

Source code change:
```python
# OLD
def get_song_by_id(self, id: int) -> Song:

# NEW
def get_by_id(self, song_id: int) -> Optional[Song]:
```

`docs/lookup/data.md` change:
```markdown
# OLD
### get_song_by_id(id: int) -> Song

# NEW
### get_by_id(song_id: int) -> Optional[Song]
```

Test file change:
```python
# OLD
class TestGetSongById:

# NEW
class TestGetById:
```

**Enforcement**:
- Before submitting a PR, verify `docs/lookup/` matches current signatures
- Use grep to find outdated method references: `grep -r "old_method_name" docs/lookup/`

---
## Weekly Review Process

1. **Check Open Brain RAG** for patterns where tests failed to catch bugs
2. **Update this document** with new rules/patterns as needed
3. **Refactor existing tests** to match new standards gradually
4. **Document new edge cases** in conftest.py fixtures
5. **Audit `docs/lookup/` integrity**: Verify all method signatures are current

---
## Summary Checklist
When writing a new test, verify:
- ✅ Uses real test database (empty_db, populated_db, edge_case_db)
- ✅ One test per scenario with descriptive name
- ✅ Exhaustive assertions on all fields
- ✅ Assertion messages in format `f"Expected {y}, got {x}"`
- ✅ Test class per method being tested
- ✅ Follows return value contract (None for not found, etc.)
- ✅ For updates: verifies changed field AND all other fields unchanged
- ✅ For deletes: verifies cascade effects explicitly
- ✅ For collections: asserts all fields for every item
- ✅ For collections: explicitly asserts unrelated entities are excluded (negative isolation)
- ✅ For APIs: tests all status codes (200, 400, 404, 422, 500)
- ✅ No mocking (unless testing "disk full" or similar impossible scenarios)
- ✅ **Pervasive logging** (entry, exit, branches) is present for traceability
- ✅ **Slop purge** completed: no speculative guards, try/except, or defensive type checks
- ✅ **Signature sync**: method matches `docs/lookup/` and test class name