# T-46: Proper Album Editor (Spec)

**Status**: Draft
**Priority**: High (v0.1 Finalization)
**Dependencies**: Side Panel, Album Repository

## 1. The Problem
Currently, the `Album` field in the Side Panel is a free-text input. This causes several data integrity issues:
1.  **Typos**: "Thriller" vs "Thriler" creates two albums.
2.  **Duplicate Titles**: "Greatest Hits" merges Queen and ABBA into the same album entity.
3.  **Missing Metadata**: Creating an album via text string doesn't allow setting the `Publisher` or `Release Year` of the *Album itself*.
4.  **Relational Violation**: Users edit `Publisher` on the Song, but Publisher belongs to the Album.

## 2. The Solution
Replace the Side Panel `Album` text field with a **Relational Picker Button** and a dedicated **Album Manager Dialog**.

### A. The UI Changes (Side Panel)
1.  **Album Field**: Change from `QLineEdit` to `QPushButton` (styled like a field).
    *   Text: Current Album Name (or "Multiple Values", or "None").
    *   Action: Clicking opens `AlbumManagerDialog`.
2.  **Publisher Field**:
    *   **Behavior**: Read-Only.
    *   **Display**: Shows the Publisher of the *selected* Album.
    *   **Tooltip**: "Publisher is managed via the Album."

### B. The Album Manager Dialog
A modal window with three modes:
1.  **Select**: List existing albums (Filtered by search).
    *   Columns: Title, Album Artist, Year, Publisher.
    *   Includes `(Unknown Artist)` or `(Various)` disambiguation.
2.  **Create**: "New Album" button.
    *   Fields: Title, Album Artist (Default: Song Artist), Type (Album/EP), Year, Publisher.
    *   Checks for duplicates on save.
3.  **Edit**: "Edit Selected" button.
    *   Allows correcting typos (renaming) and fixing metadata for the *entire* album (all songs).

## 3. Data Flow
1.  **User picks Album**:
    *   Callback returns `AlbumID`.
    *   App updates `Song.AlbumID`.
    *   App auto-updates `Song.Publisher` (Display only) from `Album.Publisher`.
2.  **User edits Metadata (Year/Publisher)**:
    *   This is an `UPDATE Albums` SQL command.
    *   It affects ALL songs linked to that album immediately.
3.  **Migration**:
    *   Existing plain-text albums must be "adopted" into the new relational structure if they aren't already. (Likely handled by `Legacy Sync` task).

## 4. Implementation Steps
1.  **Repository**: Ensure `AlbumRepository` has `find_fuzzy()`, `update()`, and `get_with_publisher()`.
2.  **Dialog**: Create `src/presentation/dialogs/AlbumManagerDialog.py`.
3.  **Integration**: Wire up Side Panel button.
4.  **Disabling**: Logic to disable the Publisher text box in Side Panel when an Album is set.

## 5. Edgy Cases
*   **Compilation Paradox**: If User creates "Greatest Hits", they MUST specify "Album Artist" (e.g. Queen) or check "Compilation" (Various Artists). The UI must enforce this uniqueness constraint.
