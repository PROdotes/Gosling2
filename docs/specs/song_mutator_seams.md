# MutationCoordinator: Seam Architecture

**Date:** 2026-04-30
**Status:** Reference document for implementation
**Supersedes:** Previous seams doc (Coordinator pattern, helltide edition)

---

## Routing

One HTTP endpoint, polymorphic command via Pydantic discriminated union:

```python
@router.post("/mutate")
def mutate(body: SongMutationCommand
                | RenameTagCommand
                | RenameCreditCommand
                | UpdatePublisherCommand
                | UpdateAlbumCommand):
    return coordinator.apply(body)
```

The `command_type: Literal[...]` field on each model is the discriminator. Coordinator's `apply()` dispatches on `type(body)` to the right internal entry point. Frontend has one fetch wrapper.

This is RPC, not REST — the app is single-tenant with one consumer (its own frontend), so fanning into many URLs adds no value.

---

## Command Shape: SongMutationCommand

Edits scoped to one or more songs. JSON in, `list[Song]` out (one post-state Song per id, in input order).

```json
{
  "command_type": "song_mutation",
  "song_ids": [1],
  "scalars": { "media_name": "Bohemian Rhapsody", "bpm": 120 },
  "add_links": [
    { "type": "credit", "name": "Freddie Mercury", "id": 1, "role": "Performer" },
    { "type": "tag", "name": "Rock", "id": 5, "category": "Genre", "make_primary": false },
    { "type": "publisher", "name": "EMI", "id": null },
    { "type": "album", "id": 3, "name": "A Night at the Opera", "track_number": 1, "disc_number": 1, "make_primary": false }
  ],
  "remove_links": [
    { "type": "credit", "id": 42 },
    { "type": "tag", "id": 7 }
  ],
  "update_album_links": [
    { "album_id": 3, "track_number": 5, "disc_number": 1 }
  ],
  "set_primary_tag_id": 5,
  "set_primary_album_id": 3
}
```

Pydantic validates shape AND scalar field values (year range, ISRC format, non-empty media_name) at the FastAPI boundary, before the router function body executes — no DB connection has opened. Invalid → 422, no DB touched.

### Multi-song semantics

`song_ids` is always a list. Bulk operations apply every scalar and every link to every song in the list, in one transaction, single batch_id (so one undo unit later). All-or-nothing — if song 3 of 10 raises, the whole batch rolls back.

No per-field guard for "uniquely-identifying" scalars (`media_name`, `isrc`). Caller is trusted to only send bulk-safe fields when bulk-editing. Mistakes are recoverable via undo (not yet built).

### Per-link scalars and primary toggles

Three orthogonal paths for primary tag/album:

