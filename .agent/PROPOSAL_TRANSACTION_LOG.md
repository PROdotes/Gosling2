# Architectural Proposal: Universal Transaction Logging

## Objective
Implement a multi-purpose audit and undo system at the data layer.

## 1. Database Schema
A single centralized `ChangeLog` table for all entities.

| Column | Type | Description |
| :--- | :--- | :--- |
| `LogID` | INTEGER (PK) | Unique ID |
| `TableName` | TEXT | 'Files', 'Contributors', 'Albums', etc. |
| `RecordID` | INTEGER | The ID of the modified row. |
| `FieldName` | TEXT | The specific column name that changed. |
| `OldValue` | TEXT | Stringified value before change. |
| `NewValue` | TEXT | Stringified value after change. |
| `Timestamp` | DATETIME | DEFAULT current_timestamp |
| `BatchID` | TEXT (UUID) | Groups simultaneous changes (e.g., bulk editing 50 tracks). |
| `RevertRefID` | INTEGER | Links a Revert action back to the original entry (ref: ChangeLog.LogID). |
| `ChangedBy` | TEXT | Identifies the User or Script/Process that made the change. |
| `Comment` | TEXT | Optional user-provided reason/justification for the change. |

## 2. Integration: The "Audited Repository"
The logging logic should live in the `BaseRepository` or be triggered by the `Field Registry`.

- **Mechanism:**
    1.  Intersects `update()` calls.
    2.  Fetches existing value for comparison.
    3.  If a change is detected, generates a `ChangeLog` entry.
    4.  Wraps both the Update and the Log entry in a **single SQLite transaction** (Atomic).

## 3. The Undo Logic
Reverting a change is a simple mathematical inverse:
- Select most recent `ChangeLog` entries for a set of IDs.
- Execute `UPDATE [TableName] SET [FieldName] = [OldValue] WHERE [RecordID] = [ID]`.

## 4. Performance & Storage
- **Bloat Prevention:** Add a background task to prune logs older than $N$ days.
- **Selective Logging:** Not all fields need logging (e.g., `last_played_at`). This is controlled by a flag in the `Field Registry`.

## 5. System Event Logging
Beyond individual field changes, the `ChangeLog` table can also capture "Macro Events":
- **Library Rescan:** Start/Stop times and result (e.g., "5 files added").
- **Physical Moves:** When a file is moved on disk by the app.
- **Backup/Restore:** Date and status of database maintenance.
- **Reporting:** Each event is tagged as `FieldName = 'SYSTEM_EVENT'`.

## 6. Long-term Archival (The Permanent Record)
To prevent the main database from slowing down over time:
- **Active Logs:** Keep the last 90 days in the `ChangeLog` table for instant undo.
- **Archive Files:** Move older logs to a compressed JSON or CSV "Archive File" (e.g., `logs_2024.json.gz`).
- **Persistence:** These archives are kept forever, satisfying the most extreme archivist requirements.

## 7. Relational & Junction Logging

To handle the complex relationships defined in `DATABASE.md` (Many-to-Many, Hierarchies), the Log must distinguish between entity edits and link edits.

### A. Entity Edits (e.g., Rename Publisher)
- **Target:** The actual entity table (`Publishers`, `Albums`, `Genres`).
- **Logic:** Changing a Publisher's name logs ONE entry in the `Publishers` table.
- **Impact:** Reverting this single entry updates every song linked to it.

### B. Junction Edits (e.g., Add Song to Album)
- **Target:** Junction tables (`FileAlbums`, `FileGenres`, `GroupMembers`).
- **RecordID:** `[ID_A]:[ID_B]` (Standardized composite string).
- **FieldName:** Internal flag (e.g., `__link__`).
- **Metadata:** For better UX, the log should store a "Snapshot" of the link's name:
    - `OldValue`: NULL
    - `NewValue`: "Greatest Hits [AlbumID: 44]"

### C. Hierarchical Edits (e.g., Move Subsidiary)
- **Target:** `Publishers` table.
- **FieldName:** `ParentPublisherID`.
- **Value:** Logs the ID of the parent.
- **Undo:** Reverting this instantly moves the entire branch of the publisher tree back to its original parent.

## 8. Audit Visualization
When viewing the history of a **Song**, the UI should "Pull Through" all relevant log entries:
1. Changes to the `Files` row directly.
2. Changes to any `FileAlbums` link involving this song.
3. Changes to any `Genres` links involving this song.

## 9. Access Patterns (User Interface)

The system should expose the history through three distinct lenses:

### A. The Micro View (Song History)
- **Trigger:** Right-click Song -> "View History".
- **Content:** The life story of one specific file.
- **Use Case:** "Why did this song's BPM change last week?"

### B. The Macro View (Global Activity Feed) 📡
- **Trigger:** Side-panel tab or Menu Item "Activity Log".
- **Content:** A chronological list of EVERY change in the database.
- **Grouping:** Uses `BatchID` to group bulk edits into single expandable rows.
- **Use Case:** "I accidentally bulk-edited 100 songs 5 minutes ago. Let me find that batch and undo the whole thing."

### C. The Entity View (Relational History)
- **Trigger:** Right-click Publisher/Album/Genre -> "View History".
- **Content:** Changes specifically related to that entity (e.g., name changes, subsidiary moves).
- **Use Case:** "When was this label folder moved under Universal?"

## 10. Reversion Logic & Safety Rules

Reverting is not just "flipping a switch"; it must be handled as a fresh data operation that preserves historical context.

### A. The "Simple Undo" (Single Entry)
1. **Validation:** Check if `CurrentValue == NewValue` from the log.
2. **Conflict Handling:** If values differ, show warning: *"Current value has changed. Revert anyway?"*
3. **Justification:** Prompt user for an optional comment (e.g., *"Wrong convention used"*).
4. **Execution:** Apply `OldValue` to the record.
5. **Audit Linking:** Create a NEW Log entry with:
    - `RevertRefID` pointing to the original entry we are undoing.
    - `Comment` containing the user's justification.

### B. The "Batch Undo" (Bulk Recovery)
1. **Transaction:** Wrap entire operation in an atomic SQLite transaction.
2. **LIFO Order:** Revert fields in Last-In-First-Out order.
3. **Ghosting:** Offer to re-insert records that have been deleted since the log was created.

### C. The "ID3 Sync" Check
- Reverted database values are flagged as "Out of Sync" until a Metadata Export is performed.

## 11. Replacing Table-Level Timestamps

By implementing this granular log, we can eliminate the need for manual `created_at` and `updated_at` columns in every individual table.

- **"Added" Date:** Displayed in UI by querying `MIN(Timestamp)` for the specific RecordID.
- **"Modified" Date:** Displayed in UI by querying `MAX(Timestamp)` for the specific RecordID.
- **Performance Note:** If library scale (100k+ logs) causes sorting lag, we will implement a cached index in the `Files` table, but the Log remains the only source of verified historical truth.
