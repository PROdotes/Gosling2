# Architectural Proposal: Transaction Log

## Objective
Implement a multi-purpose audit and undo system at the data layer.

---

## 📍 Phase 1: Log Core (Foundation)

**Goal:** Create the ChangeLog table and basic field logging.

**Scope:**
- `ChangeLog` table with: LogID, TableName, RecordID, FieldName, OldValue, NewValue, Timestamp, BatchID
- Logging intercepts `update()` calls in repositories
- Single SQLite transaction wraps update + log entry

**Schema:**
```sql
CREATE TABLE ChangeLog (
    LogID INTEGER PRIMARY KEY,
    TableName TEXT NOT NULL,
    RecordID INTEGER NOT NULL,
    FieldName TEXT NOT NULL,
    OldValue TEXT,
    NewValue TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    BatchID TEXT
);
```

**Complexity:** 2 · **Estimate:** 1-2 days

### Checklist
- [ ] Create ChangeLog table in schema
- [ ] Add logging hook in BaseRepository
- [ ] Fetch existing value before update
- [ ] Wrap update + log in transaction
- [ ] Generate BatchID for grouped changes

---

## 📍 Phase 2: Undo Core (Foundation)

**Goal:** Simple single-field revert capability.

**Scope:**
- Query most recent log entry for a field
- Apply `OldValue` back to record
- Create new log entry marking the revert

**Implementation:**
- `revert_change(log_id)` method
- Validation: check current value matches NewValue
- Conflict warning if value has changed since log

**Complexity:** 2 · **Estimate:** 1 day

**Depends on:** Log Core

### Checklist
- [ ] Implement `revert_change(log_id)`
- [ ] Validate current value before revert
- [ ] Create audit entry for revert action
- [ ] Add `RevertRefID` column to link to original

---

## 📍 Phase 2.5: Deletion Recovery (Safety Net)

**Goal:** Enable full restoration of deleted records and their relationships.

**Problem:** When someone deletes "Sandstorm", ON DELETE CASCADE wipes:
- MediaSources row
- Files row
- Songs row
- SongGenres, SongLanguages, SongAlbums, MediaSourceTags, MediaSourceContributorRoles

All gone. Millions of voices cry out in pain.

**Solution:** Before any delete, snapshot the entire object graph:

**Schema:**
```sql
CREATE TABLE DeletedRecords (
    DeleteID INTEGER PRIMARY KEY,
    TableName TEXT NOT NULL,       -- 'MediaSources', 'Songs', etc.
    RecordID INTEGER NOT NULL,
    FullSnapshot TEXT NOT NULL,    -- JSON of record + all related data
    DeletedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    RestoredAt DATETIME,           -- NULL until restored
    BatchID TEXT                   -- Groups cascaded deletes
);
```

**FullSnapshot example:**
```json
{
  "MediaSources": {"SourceID": 42, "Name": "Sandstorm", "TypeID": 1, ...},
  "Files": {"Path": "/music/sandstorm.mp3", "Duration": 234, ...},
  "Songs": {"TempoBPM": 136, "ISRC": "...", ...},
  "SongGenres": [{"GenreID": 5}, {"GenreID": 8}],
  "SongLanguages": [{"LanguageID": 2}],
  "MediaSourceContributorRoles": [{"ContributorID": 10, "RoleID": 1}]
}
```

**Restoration Logic:**
1. Restore parent record first (MediaSources)
2. Restore child records (Files, Songs)
3. Restore junction records (SongGenres, etc.)

**Edge Cases:**
- **ID conflicts:** If original SourceID is reused, assign new ID and update all references
- **Missing references:** If referenced record (Genre, Contributor) was also deleted:
  - Check if it exists in DeletedRecords
  - Prompt user to restore dependencies first
  - Or skip broken references with warning
- **Playlist restoration with deleted songs:**
  - Show playlist with "1 song missing" indicator
  - Attempt to match by Source path (file location)
  - If song was re-imported with new ID, offer to link
  - **If file exists on disk but not in DB**, offer to restore from DeletedRecords
  - Otherwise, leave PlaylistItem with broken reference (can be cleaned up later)

**Implementation:** Repository method `restore_deleted(DeleteID)` handles cascade logic.
- `delete()` calls `snapshot_record()` first
- Stores JSON blob in DeletedRecords
- Proceeds with actual deletion
- `restore_deleted(delete_id)` recreates record from snapshot

**Complexity:** 3 · **Estimate:** 2 days

**Depends on:** Log Core

### Checklist
- [ ] Create DeletedRecords table
- [ ] Implement `snapshot_record(source_id)` to collect full graph
- [ ] Store JSON snapshot before delete
- [ ] Implement `restore_deleted(delete_id)`
- [ ] Handle ID conflicts on restore (new ID vs original ID)
- [ ] Mark as restored (don't delete log entry)

---

## 📍 Phase 3: Relational Logging (Advanced)

**Goal:** Handle junction tables and hierarchies.

**Scope:**
- **Entity Edits:** Log changes to Publishers, Albums, Genres
- **Junction Edits:** Log link creation/deletion (FileAlbums, FileGenres)
- **Hierarchy Edits:** Log parent changes in recursive structures

**Implementation:**
- RecordID for junctions: `"10:45"` composite string
- FieldName for links: `"__link__"`
- Snapshot metadata in OldValue/NewValue

**Complexity:** 4 · **Estimate:** 2-3 days

**Depends on:** Undo Core, Schema Update

### Checklist
- [ ] Junction table logging
- [ ] Composite RecordID format
- [ ] Hierarchy parent change logging
- [ ] Cascade revert for bulk operations

---

## 📍 Phase 4: Audit UI (Feature)

**Goal:** User-facing history views.

**Scope:**
- **Micro View:** Right-click song → "View History"
- **Macro View:** Global activity feed with BatchID grouping
- **Entity View:** Publisher/Album/Genre history

**Implementation:**
- `HistoryDialog` with tabbed views
- Pull-through query joining relevant logs
- Expandable batch rows

**Complexity:** 3 · **Estimate:** 2-3 days

**Depends on:** Relational Logging

### Checklist
- [ ] Song history dialog
- [ ] Global activity panel/tab
- [ ] Entity history dialog
- [ ] BatchID grouping UI
- [ ] One-click batch undo

---

## Extended Features (Future)
- `ChangedBy` column for user/script identification
- `Comment` column for change justification
- Archival: move logs older than 90 days to compressed JSON
- Computed timestamps: derive "Added"/"Modified" from log queries
