# Portable Relational Metadata (The "Indestructible Library")

## Problem
Gosling2 stores rich relational data (Person/Group hierarchies, Aliases, specific Roles, Song Links) in its SQLite database. Standard ID3 tags (`TPE1`, `TALB`) are "flat" and cannot represent these structures.

**Risk:** If the database is corrupted or deleted, all structural knowledge is lost.
- "Gabry Ponte" becomes a stranger to "Gabriele Ponte".
- "Queen" forgets it contains "Freddie Mercury".
- "Instrumental" versions lose their link to the "Main Mix".

## Solution: Entity Anchors
We will use custom `TXXX` (User Defined Text) frames to act as "Anchors" or "Passports" for entities. This allows the database to be fully reconstructed solely from the files.

---

## 1. Identity Anchors (Solves Aliases & Groups)

When saving a track, we write the **UUID** of the primary identity, not just the name.

### Tag: `TXXX:GOSLING_ARTIST_UUID`
Stores the unique identifier of the **Performer Identity**.

**Example:**
- **File:** `Words.mp3`
- **TPE1 (Display):** `Gabry Ponte`
- **GOSLING_ARTIST_UUID:** `550e8400-e29b-41d4-a716-446655440000` (ID for Gabriele Ponte)

**Recovery Flow:**
1. Scanner finds `Gabry Ponte`.
2. Reads UUID.
3. Checks DB: Does Identity `550e...` exist?
   - **Yes:** Link "Gabry Ponte" as an **Alias** of that Identity.
   - **No:** Create new Identity "Gabriele Ponte" (we might need a `GOSLING_ARTIST_PRIMARY` tag too if the file credit is an alias).

---

## 2. Rich Credits (Solves "Who did what")

Standard ID3 `TIPL` (Involved People List) is poorly supported. We will use a structured JSON-like format for detailed credits.

### Tag: `TXXX:GOSLING_CREDITS`
Serialized list of `Role:Name` pairs or a mini-JSON object.

**Format:** `Role|Name;Role|Name`

**Example:**
`Composer|Gabriele Ponte;Performer|Gabry Ponte;Producer|Luny Tunes`

**Recovery Flow:**
1. Parse string.
2. Resolve names to Identities (using UUIDs if we implement multi-value UUID tags, or fuzzy matching otherwise).
3. Re-populate `SongCredits` table.

---

## 3. Album Anchors (Solves Fragmentation)

Albums often get split if "Album Artist" varies slightly or if years differ.

### Tag: `TXXX:GOSLING_ALBUM_UUID`
Unique ID for the album entity.

**Benefit:** Even if one track says "Greatest Hits" (1990) and another says "Greatest Hits (Remastered)" (2011), if they share the UUID, they are forced into the same Album bucket.

---

## 4. Relationship Anchors (Solves Remixes/Versions)

Persist the parent/child links between files.

### Tag: `TXXX:GOSLING_PARENT_UUID`
The UUID of the "Parent" song (e.g., the Main Mix).

### Tag: `TXXX:GOSLING_RELATION_TYPE`
The type of link (e.g., `Version`, `Remix`, `Instrumental`).

**Example (Instrumental Track):**
- **File:** `Song A (Instrumental).mp3`
- **GOSLING_PARENT_UUID:** `[UUID-OF-MAIN-VOCAL-MIX]`
- **GOSLING_RELATION_TYPE:** `Version`

**Recovery Flow:**
WARNING: This requires the Parent file to also be present and have its UUID assigned.
1. Import all songs.
2. Second Pass: "Stitch" relationships based on UUID matches.

---

## Implementation Strategy (Task T-107)

### Phase 1: UUID Generation
- Add `GlobalUUID` column to `Identities`, `MediaSources`, and `Albums` tables.
- Populate existing rows with random UUIDs.

### Phase 2: Write Support (Yellberus)
- Update `Yellberus` to write these `TXXX` tags during `save_metadata`.
- Needs a new "System Tags" section in the write logic that is always active (not user-configurable).

### Phase 3: Read/Recover Support (Scanner)
- Update `LibraryScanner` to look for these tags.
- "Hydration Mode": If `GOSLING_*` tags are found, favor them over raw text matching.

## 5. Import Strategy (Safety First)

User Concern: "Auto-merging based on UUIDs might cause unwanted data loss. Prompts for 1000 files are annoying."

**Proposed Loading Logic:**
1.  **Strict Match (Safe):** If `TPE1` (Display Name) matches the DB Name **AND** the UUID matches the DB Identity -> **Auto-Link**.
2.  **Name Mismatch (Risk):** If `TPE1` is different from the DB record for that UUID (e.g. file says "New Alias", DB says "Old Name") -> **Flag for Review**.
3.  **New UUID (Safe):** If UUID is unknown to DB -> **Create New Identity** (Implicit trust).

**Configuration:**
- `[x] Trust Portable Identity Tags` (Default: True)
    - If disabled, imports as plain text strings (ignoring relationships).
- **"Pending Links" Review:** Instead of interrupting the import with popups, add uncertain items to a "Inbox/Review" queue (like the Pending Changes tab) for bulk approval.

---

## Future Proofing
This effectively turns your file system into a distributed database. You could drag a file to a friend's Gosling installation, and (assuming they use UUID resolution) it would carry its "Soul" (Identity connections) with it.
