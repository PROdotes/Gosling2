---
tags:
  - layer/data
  - domain/database
  - domain/audio
  - status/planned
  - type/feature
  - size/medium
  - blocked/schema
links:
  - "[[DATABASE]]"
  - "[[PROPOSAL_LIBRARY_VIEWS]]"
---
# Architectural Proposal: Album Management

## 🚧 Blocker Warning
**Status:** BLOCKED by Schema Update.
**Reason:** Requires `Albums` entity table and `FileAlbums` junction table.

## 1. The Core Concept (Normalization)
Currently, album names are just text in the `Files` table. This causes redundancy and typos.
- **New Model:** Albums are first-class entities.
- **Relationship:** Many-to-Many (`FileAlbums`).
    - *Why Many-to-many?* A song can be on the original album ("Thriller") AND a compilation ("80s Hits").

## 2. Special Album Logic

### A. Compilations
- **Flag:** `Albums.IsCompilation` (Boolean).
- **Behavior:**
    - If `True`, the library view groups it under "Various Artists" sort key.
    - If `False`, it groups under the specific Artist.

### B. Singles
- **Problem:** Every single creating a new "Album" clutters the view.
- **Solution:** A special "Virtual Album" per artist called `[Singles]`? Or just strict `Type='Single'` filtering in the view.

## 3. Album Art Management
- **Storage:** The `Albums` table stores the `CoverArtPath`.
- **Optimization:** We scan for `folder.jpg` or `cover.png` once per Album, not once per File.
- **Cache:** The UI loads one image for the whole group.

## 4. Workflows
- **Grouping:** "Create Album from Selection" -> Takes 10 selected tracks, creates a new Album entity, links them.
- **Merging:** "Merge 'Thrller' and 'Thriller'" -> Re-links all songs to one ID, deletes the duplicate.
- **Orphan Policy:** Empty albums persist by default (preserves metadata). UX should prompt user to delete/cleanup when the last song is removed.

## 5. UI Integration
- **Grid View:** Driven entirely by the `Albums` table.
- **Editor:** "Album" field becomes a searchable combobox (Search existing albums) + "New..." button.

---

## 6. Technical Debt & Broken State (as of T-06)
- **Title Collision:** Current `AlbumRepository` merges albums solely by `Title`. "Greatest Hits" (ABBA) and "Greatest Hits" (Queen) will be merged into one entity.
- **Import Blindness:** `SongRepository` auto-creation is blind to Artist.
- **Orphans:** Logic to rename albums is missing.

## 7. Migration Plan (Task T-22)
1.  **Schema Upgrade:** Add `AlbumArtist` column to `Albums` table.
2.  **Smart Import:**
    - Read `TPE2` (Album Artist) from ID3.
    - Fallback to `TPE1` (Lead Artist) if `TPE2` missing.
    - Match Album by `(Title, AlbumArtist, ReleaseYear)`.
3.  **Review Workflow (Task T-32):**
    - If Import is ambiguous (fuzzy match), apply `System:PendingReview` tag to the Song.
    - UI "Inbox" filters for this tag for manual resolution.
