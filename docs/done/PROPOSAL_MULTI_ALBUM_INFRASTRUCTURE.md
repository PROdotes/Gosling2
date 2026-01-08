# Proposal: Modern Music Asset Architecture (v0.5)

> **Status**: FINAL BLUEPRINT (Industrial Alignment)  
> **Target**: T-22 (Albums), T-63 (Publishers), & Multi-API Compatibility  
> **Objective**: Implement a professional-grade M:M architecture for recordings, releases, and publishers, future-proofed for MusicBrainz/Discogs integration.

---

## 1. The Core Entities (The "Big Three")

To mirror reality and support multi-value ID3 tags (`TPUB`), we define three "anchors":

1.  **Recording (ISRC Anchor)**: The fixed audio capture. Owned by one or more **Master Labels**.
2.  **Release (UPC Anchor)**: The packaged product (Album/EP). Released by one or more **Release Labels**.
3.  **Track Appearance (The Link)**: The specific instance of a Recording on a Release. Can have a **Licensing Override** (The "Starred Song").

---

## 2. Technical Schema Overhaul (Junction-First)

We are moving away from flat Foreign Keys to **Junction Tables** for all assets to support joint ventures and future API syncing.

### A. The Master Owner Registry (`RecordingPublishers`)
*New Junction Table*
*   `SourceID` (FK)
*   `PublisherID` (FK)
*   *Purpose*: Stores the "P-Line" (Phonographic Copyright). Who owns this audio forever?

### B. The Release Label Registry (`AlbumPublishers`)
*Existing Junction Table (M:M Enabled)*
*   `AlbumID` (FK)
*   `PublisherID` (FK)
*   *Purpose*: Stores the label(s) on the spine of the product.

### C. The Track Appearance (`SongAlbums`)
*Updated Junction Table*
*   `SourceID` (FK)
*   `AlbumID` (FK)
*   `TrackNumber`, `DiscNumber`
*   **`IsPrimary`** (Boolean): Defines which album's metadata (Title, Year, Art) is written to the ID3 tags.
    *   **Default**: The first album linked to a song is automatically `IsPrimary=1`.
    *   **Promotion**: Linking a song to a new album sets `IsPrimary=0` by default. The user can "Promote" any link to Primary at any time.
*   ~~**`TrackPublisherID`** (Optional FK)~~: **DEPRECATED** – See Section D below for M:M replacement.

### D. Track Appearance Publishers (`TrackAppearancePublishers`)
*New Junction Table (M:M) – Replaces `SongAlbums.TrackPublisherID`*
*   `SourceID` (FK)
*   `AlbumID` (FK)
*   `PublisherID` (FK)
*   *Purpose*: The specific license(s) for this track on this album. Supports **multiple publishers** (e.g., collab artists with different labels).
*   *Composite Key*: `(SourceID, AlbumID, PublisherID)`

### E. External Identity Anchors (RESERVED - v0.3+)
*These fields are documented for alignment but will NOT be added to the live database until v0.3 integration begins.*
*   **`Songs.MusicBrainzRecordingID`** (Planned)
*   **`Albums.MusicBrainzReleaseID`** (Planned)
*   **`Albums.CatalogNumber`** (Planned)

---

## 3. The "Waterfall" Resolution Logic

When the UI or ID3 tagger asks for the **Publisher(s)**, the system resolves them in this order:

| Priority | Level | Source Table | Case Example |
|---|---|---|---|
| **1 (Highest)** | **Track Override** | `TrackAppearancePublishers` | A starred track on a compilation (M:M). |
| **2** | **Release Labels** | `AlbumPublishers` | The 3 labels on a Joint Venture album. |
| **3 (Fallback)** | **Master Owners** | `RecordingPublishers` | The original owner from the ISRC file. |

> ⚠️ **Implementation Status**: The Waterfall query logic is **NOT YET IMPLEMENTED**. Currently, the UI uses a simple JOIN on `AlbumPublishers` only.

---

## 4. ID3 Tagging & Reporting Policy

