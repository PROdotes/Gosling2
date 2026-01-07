# Identity Model: People, Names, and Credits

**Status:** Proposal  
**Author:** Schema Audit (Jan 7, 2026)  
**Priority:** CRITICAL (Foundational Rework)  
**Related:** PROPOSAL_SCHEMA_V2.md

---

## 🚨 The Core Problem

The current model conflates three distinct concepts:

1. **Identity** — The real person/group (David Bowie, the human born David Jones)
2. **Name** — A name used by that identity (David Bowie, Ziggy Stardust, Thin White Duke)
3. **Credit** — The name AS CREDITED on a specific recording ("Ziggy Stardust and the Spiders from Mars")

### Current Pain Points

```
User: "Link Ziggy Stardust to David Bowie"

Current System:
  Option A: MERGE → Delete Ziggy, all songs now say "David Bowie" ❌ (Data loss!)
  Option B: ALIAS → Make "Ziggy" a string alias → 50 songs need updating ❌ (Destructive)

Desired Behavior:
  → Create a link: Ziggy's underlying identity = Bowie
  → All 50 songs STILL display "Ziggy Stardust" ✅ (Credits preserved)
  → Searching "David Bowie" finds Ziggy's songs ✅ (Discovery works)
  → Ziggy can later be UNLINKED without touching credits ✅ (Reversible)
```

---

## 🎯 Design Goals

1. **Credits are IMMUTABLE** — What's written on the record stays on the record
2. **Identities are LINKABLE** — Discover that two names = same person without destroying data
3. **Links are REVERSIBLE** — If we made a mistake, we can undo without data loss
4. **Groups are COMPOSITIONAL** — A group has members, members can use aliases within groups

---

## 📊 Proposed Model

### Conceptual Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        IDENTITY LAYER                           │
│  (The real person/group — stores DOB, bio, photos, etc.)        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│   │   Person    │     │   Person    │     │   Group     │       │
│   │ "D. Bowie"  │     │ "F. Mercury"│     │  "Queen"    │       │
│   │  (ID: 1)    │     │   (ID: 2)   │     │   (ID: 3)   │       │
│   └──────┬──────┘     └─────────────┘     └──────┬──────┘       │
│          │                                       │              │
│          │ owns                                  │ owns         │
│          ▼                                       ▼              │
├─────────────────────────────────────────────────────────────────┤
│                         NAME LAYER                              │
│  (Artist names — what appears in credits)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │ "D. Bowie"  │  │   "Ziggy    │  │  "Queen"    │             │
│   │  Name: 10   │  │  Stardust"  │  │  Name: 30   │             │
│   │ Owner: 1    │  │  Name: 11   │  │ Owner: 3    │             │
│   └──────┬──────┘  │ Owner: 1    │  └──────┬──────┘             │
│          │         └──────┬──────┘         │                    │
│          │                │                │                    │
│          │ credited as    │ credited as    │ credited as        │
│          ▼                ▼                ▼                    │
├─────────────────────────────────────────────────────────────────┤
│                        CREDIT LAYER                             │
│  (Actual credits on songs/albums — IMMUTABLE)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Song: "Heroes"           Song: "Starman"      Album: "News"   │
│   Performer: Name 10       Performer: Name 11   Artist: Name 30 │
│   (shows "D. Bowie")       (shows "Ziggy...")   (shows "Queen") │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗃️ Proposed Schema

### 1. `Identities` (NEW — The Real Person/Group)

Replaces the "person holder" role of `Contributors`.

```sql
CREATE TABLE Identities (
    IdentityID INTEGER PRIMARY KEY,
    IdentityType TEXT CHECK(IdentityType IN ('person', 'group')) NOT NULL,
    
    -- Person-specific fields (NULL for groups)
    LegalName TEXT,              -- "David Robert Jones"
    DateOfBirth DATE,
    DateOfDeath DATE,
    Nationality TEXT,
    
    -- Group-specific fields (NULL for persons)
    FormationDate DATE,
    DisbandDate DATE,
    
    -- Shared fields
    Biography TEXT,
    Notes TEXT
);
```

