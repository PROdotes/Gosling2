# TDD Quick Start: Contract-First Testing

**Purpose**: Define the complete contract BEFORE writing any code. Tests are safeguards against assumptions and regression.

---

## Before Implementing Any Method

### 1. Define ALL Input Scenarios
Ask yourself:
- What are the **valid** inputs?
- What are the **invalid** inputs?
- What happens with **NULL/None/empty** values?
- What happens with **edge cases**? (0, negative, very large, unicode, whitespace, etc.)
- What happens with **missing/orphaned references**? (e.g., song_id=999 doesn't exist)
- What happens with **duplicate/conflicting** data?

### 2. Define Expected Output for EACH Scenario
For every input above, specify:
- What should be **returned**? (exact type, exact value)
- Should it return `None`? Empty list? Raise exception?
- Which **fields** should be populated? Which should be `None`?
- What **should NOT change**? (other records, other fields)

### 3. Define Side Effects
- What **database changes** should occur?
- What **should cascade**? (related records deleted/updated)
- What **should be preserved**? (related records NOT affected)

### 4. Write Tests for Every Scenario
One test per scenario:
- `test_{method}_{scenario}_{expected_outcome}`
- Assert **every field** (prevents silent defaults)
- Assert **negative cases** (proves unrelated data unchanged)
- Use assertion messages: `assert x == y, f"Expected {y}, got {x}"`

---

## Common "What If" Scenarios to Test

### Read Operations (get_by_id, search, etc.)
- ✅ Record exists → returns complete object with all fields
- ✅ Record doesn't exist → returns `None` (not empty object, not exception)
- ✅ NULL fields in DB → map to `None` in Python (not "", not 0, not "Unknown")
- ✅ Multiple results → returns all, excludes unrelated entities
- ✅ Empty results → returns `None` (not `[]`)
- ✅ Batch fetch with partial results → returns only found items, skips missing

### Write Operations (insert, update, delete)
- ✅ Insert: returns created object with DB-assigned ID, all fields set correctly
- ✅ Update: changed field updates, **all other fields unchanged**
- ✅ Delete: record removed, cascades work, unrelated records preserved
- ✅ Duplicate/conflict: how does it behave?

### Edge Cases
- ✅ Unicode characters (e.g., "日本語")
- ✅ Whitespace-only strings
- ✅ Very large/very small numbers
- ✅ Orphaned references (foreign key points to nonexistent record)
- ✅ Circular relationships

---

## Anti-Pattern: Superficial Testing

**Bad** (only tests "it works"):
```python
def test_get_by_id(self, populated_db):
    repo = SongRepository(populated_db)
    song = repo.get_by_id(1)
    assert song is not None  # ❌ Doesn't verify what "works" means
    assert song.title == "Smells Like Teen Spirit"  # ❌ Only checks one field
```

**Good** (tests the contract):
```python
def test_get_by_id_existing_song_returns_complete_object(self, populated_db):
    repo = SongRepository(populated_db)
    song = repo.get_by_id(1)

    # Assert EVERY field
    assert song.id == 1, f"Expected 1, got {song.id}"
    assert song.title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
    assert song.duration_ms == 200000, f"Expected 200000, got {song.duration_ms}"
    assert song.path == "/path/1", f"Expected '/path/1', got '{song.path}'"
    assert song.audio_hash == "hash_1", f"Expected 'hash_1', got '{song.audio_hash}'"
    assert song.recording_year == 1991, f"Expected 1991, got {song.recording_year}"
    assert song.is_active is True, f"Expected True, got {song.is_active}"
    assert song.processing_status is None, f"Expected None, got {song.processing_status}"
    # Repo doesn't hydrate relationships
    assert song.credits == [], f"Expected [], got {song.credits}"
    assert song.albums == [], f"Expected [], got {song.albums}"

def test_get_by_id_nonexistent_id_returns_none(self, populated_db):
    repo = SongRepository(populated_db)
    song = repo.get_by_id(999)
    assert song is None, f"Expected None for nonexistent ID, got {song}"

def test_get_by_id_with_null_fields_maps_to_none(self, edge_case_db):
    repo = SongRepository(edge_case_db)
    song = repo.get_by_id(104)  # Song with NULL audio_hash, NULL year

    assert song.id == 104, f"Expected 104, got {song.id}"
    assert song.audio_hash is None, f"Expected None for NULL hash, got {song.audio_hash}"
    assert song.recording_year is None, f"Expected None for NULL year, got {song.recording_year}"
    # ... all other fields
```

---

## Return Value Contracts (Must Follow)

| Method Pattern | Return When Found | Return When Not Found |
|----------------|-------------------|----------------------|
| `get_by_id(id)` | `Optional[T]` → object | `None` |
| `search(query)` | `Optional[List[T]]` → list | `None` (not `[]`) |
| `get_by_ids(ids)` | `List[T]` → found items only | `[]` (skip missing) |
| `insert(obj)` | Created object with ID | N/A |
| `update(obj)` | Updated object (all fields) | `None` if not found |
| `delete(id)` | `True` | `False` |

---

## Checklist Before Implementing

Before writing any implementation code:

- [ ] Listed all valid input scenarios
- [ ] Listed all invalid/edge/NULL scenarios
- [ ] Defined expected output for each scenario
- [ ] Defined what should NOT change
- [ ] Defined cascade/side effects (if applicable)
- [ ] Written test for "happy path"
- [ ] Written test for "not found" case
- [ ] Written test for NULL/empty fields
- [ ] Written test for edge cases (if method logic could create them)
- [ ] Verified tests use real database (no mocking)
- [ ] Verified exhaustive assertions (every field, not just key fields)

---

## Why This Matters

**Without exhaustive contract testing, LLMs will:**
- Default missing artist to "Composer"
- Default missing genre to "Mood"
- Set duration to 0 instead of None
- Use empty string instead of None
- Return `[]` when they should return `None`
- Accidentally reset fields to NULL during updates
- Forget to test cascade deletes

**Two months later, you'll wonder:**
- Why are we getting false positives?
- Why did this feature break silently?
- Why are tests passing when they should fail?

Tests are not just "does it work?" — they're **documentation of the contract** that prevents future you from being surprised.
