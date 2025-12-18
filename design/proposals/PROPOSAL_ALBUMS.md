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
- **Orphan Cleanup:** System task to delete Albums that have 0 linked files.

## 5. UI Integration
- **Grid View:** Driven entirely by the `Albums` table.
- **Editor:** "Album" field becomes a searchable combobox (Search existing albums) + "New..." button.