### 2. `ArtistNames` (NEW — Names Owned by Identities)

Replaces `Contributors` + `ContributorAliases`.

```sql
CREATE TABLE ArtistNames (
    NameID INTEGER PRIMARY KEY,
    OwnerIdentityID INTEGER,                -- Who owns this name (NULL = orphan/unassigned)
    DisplayName TEXT NOT NULL,              -- "Ziggy Stardust"
    SortName TEXT,                          -- "Stardust, Ziggy"
    IsPrimaryName BOOLEAN DEFAULT 0,        -- Is this the identity's main name?
    DisambiguationNote TEXT,                -- "drummer, UK" for pickers (not shown in credits)
    
    FOREIGN KEY (OwnerIdentityID) REFERENCES Identities(IdentityID)
);

-- Indexes for performance
CREATE INDEX idx_artistnames_owner ON ArtistNames(OwnerIdentityID);
CREATE INDEX idx_artistnames_display ON ArtistNames(DisplayName);
```

**Disambiguation in UI:**
- Credit display: Shows "John Smith" (clean)
- Picker display: Shows "John Smith (drummer, UK)" (disambiguated)
- Search: Matches on DisplayName AND DisambiguationNote

### 3. `GroupMemberships` (REPLACES `GroupMembers`)

Links persons to groups, with optional "credited as" name.

```sql
CREATE TABLE GroupMemberships (
    MembershipID INTEGER PRIMARY KEY,
    GroupIdentityID INTEGER NOT NULL,       -- The group
    MemberIdentityID INTEGER NOT NULL,      -- The person
    CreditedAsNameID INTEGER,               -- Optional: name used in this group
    JoinDate DATE,
    LeaveDate DATE,
    
    FOREIGN KEY (GroupIdentityID) REFERENCES Identities(IdentityID),
    FOREIGN KEY (MemberIdentityID) REFERENCES Identities(IdentityID),
    FOREIGN KEY (CreditedAsNameID) REFERENCES ArtistNames(NameID),
    
    UNIQUE(GroupIdentityID, MemberIdentityID)  -- One membership per person-group pair
);
```

### 4. `SongCredits` (REPLACES `MediaSourceContributorRoles`)

The IMMUTABLE credit record.

```sql
CREATE TABLE SongCredits (
    CreditID INTEGER PRIMARY KEY,
    SourceID INTEGER NOT NULL,              -- The song
    CreditedNameID INTEGER NOT NULL,        -- The name AS CREDITED (immutable!)
    RoleID INTEGER NOT NULL,                -- Performer, Composer, etc.
    CreditPosition INTEGER DEFAULT 0,       -- Order for display (0 = first)
    
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (CreditedNameID) REFERENCES ArtistNames(NameID),
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
    
    UNIQUE(SourceID, CreditedNameID, RoleID)
);
```

> **Note:** Schema V2 proposes adding `RoleCategory` to the `Roles` table (e.g., 'primary', 'featured', 'composition'). If implemented, the "feat." logic can use `Roles.RoleCategory = 'featured'` instead of a separate `IsFeatured` column. This keeps role metadata on the Role, not duplicated on every credit.

**Display logic for "Queen feat. David Bowie":**
```python
credits = get_credits_for_song(source_id)
performers = [c for c in credits if c.role.category == 'primary']
featured = [c for c in credits if c.role.category == 'featured']

if featured:
    display = f"{', '.join(performers)} feat. {', '.join(featured)}"
else:
    display = ', '.join(performers)
```

### 5. `AlbumCredits` (REPLACES `AlbumContributors`)

Same pattern for albums.

```sql
CREATE TABLE AlbumCredits (
    CreditID INTEGER PRIMARY KEY,
    AlbumID INTEGER NOT NULL,
    CreditedNameID INTEGER NOT NULL,
    RoleID INTEGER NOT NULL,
    
    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
    FOREIGN KEY (CreditedNameID) REFERENCES ArtistNames(NameID),
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
    
    UNIQUE(AlbumID, CreditedNameID, RoleID)
);
```

