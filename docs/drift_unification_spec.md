# Drift Compare Unification

## Problem

Clicking a song fires 3 backend requests, all for song id 312 (or whichever is active):

1. `GET /api/v1/songs/{id}` — full hydration, returns SongView.
2. `GET /api/v1/metabolic/inspect-file/{id}` — full hydration + ID3 read, returns file-side SongView.
3. `GET /api/v1/songs/{id}/sync-status` — full hydration + ID3 read, returns `{in_sync, mismatches}` (field-name strings).

That is **3 hydrations and 2 ID3 reads per click**. The same pattern fires after mutations.

The 3 endpoints exist for a reason — splitting the cheap DB call from the slow file read keeps the editor responsive when the user holds the down arrow through the list. The cheap call paints first, the slow call streams in. That part stays.

What is wasted:

- Hydrations 2 and 3 re-derive the same DB state hydration 1 already produced. The frontend already stores it in `state.activeSong` ([main.js:710](../src/static/js/dashboard/main.js#L710)). `inspect-file` only needs `source_path`; `sync-status` needs the hydrated db_song that the frontend already has.
- ID3 reads 1 and 2 are byte-identical — `inspect-file` and `sync-status` both call `MetadataService.extract_metadata()` + `MetadataParser.parse()` on the same file, ~20ms apart.
- The drift compare runs **twice on the server** (once inside `sync-status`, once implicitly via the file_song that `inspect-file` returns and the frontend then diffs locally) plus **a third time on the frontend** in `wireDriftIndicators` ([song_editor.js:494](../src/static/js/dashboard/renderers/song_editor.js#L494)).

The frontend and backend compares **diverge**. Confirmed concrete case: song 328, publisher differs between DB and file. The summary LED (server compare) lights up red, but no per-field dot appears on the publisher chip (frontend compare misses it). Frontend's `wireDriftIndicators` only checks `song.publishers`; the parsed file_song from `MetadataParser.parse()` does not populate that field the same way the DB hydration does. Two compares, two answers.

## Target

One diff. One ID3 read. One hydration per click for the two slow calls' purposes (the cheap initial `GET /songs/:id` stays as-is so the editor paints fast).

Backend produces a single diff object that both UI elements consume:

```
{
  "media_name": {"db": "Surrender", "file": "Surrender (Radio Edit)"},
  "year":       {"db": 2024, "file": 2023},
  "publisher":  {"db": "Haisley Music", "file": ""},
  "credit:Performer": {"db": "Haisley", "file": "Haisley, Other"}
}
```

- Empty object → in sync. LED green, no dots.
- Non-empty → LED red, listing the keys; one dot per key on the matching field, tooltip shows `db` vs `file` values.

Field keys must match the frontend's existing chip/scalar identifiers so the renderer can do `document.getElementById('ef-' + key)` or equivalent without translation tables. Use the existing `credit:Role` convention for credit-role granularity ([song_actions.js:59](../src/static/js/dashboard/handlers/song_actions.js#L59) already strips the prefix).

## Endpoint shape

Collapse to one slow endpoint. Suggested: extend `inspect-file` to return both pieces.

```
GET /api/v1/metabolic/inspect-file/{id}
→ { file_song: SongView, diff: {...} }
```

- One hydration (needed for `compare_songs` to have a db_song).
- One ID3 read.
- One compare.
- `file_song` is still returned because the frontend uses it for tooltip values and possibly other UI (verify before removing).
- `sync-status` endpoint and `getSongSyncStatus` API client function deleted.

Open question: can the backend skip rehydration here by accepting the db_song in the request body instead of re-fetching by id? The frontend already has it in `state.activeSong`. Trades a bigger request payload for zero hydration on this path. Decide during implementation — start with the simple version (server re-hydrates), measure, then optimize if the hydration cost is still visible.

## Backend changes

1. **`compare_songs` return shape.** Currently returns `{mismatches: [...]}` with field-name strings (used by `sync-status`). Change to return the diff object described above — keys are field identifiers, values are `{db, file}` pairs. Apply `filter_sync_mismatches` rules inline (or after) so the diff respects existing suppression rules.
2. **`inspect-file` endpoint.** After parsing the file, call `compare_songs(db_song, file_song)` and return `{file_song, diff}`. Keep the response shape stable for `file_song`; add `diff` alongside.
3. **Delete `sync-status` endpoint** ([song_updates.py:20](../src/engine/routers/song_updates.py#L20)).
4. **Verify `filter_sync_mismatches`** — what does it currently suppress? If it ignores e.g. TLEN drift because the server recomputes it, that logic is load-bearing and must stay in the unified compare.

## Frontend changes

1. **`getSongDetail`** ([api.js:122](../src/static/js/dashboard/api.js#L122)) — no signature change; response now includes `diff`.
2. **`state.activeSongFile`** — store the full response (`{file_song, diff}`) or split into `state.activeSongFile` + `state.activeSongDiff`. Pick one and be consistent.
3. **`wireDriftIndicators`** ([song_editor.js:494](../src/static/js/dashboard/renderers/song_editor.js#L494)) — rewrite. No more local set-diff. Iterate `diff` keys, find the matching DOM element, drop a dot with `db`/`file` in the tooltip. The function becomes ~20 lines.
4. **`updateSyncLed`** ([song_actions.js:40](../src/static/js/dashboard/handlers/song_actions.js#L40)) — read from `state.activeSongDiff` instead of calling `getSongSyncStatus`. No network call. `in_sync = Object.keys(diff).length === 0`. Mismatch list = `Object.keys(diff)`.
5. **Delete `getSongSyncStatus`** from [api.js:316](../src/static/js/dashboard/api.js#L316).
6. **Mutation refetch paths** — predicted future bug discussed in chat: after a title change or splitter mutation, the frontend currently refetches `getCatalogSong` even though the mutator already returned the post-state ([main.js:736, 759](../src/static/js/dashboard/main.js#L736)). Out of scope for this spec but worth noting — the same "trust the response, stop refetching" principle applies. Tackle separately.

## Cost per click after this change

- 1 hydration (cheap initial `GET /songs/:id`) — paints fast.
- 1 hydration + 1 ID3 read + 1 compare (`inspect-file`, slow path) — drift LEDs paint when ready.
- 0 redundant compares anywhere.
- 0 risk of LED-vs-dot divergence.

Down from 3 hydrations + 2 ID3 reads + 3 compares.

## Open questions to resolve during implementation

1. What does `compare_songs` currently return? Read it before designing the new shape.
2. Does `MetadataParser.parse()` populate `song.publishers` at all? If not, that's why song 328's publisher drift was invisible to the frontend compare — and the new server compare needs to handle the parser's actual output shape.
3. What rules does `filter_sync_mismatches` apply? Which are load-bearing?
4. Does anything besides the editor panel call `getSongSyncStatus`? Grep before deleting.
5. Tooltip values for chip fields (publishers, credits) — show comma-joined like today, or per-item? Match current behavior.

## Out of scope

- Caching `state.activeSong` server-side. Not needed.
- Composite endpoint that merges `GET /songs/:id` with `inspect-file`. Would break the fast-paint-on-scroll behavior.
- Mutation refetch cleanup (separate concern, separate spec).
- The "MP3 object has no attribute 'close'" warning in the log — pre-existing, unrelated.