### A. Multi-Value `TPUB` (The Law of Asset Identity)
*   **Write Policy**: Gosling2 will export ALL resolved publishers from the "Waterfall". 
    *   **ID3v2.4 (Default)**: Uses null-byte separators (Industry Standard).
    *   **ID3v2.3 (Fallback)**: Uses `/` as a separator (Legacy support).
*   **Read Policy**: The `MetadataService` will treat the `TPUB` frame as a **list field**. 
    *   It will automatically split `/` separated strings (v2.3) into separate `RecordingPublisher` entries during scanning.
    *   This allows "Warner / Sony" in a legacy file to be cleanly ingested as two distinct entity links.

### B. ZAMP Monthly Reporting
The database structure allows a single query to fetch the exact list of labels associated with a broadcast event, ensuring accurate reporting for complex co-ownership cases.

---

## 5. UI Interaction Workflow

### A. The "Rack-Mount" Aesthetic (Reuse Strategy)
*   **Modular Styling**: The `AlbumManagerDialog` panes will strictly reuse the existing **Satin Metal** gradient and border styles defined in `theme.qss` for consistency.
*   **Pane Headers**: Use the `#PaneHeaderLabel` styling (Industrial Amber on Black) to create the uniform "Rack-Mount" equipment look.
*   **The "Joint"**: The `QSplitter::handle` will use the existing solid black "Void" style to create the physical separation between panes without adding new CSS assets.

### B. Usage Modes
1.  **Expert Mode (Chip Click)**: Hides the Search Pane (2). Focuses on editing metadata (3) and seeing context (1).
2.  **Linker Mode (+ Button)**: Shows all 4 panes. **Pane 1 (Context)** acts as a **Preview** to see the tracklist of your search results before linking.

### C. Publisher Chip Interaction Policy
*   **Inherited Chips** (🔗): Locked for direct editing in the Side Panel. 
    *   *Tooltip*: Shows "Inherited from [Album Title]".
    *   *Deep Link*: Clicking an inherited chip jumps to the **Album Manager** for that specific release.
*   **Local Chips** (Solid): Fully editable. These live in **`SongAlbums.TrackPublisherID`** (Level 1).
*   **Shadow Logic**: The "Local Chip" acts as a **Track Override**, effectively "shadowing" (hiding) the inherited Album Publishers (Level 2) for that specific song.

### D. Primary Identity Toggle
*   **The "Star" Control**: In the **Album Manager (Pane 1: Tracklist)**, each song will have a star/home icon indicating its primary album.
*   **Interaction**: Right-clicking a song in any album context allows the user to **"Set as Primary Album"**.
*   **Effect**: This flips the `IsPrimary` bits in the database and triggers a "Side Panel Refresh" to update the displayed Album Title and Year.

---

## 6. Data Integrity & Recovery (The "ID3 Anchor" Policy)

Since ID3 tags are the primary source of truth and fallback:

1.  **DB Loss Recovery**: If the database is wiped, a full library rescan will re-populate the new junction-first architecture (Recordings, Releases, and Publishers) using the multi-value tags found in the files.
2.  **Portable Metadata**: By writing the Waterfall Resolution back to the `TPUB` tag, songs sent to other stations or software will carry the correct multi-publisher info.
3.  **No Migration Script Required**: The system is designed to "Self-Heal" during imports. Any missing relational data will be reconstructed from the embedded ID3 tags during the next file scan.

---

## 7. Implementation Roadmap

### Phase 1: Database Migration (The "Rip")

**A. Status Check (Existing):**
- [x] `Songs`: `RecordingYear`, `ISRC`.
- [x] `Albums`: `Title`, `AlbumArtist`, `AlbumType`, `ReleaseYear`.
- [x] `Publishers`: `PublisherName`, `ParentPublisherID`.
- [x] `AlbumPublishers`: Junction (M:M).

**B. Required Changes (Immediate - v0.2):**
- [x] **`SongAlbums`**: Add `DiscNumber`, `IsPrimary`. *(Note: `TrackPublisherID` column exists but is deprecated – see D below)*
- [x] **`RecordingPublishers`**: Create new junction table.
- [ ] **`TrackAppearancePublishers`**: Create new junction table for M:M Track-Album-Publisher links (replaces `TrackPublisherID`).

