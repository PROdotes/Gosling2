# TEST PLAN ANALYSIS - What's Missing

## Executive Summary

Your test plan is **good** but has **critical gaps**. The tests are passing 100% (69/69), yet you say "things fail or behave unexpectedly". This means:

1. **Tests are not comprehensive enough** - they're testing happy paths but missing error conditions
2. **Tests are not asserting the RIGHT things** - they check that something exists, not that it's EXACTLY correct
3. **Tests are not catching integration issues** - layers work in isolation but not together
4. **No fixtures for edge cases** - `edge_case_db` doesn't exist yet

---

## CRITICAL GAPS IN YOUR CURRENT PLAN

### 1. **Missing: Negative Path Testing**

Your plan mentions these but tests don't verify them:

| Gap | Example Missing Test |
|-----|---------------------|
| **Malformed inputs** | `get_song("not_a_number")` - does it raise 400 or crash? |
| **SQL injection** | `search_songs("'; DROP TABLE Songs--")` - is it sanitized? |
| **Integer overflow** | `get_song(9223372036854775807)` - boundary values |
| **Empty strings** | `search_songs("")` vs `search_songs(" ")` - different behavior? |
| **Special characters** | `search_songs("%")` - literal % or wildcard? |

**ACTION NEEDED**: Add Layer 7 to your plan:
```markdown
## LAYER 7: NEGATIVE PATHS (Attack/Abuse Cases)

| Scenario | Expected Behavior |
|----------|------------------|
| SQL Injection attempt | Sanitized, no execution |
| Integer overflow | ValueError or clamp to max |
| Empty query | Clear contract: [] or all? |
| Null bytes | Rejected with 400 |
| Extremely long string (10MB) | 413 Entity Too Large |
```

---

### 2. **Missing: Concurrency/Race Conditions**

No tests for concurrent operations:

| Gap | Missing Test |
|-----|--------------|
| **Parallel reads** | 100 threads calling `get_song(1)` simultaneously |
| **Read during write** | Thread A reads while Thread B updates same record |
| **Connection pool exhaustion** | What happens when all connections are busy? |
| **Deadlock scenarios** | Two transactions waiting on each other |

**WHY THIS MATTERS**: SQLite has write locks. If your app writes while serving reads, it could block or timeout.

**ACTION NEEDED**: Add Layer 8:
```markdown
## LAYER 8: CONCURRENCY (Multi-threaded Behavior)

| Scenario | Expected |
|----------|----------|
| 100 parallel reads of same song | All succeed, same data |
| Read during write (different tables) | No blocking |
| Write during write (same table) | One succeeds, one waits or retries |
| Connection pool limit | Graceful queue or 503 |
```

---

### 3. **Missing: Data Integrity Constraints**

Your tests assume data is valid. What if it's not?

| Gap | Example |
|-----|---------|
| **Orphaned records** | Song credits point to deleted identity - plan mentions this but no test exists |
| **Circular references** | Group A member of Group B, Group B member of Group A |
| **Duplicate primary keys** | Two songs with SourceID=1 (schema should prevent, but test it) |
| **Foreign key violations** | SongCredit references NameID that doesn't exist |
| **Invalid enum values** | IdentityType='invalid' instead of 'person'/'group' |

**ACTION NEEDED**: Enhance `edge_case_db` fixture:

```python
@pytest.fixture
def edge_case_db(mock_db_path):
    conn = sqlite3.connect(mock_db_path)

    # 1. Orphaned song credit (NameID points to deleted identity)
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (99, 'person')")
    cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (999, 99, 'Ghost Artist', 1)")
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration) VALUES (888, 1, 'Orphan Song', '/path', 100)")
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (888)")
    cursor.execute("INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (888, 999, 1)")
    # Now delete the identity
    cursor.execute("DELETE FROM Identities WHERE IdentityID = 99")

    # 2. Circular group membership
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (500, 'group')")
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (501, 'group')")
    cursor.execute("INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (500, 501)")
    cursor.execute("INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (501, 500)")

    # 3. NULL in required fields
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration) VALUES (777, 1, NULL, '/path', 100)")

    # 4. Extreme values
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration) VALUES (666, 1, 'Long Song', '/path', 999999999)")

    conn.commit()
    return mock_db_path
```

