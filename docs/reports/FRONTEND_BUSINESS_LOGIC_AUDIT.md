# Frontend Business Logic Audit

**Date:** 2026-04-22
**Scope:** `src/static/js/dashboard/` (28 JS files)
**Goal:** Identify logic that would break if a second frontend (e.g. PyQt) were added, because it belongs in the backend.

---

## Executive Summary

**110 findings** across 28 files. Deduplicated into **40 distinct issues** below, ranked by severity.

The #1 problem: **business workflows orchestrated client-side via multiple API calls** (sync, quick-create, resolve-conflict). The #2 problem: **domain enums and validation rules hardcoded in JS** that the backend already owns. The #3 problem: **DOM scraping** — reading business data from rendered HTML instead of the data model.

A secondary bug was found: the tag delimiter default is `:` in JS but `::` in Python.

---

## CRITICAL — Business Workflows Orchestrated Client-Side

### CW-1: `syncAlbumWithSong()` is a full backend workflow living in JS
- **File:** `song_actions.js:40-74`
- **What it does:** Fetches song + album, diffs credits by role ("only Performers"), diffs publishers by ID, issues multiple parallel API calls to sync them.
- **Why it breaks:** PyQt must duplicate the multi-fetch + diff + multi-call pattern. Any change to sync rules (e.g. also sync Composers) requires updating both frontends.
- **Fix:** Create `POST /api/v1/albums/{albumId}/sync-from-song/{songId}` — one call, atomic.

### CW-2: `handleQuickCreateAlbum()` is a multi-step process with timing hacks
- **File:** `song_actions.js:1013-1059`
- **What it does:** Creates album with hardcoded defaults (disc=1, track=2), syncs metadata via CW-1, then `await new Promise(r => setTimeout(r, 600))` for DB materialized views to settle.
- **Why it breaks:** The 600ms delay is a backend consistency smell. PyQt must reproduce the same multi-step orchestration and arbitrary delay.
- **Fix:** Create `POST /api/v1/songs/{songId}/quick-create-album` — atomic operation, backend handles consistency.

### CW-3: Spotify credit identity resolution is a matching algorithm in JS
- **File:** `spotify_modal.js:140-158`
- **What it does:** Resolves parsed Spotify credits to existing identity IDs using a two-priority strategy: (1) match by case-insensitive name + exact role against existing song credits, (2) match by name against backend preview results.
- **Why it breaks:** PyQt must reimplement the identical priority chain or produce different import behavior.
- **Fix:** Move to backend `POST /api/v1/spotify/import` — server resolves identity IDs given parsed credits.

### CW-4: `handleResolveConflict()` branches on status to drive workflows
- **File:** `song_actions.js:623-687`
- **What it does:** After resolving a conflict, branches on `status === "INGESTED"` vs `status === "PENDING_CONVERT"` to show different UIs and offer different next actions.
- **Why it breaks:** PyQt must know the same post-conflict state machine.
- **Fix:** Backend should return `next_action` and `status_label` in the resolve response.

### CW-5: `handleMoveToLibrary()` has conditional cleanup + error classification
- **File:** `song_actions.js:314-384`
- **What it does:** After moving, checks `original_exists`, prompts to delete original, classifies errors by string matching on "already exists" / "409".
- **Why it breaks:** PyQt must duplicate the cleanup workflow and error classification.
- **Fix:** Backend `move` endpoint should accept `cleanup_original=true`. Error classification should use structured error codes, not string matching.

### CW-6: Album auto-sync on creation is client-side orchestration
- **File:** `orchestrator.js:196-211`
- **What it does:** After `addSongAlbum`, immediately calls `syncAlbumWithSong` for new albums. The business rule "newly created albums should auto-sync metadata with their first song" lives in JS.
- **Fix:** Move into backend's `create_and_link_album` in `edit_service.py`.

---

## CRITICAL — Domain Enums Duplicated from Backend

### DE-1: `PROCESSING_STATUS` enum
- **Files:** `constants.js:1-6`, used in `song_editor.js`, `song_actions.js`, `components/utils.js`
- **Backend source:** `engine/config.py:10-14` (`ProcessingStatus(IntEnum)`)
- **Fix:** Expose via `/api/v1/config` or return `status_label` / `available_actions` in API responses so frontends never interpret the integer.

