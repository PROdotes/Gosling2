# Album get-or-create merge gap

`AlbumRepository.create_album` (src/data/album_repository.py, ~line 186) is a get-or-create, not a
blind insert. It matches on `AlbumTitle COLLATE UTF8_NOCASE AND ReleaseYear IS ?` — **title + year
only; artist is NOT in the key** — and if the matched row is soft-deleted it flips `IsDeleted=0`
(resurrects it). `AlbumMutator._add` calls this whenever `item.id is None` (e.g. the "create
single" action).

## Consequences

- Two different artists releasing a same-titled single in the same year silently fold into ONE
  shared album. Same-title pairs in the live DB survive today only by luck of differing years
  (e.g. "Sve" None vs 2026, "Ocean" 2026 vs None).
- Orphan-cleanup of an album can be silently undone by a later create-single of the same
  title+year (resurrection path).

## Status

- Mitigation shipped 2026-06-24: the album sub-card meta row in the song editor shows
  `track / song_count`, with the total in bold amber (`--warning`) when a `Single` has >1 song —
  a visual cue to spot accidental merges.
- Root fix NOT done: add artist to the match key, or stop auto-resurrecting (decide which with the
  user — both were floated).
- 2026-07-31: the auto-resurrect half is NOT album-specific. `song_credit_repository.py:150-165`
  does the same for artist names (wakes the name, its identity, and that identity's primary name,
  silently), and ChangeLog undo hits it from the other direction when restoring a link whose owner
  is soft-deleted. Tracked as D9 in `docs/todo/changelog_undo_map.md` — decide once, apply to both.

## Audit blind spot (made this hard to trace)

The `SongAlbums` link table is not in ChangeLog, and everything app-originated is labelled
`batch_label='ui'`. See docs/todo/logging_improvements.md.