**TEST CONTRACTS**:
- `test_orphaned_credit_handling`: What should `get_song(888)` return? Error? Skip the credit? Return "Unknown Artist"?
- `test_circular_group_infinite_loop_prevention`: Should detect cycle and break, not stack overflow
- `test_null_required_field`: Should raise ValueError or return None?

---

### 4. **Missing: Repository Isolation Tests**

You test services but NOT repositories in isolation. This is CRITICAL because services use repos.

Current state:
- ✅ `test_catalog.py` - Tests `CatalogService` (service layer)
- ❌ **Missing**: `test_repositories/test_song_repository.py` - Tests `SongRepository` (data layer)

**WHY THIS MATTERS**: If a service test fails, you don't know if the bug is in:
1. Service logic (CatalogService)
2. Repository logic (SongRepository)
3. SQL query itself

**ACTION NEEDED**: Create `tests/test_repositories/` with:

```python
# test_repositories/test_song_repository.py
def test_get_by_id_exists(populated_db):
    """REPO LAW: get_by_id returns exact Song object for valid ID."""
    repo = SongRepository(populated_db)
    song = repo.get_by_id(1)

    assert song is not None
    assert song.id == 1
    assert song.title == "Smells Like Teen Spirit"  # Exact value
    assert song.duration_ms == 200000  # Exact duration
    assert song.source_path == "/path/1"  # Exact path
    # NO credits here - that's SongCreditRepository's job

def test_get_by_id_not_found(populated_db):
    """REPO LAW: get_by_id returns None for invalid ID."""
    repo = SongRepository(populated_db)
    assert repo.get_by_id(999) is None

def test_get_by_ids_batch_efficiency(populated_db):
    """REPO LAW: get_by_ids returns results in same order as input."""
    repo = SongRepository(populated_db)
    songs = repo.get_by_ids([3, 1, 2])  # Non-sequential order

    ids = [s.id for s in songs]
    # Contract: Does it preserve order or sort? DECIDE AND TEST IT.
    assert ids == [1, 2, 3] or ids == [3, 1, 2]  # Pick one!

def test_search_surface_empty_query(populated_db):
    """REPO LAW: search_surface with '' returns ALL songs or NONE?"""
    repo = SongRepository(populated_db)
    songs = repo.search_surface("")

    # CONTRACT DECISION: Empty query should return...
    assert len(songs) == 8  # All songs in populated_db
    # OR
    # assert len(songs) == 0  # No match
    # PICK ONE AND DOCUMENT IT!
```

Do this for ALL repositories:
- `test_song_repository.py`
- `test_song_credit_repository.py`
- `test_identity_repository.py`
- `test_publisher_repository.py`
- `test_album_repository.py`
- `test_tag_repository.py`

---

### 5. **Missing: Contract Ambiguities**

Your plan says "EXACTLY Z back" but tests use fuzzy checks:

```python
# BAD (current test_catalog.py:12)
assert song is not None  # Just checks existence
assert song.id == 2  # Checks one field
assert song.title == "Everlong"  # Checks one field

# GOOD (what you need)
assert song == Song(
    id=2,
    type_id=1,
    media_name="Everlong",
    source_path="/path/2",
    duration_ms=240000,
    audio_hash=None,
    processing_status=None,
    is_active=True,
    source_notes=None,
    tempo_bpm=None,
    recording_year=None,
    isrc=None,
    credits=[],  # Not hydrated yet at repo level
    albums=[],
    publishers=[],
    tags=[]
)
```

**ACTION NEEDED**: Create exact object matchers. Add to `conftest.py`:

