# 🏗 Proposal: Generic Repository & Audit Architecture

## 1. Executive Summary

**Objective:** Consolidate data access into a `GenericRepository` pattern to enforce architectural consistency and enable centralized Audit Logging.
**Key Constraint:** "Smart Logger, Dumb Repository." The Repository handles data marshalling; the `AuditLogger` handles diff calculation.
**Architecture:**

* **Models:** Responsible for Serialization (`to_dict`).
* **Repositories:** Responsible for Transaction Management & Persistence.
* **AuditLogger:** Responsible for Diffing & History.
* **Services:** Responsible for Validation & Business Rules.

## 2. Phase 1: The Generic Foundation

### `GenericRepository` Interface

**Target File:** `src/data/repositories/generic_repository.py`

```python
class GenericRepository(ABC, Generic[T]):
    def __init__(self, connection, table_name: str, id_column: str, model_class: Type[T]):
        self.audit_logger = AuditLogger(connection)
        self.connection = connection

    # --- READ (Standard) ---
    def get_all(self) -> List[T]: ...
    def get_by_id(self, id: int) -> Optional[T]: ...

    # --- WRITE (With Audit Hooks) ---
    def insert(self, entity: T) -> int:
        """
        1. BEGIN TRANSACTION
        2. Execute SQL INSERT
        3. self.audit_logger.log_insert(table, id, entity.to_dict())
        4. COMMIT
        """
        ...

    def update(self, entity: T) -> bool:
        """
        1. Fetch `old_entity` (Standard get_by_id)
        2. BEGIN TRANSACTION
        3. Execute SQL UPDATE
        4. self.audit_logger.log_update(table, id, old_entity.to_dict(), entity.to_dict())
        5. COMMIT
        """
        ...

    def delete(self, id: int) -> bool:
        """
        1. Fetch `old_entity`
        2. BEGIN TRANSACTION
        3. Execute SQL DELETE
        4. self.audit_logger.log_delete(table, id, old_entity.to_dict())
        5. COMMIT
        """
        ...
```

## 3. Phase 2: Repository Specifications

### A. Aggregate Repositories (Complex)

*These repositories manage data across multiple tables. They **MUST** override `insert`, `update`, and `delete` to handle transactions manually.*

#### 1. `SongRepository`

* **Primary Table:** `Songs` (Joined with `MediaSources`)
* **Managed Relations (Junctions):**
  * `MediaSourceTags` (SourceID <-> TagID)
  * `MediaSourceContributorRoles` (SourceID <-> ContributorID, RoleID)
  * `RecordingPublishers` (SourceID <-> PublisherID)
* **Write Strategy (Override):**
  * **Insert/Update:** Must explicitly manage the `MediaSources` base row, then the `Songs` extension row, then sync all junction tables (Delete/Insert pattern recommended for Tags/Roles).
* **Custom Reads:**
  * `find_by_hash(audio_hash: str)`
  * `get_songs_by_criteria(filter_criteria: dict)` (Migrating legacy named queries)
  * `get_distinct_values(column: str)` (For FilterWidget)

#### 2. `ContributorRepository`

* **Primary Table:** `Contributors`
* **Managed Relations:**
  * `ContributorAliases` (One-to-Many)
  * `GroupMembers` (Self-Reference Junction)
* **Write Strategy (Override):**
  * **Insert:** Must handle `ContributorType` ('person' vs 'group'). If 'group', must process `GroupMembers`.
* **Custom Reads:**
  * `find_or_create(name: str)`: Essential for Import logic. Checks Aliases before creating new.
  * `find_by_name_fuzzy(name: str)`

#### 3. `AlbumRepository`

* **Primary Table:** `Albums`
* **Managed Relations:**
  * `AlbumPublishers` (Junction)
  * `SongAlbums` (Linking table to Songs - Note: Usually managed by SongRepo, but AlbumRepo may need to reorder tracks).
* **Write Strategy (Override):**
  * Sync `AlbumPublishers` on save.

### B. Simple Repositories

*These repositories map 1:1 to a table and should use the default `GenericRepository` implementation.*

#### 4. `PublisherRepository`

