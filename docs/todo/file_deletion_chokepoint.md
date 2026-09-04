# File Deletion Chokepoint

Status: DESIGN ONLY, parked 2026-09-04. Nothing implemented. Discussed at length; this
is the record so the reasoning does not have to be rebuilt.

## The rule (stated by the user, not previously written down anywhere)

**Unless it is a staged file, no file gets deleted without a user action.**

"User action" means an act *about that specific file* — not merely that some user-initiated
operation was running. Staged files are the exception because the app created them; cleaning
up its own scratch is not a decision about the user's data.

This rule overturned a design mid-conversation (auto-deleting the Downloads original on reject,
and setting `delete_file` for in-place rejects). It belongs in `CLAUDE.md` alongside the other
invariants — it is currently unwritten and was rediscovered only by the user objecting.

## Why this came up

Rejecting a song deletes the staging copy and leaves the user's original in Downloads, so the
same files resurface as conflict cards on the next scan. Investigating that surfaced two
separate file-deleters with different guards, and one (`resolve_conflict`) that fabricates a
provenance path. See "Related open bugs" below.

## Current surface: 16 deletion call sites, 7 files

Scratch — the app's own artifacts, no judgment call needed:

- `ingestion_service.py` x5 (staging temps)
- `waveform_service.py` (cache)
- `converter.py` x2 (source WAV after conversion, ffmpeg partial output)
- `audio_repair.py`

May be the user's files:

- `filing_service.py` x2 (`delete_staging_file`, `delete_physical_file`)
- `mutation_coordinator.py` x3
- `ingest.py` x2

## Design

### Rejected: one function with a mode flag

The shape considered first was a single `delete(a, b)` where matching paths means "the user
sent it" and a null second arg means "automatic, must be in `STAGING_DIR`".

The null branch is sound — "target must be inside `STAGING_DIR`" is a property of the path,
checkable, unfakeable, cannot drift.

The matching branch is not. Two parameters of the same type are satisfied by passing the same
variable twice, by accident or by a future session that just wants the call to go through. It
reads as a safeguard but is a convention, and conventions are exactly what got re-derived in
`resolve_conflict`.

### Preferred: two functions, one job each

- `delete_scratch_file(path)` — refuses anything outside `STAGING_DIR`, full stop. Covers 9 of
  the 16 sites with no judgment call. Cannot delete the library even when called wrongly.
- A separately-named function for user-authorized deletion, which does the corroboration
  itself. Greppable by name, so it shows up in a diff instead of hiding in an argument.

### What "user authorized" can actually mean

A human cannot be proven present from inside a function; by then there is only a call stack.
What *is* checkable: the target was corroborated by two independently-sourced values — the path
the UI showed the user, carried on the request, versus the path the DB independently holds. If
they agree, the target was not invented server-side.

That makes enforcement a **location** rather than a flag: non-staged deletion can only be
initiated where a request exists. If the dangerous function requires a value only a request
handler can produce, internal pipelines cannot call it — not because they are forbidden, but
because they have nothing to pass.

### Consequence: `DeleteOriginalFileItem` is under-specified

It carries only `song_id`. The path comes entirely from the DB, so the button that deletes a
user's file sends nothing about *which* file it believes it is deleting — there is no
user-supplied value to corroborate against.

That is why the 2026-09-04 fix bolted an audio-hash check onto that path: the hash stood in for
corroboration the item could not provide. If the item carried the path the user was shown, the
check becomes structural (compare displayed vs. DB, refuse on mismatch) and the hash returns to
being a second line of defence rather than the only one.

This is a change to the mutation item's shape, not a patch. Sketch it before coding.

## Transition ordering (this is the part that makes it safe)

The user's concern was that migrating leaves a period where some calls are guarded and some are
not, which is worse than today because it *feels* covered. That is true only in one ordering.

1. **Write the allowlist test first**, seeded with all 16 existing call sites. It adds no code
   paths and changes no behavior — a snapshot asserting "these and only these". Useful
   immediately: any future session adding an `unlink` must update the list in the diff, where a
   human sees it.
2. Migrate call sites one at a time, each removing one entry from the allowlist.
3. No window exists where the code is less safe than the day before: step 1 is inert, step 2
   only ever replaces a raw call with a guarded one.

Honest limit: this constrains the *surface* — it catches new deletion sites, not someone editing
an existing allowlisted one. It is not a correctness proof.

Precedent for this style of test: `tests/test_lookup_integrity.py`, which is constitutional
rather than behavioural.

## Why a test suite is not the answer on its own

