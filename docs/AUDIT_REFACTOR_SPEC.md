delayed for now

# Audit System Refactor Specification

**Status:** Awaiting Approval
**Date:** 2026-03-20
**Context:** Tear out broken `_log_change` from BaseRepository and implement proper audit logging based on the old v2 AuditLogger pattern.

---

## Problem Statement

The current `BaseRepository._log_change()` method (lines 24-59 of base_repository.py) was hastily added during the v3 refactor and has several issues:

**Note:** A rollback reverted earlier changes that added `_log_change` calls to `song_repository.py`. The method definition remains but is currently unused. Line references reflect the post-rollback state.

1. **No diff computation** — Logs `None → value` for all fields on insert, even when values haven't changed
2. **Repository responsibility violation** — Audit logic belongs in the service layer, not the repository
3. **Not backwards compatible** — Doesn't match the proven pattern from the old codebase
4. **Incomplete** — `AuditRepository` only has read methods, no write methods

The old v2 codebase had a working "Smart Logger, Dumb Repository" pattern that we need to port to v3.

---

## Design Decisions (Grill Resolutions)

### 1. Connection Ownership
**Decision:** Audit write methods take `connection` as a required parameter.

**Rationale:** Audit logging must share the same transaction boundary as data writes. If the data write fails and rolls back, the audit log must NOT persist. Service layer owns the transaction lifecycle.

**Fail-Secure:** If either the data write OR the audit write fails, both are rolled back together. This ensures the audit trail is always consistent with actual data state—no orphaned data without audit logs, and no audit logs for data that doesn't exist.

```python
# Service layer
conn = self._get_connection()
try:
    song_id = song_repo.insert(song, conn, batch_id)
    audit_service.log_insert(song, conn, batch_id)
    conn.commit()
except:
    conn.rollback()  # Rolls back BOTH data and audit writes
    raise
```

---

### 2. Data Types
**Decision:** Repository write methods accept Pydantic domain models (`AuditChange`, `AuditAction`, `DeletedRecord`) instead of raw tuples.

**Rationale:** v3 uses Pydantic everywhere for type safety. The old bulk-tuple API was fast but error-prone.

**Normalization:** The database `ChangeLog` table stores `OldValue` and `NewValue` as TEXT (schema.py lines 141-142). All field values are normalized to match their database representation:
- Integers → strings (`145` → `"145"`)
- Booleans → `"0"` or `"1"`
- None → `None` (stored as NULL)
- Empty strings → `None` (treated as equivalent to NULL)

This ensures ChangeLog values can be directly compared for diffs and potentially used for restoration.

---

### 3. Entity Hydration
**Decision:** Service layer hydrates full entities (with nested relations) before deletion.

**Rationale:** Already implemented. `CatalogService.delete_song()` calls `get_song()` which uses `_hydrate_songs()` to load credits, tags, albums, and publishers (catalog_service.py lines 423-452).

---

### 4. ChangeLog Granularity
**Decision:** Use exploded field-level logs to actual DB tables (not flattened JSON).

**Rationale:** Enables entity-centric queries like "show all changes for Freddie Mercury" and surgical restoration like "restore just the Rock genre tag". Flattening nested objects to JSON would require full table scans and string searches.

**Example:**
```
ChangeLog entries for deleting a song with 2 credits:
  - table: "MediaSources", record_id: 123, field: "MediaName", old: "Bohemian Rhapsody", new: NULL
  - table: "Songs", record_id: 123, field: "TempoBPM", old: "145", new: NULL
  - table: "SongCredits", record_id: "123-1", field: "CreditedNameID", old: "42", new: NULL
  - table: "SongCredits", record_id: "123-2", field: "CreditedNameID", old: "43", new: NULL
```

---

### 5. Audit Mappings
**Decision:** Manual Python mappings with automated pytest drift detection.

**Rationale:** Explicit mappings are debuggable and avoid magic. Drift detection ensures mappings stay in sync with schema changes (mirroring the existing `test_lookup_integrity.py` pattern).

**Files:**
- `src/data/audit_mappings.py` — Field and relation mappings
- `tests/test_audit_mapping_drift.py` — Automated drift detection

---