### DE-2: Ingestion status config map
- **File:** `ingestion.js:579-603`
- **What it maps:** `NEW`, `INGESTED`, `CONVERTING`, `PENDING_CONVERT`, `ALREADY_EXISTS`, `CONFLICT`, `ERROR` → human labels + severity classes + icons.
- **Fix:** Backend should return `status_label` and `status_severity` per ingestion item.

### DE-3: `ALBUM_TYPES` list
- **File:** `song_editor.js:96`
- **Hardcoded:** `["Album", "EP", "Single", "Compilation", "Anthology"]`
- **Fix:** Expose via `/api/v1/config` or `/api/v1/validation-rules`.

### DE-4: `STATUS_FILTERS` for song filtering
- **File:** `filter_sidebar.js:28-33`
- **Hardcoded:** `not_done`, `ready_to_finalize`, `missing_data`, `done` with display labels.
- **Fix:** `/api/v1/songs/filter-values` should include available status filters.

### DE-5: `REQUIRED_ROLES` / `OPTIONAL_ROLES` for credits
- **File:** `song_editor.js:937-938`
- **Hardcoded:** `["Performer", "Composer"]` and `["Lyricist", "Producer"]`
- **Fix:** Expose a `credit_roles` config with `required: bool` flag per role.

### DE-6: `BLOCKER_LABELS` abbreviation map (duplicated in TWO files)
- **Files:** `song_editor.js:260-269`, `songs.js:189-198`
- **Fix:** Backend should return `blocker_label` per blocker item, or a `blocker_labels` dict.

---

## CRITICAL — Validation Logic Duplicating or Missing Backend

### VL-1: `validators.js` duplicates backend validation for 4 fields
- **File:** `utils/validators.js:7-48`
- **Fields:** `media_name` (required), `year` (range), `bpm` (range), `isrc` (regex + normalization)
- **Backend already enforces:** `edit_service.py:135-166` with identical logic.
- **Fix:** Remove from JS. Rely on backend 400 errors. `/api/v1/validation-rules` can provide label text for UX hints.

### VL-2: `validators.js` has validation the backend does NOT enforce
- **File:** `utils/validators.js:20-27, 50-62`
- **Fields:** `release_year` (range 1860–now+1), `track_number` (positive int), `disc_number` (positive int)
- **Backend gap:** These fields are unvalidated server-side. A PyQt frontend could submit `track_number = -5` successfully.
- **Fix:** Add backend validation first, then remove from JS.

### VL-3: Field-type coercion map
- **File:** `inline_editor.js:58-71`
- **Hardcoded list:** `["year", "release_year", "bpm", "track_number", "disc_number"]` → numeric; everything else → string.
- **Fix:** Backend should accept and coerce field values itself on PATCH.

### VL-4: ISRC normalization in frontend
- **File:** `validators.js:41` — `v.replace(/-/g, "").toUpperCase()`
- **Backend also normalizes:** `edit_service.py:161` — `.replace("-", "").upper()`
- **Fix:** Remove from JS. Backend handles it.

### VL-5: `release_year` ignores server rules entirely
- **File:** `validators.js:20-27`
- **Issue:** Unlike `year` which uses `rules` parameter, `release_year` hardcodes `1860` and ignores `rules`.
- **Fix:** Use `rules` consistently, or remove entirely per VL-2.

---

## CRITICAL — DOM Scraping (Non-Portable Pattern)

### DS-1: Current albums scraped from DOM for link modal
- **File:** `navigation.js:219-235`
- **What:** Finds `remove-album` buttons in rendered HTML, extracts albumId + label from surrounding elements.
- **Why catastrophic for PyQt:** DOM scraping is entirely web-specific. No equivalent exists in Qt widgets.
- **Fix:** Use `state.activeSong.albums` from the data model.

### DS-2: Current album publishers scraped from DOM
- **File:** `navigation.js:236-251`
- **Same pattern as DS-1.** Fix: read from data model.

