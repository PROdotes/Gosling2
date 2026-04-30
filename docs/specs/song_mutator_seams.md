# MutationCoordinator: Seam Architecture

**Date:** 2026-04-30  
**Status:** Reference document for implementation  
**Supersedes:** Previous seams doc (Coordinator pattern, helltide edition)

---

## Command Shape

Same shape as original spec. JSON in, Song out.

```json
{
  "song_ids": [1],
  "scalars": { "media_name": "Bohemian Rhapsody", "bpm": 120 },
  "add_links": [
    { "type": "credit", "name": "Freddie Mercury", "id": 1, "role": "Performer" },
    { "type": "tag", "name": "Rock", "id": 5, "category": "Genre" },
    { "type": "publisher", "name": "EMI", "id": null },
    { "type": "album", "id": 3, "name": "A Night at the Opera", "track_number": 1, "disc_number": 1 }
  ],
  "remove_links": [
    { "type": "credit", "id": 42 },
    { "type": "tag", "id": 7 }
  ],
  "set_primary_tag_id": 5
}
```

Pydantic validates the shape before any connection opens. Invalid shape → 400, no DB touched.

---

## The Coordinator

`MutationCoordinator` owns the connection, transaction, and `batch_id`. It decomposes the incoming command by entity type and fans out to the right mutator. Each mutator receives a command slice — a small JSON-shaped dict with an `action` field.

```python
def apply(self, command: SongMutationCommand) -> Song:
    conn = self._get_connection()
    batch_id = uuid4()
    try:
        results = []
        for song_id in command.song_ids:
            pre = self._library.get_song(song_id, conn)
            if not pre:
                raise LookupError(f"Song {song_id} not found")

            if command.scalars:
                self._song_mutator.apply_within(
                    {"action": "edit", "song_id": song_id, "fields": command.scalars},
                    conn, batch_id
                )

            for link in (command.remove_links or []):
                self._route_link(link | {"action": "remove", "song_id": song_id}, conn, batch_id)

            for link in (command.add_links or []):
                self._route_link(link | {"action": "add", "song_id": song_id}, conn, batch_id)

            if command.set_primary_tag_id:
                self._tag_mutator.apply_within(
                    {"action": "set_primary", "song_id": song_id, "tag_id": command.set_primary_tag_id},
                    conn, batch_id
                )

            post = self._library.get_song(song_id, conn)
            # TODO: audit.log_update(pre, post, conn, batch_id)
            results.append((pre, post))

        conn.commit()

        for pre, post in results:
            try:
                self._id3_writer.write_metadata(post)
            except Exception:
                logger.error("ID3 write failed for song %s", post.id)
            try:
                self._filing.move_if_needed(pre, post)
            except Exception:
                logger.error("File move failed for song %s", post.id)

        return results[-1][1]

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

`_route_link` dispatches on `link["type"]` → correct mutator.

---

## Command Slices

Each mutator receives a flat dict with `action` + entity-specific fields. This is the seam — mutators are testable in isolation by feeding slices directly.

**SongMutator:**
```json
{ "action": "edit", "song_id": 1, "fields": { "media_name": "...", "bpm": 120 } }
```

**CreditMutator:**
```json
{ "action": "add", "song_id": 1, "name": "Freddie Mercury", "id": 1, "role": "Performer" }
{ "action": "remove", "song_id": 1, "id": 42 }
```

**TagMutator:**
```json
{ "action": "add", "song_id": 1, "name": "Rock", "id": 5, "category": "Genre" }
{ "action": "remove", "song_id": 1, "id": 7 }
{ "action": "set_primary", "song_id": 1, "tag_id": 5 }
```

**PublisherMutator:**
```json
{ "action": "add", "song_id": 1, "name": "EMI", "id": null }
{ "action": "remove", "song_id": 1, "id": 9 }
```

**AlbumMutator:**
```json
{ "action": "add", "song_id": 1, "id": 3, "name": "A Night at the Opera", "track_number": 1, "disc_number": 1 }
{ "action": "remove", "song_id": 1, "id": 2 }
```

---

## Mutator Interface

Each mutator implements `apply_within(slice: dict, conn, batch_id)`. Does NOT open connections, does NOT commit.

```python
class SongMutator:
    def apply_within(self, slice: dict, conn: Connection, batch_id: UUID) -> None: ...

class CreditMutator:
    def apply_within(self, slice: dict, conn: Connection, batch_id: UUID) -> None: ...

class TagMutator:
    def apply_within(self, slice: dict, conn: Connection, batch_id: UUID) -> None: ...

class PublisherMutator:
    def apply_within(self, slice: dict, conn: Connection, batch_id: UUID) -> None: ...
```

Internal logic (get_or_create, auto-promote, validation) stays inside each mutator. Coordinator never sees it.

---

## SongMutator note

`Songs` and `MediaSources` are two tables but one logical entity. SongMutator writes to both via `SongRepository.update_scalars()` which already handles the split internally. No separate MediaMutator for now — revisit if non-Song media types (jingles, ads) are added.

---

## Non-song mutations

Alias delete, entity renames (tag, publisher), soft-delete — these don't fit the `song_ids` + links shape. They get their own command types and their own coordinator entry points, following the same pattern:

```python
coordinator.apply_delete(DeleteSongCommand(song_id=42))
coordinator.apply_alias_delete(DeleteAliasCommand(alias_id=17))
```

Each owns its own Pydantic model, routes to the right mutator, same connection/batch_id/audit lifecycle. **Not in scope for this pass** — design separately when needed.

---

## Error mapping (router's job)

| Exception | HTTP |
|---|---|
| `LookupError` | 404 |
| `ValueError` | 400 |
| Other | 500 |

---

## Side effects

Fire after `conn.commit()`. Non-fatal — exceptions are caught and logged, execution continues.

- `MetadataWriter.write_metadata(post)` — ID3 tags
- `FilingService.move_if_needed(pre, post)` — file move if routing path changed; only when `post.processing_status == REVIEWED and AUTO_MOVE_ON_APPROVE`

`FilingService.move_if_needed` does not exist yet — add when implementing coordinator.

---

## File structure

```
src/services/
  mutation_coordinator.py
  mutators/
    song_mutator.py
    credit_mutator.py
    tag_mutator.py
    publisher_mutator.py
    album_mutator.py        # future
```

---

## What does NOT change

- All read endpoints — untouched
- `IngestionService` — has its own transaction pattern
- `EditService` — methods gain required `conn` param, lose internal `get_song()` calls and `_sync_id3_if_enabled`
- `LibraryService.get_song` — gains optional `conn` param