### 6. Diff Computation
**Decision:** Service layer passes dict representations (`model_dump()`) to `audit_service.log_update()`. Audit service computes diffs internally.

**Rationale:** Service layer already has old and new entity state. Audit service handles normalization and writing.

**Implementation:**
- **Base fields** (bpm, year, etc.): Use `_compute_diff()` to compare flat dictionaries
- **Nested relations** (credits, albums, tags, publishers): Use set-based comparison to detect:
  - Additions (in new, not in old) → log as `old=NULL, new=value`
  - Removals (in old, not in new) → log as `old=value, new=NULL`
  - Modifications (same ID, different fields) → log field-level diffs
- Each change generates individual ChangeLog entries using `_explode_entity()` for entity-centric queries

---

### 7. Batch ID Generation
**Decision:** Service layer generates and passes `batch_id` to group related operations.

**Rationale:** The service layer controls transaction scope. One `batch_id` = one API request. If a transaction fails and rolls back, a retry would be a new API request with a new `batch_id`.

**Example:** Deleting 10 songs in one UI action = one batch_id for all 10 deletes.

```python
batch_id = str(uuid.uuid4())
for song_id in song_ids:
    audit_service.log_delete(song, conn, batch_id)  # SAME batch_id
```

---

### 8. ActionLog Auto-Logging
**Decision:** `log_insert()`, `log_update()`, `log_delete()` automatically write to **both** ChangeLog (field-level) and ActionLog (high-level event).

**Rationale:**
- **ActionLog:** User-facing timeline ("User imported 5 songs")
- **ChangeLog:** Surgical restoration ("Restore the BPM field to 145")

Both tables serve complementary purposes. The action type is inferred from the method name.

---

### 9. Immediate Deletion
**Decision:** Delete `BaseRepository._log_change()` immediately. No gradual migration.

**Rationale:** The broken code hasn't been used in production yet (recent ingestion work). Clean break is safer than maintaining two patterns.

---

### 10. Implementation Scope
**Decision:** Build the audit **framework** (mappings, service methods, repository methods) but don't wire up CRUD operations yet.

**Rationale:** This is infrastructure work. Service layer integration (updating `CatalogService.insert_song()` to call `audit_service.log_insert()`) is a separate follow-up task.

---

## Implementation Plan

### Files to Create

#### 1. `src/data/audit_mappings.py`

Defines how Pydantic model fields map to database tables/columns.

```python
"""
Audit field mappings for exploding domain models into ChangeLog entries.
IMPORTANT: Keep in sync with schema.py. Run pytest to detect drift.
"""

# Song: Base fields (MediaSources + Songs tables)
SONG_FIELD_MAP = {
    # MediaSources table
    "id": ("MediaSources", "SourceID"),
    "media_name": ("MediaSources", "MediaName"),
    "source_path": ("MediaSources", "SourcePath"),
    "duration_ms": ("MediaSources", "SourceDuration"),
    "audio_hash": ("MediaSources", "AudioHash"),
    "processing_status": ("MediaSources", "ProcessingStatus"),
    "is_active": ("MediaSources", "IsActive"),

    # Songs table
    "bpm": ("Songs", "TempoBPM"),
    "year": ("Songs", "RecordingYear"),
    "isrc": ("Songs", "ISRC"),
    "groups": ("Songs", "SongGroups"),
}

# Song: Relational fields (junction tables)
SONG_RELATIONS = {
    "credits": {
        "table": "SongCredits",
        "fields": {
            "name_id": "CreditedNameID",
            "role_id": "RoleID",
        },
        "record_id_format": "{source_id}-{name_id}-{role_id}"
    },
    "tags": {
        "table": "MediaSourceTags",
        "fields": {
            "tag_id": "TagID",
            "is_primary": "IsPrimary",
        },
        "record_id_format": "{source_id}-{tag_id}"
    },
    "albums": {
        "table": "SongAlbums",
        "fields": {
            "album_id": "AlbumID",
            "track_number": "TrackNumber",
            "disc_number": "DiscNumber",
            "is_primary": "IsPrimary",
        },
        "record_id_format": "{source_id}-{album_id}"
    },
    "publishers": {
        "table": "RecordingPublishers",
        "fields": {
            "publisher_id": "PublisherID",
        },
        "record_id_format": "{source_id}-{publisher_id}"
    },
}

# Placeholder for future entity mappings
ALBUM_FIELD_MAP = {}
ALBUM_RELATIONS = {}

IDENTITY_FIELD_MAP = {}
IDENTITY_RELATIONS = {}

PUBLISHER_FIELD_MAP = {}
PUBLISHER_RELATIONS = {}
```

