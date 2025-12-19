# Field Registry (Yellberus Specification)

> **Source of Truth**: `src/core/yellberus.py`  
> **Purpose**: Document all data fields managed by the system, their properties, and ID3 mappings.

---

## 📋 Current Fields

| Name | UI Header | DB Column | Type | Visible | Filterable | Searchable | Required | Portable | ID3 Tag |
|------|-----------|-----------|------|---------|------------|------------|----------|----------|---------|
| `source_id` | ID | MS.MediaSourceID | INTEGER | No | No | No | No | No | — |
| `name` | Title | MS.Name | TEXT | Yes | No | Yes | Yes | Yes | TIT2 |
| `performers` | Performer | Performers | LIST | Yes | Yes | Yes | Yes | Yes | TPE1 |
| `composers` | Composer | Composers | LIST | Yes | Yes | Yes | Yes | Yes | TCOM |
| `lyricists` | Lyricist | Lyricists | LIST | No | Yes | No | No | Yes | TEXT/TOLY |
| `producers` | Producer | Producers | LIST | No | Yes | No | No | Yes | TIPL/TXXX |
| `groups` | Groups | S.Groups | LIST | No | Yes | No | No | Yes | TIT1 |
| `duration` | Duration | MS.Duration | DURATION | Yes | No | No | Yes | No | — |
| `path` | Path | MS.Source | TEXT | No | No | No | Yes | No | — |
| `recording_year` | Year | S.RecordingYear | INTEGER | Yes | Yes | No | Yes | Yes | TDRC/TYER |
| `bpm` | BPM | S.TempoBPM | INTEGER | Yes | Yes | No | No | Yes | TBPM |
| `is_done` | Status | S.IsDone | BOOLEAN | Yes | Yes | No | No | No | TKEY |
| `isrc` | ISRC | S.ISRC | TEXT | No | No | No | No | Yes | TSRC |
| `notes` | Notes | MS.Notes | TEXT | No | No | No | No | No | — |
| `is_active` | Active | MS.IsActive | BOOLEAN | No | No | No | No | No | — |

**Total: 15 fields**

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
|----------|---------|
| **Visible** | Shown in the Library table by default. |
| **Filterable** | Can be used in the Filter Tree sidebar. |
| **Searchable** | Included in the global search box query. |
| **Required** | Must have a value for "Done" status. |
| **Portable** | Written to ID3 tags (travels with the file). |

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
   - Model (`Song.py` or `MediaSource.py`)
