# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## 0. Agent Protocol for This Repository

This section defines how Warp agents should behave when working in Gosling2.

### 0.1 Collaboration model

- Treat the user as a partner, not a passive consumer.
- Be direct and concise; avoid flattery or "fangirling".
- If you notice risks or better approaches, surface them clearly instead of silently complying.

### 0.2 Phase workflow (SPEC → TEST → CODE)

For any non-trivial change (behavior changes, new features, schema work):

1. **SPEC**
   - Read relevant context (`README.md`, `DATABASE.md`, `TESTING.md`, `TOOLS.md`, `tasks.md`, and the concrete code under `src/` and `tests/`).
   - Draft the most detailed spec you reasonably can, including open questions and explicit assumptions.
   - Expect back-and-forth: the user may revise the spec or supply missing details; update the spec accordingly.
   - Do not start editing code before the spec is explicitly accepted.
2. **TEST**
   - Propose tests (or test changes) that would exercise the agreed spec at the smallest responsible layer.
   - Follow the mirroring rules in `TESTING.md` when choosing locations.
   - Wait for user confirmation before large test-suite reorganizations.
3. **CODE**
   - Implement against the agreed spec and test plan.
   - Run the relevant `pytest` commands and fix any regressions.

For very small edits (typos, comment fixes, trivial refactors) it is acceptable to collapse SPEC/TEST/CODE into a single step, but call this out explicitly.

### 0.3 Debugging discipline (no "vibes")

When investigating failures or bugs:

1. Reproduce the issue precisely (input data, UI actions, commands).
2. Trace the logic: UI → service → repository/model → database/schema.
3. Capture the failure in a test at the smallest layer that can meaningfully express it.
4. Only then change code to make the new test pass, and re-run the suite.

Avoid speculative changes based on intuition alone.

### 0.4 Clean code expectations

When editing or adding code:

- Prefer names that reveal intent; avoid unnecessary abbreviations.
- Keep functions small and single-purpose where practical.
- Minimize the number of arguments; group related data into objects where it clarifies intent.
- Avoid duplication; extract shared logic instead of copy-pasting.
- Use comments to explain **why** something is done, not what the code literally does.

If a requested change would clearly violate these principles (e.g., adding a large god function, duplicating complex logic), the agent should:

1. Briefly point out the conflict with clean-code expectations.
2. Ask whether to proceed anyway or adjust the design.

Once the user confirms the intent, it is acceptable to implement even if the result is not perfectly "clean", but the trade-off should be explicit.

## 1. Command & Environment Guide

All commands are intended to be run from the repository root.

### 1.1 Python environment

`tasks.md` notes that the global `python` on this machine may fail; prefer the virtualenv binary:

```bash
# Create a venv if it does not exist
python -m venv .venv

# Install runtime dependencies
.venv/Scripts/pip install -r requirements.txt

# Install dev/test dependencies
.venv/Scripts/pip install -r requirements-dev.txt
```

On Windows PowerShell in this environment, use backslashes when typing directly in the shell (the key point is to call through `.venv\Scripts\python` / `.venv\Scripts\pip` rather than a global interpreter).

### 1.2 Running the application

From the repo root:

```bash
# Using the virtualenv explicitly
.venv/Scripts/python app.py

# If PATH is already configured, this is equivalent
python app.py
```

This boots the PyQt6 desktop application and auto-creates `sqldb/gosling2.sqlite3` on first run.

### 1.3 Tests

Pytest is configured via `pyproject.toml` with `testpaths = ["tests"]` and ignores `tests/disabled_integrity` by default.

Common patterns:

```bash
# All tests (unit + integration, default verbosity and options from pyproject)
.venv/Scripts/python -m pytest

# All unit tests only
.venv/Scripts/python -m pytest tests/unit

# All integration tests only
.venv/Scripts/python -m pytest tests/integration

# Single test file
.venv/Scripts/python -m pytest tests/unit/data/repositories/test_tag_repository.py

# With coverage over src/
.venv/Scripts/python -m pytest --cov=src tests/
```

Refer to `TESTING.md` and `tests/README.md` for the canonical testing strategy and current consolidation work (Task T-04).

### 1.4 Project tools and scripts

The repo defines several project-specific tools whose ownership boundaries are described in `TOOLS.md`.

**Field Editor (Yellberus field registry)** — `tools/field_editor.py`

```bash
.venv/Scripts/python tools/field_editor.py
```

Use this to manage Yellberus `FieldDef` entries and keep them in sync with `src/core/yellberus.py`, `src/resources/id3_frames.json`, and `design/FIELD_REGISTRY.md`. Do not bypass it by hand-editing field properties in the registry files.

**Fixture injector for tests** — `tests/tools/inject_fixtures.py`

```bash
.venv/Scripts/python tests/tools/inject_fixtures.py
```

Seeds the test database from JSON fixtures (see `tests/fixtures/test_songs.json`). This is strictly for test data, not production.

**Schema and mutation utilities** — `scripts/`

