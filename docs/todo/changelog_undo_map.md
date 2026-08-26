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
- No `op` column, and operation is **NOT reliably derivable** (corrected 2026-07-31; the earlier
  claim that all-`old_value`-NULL = INSERT / all-`new_value`-NULL = DELETE / else UPDATE is wrong).
  The UPDATE trigger writes `NULLIF(CAST(NEW.{c} AS TEXT), '')` (`schema.py:211`), so clearing a
  text field to NULL or `''` when it is the ONLY changed column produces a group with every
  `new_value` NULL - indistinguishable from a DELETE. Symmetrically, setting a previously-NULL
  field reads as an INSERT. This is an ordinary edit (clear a comment, clear a release date), not
  a corner case, and an undo driven by the derivation would try to re-insert a row that was never
  deleted. Anything that consumed this fact - D5's "op is derivable everywhere" in particular -
  inherits the hole. See D10.
- Granularity floor is inherent, not a choice: field-level for UPDATE; row-level for
  INSERT/DELETE (you cannot un-set one column of an inserted row).
- The UPDATE trigger emits only CHANGED columns (`schema.py:212`). A junction-row update that
  does not touch the key columns produces a group with no link back to its song.
  REMOVES are unaffected - the DELETE trigger uses an unconditional `VALUES` and carries every
  column (`schema.py:215-219`). **ADDS are not** (corrected 2026-07-31): the INSERT trigger has
  `WHERE NEW.{c} IS NOT NULL` (`schema.py:205`), so NULL and `''` columns are omitted. Harmless
  for link tables, whose key columns are never NULL, but the blanket form of this claim was load-
  bearing under D0-b ("INSERT/DELETE groups carry every column") and only its DELETE half holds.
  Related lossiness: `NULLIF(..., '')` means an empty string is stored as NULL everywhere, so an
  undo restores NULL where the original held `''`.
- Ordering within a batch is `ChangeLog.id` (INTEGER PRIMARY KEY AUTOINCREMENT), NOT `changed_at`.
  `changed_at` defaults to `datetime('now')` - second resolution - so a whole batch shares one
  timestamp and "chronological order" is undefined inside it. `get_changelog` already reads
  `ORDER BY id DESC` and reverses per batch (`audit_repository.py:10,33`).
- EXHAUSTIVE INVENTORY of every UPDATE against a link table (2026-07-31, by grep + reading each
  statement against the trigger rule; the two starred rows are the only ones probe-verified, the
  rest are deterministic from `schema.py:212`). EVERY ONE is missing at least one key column:

  | statement | source | keys missing from the group |
  |---|---|---|
  | `SongCredits SET CreditedNameID` * | identity merge | `SourceID`, `RoleID` |
  | `AlbumCredits SET CreditedNameID` | identity merge | `AlbumID`, `RoleID` |
  | `RecordingPublishers SET PublisherID` | publisher merge | `SourceID` |
  | `AlbumPublishers SET PublisherID` | publisher merge | `AlbumID` |
  | `MediaSourceTags SET TagID` | tag merge | `SourceID` |
  | `MediaSourceTags SET IsPrimary` | set_primary_tag | both |
  | `SongAlbums SET IsPrimary` * | set/clear/promote_next | both |
  | `SongAlbums SET TrackNumber/DiscNumber` | update_track_info | both |

  `RecordingPublishers` and `AlbumPublishers` have ONLY key columns, so a repoint is their only
  possible UPDATE. This inventory is the evidence for "one trigger change covers everything" -
  it replaces an earlier extrapolation from two probed tables.
- Read path today is one global query, no filters: `AuditRepository.get_changelog`
  (`src/data/audit_repository.py:7`), `GET /api/v1/audit/changelog?limit=500`.
- `batch_label` carries no intent. Every app-originated batch is the hardcoded literal `"ui"`
  (`src/services/mutation_coordinator.py:108`); ingest is `"ingest"` six times
  (`src/services/ingestion_service.py`). Both name the write's ORIGIN, not the user's action.
  The intent is available and typed at that exact line - `body` holds `MergeIdentityItem`,
  `DeleteSongItem` etc. and the coordinator dispatches on those types four lines later - and is
  discarded. Noted 2026-05-13 (`project_logging_cleanup`), again in the previous session, written
  down neither time.
- Together with the two facts above, the log has three holes, not one: no `op` (what kind of
  change), no usable `entity_id` on composite-PK tables (which object), no `batch_label` (which
  action). Values are recorded; identity and intent are not.
