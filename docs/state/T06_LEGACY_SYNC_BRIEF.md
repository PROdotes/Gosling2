# T-06 Legacy Sync (Briefing)

## ⚠️ Critical Architecture Note: Album Uniqueness
*   **The Issue**: The current schema defines `Albums` by `Title` only. This causes a "Greatest Hits Paradox":
    *   If Queen and ABBA both have albums named "Greatest Hits", `AlbumRepository.get_or_create("Greatest Hits")` will merge them into a single Album entity.
*   **Current Behavior**: "Blind Merge" by Title.
*   **Proposed Fix (Deferred)**: Add `AlbumArtist` column to `Albums` table to allow `get_or_create(Title, Artist)`.
*   **Impact**: UI Dropdowns currently cannot distinguish between duplicates.
*   **Action**: Discuss with Team (Siblings) whether to prioritize Schema Change (T-06 Phase 1 Revision) or accept Merge behavior.

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

## 🛠️ Execution Plan (Concrete)
1.  **[x] Phase 1: Albums Infrastructure**
    *   **Schema**: Add `Albums` and `SongAlbums` to `src/data/database.py`.
    *   **Models**: Create `src/data/models/album.py` (Dataclass).
    *   **Repos**: Create `src/data/repositories/album_repository.py` (Find/Create logic).
    *   **Service**: Update `LibraryService` to handle album binding.
    *   **Tooling**: Update `yellberus.py` via manual edit (Completed).
    *   **Integration**: Wired `SongRepository` to sync albums on update. Verified via `tests/integration/test_t06_albums.py`.

2.  **[x] Phase 2: Publishers Infrastructure**
    *   **Schema**: Add `Publishers` and `AlbumPublishers` to `src/data/database.py`.
    *   **Models**: Create `src/data/models/publisher.py`.
    *   **Repos**: Create `src/data/repositories/publisher_repository.py`.

3.  **[x] Phase 3: Genres (Tags)**
    *   **Schema**: Add `Tags` and `MediaSourceTags` to `src/data/database.py`.
    *   **Models**: Create `src/data/models/tag.py`.
    *   **Repos**: `TagRepository` implementation.


## 🎨 UX Specifications
*   **Album Type Implementation**:
    *   **Backend**: Stored as `TEXT` in `Albums` table (free-form allowed for imports).
    *   **Frontend**: Must use a **ComboBox** (Dropdown) to encourage consistency.
    *   **Standard Values**: `['Album', 'Single', 'EP', 'Compilation', 'Live', 'Soundtrack']`.
    *   **Validation**: Warn but allow new values (Soft Constraint).

## 🔮 Deferred Decisions (Future Task)
*   **ID3 Import Strategy**: How to handle Album/Publisher creation during bulk import to a clean DB vs. existing DB.
    *   *Current Approach*: Auto-create if missing (Basic "Find or Create").
    *   *Future Refinement*: Sophisticated matching, asking user for confirmation, or handling metadata conflicts. (Low priority for now).