```bash
# Audits the current schema against expectations
.venv/Scripts/python scripts/audit_schema.py

# Validates schema structure/assumptions
.venv/Scripts/python scripts/validate_schema.py

# Inspects contributor/group relationships
.venv/Scripts/python scripts/inspect_groups.py

# Runs targeted mutation-style checks
.venv/Scripts/python scripts/mutation_test.py
```

`seed_dave_grohl.py` is a legacy seeder kept for historical purposes; prefer `tests/tools/inject_fixtures.py` for new work.

## 2. High-Level Architecture & Data Governance

The application is a desktop music library and player built with PyQt6, organized as a strict 3-tier architecture with an additional **core schema/registry layer**.

### 2.1 Layered structure

Top-level layout (see `README.md`, `ARCHITECTURE.md`, and `design/QUICK_START.md`):

- `src/presentation/` — **Presentation layer** (PyQt6 UI)
  - `views/main_window.py`: Main window wiring the library, playlist, and playback controls.
  - `widgets/`: Library grid, playlist widget, filter widget, seek slider, playback controls, metadata viewer dialog.
- `src/business/` — **Business logic layer**
  - `services/library_service.py`: Library operations (querying, import, mutations over songs and contributors).
  - `services/metadata_service.py`: ID3/metadata parsing and normalization using `mutagen` and the field registry.
  - `services/playback_service.py`: Dual-player crossfade engine, queue & playback state.
  - `services/settings_manager.py`: Centralized settings, column layouts, and other persisted UI state.
- `src/data/` — **Data access layer**
  - `database.py` / `database_config.py`: Connection management and schema setup.
  - `models/`: Dataclasses for `MediaSource`, `Song`, `Contributor`, `Role`, `Album`, `Tag`, `Publisher`, etc.
  - `repositories/`: Repositories for songs, media sources, contributors, albums, publishers, tags.
- `src/core/` — **Yellberus schema/field registry and logging**
  - `yellberus.py`: Canonical registry describing all portable/local fields, their constraints, and how they map to DB columns and ID3 frames.
  - `logger.py`: Centralized logging utilities used across layers.
- `src/resources/`
  - `constants.py`: Application-wide constants.
  - `id3_frames.json`: Mapping between Yellberus fields and concrete ID3 frames; coupled to the Field Editor.
- `tests/`
  - Mirrors `src/` by design; see §3 below.

The **database** lives in `sqldb/gosling2.sqlite3` (auto-created) and is defined and documented in `DATABASE.md`. The schema is intentionally larger than what is currently fully implemented; many tables are planned for future broadcast automation and logging.

### 2.2 Yellberus and the "10 Layers of Yell"

Yellberus is the central contract manager ensuring that **database schema, Python models, the field registry, and UI columns all stay in sync**:

- **Source of truth:**
  - Schema: `DATABASE.md` and the actual SQLite schema.
  - Registry: `src/core/yellberus.py` plus `src/resources/id3_frames.json`.
  - Code: `src/data/models/` and `src/data/repositories/`.
  - UI: Presentation-layer widgets that expose/filter fields.
- **Enforcement:**
  - Integrity tests in `tests/unit/core/test_yellberus.py` and related schema tests.
  - Column-name and cross-reference tests in `tests/unit/data/test_*schema*.py`.
  - Additional integrity tests (some currently parked in `tests/disabled_integrity/`) that yell when the schema and code diverge.

When modifying anything related to fields, columns, or ID3 tags:

1. Treat **Yellberus + tests** as the arbiter. If an integrity test fails, align code/schema/registry to it rather than weakening the tests.
2. Do **not** add unused columns or dead schema; `DATABASE.md` explicitly treats unused schema as a bug.
3. Keep `DATABASE.md` and `design/DATABASE.md` in sync with any deliberate schema evolution.

### 2.3 Data model and repositories

Conceptually important tables/entities (see `DATABASE.md` for details):

- `Types`, `MediaSources`, `Songs` — Base media entities.
- `Contributors`, `Roles`, `MediaSourceContributorRoles`, `GroupMembers` — People, groups, and credits.
- `Albums`, `SongAlbums`, `Publishers`, `AlbumPublishers` — Album/publisher structure.
- Future/planned: tags, playlists, audit logs, play history, content rules.

Each model in `src/data/models/` is expected to:

- Map 1:1 to a governed table or join table in `DATABASE.md`.
- Be used exclusively via a repository in `src/data/repositories/`.

Repositories encapsulate SQL and connection management; higher layers (services, UI) should not hand-write SQL or talk directly to the database. When extending the schema, add or update repositories rather than embedding new SQL in services or widgets.

### 2.4 Business services

- **LibraryService** orchestrates repositories to offer higher-level operations (import, search, updates) without exposing SQL or raw schema details.
- **MetadataService** abstracts reading/writing ID3 tags via the Yellberus registry and `id3_frames.json`, ensuring that portable metadata lives inside MP3s.
- **PlaybackService** implements a dual `QMediaPlayer` ping-pong model for crossfades, using timing and type information from the data layer.
- **SettingsManager** persists user preferences, including column layouts that are keyed by **field identity**, not column order, making column persistence resilient to schema evolution.

