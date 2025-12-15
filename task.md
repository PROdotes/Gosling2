# Feature Implementation Checklist (Ordered by Complexity)

This list prioritizes features from **Easiest** (Quick Wins) to **Hardest** (Complex Logic).
**Strategy**: "Feature-First". Build the UI/Logic first, let the tests fail, then update the Database.

---

## 🟢 1. Drag & Drop Import (Issue #8)
**Complexity**: ⭐ (Easy)
**Focus**: pure UI, no Database changes.
- [x] Implement `dragEnterEvent` in `LibraryWidget` (MP3 Only).
- [x] Implement `dropEvent` in `LibraryWidget`.
- [x] Verify imports work.
- [x] **UX**: Add visual highlight (border) on drag hover.
- [x] **UX**: Show import result feedback (count) on drop.
- [x] **UX**: Show import result feedback (count) on drop.
- [x] **ZIP Support**: Atomic Extract & Delete.
    - [x] Accept `.zip` in `dragEnterEvent`.
    - [x] `_handle_zip_drop`: Check exists -> Warn or (Extract + Import + Delete).
    - [x] Update tests (Mock `zipfile`, `os.remove`, `QMessageBox`).

## 🟢 1b. Incomplete Song Filter (Request)
**Complexity**: ⭐ (Easy)
**Focus**: Metadata Quality Assurance.
- [x] Create `completion_criteria.json`.
- [x] Implement Logic & UI (Toggle + Highlighting).
- [x] Verify Schema Sync (`test_criteria_sync.py`).
- [x] Verify Filtering & UI (`test_library_widget_filtering.py`).

## � 1c. Crossfade Controls Refactor (Request)
**Complexity**: ⭐ (Easy)
**Focus**: UI/UX & Reliability.
- [x] Replace Checkbox with Dropdown (0s, 1s, ..., 10s).
- [x] Fix Regression: Skip button disabled when Off (0s).
- [x] Verify with `tests/unit/presentation/widgets/test_playback_control_widget.py`.

## �🟡 2. Library Item Types (Issue #6)
**Complexity**: ⭐⭐ (Medium)
**Focus**: Distinguishing Songs vs. Jingles vs. Spots.
- [ ] **Step 1 (Model)**: Add `item_type` field (Enum) to `Song` class.
- [ ] **Step 2 (Safety Check)**: Run `test_schema_model_cross_ref.py` -> **EXPECT FAIL**.
- [ ] **Step 3 (DB)**: Add `Type` column to `Files` table in `BaseRepository`.
- [ ] **Step 4 (UI)**: Add "Type" column to Library View.
- [ ] **Step 5 (UI)**: Add Filter Tabs (Songs | Jingles | Spots) to `LibraryWidget`.

## 🟡 3. Cue Points & metadata (Issue #3)
**Complexity**: ⭐⭐⭐ (Medium)
**Focus**: Precise timing for radio transitions.
- [ ] **Step 1 (Model)**: Add `cue_in`, `cue_out`, `intro` fields to `Song` class.
- [ ] **Step 2 (Safety Check)**: Run `test_schema_model_cross_ref.py` -> **EXPECT FAIL**.
- [ ] **Step 3 (DB)**: Add `CueIn`, `CueOut`, `Intro` columns to `Files` table.
- [ ] **Step 4 (UI)**: Create the **Side-Panel Editor** (Right side of Library).
    - [ ] Sliders for Cue Points.
    - [ ] Time Entry fields.
    - [ ] "Test Cues" buttons (Play Intro, Play Segue).

## 🔴 4. Scheduling Basics (Issue #4)
**Complexity**: ⭐⭐⭐⭐⭐ (Hard)
**Focus**: Defining "The Day".
- [ ] **Phase Constants**: Create `AutomationPhase` Enum (Morning, Night).
- [ ] **Clocks Table**: Create Schema for `Clocks` (Hour Templates).
- [ ] **Clock Editor UI**: Create Widget to build clocks visually.

---

## 🧪 Safety Checks
Run these after *every* change:
```bash
pytest tests/unit/data/test_schema_model_cross_ref.py
```
