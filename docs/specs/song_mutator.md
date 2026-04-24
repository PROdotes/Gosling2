# Spec: SongMutator

**Status:** Draft — 2 grill sessions complete, 1 more planned  
**Date:** 2026-04-24  
**Replaces:** 22+ individual song edit endpoints + `REFACTOR_PASS_OBJECTS.md` + `multiedit.md`  
**Context:** Part of the "morning coffee" refactor. See `morning_coffee_architecture.md`.

---

## The Problem

A single artist removal triggers 5–10 full song hydrations because every layer calls `get_song()` defensively. Every layer takes `song_id: int` and re-fetches the song from scratch.

The fix is not to pass objects around — it's to have one owner of the transaction that hydrates once before and once after, and passes the connection (not the ID) down to specialists.

---

## The Command Shape

All song mutations — atomic UI edits, Spotify imports, multi-edit, splitter confirms — produce the same command:

```json
{
  "song_ids": [1],
  "scalars": {
    "media_name": "Bohemian Rhapsody",
    "bpm": 120,
    "year": 1975,
    "isrc": "GBUM71029604",
    "notes": "remaster"
  },
  "add_links": [
    {
      "type": "credit",
      "name": "Freddie Mercury",
      "id": 1,
      "role": "Performer"
    },
    { "type": "credit", "name": "New Artist", "id": null, "role": "Composer" },
    { "type": "tag", "name": "Rock", "id": 5, "category": "Genre" },
    { "type": "publisher", "name": "EMI", "id": null },
    { "type": "album", "id": 3, "name": "A Night at the Opera", "album_type": "Studio", "track_number": 1, "disc_number": 1 }
  ],
  "remove_links": [
    { "type": "credit", "id": 42 },
    { "type": "tag", "id": 7 },
    { "type": "publisher", "id": 9 },
    { "type": "album", "id": 2 }
  ],
  "set_primary_tag_id": 5
}
```

Rules:

- `song_ids` is always a list. Single edits pass `[song_id]`.
- `scalars` only includes fields the user explicitly changed (`exclude_none` contract — same as today).
- `add_links`: `id` is optional. If present, `EditService` links directly. If null, `EditService` does get_or_create by name.
- `remove_links`: always have `id` (you can't remove something you haven't identified).
- `set_primary_tag_id`: optional. Promotes a genre tag to primary for the song. Sequenced last by the mutator.
- Any combination of fields is valid. An empty `scalars` with only `add_links` is fine.

### Album link rules

Album `add_link` fields: `id`, `name`, `album_type` (optional, fallback `ALBUM_DEFAULT_TYPE = "Single"`), `track_number`, `disc_number`.

- `id` present → link directly (name ignored).
- `id` null + `name` present → get_or_create by name, then link.
- `id` null + `name` null → **invalid**, rejected at Pydantic model validation time (same pattern as credits/tags/publishers). Album `add_link` currently does not follow this pattern — it needs a rewrite to match.

---

## The Mutator Flow

`SongMutator` lives in `src/services/song_mutator.py`.

```
SongMutator.apply(command):
    conn = repo.get_connection()                     ← opened internally, fresh per apply() call
    try:
        results = []
        for each song_id in command.song_ids:
            pre  = repo.get_song(song_id, conn)      ← hydration 1
            apply scalars via EditService
            apply remove_links via EditService
            apply add_links via EditService
            apply set_primary_tag_id via EditService (if present)
            post = repo.get_song(song_id, conn)      ← hydration 2
            # TODO: audit.log_update(pre, post, conn, batch_id)
            results.append((pre, post))

        conn.commit()                                ← single atomic commit for entire batch

        for (pre, post) in results:
            try:
                id3_writer.write_metadata(post)
            except Exception:
                logger.error(...)                    ← flag song as ID3 out of sync, continue
            try:
                if post.processing_status == REVIEWED and AUTO_MOVE_ON_APPROVE:
                    filing.move_if_needed(pre, post)
            except Exception:
                logger.error(...)                    ← log failure, continue (UI shows manual move button)

    except Exception:
        conn.rollback()
        raise                                        ← bubbles up; router maps to 400/404/500
    finally:
        conn.close()

    return results[-1][1]                            ← Song post-state (last song; changes when MultiSongView lands)
```

Rules:

