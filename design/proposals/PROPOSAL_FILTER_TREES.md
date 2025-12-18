---
tags:
  - layer/ui
  - domain/tags
  - domain/table
  - status/planned
  - type/feature
  - size/large
  - blocked/schema
links:
  - "[[DATABASE]]"
  - "[[PROPOSAL_TAG_EDITOR]]"
---
# Architectural Proposal: Filter Trees (Genre & Publisher)

## 🚧 Blocker Warning
**Status:** BLOCKED by Schema Update.
**Reason:** Current `Files` table stores genres as flat strings. Implementation requires normalized `Genres` and `Publishers` tables with Junctions to function correctly.

## 1. The Genre Tree
Since we decided in `DATABASE.md` that Genres are a flat list (to avoid "Is Deep House a child of House or Electronic?" debates), the "Tree" is actually a **Smart Tag Cloud**.

- **Structure:** Flat list of unique genres from the `Genres` table.
- **Interaction:**
    - Click "House": Shows songs linked to House.
    - Click "House" + "Vocal": Shows intersection (AND logic).
- **UI Widget:** `QListWidget` or Tag Cloud.

### Functional Requirements
- Hierarchical tree view (Genres, Decades, Moods)
- **Checkboxes for multi-selection** (Select "Pop" + "Rock")
- Filtering logic: OR within category, AND across categories
  - `(Genre=Pop OR Genre=Rock) AND (Mood=Happy)`
- Expand/Collapse sections
- Show item counts: `Pop (145)`

### Usability Features (Crucial)
1. **Search-within-Tree:** 
   - Input box at top of sidebar ("Filter lists...")
   - Typing "Pink" hides all non-matching nodes
   - Instantly reveals "Artists > P > Pink" without manual expansion
2. **Active Filters Area:**
   - Pinned section at top showing selected chips
   - `[x] Pink` `[x] Pop`
   - One-click clear for individual filters
3. **Smart Sections:**
   - Artists section shows "Top 20" by default
   - "Show All" expands the full A-Z tree structure

## 2. The Publisher Tree (True Hierarchy)
Unlike Genres, Publishers have a strict corporate hierarchy (Parent -> Subsidiary).

- **Structure:** Recursive Tree using `Publishers.ParentPublisherID`.
- **Logic:**
    - **Strict Mode:** Selecting "Def Jam" shows only Def Jam releases.
    - **Recursive Mode (Default):** Selecting "Universal" (Parent) automatically includes "Def Jam" (Child) and "Island" (Child).
- **Query Strategy:**
    - Uses a **Recursive Common Table Expression (CTE)** in SQLite to fetch all Child IDs for the selected Parent.
    - Query: `WHERE PublisherID IN (SELECT ID FROM RecursivePublisherCTE)`

## 3. Integration with App
- **Location:** Left Sidebar (Filter Panel).
- **Connection:** Updates the central `LibraryModel`'s filter proxy.
- **Mode Switching:** 
    - In **Edit Mode**, drag-and-drop a song onto "House" to add that genre.
    - In **Broadcast Mode**, tree is locked (read-only filtering).

## 4. Workflows
1. **User imports "Sony" catalog:** New publishers auto-populate the tree.
2. **User merges labels:** Drag "Maverick" node onto "Warner" node to make it a subsidiary.
