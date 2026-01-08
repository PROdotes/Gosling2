# Schema V2: The Great Cleanup

**Status:** Phase 2 Complete (Publisher Clarity)  
**Author:** Schema Audit (Jan 7, 2026)  
**Priority:** CRITICAL (Blocking future features)

---

## 🚨 The Problem

The current database schema is experiencing "patch fatigue" — we're adding workarounds on top of workarounds. This creates:

1. **Dual Source of Truth:** `Albums.AlbumArtist` (TEXT) coexists with `AlbumContributors` (M2M junction). Which is canonical?
2. **Inconsistent Relationship Modeling:** Some entities use proper M2M (Songs → Contributors), others use TEXT fields (Albums → AlbumArtist).
3. **Leaky Abstraction:** Code must constantly check "is this a string or an ID?" and convert between them.
4. **Hidden Complexity:** Publishers have 4 different relationship types; Contributors have 3.

---

## 📊 Current Entity Relationship Audit

### Contributors (Artists)

| Relationship | Table | Notes |
|--------------|-------|-------|
| Song → Artist | `MediaSourceContributorRoles` | ✅ Proper M2M with Role + CreditedAliasID |
| Album → Artist | `AlbumContributors` | ⚠️ M2M exists but `Albums.AlbumArtist` TEXT still used |
| Artist → Alias | `ContributorAliases` | ✅ Proper 1:N |
| Person ↔ Group | `GroupMembers` | ✅ Proper M2M (with MemberAliasID) |

**Verdict:** Almost clean, but `Albums.AlbumArtist` is a **cancer** that must be excised.

---

### Publishers (Labels)

| Relationship | Table | Notes |
|--------------|-------|-------|
| Publisher Hierarchy | `Publishers.ParentPublisherID` | ✅ Self-referential FK |
| Album → Publisher | `AlbumPublishers` | ✅ Release label for this album |
| Recording → Publisher | `RecordingPublishers` | ✅ Master owner (different from album!) |
| Track Override | `SongAlbums.TrackPublisherID` | ⚠️ Deprecated (use RecordingPublishers instead) |

**Verdict:** Schema is correct! RecordingPublishers ≠ AlbumPublishers (different semantics). Just needs UI clarity.

---

### Albums

| Relationship | Table | Notes |
|--------------|-------|-------|
| Song → Album | `SongAlbums` | ✅ Proper M2M with IsPrimary, TrackNumber, DiscNumber |
| Album → Artist | `AlbumContributors` + `Albums.AlbumArtist` | ❌ DUAL SOURCE! |
| Album → Publisher | `AlbumPublishers` | ✅ Proper M2M |

**Verdict:** Remove `AlbumArtist` TEXT field. Make `AlbumContributors` the single source of truth.

---

### Tags

| Relationship | Table | Notes |
|--------------|-------|-------|
| Song → Tag | `MediaSourceTags` | ✅ Proper M2M |
| Tag Hierarchy | `TagRelations` | ❌ Not Implemented (but designed) |

**Verdict:** Working correctly. No changes needed.

---

## 🔧 Proposed Changes

### Phase 1: Kill the Dual Source (CRITICAL)

**Change:** Remove `Albums.AlbumArtist` TEXT column entirely.

**Impact:**
- `album_repository.py`: Remove references to `AlbumArtist` in INSERT/UPDATE/SELECT
- `Album` model: Remove `album_artist` property (or make it a computed property from M2M)
- `_get_joined_album_artist()`: Keep as the *only* way to get artist string (from M2M)
- ID3 Import: Write to `AlbumContributors`, not `Albums.AlbumArtist`
- ID3 Export: Read from `AlbumContributors` via JOIN

**Migration SQL:**
```sql
-- Step 1: Ensure all existing AlbumArtist values are in AlbumContributors
INSERT OR IGNORE INTO Contributors (ContributorName, SortName, ContributorType)
SELECT DISTINCT AlbumArtist, AlbumArtist, 'person'
FROM Albums
WHERE AlbumArtist IS NOT NULL AND AlbumArtist != '';

INSERT OR IGNORE INTO AlbumContributors (AlbumID, ContributorID, RoleID)
SELECT a.AlbumID, c.ContributorID, (SELECT RoleID FROM Roles WHERE RoleName = 'Performer')
FROM Albums a
JOIN Contributors c ON a.AlbumArtist = c.ContributorName
WHERE a.AlbumArtist IS NOT NULL AND a.AlbumArtist != '';

-- Step 2: Drop the column (SQLite requires table rebuild)
-- This is handled by schema migration code, not raw SQL
```