```python
def assert_song_exact(actual: Song, expected: Song):
    """Deep equality check for Song objects."""
    assert actual.id == expected.id, f"ID mismatch: {actual.id} != {expected.id}"
    assert actual.title == expected.title, f"Title mismatch: {actual.title} != {expected.title}"
    assert actual.duration_ms == expected.duration_ms, f"Duration mismatch"
    # ... check ALL fields

    # Credits check
    assert len(actual.credits) == len(expected.credits), f"Credit count mismatch"
    for i, (ac, ec) in enumerate(zip(actual.credits, expected.credits)):
        assert ac.display_name == ec.display_name, f"Credit {i} name mismatch"
        assert ac.role_id == ec.role_id, f"Credit {i} role mismatch"
```

---

### 6. **Missing: Performance/Load Tests**

No tests for:
- Large datasets (1M songs)
- Query performance (search < 100ms)
- Memory leaks (does hydrating 1000 songs leak?)

**ACTION NEEDED**: Add Layer 9:

```markdown
## LAYER 9: PERFORMANCE

| Metric | Test | Threshold |
|--------|------|-----------|
| Single song lookup | get_song(1) | < 10ms |
| Batch hydration | get_by_ids([1...100]) | < 100ms |
| Full scan | get_all_songs() with 10K songs | < 1s |
| Memory usage | Hydrate 1000 songs | < 500MB |
| Search response time | search_songs("common") with 10K results | < 200ms |
```

---

### 7. **Missing: HTTP Layer Error Codes**

Your router tests check 200 and 404, but what about:

| HTTP Code | Missing Test |
|-----------|--------------|
| 400 Bad Request | Invalid ID format: `/songs/abc` |
| 422 Unprocessable Entity | Valid JSON but invalid data |
| 500 Internal Server Error | Database connection lost |
| 503 Service Unavailable | Database locked |
| 413 Entity Too Large | Query string > 1MB |

**ACTION NEEDED**: Enhance Layer 3 (Routers):

```python
@pytest.mark.asyncio
async def test_get_song_invalid_id_format(populated_db):
    """ROUTER LAW: Invalid ID format returns 400."""
    os.environ["GOSLING_DB_PATH"] = populated_db
    with TestClient(app) as client:
        response = client.get("/api/v1/songs/not_a_number")
        assert response.status_code == 400  # OR 422, DECIDE!

@pytest.mark.asyncio
async def test_search_songs_query_too_long(populated_db):
    """ROUTER LAW: Query > 1000 chars returns 413."""
    os.environ["GOSLING_DB_PATH"] = populated_db
    with TestClient(app) as client:
        response = client.get(f"/api/v1/songs/search?q={'a' * 10000}")
        assert response.status_code == 413
```

---

### 8. **Missing: Transaction/Rollback Tests**

No tests for write operations:

| Operation | Missing Test |
|-----------|--------------|
| Create song | Does it assign correct ID? Rollback on error? |
| Update song | Does it preserve unchanged fields? Audit log? |
| Delete song | Cascade to credits? Hard delete protocol? |
| Batch operations | 100 inserts succeed or all rollback? |

**ACTION NEEDED**: If you have write operations, test them:

```python
def test_create_song_transaction_rollback(populated_db):
    """REPO LAW: Failed insert does not modify database."""
    service = CatalogService(populated_db)

    # Try to insert invalid song
    try:
        service.create_song(Song(id=1, ...))  # Duplicate ID
    except Exception:
        pass

    # Verify database unchanged
    songs = service.get_all_songs()
    assert len(songs) == 8  # Same as before
```

---

### 9. **Missing: Environment/Configuration Tests**

Your tests use `monkeypatch.setenv("GOSLING_DB_PATH", ...)` but don't test:

| Scenario | Missing Test |
|----------|--------------|
| GOSLING_DB_PATH not set | Should fail gracefully |
| GOSLING_DB_PATH points to non-existent file | Should create or error |
| GOSLING_DB_PATH is a directory, not file | Should error with clear message |
| Database file is read-only | Write operations fail gracefully |
| Database is corrupted | Detect and report, not crash |