- Physical vs ephemeral (shared vocabulary, 2026-07-31). PHYSICAL things - `MediaSources`,
  `ArtistNames`, `Identities`, `Albums`, `Tags`, `Publishers` - are soft-deleted, keep their IDs
  forever, and are what users read histories of. EPHEMERAL things - `SongCredits`, `AlbumCredits`,
  `SongAlbums`, `MediaSourceTags`, `RecordingPublishers` - are hard-deleted and their row ids are
  bookkeeping. An ephemeral row's real identity is its relationship TUPLE: `(song, name, role)`,
  `(song, album)`, `(song, tag)`. Nothing in the schema references `SongCredits.CreditID`, so
  restoring a credit under a different row id yields an identical database.
  NOTE the vocabulary collision: "physical/ephemeral" is about durability, and is the OPPOSITE
  pairing to soft-delete/hard-delete. Physical rows are soft-deleted; ephemeral rows are hard-deleted.
- `SongCredits.CreditedNameID` points at `ArtistNames`, NOT `Identities`. A song credits a NAME,
  with the human one hop further out via `OwnerIdentityID`. This is why a song can credit "Late!"
  while the person is Dave Grohl - and why an identity merge is a genuine change to the song.

---

## Decisions

### D0 - Attribution model: what does a change "belong to"?
**Status**: DECIDED 2026-07-31, REDRAFTED 2026-07-31 after D0-a.

> Any change to a row - INSERT, DELETE or field EDIT - attributes to its own object AND to every
> FK target the row points at. Where the change IS an FK repoint, that means BOTH the old and the
> new target, plus every other FK the row carries.

The original text split INSERT/DELETE from EDIT and said an FK edit attributes to the old and new
target but NOT to the row's other FK targets - i.e. an identity merge would not surface on the
song. D0-a walked that and it is wrong: the song's credited name changed, so the song changed.
Dropping the split is the simpler rule and is what all three stress cases actually want.

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

**Decided fast, then stressed against three cases the same day.** All three walked:
- **Identity merge** - WALKED 2026-07-31, see D0-a below. Broke D0's original FK-edit clause;
  that clause has since been redrafted away (above).
- **Song delete** - WALKED 2026-07-31, see D0-b below. Not a data problem at all; the noise worry
  was premised on a read pattern nobody has.
- **Two-album song** - WALKED 2026-07-31, see D0-c below. Confirmed the worst of the three, and
  fixed by the same one-line-ish trigger change as case 1.

### D0-a - Merge (D0 stress case 1)
**Status**: DECIDED 2026-07-31. Verified against a real IDENTITY merge run through the coordinator
with triggers installed (throwaway probe, not committed).

**Scope correction, same day:** this was written up as "identity merge" but the shape is shared by
all three merge types. `PublisherRepository.merge_into` and `TagRepository.merge_into` do the
identical dance - dedupe-DELETE where the target already exists on that parent, blanket repoint,
soft-delete the source - against `RecordingPublishers`/`AlbumPublishers` and `MediaSourceTags`
respectively. All three dedupe correctly (checked; no PK-collision bug). So everything below
applies to MergeIdentityItem, MergePublisherItem and MergeTagItem alike. Only the identity one was
probe-run; the other two are read from the code.

> A merge SURFACES on every affected song. The credited name changed, so what the song says
> changed, and that is a change to the song.

What the merge actually does (`identity_repository.py:650`) is NOT a pile of link deletes/inserts,
which is what this map assumed. It is two blanket repoints:
`UPDATE SongCredits SET CreditedNameID = target WHERE CreditedNameID = source`, same for
`AlbumCredits`. `SourceID` does not change, so per `schema.py:212` the trigger emits ONLY
`CreditedNameID` - no song anywhere in the group.

Measured on a 5-credit merge: 3 credits repointed (1 log row each, no `SourceID`), 2 credits
HARD-DELETED (5 log rows each, carrying every column including `SourceID`). The deletes happen
because `UNIQUE(SourceID, CreditedNameID, RoleID)` would be violated where the song already
credited the target in that role, so `merge_orphan_into` dedupes first. Consequence: which songs
are legible in the log is decided by a UNIQUE constraint, per-song AND per-role. Same user action,
two shapes.

**The fix is a trigger change, not an attribution model.** Making the UPDATE trigger always emit
key/FK columns turns every repoint group into `SourceID 3->3, RoleID 1->1, CreditedNameID 40->10`
- self-describing, durable, no join to the live table, no new table, no migration. Probe-confirmed:
cost was 2 extra rows per changed junction row. This change is currently a footnote under D5;
it is in fact the fix for this case and should be promoted.

