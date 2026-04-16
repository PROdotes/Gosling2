# Plan: Songs Tab UI Full Replacement (POC → Production)

## Context
The current Songs tab uses a card-list layout with a collapsible detail panel. A full-day design sprint produced `edit-design-poc.html`, a polished 3-pane layout: **filter sidebar | song list | always-visible editor** with chip-based multi-select inputs for relationships, a consolidated action sidebar, and clear visual hierarchy (Required / Additional / Raw sections). The goal is to fully replace the current Songs tab with this new layout and interaction model.

Scope decisions confirmed:
- Full layout replacement (3-pane)
- Action sidebar replaces the old workflow status banner
- Chip inputs with inline autocomplete replace the link modal flow

---

## Architecture Overview

The codebase is **vanilla JS ES Modules** served from FastAPI. Key files:

| File | Role | Size |
|------|------|------|
| `src/static/js/dashboard/renderers/songs.js` | Song list + detail panel renderer | 928 lines |
| `src/static/js/dashboard/handlers/filter_sidebar.js` | Filter sidebar logic | 514 lines |
| `src/static/js/dashboard/handlers/song_actions.js` | Action handlers (organize, delete, etc.) | ~887 lines |
| `src/static/js/dashboard/components/inline_editor.js` | Click-to-edit scalars | 173 lines |
| `src/static/js/dashboard/components/edit_modal.js` | Relationship modal (to be replaced for songs) | 725 lines |
| `src/static/js/dashboard/api.js` | All fetch calls — **reuse as-is** | 673 lines |
| `src/static/css/dashboard/` | All CSS — **replace/extend** | 2,582 lines |
| `src/templates/dashboard.html` | HTML skeleton | ~18 KB |

---

## Implementation Plan

### Phase 1 — CSS: Extract and extend POC styles

1. **Create** `src/static/css/dashboard/songs_v2.css` with the full CSS from the POC (`edit-design-poc.html` `<style>` block).
2. Scope all new selectors under `#songs-workspace` to avoid bleeding into other tabs.
3. Keep existing CSS files intact — other tabs (Albums, Artists, Ingest) still use them.
4. Add `songs_v2.css` to the `<link>` chain in `src/templates/dashboard.html`.

### Phase 2 — HTML Skeleton: 3-pane layout in dashboard.html

Replace the Songs tab container with the 3-pane structure from the POC:

```
#songs-workspace
  ├── #filter-sidebar          (reuse existing filter sidebar render logic)
  ├── .left-pane
  │   ├── .list-header         (checkbox | sort dropdown | "MISSING" label)
  │   └── #song-list-panel     (new slim list rows)
  └── #editor-panel
      ├── .editor-scroll       (form sections)
      └── .action-sidebar      (action buttons)
```

The workspace is only shown when the Songs tab is active.

### Phase 3 — Backend: Extend slim query + config flags

**`src/data/song_repository.py` — `search_slim()`**: Add two boolean flags to the SELECT:
- `has_publisher`: `COUNT(rp.PublisherID) > 0` via LEFT JOIN on `RecordingPublishers`
- `has_album`: `COUNT(sa.AlbumID) > 0` via LEFT JOIN on `SongAlbums`

**`src/engine/config.py`**: Add:
```python
BLUR_SAVES_SCALARS = True   # If False, blur reverts instead of saving
```

**`src/engine/routers/` (validation-rules endpoint)**: Expose `blur_saves_scalars` and existing tag config (`tag_delimiter`, `tag_default_category`, `tag_input_format`) in the response so the frontend reads them from `state.validationRules` at no extra fetch cost.

### Phase 4 — Song List Renderer

**File to modify**: `src/static/js/dashboard/renderers/songs.js`

Replace `renderSongsCards()` with `renderSongRows()`:
- Each row: checkbox, title/artist stacked, missing-data pills
- Pills derived from slim data: `has_publisher` → `PUB` pill, `has_album` → `ALB` pill (both shown only when missing, i.e. `false`)
- Pills update when the full catalog loads for a selected song (cache entry refreshed) and after any relationship edit
- Selection state: `song-row.selected` with left-border highlight
- Multi-select: checking multiple rows shows "N songs selected" placeholder in editor panel instead of the edit form
- Keep `data-action="select-result"` so existing selection handler still fires