---

### 10. **Missing: View Model Edge Cases**

Your plan has Layer 4 but tests don't cover:

| Transform | Missing Test |
|-----------|--------------|
| `formatted_duration` | What if duration_ms is negative? |
| `display_artist` | What if ALL credits have NULL display_name? |
| `display_publisher` | What if hierarchy is 10 levels deep? |
| `primary_genre` | What if two tags have IsPrimary=1? |

---

## RECOMMENDED EXECUTION ORDER (REVISED)

1. ✅ **Fix conftest.py** - Add `edge_case_db` fixture (you mentioned this)
2. ✅ **Create test_repositories/** - Isolate data layer testing
3. ⚠️ **Add negative path tests** - Layer 7 (malformed inputs, SQL injection)
4. ⚠️ **Add concurrency tests** - Layer 8 (parallel operations)
5. ⚠️ **Add HTTP error code tests** - Enhance Layer 3
6. 🆕 **Add exact value assertions** - Use object matchers, not just field checks
7. 🆕 **Add performance benchmarks** - Layer 9
8. 🔄 **Rewrite existing tests** - Replace fuzzy assertions with exact contracts

---

## SPECIFIC ISSUES IN CURRENT TESTS

### Issue 1: Environmental Leaks
```python
# test_engine.py:8
monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
```
**PROBLEM**: This affects ALL tests in the session. If test fails, env persists.

**FIX**: Use context manager or teardown:
```python
@pytest.fixture
def catalog_with_env(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    yield CatalogService(populated_db)
    # Auto cleanup by pytest
```

### Issue 2: Fuzzy Assertions
```python
# test_catalog.py:34
names = {c.display_name for c in song.credits}
assert "Dave Grohl" in names
```
**PROBLEM**: Doesn't check if there are EXTRA credits. Could have 10 credits and still pass.

**FIX**:
```python
assert {c.display_name for c in song.credits} == {"Dave Grohl", "Taylor Hawkins"}
```

### Issue 3: No Ordering Contracts
```python
# test_catalog.py:183
names = [i.display_name for i in identities]
assert names[0] == "Dave Grohl"
```
**PROBLEM**: Checks first item but not full order.

**FIX**:
```python
assert names == ["Dave Grohl", "Foo Fighters", "Nirvana", "Taylor Hawkins"]
```

### Issue 4: Missing NULL Checks
```python
# test_catalog.py:245
assert album.album_type is None
```
**GOOD!** But most tests don't check NULL fields. Add more.

---

## FINAL VERDICT

Your plan is **70% complete**. Here's what to add:

| Layer | Status | Missing |
|-------|--------|---------|
| 1: Repositories | ⚠️ 30% | Isolated repo tests, NULL handling, batch order |
| 2: Services | ✅ 80% | Orphaned data, circular refs, transaction rollback |
| 3: Routers | ⚠️ 50% | HTTP error codes (400, 413, 500, 503) |
| 4: View Models | ⚠️ 40% | Edge cases (negative duration, NULL fields, deep hierarchy) |
| 5: Edge Cases | ❌ 0% | **`edge_case_db` doesn't exist** |
| 6: Integration | ⚠️ 60% | End-to-end flows, transaction boundaries |
| 7: Negative Paths | ❌ 0% | **SQL injection, malformed inputs, overflow** |
| 8: Concurrency | ❌ 0% | **Parallel operations, deadlocks** |
| 9: Performance | ❌ 0% | **Load tests, memory leaks** |

---

## WHAT TO DO NEXT

1. **Create `edge_case_db` fixture** - Highest priority
2. **Create `tests/test_repositories/`** - Second priority
3. **Add negative path tests** - Security critical
4. **Add exact assertions** - Quality critical
5. **Add concurrency tests** - If you have multi-threaded access

Your philosophy is perfect: "WHEN I call X with Y, I expect EXACTLY Z back". Now **enforce EXACTLY** in assertions, not just "something like Z". 🎯
