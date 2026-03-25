# Phase 2: Metabolic Updates (CRUD) - Specification

**Feature:** CRUD infrastructure for modifying existing songs, including scalar data (BPM, ISRC) and relationship synchronization (Tags/Publishers).

**Status:** Specification Complete - Ready for Implementation

---

## Overview

This feature enables users to edit song metadata after ingestion, keeping the database and file tags synchronized. The system uses atomic saves (each action commits immediately) with a hybrid UI pattern: inline editing for scalar fields, focused modals for relationship editing.

---

## Scope & Field Editability

### Editable Scalar Fields (Song Table)
- `media_name` (Title) - **Required**
- `year` - Optional, validates 1860 to (current_year + 1)
- `bpm` - Optional, validates 1-300
- `isrc` - Optional, strips dashes, validates 12 characters after stripping
- `is_active` - Boolean flag

### Read-Only Scalar Fields
- `duration_s` - File-derived, immutable
- `audio_hash` - File-derived, immutable
- `source_path` - Programmatic updates only (when files are moved)

### Editable Relationships (All Included in MVP)
- **Credits** (Artists/Roles via `SongCredits` M2M)
- **Albums** (via `SongAlbums` M2M)
- **Tags** (via `MediaSourceTags` M2M)
- **Publishers** (via `RecordingPublishers` M2M)

---

## UI/UX Pattern

### Scalar Field Editing
**Pattern:** Inline editing with auto-save on blur

**Flow:**
1. User clicks field (Title, Year, BPM, ISRC, is_active)
2. Field becomes editable input
3. User edits value
4. On blur (or Enter key), validation runs
5. If valid → saves to DB immediately, field returns to display mode
6. If invalid → field highlights red, inline error message appears

**Validation Feedback:**
- Prevent invalid characters (e.g., letters in year field)
- Show inline error message + red highlight when validation fails
- Error format: "Year must be between 1860-2027"

### Relationship Editing
**Pattern:** Focused modals per relationship type

**General Flow:**
1. User clicks relationship field (e.g., "Artists")
2. Modal opens showing current relationships for that type
3. User performs actions (add/remove/edit)
4. Each action saves atomically to DB
5. Modal stays open for multiple edits (user closes when done)

---

## Relationship-Specific UI Patterns

### Credits (Artists/Roles)
**Display:** Grouped by role (matching existing display pattern)

**Modal Structure:**
```
PERFORMER
  - Ivan Sever [edit name] [x remove]
  [+ Add Performer]

COMPOSER
  - Ivan Sever [edit name] [x remove]
  - John Doherty [edit name] [x remove]
  [+ Add Composer]

LYRICIST
  - Ivan Sever [edit name] [x remove]
  [+ Add Lyricist]
```

**Actions:**
- **Add artist:** Click "+ Add [Role]" → autocomplete input appears in modal → type to search → shows existing artists + "Create new" options → select → saves link immediately
- **Remove artist:** Click [x] → deletes `SongCredits` link immediately (keeps `ArtistNames` record)
- **Edit artist name:** Click name → inline edit activates → blur → updates `ArtistNames` record globally (affects all songs)

**Add Artist Autocomplete (appears within modal, not nested modal):**
- Type to search existing artists
- Dropdown shows matches with category tags (Person/Group)
- Explicit "Create new as Person/Group" options
- Auto-assigns role based on which "+ Add [Role]" button was clicked
- Select option → saves immediately, autocomplete closes, new artist appears in list

### Albums
**Display:** Album cards showing title, year, type, publisher, album artist

**Modal Structure:** Complex - shows full album context to help user pick correct album

**Actions:**
- **Link to album:** Search/select from existing albums → can edit track number, disc number, and album record fields (title, album artist, year, publisher, release type) in same workflow → saves link + album updates
- **Unlink from album:** Remove button → deletes `SongAlbums` link immediately (keeps Album record)

**Why Complex?** Users need to see album details (artist, publisher, year, linked songs) to confirm they're linking the right album. Also allows fixing album metadata while linking (e.g., "oh the album year is wrong, let me fix that now").

**Autocomplete Display:** When searching for albums to link, show:
- Album title
- Release year (if available)
- Album artist (if available)
- Publisher (if available)
- Example: "(2026) Mijenjam sve - Čuvari Svirala [Croatia Records]"

This rich context helps users distinguish between albums with similar titles.

**Editable Fields:**
- **Link fields:** Track number, disc number
- **Album record fields:** Title, album artist(s), release year, publisher, release type