- `SongMutator` owns the transaction boundary: open, commit, rollback on failure.
- `SongMutator` generates `batch_id = uuid4()` once per `apply()` call.
- `SongMutator.apply(command)` — opens a fresh connection via a repo's `get_connection()` at the start of each call. Connection is closed in a `finally` block so cleanup happens even if the side-effects loop throws. No `conn` parameter — the mutator owns the connection.
- `EditService` methods receive `conn` — they do not open their own connections.
- No layer below `SongMutator` calls `get_song()`.
- `_sync_id3_if_enabled` is removed from `EditService`. The only ID3 write is in the mutator, after `conn.commit()`.
- `filing.move_if_needed` fires only when `post.processing_status == REVIEWED and AUTO_MOVE_ON_APPROVE`. It compares `pre` vs `post` routing to decide if a physical move is needed. File moves are not part of the DB transaction.
- The "Move to Library" button (`POST /songs/{id}/move`) is a separate dedicated endpoint — no `move` flag in the command shape.

---

## Return Type

The mutator always returns a single `Song` (post-state). Frontend stops re-GETting after mutations; it uses the response body.

`MultiSongView` (collapsed multi-edit response) is deferred — the mutator's return type will change when multi-edit lands, but the internal loop structure is already correct.

---

## Resolution Responsibility

`EditService` already handles this correctly today — no change needed:

- `add_link` with `id` → link directly
- `add_link` without `id` → `get_or_create` then link

The mutator never sees names. Resolution stays in `EditService`.

---

## Callers / Adapters

Each existing entry point becomes a thin adapter that builds a command and calls the mutator:

| Caller                            | What it does before calling mutator                                 |
| --------------------------------- | ------------------------------------------------------------------- |
| Atomic UI edit router             | Builds command from request body, calls mutator                     |
| Spotify import router             | `SpotifyService.parse_credits` → build command                      |
| Filename parser router            | `FilenameParser.parse_with_pattern` → resolve names → build command |
| Multi-edit router                 | Build command from bulk request body                                |
| Splitter confirm router           | Resolve tokens → create missing identities → build command          |
| Primary tag router (`PATCH /songs/{id}/tags/{tag_id}/primary`) | Builds `{ song_ids: [id], set_primary_tag_id: tag_id }`, calls mutator |

The splitter is the only adapter with a pre-step (identity creation for unresolved names). That stays in the splitter router, not the mutator.

---

## What Changes

| Layer                             | Change                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `src/services/song_mutator.py`    | **CREATE** — owns transaction, sequences specialists                           |
| `src/services/edit_service.py`    | All methods gain required `conn` parameter; remove internal `get_song()` calls; delete `_sync_id3_if_enabled`; `remove_song_tag` gains auto-promote logic for primary genre |
| `src/engine/routers/`             | Song mutation endpoints become thin adapters, return mutator response directly; old endpoints deleted in same pass |
| `src/services/catalog_service.py` | Song mutation pass-throughs removed (replaced by mutator)                      |
| `src/services/filing_service.py`  | Add `move_if_needed(pre, post)` — reads `library_root` from config internally; calls `evaluate_routing` on both pre and post, moves only if path changed |
| `src/services/library_service.py` | `get_song` gains optional `conn` parameter; when provided, skips opening its own connection |

`AuditService`, `MetadataWriter`, `FilingService`, `EditService` resolution logic — **no changes to their core logic**, only `conn` threading.

---

## What Does NOT Change

- All read endpoints (`GET /songs/{id}`, search, filter) — untouched.
- `IngestionService` — has its own transaction pattern, separate concern.
- Album/tag/publisher edit endpoints — out of scope for this pass (they affect multiple songs and need a separate analysis).
- `EditService` internal resolution logic (`get_or_create` behavior).

---

## Router Strategy

Old song mutation endpoints are **replaced** by a single `POST /api/v1/songs/mutate` endpoint that accepts the command shape directly. Old endpoints are deleted once the frontend migrates.

Read endpoints are untouched.

### Migration order

1. Write mutator tests against current behavior (document expected responses)
2. Build `SongMutator` + `POST /songs/mutate`
3. Tests go green
4. Migrate frontend to send command shape to new endpoint
5. Delete old mutation endpoints

### Response codes

Standard contract per endpoint — at minimum: 200, 400, 404, 500. Some operations may add extra codes (e.g. 409 conflict) — handled case by case.

---

## Resolved Design Decisions

11. **Primary genre auto-promote on removal** — `remove_song_tag` gains auto-promote logic: if the removed tag was the primary genre, check if exactly one genre remains and promote it. Symmetric with the existing auto-promote in `add_song_tag`. Primary tag logic stays out of the mutator.