---

#### 2. `tests/test_audit_mapping_drift.py`

Automated drift detection to ensure mappings stay in sync with Pydantic models and database schema.

```python
"""
Audit Mapping Drift Detection

Ensures audit_mappings.py stays in sync with:
1. Pydantic model fields (src/models/domain.py)
2. Database schema (src/data/schema.py)

Pattern mirrors test_lookup_integrity.py
"""
import pytest
from src.models.domain import Song, Album, Identity, Publisher
from src.data import audit_mappings
from src.data.schema import SCHEMA_SQL


def get_pydantic_fields(model_class):
    """Extract all field names from a Pydantic model."""
    return set(model_class.model_fields.keys())


def get_mapped_fields(field_map, relations_map):
    """Extract all fields covered by audit mappings."""
    mapped = set(field_map.keys())
    mapped.update(relations_map.keys())
    return mapped


def get_schema_columns(table_name):
    """Extract column names from schema.py CREATE TABLE statement."""
    # Parse SCHEMA_SQL for the given table
    # This is a simple implementation - could be improved with SQL parsing
    columns = set()
    in_table = False

    for line in SCHEMA_SQL.split('\n'):
        if f"CREATE TABLE IF NOT EXISTS {table_name}" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith(')'):
                break
            if line.strip() and not line.strip().startswith('FOREIGN KEY') and not line.strip().startswith('PRIMARY KEY') and not line.strip().startswith('UNIQUE'):
                col_name = line.strip().split()[0]
                if col_name and col_name != 'CONSTRAINT':
                    columns.add(col_name)

    return columns


def test_song_mapping_completeness():
    """Verify all Song fields are mapped in audit_mappings.py"""
    pydantic_fields = get_pydantic_fields(Song)
    mapped_fields = get_mapped_fields(
        audit_mappings.SONG_FIELD_MAP,
        audit_mappings.SONG_RELATIONS
    )

    # Fields that are computed/derived and shouldn't be audited
    SKIP_FIELDS = {"title"}  # Alias for media_name

    missing = pydantic_fields - mapped_fields - SKIP_FIELDS

    if missing:
        pytest.fail(
            f"Song fields missing from audit_mappings.py: {missing}\n"
            f"Add them to SONG_FIELD_MAP or SONG_RELATIONS"
        )


def test_song_mapping_schema_validity():
    """Verify mapped columns exist in schema.py"""
    errors = []

    # Check base fields
    for field, (table, column) in audit_mappings.SONG_FIELD_MAP.items():
        schema_columns = get_schema_columns(table)
        if column not in schema_columns:
            errors.append(
                f"SONG_FIELD_MAP['{field}'] maps to {table}.{column}, "
                f"but column doesn't exist in schema.py"
            )

    # Check relational fields
    for rel_name, rel_config in audit_mappings.SONG_RELATIONS.items():
        table = rel_config["table"]
        schema_columns = get_schema_columns(table)

        for field, column in rel_config["fields"].items():
            if column not in schema_columns:
                errors.append(
                    f"SONG_RELATIONS['{rel_name}']['{field}'] maps to {table}.{column}, "
                    f"but column doesn't exist in schema.py"
                )

    if errors:
        pytest.fail("\n".join(errors))


def test_other_entity_mappings_exist():
    """Placeholder test for Album, Identity, Publisher mappings."""
    # For now, just verify the mapping dicts exist
    assert hasattr(audit_mappings, 'ALBUM_FIELD_MAP')
    assert hasattr(audit_mappings, 'IDENTITY_FIELD_MAP')
    assert hasattr(audit_mappings, 'PUBLISHER_FIELD_MAP')

    # TODO: Add full drift detection when these entities are implemented
```

---

### Files to Modify

#### 3. `src/services/audit_service.py`

Add write methods and port normalization logic from old AuditLogger.