**Effort:** ~3 hours

---

### Phase 2: Publisher UI Clarity (Revised)

**Previous Understanding:** We thought RecordingPublishers was an "override" for AlbumPublishers.

**Corrected Understanding:** They are **two semantically different relationships**:

| Table | Meaning | Example |
|-------|---------|---------|
| `RecordingPublishers` | Who owns the **master recording** | Northern Songs owns "Help" |
| `AlbumPublishers` | Who **released this specific album** | Sony released the 2009 remaster |

**User's Original Friction:** "I wanted to edit a song's publisher but couldn't."

**Root Cause:** The UI didn't clearly expose `RecordingPublishers` for songs.

---

**Revised Solution: Just UI Clarity**

| User Sees | Stored In | Where in UI |
|-----------|-----------|-------------|
| "Master Owner" | `RecordingPublishers` | Song Side Panel → Publisher chip |
| "Released By" | `AlbumPublishers` | Album Detail → Publisher section |

**No inheritance logic needed!** Just show both publishers in their proper contexts.

**Code Changes:**
1. Song Side Panel: Add/edit `RecordingPublishers` directly (not via album)
2. Album Panel: Already shows `AlbumPublishers` — verify it works
3. Deprecate `SongAlbums.TrackPublisherID` — documented as legacy, no code change needed

**What If Song Has No RecordingPublisher?**
- That's fine — master owner is simply "unknown"
- User can add it manually anytime
- **No forced album creation needed!** ✅

**Effort:** ~1 hour (UI only)

---

### Phase 3: Strengthen Adapter Return Types

**Current Problem:** `adapter.link()` returns `True/False` with no explanation.

**Proposed:** Return a result object:

```python
@dataclass
class LinkResult:
    success: bool
    reason: Optional[str] = None  # 'already_linked', 'not_found', 'cycle_detected', etc.
    
class ContextAdapter(ABC):
    @abstractmethod
    def link(self, child_id: int, **kwargs) -> LinkResult:
        ...
```

**UI Change:** `entity_list_widget.py` can show specific error messages:
```python
if not result.success:
    QMessageBox.warning(self, "Action Failed", result.reason or "Unknown error")
```

**Effort:** ~1.5 hours

---

### Phase 4: Minor Normalizations (Incremental)

These can be done incrementally, not blocking:

#### 4a. TagCategories Table

**Current:** `Tags.TagCategory` is a free-text field ("Genre", "Mood", etc.)

**Problem:** 
- Can't add metadata to categories (icon, color, required flag)
- Different languages might use different category names
- Per-DJ personal categories (e.g., "favourites:bob") need structure

**Proposed:**
```sql
CREATE TABLE TagCategories (
    CategoryID INTEGER PRIMARY KEY,
    CategoryName TEXT NOT NULL UNIQUE,    -- "Genre", "Mood", "favourites:bob"
    CategoryIcon TEXT,                    -- "🎵", "😊", etc.
    CategoryColor TEXT,                   -- "#FF5733" for UI styling
    IsSystemCategory BOOLEAN DEFAULT 0,   -- TRUE for Genre/Mood/Language
    OwnerUserID TEXT,                     -- NULL = global, else per-user category
    DisplayOrder INTEGER DEFAULT 0
);

-- Migrate Tags to use FK
ALTER TABLE Tags ADD COLUMN CategoryID INTEGER REFERENCES TagCategories(CategoryID);
-- Backfill from TagCategory text, then drop TagCategory column
```

**Effort:** ~1.5 hours

---

#### 4b. Future: Multi-User UUID Support

**Current:** `ActionLog.UserID` and `ChangeLog.BatchID` exist but aren't linked to a Users table.

