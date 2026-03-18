# Album Implementation Mockup
*A comprehensive guide to the methods and models required for a first-class Album entity in Gosling2.*

---

## 1. Domain Models (`src/models/domain.py`)
*The "Source of Truth" for what an Album is.*

```python
class Album(DomainModel):
    """The top-level entity representing a musical release."""
    id: Optional[int] = None
    title: str
    type: Optional[str] = None  # LP, EP, Single, Compilation, etc.
    year: Optional[int] = None
    
    # Hydrated Metadata
    credits: List[AlbumCredit] = []
    publishers: List[Publisher] = []
    tracks: List[Song] = []  # Full hydrated songs, ordered by TrackNumber/DiscNumber
```

---

## 2. Repository Layer (`src/data/album_repository.py`)
*Dumb, high-performance SQL access.*

### `get_by_id(album_id: int) -> Optional[Album]`
Fetches the core row from the `Albums` table.

### `get_by_ids(ids: List[int]) -> List[Album]`
Batch fetch for list views/search results.

### `search(query: str) -> List[Album]`
Case-insensitive title match (`LIKE ?`).

### `get_all() -> List[Album]`
The "Everything" view for the library.

### `get_track_ids(album_id: int) -> List[int]`
Returns an ordered list of `SourceID`s from `SongAlbums` for this album.

### `get_credits_for_albums(album_ids: List[int]) -> List[AlbumCredit]`
(Wait, this exists in `AlbumCreditRepository`, we'd keep it there but expose it here).

### `create(album: Album) -> int`
Atomic insert of a new album record.

### `update(album: Album) -> bool`
Updates basic metadata (Title, Type, Year).

---

## 3. Service Layer (`src/services/catalog_service.py`)
*The "Smart" orchestrator. Handles hydration and business rules.*

### `get_album(album_id: int) -> Optional[Album]`
1. Calls `AlbumRepository.get_by_id`.
2. Calls `_hydrate_albums` for credits and publishers.
3. Calls `get_album_tracks(album_id)` to attach the tracklist.

### `search_albums(query: str) -> List[Album]`
Search across Titles and expanding into Artist Identities (e.g. "Dave Grohl" returns Nirvana albums).

### `merge_albums(target_id: int, source_ids: List[int])`
**The Scar-Logic**: Safely moves all `SongAlbums` links from sources to target, merges `AlbumCredits`, and deletes orphans.
- Ensures no duplicate track numbers are created.
- Updates the `ChangeLog` for every moved relation.

### `_hydrate_albums(albums: List[Album]) -> List[Album]`
**Internal Implementation**:
1. Batch-fetches `AlbumCredits` and `Publishers`.
2. Groups them by `AlbumID`.
3. Stitches them to the Pydantic models.

---

## 4. API Router Layer (`src/engine/routers/catalog.py`)
*The communication bridge.*

### `GET /albums`
Returns the full library of albums (paginated).

### `GET /albums/{album_id}`
Returns the full hydrated `Album` object including its tracklist.

### `GET /albums/search?q=...`
The discovery endpoint for the UI.

### `POST /albums/merge`
Trigger for the batch operation.

---

## 5. Frontend Store (`src/ui/stores/albumStore.ts`)
*The user's gateway.*

```typescript
interface AlbumStore {
  albums: Album[];
  selectedAlbum: Album | null;
  loading: boolean;

  /** Fetches all albums into the library view */
  fetchAll(): Promise<void>;

  /** Retrieves a specific album and sets it as 'selected' */
  selectAlbum(id: number): Promise<void>;

  /** Performs a fuzzy search and updates the local state */
  search(query: string): Promise<void>;

  /** 
   * Triggers a merge of multiple albums. 
   * Crucial for fixing "De-duplicated" library slop.
   */
  merge(targetId: number, sourceIds: number[]): Promise<void>;
}
```

---

## 6. Testing Strategy (`tests/`)
*The "Done and Green" compliance.*

1. **Integrated Test**: Verify `merge_albums` correctly updates `SongAlbums` and cleanup.
2. **Coverage**: Ensure 100% path coverage for `_hydrate_albums` (handling NULL credits/publishers).
3. **Instrumentation Check**: Every method must log `entry` (args) and `exit` (counts) to `src.services.logger`.