**Nested Modal Caveat:** Album editing requires nested modals because albums have their own relationships:
- Editing **album artists** → Opens artist autocomplete picker (nested modal/dropdown)
- Editing **album publisher** → Opens publisher autocomplete picker (nested modal/dropdown)
- This is unavoidable complexity - albums are composite entities with their own relationships
- "Import from Song" button available to prepopulate album data from current song (common workflow shortcut)

### Tags
**Display:** Pills/chips grouped by category (Genre vs Other Tags)

**Modal Structure:** Simple autocomplete add/remove

**Actions:**
- **Add tag:** Autocomplete → shows existing tags + "Create new as [Category]" options → select → saves link immediately
- **Remove tag:** Click [x] on chip → deletes `MediaSourceTags` link immediately (keeps Tag record)

**Category Selection:** UI shows category filters (ALL, Genre, Festival, Jezik) - when creating new tag, user explicitly chooses category from "Create new as..." options

**Detail Editing:** Click tag name → navigates to dedicated tag management view (not in song edit flow)

### Publishers
**Display:** Pills/chips (same as tags)

**Modal Structure:** Simple autocomplete add/remove

**Actions:**
- **Add publisher:** Autocomplete → shows existing publishers + "Create new" option → select → saves link immediately
- **Remove publisher:** Click [x] → deletes `RecordingPublishers` link immediately (keeps Publisher record)

**Hierarchy Note:** Publishers have parent/child relationships, but hierarchy editing happens in dedicated publisher management view, not in song edit flow. Song modal just handles linking/unlinking.

---

## Save Behavior

**Strategy:** Atomic saves - each action commits to DB immediately

**Rationale:** Staged saves create cognitive disconnect where users see UI changes (e.g., artist chip appears) but don't realize data isn't saved. Atomic saves eliminate this confusion - what you see is what's in the DB.

**Implementation:**
- **Scalar fields:** Save on blur/Enter
- **Add relationship:** Save immediately after selection
- **Remove relationship:** Delete immediately on click
- **Edit name:** Update immediately on blur

**Transaction Boundaries:** Each save is an independent transaction. No rollback across fields - they're independent operations.

---

## Validation Rules

### Scalar Field Validation

| Field | Required | Type | Validation |
|-------|----------|------|------------|
| `media_name` | Yes | String | Cannot be empty |
| `year` | No | Integer | If provided: 1860 ≤ year ≤ (current_year + 1) |
| `bpm` | No | Integer | If provided: 1 ≤ bpm ≤ 300 |
| `isrc` | No | String | If provided: Strip dashes, validate 12 characters |
| `is_active` | N/A | Boolean | No validation |

### Validation Error Display
- Input prevention (number-only fields block letters)
- Inline error message below/next to field
- Red highlight on field
- User must fix error before field can be exited (or cancel edit)

---

## DB vs File Conflict Resolution

**Strategy:** Accept divergence, provide manual sync controls

**Behavior:**
1. User edits metadata in DB (e.g., Year: 1990 → 1991)
2. File still contains old value (Year: 1990 in ID3 tags)
3. System accepts divergence - DB and file can differ
4. Comparison table shows difference (Library: 1991, File: 1990)
5. UI shows "Sync to File" button (enabled when DB has changes not in file)
6. UI shows "Sync to DB" button (enabled when file has changes not in DB)
7. User controls when sync happens

**Note:** Sync functionality (writing changes back to file tags or reading from file to DB) will be implemented separately - this spec covers the edit CRUD only.

---

## Relationship Data Management

### Get-or-Create Pattern
All relationship add operations use get-or-create pattern (matching existing `SongCreditRepository.insert_credits()` logic):

**Adding New Artist Example:**
1. User types artist name in autocomplete
2. If exists in `ArtistNames` → link to existing record
3. If doesn't exist → create new `ArtistNames` record with:
   - `DisplayName` = user input
   - `OwnerIdentityID` = NULL (identity linking deferred)
   - `IsPrimaryName` = 0 (not primary by default)
4. Link to song via `SongCredits` table

Same pattern applies for Tags, Publishers, Albums (though Albums are more complex due to additional fields).

### Orphan Cleanup Strategy
**Philosophy:** Keep orphaned records, provide bulk cleanup in dedicated management UI

**Behavior:**
- Remove artist from song → deletes `SongCredits` link, keeps `ArtistNames` record
- Remove tag from song → deletes `MediaSourceTags` link, keeps Tag record
- Remove publisher from song → deletes `RecordingPublishers` link, keeps Publisher record
- Remove album from song → deletes `SongAlbums` link, keeps Album record

**Rationale:** Users have separate frontends for exploring artists/albums/tags/publishers. Bulk cleanup ("show all unlinked, delete selected") happens there, not in song edit flow.

