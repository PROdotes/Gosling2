# Architectural Proposal: Library View Modes

## Objective
Implement multiple layout strategies for the music library to cater to different user workflows (Archiving vs. Browsing).

## 1. View Strategies

### A. Detail View (The "Classic")
- **Layout:** `QTreeView` or `QTableView`.
- **Focus:** Maximum metadata density. 10+ columns.
- **Workflow:** Auditing, bulk editing, technical cleanup.

### B. Grid View (The "Modern")
- **Layout:** `QListView` with an `IconMode` flow layout.
- **Components:** Large Album Art (160px), bold Title below.
- **Workflow:** Visual browsing, discovery, "finding that one cover I recognize."

### C. Compact List (The "Player")
- **Layout:** Single-line row with Artist - Title - BPM.
- **Focus:** Vertical density. Fitting 30+ tracks on screen at once.
- **Workflow:** Quick playlist construction, radio programming.

## 2. Content Filtering (The "Type" Tabs)
As defined in `plan_database.md` (Section 2.2), the Library must support quick-switching between content types:

- **The Tab Bar:** Horizontal tabs at the top of the list/grid.
- **Categories:** `All`, `Music`, `Jingles`, `Commercials`, `Speech`.
- **Query Logic:** Clicking a tab automatically applies a `WHERE Type = '...'` filter to the active view.

## 3. Implementation Approach (The "QStackedWidget" Strategy)
Instead of rewriting the `LibraryWidget`, we wrap the data in a `QAbstractItemModel` and swap the *View* component.

1. **Central Model:** Use the existing `LibraryModel`.
2. **View Multiplier:**
   - Create a `QStackedWidget` in the center of the library.
   - Index 0: `QTableView` (Detail).
   - Index 1: `QListView` (Icons).
3. **View Delegates:**
   - Custom `QStyledItemDelegate` for the Grid view to handle drawing the "Card" (Shadows, Rounded corners for art).

## 4. UI/UX Controls
- **Toggle Icons:** A small button group (segmented control) in the library header.
- **Persistence:** Save the user's preferred view mode in `SettingsManager`.
- **Zoom Slider:** A slider at the bottom right to adjust icon size (64px to 256px).

## 5. Integration with Field Registry
- Even in Grid View, "hovering" over a card should show a tooltip with metadata fields marked as `is_primary=True` in the **Registry**.

## 🚀 "Quick Win" Roadmap
1. [ ] Implement the UI Toggle buttons in the header.
2. [ ] Integrate `QStackedWidget` into `LibraryWidget`.
3. [ ] Build the "Grid Delegate" for the art-focused view.
4. [ ] Connect the existing SQLite model to the new views.