**Changes:**
- Add `log_insert(entity, conn, batch_id, details=None)`
- Add `log_update(entity, old_data: Dict, new_data: Dict, conn, batch_id, details=None)`
- Add `log_delete(entity, conn, batch_id, details=None)`
- Add `log_action(action_type, target_table, target_id, details, conn, batch_id, user_id=None)` (public method)
- Port `_normalize_dict()` from old code (handle lists, bools, None/empty strings)
- Port `_compute_diff()` from old code (compare normalized dicts)
- Add `_explode_entity(entity, parent_entity)` helper to convert Pydantic model → list of AuditChange objects using mappings

**Details Serialization:** The `details` parameter accepts an optional `Dict[str, Any]` and is serialized to JSON before writing to ActionLog. For DeletedRecords, use `entity.model_dump_json()` to get the full entity snapshot as JSON.

**Entity Explosion:** `_explode_entity()` accepts the parent entity as a parameter. When processing nested relations (like tags), it uses the parent's `id` field to populate placeholders like `{source_id}` in the `record_id_format` string. The nested objects don't need to carry the parent ID—it's extracted from the parent context.

**Example signature:**
```python
def log_insert(
    self,
    entity: DomainModel,
    conn: sqlite3.Connection,
    batch_id: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log creation of a new entity.

    Writes to:
    1. ChangeLog (field-level: None → value for all fields)
    2. ActionLog (high-level: INSERT event)

    Args:
        entity: Hydrated Pydantic model (Song, Album, etc.)
        conn: Active database connection (service owns transaction)
        batch_id: UUID grouping related operations
        details: Optional metadata for ActionLog (e.g., {"filename": "song.mp3"})
    """
```

**Old code to port:**
```python
# From git show 8fef366:src/core/audit_logger.py

def _normalize_dict(self, data: Dict[str, Any]) -> Dict[str, str]:
    """Convert all nested types (lists, objects) to consistent strings for storage."""
    normalized = {}
    for k, v in data.items():
        if v is None:
            normalized[k] = None
            continue

        # List Handling: Sort and Join
        if isinstance(v, list):
            items = sorted([str(x).strip() for x in v if x])
            val = ", ".join(items)
            normalized[k] = val

        # Bool Handling: explicit 0/1
        elif isinstance(v, bool):
            normalized[k] = "1" if v else "0"

        # Primitives: Convert to string, normalize empty to None
        else:
            s_val = str(v).strip()
            normalized[k] = s_val if s_val else None

    return normalized

def _compute_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Compare old vs new. Returns { field: {'old': str, 'new': str} }
    """
    diffs = {}

    norm_old = self._normalize_dict(old)
    norm_new = self._normalize_dict(new)

    all_keys = set(norm_old.keys()) | set(norm_new.keys())

    for k in all_keys:
        val_old = norm_old.get(k)
        val_new = norm_new.get(k)

        # Treat None and "" as equivalent
        eff_old = val_old if val_old is not None else ""
        eff_new = val_new if val_new is not None else ""

        if eff_old != eff_new:
            diffs[k] = {'old': val_old, 'new': val_new}

    return diffs
```

---

#### 4. `src/data/audit_repository.py`

Add write methods (currently only has reads).

**Changes:**
- Add `insert_change_logs(changes: List[AuditChange], conn: Connection)`
- Add `insert_deleted_record(deleted_record: DeletedRecord, conn: Connection)`
- Add `insert_action_log(action: AuditAction, conn: Connection)`
- Keep all existing read methods unchanged