**When Multi-User Arrives:**
```sql
CREATE TABLE Users (
    UserID TEXT PRIMARY KEY,              -- UUID
    UserName TEXT NOT NULL,
    UserEmail TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- All transaction tables get UserID FK
ALTER TABLE ChangeLog ADD COLUMN UserID TEXT REFERENCES Users(UserID);
ALTER TABLE ActionLog ... -- already has UserID
ALTER TABLE MediaSourceTags ADD COLUMN AppliedByUserID TEXT REFERENCES Users(UserID);
ALTER TABLE MediaSourceTags ADD COLUMN AppliedAt DATETIME DEFAULT CURRENT_TIMESTAMP;
```

**Impact:** Every create/update/delete operation needs to capture current user UUID.

**Effort:** ~3 hours (when needed)

---

#### 4c. Publishers: Type Distinction (Optional Clarity)

**Current Design (Already Correct!):**
- `RecordingPublishers` = Original master owner (e.g., Northern Songs for "Help")
- `AlbumPublishers` = Release label for that specific album (e.g., Sony for modern reissue)

This is industry-correct! The two junction tables already model the RELATIONSHIP properly.

**Optional Enhancement:** Add `PublisherType` for display/filtering clarity:
```sql
ALTER TABLE Publishers ADD COLUMN PublisherType TEXT 
    CHECK(PublisherType IN ('label', 'publisher', 'distributor'))
    DEFAULT 'label';
```

- `'publisher'` = Owns composition (songwriter royalties) — rarely needed for radio
- `'label'` = Owns master / releases product (what radio usually cares about)
- `'distributor'` = Gets music to stores (rarely needed)

**Verdict:** Low priority. Current schema is correct; this just adds metadata.

**Effort:** ~0.5 hours if desired

---

#### 4d. Roles: Categorization for Reporting

**Current:** `Roles` table only has `RoleName` (Performer, Composer, Lyricist, Producer).

**Problem:** Royalty reporting rules vary:
- Sometimes report only Composer + Lyricist
- Sometimes include Producer
- "Featuring Artist" should display differently than "Performer"

**Proposed:**
```sql
ALTER TABLE Roles ADD COLUMN RoleCategory TEXT 
    CHECK(RoleCategory IN ('primary', 'composition', 'production', 'featured'))
    DEFAULT 'primary';

ALTER TABLE Roles ADD COLUMN ShowInCredits BOOLEAN DEFAULT 1;
ALTER TABLE Roles ADD COLUMN ShowInReport BOOLEAN DEFAULT 1;
ALTER TABLE Roles ADD COLUMN DisplayOrder INTEGER DEFAULT 0;
```

**Default Mapping:**
| Role | Category | ShowInCredits | ShowInReport |
|------|----------|---------------|--------------|
| Performer | primary | 1 | 1 |
| Featuring | featured | 1 | 1 |
| Composer | composition | 1 | 1 |
| Lyricist | composition | 1 | 1 |
| Producer | production | 1 | 0 (varies) |
| Engineer | production | 0 | 0 |

**Benefit:** Also helps with "feat." display — query roles where `RoleCategory = 'featured'`.

**Effort:** ~1 hour

---

#### 4e. SongAlbums: Enforce Single Primary Album

**Current:** Nothing prevents multiple `IsPrimary = 1` for the same song.

**Proposed:** Add partial unique index:
```sql
CREATE UNIQUE INDEX idx_single_primary_album 
ON SongAlbums(SourceID) 
WHERE IsPrimary = 1;
```

This ensures each song can have at most ONE primary album.

**Effort:** ~0.5 hours (trivial, just add to migrations)

---

## 📋 Migration Checklist

### Phase 1: AlbumArtist Removal
- [x] Add migration function to `database.py` or separate migration script
- [x] Update `Album` model: make `album_artist` a computed property
- [x] Update `AlbumRepository._insert_db()`: Remove AlbumArtist from INSERT
- [x] Update `AlbumRepository._update_db()`: Remove AlbumArtist from UPDATE  
- [x] Update `AlbumRepository.get_by_id()`: Remove fallback to AlbumArtist TEXT
- [x] Update `AlbumRepository.search()`: Search via AlbumContributors JOIN
- [x] Update `AlbumRepository.create()`: Ensure contributors are linked via M2M
- [x] Update `AlbumRepository.assign_album()`: Already uses M2M, verify
- [x] Update ID3 Import (`metadata_service.py`): Write artist to AlbumContributors
- [x] Update ID3 Export (`metadata_service.py`): Read artist from AlbumContributors
- [x] Run test suite (expect failures, fix them)
- [x] Verify existing albums display correctly in UI

