# Gosling2

Music-library manager for a radio station. FastAPI backend (`src/engine_server.py`) + vanilla-JS dashboard (`src/static/js/dashboard/`) + SQLite. Long-term there will be a desktop app and the web UI consuming the **same JSON API** — the frontend must stay a dumb view layer. A legacy PyQt `Gosling2.exe` coexists; `gosling-server.exe` is the shared headless engine (PyInstaller build).

## Navigation

Read `docs/lookup/` before exploring code or launching search agents — it is the LLM-oriented map of the codebase (data layer, routers, services, JS modules, utils). Only deep-search when the lookup docs don't answer. Roadmap lives in `docs/FEATURES.md`; specs in `docs/specs/` and `docs/todo/`; architecture vocabulary in `.claude/skills/improve-codebase-architecture/LANGUAGE.md` (use module/interface/seam/depth — not component/boundary/unit).

## Architecture invariants

Each of these was established after a real bug. Violating one is never a style issue.

1. **All DB writes go through the mutator path**: `MutationCoordinator` (`src/services/mutation_coordinator.py`) → `src/services/mutators/*_mutator.py` → repository. Single endpoint: `POST /api/v1/mutate`. Any write-shaped method in a plain service is dead legacy code — do not extend it, call it, or test it. Writes that bypass the coordinator leave no audit trail and cannot be undone.
2. **SQL CRUD and `conn.commit()` live only in `src/data/*_repository.py`.** Never in services, mutators, coordinators, or routers. Test seed helpers in `tests/` are exempt.
3. **Repo write contract**: repo write methods return `cursor.rowcount` and never raise on zero rows. The mutator checks the count and raises `LookupError`. Don't invert this in either direction.
4. **Read paths are pure.** Hydration (`_hydrate_songs` etc.) and any `get_/list_/search_` method must never write to the DB or move files. Side effects belong only in the coordinator's post-commit block. The `conn` passed into hydration is caller-owned.
5. **Passthrough/coordinator services contain no try/except and no business logic.** Error handling belongs in the layer that owns the operation.
6. **Thin frontend.** Business logic, validation, and computed fields live behind the API, never in `main.js`/handlers/renderers. Every frontend mutate caller must inspect `result.warnings` — filing failures come back as `kind: "file_move"` warnings inside a 200 response.
7. **`src/engine/config.py` owns every filesystem path and validation constant.** Any `open()`/`Path(...)` must trace to a named constant there; validation bounds come from `SCALAR_VALIDATION`. Never construct paths or hardcode bounds inline.
8. **Filing delete safety**: a file already existing at the destination means the work is done — return early. Never treat destination-existence as a duplicate to delete (this once deleted real files on the network drive).
9. **Coupled pair**: `ingestion_service.py` return dicts and `IngestionReportView` must be audited together — a field added to one silently drops unless mirrored in the other.
10. **Never run raw SQL against the live DB** (`sqldb/gosling2.db`). Triggers write a NULL `batch_id` and the integrity guard then locks all writes. The root-level `gosling.db` is empty/stale — ignore it.

## Working rules

- Something broke at runtime → grep `gosling.log` first (server runs with `reload=True`; don't ask the user to restart or relay logs).
- No emoji or Unicode icons anywhere in source — they have corrupted ID3 JSON serialization before. Plain ASCII strings only.
- Browser-served assets go in `src/static/resources/` (served at `/static/resources/`); the root `resources/` folder is PyInstaller-only.
- Songs can belong to multiple albums; the primary album drives the single ID3 album frame. Test album features against a two-album song.
- Entity renames (artist/composer) are DB-only by design; ID3 files go stale intentionally and are re-synced by a user-triggered bulk write (see `docs/todo/id3_stale_tracking.md`).
- Work in small, review-sized units testable at a seam; the user personally reviews backend diffs. Nudge for a commit when a unit is done; keep commit messages to one terse subject line.
- Before ending a session: `ruff check .`, `black .`, and `pytest` (at minimum the affected modules).
