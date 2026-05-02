# MutationCoordinator: Seam Architecture

**Date:** 2026-05-02
**Status:** Reference document for implementation
**Supersedes:** Previous seams doc (discriminated union edition, 2026-04-30)

---

## Purpose

The MutationCoordinator is the single gateway for all database write operations. Every write in the app goes through it — nothing else opens a connection to write. It owns the connection, transaction, batch_id, audit, ID3 sync, and filing side effects. Upstream callers (Spotify parser, filename parser, splitter, UI) resolve their raw input into clean add/update/remove items before handing off. The coordinator never parses, never reads files, never knows where data came from.

---

## Routing

One HTTP endpoint, one flat request shape:

```python
@router.post("/mutate")
def mutate(body: MutationRequest):
    return coordinator.apply(body)
```

No discriminated union. No per-operation command types. The `type` field on each item is sufficient for the coordinator to fan out.

---

## Request Shape

```json
{
  "add": [
    { "type": "credit",    "song_id": 1, "name": "Freddie Mercury", "id": 1,   "role": "Performer" },
    { "type": "tag",       "song_id": 1, "name": "Rock",            "id": 5,   "category": "Genre", "make_primary": false },
    { "type": "publisher", "song_id": 1, "name": "EMI",             "id": null },
    { "type": "album",     "song_id": 1, "name": "A Night at the Opera", "id": 3, "track_number": 1, "disc_number": 1, "make_primary": false }
  ],
  "update": [
    { "type": "song",      "id": 1, "media_name": "Bohemian Rhapsody", "bpm": 120 },
    { "type": "tag",       "id": 5, "name": "Rock", "category": "Genre" },
    { "type": "song_tag",  "song_id": 1, "tag_id": 5, "is_primary": true },
    { "type": "song_album","song_id": 1, "album_id": 3, "track_number": 5, "disc_number": 1 },
    { "type": "album",     "id": 3, "title": "A Night at the Opera", "album_type": "LP", "release_year": 1975 },
    { "type": "credit",    "id": 1, "display_name": "F. Mercury" },
    { "type": "publisher", "id": 9, "name": "EMI", "parent_id": 12 }
  ],
  "remove": [
    { "type": "credit",    "song_id": 1, "id": 42 },
    { "type": "tag",       "song_id": 1, "id": 7 }
  ]
}
```

All three buckets are optional. An empty request (all buckets absent or empty) → 422.

Pydantic validates field values (year range, ISRC format, non-empty names) at the FastAPI boundary before any DB connection opens. Invalid → 422, no DB touched.

---

## Coordinator flow

Groups items by `type`, opens one connection, one transaction, one batch_id, fans out to per-entity mutators, commits, then fires side effects.

```python
def apply(self, body: MutationRequest):
    conn = self._get_connection()
    batch_id = uuid4()
    try:
        touched_songs = set()

        for item in (body.remove or []):
            self._route(item, "remove", conn, batch_id)
            if "song_id" in item:
                touched_songs.add(item["song_id"])

        for item in (body.add or []):
            self._route(item, "add", conn, batch_id)
            if "song_id" in item:
                touched_songs.add(item["song_id"])

        for item in (body.update or []):
            self._route(item, "update", conn, batch_id)
            if item["type"] == "song" or "song_id" in item:
                touched_songs.add(item.get("song_id") or item["id"])

        pre_post = {
            song_id: (self._library.get_song(song_id, conn), None)
            for song_id in touched_songs
        }
        # TODO: audit.log_update(pre, post, conn, batch_id)

        conn.commit()

        results = []
        for song_id in touched_songs:
            post = self._library.get_song(song_id, conn)
            results.append(post)
            try:
                self._id3_writer.write_metadata(post)
            except Exception:
                logger.error("ID3 write failed for song %s", post.id)
            try:
                self._filing.move_if_needed(post)
            except Exception:
                logger.error("File move failed for song %s", post.id)

        return results

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

`_route(item, action, conn, batch_id)` dispatches on `item["type"]` to the right mutator.

---

## Mutator Interface

Each mutator implements `apply_within(action, item, conn, batch_id)`. Does NOT open connections, does NOT commit. Internal logic (get-or-create, validation, auto-promote) stays inside the mutator.

```python
class SongMutator:
    def apply_within(self, action, item, conn, batch_id) -> None: ...    # action: "update"

class CreditMutator:
    def apply_within(self, action, item, conn, batch_id) -> None: ...    # actions: "add", "remove", "update"

class TagMutator:
    def apply_within(self, action, item, conn, batch_id) -> None: ...    # actions: "add", "remove", "update"
                                                                          # update handles both entity rename and is_primary on song_tag

class PublisherMutator:
    def apply_within(self, action, item, conn, batch_id) -> None: ...    # actions: "add", "remove", "update"

class AlbumMutator:
    def apply_within(self, action, item, conn, batch_id) -> None: ...    # actions: "add", "remove", "update"
                                                                          # update handles entity fields, song_album join row (track/disc), and is_primary