10. **`EditService` caller migration** — `conn` becomes a required parameter on all `EditService` methods. No backward-compat default. Callers outside the routers (tests, other services) are fixed as they break during the migration pass. Tests continue to use the conftest DB.

1. **`EditService` connection threading** — mutator owns the connection and passes `conn` down to all `EditService` methods. `EditService` methods gain a required `conn` parameter and stop opening their own connections. Old direct callers (routers via `CatalogService`) are deleted in the same pass. `batch_id` is naturally shared across all operations in one `apply()` call — the audit UUID will cover the entire mutation atomically once audit write is built.

2. **Album/tag/publisher mutations** — `update_album`, `update_tag`, `update_publisher` affect multiple songs because they trigger file path recalculation on every linked song (e.g. album year changes the folder name). They need the same treatment but are a genuinely different problem — "edit an entity that many songs reference" vs "edit a song." Separate spec, separate pass.

3. **ID3 failure** — ID3 is a projection of DB truth, not part of the transaction. If `write_metadata` fails, the DB commit stands and the song is flagged "ID3 out of sync." A manual re-sync resolves it. Bundling the file write into the DB transaction is not the right model. The sync indicator UI is a separate concern, not in this scope. `_sync_id3_if_enabled` is removed from `EditService` — the mutator's post-commit write is the only ID3 write path.

4. **Multi-edit atomicity** — all-or-nothing. Partial success ("songs 1–6 updated, 7–10 failed") is a worse outcome than a clean rollback with an error. It also breaks the audit batch UUID — a half-committed batch has no coherent undo story.

5. **`set_primary_tag_id`** — primary tag promotion is a top-level command field, not an `add_links` flag. The `PATCH /songs/{id}/tags/{tag_id}/primary` endpoint becomes a thin adapter that builds a minimal command and calls the mutator. Every song DB mutation goes through the mutator — no exceptions.

6. **Album `add_link` shape** — albums follow the same get_or_create contract as credits/tags/publishers. `id` present → link directly. `id` null + `name` present → get_or_create. `id` null + `name` null → invalid. `album_type` is optional, falls back to `ALBUM_DEFAULT_TYPE`. `year` is not required.

7. **Audit log** — `audit.log_update(pre, post, conn, batch_id)` is a known future insertion point in the mutator loop. A `# TODO` placeholder marks the spot. Not in scope for this pass.

8. **`move_if_needed`** — fires only when `post.processing_status == REVIEWED and AUTO_MOVE_ON_APPROVE`. The "Move to Library" button stays a separate dedicated endpoint and does not add a `move` flag to the command shape. `move_if_needed(pre, post)` reads `library_root` from config, calls `evaluate_routing` on both pre and post, and moves only if the path changed. Missing-file errors are caught by the mutator's side-effects `except` block and logged — no special handling needed.

12. **`LibraryService.get_song` conn threading** — `get_song` gains an optional `conn` parameter. When provided, it skips `get_connection()` and uses the caller's connection. Required so the mutator can read pre/post state within its own transaction.

13. **Command validation** — invalid command shapes (e.g. album `add_link` with both `id` and `name` null) are rejected at Pydantic model validation time, before the mutator opens a connection. Same pattern as credits/tags/publishers. Album currently doesn't follow this pattern — it needs a rewrite to match.

14. **Song not found** — if `get_song(song_id, conn)` returns `None`, the mutator raises (same as all other errors). The exception bubbles up; the router maps it to 404.

15. **`set_primary_tag_id` conflict with `remove_links`** — if the same tag_id appears in both `remove_links` and `set_primary_tag_id`, the remove runs first (per operation order) and `set_primary_song_tag` will fail on a non-linked tag. This is acceptable: add/remove auto-promote logic guarantees the song still has a primary genre, just not the explicitly requested one. No upfront validation needed.

9. **`MultiSongView`** — deferred. Mutator returns a single `Song` for now. The internal loop is already structured for multi-song; the return type changes when multi-edit lands.

---

## Success Criteria

- A title change triggers exactly 2 `get_song()` calls (pre + post).
- An artist removal triggers exactly 2 `get_song()` calls.
- A 50-song multi-edit triggers exactly 2 `get_song()` calls per song (100 total), not 500.
- All existing tests pass.
- Frontend stops sending redundant GET requests after mutations.