* **Primary Table:** `Publishers`
* **Scope:** Basic CRUD. Parent/Child hierarchy (`ParentPublisherID`) is self-contained in the table.

#### 5. `TagRepository`

* **Primary Table:** `Tags`
* **Scope:** Managing the Master Tag List.
* **Note:** `MediaSourceTags` is managed by `SongRepository`. `TagRepository` only manages the definitions (e.g., renaming "Rock" to "Classic Rock").

#### 6. `PlaylistRepository`

* **Primary Table:** `Playlists`
* **Managed Relations:** `PlaylistItems`.
* **Write Strategy (Override):**
  * `update`: Likely needs transaction support for reordering `PlaylistItems` (updating `PlaylistItemPosition`).

## 4. Phase 4: AuditLogger Logic

**Component:** `src/core/audit_logger.py`

**Responsibility:** The "Smart" half of the system.

### A. Reliability: Fail-Secure
**Policy:** "If I can't sign the logbook, I can't enter the building."
*   If the Audit Log write fails (e.g., database lock, syntax error), the **entire transaction MUST be rolled back**.
*   The `AuditLogger` must propagate exceptions, NOT suppress them.
*   The `GenericRepository` must catch these exceptions in the Transaction block and perform a `rollback()`.

### C. User Attribution Strategy
**Problem:** `ChangeLog` has no `UserID` column.
**Solution:** Linkage via `BatchID`.
1.  Every update generates a unique `BatchID` (UUID) stored in `ChangeLog`.
2.  The same `BatchID` is logged in `ActionLog` (as part of `ActionDetails` or a future column).
3.  `ActionLog` *does* have a `UserID` column.
4.  **Query:** To find who changed a field -> Join `ChangeLog` on `ActionLog` via `BatchID` (implicit) or Time Window.

### D. Database Schema (`ChangeLog`)
*Aligned with `DATABASE.md` (Table 17).*

```sql
CREATE TABLE ChangeLog (
    LogID INTEGER PRIMARY KEY AUTOINCREMENT,
    LogTableName TEXT NOT NULL,
    RecordID INTEGER NOT NULL,
    LogFieldName TEXT NOT NULL,
    OldValue TEXT,
    NewValue TEXT,
    LogTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    BatchID TEXT  -- UUID to group multiple field changes from one transaction
);
```

### B. The Diff Engine (`compute_diff`)

The core intelligence resides in `src/core/audit_logger.py`.

**Granularity Rule:**
Instead of storing a single JSON blob, `log_update` must explode the changes into multiple rows—one per changed field.

**Logic:**
1.  **Primitives:**
    *   `if old[key] != new[key]`: Insert 1 row (`LogFieldName`=key).
2.  **Lists (Tags/Publishers):**
    *   Compute `Added` and `Removed` sets.
    *   **Strategy:** We record the *entire* serialized list string as `OldValue` and `NewValue` to keep the simplified "Field changed" logic, OR we log distinct "ADD" / "REMOVE" actions if we move to `ActionLog`.
    *   **Decision:** For `ChangeLog`, we treat the list field (e.g., `tags`) as a string.
        *   Old: "Rock, Pop"
        *   New: "Rock, Pop, Jazz"
        *   This allows easy "Diff Viewing" in UI without complex JSON parsing.

### C. Class Interface

```python
class AuditLogger:
    def __init__(self, connection):
        self.conn = connection

    def log_insert(self, table: str, record_id: int, new_data: dict) -> None:
        """
        Action: 'INSERT'
        Logs with OldValue=None.
        """
        pass

    def log_update(self, table: str, record_id: int, old_data: dict, new_data: dict) -> None:
        """
        Action: 'UPDATE'
        1. Compares keys.
        2. Generates a BatchID (UUID).
        3. Inserts one row into ChangeLog per changed key.
        """
        pass

    def log_delete(self, table: str, record_id: int, old_data: dict) -> None:
        """
        Action: 'DELETE'
        1. Logs to `DeletedRecords` (Full Snapshot).
        2. Logs to `ChangeLog` (Change state to 'DELETED' or similar marker).
        """
        pass
```