Wart it introduces: those `3 -> 3` context rows are non-changes living in a change log. Consumers
must know to skip them, and D2's staleness check in particular must not assert on them.
**The wart turned out to be load-bearing enough to reopen the SHAPE of the change - see D10.**
What is decided here is that the trigger must carry the key tuple; HOW it carries it (pseudo-rows
vs a `row_key` column) is D10 and is still open.

Undo is unaffected by the two-shape asymmetry: undo reverses row groups mechanically and does not
care whether a group was an UPDATE or a DELETE. Repoints go `10 -> 40`, deleted credits are
re-inserted from their `old_value`s, `ArtistNames`/`Identities` flip `IsDeleted` back to 0.
Restoring a credit under a NEW row id is functionally identical (nothing references `CreditID`),
so the row id does not need preserving - the TUPLE does. This removes most of D6's worry for
credits; other tables not yet checked.

Corrections to earlier claims in this map, recorded so they are not re-derived:
- A's history DOES end legibly (`ArtistNames.IsDeleted 0->1`, `Identities.IsDeleted 0->1`).
- The repoint rows were never unrecoverable. `SongCredits.CreditID` is a real
  `INTEGER PRIMARY KEY`, so the song was reachable by joining live `SongCredits` - fragile
  (breaks once the credit is deleted), not lost. Case 3's `SongAlbums` is the genuinely
  unaddressable one.

**Still open, and it is this map's original case-1 bullet:** nothing in the log says a MERGE
happened. You infer it from N repoints plus an `ArtistNames` soft-delete sharing a batch. Whether
a batch-level event is first-class ("merged Taylor Hawkins into Dave Grohl") or whether the user
reads N per-row events is undecided - deliberately left to emerge rather than decided up front.
The two shapes also still render as two different sentences ("credit removed" vs "credit changed")
for one action; that dissolves if the batch carries intent.

**Consequence for D0's text: APPLIED 2026-07-31.** D0 originally said a field EDIT on an FK
attributes to the row plus the old and new target - explicitly NOT the song. That is the opposite
of the decision above, so the INSERT/DELETE vs EDIT split was dropped and D0 now reads "any change
attributes to the row plus ALL its FK targets". Recorded here because the reasoning, not the rule,
is the durable part.

### D0-b - Song delete (D0 stress case 2)
**Status**: DECIDED 2026-07-31. Verified by probe (delete of a song holding one link of every
junction type).

> Link events belong to the SONG. Whether any other endpoint gets a history view is a per-entity
> display choice, decided later and independently, not an attribution-model decision.

**There is no capability gap here.** The delete writes 21 fully self-describing rows: 2 SongCredits
groups (5 cols each), 1 SongAlbums (5), 1 MediaSourceTags (3), 1 RecordingPublishers (2), plus
`MediaSources.IsDeleted 0->1`. DELETE groups carry every column by design (`schema.py:215-219`),
so each carries its full tuple - no join needed, nothing missing for undo. Note this narrows the
trigger fix from D0-a: only UPDATE groups ever had the gap. Inserts and deletes were always fine.

