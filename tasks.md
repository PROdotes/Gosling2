
---
tags:
  - type/index
  - status/active
links: []
---
# Gosling2 Task Registry

## 📍 Current State
> **Note**: Use `.venv\Scripts\python` to execute Python scripts or pytest. The global `python` command may fail.

| Area | Status |
|------|--------|
| **Schema Awareness** | ✅ Active (10-layer Enforcement) |
| **Schema Migration** | ✅ MediaSources/Songs (MVP) |
| **Drag & Drop Import** | ✅ Complete (Issue #8) |
| **Metadata Write** | ✅ 28 tests passing |
| **Settings Manager** | ✅ Centralized with DI |
| **Logging System** | 🏗️ Created but not adopted (T-07 Pending) |
| **Unified Artist** | ✅ Complete (Backend + UI) |
| **Column Persistence** | ✅ Named-Identity (T-18) |
| **Registry Strategies** | ✅ Filter Logic (T-27) |
| **Field Editor** | ✅ Hardened (T-19) |

---

## 🎯 Priority Matrix

> **Score** = Priority × (6 - Complexity) — Higher = better value

### Quick Wins (Score ≥10)
| ID | Task | Pri | Cmplx | Score | Status | Spec |
|----|------|-----|-------|-------|--------|------|
| T-04 | **Test Audit** | 5 | 3 | 10 | 🚀 (Next) | [spec](design/proposals/TEST_AUDIT_PLAN.md) |
| T-17 | **Unified Artist View** | 5 | 3 | 15 | ✅ | [spec](design/issues/T-17_unified_artist_view.md) <br> ([Groups Logic Status](design/state/GROUPS_LOGIC_STATUS.md)) |
| T-18 | **Column Resilience** | 5 | 2 | 20 | ✅ | [docs](design/issues/T-18_column_persistence.md) |
| T-19 | **Field Editor Hardening** | 5 | 3 | 15 | ✅ | [prop](design/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-27 | **Registry Strategies** | 5 | 3 | 15 | ✅ | [prop](design/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-06 | **Legacy Sync** | 5 | 4 | 10 | ✅ | [design/reference/LEGACY_LOGIC.md](design/reference/LEGACY_LOGIC.md) |
| T-01 | **Type Tabs** | 3 | 1 | 15 | ✅ | [done/T-01_type_tabs.md](design/done/T-01_type_tabs.md) |
| — | **Completeness Check** | 3 | 1 | 15 | ✅ | — |
| T-02 | **Field Registry** | 5 | 4 | 10 | ✅ | [done/T-02_field_registry.md](design/done/T-02_field_registry.md) |
| T-15 | **Column Customization**| 4 | 2 | 8 | ✅ | [done/T-15_column_customization.md](design/done/T-15_column_customization.md) |

### Foundation Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-28 | **Refactor: Leviathans** | 4 | 4 | 8 | 📋 | — | SPLIT: library_widget, yellberus, field_editor, song_repository. **song_repository issues**: Raw SQL in `_sync_album`/`_sync_publisher` (should use repos with `conn` param); fragile tuple unpacking in `get_by_path` (use named columns). |
| — | **Schema Update** | 5 | 3 | 10 | ✅ | — | — |
| T-05 | **Log Core** | 4 | 2 | 8 | 📋 | Schema | [spec](design/issues/T-05_log_core.md) |
| T-13 | **Undo Core** | 4 | 2 | 8 | 📋 | Log Core | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-07 | **Logging Migration** | 3 | 2 | 6 | 📋 | — | [design/LOGGING.md](design/LOGGING.md) |

### Feature Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-12 | **Side Panel** | 5 | 3 | 10 | 📋 | Legacy Sync | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-03 | **Inline Edit** | 4 | 2 | 8 | 📋 | — | [spec](design/issues/T-03_inline_edit.md) |
| T-10 | **Basic Chips** | 3 | 2 | 6 | 📋 | — | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-11 | **View Modes** | 3 | 4 | 6 | 📋 | Type Tabs | [spec](design/proposals/PROPOSAL_LIBRARY_VIEWS.md) |
| T-14 | **Smart Chips** | 3 | 3 | 6 | 📋 | Basic Chips | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-16 | **Advanced Search** | 3 | 3 | 9 | 📋 | — | [spec](design/issues/T-16_advanced_search.md) |
| T-31 | **Legacy Shortcuts** | 4 | 2 | 8 | 📋 | — | [spec](design/issues/T-31_legacy_shortcuts.md) |

### Heavy Lift (Defer)
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-20 | **Bulk Edit** | 4 | 4 | 8 | ⏸️ | Side Panel | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-21 | **Saved Playlists** | 4 | 3 | 8 | 📋 | — | [spec](design/proposals/PROPOSAL_PLAYLISTS.md) |
| — | **Relational Logging** | 3 | 4 | 6 | ⏸️ | Undo Core | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-26 | **Audit UI** | 3 | 3 | 6 | ⏸️ | Relational Logging | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-22 | **Albums** | 4 | 4 | 8 | 📋 | Legacy Sync | [spec](design/proposals/PROPOSAL_ALBUMS.md) |
| T-23 | **Filter Trees** | 3 | 3 | 6 | 📋 | Legacy Sync | [spec](design/proposals/PROPOSAL_FILTER_TREES.md) <br>*(Note: Treat 'Groups' as meta-Artist for filtering)* |
| T-24 | **Renaming Service** | 4 | 4 | 8 | ⏸️ | Field Registry | [spec](design/proposals/PROPOSAL_RENAMING_SERVICE.md) |
| T-25 | **PlayHistory** | 3 | 3 | 9 | ⏸️ | Log Core | DATABASE.md |
| T-30 | **Broadcast Automation** | 2 | 5 | 2 | ⏸️ | Everything | [spec](design/proposals/PROPOSAL_BROADCAST_AUTOMATION.md) |
| T-32 | **Pending Review Workflow** | 3 | 3 | 6 | 📋 | Tags (T-06 Phase 3) | [spec](design/proposals/PROPOSAL_ALBUMS.md#7-migration-plan-task-t-22) |

---

## 🚀 The Golden Path (v2.2)

> **Revised**: Tests must be hardened (dynamic) BEFORE schema expansion (Migration) to avoid breaking.

```
 TRACK A (Data):   Item Cleaning ──► Legacy Sync ──► Log+Undo
                       🧹             💾             📜
                   [Immediate]       [Next]         [Soon]

 TRACK B (UI):     Side Panel ──► Inline Edit ──► Bulk Edit
                       📋              ✏️             📝
                   [Blocked]       [Parallel]      [Later]

                   ✅ Field Editor — DONE
```

### Track A: Data Integrity (Critical Path)
1. **Item Cleaning** — ✅ DONE (Field Editor Verified)
2. **Unified Artist View** — ✅ DONE (Combined Groups + Artists)
3. **Legacy Sync** — ✅ DONE (Albums, Genres, Publishers implemented).
4. **Log Core** — Add history tracking. (T-05)

### Track B: User Experience (UI)
1. **Side Panel** — Requires Legacy Sync data.
2. **Inline Edit** — Can proceed in parallel.
3. **Bulk Edit** — Dependent on Side Panel logic.

---

## ⚠️ Known Tech Debt

| Area | Issue | Trigger to Fix |
|------|-------|----------------|
| **ID3 Lookup** | JSON loaded twice: once in `field_editor.py` (cached), once in `yellberus_parser.write_field_registry_md()` (not cached). Lookup logic also duplicated. | If this area causes more bugs, extract shared `id3_lookup.py` module. |
| **Custom ID3 Tags** | No way to make a field portable without a JSON mapping. User can't specify TXXX:fieldname or custom frames through UI. | ✅ FIXED (Popup implemented) |
| **Album Duplicates** | `find_by_title` is case-sensitive ("nevermind" != "Nevermind"). And `Greatest Hits` titles merge different artists. | Fix case-sensitivity ASAP. Defer "AlbumArtist" schema change. |
| **Album Renaming** | `AlbumRepository` has no `update()` method. Typo corrections create orphan albums. | Implement update() + proper migration logic. |
| **Publisher Hierarchy** | `Publisher.parent_publisher_id` allows circular references (A→B→A). No validation exists. ~~Also: no "get descendants" query.~~ | Add cycle detection in `set_parent()`. ✅ `get_with_descendants()` implemented. |
| **Repository Duplication** | `AlbumRepository`, `PublisherRepository`, `TagRepository` all have identical CRUD patterns (`get_by_id`, `find_by_name`, `get_or_create`). | Refactor to generic `EntityRepository[T]` base class. ~1 day. |
| **Filter Widget Legacy** | `library_widget.py` has hardcoded legacy filter methods (`_filter_by_performer`, etc.) that are thin wrappers. `filter_widget.py` has legacy signals. | Migrate simple filters to generic `_filter_by_field()`. Keep complex ones (unified_artist). |

---

## 📚 Reference Docs

| Doc | Purpose |
|-----|---------|
| [DATABASE.md](design/DATABASE.md) | Schema governance |
| [TESTING.md](TESTING.md) | 10-layer yelling |
| [LOGGING.md](design/LOGGING.md) | Logging Architecture |
