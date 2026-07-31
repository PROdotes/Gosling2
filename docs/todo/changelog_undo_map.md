# ChangeLog undo - decision map

Companion to `changelog_undo.md` (recovery playbook + the "missing feature" note that started this).
That doc says WHAT is wanted. This one tracks WHAT IS STILL UNDECIDED about how.

## Destination

ChangeLog becomes queryable per entity, and changes become reversible at two granularities:
a whole batch (one user action) and a single field of a single row. Plus provenance reads
("when was this artist added to this song").

## How to use this map

- Work ONE decision per session. Resolve it, write the answer into its Resolution line, move it
  to Decided.
- A decision is only listed here if it can be stated sharply. Everything vaguer lives in Fog.
- When fog clears into a sharp question, add it as a new decision.
- A decision needing real research graduates to its own `docs/todo/` doc; link it from here.
- Do not write implementation from this map. It ends when the route is clear; the build is a
  separate pass (zero-slop or plain units).

Status: OPEN | BLOCKED (by ...) | DECIDED

**This file is a dated draft, not a spec.** It is a snapshot of what was understood on the date of
each entry. Any part of it can be wrong and is expected to be revised once implementation or the
next conversation surfaces something it did not account for. A DECIDED entry is not binding; it
records what we concluded and WHY, so the reasoning can be re-examined rather than reinvented.
**This file has no authority.** It is evidence of past reasoning, never a rule to enforce, and
never grounds for arguing with the user. If the user says a decision recorded here is wrong -
including one they agreed to themselves - it is wrong, and the file gets updated. They hold the
shape of the app; this is a lossy snapshot of one conversation about it. Never answer a
correction with "but the doc says". Pointing at an entry's stated condition is a convenience for
reasoning, not a bar the user has to clear.

---

## Established facts (not decisions - already verified in code)

- One batch = one `write_connection(label)` = one mutate call = one user action
  (`src/data/base_repository.py:49`). `batch_id` uuid + human `batch_label`.
- Triggers write one ChangeLog row per COLUMN, `entity_id = NEW.rowid`
  (`src/data/schema.py:203-217`).
- `entity_id` is only meaningful where the PK is `INTEGER PRIMARY KEY`. On `SongAlbums`,
  `MediaSourceTags`, `RecordingPublishers`, `AlbumPublishers` (composite PKs) it is a bare
  implicit rowid - meaningless and reusable after deletes.
- No `op` column. Operation is derivable per group: all `old_value` NULL = INSERT,
  all `new_value` NULL = DELETE, else UPDATE.
- Granularity floor is inherent, not a choice: field-level for UPDATE; row-level for
  INSERT/DELETE (you cannot un-set one column of an inserted row).
- The UPDATE trigger emits only CHANGED columns (`schema.py:212`). A junction-row update that
  does not touch the key columns produces a group with no link back to its song. Adds and
  removes are unaffected (they carry every column).
- Read path today is one global query, no filters: `AuditRepository.get_changelog`
  (`src/data/audit_repository.py:7`), `GET /api/v1/audit/changelog?limit=500`.

---

## Decisions

### D0 - Attribution model: what does a change "belong to"?
**Status**: DECIDED 2026-07-31.

> A row INSERT or DELETE attributes to its own object AND every FK target it points at.
> A field EDIT attributes to its own object only - unless the edited field IS an FK, in which
> case it also attributes to the old and the new target.

Plain form: edits are tracked per object, relationships are tracked per both endpoints.
An artist rename belongs to the artist and has nothing to do with their songs. Linking that
artist to a song belongs to both the artist and the song. Adding an alias belongs to both the
alias and the identity.

Keyed off FKs, not table type, because some tables are both: `ArtistNames` is an editable object
(DisplayName, IsPrimaryName) that also carries an `OwnerIdentityID` link; `Publishers` carries
`ParentPublisherID`.

Consequence: song history NEVER reaches into artist entity edits, only into link events. This
removes the transitive walk and the "credited now vs credited at the time" ambiguity entirely -
there is no point-in-time reconstruction anywhere in this design.

