# 🏥 T-12 Side Panel Alpha Spec (Refined-Modal)

## Objective
Implement a collapsible, Field-Registry-driven side panel that shares the rightmost workspace with the Playlist. This reduces horizontal clutter and allows the user to switch between "Playing" and "Editing" modes.

## 🏛️ Layout Architecture (The Stacked Right Wing)
- **Left**: `FilterWidget`.
- **Center**: `Library Table`.
- **Right**: `RightPanelStack` (New Container).
  - Top: `ModeSelector` (QTabBar with "Playlist" and "Editor" tabs).
  - Bottom: `QStackedWidget`.
    - Page 0: `PlaylistWidget`.
    - Page 1: `SidePanelWidget` (The Metadata Editor).
   ## 🧠 State & Safety (Focus Protection)
1. **Staging Buffer (`_staged_changes`)**: 
   - A dictionary: `{song_id: {field_name: value}}`.
   - Changes are only written to the DB/ID3 when "SAVE ALL" is clicked.
2. **Persistence on Selection Loss**: 
   - If selection becomes 0, the panel shows "No Selection" but the `_staged_changes` for the previous ID remain in memory. 
   - If the user re-selects the previous song, the staged edits reappear.
3. **Dirty Indicators**: 
   - Table rows for `song_id` present in `_staged_changes` are tinted orange.
   - The "Editor" tab on the Right Panel glows or shows an asterisk `Editor*`.
4. **App Shutdown Safety**: 
   - `MainWindow.closeEvent` must check if `_staged_changes` is non-empty.
   - Prompt: "You have unsaved metadata changes for X songs. Save them before exiting?"

## 👥 Multi-Selection Logic (Bulk Mode)
- **Selection Change**: 
  - 0-1 songs -> Single Mode.
  - 2+ songs -> Bulk Mode.
- **Bulk Dynamics**:
  - If values across selection differ: Placeholder shows `(Multiple Values)`.
  - **Manual Override**: Typing in a "Multiple Values" field marks that field to be overwritten for the **entire selection** upon save.
  - **Relational Fields**: (Alpha) Bulk-assigning Genres/Albums is supported; bulk-assigning Titles/Paths is blocked.

## ⚡ The "Done" Workflow (Backlog Chain)
1. **Validation Gate**:
   - The `MARK DONE` button is **gated** by `yellberus` requirements. 
   - It remains disabled until all `required=True` fields for the selection are satisfied.
2. **State Transition**:
   - Marking as "Done" toggles the `is_done` bit in the Staging Buffer.
   - It does **not** commit to the DB until the user clicks `SAVE` (or if `MARK DONE` is configured as a `SAVE & ADVANCE` macro).
3. **Status Sync**: 
   - A song with `is_done=0` is considered "For Review" (Alpha status).
   - A song with `is_done=1` is "Library Ready".
4. **Action (The Leap)**: 
   - After a successful `SAVE` where `is_done` transition was recorded:
   - Determine the next row index in the `Library Table`.
   - Update selection to the next row (Auto-Advance).

## 🛡️ Technical Ledger (Rules of the Machine)
- **Field Sync**: If a field is edited in the Side Panel, the corresponding cell in the Table does NOT update until "SAVE" is clicked (preventing table-flicker during typing).
- **ID3 Priority**: Side Panel strictly enforces Yellberus portability. If `portable=True`, the field **WILL** be written to ID3; if `False`, it remains local to DB. No manual override (Alpha).
- **Strict Validation**:
  - **Year**: Must be between 1860 and Current Year + 1. (Abort Save).
  - **ISRC**: Must match alphanumeric regex standard. (Abort Save).
  - **Unified Artist**: "Mark Done" is disabled unless Performer OR Group exists.
- **Shortcuts**: `Ctrl+S` commits staged changes in the Side Panel (if visible/focused).
- **Bulk Set Operations (Future)**: 
  - (Alpha): Bulk edits are **Overwrite-only**. Replacing a field replaces it for all selected souls.
- **Focus Safety**: Pressing `Escape` in any Side Panel line-edit discards changes for that specific field.
- **Garbage Collection**: If a song is deleted from the library, it is immediately removed from `_staged_changes`.

## 🛠️ Implementation Protocol (Phased Burial)

### Phase 1: The Right Wing Container
- [x] Refactor `MainWindow` to replace `PlaylistWidget` with `RightPanelContainer`.
- [x] Implement `QTabBar` ("Playlist" / "Editor") and `QStackedWidget`.
- [x] Basic Tab switching logic with state persistence in `SettingsManager`.

### Phase 2: Selection & Context
- [x] Connect `library_widget.selectionChanged`.
- [x] Fix the `LibraryWidget` row-retrieval to fetch real `Song` objects (or IDs).
- [x] Side Panel `set_songs(songs)`: Update Header and clear/prep staging for the selection.

### Phase 3: The Surgical Table (Fields)
- [x] Logic to iterate `yellberus.FIELDS` and generate `QLineEdit` (Alpha) or `QCheckBox`.
- [x] Mapping logic: Registry Strategy -> Qt Widget.
- [x] "Core" vs "Advanced" field grouping (Collapsible sections).

### Phase 4: The Staging Buffer
- [x] Implement `_staged_changes` dictionary in `SidePanelWidget`.
- [x] Dirty row highlighting: Tinting table rows in `LibraryWidget` based on IDs in the staging buffer.
- [x] Implement `Escape` revert logic per field.

### Phase 5: The Done Gate (Logic)
- [x] Real-time validation: Check `required=True` across the current selection.
- [x] Enable/Disable `MARK DONE` button based on validation.
- [x] Toggle `is_done` bit in staging buffer.

### Phase 6: The Great Burial (Save & Advance)
- [x] Implement `SAVE ALL` logic: Loop through buffer, call `LibraryService.update_song`.
- [x] Trigger ID3 export for portable fields.
- [x] **Auto-Advance**: Logic removed per user request (Selection persists after save).
- [x] **New**: `Ctrl+S` shortcut triggers save.
- [x] **New**: Strict Validation (Year/ISRC) aborts save on error.
- [x] Cleanup buffer for the saved IDs.
