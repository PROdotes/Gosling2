# ID3 Stale Tracking (dirty-flag) + Bulk Sync

## Problem
Detecting which songs' file tags are out of date with the DB. The naive approach —
walk all files and read ID3 frames over the network — is hundreds of round-trips and
slow over an SMB share. Multiprocessing does not help: this is I/O-bound (waiting on the
network), not CPU-bound, so processes just add overhead. Threads/async with bounded
concurrency would saturate the link better, but you are still opening every file.

This is the "how" for the bulk ID3 rewrite deferred in `project_deferred_id3_sync`
(entity renames are DB-only on purpose; auto-writing on rename would thrash hundreds of
files over the network).

## Insight
Staleness is a **write-tracking** problem, not a scan problem. Every DB write already
funnels through one chokepoint (`MutationCoordinator -> mutator -> repo`, the
`/api/v1/mutate` path). So a song is stale iff a tag-bound field changed since its last
sync — which we can record for free at write time. The stale-list then becomes a DB
query with zero network.

## Design

### Column
- `songs.id3_dirty BOOL NOT NULL DEFAULT 0`.
- **Schema default 0** — a freshly ingested song's DB was populated from its file's tags,
  so it is clean. Defaulting to 1 would falsely flag every new song.
- **Migration backfill = 1** for the existing rows. Entity renames have been DB-only all
  along, so the current ~500 files are already drifted from the DB. Backfill dirty, run
  one deliberate full sync to reconcile, and the flag is accurate from then on. (This is
  the init value vs. the schema default — two different decisions.)

### Marking dirty (in the mutator, one layer — no scatter)
Add `mark_songs_dirty(song_ids)` as a repo helper. The mutator calls it after any
mutation that touches a tag-bound field. The only real work is per-mutation "which songs
does this affect?" resolvers — irreducible domain joins, but all living in one file:

| Mutation | Affected songs |
|---|---|
| Song scalar / credit edit | that song |
| Identity / credit rename | all songs crediting that identity |
| Album rename | all songs on that album |
| Publisher rename | songs (and albums) under that publisher |
| Tag rename | all songs with that tag |

Guard against false positives with an `ID3_SYNCED_FIELDS` set in `config.py` (title,
year, BPM, ISRC, track/disc, performers, composers, tags, publisher, ...). A scalar edit
only marks dirty if the changed field is in that set — editing `notes` (not a tag field)
must not flag the file.

### Bulk sync
Iterate the dirty set, write DB -> file tags, clear `id3_dirty` to 0 per file on success.
User-triggered (works with the existing metadata writer; bulk path is new). Pairs with
multi-select once that is confirmed (`project_multiselect_status`).

### Full file scan — demoted, not eliminated
The dirty-flag misses only **out-of-band edits** (tags changed in another tool outside
Gosling) — rare. Keep a full scan as a rare background verification pass (status-3
background-job pattern, like WAV conversion), never blocking the UI. Prefilter with stored
`mtime`: 500 stats (cheap over SMB) and read frames only for files whose mtime moved.

## Cost shape
The one expensive 500-file pass happens **once**, on the user's terms (the baseline sync
after backfill), not on every audit. Steady state is always the cheap dirty-set query.

## Related
- `project_deferred_id3_sync` — the deferral this resolves.
- `project_metadata_writer` — the writer this bulk-drives.
- `project_multiselect_status` — selection surface for triggering bulk sync.