When adding new features, prefer to extend or add services and keep the presentation layer as thin as possible.

### 2.5 Presentation layer

UI components live under `src/presentation/` and are organized by responsibility:

- `views/main_window.py` wires together the library, playlist, metadata, and playback widgets and injects services.
- `widgets/library_widget.py` exposes the library grid and filters; it is sensitive to column identity and Yellberus field names.
- `widgets/filter_widget.py` handles filter controls and connects to library filtering logic.
- `widgets/playlist_widget.py` and `widgets/seek_slider.py` implement playlist and time-slider behaviors.
- `widgets/metadata_viewer_dialog.py` shows full metadata for a track, driven by the registry.

Changes that impact which fields are visible, filterable, or required should be coordinated with Yellberus and the Field Editor, not done ad hoc in widgets.

## 3. Testing Architecture

`TESTING.md` is the canonical guide; the highlights that matter for agents are:

### 3.1 Laws governing the test suite

- **Law of Mirroring:** `tests/` mirrors `src/` path structure. For example:
  - `src/data/repositories/song_repository.py` → `tests/unit/data/repositories/test_song_repository.py`.
- **Law of Containment:** One component per test file; use nested test classes for organization instead of spawning many small test files.
- **Law of Separation:**
  - Logic tests (`test_{component}.py`) for core behavior and spec-adjacent boundaries.
  - Mutation/robustness tests (`test_{component}_mutation.py`) for garbage/abuse inputs and fuzzing.
  - Integrity tests under `tests/unit/integrity/` (and temporarily `tests/disabled_integrity/`) to enforce contracts between schema, registry, models, and UI.
- **Law of Unity:** Shared fixtures go into `tests/conftest.py` rather than duplicated `setUp` code.

Agents should preserve these laws when adding or moving tests.

### 3.2 Where to put and how to run tests

- New tests for a component belong under the mirrored path in `tests/unit/`.
- Integration flows belong in `tests/integration/` and typically exercise repositories + services + a thin UI layer.
- Integrity tests (Yellberus, schema alignment) must remain fast and loud; do not downgrade failures into warnings.

`pyproject.toml` configures pytest with:

- `testpaths = ["tests"]` so `pytest` from the repo root finds everything.
- `addopts = ["-v", "--strict-markers", "--ignore=tests/disabled_integrity"]` so disabled integrity tests are not run by default.

If you temporarily enable a disabled integrity test during refactors, remember to run it explicitly and either bring it back to green or move it back under `tests/disabled_integrity/` with a clear rationale.

## 4. Schema, Field Registry, and Tooling Rules

When working on schema, field definitions, or ID3 behaviors, follow these repository-specific rules (summarized from `DATABASE.md` and `TOOLS.md`):

1. **Never introduce dead schema.** Every table and column must be used by code and reflected in tests; unused additions are treated as bugs.
2. **Keep the Yellberus registry authoritative.**
   - Add or change field definitions via `tools/field_editor.py`.
   - Only `query_expression` is explicitly safe to edit by hand; other properties (visibility, filter flags, required-ness) should stay under Field Editor control.
3. **Maintain cross-layer alignment:** any change to fields/columns requires coordinated updates to:
   - `src/core/yellberus.py` and `src/resources/id3_frames.json`.
   - `src/data/models/` and `src/data/repositories/`.
   - UI widgets that expose or depend on those fields.
   - Integrity tests under `tests/unit/core/`, `tests/unit/data/`, and related locations.
4. **Respect test-driven governance:**
   - If an integrity test fails after a change, assume the change is incomplete rather than weakening the test.
   - Use `scripts/audit_schema.py` / `scripts/validate_schema.py` alongside pytest when evolving the schema.
5. **Use fixture injection for realistic data:** for schema or field-related work, prefer `tests/tools/inject_fixtures.py` and the JSON fixtures over hand-seeding the DB.

## 5. Key Documentation Entry Points

When you need deeper context beyond the above summary, prefer these documents before diving into arbitrary files:

- `README.md` — Overall project summary, features, and high-level architecture.
- `design/QUICK_START.md` — Refactor overview, before/after structure, and common dev flows.
- `ARCHITECTURE.md` — Early architecture map (marked as outdated; see Task T-36 in `tasks.md` for planned updates). Still useful for understanding the intended layering.
- `DATABASE.md` — Canonical schema description, including current vs planned tables and strict governance rules.
- `TESTING.md` — Test philosophy, the "10 layers of yell", and how integrity tests are organized.
- `TOOLS.md` — Ownership boundaries and rules for `tools/`, `tests/tools/`, and `scripts/`.
- `tasks.md` — Active task registry and roadmap, including notes about environment usage on this machine.

These documents, combined with the architecture summary above, should allow future Warp agents to navigate and modify the codebase safely without rediscovering the invariants from scratch.