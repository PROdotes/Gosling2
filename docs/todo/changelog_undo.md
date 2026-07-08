# ChangeLog batch undo (recovery playbook + missing UI)

Every mutate batch is keyed by `batch_id` (uuid) in `ChangeLog`; field-level rows store
`old_value`/`new_value` per `(table_name, entity_id, field_name)`. This makes accidental
delete/reject batches recoverable — proven live 2026-06-24 (songs 165+651, "Između nas").

## Recovery playbook

- A deleted row = a ChangeLog group where every `new_value IS NULL`; reconstruct the INSERT from
  the `old_value`s. A scalar update = reverse each field to `old_value`.
- `DeletedRecords.FullSnapshot` was empty in the real case — ChangeLog is the reliable source.
- The reject path ("REJECTED: DUPLICATE") does `delete_song_links` (hard-deletes SongCredits /
  SongAlbums / MediaSourceTags / RecordingPublishers) + `soft_delete` (MediaSources.IsDeleted=1)
  + notes update. For a fresh-ingest duplicate it ALSO deletes the staging MP3 — the file is
  unrecoverable; only the DB rows come back.
- MediaSources PK is `SourceID` (not MediaSourceID). Set `PYTHONIOENCODING=utf-8` for any script
  printing song titles (diacritics crash cp1252).

## THE TRAP — never raw-SQL the live DB

DB triggers mirror every write into ChangeLog, but `batch_id` is stamped by the app's
`write_connection()` layer. A raw sqlite3 INSERT/UPDATE fires the triggers WITHOUT a batch_id ->
NULL-batch_id ChangeLog rows -> the `/api/v1/audit/integrity` guard reports "DB LOCKED" and
refuses all writes (polls ~30s). Recovery from the trap: delete the orphan rows
`WHERE batch_id IS NULL` after verifying `changed_at` matches the raw write. Better: do recovery
through the app's mutate path in the first place.

## Missing feature

No `batch_id` is surfaced anywhere in the UI, so undo is a manual log + ChangeLog dig. Wanted:
"show last batch + undo this batch" — reconstruct the reverse operations from old_values and apply
them through the normal mutate path (never raw SQL).