**List header**:
- Checkbox (select-all)
- "AUDIO TRACK" label + sort `<select>` dropdown inline: options are Default, Title ↑, Title ↓, Artist ↑, Artist ↓, ID ↑, ID ↓
- Filter toggle button (moves here from the old sort controls toolbar)
- "MISSING" label right-aligned

### Phase 5 — Editor Form Renderer

**New function** `renderSongEditorV2(song)` — extract to new file `src/static/js/dashboard/renderers/song_editor.js`:

**Empty state**: When no song is selected, render a blank placeholder ("Select a song to edit").

**Multi-select state**: When multiple rows are checked, render "N songs selected" (no form).

**Load sequence** (same as current, on single song selection):
1. Fire 3 parallel fetches: `getCatalogSong`, `getSongDetail` (file data), `getAuditHistory`
2. Render form immediately with catalog data; file data feeds drift indicators; audit history feeds Raw section (deferred — only fetched/shown when Raw section is scrolled into view or expanded)

**Section 1 — Required Metadata:**
- `Title` (col-8): `<input>` + S/T format buttons → `patchSongScalars(id, {media_name})`
- `Year` (col-4): `<input type="number">` → `patchSongScalars(id, {year})`
- `Artist / Performer` (col-6): chip input with autocomplete + ✂ per chip
- `Composer / Credit` (col-6): chip input with autocomplete + ✂ per chip
- `Tags` (col-12): chip input with category-prefixed chips + Play button
- `Publisher` (col-6): chip input (single), error border when empty
- `Album / Release` (col-6): chip input

**Section 2 — Additional Data:**
- BPM, ISRC, Track No — plain inputs → `patchSongScalars`

**Section 3 — Extraneous / Raw Metadata:**
- Comments input
- Raw ID3 block (read-only, from file data)
- Audit history (lazy — loaded on expand)

**Drift indicators**: Each input field label gets a small colored dot when the DB value ≠ the file value. Hovering shows a tooltip with the file's value. Full comparison deferred to a future "Write ID3" confirmation modal.

**Scalar save behavior**:
- Enter → saves immediately
- Escape → reverts to saved value
- Blur → saves if `state.validationRules.blur_saves_scalars === true` (default), reverts if false

### Phase 6 — Chip Input Component

**New file**: `src/static/js/dashboard/components/chip_input.js`

```js
createChipInput({
  container,       // .input-wrap element
  items,           // initial chips [{id, label, category?}]
  onSearch,        // async (q) => [{id, label, meta?}]
  onAdd,           // async (item) => {}
  onRemove,        // async (id) => {}
  onSplit,         // async (id) => {} — artists/composers only
  allowCreate,     // show "+ Create new X" option
  singleSelect,    // publisher uses this
  tagMode,         // enables category prefix display + parseTagInput logic
})
```

**Tag mode specifics**: Uses `parseTagInput()` extracted to `src/static/js/dashboard/utils/tag_input.js` (shared with orchestrator). Reads `tag_delimiter`, `tag_default_category`, `tag_input_format` from `state.validationRules`. "Create new" label shows parsed category: `Add "French" in "Language"`.

