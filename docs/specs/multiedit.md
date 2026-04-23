# Multi-Edit Spec

## Scope

Songs only (v1). Triggered when 2+ songs are selected in the song list.

---

## Read: Collapsed View

**New endpoint**: `POST /api/v1/songs/multi-view`  
**Body**: `{ "song_ids": [1, 2, 3] }`

The service fetches all songs via `SongRepository.get_by_ids`, hydrates each, then collapses into a `MultiSongView`. All collapsing logic lives in the service layer — no logic in the frontend.

### Scalar fields

Each editable scalar (`media_name`, `bpm`, `year`, `isrc`, `notes`) is represented as:

```json
{ "value": 2025, "mixed": false }
{ "value": null, "mixed": true }
```

- All songs agree → `value` = that value, `mixed: false`
- Any disagreement → `value: null`, `mixed: true`

### M2M fields (credits, tags, publishers, albums)

Union of all entries across selected songs. Each entry is tagged:

- `universal: true` — present on **all** selected songs
- `universal: false` — present on **some** but not all (partial)

A credit entry is identified by `(name_id, role_name)` — Artist B as Performer and Artist B as Composer are two separate entries.

```json
"credits": [
  { "name_id": 2, "display_name": "Artist B", "role": "Performer", "universal": true },
  { "name_id": 1, "display_name": "Artist A", "role": "Performer", "universal": false },
  { "name_id": 3, "display_name": "Artist C", "role": "Performer", "universal": false }
]
```

The frontend uses `universal` only for display state — no logic.

---

## UX: Display Rules

- **Scalar, agreed**: show the value normally
- **Scalar, mixed**: show blank input with ghost text `Mixed values`; if the user doesn't touch it, it is not included in the save payload
- **M2M, universal**: show entry normally
- **M2M, partial**: show entry with a visual indicator (e.g. dimmed, striped) — it exists on some songs but not all

---

## Write: Scalars

**New endpoint**: `PATCH /api/v1/songs/bulk-scalars`  
**Body**: `{ "song_ids": [1, 2, 3], "fields": { "bpm": 120 } }`

- Only fields the user explicitly changed are included — same `exclude_none` contract as single-song edit
- Service loops through `song_ids` and calls existing `EditService.update_song_scalars` per song
- **Full rollback** if any song fails — all-or-nothing (required for future audit UUID)
- All editable scalar fields are in scope: `media_name`, `bpm`, `year`, `isrc`, `notes`
- No exclusions — bulk-setting title or ISRC is the user's responsibility

---

## Write: M2M (credits, tags, publishers, albums)

Reuse existing single-song endpoints. The server applies the delta to each song individually.

**New endpoints** (bulk wrappers):

Each credit entry in the collapsed view is identified by `(name_id, role_name)` — the unique natural key across the `SongCredits` table. The service resolves the per-song `CreditID` internally.

| Action | Endpoint |
|---|---|
| Add credit | `POST /api/v1/songs/bulk/credits` |
| Remove credit | `DELETE /api/v1/songs/bulk/credits` body: `{ song_ids, name_id, role_name }` |
| Add tag | `POST /api/v1/songs/bulk/tags` |
| Remove tag | `DELETE /api/v1/songs/bulk/tags/{tag_id}` |
| Add publisher | `POST /api/v1/songs/bulk/publishers` |
| Remove publisher | `DELETE /api/v1/songs/bulk/publishers/{publisher_id}` |
| Add album | `POST /api/v1/songs/bulk/albums` |
| Remove album | `DELETE /api/v1/songs/bulk/albums/{album_id}` |

All bulk M2M bodies include `song_ids: List[int]` plus the same fields as the single-song equivalent. Album links added via multi-edit default to `track_number=0, disc_number=0`.

### Delta logic for M2M (server-side, in service layer)

When adding an entry:
- Songs that already have it → skip (idempotent)
- Songs that don't → add it

When removing an entry:
- Songs that have it → remove it
- Songs that don't → skip (no-op)

**Full rollback** on any failure — all-or-nothing.

---

## New Files

| File | Purpose |
|---|---|
| `src/models/multi_edit_models.py` | `MultiSongView`, `ScalarField`, `MultiCreditEntry`, etc. |
| `src/engine/routers/multi_edit.py` | New router for all multi-edit endpoints |
| `src/services/multi_edit_service.py` | Collapsing logic (read) and bulk apply logic (write) |
