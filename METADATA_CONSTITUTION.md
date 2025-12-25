# METADATA CONSTITUTION 📜
**The Supreme Law of Data for Gosling2** - first draft

This document serves as the **Single Source of Truth** for how data is interpreted, stored, and displayed within the Gosling2 Music Player. If the code drifts from this text, the code is in error.

---

## I. The Canonical Field Registry
Every field in Gosling2 must be defined here. The order of this table matches the `yellberus.py` registry index used for database queries.

| # | Field Name | UI Header | ID3 Tag | Type | Source | Portable? |
|---|------------|-----------|---------|------|--------|-----------|
| 0 | performers | Performers | TPE1 | LIST | ID3 | Yes |
| 1 | groups | Groups | TIT1 | LIST | ID3 | Yes |
| 2 | unified_artist | Artist | - | TEXT | Computed | No |
| 3 | title | Title | TIT2 | TEXT | ID3 | Yes |
| 4 | album | Album | TALB | TEXT | Relational | Yes* |
| 5 | composers | Composer | TCOM | LIST | ID3 | Yes |
| 6 | publisher | Publisher | TPUB | TEXT | Relational | Yes* |
| 7 | recording_year | Year | TDRC | INT | ID3 | Yes |
| 8 | genre | Genre | TCON | TEXT | Relational | Yes* |
| 9 | isrc | ISRC | TSRC | TEXT | ID3 | Yes |
| 10| duration | Duration | TLEN | TIME | File Info | No |
| 11| producers | Producer | TIPL | LIST | ID3 (People) | Yes |
| 12| lyricists | Lyricist | TEXT | LIST | ID3 | Yes |
| 13| album_artist | Album Artist | TPE2 | TEXT | ID3 | Yes |
| 14| notes | Notes | - | TEXT | Database | No |
| 15| is_done | Status | - | BOOL | Database | No |
| 16| path | Path | - | TEXT | Local FS | No |
| 17| file_id | ID | - | INT | Database | No |
| 18| type_id | Type | - | INT | Database | No |
| 19| bpm | BPM | TBPM | INT | ID3 | Yes |
| 20| is_active | Active | - | BOOL | Database | No |

*\*Portable through the Relational Sync ritual.*

---

## II. The Rites of Extraction (Reading)
When the application reads metadata from a file, it must follow these sacred rules:

### 1. The Multi-Value Resolution
If multiple frames of the same type exist (e.g., two `TPE1` frames), they shall be merged into a single list.
- **Deduplication**: Duplicate names shall be purged, ignoring case and leading/trailing whitespace.
- **Splitting**: Values containing `/` (ID3v2.3 legacy) or `,` (Standard) shall be split into individual items if the field type is `LIST`.

### 2. The Performer & Producer Paradox
- **Performers (TPE1)**: Extracted from the `text` attribute.
- **Producers (TIPL)**: Extracted specifically from the `people` attribute of the `TIPL` frame. The role description (e.g., "producer") is discarded; only the name is kept.
- **Groups (TIT1)**: Treated as a distinct entity from Performers, though both feed into the `unified_artist` computation.

### 3. Graceful Failure
If a tag contains non-numeric data in a numeric field (e.g., `TBPM = "fast"`), the value shall be discarded and treated as `None`. The application must not crash.

---

## III. The Rites of Preservation (Writing)
When the application saves metadata back to the file, it must remain faithful to the format:

### 1. The Version Decree
All tags written by Gosling2 **MUST** be in **ID3v2.4** format with **UTF-8** encoding. 

### 2. The Snapshot Policy (Relational Data)
For relational fields like `Album`, `Genre`, and `Publisher`:
- Saving a change is a **Replacement**, not an addition.
- Existing links in the database are cleared for that specific item and replaced with the new data from the UI snapshot.

### 3. The Stationary Fields
Fields marked as `Portable: No` (e.g., `notes`, `is_done`) are **Database-Only**. They shall never be written into the ID3 tags of the file.

---

## IV. The UI Covenant
- **Invisible Fields**: Fields like `file_id`, `path`, and `is_active` are essential for the machine but shall remain hidden from the standard User Interface.
- **Unified Artist**: The UI shall prioritize the `unified_artist` field for display, which is a COALESCE of `Groups` and `Performers`.

---

## V. Governance
Any change to the `Song` model or the `id3_frames.json` registry **REQUIRES** a corresponding update to this Constitution. The **Integrity Tests** (Inquisitors) are the enforcers of this law.