**Autocomplete search functions** (all already in `api.js`):
- Artists/Composers: `searchArtists(q)` — note: NOT `searchIdentities` (doesn't exist)
- Tags: `searchTags(q)`
- Publishers: `searchPublishers(q)`
- Albums: `searchAlbums(q)` (slim variant)

**Relationship APIs** (all already in `api.js`, reused as-is):
- `addSongCredit` / `removeSongCredit`
- `addSongTag` / `removeSongTag`
- `addSongPublisher` / `removeSongPublisher`
- `addSongAlbum` / `removeSongAlbum`

**✂ Split**: per-chip only. Opens existing splitter modal with that chip's string. No multi-chip split.

**After any chip add/remove**: refresh the in-memory slim cache entry for the song and re-render its list row pills.

### Phase 7 — Action Sidebar

The action sidebar replaces the workflow status banner. Same 4-state machine, same `data-action` attributes, just rendered in the new slot:

| State | Button label | Style |
|-------|-------------|-------|
| Status 1, blockers present | Mark as Done | Grey / disabled (`.organize.blocked`) |
| Status 1, no blockers | Mark as Done | Green (`.organize`) |
| Status 0, in staging | Organize to Library | Green (`.organize`) |
| Status 0, not in staging | *(hidden)* | — |

Full sidebar button list:

| Button | data-action | Notes |
|--------|-------------|-------|
| Parse | `open-filename-parser-single` | |
| Spotify ⇅ | `open-spotify-modal` | |
| Search ▾ | `web-search` + `web-search-set-engine` | Split button with engine picker |
| ↑ Write ID3 | `sync-id3` | Future: opens comparison modal first |
| Mark as Done / Organize | `mark-reviewed` / `move-to-library` | State machine above |
| Unreview | `unreview-song` | Shown when status === 0 |
| ⚠ Delete Original | `cleanup-original` | Amber, shown when original exists |
| 🗑 Delete Record | `delete-song` | Danger, always shown |

File paths shown below Organize (destination: `organized_path_preview`) and below Delete Original (source: `estimated_original_path`).

### Phase 8 — Filter Sidebar

`filter_sidebar.js` reused as-is. Changes:
- Filter toggle button moves from old sort controls toolbar into the new list header
- Ensure it targets the `#filter-sidebar` slot inside `#songs-workspace` (not the old position)

### Phase 9 — Cleanup

Once new UI is wired and working:
- Remove `renderSongsCards()`, `renderSongDetailComplete()`, `renderSongDetailLoading()`, `renderWorkflowStatus()` from `songs.js`
- Remove `edit_modal.js` usages specific to song relationships (keep modal for identity rename and other entity types)
- Remove detail-panel-specific CSS from `detail.css` that no longer applies
- Remove old sort controls rendering from `songs.js`

---

## Critical Files

| File | Change |
|------|--------|
| `src/data/song_repository.py` | Extend slim query with `has_publisher`, `has_album` |
| `src/engine/config.py` | Add `BLUR_SAVES_SCALARS` |
| `src/engine/routers/` (validation-rules) | Expose blur + tag config flags |
| `src/static/js/dashboard/renderers/songs.js` | Replace list renderer, remove old detail renderer |
| `src/static/js/dashboard/renderers/song_editor.js` | **New file** — editor form renderer |
| `src/static/js/dashboard/components/chip_input.js` | **New file** — chip input component |
| `src/static/js/dashboard/utils/tag_input.js` | **New file** — `parseTagInput` shared util |
| `src/static/js/dashboard/handlers/song_actions.js` | Wire action sidebar buttons |
| `src/static/js/dashboard/handlers/filter_sidebar.js` | Minor: correct DOM target + toggle wiring |
| `src/static/css/dashboard/songs_v2.css` | **New file** — POC CSS scoped to `#songs-workspace` |
| `src/templates/dashboard.html` | 3-pane skeleton insertion |
| `edit-design-poc.html` | Source of truth — do not delete |

---

## Phasing Strategy

Build incrementally so the app stays functional at each step:

1. Backend: extend slim query + config flags + validation-rules endpoint
2. CSS + skeleton (layout in place, content still old)
3. New list rows (replacing cards) + sort dropdown + filter toggle
4. Static editor form (renders from catalog data, no events yet)
5. Scalar inputs wired (Title, Year, BPM, ISRC) + drift indicators
6. Chip inputs: Artists + Composers (with ✂ split)
7. Chip inputs: Tags (with parseTagInput) + Publisher + Album
8. Action sidebar wired
9. Cleanup old code

---

## Verification

- Open Songs tab → 3-pane layout renders, editor is blank placeholder
- All rows show `PUB`/`ALB` pills where applicable immediately on load
- Sort dropdown cycles correctly, list re-orders
- Filter toggle shows/hides filter sidebar from list header button
- Clicking a song row selects it, editor populates from catalog data
- Checking multiple rows shows "N songs selected" placeholder
- Drift indicator dot appears on Title label when DB ≠ file value; tooltip shows file value
- Edit Title + Enter → saves, list row title updates
- Edit Title + Escape → reverts
- Edit Title + blur → saves (default) or reverts (if `BLUR_SAVES_SCALARS=False`)
- Add Artist chip → autocomplete fires, chip appears, credit saved in DB, list row refreshes
- Remove Artist chip → credit deleted from DB
- ✂ on artist chip → splitter modal opens with that chip's string
- Type `French::Language` in tag chip → "Add 'French' in 'Language'" shown, correct category saved
- Publisher field shows error border when empty
- "Mark as Done" disabled when blockers present, enabled when clear
- "Mark as Done" click → status 0 → button changes to "Organize to Library"
- "Organize to Library" → file moved, song removed from staging filter
- "Delete Record" → song deleted, row removed from list
- All other tabs (Albums, Artists, Ingest) unaffected