```

The `type` field distinguishes entity-level updates from join-row updates inside the same mutator:
- `TagMutator` receives both `type: "tag"` (rename) and `type: "song_tag"` (is_primary, song_id scoped)
- `AlbumMutator` receives both `type: "album"` (entity fields) and `type: "song_album"` (track_number, disc_number, is_primary)

---

## Add semantics

- `id: null` → get-or-create by name.
- `id: <int>` → use directly, skip lookup.
- Credit link identity is `(song_id, credit_id, role_id)`. Same person as Performer and Producer = two rows. Role changes are remove + add.
- Adding an already-linked target → **skip silently** (per-song). Bulk ergonomics: adding a credit to 20 songs where 5 already have it should not require pre-filtering.

---

## Remove semantics

- Removing a non-existent link → hard error (`LookupError` → 404), full transaction rollback. Asymmetric with add on purpose — a missing remove is a stale-UI / concurrent-edit signal.
- Removing the currently-primary tag or album → allowed. Auto-promote the next remaining link of the same category. If none remains, song ends up with no primary in that category.
- Remove only deletes the join row. The underlying entity (Credit, Tag, Publisher, Album) is never touched, even if it ends up with zero links anywhere. Orphan cleanup is a separate explicit operation, never a side effect of unlink.

---

## Update semantics

- Absent key → leave field alone (Pydantic `exclude_unset`).
- Explicit `null` → clear the field.
- Empty string → 422. Use `null` to clear.
- Writes pass through to DB unconditionally. Audit is diff-based: no-change → no audit row. Case changes count (`Bob` → `bob` is a real diff).
- `set_primary_*`: `is_primary: true` on a `song_tag` or `song_album` update item referencing an id not currently linked → 404 hard error. Use add with `make_primary: true` to add + promote in one call.
- `song_album` update for an album not currently linked to the song → 404 hard error. No upsert.

---

## Auto-promote (TagMutator and AlbumMutator)

On add: if the song has no existing primary in this category, the new link is promoted automatically regardless of `make_primary`. If `make_primary: true` is explicit, promote unconditionally (and demote any existing primary).

---

## Side effects

Fire after `conn.commit()`. Non-fatal — exceptions are caught, logged, and reported in the response. Only apply when songs were touched.

- `MetadataWriter.write_metadata(post)` — ID3 tags
- `FilingService.move_if_needed(post)` — moves file if `post.desired_state_synced` is False and `AUTO_MOVE_ON_APPROVE` is enabled. Does not exist yet — add when implementing coordinator.

ID3 / filing failure leaves DB authoritative; file drifts. Existing UI elements surface this; user reconciles via bulk sync (planned).

Warnings reported in response body:

```json
{
  "songs": [ ... ],
  "warnings": [
    { "song_id": 42, "kind": "id3_write", "error": "..." },
    { "song_id": 42, "kind": "file_move", "error": "..." }
  ]
}
```

Status remains 200.

---

## Return shape

- Touched songs → `list[Song]` (post-state, one per touched song_id)
- Entity-only updates (no song_id involved, e.g. renaming a tag) → the updated entity object
- If both songs and entities are touched in one request → `{ "songs": [...], "entities": [...] }`

Entity updates have unbounded fan-out (a credit on 500 songs); the API does not return all affected views. View consistency is a frontend concern.

---

## SongMutator + MediaMutator split

`Songs` and `MediaSources` are two tables. `SongRepository.update_scalars()` currently writes to both via an internal split. A separate **MediaMutator** is planned for when non-Song media types land (streams, commercials, jingles) — they'll need to mutate Media rows without going through Song.

**TBD:** field-level boundary (which scalars belong to MediaMutator vs SongMutator) and how the coordinator routes a `type: "song"` update whose fields straddle both tables. Design before implementation.

---

## Error mapping (router's job)

| Exception | HTTP |
|---|---|
| `LookupError` (missing entity, missing link to remove) | 404 |
| `ValueError` (constraint violation, conflicting primary) | 400 |
| Pydantic validation error | 422 (FastAPI default) |
| Other | 500 |

---

## LibraryService.get_song conn threading

`get_song` gains an optional `conn` parameter. When provided, skip `get_connection()` and do NOT use a `with` block — sqlite3's context manager commits/rolls back on exit, which would break the coordinator's transaction. Call repo methods directly with the provided conn.

---

## File structure

```
src/services/
  mutation_coordinator.py
  mutators/
    media_mutator.py
    song_mutator.py
    credit_mutator.py
    tag_mutator.py
    publisher_mutator.py
    album_mutator.py
```

---

## What does NOT change

- All read endpoints — untouched.
- `IngestionService` — its own transaction pattern.
- `EditService` — only the methods that mutators actually call gain a required `conn` param and lose internal `get_song()` / `_sync_id3_if_enabled` calls. The other methods stay as-is until a separate cleanup pass.
- `LibraryService.get_song` — gains optional `conn` param (see threading note above).

---

## Staging (rollout, not architecture)

1. Frontend posts to stub `POST /mutate` — already done.
2. Old per-operation endpoints deleted so nothing accidentally calls them.
3. MutationCoordinator + Pydantic request model land behind the stub.
4. Mutators land one by one, each behind feature-gating in the coordinator dispatch.
5. Audit hookup once `AuditRepository.log_action` exists.

---

## Deferred

- Audit seam specifics: pre/post computation for entity-only updates, slice contents for audit row.
- Authn/authz — single-tenant local app, presumably no-op, undocumented.
- Multi-song bulk return shape — defer until multi-select UI exists.
- MediaMutator field boundary — design before implementation.