**C. Future Alignment (Reserved - v0.3):**
- [ ] `Songs`: `MusicBrainzRecordingID`
- [ ] `Albums`: `MusicBrainzReleaseID`, `CatalogNumber`

---

### Phase 2: Repository Rebuild
- [ ] **`SongRepository`**: Implement **Waterfall Resolver** query (cascade Level 1 → 2 → 3). *(Schema exists, logic NOT implemented)*
- [x] **`SongRepository`**: Implement `List[Release]` hydration. *(Partial – query exists, but uses simple JOIN, not Waterfall)*
- [x] **`AlbumRepository`**: Support M:M updates (no delete/replace).
- [x] **`MetadataService`**: Update `id3_frames.json` to define `TPUB` as a `list` type. *(Done)*
- [ ] **`MetadataService`**: Update the scanner to pull multi-value `TPUB` into `Song.publisher`. *(Needs verification)*
- [ ] **`MetadataService`**: Update ID3 writer to export Waterfall-resolved `TPUB` (Write Policy). *(Blocked by Waterfall)*
- [ ] **`MetadataService`**: Implement Version-Aware TPUB Export (Null-byte for v2.4, '/' for v2.3). *(Not implemented)*
- [x] **`SongRepository`**: Fix `_sync_album` to be **Non-Destructive**. *(Done – demotes existing, doesn't delete)*
- [x] **`SongRepository`**: Auto-link loose files to "Single" release (The Single Paradox). *(Done in `_sync_publisher`)*
- [ ] **`SongRepository`**: Migrate `_sync_publisher` to use `TrackAppearancePublishers` (M:M) instead of `TrackPublisherID` (1:1).

---

### Phase 3: The Modular UI
- [x] **`SidePanelWidget`**: Replace buttons with `ChipTrayWidget`. *(Done)*
- [x] **`SidePanelWidget`**: Implement **Ghost Chips** logic (`is_inherited` property + styling). *(Fixed 2026-01-01 – duplicate elif removed)*
- [ ] **`SidePanelWidget`**: Implement "Shadow Logic" (allow adding local publisher even if inherited exists). *(Needs verification)*
- [ ] **`SidePanelWidget`**: Implement "Track Override Write" (Local Chip → `TrackAppearancePublishers`). *(Blocked by schema)*
- [x] **`SidePanelWidget`**: Implement **Deep Link** (Clicking Inherited Chip → Opens Album Manager). *(Fixed 2026-01-01 – display name mismatch)*
- [x] **`SidePanelWidget`**: Implement "Inheritance Tooltip" ("Inherited from [Album Title]"). *(Verified 2026-01-01)*
- [ ] **`SidePanelWidget`**: Ensure "Side Panel Refresh" triggers upon Primary Album toggle changes. *(Needs verification)*
- [x] **`AlbumManagerDialog`**: Implement **Pane Visibility** (Expert Mode hides Search/Vault). *(Done)*
- [x] **`AlbumManagerDialog`**: Apply **Void Style** to Splitter Handle (CSS Reuse). *(Done)*
- [x] **`AlbumManagerDialog`**: Implement Expert/Linker modes + Rack-Mount styling. *(Done)*
- [x] **`SidePanelWidget`**: Multi-album display (song on multiple albums shows multiple chips). *(Fixed 2026-01-01 – query now uses GROUP_CONCAT)*
- [x] **`AlbumRepository`**: `get_publisher` returns all album publishers. *(Fixed 2026-01-01 – was LIMIT 1)*

---

### Phase 4: Validation & Integrity
- [ ] **Recovery Test**: Verify DB wipe & rescan populates `RecordingPublishers` correctly.
- [ ] **Write Test**: Verify `TPUB` matches the Waterfall resolution in exported files. *(Blocked by Waterfall implementation)*
- [x] **Seed Test**: Run `RESEED.bat` and verify multi-publisher fixtures display correctly in UI. *(Verified 2026-01-01)*

---

## 8. Final Brainstorm Questions
1.  **Multiple ISRCs**: If a song is remixed, it gets a new ISRC. We treat these as separate **Recordings**.
2.  **The "Single" Paradox**: Loose files without albums will be auto-linked to a generated "Single" release to satisfy the product-record identity requirement.

---