**Example implementation:**
```python
def insert_change_logs(
    self,
    changes: List[AuditChange],
    conn: sqlite3.Connection
) -> None:
    """
    Bulk insert field-level change logs.

    Args:
        changes: List of AuditChange domain models
        conn: Active connection (caller owns transaction)

    Raises:
        Exception: Propagates DB errors for rollback
    """
    if not changes:
        return

    cursor = conn.cursor()
    rows = [
        (
            change.table_name,
            change.record_id,
            change.field_name,
            change.old_value,
            change.new_value,
            change.batch_id,
        )
        for change in changes
    ]

    try:
        cursor.executemany(
            """
            INSERT INTO ChangeLog
            (LogTableName, RecordID, LogFieldName, OldValue, NewValue, BatchID)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows
        )
        logger.debug(f"[AuditRepository] Wrote {len(rows)} ChangeLog entries")
    except Exception as e:
        logger.error(f"[AuditRepository] CRITICAL: Failed to write ChangeLog: {e}")
        raise  # Fail-secure: propagate for rollback

def insert_deleted_record(
    self,
    deleted_record: DeletedRecord,
    conn: sqlite3.Connection
) -> None:
    """Archive a deleted record's full JSON snapshot."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO DeletedRecords
            (DeletedFromTable, RecordID, FullSnapshot, BatchID)
            VALUES (?, ?, ?, ?)
            """,
            (
                deleted_record.table_name,
                deleted_record.record_id,
                deleted_record.snapshot,
                deleted_record.batch_id,
            )
        )
        logger.debug(f"[AuditRepository] Archived {deleted_record.table_name} ID {deleted_record.record_id}")
    except Exception as e:
        logger.error(f"[AuditRepository] CRITICAL: Failed to write DeletedRecord: {e}")
        raise

def insert_action_log(
    self,
    action: AuditAction,
    conn: sqlite3.Connection
) -> None:
    """Log a high-level user action."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ActionLog
            (ActionLogType, TargetTable, ActionTargetID, ActionDetails, UserID, BatchID)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action.action_type,
                action.target_table,
                action.target_id,
                action.details,
                action.user_id,
                action.batch_id,
            )
        )
        logger.debug(f"[AuditRepository] Logged action: {action.action_type}")
    except Exception as e:
        logger.error(f"[AuditRepository] CRITICAL: Failed to write ActionLog: {e}")
        raise
```

---

#### 5. `docs/lookup/data.md`

**Update** to reflect new state:
- Remove `_log_change` entry from BaseRepository section
- Add write methods to AuditRepository section (`insert_change_logs`, `insert_deleted_record`, `insert_action_log`)

#### 6. `src/data/base_repository.py`

**Delete lines 24-59** (`_log_change` method entirely).

---

#### 6. `src/data/song_repository.py`

**Remove all `_log_change()` calls:**
- Lines 224-280 (insert audit logging)
- Lines 297-302 (delete audit logging)

The repository methods become simpler — just DB operations, no audit logic.

**Example before/after:**

**Before (lines 215-283):**
```python
cursor.execute(
    """
    INSERT INTO Songs (SourceID, TempoBPM, RecordingYear, ISRC)
    VALUES (?, ?, ?, ?)
    """,
    (source_id, song.bpm, song.year, song.isrc),
)

# 3. Audit Logging (MediaSources)
self._log_change(cursor, "MediaSources", source_id, "TypeID", None, 1, batch_id)
self._log_change(cursor, "MediaSources", source_id, "MediaName", None, song.media_name or song.title, batch_id)
# ... 10 more audit calls ...

logger.debug(f"[SongRepository] <- insert() created SourceID: {source_id}")
return source_id
```

**After:**
```python
cursor.execute(
    """
    INSERT INTO Songs (SourceID, TempoBPM, RecordingYear, ISRC)
    VALUES (?, ?, ?, ?)
    """,
    (source_id, song.bpm, song.year, song.isrc),
)

logger.debug(f"[SongRepository] <- insert() created SourceID: {source_id}")
return source_id
```

---

## Testing Strategy

All tests use the existing **hermetic SQLite database fixtures** from `tests/conftest.py`:
- `empty_db` - Schema only, for negative/empty tests
- `populated_db` - Rich "Dave Grohl" scenario with known exact values
- `edge_case_db` - Orphans, nulls, unicode, boundary values

This follows the established "contract testing against real SQLite" pattern (no mocking, isolated test databases).

### Unit Tests

1. **`test_audit_mapping_drift.py`** (new)
   - Verify Song fields are completely mapped
   - Verify mapped columns exist in schema.py
   - Placeholder tests for Album/Identity/Publisher

2. **`tests/test_repositories/test_other_repositories.py`** (modify)
   - Delete existing `_log_change` tests (lines 307-340)
   - Add tests for new `AuditRepository` write methods:
     - `test_insert_change_logs_bulk()`
     - `test_insert_deleted_record()`
     - `test_insert_action_log()`

