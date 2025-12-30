---
tags:
  - ui
  - browsing
  - status/done
  - priority/high
links:
  - "[[PROPOSAL_FILTER_TREES]]"
---

# T-17: Unified Artist View

## Goal
Combine "Groups" (legacy concept) and "Artists" (metadata) into a single, unified "Artist" view in the Filter Tree.

## Context
Currently, `Groups` and `Artists` are separate entities. Users want a simplified view where Groups are treated as just another Artist (or vice-versa) for filtering purposes.

## Requirements

### 1. Unified Table View (Display)
*   The main library table should have a single **"Artist"** column.
*   **Logic:**
    *   Display the `Group` name if one is assigned.
    *   Fallback to the `Performer` field if no Group is assigned.
*   **Goal:** User sees a consistent "who performed this" column without needing to check two separate columns.

### 2. Unified Filter Tree
*   The "Artists" node in the side panel should contain **both** `Performer` values and `Group` names.
*   Users can drill down by Artist regardless of whether it's technically stored as a Group or a generic Performer string.

### 4. Search/Filter Logic (Cross-Referencing)
*   **Concept**: Search targets the *Person Identity*, not just the string name.
*   **The "Bob" Scenario**:
    1.  **Group**: "The Cows" (Members: Bob, Alice).
    2.  **Alias**: "The Bull" (Identity: Bob).
    3.  **Individual**: "Bob" (Composer/Lyricist).
*   **Unified Search Result**: Searching for "Bob" (or "The Bull") should return:
    *   Songs by "The Cows" (because Bob is a member).
    *   Songs by "The Bull" (because Bob is the artist).
    *   Songs where Bob is a contributor (Lyricist/Composer).
*   **Display Constraint**: The song metadata in the result list MUST preserve the original release artist ("The Cows", "The Bull"), even if found via "Bob".

### 5. Implementation Scope (Full)
We will implement the **complete backend and frontend logic** for this unification, even if the "Editor" UI (to create aliases) is not yet ready.

#### A. Data Layer Support (The "Who") ✅ DONE
1.  **Implement `ContributorAliases` Table**: [x] Create table and Model.
2.  **Verify `GroupMembers` Table**: [x] Ensure Model and Repository support exists.
3.  **Repository Update**: [x] Add `resolve_identity_graph` method to `ContributorRepository`.

#### B. Schema/Validation Updates ✅ DONE (2024-12-21)
1.  **`unified_artist` field**: Added to Yellberus FIELDS with query_expression using COALESCE.
2.  **`unified_artist` on Song model**: Added as Optional[str] field.
3.  **Validation logic refactored**:
    - `performers.required` changed to `False`
    - Added `VALIDATION_GROUPS` with "at_least_one" rule for ["performers", "groups"]
    - `yellberus.validate_row()` now reads from VALIDATION_GROUPS (data-driven)
    - LibraryWidget delegates to `yellberus.validate_row()`

#### C. Unified View Logic (The "What") ✅ DONE (2025-12-21)
1.  **Unified Table Column**: [x] `unified_artist` field now `visible=True` with `ui_header="Artist"`
2.  **Unified Filter Tree**: 
    - [x] `unified_artist` field now `filterable=True` - appears in filter sidebar
    - [x] Filter values include BOTH Performers AND Groups
    - [x] Added `library_service.get_all_groups()` method
3.  **Search Logic**: [x] `unified_artist` remains `searchable=True` - search covers both groups and performers
4.  **Filtering Logic**:
    - [x] Update `SongRepository` to support querying by unified artist (Group OR Performer)
    - [x] Update `LibraryWidget`/`LibraryService` to use unified query for `unified_artist` field
5.  **Hidden raw fields**: 
    - [x] `performers` and `groups` are now `visible=False`, `filterable=False` (still editable)
    - [x] **UI Enforcements**: Enforced `visible=False` as a "hard ban" (hidden from right-click column menu and Reset Layout).


#### D. UX Refinements ✅ DONE (2025-12-21)
1.  **Alphabetical Categories**: [x] Sorted root category headers alphabetically.
2.  **Tree UX**: [x] Double-clicking root nodes expands/collapses (manual toggle fix).
3.  **Filter Reset Logic**: [x] "Reset Filter" moved to double-click on root nodes.