---

## 🔄 Migration Mapping

| Old Table | New Table(s) | Notes |
|-----------|--------------|-------|
| `Contributors` | `Identities` + `ArtistNames` | Split into two layers |
| `ContributorAliases` | `ArtistNames` | Aliases become first-class names |
| `GroupMembers` | `GroupMemberships` | Add temporal + credited-as fields |
| `MediaSourceContributorRoles` | `SongCredits` | Rename for clarity |
| `AlbumContributors` | `AlbumCredits` | Rename for clarity |

---

## 🎭 Scenario Walkthroughs

### Scenario 1: "Link Ziggy to Bowie"

**Before:**
```
Identities:
  ID 1: Person "David Bowie" (has biography, DOB, etc.)
  ID 2: Person "Ziggy Stardust" (has some data)

ArtistNames:
  NameID 10: "David Bowie" → Owner: Identity 1
  NameID 11: "Ziggy Stardust" → Owner: Identity 2

SongCredits:
  Song "Starman" → Performer: NameID 11 (shows "Ziggy Stardust")
```

**Action:** User links Ziggy to Bowie

**System Check:**
```
Does Identity 2 (Ziggy) have unique data that Identity 1 (Bowie) lacks?
  - DOB? → Ziggy has none, Bowie has 1947-01-08 → No conflict
  - Biography? → Ziggy has "Alter ego persona" → POTENTIAL LOSS

⚠️ WARNING: "Ziggy Stardust has a biography that will be lost. Merge anyway?"
  [ ] Append Ziggy's bio to Bowie's
  [ ] Discard Ziggy's bio
  [Cancel]
```

**After Merge:**
```
Identities:
  ID 1: Person "David Bowie" (merged data)
  ID 2: DELETED (or soft-deleted)

ArtistNames:
  NameID 10: "David Bowie" → Owner: Identity 1  (unchanged)
  NameID 11: "Ziggy Stardust" → Owner: Identity 1  (RE-PARENTED!)

SongCredits:
  Song "Starman" → Performer: NameID 11 (STILL shows "Ziggy Stardust"!) ✅
```

**Result:**
- Song credits UNCHANGED
- "Ziggy Stardust" is now a name owned by Bowie
- Searching "David Bowie" finds "Starman" via the name ownership chain

---

### Scenario 2: "Add The Ghost of Mixes as a member of DJ Someone's group"

**Before:**
```
Identities:
  ID 5: Person "DJ Someone"
  ID 6: Group "Beats Collective"

ArtistNames:
  NameID 50: "DJ Someone" → Owner: Identity 5
  NameID 51: "The Ghost of Mixes" → Owner: Identity 5  (alias)
```

**Action:** Add "The Ghost of Mixes" as member of "Beats Collective"

**System:**
```
GroupMemberships:
  INSERT (GroupIdentityID: 6, MemberIdentityID: 5, CreditedAsNameID: 51)
```

**Result:**
- "Beats Collective" now shows member: "The Ghost of Mixes"
- NOT "DJ Someone" — because we specified the credited name

---

### Scenario 3: "Unlink Ziggy from Bowie" (Oops, they're actually different people!)

**Before:**
```
ArtistNames:
  NameID 11: "Ziggy Stardust" → Owner: Identity 1 (Bowie)
```

**Action:** User realizes Ziggy is actually a separate person, wants to unlink

**System:**
```
1. Create new Identity for Ziggy:
   INSERT INTO Identities (IdentityType) VALUES ('person') → ID 7

2. Re-parent the name:
   UPDATE ArtistNames SET OwnerIdentityID = 7 WHERE NameID = 11
```

**Result:**
- Song credits STILL show "Ziggy Stardust"
- Ziggy is now an independent person
- NO DATA LOSS

---

## 🔍 Query Examples

### "Find all songs by David Bowie (including aliases)"