**Decided fast and NOT yet stressed.** Cases likely to break it, to walk before building on it:
- **Identity merge** - rewrites credits from A's names onto B and deletes A. Under D0 that is a
  pile of link deletes/inserts attributing across every affected song. Does A's history end with
  anything legible? D0 has no concept of an event that belongs to the BATCH rather than to any
  single object, and a merge may be exactly that.
- **Song delete** - `delete_song_links` hard-deletes all four junction types, so under D0 one
  song deletion writes a "link removed" event into every credited artist, album and tag. Wanted,
  or history noise?
- **Two-album song** - primary-album flips are `SongAlbums.IsPrimary` edits: a link-table UPDATE,
  the exact case D0's FK rule handles worst. This makes the D5 "scar" a NORMAL user action, not
  an edge case.

### D1 - Does undo from an entity-scoped view apply the whole batch?
**Status**: OPEN. Blocks D3, D6.
A batch is atomic but not entity-scoped: a merge or a multi-select bulk edit is ONE batch
touching many songs. Viewing "changes to this song" can surface a batch that is mostly about
other songs.
Options: (a) undo applies the whole batch, UI states the blast radius loudly; (b) undo from a
scoped view reverts only this entity's rows, i.e. partial-by-entity; (c) scoped view is
read-only, undo only from the batch view.
**Resolution**:

### D2 - Staleness semantics when reversing a row
**Status**: OPEN. Blocks D3.
If a later batch changed the same field again, reverting to this row's `old_value` silently
clobbers the newer edit. Reversal must first assert current value still equals this row's
`new_value`.
Options: (a) hard refuse on mismatch; (b) warn and allow force; (c) skip stale rows, report them.
**Resolution**:

### D3 - Batch undo atomicity
**Status**: BLOCKED by D1, D2.
Batch undo = partial undo looped over the batch's rows. If row 7 of 20 fails the staleness
check: all-or-nothing rollback, or apply what is applicable and return a report?
**Resolution**:

### D4 - How is attribution stored?
**Status**: OPEN - the keystone. Blocks D5, D8, and the whole read side.
Query-time pivoting is ruled out by D0, not on cost but on capability: at trigger time the
trigger sees `NEW.*`/`OLD.*` for ALL columns, but the log only records CHANGED ones
(`schema.py:212`). So a `SongCredits.CreditPosition` edit records no FK columns and can NEVER be
attributed after the fact. Attribution must be stamped at write time.
Note D0 produces ONE-TO-MANY attribution (a link insert attributes to two objects), so a single
`root_table`/`root_id` column pair does not fit.
Options: (a) a separate `ChangeLogRefs` table, rows of (batch_id, table_name, entity_id,
ref_table, ref_id) - one per attributed object; (b) denormalised columns on ChangeLog with a
fixed max of 2 refs; (c) something else.
Also still needed regardless: an `op` column, or keep deriving it from the all-NULL tests?
**Resolution**:

### D5 - Backfill scope, and the junction-UPDATE scar
**Status**: BLOCKED by D4.
Existing rows CAN be largely backfilled - `op` is derivable everywhere, and INSERT/DELETE groups
carry every column so their FK targets are recoverable. The exception is link-table UPDATE groups
(`SongCredits.CreditPosition`, `SongAlbums.TrackNumber`/`IsPrimary`, `MediaSourceTags.IsPrimary`)
which recorded no FK columns. Decide: accept the scar, or resolve against the live table for the
subset whose rows still exist?
Separate and probably yes: change the UPDATE trigger to ALWAYS emit FK/key columns so the scar
does not keep growing.
**Resolution**:

### D6 - How does a reversal actually get applied?
**Status**: BLOCKED by D1.
Invariant 1: all writes go through `MutationCoordinator` -> mutators. Never raw SQL
(`changelog_undo.md:19-26` - raw SQL leaves NULL batch_id and trips the integrity guard,
locking all writes).
Open: does the existing mutation vocabulary express "re-insert this deleted credit"? Mutators
create rows with NEW ids; restoring a DELETE may need the original id back. If no mutation type
fits, one must be designed - and an undo is itself an audited batch, so undo-of-undo falls out.
**Resolution**:

