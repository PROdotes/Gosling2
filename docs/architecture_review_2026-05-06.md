# Architecture Review: Drift Unification + MutationCoordinator
_2026-05-06_

Two features reviewed: (1) Drift Unification — single `inspect-file` endpoint returning `{file_song, diff}`, frontend `wireDriftIndicators` rewrite; (2) MutationCoordinator — `POST /mutate` with discriminated union, per-entity mutators.

---

## Candidates

### 1. Diff key contract has no seam

**Files:** `song_editor.js:495–541`, `song_actions.js:40–65`, `metabolic.py`

**Problem:** `wireDriftIndicators` hardcodes the diff key → DOM element mapping inline. `SCALAR_INPUT_BY_KEY` is a 5-entry table defined inside the function body. The credit branch works dynamically (`data-chip-field="${role}"`) so new roles are fine, but scalar keys are frozen in that inline table. If the backend renames a diff key, dots silently stop appearing — same class of bug the drift unification was built to fix.

**Solution:** Hoist `SCALAR_INPUT_BY_KEY` to module scope (or a shared constants file). The mapping is the seam; the renderer is just an iterator over it. No structural change needed — this is a small locality fix, not a full refactor.

**Benefits:** One place to update when scalar diff keys change. The table becomes auditable against the backend's `compare_songs` output keys.

**Note (2026-05-06):** The `credit:` branch is already dynamic and does not need a lookup table. `getRoles()` is not involved here.

---

### 2. `refreshActiveSongV2` is a god function with no abort

**Files:** `main.js:200–260`, `main.js:708–790`

**Problem:** The refresh function does: DB fetch → structural diff → conditional full re-render → wire scalars → wire chips → background file fetch → state update → LED update → drift dots. It is not cancellable. If the user clicks song A then song B rapidly, song A's `getSongDetail` resolve can overwrite song B's `activeSongDiff`. The guard `state.activeSong?.id !== fresh.id` catches this in some paths but not all. `openSelectedResult` duplicates ~40% of the same logic.

**Solution:** Extract the two-phase load (fast paint → slow file state) into a small `SongLoader` module that owns an `AbortController` per load cycle. Any new load cancels the previous one. Both `refreshActiveSongV2` and `openSelectedResult` call into it.

**Benefits:** Race condition eliminated at the seam. The two duplication sites collapse. The two-phase pattern is testable in isolation.

---

### 3. Orchestrator entity flows are copy-paste deep

**Files:** `orchestrator.js` — `manageSongCredits`, `manageSongAlbums`, `manageSongPublishers`

**Problem:** These three functions are ~80% structurally identical: fetch current links → open link modal with search + add + remove callbacks → refresh. Business logic (e.g. `MERGE_REQUIRED` error handling, confirmation dialogs) is embedded inside each callback closure. Adding a new entity type means copying ~60 lines. Changing the error-handling pattern means touching three places.

**Solution:** Extract a single `manageSongRelationship(ctx, config)` where `config` carries entity-specific callbacks. The shared orchestration (open modal, handle error, refresh) lives once. Each entity type becomes a ~10-line config block.

**Benefits:** Adding a fourth entity type is one config block. Error-handling logic has locality.

---

### 4. Filing side-effect is split across two owners

**Files:** `mutation_coordinator.py:100–130`, `filing_service.py`

**Problem:** The file move sequence is: `FilingService.copy_if_needed()` → `SongRepository.update_source_path()` → coordinator manually `unlink()`s the old file. Three owners, no rollback if `unlink` fails. Coordinator has raw `Path.unlink()` calls that belong in a service. The spec says `FilingService.move_if_needed()` should exist; the implementation uses copy-then-delete instead.

**Solution:** Give `FilingService` a `move_if_needed(song_id, old_path, new_path, conn)` that owns all three steps. The coordinator calls it once and no longer touches the filesystem directly.

**Benefits:** Filing logic has locality. Orphan-file scenario is handled in one place. Coordinator's post-commit block shrinks.

---

## Deferred / Not Recommended

- **Timeout on I/O** (`getSongDetail`, etc.) — simple defensive add, not an architectural issue.
- **Client-side validation** — already handled via `validationRules` fetched from server; round-trip cost is acceptable for now.
- **Diff shape versioning** — no versioning plan needed until there's actually a second consumer of the diff.
- **Modal coordinator class** — speculative; no concrete deadlock observed in production.
- **Audit seam** — already tracked as deferred in `project_audit_logging.md`.
