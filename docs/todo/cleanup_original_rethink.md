# Cleanup Original — Rethink

Status: a partial fix is ALREADY COMMITTED in `src/engine/routers/ingest.py` (streaming loop
~line 112, `cleanup-original` endpoint) but was flagged "do not ship as-is" — it needs the rework
below before the feature is trusted. `cleanup-original` has zero test coverage.

## Problem

The "Delete Original" button on duplicate ingest cards was disabled for in-place scans because
`original_path=None` in in-place mode, so `original_exists` was never set.

- Staged mode: file copied to `temp/staging/<uuid>_name.mp3`; `original_path` = real source file
- In-place mode: file ingested where it sits; `original_path=None`; `staged_path` IS the file
- The streaming loop only set `res["original_path"]` / `res["original_exists"]` when
  `original_path` was truthy — button always disabled for in-place

## Partial fix currently in the code (needs rework)

1. Streaming loop: `effective_original = original_path or staged_path`
2. `cleanup-original` endpoint: Downloads-only guard replaced with a `get_by_path` string lookup
   (block if the file is some song's `source_path`)

Why it's not good enough: SQLite string comparison is case-sensitive, so
`Z:\Songs\song.mp3` vs `z:\songs\song.mp3` bypasses the guard on Windows.

## Agreed design

Mental model: "there is one file; is it a copy or the real thing?"

- The duplicate card frontend already has the matched song (`result.song.id`)
- Send `{ file_path, song_id }` to `cleanup-original`
- Backend: fetch song by ID, then compare
  `os.path.normcase(real_target) == os.path.normcase(source_path)`
- Same file -> block (you'd be deleting the library copy)
- Different -> delete (it's a redundant copy elsewhere)
- No Downloads guard, no string-keyed `get_by_path` lookup — ID-based fetch + normcase compare only

## Edge cases (all discussed and settled)

1. Drop from Downloads -> duplicate: staged copy auto-deleted; the Downloads original is the user's
   to delete manually — fine
2. Drop from outside Downloads -> duplicate: original path unknown to the server; button disabled;
   correct
3. Scan of a Downloads subfolder -> duplicate: `staged_path` is the real path; song_id available;
   safe to delete
4. Scan of `Z:\Songs\temp` -> duplicate: same as 3; normcase check prevents deleting the library copy
5. Scan of the library folder itself -> duplicate: `staged_path == source_path` -> normcase match ->
   blocked

Reminder (general filing rule, see CLAUDE.md): a file already existing at the destination means the
work is done — existence is never a reason to delete.