### DS-3: Current album credits scraped from DOM
- **File:** `navigation.js:253-268`
- **Same pattern as DS-1.** Fix: read from data model.

### DS-4: Track/disc paired-field editing scrapes sibling from DOM
- **File:** `song_actions.js:797-837`
- **What:** When editing `track_number`, reads `disc_number` from the DOM sibling element (and vice versa), interprets `"-"` as null, submits both together.
- **Fix:** Backend should accept partial updates (only the changed field).

---

## HIGH — Business Rules Driving Conditional UI

### BR-1: Staging path detection
- **File:** `song_editor.js:802-804`
- **Logic:** `(song.source_path || "").toLowerCase().includes("staging")`
- **Fix:** Backend should return `is_in_staging: bool` in song views. Backend already knows `STAGING_DIR`.

### BR-2: Processing status + staging → available actions
- **File:** `song_editor.js:809-817`
- **Logic:** `NEEDS_REVIEW + blockers` → "Mark as Done"; `REVIEWED + staging` → "Organize to Library" + "Unreview".
- **Fix:** Backend should return `available_actions: ["mark_reviewed", "move_to_library", "unreview"]` computed from status + staging state.

### BR-3: "Only reviewed songs can be active" rule
- **Files:** `song_editor.js:993`, `components/utils.js:101-108`
- **Logic:** `processing_status !== REVIEWED` → disable active toggle.
- **Backend also enforces:** `edit_service.py:129`
- **Fix:** Backend should return `can_activate: bool`.

### BR-4: Entity deletion guards (repeated per entity type)
- **Files:** `tags.js:97`, `publishers.js:117`, `artists.js:135`, `albums.js:184`, `song_editor.js:810`
- **Logic:** Each entity type computes `can_delete` differently (tags: song_count=0; publishers: song_count=0 AND album_count=0; albums: song_count=0).
- **Fix:** Each entity list API should return `can_delete: bool`.

### BR-5: Bulk parse eligibility filter
- **File:** `ingestion.js:733-744`
- **Logic:** Only INGESTED/CONFLICT/CONVERTING entries with IDs are eligible.
- **Fix:** Backend should return `can_bulk_parse: bool` per entry, or silently skip ineligible entries.

### BR-6: Group→person conversion guard
- **File:** `orchestrator.js:329-331`
- **Backend also enforces:** `identity_repository.py:403-411`
- **Fix:** Remove client-side guard. Show backend error.

### BR-7: "Groups can't be members" filter
- **File:** `orchestrator.js:416-421`
- **Backend also enforces:** `identity_repository.py:436-439`
- **Fix:** Remove client-side filter, or add `?exclude_groups=true` to search endpoint.

---

## HIGH — Client-Side Data Transformation (Should Be Backend)

### DT-1: Tag input parsing
- **File:** `utils/tag_input.js:1-24` (entire file)
- **What:** Parses `"Jazz::Genre"` → `{name: "Jazz", category: "Genre"}` using configurable delimiter/format.
- **Fix:** Backend should accept raw strings on `POST /songs/{id}/tags` and parse server-side.

### DT-2: Tag deduplication (`shouldCreate`)
- **File:** `orchestrator.js:132-144`
- **What:** Case-insensitive name + category match against search results to decide if tag can be created.
- **Fix:** Backend `POST /songs/{id}/tags` should handle dedup (link to existing if match found).

### DT-3: Tag search sort by category match
- **File:** `orchestrator.js:88-97`
- **Fix:** Backend `/api/v1/tags/search` should accept optional `category` param and sort accordingly.

### DT-4: Splitter token-to-name resolution
- **File:** `splitter_modal.js:90-105`
- **What:** Stateful algorithm that assembles names from tokens based on separator ignore flags.
- **Fix:** Backend already tokenizes; add a `/api/v1/tools/splitter/resolve` endpoint.

### DT-5: Duration formatting (seconds → MM:SS)
- **File:** `ingestion.js:619-624`
- **Backend already has:** `SongSlimView.formatted_duration` (view_models.py:131-138)
- **Fix:** Ingestion response should use a view model that includes `formatted_duration`.

### DT-6: File size formatting (bytes → KB)
- **File:** `ingestion.js:233`
- **Fix:** Backend should return `display_size`.