### Editing Related Entities Globally
**Artist Name Example:**
- User edits "Bon Jovi" → "Jon Bon Jovi" in song edit modal
- Updates `ArtistNames` record directly
- Change propagates to all songs linked to that artist (50+ songs updated automatically)

**Same behavior applies to:** Tag names, Publisher names, Album fields

**Important:** When editing related entity names/fields:
- Artist name edit → updates `ArtistNames` record → affects all linked songs globally
- Tag name edit → updates `Tag` record → affects all linked songs globally
- Publisher name edit → updates `Publisher` record → affects all linked songs globally
- Album field edit → updates `Album` record → affects all linked songs globally
- This is acceptable because modals show context to user and changes are intentional

**Transaction Boundaries for Global Updates:**
- Global updates (artist name, tag name, etc.) execute as a single UPDATE statement on the entity table
- Example: `UPDATE ArtistNames SET DisplayName = ? WHERE NameID = ?`
- No explicit transaction needed beyond the single statement (atomic at DB level)
- If update fails, no changes are committed (standard SQL behavior)
- Service layer wraps in transaction context for consistency with other operations

---

## API Design

### Endpoint Structure
Separate endpoints per entity type:

#### Scalar Fields
- `PATCH /api/songs/{song_id}` - Update scalar fields (title, year, BPM, ISRC, is_active)
  - Request body: `{ "media_name": "New Title", "year": 1991 }`
  - Partial updates allowed (only send changed fields)

#### Credits (Artists/Roles)
- `POST /api/songs/{song_id}/credits` - Add artist link
  - Request body: `{ "display_name": "Jon Bon Jovi", "role_name": "Composer" }`
  - Returns created `SongCredit` object
- `DELETE /api/songs/{song_id}/credits/{credit_id}` - Remove artist link
- `PATCH /api/artists/{name_id}` - Update artist name (global change)
  - Request body: `{ "display_name": "Jon Bon Jovi" }`

#### Albums
- `POST /api/songs/{song_id}/albums` - Link to album
  - Request body: `{ "album_id": 123, "track_number": 5, "disc_number": 1 }`
  - OR: `{ "album_title": "New Album", "release_year": 2026, ... }` (create new album)
- `DELETE /api/songs/{song_id}/albums/{album_id}` - Unlink from album
- `PATCH /api/songs/{song_id}/albums/{album_id}` - Update link fields (track/disc number)
  - Request body: `{ "track_number": 6, "disc_number": 2 }`
- `PATCH /api/albums/{album_id}` - Update album record (global change)
  - Request body: `{ "album_title": "Updated Title", "release_year": 2027, ... }`
- `POST /api/albums/{album_id}/artists` - Add artist to album
  - Request body: `{ "artist_name": "Čuvari Svirala" }`
- `DELETE /api/albums/{album_id}/artists/{artist_id}` - Remove artist from album
- `PATCH /api/albums/{album_id}/publisher` - Update album publisher
  - Request body: `{ "publisher_name": "Croatia Records" }`

#### Tags
- `POST /api/songs/{song_id}/tags` - Add tag link
  - Request body: `{ "tag_name": "Indie Rock", "category": "genre" }`
- `DELETE /api/songs/{song_id}/tags/{tag_id}` - Remove tag link
- `PATCH /api/tags/{tag_id}` - Update tag name (global change)

#### Publishers
- `POST /api/songs/{song_id}/publishers` - Add publisher link
  - Request body: `{ "publisher_name": "Sony Music Publishing" }`
- `DELETE /api/songs/{song_id}/publishers/{publisher_id}` - Remove publisher link
- `PATCH /api/publishers/{publisher_id}` - Update publisher name (global change)

---

## Backend Architecture

### Service Layer (CatalogService)
Create update methods mirroring API structure (matching existing insert pattern):

#### Scalar Updates
```python
def update_song_scalars(song_id: int, fields: dict) -> Song:
    """Update scalar fields (title, year, BPM, ISRC, is_active).

    Args:
        song_id: Target song ID
        fields: Dict of field names to new values (partial updates)

    Returns:
        Updated Song object with relationships hydrated

    Raises:
        ValueError: If validation fails
    """
```

#### Credit (Artist) Updates
```python
def add_song_credit(song_id: int, display_name: str, role_name: str) -> SongCredit:
    """Add artist to song with specified role. Get-or-create artist + role."""

def remove_song_credit(song_id: int, credit_id: int) -> None:
    """Remove artist from song. Deletes link only, keeps artist record."""

def update_artist_name(name_id: int, new_name: str) -> None:
    """Update artist display name. Affects all songs globally."""
```