```sql
SELECT DISTINCT ms.SourceID, ms.MediaName
FROM MediaSources ms
JOIN SongCredits sc ON ms.SourceID = sc.SourceID
JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
WHERE i.IdentityID = 1  -- Bowie's identity ID
   OR an.DisplayName LIKE '%Bowie%';  -- Fallback text search
```

### "Search by legal name (e.g., 'Alecia Moore' → finds P!nk songs)"

```sql
-- Unified artist search that spans ALL name fields
SELECT DISTINCT ms.SourceID, ms.MediaName, an.DisplayName AS CreditedAs
FROM MediaSources ms
JOIN SongCredits sc ON ms.SourceID = sc.SourceID
JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
LEFT JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
WHERE an.DisplayName LIKE '%alecia%'           -- Stage name
   OR an.SortName LIKE '%alecia%'              -- Sort name
   OR an.DisambiguationNote LIKE '%alecia%'    -- Disambiguation
   OR i.LegalName LIKE '%alecia%';             -- Real name → finds P!nk!
```

**Result:**
| SourceID | MediaName | CreditedAs |
|----------|-----------|------------|
| 500 | "So What" | P!nk |
| 501 | "Raise Your Glass" | P!nk |

✅ Searching "Alecia Moore" finds P!nk songs because `Identity.LegalName = 'Alecia Beth Moore'`

### "Show all names used by this person"

```sql
SELECT DisplayName, IsPrimaryName
FROM ArtistNames
WHERE OwnerIdentityID = 1
ORDER BY IsPrimaryName DESC, DisplayName;
```

### "Show group members with their credited names"

```sql
SELECT 
    an.DisplayName AS CreditedAs,
    i.LegalName AS RealName
FROM GroupMemberships gm
JOIN Identities i ON gm.MemberIdentityID = i.IdentityID
LEFT JOIN ArtistNames an ON gm.CreditedAsNameID = an.NameID
WHERE gm.GroupIdentityID = 6;  -- The group
```

---

## 📊 Entity Diagram

```
┌─────────────┐       ┌───────────────┐       ┌─────────────┐
│ Identities  │──1:N──│  ArtistNames  │──1:N──│ SongCredits │
│  (Person/   │       │ (Owned names) │       │  (On songs) │
│   Group)    │       └───────────────┘       └─────────────┘
└──────┬──────┘               │
       │                      │
       │ GroupMemberships     │ CreditedAsNameID
       │ (M:N with            │ (Optional)
       │  credited name)      │
       └──────────────────────┘
```

---

## ⚠️ Breaking Changes

This is a **major architectural change**. All of the following need updates:

1. **Data Layer:**
   - New tables: `Identities`, `ArtistNames`, `GroupMemberships`, `SongCredits`, `AlbumCredits`
   - Migration script to split `Contributors` into two layers

2. **Repository Layer:**
   - `ContributorRepository` → `IdentityRepository` + `ArtistNameRepository`
   - New `CreditRepository` for song/album credits

3. **Service Layer:**
   - `ContributorService` → `IdentityService` + `NameService`
   - New merge/unmerge logic with conflict detection

4. **UI Layer:**
   - Artist picker now searches `ArtistNames`, returns `NameID`
   - Artist editor shows Identity info + list of owned names
   - Merge/unlink dialogs with conflict warnings

5. **Context Adapters:**
   - All adapters need to work with `NameID` instead of `ContributorID`

---

## 🧮 Effort Estimate

| Task | Hours |
|------|-------|
| Schema design + migration script | 4.0 |
| Repository layer rewrite | 4.0 |
| Service layer rewrite | 3.0 |
| UI updates (pickers, editors) | 4.0 |
| Context adapter updates | 2.0 |
| Testing + Documentation | 3.0 |
| **Total** | **20.0** |

**Recommendation:** This is a 2.5-day effort. Should be done BEFORE more features pile on.

---

## ⚠️ Potential Edge Cases & Future Issues

### 1. Collaborative Credits ("Queen feat. David Bowie")

**Problem:** How do we represent "Queen feat. David Bowie" or "David Bowie & Bing Crosby"?

