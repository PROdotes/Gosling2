# Duplicate detection (acoustic fingerprint + fuzzy name)

## Build checklist - Part 1 (traced against the codebase 2026-09-10)

Everything below this section is rationale and evidence. This is the part an implementer
needs. Decisions are already made - do not re-open them here, read the rationale if a
decision looks wrong.

### 1. `src/engine/config.py` - path constant

Add next to `FFMPEG_PATH` (currently line ~86):

```python
FPCALC_PATH = _PROJECT_ROOT / "ffmpeg/fpcalc.exe"
```

`fpcalc.exe` is already present in `ffmpeg/`. Invariant 7: no inline paths anywhere else.

### 2. `src/data/schema.py` - new table

Add a `CREATE TABLE IF NOT EXISTS AudioFingerprints (...)` alongside the others:

- `SourceID` - PK, FK to `MediaSources(SourceID)`
- `Fingerprint` BLOB - raw uint32 array, explicit little-endian, NULL when not computed
- `DurationS` REAL - duration as fingerprinted
- `LengthCap` INTEGER - 180, stored so a future cap change is detectable
- `ComputedStatus` TEXT - the tri-state: never attempted / computed / fpcalc failed.
  A NULL blob alone cannot distinguish "not tried" from "tried and failed", and that
  distinction is what stops backfill re-reading broken files off the network drive forever.
- `CreatedAt`

**CRITICAL: add `"AudioFingerprints"` to `EXCLUDED_FROM_AUDIT`** (currently
`{"ChangeLog", "StagingOrigins"}`, schema.py line ~178). This is not optional:

- `build_trigger_sql()` generates `CAST(NEW.{c} AS TEXT)` for *every* column, so an audited
  blob table would dump a ~5.7 KB binary-cast-to-text row into `ChangeLog` on every insert.
- Worse, audited writes that do not go through `write_connection()` leave NULL `batch_id`
  rows, and `BaseRepository.get_connection()` raises `AuditIntegrityError` on the next open,
  **locking all writes** (invariant 10). Fingerprints are machine-derived and written on the
  ingest path, so they must not enter the audit stream at all.

This mirrors the design split exactly: derived data is excluded from audit, human judgment
(the future verdicts table) is not.

Note `build_trigger_sql()` must run after the table exists - `_ensure_db()` in
`src/engine_server.py` (line ~55) already handles fresh databases. An existing database
needs the `regenerate_triggers.py` utility, per the docstring in schema.py.

### 3. `src/utils/audio_fingerprint.py` - new module

Mirror `src/utils/audio_hash.py` in shape and error style.

```python
def calculate_fingerprint(filepath: str) -> tuple[np.ndarray, float] | None
```

- Shells `FPCALC_PATH -raw -length 180`, parses `FINGERPRINT=` and `DURATION=`.
- Returns the raw uint32 array plus the reported duration.
- **No trimming, no normalisation.** Rejected - see the trim section below.
- fpcalc failure -> log, return None, caller records the failed status and continues.
  Ingest must never fail because a fingerprint could not be computed.

### 4. `src/data/audio_fingerprint_repository.py` - new repository

SQL/CRUD lives here and nowhere else (invariant 2). Write methods return
`cursor.rowcount` and never raise on zero rows (invariant 3). Takes a caller-owned `conn`.

### 5. `src/services/ingestion_service.py` - compute + store

**Three call sites create sources, not one.** Extract a single private helper and call it
from all three rather than writing it three times:

| Method | Line (approx) | Notes |
|---|---|---|
| `ingest_file` | 389 | main path |
| `resolve_conflict` | 468 | re-ingest / ghost reactivate |
| `finalize_wav_conversion` | 306 | WAV path, hashes the converted MP3 |

Hook inside the existing `with self._song_repo.write_connection("ingest") as conn:` block,
after `new_id = self._song_repo.insert(song, conn)` - the SourceID must exist first.

Must run **after** `_repair_staged_audio()`, for the same reason hashing does: a Xing repair
re-muxes the frames and changes the audio the fingerprint is computed from.

Direct repo write, NOT `MutationCoordinator` - same precedent as the rest of ingestion.

### 6. PyInstaller

Nothing to do. `ffmpeg/` is gitignored and provisioned as a runtime sibling folder (like
`sqldb/`, `json/`, `temp/`) - the PyInstaller recipe does not bundle `ffmpeg.exe`, so there
is no bundling step to extend. `fpcalc.exe` already sits in `ffmpeg/` next to `ffmpeg.exe`
and `FPCALC_PATH` resolves exactly parallel to `FFMPEG_PATH`. A build machine setting up
`ffmpeg/` just needs fpcalc in it (noted in the exe-build recipe).

### Not in Part 1

No comparison, no scoring, no UI, no API. Fingerprints accumulate silently for newly
ingested songs and nothing reads them yet. Backfill of the existing library is a separate
`tools/` script - and note that until it runs, comparison can only ever see songs ingested
after this lands.

### Still needs a design pass before it can be built

- **Part 2B (fuzzy name matching)** is a sketch, not a spec. No algorithm, threshold,
  normalisation rule, or SQL-vs-Python decision is pinned. It must also be reconciled with
  what already exists: the `MediaName_Search` column on `MediaSources`, the exact-match
  `find_duplicate_groups` in `song_repository.py`, and the diacritic handling in
  `docs/todo/identity_normalization_gap.md`. Do not start 2B from this document alone.
