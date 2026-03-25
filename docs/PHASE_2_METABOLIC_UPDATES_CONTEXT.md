# Context for Metabolic Updates Grilling Session

**Purpose:** This document provides the minimal context needed to grill the Metabolic Updates (CRUD) feature for Phase 2.

---

## What is Metabolic Updates?

From roadmap: **"CRUD infrastructure for modifying existing songs, including scalar data (BPM, ISRC) and relationship synchronization (Tags/Publishers)."**

Allows users to edit song metadata after ingestion, keeping DB and file tags in sync.

---

## What You Need to Know

### 1. Current UI Pattern (Already Built)
- Song detail panel shows comparison table: **Library** vs **File** columns
- Location: `src/static/js/dashboard/renderers/songs.js` lines 186-207
- Displays: Title, Artist, Year, BPM, Duration, ISRC, Publisher (Master)
- Currently read-only - needs edit capability

### 2. Domain Model (Song Structure)
**Location:** `src/models/domain.py`

**Song Model Fields:**
```python
class Song(DomainModel):
    id: int
    media_name: str           # Title
    source_path: str          # File location
    year: Optional[int]
    bpm: Optional[int]
    isrc: Optional[str]
    duration_s: float
    audio_hash: str
    is_active: bool

    # Relationships (hydrated)
    credits: List[SongCredit]        # M2M via SongCredits table
    albums: List[SongAlbum]          # M2M via SongAlbums table
    tags: List[Tag]                  # M2M via MediaSourceTags table
    publishers: List[Publisher]      # M2M via RecordingPublishers table
```

### 3. Data Layer (Repositories)
**Location:** `src/data/`

**Existing Insert Logic:** `SongRepository.insert()` handles atomic writes:
- Inserts into `MediaSources`, `Songs` tables
- Calls `TagRepository.insert_tags()`
- Calls `SongAlbumRepository.insert_albums()`
- Calls `PublisherRepository.insert_song_publishers()`
- Calls `SongCreditRepository.insert_credits()`
- Does NOT commit (caller controls transaction)

**Update Logic:** Does NOT exist yet - needs to be created

### 4. Audit System (Already Built)
**Location:** `src/data/audit_repository.py`

**Tables:**
- `ActionLog` - High-level events (IMPORT, DELETE, UPDATE)
- `ChangeLog` - Field-level modifications (before/after values)
- `DeletedRecords` - JSON snapshots of deleted records

Updates should log to both `ActionLog` (UPDATE event) and `ChangeLog` (per-field changes).

### 5. Service Layer
**Location:** `src/services/catalog_service.py`

**Existing Methods:**
- `get_song(song_id)` - Fetches full song with relationships
- `search_songs(query)` - Surface search
- (Deep search/filter methods will be added in Phase 2)

**Missing Methods:**
- `update_song()` - Needs to be created
- `update_song_credits()` - Needs to be created
- `update_song_tags()` - Needs to be created
- etc.

---

## Questions to Grill

### Scope & Fields
1. Which fields are editable vs read-only?
   - Scalar: Title, Year, BPM, ISRC (editable?)
   - Computed: Duration, AudioHash (read-only?)
   - File path: SourcePath (editable or immutable?)
   - Active status: is_active (editable?)

2. Can users edit relationship data?
   - Credits (add/remove artists, change roles?)
   - Albums (add/remove album links, change track numbers?)
   - Tags (add/remove genres/tags?)
   - Publishers (add/remove publishers?)

### UI/UX Pattern
3. How does editing work in the UI?
   - Inline editing (click field to edit)?
   - Modal dialog (popup form)?
   - Separate edit panel (replaces detail view)?
   - Edit mode toggle (switches read-only detail to editable form)?

4. What triggers a save?
   - Auto-save on field blur?
   - Explicit Save button?
   - Batch save (edit multiple fields, save once)?

5. What happens on cancel?
   - Revert all changes?
   - Warn if unsaved changes?

### Validation & Conflicts
6. What validation rules exist?
   - Required fields (Title required, others optional)?
   - Format validation (Year = 4 digits, BPM = 1-300, ISRC = 12 chars)?
   - Uniqueness checks (prevent duplicate AudioHash)?

7. What if file metadata differs after edit?
   - User edits Year in DB to 1991
   - File still has Year = 1990 tag
   - Show conflict warning?
   - Allow "sync to file" option?
   - Just accept divergence?

### Relationship Synchronization
8. When editing relationships, what happens to linked tables?
   - Add new artist → Get-or-create in ArtistNames table?
   - Remove artist → Delete link only, or delete artist if orphaned?
   - Change album → Affects other songs on same album?

9. Publisher hierarchy - how to handle?
   - Publishers have parent/child relationships
   - Can user edit publisher links freely?
   - Does it affect publisher hierarchy?

### Batch Operations
10. Can users edit multiple songs at once?
    - Select 10 songs → Set Year = 1991 for all?
    - Or only single-song editing for MVP?

### Audit & History
11. What audit data gets logged?
    - ActionLog: Single UPDATE entry per save?
    - ChangeLog: One entry per changed field?
    - Include old/new values?

12. Can users revert changes?
    - View change history?
    - Rollback to previous version?
    - Or just forward-only edits?

### Backend Architecture
13. Transaction boundaries?
    - Update scalar fields in one transaction?
    - Update relationships in same transaction or separate?
    - Rollback on validation failure?

14. API design?
    - Single endpoint: `PATCH /songs/{id}` with full song object?
    - Multiple endpoints: `PATCH /songs/{id}/credits`, `PATCH /songs/{id}/tags`?
    - Partial updates (only send changed fields)?

---

## Constraints & Gotchas

### From Previous Sessions:
- **Multiple frontends planned** (web + desktop) → logic must be in backend
- **Audit is mandatory** - all changes must be logged
- **Filter rebuild triggers on DB writes** - edits will trigger filter cache rebuild
- **Get-or-create pattern used for tags/publishers** - editing relationships may create new records

### From Domain Knowledge:
- **AudioHash is immutable** - ties to physical file, don't allow edits
- **SourcePath changes** - if file moved, how to handle? Re-hash? Update path? Mark inactive?
- **Album credits vs Song credits** - separate tables, editing one doesn't affect the other
- **Identity system exists** - ArtistNames can link to Identities (canonical artist records)

### Performance Considerations:
- Relationship updates may require multiple table writes (M2M link tables)
- Validation may require lookups (check existing albums, artists)
- Audit logging adds overhead per field change

---

## Implementation Complexity

**Scalar field updates:** Low complexity
- Direct UPDATE on Songs table
- Simple validation
- Single audit log entry

**Relationship updates:** High complexity
- Multiple table writes (link tables)
- Get-or-create logic for new values
- Orphan cleanup (remove links)
- Audit all relationship changes
- Sync album/tag/publisher metadata

**MVP Recommendation:** Start with scalar fields only, defer relationship editing to post-MVP.

---

## Next Steps for Grilling

1. Define editable vs read-only fields
2. Choose UI pattern (inline, modal, edit mode)
3. Define validation rules
4. Decide conflict resolution strategy (DB vs File)
5. Scope relationship editing (include in MVP or defer?)
6. Define audit logging detail level
7. Design API endpoints
8. Plan transaction boundaries

---

## Reference Files

- Current detail panel: `src/static/js/dashboard/renderers/songs.js` (lines 150-290)
- Domain models: `src/models/domain.py`
- Song repository: `src/data/song_repository.py`
- Catalog service: `src/services/catalog_service.py`
- Audit repository: `src/data/audit_repository.py`
- Existing insert logic: `SongRepository.insert()` - template for update logic