**Options:**
- **A) Separate credit rows:** Two SongCredits, each with a different NameID
  - ✅ Clean relational model
  - ❌ Loses the "feat." or "&" relationship type
  
- **B) Composite credit entity:** New `CreditGroup` table with ordered members + relationship type
  ```sql
  CreditGroups (CreditGroupID, CreditType: 'featuring', 'with', 'and', 'vs')
  CreditGroupMembers (CreditGroupID, NameID, Position)
  ```
  - ✅ Preserves order and relationship
  - ❌ More complex, may be overkill

**Recommendation:** Start with Option A. Add Option B later if needed.

---

### 2. Name Collisions ("John Smith" × 2)

**Problem:** Two different people named "John Smith". User imports a song by "John Smith" — which one?

**Current Design:** Each name is tied to ONE identity. So we'd have:
- NameID 100: "John Smith" → Identity 1 (the drummer)
- NameID 101: "John Smith" → Identity 2 (the DJ)

**Resolution Flow:**
1. Import sees "John Smith" (string)
2. Search finds TWO matching names
3. Prompt: "Which John Smith? [The drummer from Band X] or [DJ from City Y]?"
4. User picks → Credit links to that NameID

**Edge Case:** What if user clicks "Create New" for every John Smith?
- They end up with 50 different "John Smith" identities
- Need a periodic "duplicate detection" audit tool

---

### 3. Temporal Names ("The Artist Formerly Known As...")

**Problem:** Prince → ⌂ → Prince again. Are these the same name or different?

**Current Design:** Names don't have date ranges. 

**Options:**
- **A) Ignore temporality:** All "Prince" credits link to one NameID
  - ✅ Simple
  - ❌ Can't distinguish "1980s Prince" from "2010s Prince"
  
- **B) Add date fields to ArtistNames:** `ActiveFrom`, `ActiveTo`
  - ✅ More accurate
  - ❌ Complicates the model, rarely needed for radio

**Recommendation:** Ignore for now. Add if a real use case emerges.

---

### 4. Orphan Names (Name with NULL OwnerIdentityID)

**Problem:** During import, we create a name before we know who owns it.

**Options:**
- **A) Require identity on creation:** Every name must have an owner
  - ✅ Clean data
  - ❌ Friction during import (must create identity first)
  
- **B) Allow orphan names temporarily:** NULL OwnerIdentityID allowed
  - ✅ Flexible import
  - ❌ Need cleanup process for orphans

**Recommendation:** Allow orphans but flag them in UI. Add "Unassigned Names" admin view.

---

### 5. Nested Groups ("Traveling Wilburys")

**Problem:** Tom Petty is in "Traveling Wilburys" but also leads "Tom Petty and the Heartbreakers".

**Current Design:** GroupMemberships links Person → Group. Works fine!

**Edge Case:** Can a GROUP be a member of another GROUP?
- "All-Star Band" contains "The Heartbreakers" (as a unit)

**Options:**
- **A) No group-in-group:** Only persons can be members
  - ✅ Simple
  - ❌ Can't model "supergroups of groups"
  
- **B) Allow group-in-group:** MemberIdentityID can reference any identity
  - ✅ Flexible
  - ⚠️ Need cycle detection (A contains B contains A)

**Recommendation:** Allow group-in-group. Add cycle detection validation.

---

### 6. Album Artist ≠ Track Artist

**Problem:** Album by "Various Artists" but tracks have individual performers.

**Current Design:** 
- AlbumCredits: "Various Artists" (NameID for the compilation identity)
- SongCredits: "Actual Performer" per track

**This works!** But needs clear UI:
- Album view shows album artist
- Track list shows track artists
- Side panel shows correct context based on what's selected

---

### 7. ID3 Round-Tripping & Cross-Database Import

**Problem:** When we export to ID3:
- Do we write "Ziggy Stardust" or "David Bowie"?
- Internal NameIDs are meaningless if file moves to a different Gosling2 install

