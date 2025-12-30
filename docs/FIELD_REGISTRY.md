# Field Registry (Yellberus Specification)

> **Source of Truth**: `src/core/yellberus.py`  
> **Purpose**: Document all data fields managed by the system, their properties, and ID3 mappings.

---

## 📋 Current Fields

| Name | UI Header | DB Column | Type | Strategy | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag | Validation |
|------|-----------|-----------|------|----------|---------|----------|------------|------------|----------|----------|---------|------------|
| `performers` | Performers | Performers | LIST | First Letter | Yes | Yes | No | No | No | Yes | TPE1 |
| `groups` | Groups | S.Groups | TEXT |  | No | Yes | No | No | No | Yes | TIT1 |
| `unified_artist` | Artist | UnifiedArtist | TEXT | First Letter | Yes | No | Yes | Yes | No | No | — |
| `title` | Title | MS.Name | TEXT |  | Yes | Yes | No | Yes | Yes | Yes | TIT2 |
| `album` | Album | AlbumTitle | TEXT | First Letter | Yes | Yes | Yes | Yes | Yes | Yes | TALB |
| `composers` | Composer | Composers | LIST | First Letter | Yes | Yes | Yes | Yes | Yes | Yes | TCOM |
| `publisher` | Publisher | Publisher | TEXT | First Letter | Yes | Yes | Yes | Yes | Yes | Yes | TPUB |
| `recording_year` | Year | S.RecordingYear | INTEGER | Decade Grouping | Yes | Yes | Yes | Yes | Yes | Yes | TDRC |
| `genre` | Genre | Genre | TEXT | Decade Grouping | Yes | Yes | Yes | Yes | Yes | Yes | TCON |
| `isrc` | ISRC | S.ISRC | TEXT |  | Yes | Yes | No | No | No | Yes | TSRC |
| `duration` | Duration | MS.Duration | DURATION |  | Yes | No | No | No | Yes | No | TLEN |
| `producers` | Producer | Producers | LIST | First Letter | Yes | Yes | Yes | Yes | No | Yes | TIPL |
| `lyricists` | Lyricist | Lyricists | LIST | First Letter | Yes | Yes | Yes | Yes | No | No | TOLY |
| `album_artist` | Album Artist | AlbumArtist | TEXT | First Letter | No | Yes | No | Yes | No | Yes | TPE2 |
| `notes` | Notes | MS.Notes | TEXT |  | Yes | Yes | No | No | No | No | — |
| `is_done` | Status | S.IsDone | BOOLEAN | Boolean Toggle | Yes | Yes | Yes | No | No | No | — |
| `path` | Path | MS.Source | TEXT | Decade Grouping | No | No | No | No | Yes | No | — |
| `file_id` | ID | MS.SourceID | INTEGER |  | No | No | No | No | Yes | No | — |
| `type_id` | Type | MS.TypeID | INTEGER |  | No | No | No | No | No | No | — |
| `bpm` | BPM | S.TempoBPM | INTEGER | Range Filter | Yes | Yes | Yes | No | No | Yes | TBPM |
| `is_active` | Active | MS.IsActive | BOOLEAN | First Letter | Yes | Yes | Yes | No | No | No | — |
| `audio_hash` | Audio Hash | MS.AudioHash | TEXT |  | No | No | No | No | No | No | — |

**Total: 22 fields**

---

## 🆕 Planned Additions (T-06: Legacy Sync)

| Name | UI Header | DB Column | Type | Visible | Filterable | Portable | ID3 Tag | Notes |
|------|-----------|-----------|------|---------|------------|----------|---------|-------|
| `album` | Album | S.Album | TEXT | Yes | Yes | Yes | TALB | Used in legacy for grouping. |
| `publisher` | Publisher | S.Publisher | TEXT | No | Yes | Yes | TPUB | Record label / Publishing house. |
| `genre` | Genre | S.Genre | TEXT | Yes | Yes | Yes | TCON | **Critical**: Used for folder routing. |

---

## 📖 Field Property Definitions

| Property | Meaning |
| :--- | :--- |
| **Name** | Internal field identifier (used in code). |
| **UI Header** | Label shown in the column header and metadata editors. |
| **DB Column** | SQL expression (Column name or joined field). |
| **Type** | Data type of the field (`string`, `integer`, `boolean`, `list`). |
| **Visible** | **Hard Constraint**: Shown in table by default; hidden fields are banned from UI toggle menus and resets. |
| **Editable** | Determines if the field can be modified by the user in editors. |
| **Filterable** | Can be used as a branch in the side-panel Filter Tree. |
| **Searchable** | Field is included in global search box queries. |
| **Required** | Must have a value for the song to be marked as "Done". |
| **Portable** | Written back to MP3 ID3 tags during export. |

---

## 🛠️ Implementation Notes

1. **Yellberus is the source of truth.** If a field is not in `FIELDS`, it doesn't exist to the system.
2. **ID3 Mappings** are defined in `src/resources/id3_frames.json`.
3. **Database Columns** must align with `schema.sql` (see `DATABASE.md`).
4. **Adding a new field requires updates to:**
   - `src/core/yellberus.py` (FieldDef)
   - `src/resources/id3_frames.json` (if portable)
   - Database schema (migration or DDL)
   - `MetadataService` (read/write logic)

5. **Advanced Logic (Manual)**:
   - The `query_expression` (SQL) property is currently managed manually in `src/core/yellberus.py`.
   - **Safety**: The Field Editor preserves this value but cannot display or edit it.
   - Model (`Song.py` or `MediaSource.py`)
