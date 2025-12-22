# T-06 Legacy Sync (Briefing)

## 🎯 Objective
Implement the missing metadata structures to match Gosling 1 features (`Album`, `Genre`, `Publisher`).

## ⚠️ Architectural Directive: RELATIONAL MODE
**DO NOT** simply add text columns (`S.Album`) to the `Songs` table.
The User has explicitly requested the **Relational Implementation** defined in `DATABASE.md` (Target Architecture).

### 1. Albums
*   **Table**: `Albums` (ID, Title, Type, ReleaseYear).
*   **Junction**: `SongAlbums` (SourceID, AlbumID, TrackNumber).
*   **Ref**: `DATABASE.md` tables 23 & 24.

### 2. Publishers
*   **Table**: `Publishers` (ID, Name, ParentID).
*   **Junction**: `AlbumPublishers` (AlbumID, PublisherID).
*   **Ref**: `DATABASE.md` tables 22 & 25.
*   **Edge Case Warning**:
    *   ID3 allows a Publisher (`TPUB`) on a track without an Album (`TALB`) or on a Single.
    *   Since our schema links Publisher -> Album -> Song, you must define a strategy for "Singles".
    *   *Strategy*: If `TPUB` present, ensure an `Album` exists (create one with Title=SongName, Type='Single' if needed).

### 3. Genres (Tags)
*   **Strategy**: Unified Tags System.
*   **Table**: `Tags` (ID, Name, Category='Genre').
*   **Junction**: `MediaSourceTags` (SourceID, TagID).
*   **Ref**: `DATABASE.md` tables 9 & 10.

## ⛔ Constraints
*   **Groups Logic**: The "Groups/Unified Artist" features are **SETTLED**. Do not refactor `ContributorRepository` or `GroupMembers`.
*   **Field Editor**: **Use `tools/field_editor.py`** to add the new fields (`album`, `genre`, `publisher`) to `yellberus.py`. Do not manually edit the registry file.

## 🧠 Relationship Logic (Implementation Guide)
The schema is relational, but the input (ID3) is flat. You must implement **"Find or Create"** logic in the Service layer:
1.  **Genre**: Input "Rock" -> Find TagID for "Rock" (Cat='Genre'). If missing, create it. -> Link `MediaSourceTags`.
2.  **Album**: Input "Nevermind" -> Find AlbumID. If missing, create it. -> Link `SongAlbums`.
3.  **Publisher**: Input "DGC" -> Find PublisherID. If missing, create it. -> Link `AlbumPublishers` (via the Album).

## 🔁 Execution Sequence (Iterative)
This is not a batch job. Implement and Verify one by one:
1.  **[ ] Phase 1: Albums** (Table `Albums`, Junction `SongAlbums`).
    *   *Test Case*: One Song linked to Two Albums (Original & Greatest Hits).
    *   *Requirement*: Filter by Year matches *either* album's release year (if logic permits).
2.  **[ ] Phase 2: Publishers** (Table `Publishers`, Junction `AlbumPublishers`).
    *   *Test Case*: Parent/Child Hierarchy (e.g. Island -> Universal).
3.  **[ ] Phase 3: Genres** (Table `Tags`, Junction `MediaSourceTags`).

## 🧪 Testing Complexity
*   **Multi-Album Logic**: Ensure a single SourceID can be linked to multiple Albums. Verification involves checking Filters (does it show up in both contexts?) and Database integrity (Junction table rows).
*   **Publisher Hierarchy**: Verify that selecting a Parent Publisher in a future filter includes the Child Publisher's albums.

## 🛠️ Execution Plan (Suggested)
1.  **Schema**: Create the tables in `src/data/database.py`.
2.  **Models**: Create `Album.py`, `Publisher.py`, `Tag.py` in `src/data/models/`.
3.  **Repos**: Implement `AlbumRepository`, `TagRepository`.
4.  **Service**: Expose methods in `LibraryService` (handling the "Find or Create" logic).
5.  **User Action**: User runs `python tools/field_editor.py` to register the new fields.

## 🔮 Deferred Decisions (Future Task)
*   **ID3 Import Strategy**: How to handle Album/Publisher creation during bulk import to a clean DB vs. existing DB.
    *   *Current Approach*: Auto-create if missing (Basic "Find or Create").
    *   *Future Refinement*: Sophisticated matching, asking user for confirmation, or handling metadata conflicts. (Low priority for now).
