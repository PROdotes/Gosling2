# Refactor: Pass Song Objects, Not IDs

## Problem

A single "remove artist from song" triggers **10 full hydrations** (200+ log lines). Every layer fetches the same song from scratch because every function takes a `song_id: int` and defensively calls `get_song()` internally.

## Current Flow (broken)

```
Router: get_song(id)        ← validate existence
  EditService: get_song(id) ← _sync_physical_state
    MetadataWriter: get_song(id) ← write tags
      move_song: get_song(id) ← rename file
  EditService: get_song(id) ← return value
Router: get_song(id)        ← frontend re-GETs
Router: get_song(id)        ← frontend re-GETs again
```

Each `get_song()` = 7 DB queries + `evaluate_routing()` file path calculation.

## Target Flow

```
Router: get_song(id)        ← ONE hydration, pass object down
  EditService: DB delete    ← no fetch, just SQL
  EditService: hydrate once ← re-hydrate post-mutation for ID3 + routing
  MetadataWriter: write_metadata(song) ← use the object we already have
  EditService: move if needed           ← same object
  return that object to frontend       ← no re-GET
```

**Minimum viable: 2 hydrations** (one pre-mutation for validation, one post-mutation for the new state). The frontend uses the DELETE response instead of re-fetching.

## Scope

### EditService — 16 methods change signature

Every method that takes `song_id: int` and calls `self._library_service.get_song()` inside:

| Method | get_song() calls | Change |
|--------|-----------------|--------|
| `update_song_scalars` | 3 | Take `Song`, return mutated `Song` |
| `add_song_credit` | 2 | Take `Song`, return mutated `Song` |
| `remove_song_credit` | 2 | Take `Song`, return mutated `Song` |
| `add_song_album` | 2 | Take `Song`, return mutated `Song` |
| `create_and_link_album` | 2 | Take `Song`, return mutated `Song` |
| `remove_song_album` | 2 | Take `Song`, return mutated `Song` |
| `update_song_album_link` | 2 | Take `Song`, return mutated `Song` |
| `add_song_tag` | 2 | Take `Song`, return mutated `Song` |
| `remove_song_tag` | 1 | Take `Song`, return mutated `Song` |
| `set_primary_song_tag` | 2 | Take `Song`, return mutated `Song` |
| `add_song_publisher` | 2 | Take `Song`, return mutated `Song` |
| `remove_song_publisher` | 2 | Take `Song`, return mutated `Song` |
| `import_credits_bulk` | 1 | Take `Song`, return mutated `Song` |
| `delete_song` | 0 (uses repo directly) | Take `Song` |
| `move_song_to_library` | 3 | Take `Song`, return mutated `Song` |
| `delete_original_source` | 0 | Take `Song` |

### `_sync_physical_state` — the hub

Currently takes `song_id`, fetches internally. Must accept a `Song` object instead. This is called by all 16 methods above.

Also called by 7 **batch methods** that resolve song_ids from album/tag/publisher changes:
- `update_album`, `add/remove_album_credit`, `add/remove_album_publisher`
- `update_tag`, `update_publisher`

These would batch-fetch songs first, then pass objects.

### CatalogService — 21 methods (pass-through layer)

Thin facade. Every method just changes its `song_id: int` param to `song: Song`.

### Routers — 22 endpoints

- `_require_song(song_id)` becomes the single hydration point, returns the `Song`
- Every endpoint passes that `Song` object into the service layer
- DELETE/POST/PATCH endpoints return the mutated `Song` directly — frontend stops re-GETting

### Unaffected (read-only endpoints)

- `GET /songs/{song_id}` (catalog.py)
- `GET /songs/{song_id}/web-search` (catalog.py)
- `GET /inspect-file/{song_id}` (metabolic.py)
- `GET /songs/{song_id}/audio` (audio.py)

These already do one fetch and return. No change needed.

## Open Questions

1. **Pre-mutation validation** — do we still hydrate before the DB write (to check "does this credit exist on this song?"), or just let the DB reject it? Letting the DB reject means fewer hydrations but different error handling.

2. **Batch methods** (`tools.py /filename-parser/apply`) — iterates multiple song_ids. Hydrate per-item or batch-hydrate upfront?

3. **Album/tag/publisher edits** — these affect multiple songs. The 7 batch methods in EditService resolve song_ids from the entity. Do we batch-hydrate all affected songs once, then sync each?

4. **Frontend contract** — currently the frontend re-GETs after every mutation. We need the frontend to trust the response from the mutation endpoint instead.

## Suggested Implementation Order

1. Change `_sync_physical_state(song_id)` → `_sync_physical_state(song: Song)` — biggest single win
2. Change `remove_song_credit` as the pilot refactor (the case we just traced)
3. Roll the pattern out to the other 15 EditService methods
4. Update CatalogService signatures (mechanical pass-through changes)
5. Update router endpoints to hydrate once and pass down
6. Frontend: stop re-GETting after mutations, use the response body