### DT-7: Batch success rate calculation
- **File:** `ingestion.js:529-532`
- **Fix:** Add `success_rate` to `BatchIngestReport` backend model.

### DT-8: Credit grouping by role (repeated 6+ times)
- **File:** `song_editor.js:940-944, 553-561, 188-194, 460-463`
- **Fix:** Backend should return `credits_by_role: {Performer: [...], Composer: [...]}` computed field.

---

## HIGH — Display Fallback Chains (Should Be Backend Computed Fields)

### FB-1: Album title: `album_title || display_title || "Unknown Album"`
- **File:** `song_editor.js:102-103`

### FB-2: Artist name: `display_name || legal_name || name`
- **Files:** `song_editor.js:569-572`, `orchestrator.js:163-164, 283-285`

### FB-3: Song title: `title || media_name || "Untitled"`
- **File:** `songs.js:185-187`

### FB-4: Song artist: `display_artist || "Unknown Artist"`
- **File:** `songs.js:188`

### FB-5: Ingestion title with CONFLICT special case
- **File:** `ingestion.js:609-615`

### FB-6: Publisher display with parent: `name (parent_name)` or `name`
- **Files:** `publishers.js:59`, `albums.js:59`

**Universal fix:** Backend should guarantee populated `display_title`, `display_artist`, `display_name` computed fields in all API responses. Frontends use one field.

---

## MEDIUM — Conditional API Routing / Body Construction

### AP-1: Empty query → list endpoint, non-empty → search endpoint
- **File:** `api.js:96-126, 405-410`
- **Fix:** Consolidate backend: `GET /albums?q=` where empty q returns all.

### AP-2: ID-vs-name linking body construction
- **Files:** `api.js:296-306, 464-472, 486-495, 543-553`
- **Logic:** `publisherId !== null ? {publisher_id} : {publisher_name}` — branching logic for entity linking.
- **Fix:** Backend should accept unified payload and handle the branching server-side.

### AP-3: Default role "Performer" hardcoded
- **File:** `api.js:522` (function default), `orchestrator.js:293`
- **Backend also defaults:** `catalog_service.py:333`, `edit_service.py:410`
- **Fix:** Frontend should omit role; let backend default apply.

### AP-4: `getSongDetail` silently returns null for 404/500
- **File:** `api.js:140-152`
- **Fix:** Backend should return `204 No Content` or a structured response instead of throwing.

---

## MEDIUM — Client-Side Search/Filter Logic

### SF-1: Link modal deduplication (by ID or case-insensitive label)
- **File:** `link_modal.js:156-164`
- **Fix:** Backend search should accept `exclude_ids` parameter.

### SF-2: Link modal "should create" decision
- **File:** `link_modal.js:169-182`
- **Fix:** Backend should return `can_create` flag.

### SF-3: Edit modal category search (client-side re-filter)
- **File:** `edit_modal.js:554-567`
- **Fix:** Backend category endpoint should accept `q` param.

### SF-4: Tag category search (fetches ALL, filters client-side)
- **File:** `orchestrator.js:495-499`
- **Fix:** Add `q` param to `/api/v1/tags/categories`.

### SF-5: Filter dimension list hardcoded in 3 places
- **Files:** `filter_sidebar.js:42-52, 118-150, 261-294`
- **Fix:** Backend should provide a filter schema endpoint.

---

## MEDIUM — State Management With Domain Knowledge

### SM-1: Structural change detection
- **File:** `main.js:203-207`
- **Logic:** Counts albums/credits/publishers to decide full vs partial re-render.
- **Fix:** Backend could return `structural_version` hash.

### SM-2: Ingestion status → toast severity mapping
- **File:** `main.js:879-893`
- **Fix:** Backend should include `severity` in `IngestionReportView`.

### SM-3: Optimistic cache mutation on toggle active
- **File:** `song_actions.js:248-255`
- **Fix:** Backend should return the full updated entity.

### SM-4: "credit:" prefix stripping from mismatch strings
- **File:** `song_actions.js:27-29`
- **Fix:** Backend should return structured mismatches: `{type: "credit", label: "..."}`.