- **Top-level `set_primary_tag_id` / `set_primary_album_id`:** promote an *already-linked* tag/album. No add involved.
- **`make_primary: true` on a tag/album add_link:** add new + promote in one call (caller doesn't need to round-trip to learn the new id).
- **Auto-promote (silent):** when song has no existing primary genre tag (or no existing primary album), an `add` of a Genre tag (or album) with `make_primary` absent/false still gets promoted.

Album track/disc number changes on an existing link use `update_album_links` (not remove+add). This is currently the only join row with editable per-link scalars; tag/credit/publisher join rows have nothing user-editable beyond what `set_primary_*` covers, so no generic `update_links` bucket exists.

### Add/remove identity rules

- `add_links` with `id: null` → get-or-create by name.
- `add_links` with `id: <int>` → use directly, skip lookup.
- `add_links` for a credit identifies a SongCredit row by `(song_id, credit_id, role_id)`. Same person credited as both Performer and Producer = two rows. Role changes are remove+add.
- `add_links` of an already-linked target → **skip silently** (per-song). Rationale: bulk edit ergonomics. Selecting 20 songs from an album to add a credit, where 5 already have it, should not require pre-filtering to the 15 missing ones. The skip is per-song inside a bulk; the rest of the batch proceeds.
- `remove_links` of a non-existent link → hard error (`LookupError` → 404), full transaction rollback. **Asymmetric with add on purpose** — removing something that isn't there is "hey, that's not here, you should check that." Stale UI / concurrent-edit signal.
- `remove_links` of the currently-primary tag or album → allowed. Auto-promote the next remaining link of the same category to primary. If no remaining link exists, song ends up with no primary in that category.

### Empty containers

`SongMutationCommand` requires a minimum of 1 `song_id` and 1 actual change (i.e. at least one of `scalars`, `add_links`, `remove_links`, `update_album_links`, `set_primary_tag_id`, `set_primary_album_id` must be non-empty / set). Otherwise → 422 at Pydantic.

### Same-value writes

Writes pass through to the DB unconditionally. The audit layer is diff-based: it compares pre/post and emits no audit row if nothing actually changed. Case changes count as changes (e.g. `Bob` → `bob` is a real diff).

### Null vs empty string for nullable scalars

- Absent key → leave field alone (Pydantic `exclude_unset`).
- Explicit `null` → clear the field.
- Empty string → 422 reject. Use `null` to clear.

### set_primary_* on unlinked target

`set_primary_tag_id` / `set_primary_album_id` referencing an id not currently linked to the song → 404 hard error. Use `add_link` with `make_primary: true` to add+promote in one call.

### update_album_links on unlinked album

`update_album_links` for an album not currently linked to the song → 404 hard error. No upsert.

### Orphan policy

`remove_links` only deletes the join row. The underlying entity (Credit, Tag, Publisher, Album) is never touched, even if it ends up with zero remaining links anywhere. Orphan cleanup is a separate explicit command, never a side effect of unlink. (Aliases must not be deleted by an unlink operation.)

---

## Command Shape: Entity update commands

Entity renames affect every song/album linked to the entity. **In scope this pass** — the app doesn't function without them. Each is its own Pydantic class with its own field validators.

```json
{ "command_type": "rename_tag",       "tag_id": 5,      "name": "Rock",         "category": "Genre" }
{ "command_type": "rename_credit",    "credit_id": 1,   "display_name": "F. Mercury" }
{ "command_type": "update_publisher", "publisher_id": 9, "name": "EMI",         "parent_id": 12 }
{ "command_type": "update_album",     "album_id": 3,    "title": "...",        "type": "LP", "release_year": 1975 }
```

Coordinator opens conn + batch_id, dispatches to the right mutator's rename method, commits.

**No automatic per-song side effects.** Renaming Tag 5 from "Shrock" to "Rock" updates one row. The N songs linked to Tag 5 still have "Shrock" embedded in their ID3 files on disk — that drift is surfaced by existing UI elements and resolved by the user via bulk sync (planned, not built). Same drift-tolerance philosophy as ID3 write failures during song mutation.

API returns the updated entity object only.

---

## The Coordinator

Owns connection, transaction, batch_id. Decomposes the incoming command and fans out to per-entity mutators.

```python
def apply(self, command):
    if isinstance(command, SongMutationCommand):
        return self._apply_song_mutation(command)
    if isinstance(command, RenameTagCommand):
        return self._apply_rename_tag(command)
    # ...etc per command type
```

Song mutation flow:

```python
def _apply_song_mutation(self, command: SongMutationCommand) -> list[Song]:
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

            for upd in (command.update_album_links or []):
                self._album_mutator.apply_within(
                    upd | {"action": "update_link", "song_id": song_id},
                    conn, batch_id
                )

            if command.set_primary_tag_id:
                self._tag_mutator.apply_within(
                    {"action": "set_primary", "song_id": song_id, "tag_id": command.set_primary_tag_id},
                    conn, batch_id
                )
            if command.set_primary_album_id:
                self._album_mutator.apply_within(
                    {"action": "set_primary", "song_id": song_id, "album_id": command.set_primary_album_id},
                    conn, batch_id
                )

            post = self._library.get_song(song_id, conn)
            # TODO: audit.log_update(pre, post, conn, batch_id)
            results.append((pre, post))

        conn.commit()

        for _, post in results:
            try:
                self._id3_writer.write_metadata(post)
            except Exception:
                logger.error("ID3 write failed for song %s", post.id)
            try:
                self._filing.move_if_needed(post)
            except Exception:
                logger.error("File move failed for song %s", post.id)

        return [post for _, post in results]

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

`_route_link` dispatches on `link["type"]` to the right mutator.

---

## Mutator Interface

Each mutator implements `apply_within(slice: dict, conn, batch_id)`. Does NOT open connections, does NOT commit. Internal logic (get-or-create, validation, auto-promote) stays inside the mutator.

```python
class SongMutator:
    def apply_within(self, slice, conn, batch_id) -> None: ...    # action: "edit"

class CreditMutator:
    def apply_within(self, slice, conn, batch_id) -> None: ...    # actions: "add", "remove"
    def rename(self, slice, conn, batch_id) -> Credit: ...

class TagMutator:
    def apply_within(self, slice, conn, batch_id) -> None: ...    # actions: "add", "remove", "set_primary"
    def rename(self, slice, conn, batch_id) -> Tag: ...

class PublisherMutator:
    def apply_within(self, slice, conn, batch_id) -> None: ...    # actions: "add", "remove"
    def update(self, slice, conn, batch_id) -> Publisher: ...     # name + parent_id

class AlbumMutator:
    def apply_within(self, slice, conn, batch_id) -> None: ...    # actions: "add", "remove", "update_link", "set_primary"
    def update(self, slice, conn, batch_id) -> Album: ...         # title, type, release_year
```

Action set per mutator reflects the actual schema:
- **CreditMutator** has no `update` action — role is part of link identity, position is unused.
- **PublisherMutator** has no per-link scalars, so no link-update action.
- **TagMutator** join-row update collapses into `set_primary` (the only editable per-link scalar).
- **AlbumMutator** has `update_link` for `track_number` / `disc_number`.

---

## Command Slices (mutator-internal shape)

Mutators are unit-testable in isolation by feeding slices directly. Each slice is a flat dict with `action` + entity-specific fields.

```json
SongMutator:    { "action": "edit",        "song_id": 1, "fields": { ... } }
CreditMutator:  { "action": "add",         "song_id": 1, "name": "...", "id": 1, "role": "Performer" }
                { "action": "remove",      "song_id": 1, "id": 42 }
TagMutator:     { "action": "add",         "song_id": 1, "name": "Rock", "id": 5, "category": "Genre", "make_primary": false }
                { "action": "remove",      "song_id": 1, "id": 7 }
                { "action": "set_primary", "song_id": 1, "tag_id": 5 }
PublisherMutator:{"action": "add",         "song_id": 1, "name": "EMI", "id": null }
                { "action": "remove",      "song_id": 1, "id": 9 }
AlbumMutator:   { "action": "add",         "song_id": 1, "id": 3, "name": "...", "track_number": 1, "disc_number": 1, "make_primary": false }
                { "action": "remove",      "song_id": 1, "id": 2 }
                { "action": "update_link", "song_id": 1, "album_id": 3, "track_number": 5, "disc_number": 1 }
                { "action": "set_primary", "song_id": 1, "album_id": 3 }
```

---

## TagMutator and AlbumMutator: primary auto-promote

Both mutators own auto-promote logic internally. On `action: "add"`:

- `_check_primary(song_id, conn)` — returns True if the song has no existing primary in this category.
- If True, OR if `make_primary: true` is set on the slice, the new link is inserted with IsPrimary set (and any existing primary is demoted).

`set_primary` is a separate internal method used by both `action: "set_primary"` and the auto-promote path.

---

## SongMutator note

`Songs` and `MediaSources` are two tables but one logical entity. SongMutator writes to both via `SongRepository.update_scalars()` which already handles the split internally. No separate MediaMutator for now — revisit if non-Song media types (jingles, ads) are added.

---

## Truly non-song mutations (out of scope this pass)

Alias delete, soft-delete on songs, and any other operation that doesn't fit the song-or-entity-update shape. They get their own command types and own coordinator entry points later, following the same pattern (own Pydantic model, own conn/batch_id/audit lifecycle).

```python
coordinator.apply(DeleteSongCommand(song_id=42))
coordinator.apply(DeleteAliasCommand(alias_id=17))
```

Design separately when needed.

---

## Error mapping (router's job)

| Exception | HTTP |
|---|---|
| `LookupError` (missing song, missing link to remove, missing entity) | 404 |
| `ValueError` (constraint violation, conflicting primary, add of already-linked) | 400 |
| Pydantic validation error | 422 (FastAPI default) |
| Other | 500 |

---

## Side effects

Apply only to `SongMutationCommand`. Entity renames have **no automatic side effects** — DB write only, drift surfaced by UI.

For song mutations: side effects fire after `conn.commit()`. Non-fatal — exceptions caught and logged, execution continues.

- `MetadataWriter.write_metadata(post)` — ID3 tags
- `FilingService.move_if_needed(post)` — moves file if `post.desired_state_synced` is False and `AUTO_MOVE_ON_APPROVE` is enabled. Does not exist yet — add when implementing coordinator.

ID3 / filing failure leaves the DB authoritative; the file drifts. Existing UI elements (file-vs-DB diff panels) surface this; the user reconciles via bulk sync (planned).

Failures are also reported in the response body so the frontend can surface them immediately (toast etc.) without waiting for the next read:

```json
{
  "songs": [ ... ],
  "warnings": [
    { "song_id": 42, "kind": "id3_write", "error": "..." },
    { "song_id": 42, "kind": "file_move", "error": "..." }
  ]
}
```

Status remains 200 — the mutation succeeded; the warnings are advisory.

---

## Return shape

API returns only the directly-mutated resource:

- `SongMutationCommand` → `list[Song]` (post-state, one per song_id, in input order). **Note:** multi-song bulk return shape is unverified — there is no multi-select frontend yet, so only the single-song path is exercised. Revisit when bulk-edit UI lands.
- `RenameTagCommand` → `Tag`
- `RenameCreditCommand` → `Credit`
- `UpdatePublisherCommand` → `Publisher`
- `UpdateAlbumCommand` → `Album`

Entity renames have unbounded fan-out (a credit might appear on 500 songs); the API can't return all affected views. View consistency is a frontend concern — refresh-on-modal-close, normalized client cache, or full reload, frontend's choice. Backend is uniform.

---

## LibraryService.get_song conn threading

`get_song` gains an optional `conn` parameter. When provided, skip `get_connection()` and do NOT use a `with` block — sqlite3's context manager commits/rolls back on exit, which would break the coordinator's transaction. Call repo methods directly with the provided conn.

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
    album_mutator.py
```

---

## What does NOT change

- All read endpoints — untouched.
- `IngestionService` — its own transaction pattern.
- `EditService` — **only the methods that mutators actually call** gain a required `conn` param and lose internal `get_song()` / `_sync_id3_if_enabled` calls. The other ~20 methods stay as-is until a separate cleanup pass.
- `LibraryService.get_song` — gains optional `conn` param (see threading note above).

---

## Staging (rollout, not architecture)

"All five mutators ship together" is a **runtime** constraint — once frontend retargets to the new endpoint, all command types must work or the UI breaks. It is **not** a single-PR mandate. The implementation is staged across many reviewable PRs:

1. Frontend retargets to a stub `POST /mutate` that returns "got it" without doing anything.
2. Old per-operation endpoints get deleted so nothing accidentally calls them.
3. MutationCoordinator + Pydantic command models land behind the stub.
4. Mutators land one by one, each behind feature-gating in the coordinator dispatch.
5. Audit hookup once `AuditRepository.log_action` exists.

No single sitting writes the whole thing — review-ability is the constraint.

---

## Deferred details (next grill)

- Audit seam specifics: where pre/post computation lives for entity renames, slice contents for the audit row. (General principle established: auditor is diff-based, no-change → no row.)
- Authn/authz — single-tenant local app, presumably no-op, but undocumented.
- Multi-song bulk return shape — defer until multi-select UI exists.

Resolved in the alignment grill (2026-04-30): empty containers, same-value writes, null/empty-string handling, add-already-linked semantics, remove-missing semantics, primary-on-unlinked, update-album-link-on-unlinked, orphan policy, side-effect failure reporting, removal of currently-primary.