- **Part 3** integration remains open by design (options A/B/C below).

Part 2A, by contrast, is buildable from this document as written - it is a pure module and
every pin is stated.

## Problem

Songs 1006 and 1011 are the same recording (`Mladen Burnac - Moja Pozega`) but different
320 kbps encodes. `AudioHash` is a SHA256 of the raw MPEG frame bytes, so it only ever
matches byte-identical files - any re-encode, re-mux, or LAME-header rewrite produces a
different hash. Hash dedup at ingest misses these entirely.

We want to catch "same recording, different file" and, more loosely, "same song, different
version" (radio edit, remaster, instrumental) - as an advisory signal a human confirms,
never an automatic merge or reject.

## What was tested (2026-09-09)

Chromaprint (`fpcalc`) fingerprints, scored as `1 - popcount(a XOR b) / (32 * overlap)`
after a best-offset alignment slide:

| Case | Score |
|---|---|
| 1006 vs 1011 - same recording, different encode | 0.98 |
| Instrumental vs vocal, same backing track (Duane Face 606/607) | 0.81 |
| Nabucco "a" vs "b" (Gerhardt, byte sizes identical) - literal dupe in OnAir library | 1.00 |
| Nessun dorma: Bocelli / 3 Tenors / Pavarotti - same aria, different performances | 0.55 |
| Eine Kleine Nachtmusik: full vs 1st-movement-only | 0.58 |
| The Swan: Yo-Yo Ma vs Ana Rucner | 0.55 |
| Same performer, different composition (Ana Rucner cello set) | 0.57-0.60 |
| Unrelated tracks | 0.51-0.53 |

Conclusions:

- **Different performances of the same work are indistinguishable from unrelated tracks**
  (~0.55). Chromaprint keys off the acoustic waveform, not the score. Classical/instrumental
  is NOT a false-positive source for a local threshold. The Facebook/Content-ID false
  positives the station has seen are a Content-ID tuning problem (aggressive recall, huge
  catalog), not inherited by a local cutoff.
- Three bands: **~0.97+** same recording; **~0.75-0.95** same song, real musical difference
  (instrumental, edit, remix - human decides); **~0.5** unrelated (bit-noise floor).
- `fpcalc -length N` is a cap, not a window. A 150s track is fingerprinted end-to-end; the
  cap only truncates tracks longer than N. 180s covers all radio pop and most arias; only
  long classical / extended mixes lose their tail.
- Fingerprint is ~7.9 items/sec (~1400 uint32 at 180s), ~6 KB/song raw.

`fpcalc.exe` is currently sitting in `ffmpeg/` for the experiments. Scratch scripts in the
session scratchpad.

## Cost at scale

One new song vs a 50k library, done properly (numpy XOR/bit-count, bounded offset
search, duration +-3s pre-filter): ~1-2s per file (fpcalc decode ~0.5s + scan ~0.5-1s).
NOTE - both figures here were superseded on 2026-09-10. The +-30 frame bound silently
drops true matches whose lead-in differs by more than ~3.8s, and the +-3s duration
pre-filter discards pairs before they are ever scored. Settled values: **+-120 frame offset
window, +-16s duration pre-filter**; budget **~2-4s per file**, not ~1-2s. See "The real
constraint is the offset bound" and "Pins settled" below. A naive pure-Python full-length offset slide is 30-60+ min - not optional to
optimise. A 20-song batch drop = ~40s of added wait if done inline at ingest -> **do not
scan at ingest**.