The "history noise" worry dissolves because the read direction is song -> its link events, not
tag -> its songs. Nobody opens Rock to read what happened to it. The one real tag-side case is
scanning dates for rhythm ("a few Rock songs a day, or one a week?") - and that is served by the
same generic per-entity history list every object gets, so it needs no separate analytics feature.
Ranking if entity-side views ever get built: album is the most plausible ("which songs joined or
left this album"); artist's interesting events (rename/alias/merge) are edits to its OWN rows and
land in its history regardless; tag and publisher are lowest.

**Consequence for D4 - it shrinks again.** Since delete groups carry the full tuple (and insert
groups do for link tables, whose keys are never NULL - narrowed 2026-07-31),
"whose history shows this" is answerable by querying the log; it does not need attribution stamped
at write time. D4 is no longer "design an attribution store", it is "can the log be queried
object-scoped at volume, or does that need an index / materialised side table?" - an ergonomics
and row-count question.

**Type filter on song history (raised as a real use case: "when did the genres change, when did
the artists change").** `table_name` already IS the type, so the filter is a facet, not a feature:
`SongCredits`=artists, `SongAlbums`=albums, `RecordingPublishers`=publishers,
`Songs`/`MediaSources`=the song's own fields, `MediaSourceTags`=tags.

DECIDED: the filter is **tags**, not genres. A genre sub-filter may come later if wanted.
Reason to defer: `MediaSourceTags` rows are `(SourceID, TagID, IsPrimary)` and carry no category -
`TagCategory` lives on `Tags`, one hop away. So a genre-specific filter must resolve every TagID
against the live `Tags` table and silently drops rows for tags later deleted. That is D8's
fallback chain (live DB -> log history -> raw id) appearing in a FILTER rather than a label, which
is worse: a filter that quietly omits rows beats no filter only if you know it does it. Filtering
at the tag level needs none of that.

**Open interaction with D1 / the row-level rule-out:** a type-filtered song history IS a row-level
filtered view, which the "Ruled out" section permits only if it is read-only. If undo buttons
appear next to filtered rows, that rule-out is being violated. Resolve when D1 lands.

### D0-c - Primary album flip (D0 stress case 3)
**Status**: DECIDED 2026-07-31. Probe-verified on a two-album song.

> Same fix as D0-a. The trigger carrying key columns makes link-table edits addressable by TUPLE.
> **The surrogate-PK migration is dropped** - link rows need no stable id of their own.

(As first written this said "no schema migration is needed" full stop. Narrowed 2026-07-31: what is
retired is the surrogate-PK migration. D10 option (b) would still add one nullable column to
ChangeLog, which is not the same order of cost and should not be blocked by this sentence.)

Unpatched, flipping primary from album 1 to album 2 on song 6 logs exactly this:

    SongAlbums  eid=3  IsPrimary  1 -> 0
    SongAlbums  eid=4  IsPrimary  0 -> 1

No `SourceID`, no `AlbumID`. `entity_id` is an implicit rowid on a composite-PK table, so it is
both meaningless and reusable. This is the genuinely unattributable case - worse than D0-a, where
`SongCredits.CreditID` at least gave a real key to join on.

With key columns emitted, the same flip logs:

    SongAlbums  eid=3  SourceID 6->6  AlbumID 1->1  IsPrimary 1->0
    SongAlbums  eid=4  SourceID 6->6  AlbumID 2->2  IsPrimary 0->1

Fully addressable. **This retires the one expensive item in the whole plan.** Earlier reasoning
assumed link rows needed a stable surrogate id (also North star point 1); they do not, because the
TUPLE is the identity and the trigger was simply withholding it. Cases 1, 3 and D5's scar are now
one change to `build_trigger_sql` - though "one change" is ~10 lines and a scoping decision, not a
one-liner, and its shape is D10.

**Second finding - the no-op pair (FIXED, see below).** `set_primary` demoted ALL links then
promoted the target, so re-selecting the album that was already primary wrote a net no-op pair on
one row: `IsPrimary 1->0` then `0->1`. Undo of that batch depends entirely on iteration order.
Current value is 1; reverse order gives 0 then 1 and lands correct, forward order gives 1 then 0
and **leaves the song with NO primary album**. D2's staleness check does not catch it - current
value 1 matches the second row's `new_value` of 1, so the check passes and applies the wrong thing
confidently.

Two consequences:
1. **Batch undo MUST apply rows in DESCENDING `ChangeLog.id` order.** Absent from D3, load-bearing
   here. Note the ordering key is `id`, not `changed_at` - see Established facts; a whole batch
   shares one second-resolution timestamp, so "reverse chronological" is undefined inside a batch.
   In practice this is `get_changelog`'s raw query order with its per-batch `.reverse()` skipped.
2. Fixed at source 2026-07-31: `set_primary` (`song_album_repository.py`) and `set_primary_tag`
   (`tag_repository.py` - identical defect, one table over) now exclude the target from the demote.
   Probe confirms the no-op flip writes 0 ChangeLog rows and the real flip still writes its 2.
   Full suite green. This stops junk history accruing regardless of what undo ends up doing.

### D1 - Batch undo vs line undo
**Status**: DECIDED 2026-07-31 by the user, and it was already answered 2026-07-31 09:42 before
this entry was written - the entry re-asked a settled question and should not have existed.

> **Batch undo and line undo are SEPARATE OPERATIONS.** Not one operation with a scope ambiguity.
> The user chooses which one they are doing.

User's words: "batch undo and partial undo are both separate things... if i change the year on 20
songs by mistake, i have to be able to undo that... but i also have to be able to undo just 1 year
of 1 song".

So the question this entry originally asked - "does undo from an entity-scoped view apply the whole
batch, or only this entity's rows?" - is a false frame. There is no ambiguity to resolve: a line
undo undoes that line, a batch undo undoes that batch, and the UI offers both as distinct actions.

Consequence for the row-level-filtering rule-out: it dies completely. The objection was that
reversing a filtered fragment of a batch "produces a state the mutators never would". But a line
undo is not a fragment of a batch - it is a first-class operation in its own right. See Ruled out.
**Resolution**: recorded above.

### D1-a - Undo is a RESTORE, not a Ctrl-Z
**Status**: DECIDED 2026-07-31 by the user. New information; not previously stated.

> "the undo is not a ctrl z... not a literal undo... it's a restore... i'm not looking to go back
> 1 or 5 steps... i'm looking to restore something to that state"

This is the load-bearing frame for the whole feature and it was mis-modelled until now. The design
assumed transactional reverse semantics: walk back N steps, and a later edit to the same field is a
CONFLICT. It is not. The operation is "set this thing to the state it had at that point", chosen
deliberately by a user looking at a specific past state. A newer intervening edit is simply what the
current value happens to be, and overwriting it is the POINT of the operation, not a hazard.

Dissolves D2 (see below). Shrinks D3 and D6.

### D2 - Staleness semantics when reversing a row
**Status**: DISSOLVED 2026-07-31 by D1-a. Was: OPEN, blocking D3.
The entry asked whether a restore should hard-refuse / warn-and-force / skip when a later batch
changed the same field. **The question only exists under Ctrl-Z semantics.** Under restore
semantics there is no staleness and no conflict: the user is choosing a past state to return to,
and whatever the value is now is exactly what gets overwritten.

No staleness assertion. Do NOT build one - it would refuse the operation's main use case (the
field was changed again by mistake and the user wants it back).

Displaying the current value next to the restore target is a UI nicety, not a guard, and belongs
with D8's display work. Note this also retires the reason the no-op `IsPrimary` pair was scary
under D0-c: order still matters for correctness, but there is no check to fool.
**Resolution**: recorded above.

### D3 - Batch undo atomicity
**Status**: OPEN, and much smaller. Unblocked 2026-07-31 (D1 decided, D2 dissolved).
Originally: "if row 7 of 20 fails the staleness check, all-or-nothing or partial-with-report?"
**There is no staleness check** (D2), so that failure mode is gone. What can still fail mid-restore
is narrow: a restore whose endpoint owner is soft-deleted (D9), or an FK/UNIQUE constraint refusing
a re-inserted link. Question reduces to: on one of those, roll the whole batch restore back, or
apply the rest and report? Given D1-a's framing - the user picked a state to return to - partial
application with a clear report is the likelier fit, but not decided.
**Resolution**:

### D4 - How is attribution stored?
**Status**: OPEN, but SHRUNK and DOWNGRADED 2026-07-31 - no longer the keystone, and no longer
blocking. D0-b and D0-c between them establish that no attribution STORE is needed: once the key
tuple is in the log (D10), every event is self-describing and attribution is a query. What remains
is an ergonomics/volume question - can the log be queried object-scoped at 50-60k songs, or does it
need an index / materialised side table? That does not gate D5, D7 or D8, all of which were
formally blocked on this entry and should be treated as unblocked. The keystone is now D10.
The options below are kept only as the record of why an attribution store was considered.

Query-time pivoting was ruled out by D0, not on cost but on capability: at trigger time the
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
**Status**: OPEN (unblocked 2026-07-31 - D4 no longer gates it). PARTLY OVERTAKEN - the "separate
and probably yes" trigger change at the bottom of this entry turned out to be the fix for D0-a AND
D0-c, and has since been promoted out entirely into D10. Treat this entry as backfill-only.
Existing rows CAN be largely backfilled - though two premises weakened 2026-07-31: `op` is NOT
derivable everywhere (NULL/`''` clears masquerade as DELETEs) and only DELETE groups truly carry
every column, INSERT groups omit NULLs. Neither breaks backfill for link tables, whose keys are
never NULL, but a backfill must not assume the general case. The exception is link-table UPDATE groups
(`SongCredits.CreditPosition`, `SongAlbums.TrackNumber`/`IsPrimary`, `MediaSourceTags.IsPrimary`)
which recorded no FK columns. Decide: accept the scar, or resolve against the live table for the
subset whose rows still exist?
Stopping the scar from growing is D10 and is decided there, not here.
**Resolution**:

### D6 - How does a reversal actually get applied?
**Status**: OPEN and mostly closed 2026-07-31. Unblocked (D1 decided); the id half was already shut.
D1-a shrinks it further: a restore is an ordinary mutate setting a field to a KNOWN value, which the
existing vocabulary already expresses for scalars. Only re-creating a hard-deleted link row needs
checking against the mutators - and by the ephemeral rule below, that is a plain create.
Invariant 1: all writes go through `MutationCoordinator` -> mutators. Never raw SQL
(`changelog_undo.md:19-26` - raw SQL leaves NULL batch_id and trips the integrity guard,
locking all writes).

**The "may need the original id back" worry is dead**, answered by the physical/ephemeral
vocabulary already in Established facts (the map made this observation for credits under D0-a and
never generalised it). EPHEMERAL rows are hard-deleted and nothing references their ids, so
restoring under a new id yields an identical database - the TUPLE is the identity. PHYSICAL rows
are soft-deleted, so their undo is an `IsDeleted` flip with the id never having gone anywhere.
There is no case where an id must be forced.

What is left is a code survey, not a design question: does the existing mutation vocabulary express
each needed reverse op? If no mutation type fits, one must be designed - and an undo is itself an
audited batch, so undo-of-undo falls out.
**Resolution**:

### D7 - Is provenance its own feature?
**Status**: OPEN (likely dissolves). Unblocked 2026-07-31 - was waiting on D4, which no longer
gates anything.
"When was the artist added to this song", "when was this publisher linked", "when was this alias
added" are all the same query once D0 attribution exists: filter the log to rows attributed to
BOTH objects, take the INSERT. Probably not a separate feature at all - just a two-object filter
on the scoped view. Confirm once D10 lands - note "take the INSERT" needs the op question from
D10's rider, since op is not derivable.
**Resolution**:

### D8 - Making the log human-readable
**Status**: OPEN. Unblocked 2026-07-31 (was "depends on D4"). Interacts with D10: option (a) there
would put non-change rows in front of this display layer, which would have to hide them.
Raw rows are unreadable: "linked 458 to 203", `IsDeleted: 0 -> 1`, `CreditedNameID: null -> 1847`.
Needs a display layer resolving (a) entity ids to names, (b) column names to labels, (c) whole
groups to sentences ("added Tom Waits as Artist").
The wrinkle: an id cannot always be resolved against the live DB - if the entity was later
deleted its name is gone. But it IS in the log (the delete group carries the old DisplayName).
So resolution is a fallback chain: live DB -> log history -> raw id.
Open: does this live behind the API as resolved display fields (invariant 6, thin frontend), and
is the chain computed per-request or materialised?
**Resolution**:

### D9 - Linking to a soft-deleted owner: silently resurrect, or ask?
**Status**: OPEN. Raised 2026-07-31 from the undo side; shared root with
`docs/todo/album_merge_gap.md`, decide ONCE for both.
Today the app silently resurrects. Adding a credit whose `ArtistNames` row is soft-deleted
(`src/data/song_credit_repository.py:150-165`) wakes the name, its identity, AND that identity's
primary name - three undeletes, no prompt. `AlbumRepository.create_album` does the same for albums;
`album_merge_gap.md` already lists "stop auto-resurrecting" as a candidate root fix, undecided.
Undo needs the same guard from the other direction: restoring a link whose endpoint is deleted must
not quietly revive it. Proposal on the table: the UI raises and asks whether to undelete the owner.
This is what makes row-level filtered views safe (see Ruled out, weakened entry) - it is a
mutator-level dependency check, not a UI restriction.
**Resolution**:

### D10 - What SHAPE does the trigger change take?
**Status**: OPEN. Raised 2026-07-31 (fresh-eyes pass). **This is the new keystone** - D0-a, D0-c,
D5's scar, the op-derivation hole in Established facts, and North star point 1 all terminate here.
Nothing else should be built before it.

D0-a and D0-c decided WHAT: the log must carry the key tuple of the row that changed. They also
assumed HOW - the UPDATE trigger emits key/FK columns as ordinary rows, giving `SourceID 6->6`
context rows. That how is now in question.

**Option (a) - pseudo-rows (currently recorded).** No schema change. But:
- `get_changelog` (`audit_repository.py:7`) returns every row ungrouped to the UI, so a 2-row
  primary-album flip renders as 6 rows, 4 of them saying nothing changed. A visible audit-view
  regression, not only an internal consumer note.
- It contradicts the generator's own documented contract (`schema.py:184`, "Only logs where the
  value actually changed"). A ChangeLog row stops meaning "a change".
- It patches UPDATE only; INSERT/DELETE keep carrying the tuple by luck of emitting all columns.

**Option (b) - `ALTER TABLE ChangeLog ADD COLUMN row_key TEXT`**, populated by all three triggers
with the row's key tuple. Same trigger-regeneration effort, no non-change rows, no consumer or UI
change, uniform across INSERT/UPDATE/DELETE, and it delivers North star point 1 directly rather
than as a side effect. Costs one nullable ADD COLUMN.
The recorded reason for preferring (a) was "no migration" - but the migration that phrase was
coined against was the surrogate-PK one dropped in D0-c. A nullable ADD COLUMN on ChangeLog is not
in that category, and "no migration" appears to have been promoted from a tradeoff to a goal after
it stopped being the relevant tradeoff.

**Rider, decide with it: add `op` in the same pass.** Established facts now records that operation
is NOT derivable (empty-string/NULL clears masquerade as DELETEs). The only thing that made an `op`
column look expensive was the same migration objection. If (b) wins, `row_key` + `op` is one pass
and the hole closes for free; if (a) wins, `op` still has to be solved somehow and gets no cheaper
later.

**Scope question neither option has answered:** `build_trigger_sql` reads only `PRAGMA table_info`
and has no notion of key or FK. Either shape needs a `PRAGMA foreign_key_list` pass plus a decision
on WHICH columns count - PK, UNIQUE-constraint, or all FKs - and whether this applies to link
tables only or to every table (a `Songs.Title` edit would otherwise start carrying its FKs too).
This is ~10 lines plus that decision, not the one-liner D0-c implies.

**Deploy note (unlisted anywhere so far):** triggers are `CREATE TRIGGER IF NOT EXISTS`, so editing
`build_trigger_sql` changes nothing on an existing DB. The live DB needs its audit triggers dropped
and regenerated (`regenerate_triggers.py`, `schema.py:180`). DDL does not fire triggers, so this
does not trip the NULL-batch_id guard - but it is a required step, and until it runs the change is
invisible.

**Resolution**: DECIDED 2026-07-31. **Option (b), plus an explicit `op` column, in one pass.**
`ALTER TABLE ChangeLog ADD COLUMN row_key TEXT` + `ADD COLUMN op TEXT`, both populated by all three
regenerated triggers. `row_key` = PK columns + all FK columns, packed as a string.

Why (b) over (a): (b) is additive - `get_changelog` selects explicit columns, so nothing existing
sees the new column until it asks. (a) changes what a ChangeLog row MEANS for all time, and that
meaning has to be re-taught at every consumer, including ones not yet written.

Why explicit `op` even though (a) would have given it free: (a)'s pseudo-rows disambiguate a
cleared-field UPDATE from a DELETE only as a side effect of a different decision (a DELETE group
never has a non-null -> non-null row; an (a)-style UPDATE always does). That is exactly the class of
implicit rule that produced this map's corrections. `op` says what it means; once it exists, (a)'s
only unique advantage is gone.

Why packed string over JSON+generated columns or a refs table: this is where D10 and D4 turn out to
be one decision - once `row_key` carries the FKs it IS D0 attribution, and querying it is D4's
residue. A packed string answers that with `LIKE`, which will not hold at 50-60k songs. Accepted
deliberately: the log is append-only, so a refs table can be materialised FROM `row_key` whenever
volume proves it necessary, losing nothing. Getting row_key's CONTENTS wrong would cost a history
rewrite; getting its FORMAT wrong is recoverable. Optimise for the retreat.

**One-way door, flagged and accepted:** `row_key` is stamped at write time and cannot be
reconstructed for existing rows. Everything logged before the trigger regen has no `row_key` and
never will - D5's junction-UPDATE scar is permanent. Accepted because no current feature reads
history from before the change.

Next step is a probe on a throwaway DB, not implementation - confirm the generated trigger SQL and
what the rows actually look like for a merge, a primary flip, and a song delete.

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
   **RESOLVED 2026-07-31 by D0-c, and cheaper than this feared.** The identity is the TUPLE, not a
   surrogate id. Once the trigger carries the key tuple (D10), every link-row event carries
   `(song, album)` / `(song, tag)` / `(song, name, role)` and the reusable rowid stops mattering.
   No surrogate-PK migration. This point is closed in principle; D10's shape decides whether the
   tuple arrives as context rows or as a `row_key` column, and (b) serves replay more directly.
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
  Second clause found wrong by D0-a and REDRAFTED same day: any change attributes to the row plus
  ALL its FK targets; the INSERT/DELETE vs EDIT split is gone.
- **D0-a** (2026-07-31) Merge (identity AND publisher AND tag - same shape) surfaces on every
  affected song. Fix is "UPDATE trigger always emits key/FK columns", not an attribution store.
  Promotes that change out of D5.
- **D0-b** (2026-07-31) Song delete: link events belong to the song; other-endpoint views are a
  later per-entity display choice. No data change needed. Song-history type filter is a facet on
  `table_name`; it filters TAGS, not genres.
- **D0-c** (2026-07-31) Primary-album flip: same trigger fix; link identity is the TUPLE, so the
  surrogate-PK migration is dropped. Batch undo must iterate by descending `ChangeLog.id`.
  `set_primary` / `set_primary_tag` no-op pair fixed at source.
- **D10** (2026-07-31) Trigger shape: `row_key` + `op` columns on ChangeLog, populated by all three
  triggers; `row_key` = PK + FK columns, packed string. Additive rather than semantic; format
  chosen to keep the retreat to a refs table open. Pre-regen history keeps no `row_key`, accepted.
- **D1** (2026-07-31, user) Batch undo and line undo are SEPARATE OPERATIONS, not one operation with
  a scope ambiguity. Kills the row-level-filtering rule-out outright.
- **D1-a** (2026-07-31, user) Undo is a RESTORE to a chosen past state, not a Ctrl-Z walking back N
  steps. Overwriting a newer edit is the point, not a hazard. The single most load-bearing frame in
  the feature, and it was mis-modelled until stated.
- **D2** (2026-07-31) DISSOLVED by D1-a. No staleness check exists to design; building one would
  refuse the feature's main use case.

**The through-line of all three:** every case reduced to one change - get the row's key tuple into
the log at trigger time. No attribution table needed. D4 shrank from "design an attribution store"
to "can the log be queried object-scoped at 50-60k songs, or does it need an index?" - a volume
question, not a design one - and stopped being the keystone.

**Fresh-eyes pass, 2026-07-31 (same day).** The through-line survived; two of its riders did not.
"No `op` column yet" rested on op being derivable, which it is not (see Established facts). "No
migration" rested on a comparison with the dropped surrogate-PK migration, not on a nullable ADD
COLUMN being costly. Both now sit inside the one genuinely open question, D10 - the SHAPE of the
trigger change - which is the new keystone. Also corrected in this pass: INSERT groups do not carry
every column, and batch-undo ordering is by `ChangeLog.id`, not `changed_at`. D4 and D6 were
downgraded; D5, D7 and D8 are unblocked.

## Ruled out

Each entry states what would make it valid again. If nothing would, it belongs in Established
facts instead. Do not cite an entry here as a rule without checking its condition first.

- **Filtering the log at the ROW level** (2026-07-31). A filtered set of rows is a fragment of a
  batch, and reversing a fragment produces a state the mutators never would.
  *Valid again if*: the view is read-only with no undo affordance anywhere near it.
  **DEAD, same day (2026-07-31), superseding the "weakened" note below.** D1 settles that a line
  undo is a FIRST-CLASS OPERATION, not a fragment of a batch - the user chooses line or batch. The
  entire objection rested on treating a filtered row as a batch fragment, so it does not apply.
  Filtered views are fine. The only real constraint left is D9's dependency check. Retained below
  for the reasoning, not as a live rule.

  **WEAKENED, earlier same day.** The objection is narrower than written. Walking it against a concrete
  case (song-delete batch, history filtered to "artists", undo the one visible credit removal) the
  only genuinely unreachable state was a credit hanging off a DELETED song. Everything else the
  fragment produces - a live song with one credit and no album/tag/publisher - is a perfectly legal
  state reachable by ordinary use. So the fix is a dependency check at restore time (see D9), NOT a
  ban on filtered views. Undo-one-line-undoes-one-line is a defensible promise provided the UI does
  not imply it restored the whole batch. Treat this entry as: filtered views are fine, fragments
  that land on a dead owner are not.

- **Batch undo as the simple first feature, partial undo as a later add-on** (2026-07-31).
  Inverted: partial undo is the primitive, batch undo is a loop over it, and both need the same
  staleness check.
  *Valid again if*: undo is restricted to the most recent batch only - then there is nothing
  newer to clobber, the staleness check disappears, and batch undo genuinely is standalone.

- **Deriving attribution by pivoting ChangeLog at query time** (2026-07-31). The UPDATE trigger
  emits only CHANGED columns (`schema.py:212`), so a link-table update records no FK columns and
  cannot be attributed after the fact. Not a cost problem, a capability one.
  *Valid again if*: the trigger is changed to carry the key tuple (D10, either shape) - then
  pivoting works for rows written after that change, and remains impossible for older ones.

- **Point-in-time credit resolution AS AN ATTRIBUTION FILTER** ("was this artist credited WHEN
  the change happened", used to decide whose history a change appears in) (2026-07-31).
  Dissolved by D0: song history contains link events, never artist entity edits, so the question
  never arises.
  *Valid again if*: D0 is overturned and song history must surface edits to linked entities.
  **NOT the same thing as state replay** - see the North star below. Do not cite this entry
  against a "song as of date X" feature.
