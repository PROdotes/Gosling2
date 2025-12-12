# Migration Gaps & Feature Discrepancies

This document tracks features and behaviors from the old `main.py` that have not yet been fully ported or have been modified in the new architecture.

## 🛑 Missing Features

### 1. Context Menu: "Show ID3 Data"
- **Old Behavior**: Right-clicking a song in the library offered a "🔍 Show ID3 Data" option. This opened a popup displaying raw metadata (File, Title, Performers, Duration, BPM) extracted directly from the file.
- **New Behavior**: The context menu only offers "Delete" and "Add to Playlist".
- **Action**: Add `_show_id3_tags` logic to `LibraryWidget`.

### 2. Library Edit Mode
- **Old Behavior**: A button "📝 Library Edit Mode: OFF/ON" allowed users to toggle inline editing of the library table. Signals connected to `_handle_cell_edit_logging`.
- **New Behavior**: `LibraryWidget` sets `setEditTriggers(QTableView.EditTrigger.NoEditTriggers)`, permanently disabling invalid editing.
- **Action**: Decide if inline editing is still desired. If so, implement an edit toggle and update `SongRepository.update()` connections.

### 3. Crossfade Support
- **Old Behavior**: `main.py` included a `self.crossfade_timer` and `_crossfade_to_next` logic to smoothly transition between tracks.
- **New Behavior**: `PlaybackService` handles standard `play()`, `pause()`, and simple track switching. Crossfading logic appears to be missing.
- **Action**: Implement crossfade logic in `PlaybackService`.

### 4. Numeric Sorting
- **Old Behavior**: Columns like Duration, BPM, and FileID sorted numerically (2 < 10).
- **New Behavior**: `LibraryWidget` currently converts all data to strings, causing lexical sorting ("10" < "2").
- **Action**: Update `_populate_table` in `LibraryWidget` to set `Qt.ItemDataRole.UserRole` with numeric values for relevant columns.

### 5. Composer Filtering
- **Old Behavior**: The tree view had a "Composers" node alongside "Performers".
- **New Behavior**: `FilterWidget` only loads "Performers" (labeled as "Artists").
- **Action**: Add logic to `FilterWidget.populate()` to fetch and list Composers.

### 6. UI Styling (Green Buttons)
- **Old Behavior**: Play/Pause and Skip buttons had a distinct green background (`#5f8a53`).
- **New Behavior**: `PlaybackControlWidget` buttons use default system styling (or simple size adjustments) without the green color.
- **Action**: Update `media_button_style` in `PlaybackControlWidget` to include `background-color: #5f8a53; color: white; border-radius: 10px;`.

### 7. Settings Migration (Key Mismatch)
- **Old Behavior**: Settings were saved as top-level keys (`"geometry"`, `"splitter_state"`).
- **New Behavior**: `SettingsManager` uses namespaced keys (`"window/geometry"`, `"window/mainSplitterState"`).
- **Consequence**: Existing user preferences (window size, layout) will **reset** to defaults upon first run.
- **Action**: Either update `SettingsManager` to check for legacy keys and migrate them, or accept the reset.

## ⚠️ Changed Implementations

### 4. Filter Tree Structure
- **Old Behavior**: The tree view showed two root nodes: "Performers" and "Composers", populated directly from the database.
- **New Behavior**: `FilterWidget` groups artists alphabetically (A-Z) under a single "Artists" root. "Composers" are currently not listed.
- **Action**: Verify if the alphabetical grouping is preferred or if "Composers" need to be added back.

### 5. Search Functionality
- **Old Behavior**: Search used regex filtering. When filtering by a tree node (e.g., a specific artist), the search bar would filter *within* that artist's songs.
- **New Behavior**: Search uses simple wildcard matching (`*{text}*`). Searching might reset or conflict with tree filters depending on exact usage.
- **Action**: Review `QSortFilterProxyModel` logic in `LibraryWidget` to ensure advanced filtering needs are met.

### 6. "Scan Folder" Error Handling
- **Old Behavior**: Contained specific error handling and summaries for `insert_file_basic` failures.
- **New Behavior**: `LibraryWidget` creates a summary, but deeper error handling logic might differ.
- **Action**: Verify robustness of `LibraryService` error reporting during bulk imports.

## ✅ Safe to Remove
Despite the above gaps, the core logic has been ported. The `old/` directory can be deleted if you are comfortable implementing the missing features from scratch or referencing this document.

- `old/Song.py` -> `src/data/models/song.py`
- `old/db_manager.py` -> `src/data/repositories/`
- `old/main.py` -> `src/presentation/` & `src/business/`