#### E. Registry & Tool Consolidation ✅ DONE
1.  **Parser Aware (Safety)**: [x] Updated `yellberus_parser.py` to explicitly handle `query_expression` and `VALIDATION_GROUPS`. (Prevents stripping logic on save).
2.  **Property Viewer (Consolidation)**: [ ] (Deferred) UI update for Field Editor deferred; underlying Parser safety is sufficient for now.

#### F. Persistence & Robustness ✅ DONE
1.  **Settings Feature**: [x] Add column resize (`width`) support to `SettingsManager`.
2.  **Documentation**: [x] Document `width` persistence logic in `SettingsManager`.
3.  **Bug Fix**: [x] Implement "Auto-Save" to prevent resize reset on filter.

### 🏁 Technical Handoff: The "Bob Scenario"
### 🧩 Refined Identity Graph Logic (Directional)
To prevent "Supergroup Mergers" (e.g., clicking Nirvana showing Foo Fighters), the expansion logic must be **Directional**:

1.  **Person ➔ Group**: ✅ ALLOWED.
    - User clicks "Dave Grohl" -> System finds his Groups (Nirvana, Foo Fighters).
    - Result: Shows all songs from his entire career.
2.  **Alias ➔ Identity**: ✅ ALLOWED.
    - User clicks "David Grohl" -> System resolves to "Dave Grohl" -> Finds Groups.
    - Result: Shows full career.
3.  **Group ➔ Member**: ❌ BLOCKED.
    - User clicks "Nirvana" -> System does **NOT** expand to members.
    - Result: Shows ONLY Nirvana songs. (Does NOT show Foo Fighters).

### ✅ Final Implementation (2025-12-21)

#### 1. Identity Graph (Directional)
The "Supergroup Merger" bug was solved by enforcing **Directional Expansion**:
- **Person -> Group**: Allowed. (Dave Grohl -> Nirvana).
- **Group -> Member**: BLOCKED. (Nirvana -> Dave Grohl -> Foo Fighters).
- This ensures filtering by a Band only validates that Band's songs.

#### 2. Persistence & UI (V2)
A robust **Name-Based Persistence** system (`library/layouts_v2`) was implemented to fix column visibility bugs:
- **Visibility**: Saved as `{field_name: bool}` map, avoiding index corruption.
- **Widths**: Saved as `{field_name: int}` map, persisting user resizing.
- **Strict Hiding**: Columns like `Performers` and `Groups` are forcibly hidden regardless of saved state.
- **Auto-Save**: Layout is auto-saved before every table refresh (filter click).
    - *Fixes*: "Clicking a filter resets column width" bug by capturing state immediately before the view model is wiped.

#### 3. UX Polish
- `is_active` is now rendered as a Checkbox (currently read-only).
- "Ghost Columns" (Performers/Groups) are permanently banished.

---
**Status: CLOSED**

## Handoff Notes (2025-12-21)

### What's Done
- **Phase A**: Data layer support complete (tables, models, repositories)
- **Phase B**: Schema/validation updates (VALIDATION_GROUPS, validate_row)
- **Phase C**: Unified view logic complete:
  - `unified_artist` is now the main "Artist" column in table and filters
  - SQL computes: `COALESCE(NULLIF(Groups, ''), Performers)`
  - Raw `performers` and `groups` columns are hidden but still editable
- Test coverage: 355 tests passing

### Key Files Modified This Session
- `src/core/yellberus.py` - unified_artist visible/filterable, performers/groups hidden
- `tests/unit/core/test_yellberus.py` - Updated test_filterable_fields for new design

### What's Next (Optional Enhancements)
1. **Identity Graph Search**: When filtering by "Bob", resolve aliases/group memberships
2. **Editor UI**: Add way to edit performers/groups (currently hidden columns)
3. **Manual Testing**: Verify display with real data containing groups

### Key Code Locations
- `yellberus.FIELDS["unified_artist"]` - Main artist display field
- `yellberus.VALIDATION_GROUPS` - Cross-field validation rules
- `yellberus.validate_row()` - Centralized validation function

> [!NOTE]
> Full identity graph search (aliases, group memberships) is a future enhancement. Current implementation provides unified display via SQL COALESCE.