#### Album Updates
```python
def add_song_album(song_id: int, album_id: int, track_number: int, disc_number: int) -> SongAlbum:
    """Link song to existing album."""

def create_and_link_album(song_id: int, album_data: dict, track_number: int, disc_number: int) -> SongAlbum:
    """Create new album and link to song."""

def remove_song_album(song_id: int, album_id: int) -> None:
    """Unlink song from album. Deletes link only, keeps album record."""

def update_song_album_link(song_id: int, album_id: int, track_number: int, disc_number: int) -> None:
    """Update track/disc number for song-album link."""

def update_album(album_id: int, album_data: dict) -> Album:
    """Update album record. Affects all linked songs globally."""

def add_album_artist(album_id: int, artist_name: str) -> None:
    """Add artist to album. Get-or-create artist."""

def remove_album_artist(album_id: int, artist_name_id: int) -> None:
    """Remove artist from album."""

def update_album_publisher(album_id: int, publisher_name: str) -> None:
    """Update album publisher. Get-or-create publisher."""
```

#### Tag Updates
```python
def add_song_tag(song_id: int, tag_name: str, category: str) -> Tag:
    """Add tag to song. Get-or-create tag."""

def remove_song_tag(song_id: int, tag_id: int) -> None:
    """Remove tag from song. Deletes link only, keeps tag record."""

def update_tag(tag_id: int, new_name: str, new_category: str) -> None:
    """Update tag name/category. Affects all songs globally."""
```

#### Publisher Updates
```python
def add_song_publisher(song_id: int, publisher_name: str) -> Publisher:
    """Add publisher to song. Get-or-create publisher."""

def remove_song_publisher(song_id: int, publisher_id: int) -> None:
    """Remove publisher from song. Deletes link only, keeps publisher record."""

def update_publisher(publisher_id: int, new_name: str) -> None:
    """Update publisher name. Affects all songs globally."""
```

### Repository Layer
Repositories handle all database operations. Service layer orchestrates logic.

#### New Repositories Needed
- `SongRepository.update_scalars(song_id, fields, conn)` - UPDATE Songs table
- `ArtistRepository` (create new file)
  - `update_artist_name(name_id, new_name, conn)`
  - `get_or_create_artist(display_name, conn) -> int` (returns name_id) - Extract from existing inline logic
  - `get_or_create_role(role_name, conn) -> int` (returns role_id) - Extract from existing inline logic in `SongCreditRepository`
- `SongCreditRepository` (extend existing)
  - `add_credit(source_id, name_id, role_id, conn)` - Single link insert, simpler than `insert_credits()`
  - `remove_credit(credit_id, conn)` - Delete single link by credit_id
  - Keep existing `insert_credits()` for batch inserts during ingestion
- `SongAlbumRepository` (extend existing)
  - `add_album(source_id, album_id, track_number, disc_number, conn)`
  - `remove_album(source_id, album_id, conn)`
  - `update_track_info(source_id, album_id, track_number, disc_number, conn)`
- `AlbumRepository` (create new file)
  - `update_album(album_id, fields, conn)`
  - `create_album(album_data, conn) -> int` (returns album_id)
  - `get_album_by_id(album_id, conn) -> dict` - For displaying album context in autocomplete
  - `search_albums(query, conn) -> List[dict]` - For autocomplete search
  - `add_album_artist(album_id, artist_name_id, conn)` - Link artist to album
  - `remove_album_artist(album_id, artist_name_id, conn)` - Unlink artist from album
  - `update_album_publisher(album_id, publisher_id, conn)` - Update album publisher (single publisher per album)
- `TagRepository` (extend existing)
  - `add_tag(source_id, tag_id, conn)`
  - `remove_tag(source_id, tag_id, conn)`
  - `update_tag(tag_id, name, category, conn)`
  - `get_or_create_tag(name, category, conn) -> int` (returns tag_id)
- `PublisherRepository` (extend existing)
  - `add_publisher(source_id, publisher_id, conn)`
  - `remove_publisher(source_id, publisher_id, conn)`
  - `update_publisher(publisher_id, name, conn)`
  - `get_or_create_publisher(name, conn) -> int` (returns publisher_id)

**Pattern:** All write operations take `conn` parameter (caller controls transaction). Methods do NOT commit.

**Note on Refactoring:** We're extracting get-or-create logic from `SongCreditRepository.insert_credits()` into dedicated `ArtistRepository` methods for reusability. The existing `insert_credits()` method will be refactored to call `ArtistRepository.get_or_create_artist()` and `ArtistRepository.get_or_create_role()` internally.