---

## MEDIUM — Hardcoded Defaults / Config

### HC-1: Default filename parse pattern `"{Artist} - {Title}"`
- **File:** `filename_parser_modal.js:230-231`
- **Fix:** Backend `/api/v1/ingest/parser-config` should include `default_pattern`.

### HC-2: Tag default category fallback `"other"` vs backend default `"Genre"`
- **File:** `tags.js:8-14`
- **MISMATCH:** JS defaults to `"other"`, Python defaults to `"Genre"` (config.py:49).
- **Fix:** Use backend default.

### HC-3: 600ms settlement delay after album sync
- **Files:** `song_actions.js:984-999, 1013-1059`
- **Fix:** Backend should ensure read-after-write consistency before responding.

---

## BUG — Tag Delimiter Mismatch

### BUG-1: `tag_input.js` defaults delimiter to `:` but backend config is `::`
- **JS:** `tag_input.js:9` — `rules.delimiter || ":"`
- **Python:** `engine/config.py:50` — `TAG_CATEGORY_DELIMITER = "::"`
- **Impact:** If validation rules fail to load, `"Jazz::Genre"` splits as `["Jazz", ":Genre"]` instead of `["Jazz", "Genre"]`.

---

## Checklist

### Phase 1: Quick Wins (eliminate duplication)
- [x] **1.** Remove `validators.js` content for 4 fields backend already validates (media_name, year, bpm, isrc) — VL-1
- [x] **2.** Remove client-side guards backend already enforces (group→person, groups-as-members) — BR-6, BR-7
- [x] **3.** Fix tag delimiter mismatch (`:` in JS vs `::` in Python) — BUG-1

### Phase 2: Backend Enforcement Gaps
- [x] **4.** Add backend validation for `release_year`, `track_number`, `disc_number` — VL-2
- [x] **5.** Add `can_delete: bool` to entity list responses — BR-4
- [x] **6.** Add `can_activate: bool` to song responses — BR-3
- [x] **7.** Add `is_in_staging: bool` to song responses — BR-1
- [x] **8.** Add `available_actions: [...]` to song responses — BR-2

### Phase 3: Atomic Backend Operations
- [x] **9.** Create `POST /albums/{id}/sync-from-song/{songId}` — eliminates CW-1, CW-2, CW-6, HC-3 **(backend done, frontend pending)**
- [x] **10.** Create `POST /songs/{id}/quick-create-album` — eliminates CW-2 **(backend done, frontend pending)**
- [x] **11.** Move identity resolution to backend — eliminates CW-3 **(backend done, frontend pending)**
- [x] **12.** Backend tag parsing on `POST /songs/{id}/tags` — eliminates DT-1, DT-2 **(backend done, frontend pending)**

### Phase 4: Computed Display Fields
- [ ] **13.** Guarantee `display_title`, `display_artist`, `display_name` in all API responses — FB-1–FB-6
- [ ] **14.** Add `status_label` + `status_severity` to ingestion items — DE-2, SM-2
- [ ] **15.** Add `formatted_duration` + `display_size` to ingestion responses — DT-5, DT-6
- [ ] **16.** Return `credits_by_role` as computed field — DT-8

### Phase 5: Replace DOM Scraping
- [x] **17.** Replace DOM-scraping in `navigation.js` with data model access — DS-1–DS-4
  - DS-4 (track/disc paired DOM scrape in `handleStartEditAlbumLink`) eliminated: album link fields now use always-on `<input>` elements wired via `wireAlbumScalarInputs`, sending partial PATCH (one field at a time). `handleStartEditAlbumScalar` and `handleStartEditAlbumLink` deleted.
  - DS-1–DS-3 (album/publisher/credit DOM scraping in `navigation.js`) deferred: these belong to the legacy song detail view link modal path, not the V2 editor.

### Phase 6: Config Consolidation
- [ ] **18.** Expand `/api/v1/config` to include: PROCESSING_STATUS, ALBUM_TYPES, STATUS_FILTERS, credit roles, filter dimensions, default patterns — DE-1–DE-6
- [ ] **19.** Remove all hardcoded fallback defaults from JS — HC-1–HC-3