A suite only covers failures someone imagined. The allowlist check is not a prediction — it
answers "how many places in this codebase can delete a file", which is answerable without
imagining anything. Reviewing a diff by file count says nothing about blast radius; grepping the
diff for deletion call sites does.

## Corroborating the origin file's identity (open)

Wanted: before deleting a recorded origin, confirm the file sitting at that path is the one
that was dropped. The drop path only guesses `Downloads/<filename>`, so a same-named unrelated
file can occupy it.

Tried 2026-09-04 and reverted: comparing the origin against the song's `audio_hash`. That hash
is computed from the *stored* file, which for a WAV import is the transcoded MP3 — a WAV and the
MP3 made from it never hash alike, so the guard refused every legitimate delete for converted
files (observed as a 400 on song 998). Xing-header repair on ingest rewrites frames too, so the
same mismatch can occur without any conversion.

Correct shape: capture the origin's own hash at drop time (`StagingOrigins.OriginHash`, set
alongside `OriginPath`) and compare the file against that. Survives conversion and repair,
because it never involves the stored song's bytes. Existing rows have no hash, so the check
must skip rather than block when it is absent.

Scenario pinned as `xfail(strict=True)` in
`tests/test_services/test_cleanup_original.py::test_refuses_a_same_named_but_different_file`,
so it flips to a failure the moment corroboration lands.

## Related open bugs (separate from this design)

- FIXED 2026-09-04. `resolve_conflict` (`ingest.py`) reconstructed the origin path from the *staged* filename:
  `Path(staged_path).name.split("_", 1)[-1]`. After WAV->MP3 conversion the staged file is the
  converted `.mp3`, so it fabricates a `Downloads\....mp3` that never existed, overwriting the
  correct `.wav` origin recorded at drop time. Provenance re-derived from a derivative.
  Fix: carry forward the existing origin record; record nothing when there is none. Do not
  derive. Landed in `8d120e6` (2026-04-21) inside a 19-file commit, alongside the
  `StagingOrigins` table it breaks — never independently reviewed.
- Reject clears the editor panel (`song_actions.js` `clearSongEditorV2()`), so
  `renderDeletedSongView` never renders in the reject flow. Worked around with a post-reject
  toast; the sidebar affordance added to that view is only reachable by opening an
  already-rejected song from a list.

## Logging: what "everything" means (discussed 2026-09-04, not yet enforced)

Standing rule: if it is not in the log file, the logging is not good enough. The log is tuned
for an LLM reader, not a human — reading thousands of lines is cheap for the agent and the
value is high, so verbosity is a feature. `gosling.log` is the first thing to grep on any
runtime problem.

**Two axes, often confused.** Severity (how alarmed the code is) is not significance (whether
the world changed). `GET /songs/filter 200` and `song 998 rejected` are both INFO; only one is
a domain event. So a "human log" cannot be produced by filtering on level — the discriminator
has to be marked at the call site.

**The firehose = entered/exited method.** Mechanical, universal, no judgment call, which is the
point: nobody gets to decide something was not worth logging. Purpose of each half:

- entry — "this was touched", i.e. reachability when tracing a path
- exit — "did this finish the way that was expected", so exits must carry the *outcome*
  (`NOT_FOUND`, `SOFT_DELETED`, `DONE`), not merely that the method returned

An entry with no matching exit is itself the signal that something threw. Hard breaks are
findable by absence — grep for the `->` whose `<-` never came — without knowing in advance what
went wrong.

**The gap entry/exit cannot cover.** A decision made inside a coarse-grained method is invisible,
because no method boundary corresponds to it. This is what cost time on 2026-09-04: the audio-hash
guard compared two hashes and refused, deep inside `coordinator.apply()`, whose exit line covers a
whole mutation. The log showed every method entry and exit and still could not say why the code
turned left.

Narrow rule that follows: **if a branch decides something the method's exit line will not report,
it needs its own line.** Most methods need nothing extra. Refusals always do — a guard that
blocks without saying why is the most expensive silence, because someone is left staring at a UI
error with no trace.

Done 2026-09-04: `/api/v1/mutate` now logs the reason on every 4xx branch before raising
(`mutations.py`). Previously the reason went only to the browser and was lost. Since mutate is
the single write endpoint, this covers all failed writes.

**Possibly the real shape of the "human log".** `ChangeLog` is already the record of what
happened to the library, but it is trigger-based on table writes, so file operations can never
appear in it by construction — moving a file into the library, deleting a user original, staging
cleanup. The one category of irreversible action has no durable record, and in `gosling.log` it
is indistinguishable from a filter query. A single deletion chokepoint is exactly the place that
could write those audit entries.