---

## Audit Logging

**Status:** Deferred

**Rationale:** Implement CRUD functionality first, then decide on audit strategy based on actual usage patterns.

**Future Considerations:**
- `ActionLog` entry per save operation?
- `ChangeLog` entries for field-level changes?
- Log relationship changes (add/remove links)?
- Include old/new values for scalar changes?

Will revisit after CRUD implementation is complete and we can evaluate audit requirements.

---

## Implementation Order

### Phase 1: Backend Foundation
1. Create/extend repository classes with update methods
2. Add validation logic for scalar fields
3. Create service layer methods (scalars first, then relationships)
4. Write unit tests for repositories and services

### Phase 2: API Endpoints
1. Implement scalar update endpoint (`PATCH /api/songs/{id}`)
2. Implement credit endpoints (add/remove/update artist)
3. Implement album endpoints (add/remove/update)
4. Implement tag endpoints (add/remove/update)
5. Implement publisher endpoints (add/remove/update)
6. Integration tests for all endpoints

### Phase 3: Frontend - Scalar Editing
1. Add inline editing to scalar fields in detail panel
2. Implement validation feedback (red highlight, error messages)
3. Wire up to backend API
4. Test auto-save behavior

### Phase 4: Frontend - Relationship Editing
1. Build credits modal (grouped by role, add/remove/edit)
2. Build albums modal (complex - link fields + album record fields)
3. Build tags modal (simple autocomplete)
4. Build publishers modal (simple autocomplete)
5. Wire all modals to backend API
6. Test atomic save behavior

### Phase 5: Polish & Testing
1. Error handling for network failures
2. Loading states during saves
3. Success feedback (subtle confirmation)
4. Edge case testing (concurrent edits, validation errors, etc.)

---

## Files to Create/Modify

### New Files
- `src/data/artist_repository.py` - Artist name CRUD operations + role management
- `src/data/album_repository.py` - Album CRUD operations + search/autocomplete
- `src/routers/song_updates.py` - API endpoints for song updates (or extend existing songs router)
- Frontend modal components (exact file structure TBD based on existing JS architecture)

### Modified Files
- `src/data/song_repository.py` - Add `update_scalars()` method
- `src/data/song_credit_repository.py` - Add `add_credit()`, `remove_credit()` methods
- `src/data/song_album_repository.py` - Add album link CRUD methods
- `src/data/tag_repository.py` - Add tag link CRUD methods, `update_tag()` method
- `src/data/publisher_repository.py` - Add publisher link CRUD methods, `update_publisher()` method
- `src/services/catalog_service.py` - Add all update methods listed above
- `src/static/js/dashboard/renderers/songs.js` - Add inline editing + relationship modals
- `src/static/css/*` - Add styles for edit modes, modals, validation errors

---

## Open Questions & Future Work

### Not in Scope for MVP
1. **Sync to File functionality** - Writing DB changes back to file ID3 tags (separate feature)
2. **Sync to DB functionality** - Reading file tags to update DB (separate feature)
3. **Audit logging** - Deferred until CRUD is complete
4. **Batch editing** - Edit multiple songs at once (future enhancement)
5. **Change history viewer** - View/revert past changes (future enhancement)
6. **Conflict resolution UI** - Automated merge strategies for DB vs File differences (future enhancement)
7. **Publisher hierarchy editing** - Happens in dedicated publisher management view (separate feature)
8. **Identity resolution** - Linking ArtistNames to canonical Identities (separate feature)

### Questions for Later
1. Should we debounce rapid edits (e.g., user typing in year field)?
2. How to handle concurrent edits from multiple users (if multi-user support added)?
3. Should we cache autocomplete results for performance?
4. Do we need undo/redo functionality?

---

## Success Criteria

MVP is complete when:
- [ ] Users can edit all scalar fields (title, year, BPM, ISRC, is_active) with inline editing
- [ ] Users can add/remove/edit artists (credits) with role grouping
- [ ] Users can link/unlink albums with full context display
- [ ] Users can add/remove tags with category selection
- [ ] Users can add/remove publishers
- [ ] All edits save atomically (no staging)
- [ ] Validation errors display clearly with inline messages
- [ ] Comparison table shows divergence between Library and File
- [ ] No data loss or corruption from edit operations
- [ ] All backend operations are tested (unit + integration tests)

---

## Notes

- This spec captures decisions from grilling session on 2026-03-25
- Implementation will follow existing patterns from insert logic (`SongRepository.insert()`, `SongCreditRepository.insert_credits()`)
- UI will match existing design language from song detail panel
- Backend must support multiple frontends (web + desktop planned)