**Solution: Hybrid export with fallback chain**
```
# Standard fields (always portable)
TPE1 (Artist): "Ziggy Stardust"              ← Display name (always works)

# Internal reference (for same-database re-import)
TXXX:GOSLING_NAME_ID: "100"                  ← Fast lookup if same DB

# Human-readable fallback (for cross-database import)
TXXX:GOSLING_IDENTITY_NAME: "David Bowie"    ← Text match on identity

# Industry standard (if known)
TXXX:MUSICBRAINZ_ARTIST_ID: "abc-123-def"    ← Universal interop
```

**Import Resolution Chain:**
1. Check `TXXX:MUSICBRAINZ_ARTIST_ID` → Exact match if we have it
2. Check `TXXX:GOSLING_NAME_ID` → Direct link if same database
3. Check `TXXX:GOSLING_IDENTITY_NAME` → Search identities by name
4. Fallback to `TPE1` → Text match on ArtistNames.DisplayName
5. No match? → Create new orphan name, flag for review

---

### 8. "Various Artists" and "Unknown Artist"

**Problem:** Special identities that don't represent real people.

**Solution:** Create reserved identities:
```sql
INSERT INTO Identities VALUES (0, 'placeholder', 'Unknown Artist');
INSERT INTO Identities VALUES (-1, 'placeholder', 'Various Artists');
INSERT INTO ArtistNames VALUES (0, 0, 'Unknown Artist', NULL, 1);
INSERT INTO ArtistNames VALUES (-1, -1, 'Various Artists', NULL, 1);
```

Flag these in UI (non-editable, special styling).

---

### 9. Sort Name Inheritance

**Problem:** If "P!nk" → OwnerIdentity "Alecia Moore", what's the sort name?
- ArtistNames.SortName? Or fallback to Identity.LegalName?

**Solution:** Explicit hierarchy:
1. `ArtistNames.SortName` if set
2. Else `Identities.LegalName` (for persons)
3. Else `ArtistNames.DisplayName` (final fallback)

---

### 10. Performance: Many Names per Identity

**Problem:** David Bowie might have 20 name variants. Query for "all Bowie songs" needs to find all 20.

**Solution:** Ensure index on `ArtistNames.OwnerIdentityID`:
```sql
CREATE INDEX idx_artistnames_owner ON ArtistNames(OwnerIdentityID);
```

Query becomes:
```sql
SELECT DISTINCT sc.SourceID 
FROM SongCredits sc
JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
WHERE an.OwnerIdentityID = ?;
```

---

## 📋 Edge Case Summary

| Edge Case | Risk | Current Plan | Future Work |
|-----------|------|--------------|-------------|
| Collaborative credits | Medium | Separate rows | Add CreditGroups later |
| Name collisions | Low | Disambiguation picker | Duplicate detection tool |
| Temporal names | Low | Ignore | Add if needed |
| Orphan names | Medium | Allow + flag | Admin cleanup view |
| Nested groups | Low | Allow + cycle check | Validate on insert |
| Album vs Track artist | None | Works as designed | Clear UI context |
| ID3 round-trip | Medium | Custom TXXX frames | Already planned |
| Special artists | Low | Reserved IDs | Style in UI |
| Sort name inheritance | Low | Explicit hierarchy | Document clearly |
| Query performance | Low | Proper indexes | Monitor in production |

---

## ✅ Decision Points

1. **Do we keep `Contributors` as a view for backward compatibility?**
   - YES → Less code changes, but confusing naming
   - NO → Clean break, but more refactoring

2. **Soft-delete or hard-delete merged identities?**
   - Soft-delete → Allows recovery but clutters DB
   - Hard-delete → Clean but irreversible

3. **Do Names have their own metadata (e.g., "name active from 1972-1975")?**
   - YES → More accurate but complex
   - NO → Simpler, good enough for radio

4. **Phase this in or do a big-bang migration?**
   - Phased → Less risky but maintains two systems temporarily
   - Big-bang → Cleaner but more testing required

---

## 🚀 Next Steps

1. Review and approve this proposal
2. Create migration script (can test on copy of DB)
3. Implement new repositories
4. Update UI pickers to use new model
5. Migrate existing data
6. Update documentation
