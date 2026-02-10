# Album Chip Field — Bug Report

The album chip field has multiple issues causing unexpected behavior:

1. **Multi-select never shows "Mixed"** — the special-case album handler returns without checking `mixed_count`
2. **Staged changes are ignored** — it fetches directly from DB instead of using staged values
3. **Comma splitting when typing** — if you type "Album, Feat. X", it splits into two albums
4. **No ordering guarantee** — albums appear in arbitrary DB order, primary status is random

**Root cause:** The album field has a hardcoded bypass in `_get_latest_chips()` that prevents it from flowing through the standard pipeline like every other chip field.

**Key locations:**
- `src/presentation/widgets/side_panel_widget.py`, lines 1736-1744 (special-case album handler)
- `src/core/yellberus.py`, line 850 (comma-splitting in `cast_from_string()`)
- `src/data/repositories/album_repository.py`, lines 377-392 (no ORDER BY in query)

---

## 1. Multi-select never shows "Mixed"

**What happens:** When multiple songs are selected with different albums, the album chip tray just shows the first song's albums. No "X Mixed" chip appears.

**Why:** The album branch fetches from DB using only `self.current_songs[0]` and returns early, never checking the `mixed_count` variable that `_calculate_bulk_value()` already computed on line 1726.

**Compare:** Tags (line 1731) and all other fields (line 1805) both append `(-1, f"{mixed_count} Mixed", "🔀", ...)` when `mixed_count > 0`.

---

## 2. Staged changes are ignored

**What happens:** If a user edits the album field, the staged value is never consulted — the chip tray always shows the raw DB state.

**Why:** The album branch calls `self.album_service.get_albums_for_song()` directly instead of using `effective_val` from `_calculate_bulk_value()`, which runs through `_get_effective_value()` (the staging-aware lookup).

---

## 3. **REAL BUG**: Comma splitting when reading from ID3 tags

**What happens:** An MP3 with ID3 tag `TALB="Album [Something, Something, Something]"` gets read by MetadataService, which stores it as a string (line 75 of metadata_service.py). When saved, `yellberus.cast_from_string()` splits on commas, creating THREE separate albums instead of one.

**The flow:**
1. ID3 tag read → `song.album = "Album [Something, Something, Something]"` (string)
2. Song saved → `cast_from_string(FieldDef.LIST, song.album)` called
3. Line 850 of yellberus.py: `return [v.strip() for v in s_val.split(',') if v.strip()]`
4. Result: `["Album [Something", "Something", "Something]"]` ❌

**Root cause:** `yellberus.cast_from_string()` (line 850) splits ALL LIST-type field values on commas:

```python
if field_def.field_type == FieldType.LIST:
    return [v.strip() for v in s_val.split(',') if v.strip()]
```

**Why this is wrong for albums specifically:**
- **Performers/Composers:** Comma-splitting is correct (they come from ID3 as `;` or `/` separated, converted to `,` by ID3Registry)
- **Album:** Comma-splitting is WRONG (album titles can legitimately contain commas; the DB uses `|||` as delimiter)
- **Tags, Publisher:** Also use `|||` as delimiter

**The fix:** Album field should split on `|||` only, not commas. Other fields should keep comma-splitting (or better yet, use a field-specific delimiter strategy in `cast_from_string()`).

---

## 4. No ordering guarantee from DB

**What happens:** Album chips appear in arbitrary database order. The first result is treated as "primary" (`i==0`) regardless of actual primary status.

**Why:** `album_repository.get_albums_for_song()` (line 377-392) has no `ORDER BY` clause.

**Note:** The yellberus query expression *does* have `ORDER BY SA_SUB.IsPrimary DESC`, but the album branch never uses that query — it goes through the repository method instead.

---

## Fix Strategy

There are THREE separate fixes needed:

### Fix 1: Remove hardcoded album bypass in `_get_latest_chips()` (Fixes issues #1 and #2)

**Delete lines 1736-1744** in `src/presentation/widgets/side_panel_widget.py` — remove the special-case album handler. Let album flow through the same code path as tags, publisher, performers, etc. via EntityListWidget.

This restores:
- Multi-select "X Mixed" indicator (issue #1)
- Staged value recognition (issue #2)
- Consistent ordering from standard pipeline

### Fix 2: Fix comma-splitting for album in `cast_from_string()` (Fixes issue #3)

**File:** `src/core/yellberus.py`, line 849-850

**Current code:**
```python
if field_def.field_type == FieldType.LIST:
    return [v.strip() for v in s_val.split(',') if v.strip()]
```

**Should be:**
```python
if field_def.field_type == FieldType.LIST:
    # Album uses ||| delimiter (matches DB GROUP_CONCAT)
    # Other LIST fields use comma (ID3 standard)
    if field_def.name == 'album':
        delimiter = r'\|\|\|'
    else:
        delimiter = ','
    import re
    return [v.strip() for v in re.split(delimiter, s_val) if v.strip()]
```

This prevents album names with commas from being split while keeping comma-splitting for performers, composers, etc.

### Fix 3: Add ORDER BY to album repository query (Ensures consistent ordering)

**File:** `src/data/repositories/album_repository.py`, lines 377-392

Add `ORDER BY sa.IsPrimary DESC, a.AlbumTitle ASC` to the query to ensure consistent, predictable album ordering.
