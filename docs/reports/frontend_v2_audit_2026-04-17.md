# Songs V2 UI — Audit Report

**Date:** 2026-04-17
**Commits audited:** `690550c`, `28c63ac`, `9c64fcf`, `42719cd`, `f933892`
**Plan:** [docs/plan_songs_v2_ui.md](../plan_songs_v2_ui.md)

---

## Verdict: **FIX-FORWARD, but with scoped rework.**

Revert is not warranted. The core scaffolding (slim-query columns, 3-pane HTML, chip input component, scalar wiring, action sidebar) is present and roughly correct. Nothing is catastrophically broken — the Songs tab should load and the new flow should mostly work.

However, the work is **sloppy in well-defined, enumerable ways**: dead backend fields, Phase 9 cleanup entirely skipped, dual old/new code paths coexisting by DOM sniffing, a drift indicator that was specced but never wired into the one code path that renders drift, and a few subtle state bugs. These are fix-forward items — not architectural mistakes. ~1 focused session should clear the punch list. Reverting means losing 8 phases of work to rewrite the same thing.

**Confidence:** Medium-high. I read the full plan, all 5 commit diffs (stats + key hunks), and the post-commit state of the 4 most critical files ([songs.js](../../src/static/js/dashboard/renderers/songs.js), [song_editor.js](../../src/static/js/dashboard/renderers/song_editor.js), [chip_input.js](../../src/static/js/dashboard/components/chip_input.js), [main.js](../../src/static/js/dashboard/main.js)). I did not run the app.

---

## The headline problems

### 1. Phase 9 (cleanup) was completely skipped

The plan explicitly says: *"Once new UI is wired and working: Remove `renderSongsCards()`, `renderSongDetailComplete()`, `renderSongDetailLoading()`, `renderWorkflowStatus()` from `songs.js`"*.

None of that was done. `songs.js` is **1042 lines** and contains **both** renderers:

- `renderSongRows` — new ([songs.js:505-597](../../src/static/js/dashboard/renderers/songs.js#L505-L597))
- `renderSongsCards` — old, dead-but-live ([songs.js:599-678](../../src/static/js/dashboard/renderers/songs.js#L599-L678))
- `renderSongDetailComplete` — old, dead-but-live ([songs.js:800-1042](../../src/static/js/dashboard/renderers/songs.js#L800-L1042))
- `renderWorkflowStatus` — old, dead-but-live ([songs.js:738-798](../../src/static/js/dashboard/renderers/songs.js#L738-L798))

This matters beyond aesthetics because of (2).

### 2. The new and old paths coexist via DOM sniffing

The renderer branches at runtime on whether `#song-list-panel` exists in the DOM ([songs.js:456-461](../../src/static/js/dashboard/renderers/songs.js#L456-L461), [songs.js:703-707](../../src/static/js/dashboard/renderers/songs.js#L703-L707)):

```js
const songListPanel = document.getElementById("song-list-panel");
if (songListPanel) { renderSongRows(ctx, sorted); }
else { renderSongsCards(ctx, sorted); }
```

[main.js:689](../../src/static/js/dashboard/main.js#L689) does the same with `.classList.contains("active")`. This is a dual-mode runtime switch that should not exist — the plan was a **full replacement**, not a fallback. Every selection, sort, and render path has to evaluate which of two UIs is active. This is where subtle bugs hide.

### 3. The slim query has two dead backend columns

The plan ([lines 57-61](../plan_songs_v2_ui.md#L57-L61)) asked for `has_publisher` and `has_album` on the slim query so list rows could render `PUB` / `ALB` pills directly.

- ✅ Columns added to SQL in 3 places — [song_repository.py:275-276, 345-346, 872-873](../../src/data/song_repository.py#L275)
- ✅ Exposed on `SongSlimView` — [view_models.py:112-113](../../src/models/view_models.py#L112-L113)
- ❌ **Frontend never reads `song.has_publisher` or `song.has_album`** — `grep` for them in `src/static` returns zero hits.

Instead, the list row pills come from `song.review_blockers` ([songs.js:521-522](../../src/static/js/dashboard/renderers/songs.js#L521-L522)), which is a server-side computed field on the view model ([view_models.py:115-127](../../src/models/view_models.py#L115-L127)). This works (the computed property reads `has_publisher`/`has_album` server-side), but it means the flat bool columns were added to the SQL for a design that was abandoned mid-implementation. They should either be used directly (plan-faithful) or removed. Currently they're transmitted over the wire for nothing.

### 4. Drift indicator is half-wired

Plan ([line 116](../plan_songs_v2_ui.md#L116)): *"Each input field label gets a small colored dot when the DB value ≠ the file value."*

- ✅ `wireDriftIndicators()` exists and works — [song_editor.js:181-204](../../src/static/js/dashboard/renderers/song_editor.js#L181-L204)
- ✅ Called from `openSelectedResult` in main.js:698
- ❌ **Not called from `refreshActiveSongV2`** — [main.js:223-233](../../src/static/js/dashboard/main.js#L223-L233). That function re-renders the editor after edits, and drops the file data entirely (it re-fetches catalog only, not `getSongDetail`). So the moment the user edits a scalar, drift dots disappear.
- ❌ **Not called from the splitter `onConfirm`** at [main.js:722-733](../../src/static/js/dashboard/main.js#L722-L733) either.

Drift dots only appear on *first* selection of a song, then vanish on any subsequent render. That's a real bug.

### 5. Editor re-render after edits re-mounts chips unnecessarily

In `wireScalarInputs` ([song_editor.js:134](../../src/static/js/dashboard/renderers/song_editor.js#L134)), the `onUpdated` callback fires with fresh data but does NOT re-render chips. However, in the splitter `onConfirm` callback ([main.js:722-733](../../src/static/js/dashboard/main.js#L722-L733)) and `refreshActiveSongV2` ([main.js:223-233](../../src/static/js/dashboard/main.js#L223-L233)), the code calls `renderSongEditorV2(fresh)` which **blows away the entire DOM** and re-calls `wireScalarInputs` + `wireChipInputs`. This:

- Re-creates every chip input fresh (losing focus, dropdown state, in-flight searches)
- Loses any drift dots (see 4)
- Duplicates `errorEl` divs if re-called without a full innerHTML reset (actually safe here because `renderSongEditorV2` resets `scroll.innerHTML`, but the pattern is fragile)

The chip input component already has `handle.setItems(...)` designed for exactly this. The architectural split isn't being respected.

### 6. `renderActionSidebar` isn't called in the splitter confirm path

[main.js:722-733](../../src/static/js/dashboard/main.js#L722-L733) — after a split, the editor re-renders but the action sidebar does too. Fine. But what's more surprising: in the `wireChipInputs` onUpdated callbacks for credits/tags/publisher/album, the action sidebar **is** re-rendered (main.js:710-713). Consistency ping-pong between re-render paths.

### 7. Typos / small bugs in sidebar code

- [song_editor.js:370](../../src/static/js/dashboard/renderers/song_editor.js#L370): variable named `unreviweBtn` (misspelled). Not a bug, but symptomatic.
- [song_editor.js:371](../../src/static/js/dashboard/renderers/song_editor.js#L371): `title=\"Missing required fields\"` is emitted as a raw escaped string *inside* the `disabled` attribute string. In HTML output this becomes `disabled title="Missing required fields"` which is fine — but it's written that way because of inline string concatenation rather than proper attribute handling. Works, ugly.
- [song_editor.js:394](../../src/static/js/dashboard/renderers/song_editor.js#L394): "Delete Original" button uses `song.original_exists && isInStaging && song.estimated_original_path` — the plan says "shown when original exists" with no staging restriction. Not a functional bug but tightens the plan without saying so.

### 8. `chip_input.js` — `setItems` called after `onAdd` is partially redundant

For example, credits wiring in [song_editor.js:241-244](../../src/static/js/dashboard/renderers/song_editor.js#L241-L244):

```js
onAdd: async (opt) => {
    await addSongCredit(...);
    const fresh = await refresh();   // triggers onUpdated → state.activeSong
    handle.setItems(getItems(fresh));
},
```

`refresh()` calls `onUpdated` which on the `openSelectedResult` path re-renders the whole action sidebar (not the editor — good). But on the splitter/scalar-save paths, the parent calls `renderSongEditorV2` which wipes the chips DOM anyway. So `handle.setItems` here is working against a DOM that will be destroyed moments later. Not broken, just inefficient and indicative of the same not-respecting-the-split problem as #5.

### 9. Plan itself was over-optimistic on a few specifics

Not your fault that the plan was unrealistic, but since you said "even the plan you wrote is bad":

- **Phase 3** promised exposing `tag_delimiter`, `tag_default_category`, `tag_input_format`, `blur_saves_scalars` via the validation-rules endpoint. The code reads `validationRules?.blur_saves_scalars` ([song_editor.js:81](../../src/static/js/dashboard/renderers/song_editor.js#L81)) and `validationRules?.tags` ([song_editor.js:263](../../src/static/js/dashboard/renderers/song_editor.js#L263)) — but I didn't verify the endpoint actually emits those. Worth a 5-minute check.
- **Phase 5** line 97-98 says: *"Render form immediately with catalog data; file data feeds drift indicators; audit history feeds Raw section (deferred — only fetched/shown when Raw section is scrolled into view or expanded)."* Audit lazy-load via `<details>` toggle is implemented ([song_editor.js:430-454](../../src/static/js/dashboard/renderers/song_editor.js#L430-L454)). Good. But the plan says "render immediately with catalog data" — the actual flow at [main.js:691-694](../../src/static/js/dashboard/main.js#L691-L694) awaits BOTH catalog AND file data before rendering. Skipped the progressive render.
- **Phase 6 `getCreateLabel`** — plan didn't specify this hook; the implementation added it. That's fine, but illustrative: the plan wasn't detailed enough to prevent drift.

### 10. What I didn't check

I didn't verify:

- That the new UI actually loads without JS errors (I didn't run the app).
- Whether `filter_sidebar.js` correctly targets `#filter-sidebar` inside `#songs-workspace` (Phase 8). There's a `filter-sidebar-legacy` element at [dashboard.html:128](../../src/templates/dashboard.html#L128) suggesting dual-state here too.
- Whether any tests were added for the new code paths. `tests/test_data/test_filter_slim.py` was touched in commit `690550c` — the backend side is tested. I saw no frontend tests (but this repo may not have any).
- Whether `song_actions.js` still handles all the old action names the new sidebar emits (plan line 161: *"Same 4-state machine, same `data-action` attributes"*). Worth spot-checking.

---

## ADDENDUM — Lost features (added 2026-04-17 morning)

User flagged that the original audit missed functional **regressions**, not just sloppiness. On re-read of the old `renderSongDetailComplete` and album-card rendering in [songs.js:108-313](../../src/static/js/dashboard/renderers/songs.js#L108-L313), and comparing against the new chip-based editor in [song_editor.js](../../src/static/js/dashboard/renderers/song_editor.js), here is what the new UI **cannot do that the old one could**:

### Rename / edit via chip-label click
Old UI: clicking a chip label fired `data-action="open-edit-modal"` with `data-chip-type="credit|publisher|tag"` — opens the edit modal to rename the entity or (for credits) manage group members / aliases. Wired at songs.js:151, 229, 255, 984, 1010.

New UI: chip labels in [chip_input.js:78-82](../../src/static/js/dashboard/components/chip_input.js#L78-L82) are **static `<span>`s with no click handler**. Only the × (remove) and ✂ (split) buttons do anything. No entry point to the edit modal at all from the Songs V2 editor.

**Lost:**
- Rename publisher from Songs tab
- Rename tag from Songs tab
- Open identity/credit edit modal (which is how you link group members, edit aliases, set legal name) from Songs tab
- Any path to the `edit_modal.js` component for song-related entities

The Publishers/Artists/Tags tabs presumably still have these paths, so the functionality isn't deleted from the app — but the Songs tab workflow that lets you fix a misnamed publisher in-context while reviewing a song **is gone**.

### Set primary genre
Old UI: `link-chip-primary` ★ button on genre tags, `data-action="set-primary-tag"` — songs.js:361-369. Handler still exists in [song_actions.js:91](../../src/static/js/dashboard/handlers/song_actions.js#L91).

New UI: tag chips have no star. No way to set primary genre from the V2 editor. Handler is now orphaned code.

### Album sub-editing (substantial — this is the big one)
Old UI's `renderAlbumCards` at [songs.js:186-313](../../src/static/js/dashboard/renderers/songs.js#L186-L313) rendered each linked album as a mini-editor:
- Edit album **title** inline (`start-edit-album-scalar` + Sentence/Title case buttons)
- Edit album **release_year** inline
- Edit **disc_number** / **track_number** inline (`start-edit-album-link`)
- Change album **type** via dropdown (`change-album-type`)
- Add/remove album **credits** (`open-link-modal` type `album-credits`, `remove-album-credit`)
- Add/remove album **publishers** (`open-link-modal` type `album-publishers`, `remove-album-publisher`)
- "↓ sync from song" button (`sync-album-from-song`)

New UI: album is a single chip with just a label. No access to any of that from the Songs tab. All handlers at [song_actions.js:98-101](../../src/static/js/dashboard/handlers/song_actions.js#L98-L101) + navigation.js:223,240 are **orphaned**.

### Format-case buttons on scalars
Old UI: S/T buttons next to Title for Sentence/Title case conversion (`data-action="format-case"`). Plan line 103 explicitly said: *"`Title` (col-8): `<input>` + S/T format buttons"*.

New UI: `renderScalarField` in [song_editor.js:28-36](../../src/static/js/dashboard/renderers/song_editor.js#L28-L36) renders a plain input with no sibling buttons. **Plan item skipped.**

### File-side comparison view
Old UI: two-column Library | File layout for credits, albums, tags, publishers — you could see what the file ID3 said vs. what the DB said, side by side.

New UI: file data only feeds drift dots on scalar inputs (Title, Year, BPM, ISRC) and renders raw ID3 tags in a collapsed block. **No side-by-side comparison for relationships.** You can no longer see "the file claims 2 composers but the DB has 1" at a glance. The plan at line 116 waved this away as "deferred to a future Write ID3 confirmation modal" — but that modal doesn't exist, so the feature is gone with no replacement.

### Raw tags surfacing
The auto-memory I carry flags raw-tag visibility as an existing debt ([raw_tags_visibility.md](../../../../.claude/projects/c--Users-glazb-PycharmProjects-gosling2/memory/project_raw_tags_visibility.md)). New UI keeps raw tags at the bottom and gates them behind a conditional — no regression, but also no improvement, on a known pain point.

### Audio scrubber / Play button
Old header button: `data-action="open-scrubber"` at [songs.js:863](../../src/static/js/dashboard/renderers/songs.js#L863).

New action sidebar: no Play button. The `scrubber_modal` import still exists in main.js. **Another orphan.**

### Sync LED
Old UI: `span.sync-led` + `updateSyncLed(song.id)` call that polls file-vs-DB sync state and shows a colored dot, plus a `sync-mismatch-list`. [songs.js:871-874](../../src/static/js/dashboard/renderers/songs.js#L871-L874), called from [main.js:523](../../src/static/js/dashboard/main.js#L523).

New UI: no sync LED, no mismatch list. `updateSyncLed` is imported at [main.js:67](../../src/static/js/dashboard/main.js#L67) but only called from the legacy `openSongDetail` path — not from the V2 `openSelectedResult` branch. **Orphaned in V2 flow.**

### Is_active / airplay toggle
Old card UI had a `toggle-active` switch per song card (songs.js:615-623). The new slim list rows have only a select-checkbox, no airplay toggle.

**Lost:** can't activate/deactivate a song for airplay from the Songs tab list anymore.

---

## Revised verdict

The audit's original "fix-forward" call **stands but gets more expensive**. Re-wiring the lost features is not trivial:

| Item | Effort |
|------|--------|
| Chip-label click → edit modal | Small — add click handler to chip label, dispatch existing `open-edit-modal` |
| Set primary genre ★ button | Small — add to tagMode chip rendering |
| Format-case S/T buttons on Title | Small — add to `renderScalarField` for `media_name` |
| Album sub-editing | **Large** — either port the album-card renderer into the new editor or link out to a dedicated Album edit surface. This is half a phase of work on its own. |
| File-side comparison for relationships | **Medium** — needs UX decision: inline drift indicators on chips? Separate compare view? |
| Play button / scrubber | Small — add to action sidebar |
| Sync LED | Small — render near song title in editor, call `updateSyncLed` |
| `is_active` toggle | Small-Medium — add to list row or editor |

**My updated recommendation:** still fix-forward, but treat "lost features" as its own Phase 10 before Phase 9 cleanup. Do NOT delete the old renderers (as Phase 9 prescribes) until every orphaned `data-action` has either been re-wired in V2 or explicitly deprecated. The orphaned handlers are currently your documentation for what's missing — deleting them before porting loses the spec.

If porting album sub-editing turns out to be genuinely large (>half day), consider scoping it out of V1 and shipping V2 with a "✎ Open album editor" button that opens the legacy detail view for that album only. Users lose inline editing in the song context but keep the capability. Explicit tradeoff instead of silent regression.

This is also a fair critique of the original plan: **it never enumerated the features of the current UI that needed to survive the rewrite.** Phases 1-9 describe what to *build*, not what to *preserve*. A "feature parity checklist" as Phase 0 would have caught all of this before any code was written. If you redo the plan, start there.

---

## Fix-forward punch list

Priority order for tomorrow morning:

1. **Delete old code** — `renderSongsCards`, `renderSongDetailComplete`, `renderSongDetailLoading`, `renderWorkflowStatus`, `renderSortControls`, `applySortAndRender`, `clearSort` in [songs.js](../../src/static/js/dashboard/renderers/songs.js). Delete all `if (songListPanel)` branching. Delete `filter-sidebar-legacy` in dashboard.html. Delete the `elements.legacyMain` toggle in main.js.
2. **Drift indicator fix** — thread file data through `refreshActiveSongV2` and the splitter `onConfirm`, call `wireDriftIndicators` on every re-render. Or better: cache `fileData` on `state.activeSong` so it's available without re-fetch.
3. **Decide: `has_publisher`/`has_album` — keep or kill.** If keeping, have the list renderer read them directly (plan-faithful, avoids `review_blockers` round-trip for list pills). If killing, drop from SQL + view model.
4. **Replace full-editor re-renders with targeted updates.** Use `handle.setItems` after chip operations; re-render only the sidebar when the action-state-affecting fields change. No full `renderSongEditorV2(fresh)` except on song switch.
5. **Verify validation-rules endpoint** exposes `blur_saves_scalars` and tag config. If not, add it (it's one endpoint change).
6. **Fix `unreviweBtn` typo** and do a readthrough of `song_editor.js` for similar.
7. **Progressive render** (optional): render editor on catalog fetch, drop in drift dots when file data resolves. Low-value unless file fetches are slow for you.

---

## Why I'm recommending fix-forward despite the sloppiness

- The data model changes are correct (slim query additions, view model `review_blockers`).
- The HTML skeleton matches the plan.
- The chip input component is a clean, self-contained, correctly-abstracted piece of code — arguably the strongest part of this work.
- The action sidebar state machine matches the plan's table.
- Almost every defect is "X was specced but not wired to every code path" — mechanical fixes, not design mistakes.

Reverting means redoing all of the above from scratch. Fixing means ~1 focused pass through the punch list above.

If you disagree after reading this, the second-best option is: keep commits `690550c` (backend/slim) and `28c63ac` (CSS + skeleton + list), revert `42719cd` and `f933892`, and redo the editor form + chip wiring + action sidebar with tighter discipline. That's a middle path I'd only take if you're genuinely unwilling to do the cleanup pass.