### D7 - Is provenance its own feature?
**Status**: OPEN (likely dissolves).
"When was the artist added to this song", "when was this publisher linked", "when was this alias
added" are all the same query once D0 attribution exists: filter the log to rows attributed to
BOTH objects, take the INSERT. Probably not a separate feature at all - just a two-object filter
on the scoped view. Confirm once D4 lands.
**Resolution**:

### D8 - Making the log human-readable
**Status**: OPEN. Depends on D4.
Raw rows are unreadable: "linked 458 to 203", `IsDeleted: 0 -> 1`, `CreditedNameID: null -> 1847`.
Needs a display layer resolving (a) entity ids to names, (b) column names to labels, (c) whole
groups to sentences ("added Tom Waits as Artist").
The wrinkle: an id cannot always be resolved against the live DB - if the entity was later
deleted its name is gone. But it IS in the log (the delete group carries the old DisplayName).
So resolution is a fallback chain: live DB -> log history -> raw id.
Open: does this live behind the API as resolved display fields (invariant 6, thin frontend), and
is the chain computed per-request or materialised?
**Resolution**:

---

## North star (NOT in scope - months out, recorded only so we do not foreclose it)

"Song history" in the Wayback Machine sense: view a song's full state as of an arbitrary past
date, not just a list of changes. ChangeLog is already an ordered old->new event stream, so replay
is possible in principle and nothing decided so far prevents it.

Two things could quietly foreclose it, both cheap now and painful to retrofit:
1. **Stable identity for link rows.** Replay needs to know WHICH `SongAlbums`/`MediaSourceTags`
   row a historical change belonged to. Today `entity_id` on those tables is an implicit rowid
   that SQLite REUSES after deletes, so a replay can conflate two different rows. D4 should give
   link rows a stable identity, not only an attribution ref - that is nearly free while D4 is
   open and expensive afterwards.
2. **Retention.** Any pruning of ChangeLog caps how far back replay can reach. See Fog.

Do not build toward this. Just do not block it.

## Fog (not yet specified - do not ticket until sharp)

- UI surface: history panel on detail views, filter bar on the audit view, or both.
- What an undo looks like in the log afterwards (own batch? labelled how?).
- ChangeLog retention/pruning at 50-60k-song scale. Untouched so far.
- Whether album/artist/tag entities get the same scoped view as songs, or songs first.
- Undo permissions - anything gated, or all changes equally reversible?

## Decided so far

- **D0** (2026-07-31) Attribution model: edits per object, relationships per both endpoints,
  keyed off FKs. Removes all point-in-time reconstruction from the design.

## Ruled out

Each entry states what would make it valid again. If nothing would, it belongs in Established
facts instead. Do not cite an entry here as a rule without checking its condition first.

- **Filtering the log at the ROW level** (2026-07-31). A filtered set of rows is a fragment of a
  batch, and reversing a fragment produces a state the mutators never would.
  *Valid again if*: the view is read-only with no undo affordance anywhere near it.

- **Batch undo as the simple first feature, partial undo as a later add-on** (2026-07-31).
  Inverted: partial undo is the primitive, batch undo is a loop over it, and both need the same
  staleness check.
  *Valid again if*: undo is restricted to the most recent batch only - then there is nothing
  newer to clobber, the staleness check disappears, and batch undo genuinely is standalone.

- **Deriving attribution by pivoting ChangeLog at query time** (2026-07-31). The UPDATE trigger
  emits only CHANGED columns (`schema.py:212`), so a link-table update records no FK columns and
  cannot be attributed after the fact. Not a cost problem, a capability one.
  *Valid again if*: the UPDATE trigger is changed to always emit FK/key columns - then pivoting
  works for rows written after that change, and remains impossible for older ones.

- **Point-in-time credit resolution AS AN ATTRIBUTION FILTER** ("was this artist credited WHEN
  the change happened", used to decide whose history a change appears in) (2026-07-31).
  Dissolved by D0: song history contains link events, never artist entity edits, so the question
  never arises.
  *Valid again if*: D0 is overturned and song history must surface edits to linked entities.
  **NOT the same thing as state replay** - see the North star below. Do not cite this entry
  against a "song as of date X" feature.