Library-wide all-pairs sweep: 50k^2/2 ~= 1.25B pairs, ~17h naive. Needs duration bucketing
(~tens of minutes, overnight job) or an inverted index on fingerprint sub-blocks (how
AcoustID's server does it). Separate project.

## Plan

Superseded in places by "Design decisions (2026-09-10)" below.

### Part 1 - fingerprint storage (small, no user-visible effect)

- Bundle `fpcalc.exe` in the PyInstaller spec for `gosling-server.exe`; path as a named
  constant in `src/engine/config.py` (invariant 7).
- New table `AudioFingerprints(SourceID, Fingerprint BLOB, DurationS, LengthCap,
  ComputedStatus, CreatedAt)` + its own repository. SQL/CRUD stays in the repo (invariant 2). Separate table so hydration
  never drags 6 KB/song into list/search reads.
- `src/utils/audio_fingerprint.py` next to `audio_hash.py`: shells `fpcalc -raw -length 180`,
  returns the raw uint32 array. fpcalc failure -> log, store nothing, caller continues.
- Compute + store. Ingestion already writes directly via `song_repo` (not the coordinator);
  post-ingest audio-fingerprint maintenance has precedent in `update_audio_fingerprint`
  (used by Xing repair). Mirror that - a repo update method, NOT MutationCoordinator.
  Whether it runs synchronously in the ingest path or as a trivial deferred step is a Part 3
  detail; Part 1 can just do it inline after the Xing repair + hash step since there is no
  comparison yet.
- Storage format: raw uint32 array packed as a blob, explicit little-endian (compare-ready
  later). Not the compact chromaprint base64.
- **The stored fingerprint is untrimmed.** Lead-in trimming was tested and rejected - see
  "Lead-in silence trim - tested and REJECTED" below. Nothing is normalised before
  fingerprinting; alignment is handled entirely by the offset window in 2A.
- Decisions locked: 180s length cap (confirmed AcoustID-compatible, see the MusicBrainz
  section); raw uint32 little-endian blob; no trim.

### Part 2A - acoustic comparison module (standalone, pure)

- `score(fp_a, fp_b) -> float` - numpy XOR/bit-count with a bounded offset search.
- `find_matches(fp, candidates, threshold) -> [(song_id, score)]` - duration pre-filter +
  scan.
- No DB writes, no ingest changes. Unit-tested against the real files above (0.98 / 0.81 /
  1.00 / 0.55).
- Pins: offset bound **+-120 frames (~15s)** - +-30 fails silently, +-60 is the minimum,
  and +-120 is what replaces the rejected trim for long lead-ins; threshold value(s);
  pre-filter width (>= the offset window in seconds, so **+-16s** - a narrow duration
  pre-filter silently cancels the window); minimum comparable duration (~30s). Tunable here
  in isolation.
  Consider two bands eventually (0.97+ "same recording, pick better bitrate" vs 0.75-0.95
  "related, human decides"); MVP can be one.

### Part 2B - fuzzy name/metadata check (standalone)

- Token-set / edit-distance on title + performer. Cheaper than acoustic, different
  false-positive profile (name collisions are common and meaningless on their own).
- Extends the existing exact-match `find_duplicate_groups` in `song_repository.py`; closes
  the "fuzzy dupe report wanted before Jazler import" backlog item.
- Value is as a cross-signal: acoustic 0.8 AND a fuzzy name match = strong dupe call;
  either alone is weak.

### Temporary "check dupes" button (test harness for Part 2)

- Read-only `POST /api/v1/songs/{id}/find-duplicates` - runs 2A + 2B against the DB, returns
  matches with scores, writes nothing. No invariant surface.
- Button on the song detail view. Lets the threshold be tuned on live data.
- Removed or absorbed in Part 3. Acknowledged low value on its own (you want to know before
  you edit, not on demand).

### Part 3 - integration (the hard part, deferred)

Open decision: when the scan runs and whether its result is persisted. Fingerprint storage
itself is settled either way (re-decoding per view is worse than storing).

- **A. Lazy, unstored.** Scan 1-vs-N when a song is opened, show, discard. No infra, always
  fresh; 1-2s per view, recomputed every visit, unopened songs never checked.
- **B. Eager, stored.** Background worker fingerprints + scans each ingested song, writes
  match rows. Instant detail-view reads, every song checked once; needs background-task
  infrastructure (first of its kind in the engine - queue table + polling thread, or a
  periodic job). Sequential processing makes the 1006/1011 case self-resolve: the later
  song scans against all existing and finds the earlier.
- **C. Hybrid - lazy trigger, stored result, watermark.** On open, check the links table; if
  last scanned against "max song id N" and library is now N+k, scan the k new ones and
  update. No worker; first view pays ~1-2s, later views instant; stays fresh incrementally.
  The scan-and-write runs as a real post-response side effect, not inline in hydration
  (invariant 4).

C is likely the sweet spot if avoiding background-task infra. Benefits from 2A being tuned
first.

- Result storage (B/C): match rows, one ingest can match several existing songs.
  REVISED - see "Storage shape" below: rows are double-written rather than displayed
  bidirectionally from one row, there is one row per *pair* rather than per signal kind
  (a pair matched by both acoustic and fuzzy-name gets one row with a score per signal,
  not two rows), and the review verdict lives in a separate table.
- Read path: song *detail* hydration gains a `possible_duplicates: [{song_id, title, score}]`
  field. List/search unchanged.
- A fingerprint hit is always a **new ingest** - it never triggers the hash-style
  ghost/CONFLICT reactivate prompt, even when the match is a soft-deleted song. It just
  records the link.
- MVP is advisory only: UI shows it, human clicks through, nothing auto-merges or
  auto-rejects.

## Backfill

Deferred. A `tools/` script pointed at rows with no fingerprint. Standalone, low-risk, but
re-reads every file off the network drive (many minutes) - a separate run, not part of the
Part 1 change. Until it runs, comparison only sees songs ingested after Part 1 ships (incl.
the Nabucco dupe already in the library - invisible until backfilled or swept).

## Design decisions (2026-09-10)

Settled in conversation. These supersede the Plan section above where they conflict.

### Nothing is ever auto-decided

No auto-merge, no auto-reject, no auto-delete - and also **no auto-dismiss and no
auto-hide**. A 1.00 score is not pre-marked reviewed. A song with 40 matches is not
silently suppressed. Both of those are decisions made without a human; they just hide in
places that do not look like decisions. Surface them instead (including "40 matches,
probably a degenerate fingerprint") and let a human act once, explicitly.

Consequence worth holding onto: **the score's only job is ordering and surfacing.** It
decides what appears and in what order, never what happens to a file. That makes threshold
tuning low-stakes - a wrong cutoff produces noise or a miss, never a wrong action on a
recording. Ship a deliberately loose cutoff, watch it on live data, tighten later. There is
no window in which a bad number costs anything.

### Derived data vs human judgment - separate tables

- Fingerprint: derived, recomputable from the file.
- Match scores: derived, recomputable from fingerprints. Disposable.
- **Review verdict: not derived. Irreplaceable** - losing it means a human re-listens.

So verdicts live in their own table, never as a column on a match row. The test: you will
retune the threshold and want to wipe every score and re-sweep the library. `DELETE FROM
matches` has to stay a boring, safe operation forever. If verdicts ride on those rows, the
re-sweep destroys human work and you find out afterwards.

Corollary: a dismissed pair stays dismissed even if a retune drops it below threshold and
it stops being a match at all. The verdict outlives the evidence.

### Storage shape - double-written matches, canonical verdicts

- **Match rows are double-written.** 1011 gets a row pointing at 1006, and 1006 gets one
  pointing at 1011. Reads stay dumb: `WHERE SourceID = ?`, one index, no OR, no min/max
  juggling and no "did I put it in the left or the right column" thinking at every call
  site. That is the query that gets written a hundred times.
- Desync is tolerable here *precisely because the rows are derived*. The usual objection to
  double-writing only bites when the rows carry state you cannot regenerate. Repair is
  "rebuild from fingerprints" - a script that has to exist anyway for retuning. Write both
  rows in one transaction; a crash mid-scan is a repair job, not corruption.
- **Verdicts are a single canonical row**, keyed on the ordered pair (min, max) with a real
  UNIQUE index - a constraint, not a convention. Dismissing from 1006's view writes one row
  and 1011's view sees it immediately. The desync bug is designed out rather than guarded
  against.
- Each match row carries the canonical pair key as columns alongside its own direction, so
  the join to verdicts is plain two-column equality. No min()/max() in queries, no chance of
  computing the key differently in two places. Costs two integers per row.

### Verdict grain is the pair, not the song

"Song 1006 is reviewed" rots the moment the library grows - tomorrow's ingest of a third
copy is silently suppressed because 1006 is already "done". "1006 and 1011 are the same
recording" is true forever, regardless of what else arrives.

There *is* a legitimate song-level thing, but it is a **watermark**, not a verdict: "this
song's match list has been fully triaged as of library position N". That is what drives a
UI badge ("3 unreviewed possible duplicates"). Both exist and they answer different
questions.

### Three state axes, kept separate

Collapsing any two of these produces a bug.

1. **Computed** - does this song have a fingerprint? Tri-state, not null/not-null:
   *never attempted* vs *attempted and fpcalc failed*. Collapse those and the backfill
   script re-reads the same broken file off the network drive on every run, forever.
2. **Scanned** - what has this song been compared against? Stored independently, never
   inferred from the presence of match rows. Otherwise "scanned, zero matches, clean" is
   indistinguishable from "never scanned", and clean songs get rescanned forever.
3. **Reviewed** - the human verdict, per pair.

### Verdict vocabulary - richer than yes/no

Four conclusions a human can reach, two of which look alike but are opposite facts:

- **Same recording, dealt with** (merged, or one deleted).
- **Same recording, keeping both deliberately** - one is the on-air master, one a better
  encode.
- **Genuinely related but different** - instrumental vs vocal, radio edit vs album version
  (the 0.81 case). This is real station knowledge, not a dismissal: it is exactly what you
  want surfaced at scheduling time so the radio edit and the album version do not play
  twenty minutes apart. That relationship graph is a separate feature, but the data falls
  out of this one for free if the vocabulary allows it.
- **False positive, unrelated** - threshold-tuning data and nothing else.

Plus a fifth state that is not a verdict: **seen, undecided.** Without it, a user who opens
a song, sees a match and is not sure yet has no honest move that clears the badge. They
either live with a permanent nag or dismiss falsely - and a false "unrelated" is worse than
no verdict at all, because it is wrong data wearing the costume of human judgment.

### Which writes go through the mutator

- **Machine-generated match rows**: ingest-shaped bulk derived data -> direct repo write,
  same precedent as ingestion.
- **Human verdicts**: user intent -> `MutationCoordinator` (invariant 1). Auditable,
  undoable, visible in the change log.

Pin this now. It is exactly the kind of thing that gets done wrong later and is annoying to
unwind.

### Known sharp edges

- **Hub songs.** Station idents, jingle beds, stings, near-silence - short generic audio
  will match dozens of things. A song with 40 matches is not 40 duplicates, it is a
  degenerate fingerprint. Most likely source of "this feature is annoying, turn it off".
  Decide early whether that is capped, flagged, or tolerated - but per the rule above, not
  auto-hidden.
- **Re-ingest orphans verdicts.** Delete and re-ingest produces a new SourceID, so every
  verdict about that song is orphaned and the user re-reviews. Probably correct behaviour;
  should be a decision rather than a discovery.
- **Pair identity vs a Recording entity.** Keying verdicts on SourceID pairs is *why*
  re-ingest loses history. "These files are the same recording" is literally what a verdict
  asserts - a second piece of evidence for the missing Recording rung in the file-centric
  core. Not a blocker, but this feature is quietly asking for that entity.
- **Nabucco / hash gap - CHECKED 2026-09-10, mostly resolved.** Neither copy is in gosling
  (`MediaSources` has zero rows matching "nabucco"), and only one copy is reachable on `Z:`,
  so the pair is OnAir-only and yesterday's a/b files are no longer on disk. The specific
  pair cannot be re-examined.
  The load-bearing claim behind it was tested instead and **holds**: `calculate_audio_hash`
  is genuinely tag-invariant. Same file with short tags / bloated tags / tags stripped gave
  byte sizes 11,930,131 and 11,925,419 but a single identical hash. Ingest would reject all
  of them as duplicates. So "the hash already covers exact duplicates" is verified for the
  tag-difference case, which was the plausible gap.
  What stays unknown is only whether yesterday's a/b were byte-identical audio (hash catches
  them too) or subtly different frames at coincidentally equal size (hash misses, fingerprint
  scored 1.00). Either way the fingerprint catches it, so this no longer affects scoping.

## Jazler import - why this is a precondition, not a companion

Hash dedup at ingest does not merely deduplicate; it **silently freezes an arbitrary
choice**. Arrival order has no relationship to which copy is better - bitrate, metadata
completeness, truncation, filing state and on-air history are all uncorrelated with who got
there first. And the moment a candidate is rejected the evidence is gone, so the decision
can never be revisited.

What a mass import actually wants is not "reject duplicate" but "record that a second
candidate existed, keep its metadata, flag the pair, decide later". That is a **merge
candidate** - a pair with evidence awaiting a verdict - which is the same structure this
whole document describes.

Importing without fingerprints has two failure modes, and the second is worse:

- **Byte-identical** -> rejected, arbitrary winner, candidate metadata discarded. At least
  visible, because rejections get reported.
- **Re-encode or downscale** -> the hash misses entirely and both are admitted as separate
  songs. The library silently doubles with no signal at all.

The second population is likely large: years of accumulated library means plenty of "same
recording, 128 kbps rip from 2009" sitting next to a later 320 acquisition. Nothing will
ever connect them unless the fingerprint exists at import time.

This also raises the priority of **backfill** (deferred above). The existing library needs
fingerprints *before* the import runs, or only new-against-new can ever match.

### Scale vs "nothing auto-decided"

These are in genuine tension: per-pair human review across thousands of merge candidates is
not going to happen.

The resolution is that a human choosing a **policy for a named batch** - "for the Jazler
import, prefer higher bitrate, prefer the richer metadata source, queue anything where
those two disagree" - is still a human decision, just applied at scale. That is
meaningfully different from the system defaulting to arrival order, which is what happens
today. The principle being protected is "no decision gets made without someone choosing
it", not "no decision gets applied to more than one row at a time".

What stays manual is the disagreements - where the higher-bitrate copy has the worse
metadata. Those are the interesting cases and there will be far fewer of them.

### Downscale robustness - TESTED 2026-09-10

Source: `Z:\Songs\Cro\Domoljubne\Mladen Burnac - Moja Pozega.mp3` (song 1006, 9.0 MB,
236.8s, 1432 fingerprint items at the 180s cap). Transcoded with the bundled `ffmpeg.exe`,
fingerprinted with `fpcalc -raw -length 180`, scored with a +-30 frame offset slide unless
noted. Song 1011's staging file no longer exists, so the original/downscale pairs stand in
for it.

**Bitrate reduction is a non-issue.** Every encode stayed inside the "same recording" band:

| Variant | Size | Score |
|---|---|---|
| mp3 320 re-encode | 9.0 MB | 0.9994 |
| mp3 192 CBR stereo | 5.4 MB | 0.9972 |
| mp3 128 CBR stereo | 3.6 MB | 0.9932 |
| mp3 96 CBR stereo | 2.7 MB | 0.9893 |
| mp3 64 CBR stereo | 1.8 MB | 0.9857 |
| mp3 128 mono | 3.6 MB | 0.9984 |
| mp3 64 mono 22 kHz | 1.8 MB | 0.9945 |
| mp3 32 mono 22 kHz | 0.9 MB | 0.9806 |

Even a 32 kbps mono 22 kHz encode - a tenth the size - scores 0.98. The mechanism holds:
chromaprint downmixes to mono and resamples to ~11 kHz before it computes anything, so it
never looks at the spectrum that lossy encoding destroys. Mono encodes score *higher* than
stereo at the same bitrate (0.9984 vs 0.9932 at 128k) because every bit went into the one
channel the fingerprint actually reads.

**No threshold change needed for the Jazler import on bitrate grounds.** The 0.97+ "same
recording" band survives intact down to 32 kbps.

Level changes are also a non-issue: +6 dB, -6 dB and `dynaudnorm` all scored 0.995+.

### The real constraint is the offset bound, not the fingerprint

The doc's cost estimate assumed an offset search "bounded to ~+-30 frames". At ~7.9
items/sec that is only **+-3.8 seconds**, and it is the binding limit:

| Head difference | Score @ bound 30 | Score @ bound 60+ |
|---|---|---|
| 0.5s silence prepended | 0.9935 (off -4) | - |
| 2.0s silence prepended | 0.9767 (off -16) | - |
| 1.0s trimmed | 0.9880 (off 8) | - |
| **5.0s trimmed** | **0.5545 (off 30, clamped)** | **0.9421 (off 40)** |

A 5-second head difference drops a true match to 0.55 - the unrelated noise floor -
purely because the search cannot reach the alignment. Widening to +-60 recovers it to 0.94
at offset 40; +-120 and +-240 find nothing further, so 40 is the true alignment.

This is the single most important tuning parameter and it is a **recall cliff, not a
gradient** - a missed alignment looks exactly like an unrelated track, so it fails silently
and invisibly. Differing lead-in silence is extremely common between a station rip and a
purchased copy.

- Minimum bound: **+-60 frames (~7.6s)**. **+-120 (~15s) is the settled value** - it is
  what covers long lead-ins now that the trim is rejected.
- Cost is linear in the bound. +-120 is 4x the alignments of +-30, pushing the scan half
  from ~0.5-1s toward ~2-4s per song. Acceptable under plan C (first view pays, later
  views instant); another reason not to scan at ingest.
- Cheaper refinement available later: the stored `DurationS` delta predicts a head trim's
  offset, so the search can be seeded near `(dur_a - dur_b) * 7.9` and stay narrow. It does
  not distinguish a head trim from a tail trim, so it is a seed, not a replacement for a
  real window.


### Lead-in silence trim - tested and REJECTED (2026-09-10)

The obvious fix for lead-in misalignment is to normalise the start: trim leading silence
before fingerprinting, so both copies begin at the same musical moment.
`ffmpeg -af silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB`.

**It works, exactly, for the case it addresses.** Every lead-in silence difference collapses
to a perfect match at offset 0:

| Case | Duration | Score | Offset |
|---|---|---|---|
| trimmed reference | 236.23s | 1.0000 | 0 |
| 0.5s silence prepended, trimmed | 236.23s | 1.0000 | 0 |
| 2.0s silence prepended, trimmed | 236.23s | 1.0000 | 0 |
| 5.0s silence prepended, trimmed | 236.23s | 1.0000 | 0 |

That is a genuine improvement over relying on the offset slide, which only got the 2s case
to 0.9767. Worth adopting.

**But it cannot replace the offset window.** Three failure modes, all of which land back on
the window:

*1. Content trims are untouched.* Cutting 5s of actual music off the head still needs
offset 36 (score 0.9629). No silence detector recovers audio that was removed.

*2. On a fade-in, level couples into the trim point.* The moment the signal crosses -50 dB
depends on how loud the copy is, so a quieter copy trims later. Measured on a 4s fade-in:

| Case | Duration | Score | Offset |
|---|---|---|---|
| fade-in, 0 dB (ref) | 235.83s | 1.0000 | 0 |
| fade-in, -6 dB | 235.39s | 0.9265 | 4 |
| fade-in, -12 dB | 234.42s | 0.9552 | 11 |
| fade-in, +6 dB | 236.12s | 0.9543 | -2 |

Note this is a *regression* on material that was already fine. Without trimming, level
differences were harmless (+-6 dB scored 0.995+ at offset 0). With trimming, a level
difference on fade-in material becomes an alignment difference worth up to ~11 frames
(~1.4s), and the residual sub-frame misalignment drags the score from 1.00 down to ~0.93.
Still comfortably a match, but the trim made this pair worse, not better.

*3. A noisy source defeats the trim silently.* If the lead-in hiss sits above the
threshold, nothing is trimmed and the pair reverts to the untrimmed case - with no
indication that normalisation did not happen:

| Lead-in noise (2s lead-in) | Duration | Score | Offset |
|---|---|---|---|
| hiss -54 dB (below threshold) | 236.23s | 0.8727 | 0 |
| hiss -46 dB (above threshold) | 238.81s | 0.8728 | -21 |
| hiss -40 dB (above threshold) | 238.81s | 0.8728 | -21 |
| hiss -30 dB (above threshold) | 238.81s | 0.8727 | -21 |

A 2s lead-in reverts to offset -21, which a +-30 window still catches. A 5s lead-in on the
same noisy source would revert to ~-40 and clamp to the noise floor. Exactly the silent
recall cliff the trim was supposed to remove. (Separately: broadband hiss at any level
costs ~0.13 of score outright - noisy rips match at ~0.87 rather than ~0.99, which is worth
knowing when picking a threshold.)

**Conclusion: REJECTED. Do not trim; widen the window instead.**

Initially adopted, then reversed the same day once the worst cases were compared directly:

| Case | Untrimmed | Trimmed |
|---|---|---|
| 0.5s lead-in | 0.9935 | 1.0000 |
| 2s lead-in | 0.9767 | 1.0000 |
| 5s content trim | 0.9421 | 0.9629 |
| +-6 dB level | 0.9949 | - |
| fade-in + -6 dB | ~0.995 | **0.9265** |

The trim's worst case (0.9265) is *worse* than untrimmed's worst case (0.9421). It improves
cases that were already comfortable and degrades one that was comfortable before. Given the
0.97 line is not a truth line anyway (see band blur), moving a clean case from 0.98 to 0.94
costs nothing operationally.

What actually fixed the recall cliff was the offset window. The trim was polish, and it
carried a stored parameter, an ordering constraint, a fade-in regression, a silent
failure mode on noisy sources, and AcoustID incompatibility.

The one case where the trim is genuinely load-bearing is lead-in silence longer than the
window. The honest answer there is to spend on window width instead - **+-120 frames covers
15s lead-ins**, roughly doubles the scan half (~2-4s/song, fine under plan C), and is a dial
with no silent failure mode. The trim's answer to a noisy 10s lead-in is to quietly do
nothing.

**Can the trimmed form be derived from a stored untrimmed one?** Only approximately. Tested
by dropping the first N items of an untrimmed fingerprint and comparing against a genuinely
trimmed one:

| Lead-in | Bit-identical items | Score vs true trimmed |
|---|---|---|
| 1s | 0.0000 | 0.9692 |
| 2s | 0.0000 | 0.9804 |
| 3s | 0.0000 | 0.9902 |
| 5s | 0.0000 | 0.9845 |

Not one item matches exactly. Chromaprint's frames are computed on overlapping windows
anchored to the start of the decoded stream, so trimming re-anchors every window boundary -
same content, different numbers. The derivation costs ~0.02-0.03 of fidelity, which is
about what simply comparing two untrimmed fingerprints through the offset window costs
anyway (0.9767 at a 2s lead-in). So deriving is work for no gain, and the reverse direction
(trimmed -> untrimmed) is impossible outright. **One untrimmed blob, no derivation code.**

### Known blind spot: speed and pitch changes

| Change | Score |
|---|---|
| +0.5% | 0.7947 |
| +1% | 0.7017 |
| +2% | 0.6291 |
| +4% (PAL speed-up) | 0.5848 |
| -4% | 0.5854 |

Chromaprint is **not** tempo-invariant. Half a percent already drops out of the "same
recording" band; 4% is at the noise floor and indistinguishable from an unrelated track.
No threshold fixes it - a tempo-invariant match is a different algorithm.

In practice this matters much less than the numbers suggest, because the deliberate cases
arrive labelled. A nightcore or sped-up edit says so in its title, so **the fuzzy name
check (2B) catches precisely what the acoustic check (2A) is blind to.** That is a stronger
argument for the two-signal design than the cross-signal one already noted: the signals
have complementary *blind spots*, not just complementary false-positive profiles. Acoustic
is blind to tempo but immune to name collisions; fuzzy name is the reverse.

The correct outcome for such a pair is also not a merge - it is "genuinely related but
different", the third verdict. So a 0.58 acoustic score on a nightcore pair is not a miss
at all: the pair surfaces by name, gets the right verdict, and both files stay.

What is left as a genuine blind spot is the *unlabelled* tempo difference - a vinyl or tape
rip running slightly off speed, PAL speed-up on a soundtrack, a copy nudged faster to fit a
slot. Rare in a CD/digital-sourced pop library. Not worth solving; worth knowing, so a miss
of this kind is not read as a bug in the implementation.

Scratch scripts: `downscale_test.py`, `realworld_test.py` in the session scratchpad.

### Pins settled by the 2026-09-10 measurements

Things in Parts 1 and 2A that the day's results changed or contradicted. All are
decisions to lock before implementation, not open questions.

**1. The duration pre-filter must be at least as wide as the offset window.**

The plan specifies a `duration +-3s` pre-filter to cut the candidate set. That contradicts
the offset window: the 5s content-trim case has a duration delta of ~5s
(236.77s -> 231.81s), so a +-3s pre-filter discards it *before it is ever scored*. The
window would be widened at 2-4x the scan cost and gain nothing, because the pre-filter
already threw the pair away.

- Pre-filter width >= offset window in seconds. With the window at **+-120 frames (~15s)**
  the pre-filter must be **+-16s**.
- Cost: a wider pre-filter admits more candidates per scan. This is the price of dropping
  the trim, and it is the right trade - the pre-filter is a tunable dial, whereas the trim
  failed silently.
- No trimmed duration to store. Since nothing is trimmed, there is one duration, and
  lead-in silence contributes to the delta like any other content. That is what the +-16s
  width is covering.

**2. Minimum duration floor - do not compare short audio.**

Below ~20s there are not enough fingerprint items to run a +-60 offset window at all:

| Clip length | Fingerprint items |
|---|---|
| 3s | 3 |
| 5s | 19 |
| 8s | 43 |
| 10s | 59 |
| 15s | 100 |
| 20s | 140 |
| 30s | 221 |

The scorer needs a minimum overlap (50 items in the scratch implementation) to produce a
meaningful number, so a 3s ident cannot be aligned against anything, and short generic
audio is the hub-song problem anyway - idents, stings and jingle beds match everything.

**Set a floor of ~30s and do not compare below it.** This resolves the hub-song risk noted
under "Known sharp edges" by construction rather than by capping or suppressing results,
which keeps the "nothing auto-decided" rule intact - nothing is being hidden, a whole class
of audio is simply out of scope for acoustic matching. Fuzzy name matching (2B) still
applies to short audio and is the better signal for it.

**3. "Not comparable" is a third state, not a score of zero.**

The minimum-overlap guard must return *not comparable*, never 0.0 or a low score. A short
track, a missing fingerprint and a genuinely unrelated track would otherwise be
indistinguishable at the call site, and the first two would render as confident
"unrelated" - the same class of bug as collapsing the computed tri-state, and it would look
like the feature working correctly.

**4. Fix the blob byte order explicitly.**

The stored format is a packed uint32 array. Pack with an explicit little-endian layout
rather than native order. Everything in play is x86 today, but the fingerprint outlives the
process that wrote it and a native-order assumption is a silent comparison failure the day
it is wrong - and it would look exactly like an unrelated track, same as every other
failure mode in this document.

## AcoustID / MusicBrainz - verified 2026-09-10, future feature

Not part of Parts 1-3. Recorded because it independently justifies fingerprint storage and
because it constrains one Part 1 decision (the length cap).

### Chromaprint is not AcoustID

- **Chromaprint** is the algorithm. Local, offline, deterministic. What `fpcalc` computes
  and what this whole document is about.
- **AcoustID** is a web service and database built on top of it. Submit a fingerprint plus
  a duration; get back AcoustID track IDs and the MusicBrainz recordings people have linked
  to them.

The matching math for a catalogue lookup is **not ours to write**. Their server runs an
inverted index over fingerprint sub-blocks to shortlist candidates, then precise alignment
on the shortlist. Our side is: fingerprint -> HTTP POST -> parse candidates. (That two-stage
index technique is also the answer for a library-wide all-pairs sweep, if that is ever
built - borrow the method, not the service.)

### Why text search cannot do this job

The auto-lookup feature cannot be built on artist + title:

- It is circular. Good metadata is needed to search for good metadata, and the lookup exists
  precisely because the metadata is bad. Song 1009 has `MediaName = "FALLEN ANGEL"` and **no
  artist at all** - text search has nothing to work with.
- Artist + title identifies a *song*, not a *recording*. Album version, single edit,
  remaster, live take are separate MusicBrainz recordings sharing artist and title. Text
  cannot separate them; the fingerprint identifies which one is actually in the file.

Fingerprint is the key; text is the fallback for files whose fingerprint has no links.

### Verified end to end (song 1009)

Our own `fpcalc` fingerprint, submitted to `api.acoustid.org/v2/lookup`:

```
1009 (MediaName "FALLEN ANGEL", no artist set)
  -> fpcalc fingerprint (compact base64, 5300 chars at -length 180)
  -> AcoustID  d3451810-96b9-4b3d-a24c-517b122b2715   score 0.99911
  -> MB recording      04b2b3fe-fbfb-4c90-aa83-d2c83557fcee  "FALLEN ANGEL"
  -> MB artist         779351de-0da5-4943-928b-495a3c40e8c0  "JENNIE"
  -> MB release group  cda1edf6-2f05-42d4-9c69-cfafef0907b9  "Fallen Angel" (EP)
```

One request returns the whole tree with `meta=recordings releasegroups` (space-separated;
`+` is rejected). A file with no artist produced a precise recording, artist and release
group.

**This settles the length cap.** `-length 180` and the `fpcalc` default of 120 returned the
identical AcoustID at the identical score, so 180s is AcoustID-compatible and Part 1 can
keep it. This was an open compatibility risk that would have surfaced as "no results"
rather than an error.

### Consequences for Part 1

- The stored fingerprint must be **untrimmed** to stay AcoustID-compatible. Already the
  decision for local-matching reasons; this is a second, independent reason.
- No AcoustID-specific storage is needed now. The submission form is the compact base64,
  which `fpcalc` emits directly, so a future lookup can simply re-run `fpcalc`. Storing raw
  uint32 preserves the option either way.
- **No second fingerprint field.** One untrimmed blob serves both uses.

### Open for the future feature, not now

- **A lookup returns candidates, not an answer.** AcoustID-to-MusicBrainz is many-to-many:
  expect 0 links (fingerprint known, nobody attached a recording), 1 link (song 1009 - the
  clean case), or N links (mis-submissions, or genuinely distinct recordings linked
  together). A single `MusicBrainzRecordingID` column is therefore the wrong shape for the
  same reason a `Reviewed` boolean was - it presumes an answer where there is a candidate
  list plus a human decision. Same structure as the dedup verdict split.
- ID columns (AcoustID track ID, MB recording MBID) cost nothing to add now and nothing to
  add later. Skipped for now on plain YAGNI.
- **Credentials - how to get them again.** Log in at acoustid.org with the Google account,
  then:
  - **Application key** - acoustid.org/my-applications (create one if the list is empty).
    Used as `client=` for *lookups*. This is the one the auto-lookup feature needs.
  - **User key** - acoustid.org/api-key. Used as `user=` for *submitting* new fingerprints
    back to AcoustID. Not needed for lookups. Easily confused with the above; submitting
    the wrong one returns `{"error": {"code": 4, "message": "invalid API key"}}` as an
    HTTP 400.

  Keys are not recorded here on purpose - fetch them when the feature is built. Note that
  **`json/settings.json` is tracked in git**, so keys must NOT go there. `.env` and
  `json/secrets.json` are gitignored for this purpose.
- Coverage is user-contributed and uneven. A 2026 K-pop single resolves perfectly; Croatian
  domestic material and the classical shelf are likely thinner. Untested - worth sampling
  the actual library before designing around a hit rate.
