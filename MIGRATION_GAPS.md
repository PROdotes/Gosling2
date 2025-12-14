# Migration Gaps & Feature Discrepancies

This document tracks features and behaviors from the old `main.py` that have not yet been fully ported or have been modified in the new architecture.

## 🛑 Functionality Gaps

### 1. Crossfade Support
- **Old Behavior**: `main.py` included a `self.crossfade_timer` and `_crossfade_to_next` logic to smoothly transition between tracks.
- **New Behavior**: `PlaybackService` handles standard `play()`, `pause()`, and simple track switching. Crossfading logic is currently missing.
- **Action**: Implement crossfade logic in `PlaybackService`.

### 2. Numeric Sorting
- **Old Behavior**: Columns like Duration, BPM, and FileID sorted numerically (2 < 10).
- **New Behavior**: `LibraryWidget` currently converts all data to strings, causing lexical sorting ("10" < "2").
- **Action**: Update `_populate_table` in `LibraryWidget` to set `Qt.ItemDataRole.UserRole` with numeric values for relevant columns.

### 3. Library Edit Mode (🚧 DEFERRED / FUTURE WORK)
- **Old Behavior**: A button "📝 Library Edit Mode: OFF/ON" allowed users to toggle inline editing of the library table.
- **New Behavior**: `LibraryWidget` sets `setEditTriggers(QTableView.EditTrigger.NoEditTriggers)`.
- **Reason**: Inline editing requires robust ID3 tag writing capabilities (`MetadataWriterService`), which are currently not implemented. Enabling DB-only edits would cause synchronization issues.
- **Action**: Deferred until metadata writing infrastructure is built.

### 4. Search Functionality (✅ COMPLETED)
- **Old Behavior**: Search used regex filtering.
- **New Behavior**: `LibraryWidget` now uses `setFilterRegularExpression` instead of wildcard, restoring full regex capabilities (e.g., `^The`, `Queen|Bowie`).
- **Action**: Updated `_on_search` to use `setFilterRegularExpression`. Validated with tests.

## 🎨 UI & Navigation Changes

### 5. Composer Filtering & Tree Structure (✅ COMPLETED)
- **Old Behavior**: The tree view displayed two root nodes directly from the database: "Performers" and "Composers".
- **New Behavior**: `FilterWidget` loads both "Performers" and "Composers", grouped alphabetically (A-Z).
- **Action**: Refactored `FilterWidget` to support generic roles and implemented `get_songs_by_composer` pipeline. Renamed "Artist" to "Performer" codebase-wide.

### 6. Context Menu: "Show ID3 Data" (✅ COMPLETED)
- **Old Behavior**: Right-clicking a song in the library offered a "🔍 Show ID3 Data" option. This opened a popup displaying raw metadata (File, Title, Performers, Duration, BPM) extracted directly from the file.
- **New Behavior**: The context menu now includes "Delete", "Add to Playlist", and "Show ID3 Data".
- **Action**: `_show_id3_tags` logic added to `LibraryWidget` and `MetadataViewerDialog` implemented.



## ✅ Safe to Remove
Despite the above gaps, the core logic has been ported. The `old/` directory can be deleted if you are comfortable implementing the missing features from scratch or referencing this document.

- `old/Song.py` -> `src/data/models/song.py`
- `old/db_manager.py` -> `src/data/repositories/`
- `old/main.py` -> `src/presentation/` & `src/business/`