3. **`tests/test_audit.py`** (modify existing)
   - Add tests for `AuditService.log_insert()`
   - Add tests for `AuditService.log_update()`
   - Add tests for `AuditService.log_delete()`
   - Verify ChangeLog AND ActionLog are both written
   - Verify nested relations are exploded correctly

### Integration Tests

Not in scope for this refactor. Service layer integration (wiring up `CatalogService` to call audit methods) is future work.

---

## Migration Notes

### Database Impact

**Schema migration required for `ChangeLog.RecordID`:**
- Change column type from `INTEGER` to `TEXT` to properly support composite primary keys for junction tables (e.g., `"123-42-1"` for SongCredits)
- SQLite's dynamic typing currently allows this to work, but the schema declaration is misleading
- Migration: The column already stores TEXT values in practice, so this is primarily a schema documentation fix
- **Status:** Fixed in [src/data/schema.py:139](src/data/schema.py#L139)

### Data Loss Risk

**Low.** The broken `_log_change` code was only added in recent commits and hasn't been used in production. Current audit logs (if any exist) were generated by the old v2 code before the v3 refactor.

### Rollback Plan

If issues are discovered after merge:
1. Revert the commit
2. The old v2 `AuditLogger` code is preserved in git history (`8fef366:src/core/audit_logger.py`)

---

## Open Questions

### For Future Discussion (Not Blocking)

1. **Restoration API:** How should the service layer invoke "undo batch X" or "restore field Y"?
   - Likely a new `AuditService.restore_batch(batch_id)` method
   - Out of scope for this refactor

2. **ActionLog user_id:** Where does this come from in the engine API context?
   - Desktop app doesn't have authenticated users yet
   - Could use `"system"` or `None` for now

3. **Custom action types:** Should we standardize action names?
   - Current plan: `"INSERT"`, `"UPDATE"`, `"DELETE"`, `"IMPORT"`, `"BULK_DELETE"`
   - Could add enum/constants later

---

## Done Protocol Checklist

Before marking complete, run:

1. `black .` — zero errors
2. `ruff check . --fix` — zero errors
3. `pytest` — full suite passes
4. `pytest --cov` — 100% coverage on new code (`audit_mappings.py`, new `audit_service.py` methods, new `audit_repository.py` methods)
5. `docs/lookup/data.md` — accurate to implementation

---

## Success Criteria

✅ All tests pass (including new drift detection)
✅ `BaseRepository._log_change` deleted
✅ `SongRepository` cleaned up (no audit calls)
✅ `AuditRepository` has write methods
✅ `AuditService` has `log_insert/update/delete` methods
✅ Audit mappings defined for Song entity
✅ Code ready for service layer integration (future PR)

---

## Files Modified Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/data/audit_mappings.py` | **CREATE** | Field and relation mappings for Song (+ placeholders for Album/Identity/Publisher) |
| `tests/test_audit_mapping_drift.py` | **CREATE** | Automated drift detection for mappings vs schema |
| `src/services/audit_service.py` | **MODIFY** | Add write methods, port normalization/diff logic |
| `src/data/audit_repository.py` | **MODIFY** | Add write methods (insert_change_logs, insert_deleted_record, insert_action_log) |
| `docs/lookup/data.md` | **MODIFY** | Remove `_log_change` entry, add AuditRepository write methods |
| `src/data/base_repository.py` | **MODIFY** | Delete `_log_change()` method (lines 24-59) |
| `src/data/song_repository.py` | **MODIFY** | Remove all `_log_change()` calls from insert/delete |
| `tests/test_repositories/test_other_repositories.py` | **MODIFY** | Delete old `_log_change` tests, add new AuditRepository write tests |
| `tests/test_audit.py` | **MODIFY** | Add tests for AuditService write methods |

---

## Estimated Complexity

**Medium-High**

- Porting old code: Low risk (proven pattern)
- Mapping system: Medium complexity (manual but straightforward)
- Testing: Medium (drift detection requires introspection)
- Integration: Not in scope (deferred)

**Estimated LOC:** ~800 lines (300 implementation, 500 tests/mappings)

---

**Ready for review Monday. Ping me with questions or required changes.**