### Phase 2: Publisher UI Clarity
- [x] Verify Song Side Panel shows "Master Owner" from `RecordingPublishers`
- [x] Verify Album Panel shows "Released By" from `AlbumPublishers`
- [x] Add UI to add/edit `RecordingPublishers` directly from song view
- [x] Document `SongAlbums.TrackPublisherID` as deprecated

### Phase 3: LinkResult Refactor
- [ ] Create `LinkResult` dataclass in `context_adapters.py`
- [ ] Update `ContextAdapter.link()` signature (breaking change)
- [ ] Update all adapter implementations
- [ ] Update `EntityListWidget._do_add()` to use result.reason
- [ ] Run test suite

### Post-Migration
- [ ] Run full test suite (must pass)
- [ ] Manual smoke test: Import song, edit album, add artist
- [ ] Verify audit log captures all changes
- [ ] Update `DATABASE.md` to reflect new schema
- [ ] Commit with message: "Schema V2: Remove AlbumArtist TEXT, standardize M2M"

---

## 🎯 Success Criteria

1. **No TEXT-based artist fields** in Albums table
2. **Single source of truth** for Album ↔ Artist relationship
3. **Clear error messages** when link operations fail
4. **All tests pass** after migration
5. **DATABASE.md** accurately reflects actual schema

---

## ⏳ Effort Estimate

| Phase | Task | Hours |
|-------|------|-------|
| 1 | AlbumArtist removal + migration | 3.0 |
| 2 | Publisher UI clarity (not inheritance) | 1.0 |
| 3 | LinkResult refactor | 1.5 |
| 4a | TagCategories normalization | 1.5 |
| 4b | Multi-user UUID support | 3.0 (future) |
| 4c | Publisher type column (optional) | 0.5 |
| 4d | Roles categorization for reporting | 1.0 |
| 4e | IsPrimary unique constraint | 0.5 |
| - | Testing + Documentation | 1.5 |
| **Total (now)** | Phases 1-3 + 4a + 4d + 4e | **10.0** |
| **Total (with optional)** | + 4b + 4c | **13.5** |

---

## 🤔 Decisions Needed

1. ~~**Keep or Drop RecordingPublishers?**~~ ✅ **RESOLVED: KEEP (Different Semantics!)**
   - RecordingPublishers = Who owns the **master recording** (e.g., Northern Songs)
   - AlbumPublishers = Who **released this album** (e.g., Sony remaster)
   - These are NOT override/fallback — they're two different relationships!

2. ~~**Keep or Drop SongAlbums.TrackPublisherID?**~~ ✅ **RESOLVED: DEPRECATE**
   - Redundant now that RecordingPublishers is properly exposed in UI
   - Can be removed in a future version (low priority)

3. **Migration Strategy:**
   - **Option A:** Migrate in-place (add migration code to `_ensure_schema`)
   - **Option B:** Create a standalone migration script
   - **Option C:** Fresh database with import tools

---

## Appendix: Current vs Target Schema

### Albums Table

**Current:**
```sql
CREATE TABLE Albums (
    AlbumID INTEGER PRIMARY KEY,
    AlbumTitle TEXT NOT NULL,
    AlbumArtist TEXT,          -- ❌ REMOVE THIS
    AlbumType TEXT,
    ReleaseYear INTEGER
);
```

**Target:**
```sql
CREATE TABLE Albums (
    AlbumID INTEGER PRIMARY KEY,
    AlbumTitle TEXT NOT NULL,
    AlbumType TEXT,
    ReleaseYear INTEGER
);
-- Artist info comes ONLY from AlbumContributors M2M
```

### Album Model

**Current:**
```python
@dataclass
class Album:
    album_id: Optional[int]
    title: str
    album_artist: Optional[str] = None  # ❌ REMOVE or make computed
    album_type: Optional[str] = None
    release_year: Optional[int] = None
```

**Target:**
```python
@dataclass
class Album:
    album_id: Optional[int]
    title: str
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    # album_artist is now computed via repository/service call, not stored
```
