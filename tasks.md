
---
tags:
  - type/index
  - status/active
links: []
---
# Gosling2 Task Registry

## 📍 Current State

| Area | Status |
|------|--------|
| **Schema Awareness** | ⏸️ Paused (9-layer silenced for Migration) |
| **Schema Migration** | ✅ MediaSources/Songs (MVP) |
| **Drag & Drop Import** | ✅ Complete (Issue #8) |
| **Metadata Write** | ✅ 28 tests passing |
| **Settings Manager** | ✅ Centralized with DI |
| **Logging System** | ✅ Centralized (T-07 Implemented) |

---

## 🎯 Priority Matrix

> **Score** = Priority × (6 - Complexity) — Higher = better value

### Quick Wins (Score ≥10)
| ID | Task | Pri | Cmplx | Score | Status | Spec |
|----|------|-----|-------|-------|--------|------|
| T-04 | **Test Audit** | 5 | 3 | 10 | 🚀 (Next) | [spec](design/proposals/TEST_AUDIT_PLAN.md) |
| T-17 | **Unified Artist View** | 5 | 3 | 15 | 🚀 (Top) | Combine Groups + Artists |
| T-06 | **Legacy Sync** | 5 | 4 | 10 | � | [design/LEGACY_LOGIC.md](design/LEGACY_LOGIC.md) |
| T-01 | **Type Tabs** | 3 | 1 | 15 | ✅ | [spec](design/issues/T-01_type_tabs.md) |
| — | **Completeness Check** | 3 | 1 | 15 | ✅ | — |
| T-02 | **Field Registry** | 5 | 4 | 10 | ✅ | [spec](design/issues/T-02_field_registry.md) |

### Foundation Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
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
| T-16 | **Advanced Search** | 3 | 3 | 9 | 📋 | — | GitHub #10 |

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
2. **Unified Artist View** — 🚀 [Next] Combine Groups + Artists. (Score: 15, Est: 2 hrs)
3. **Legacy Sync** — Add Album, Genre, Publisher. (Score: 10, Est: 4-6 hrs)
4. **Log Core** — Add history tracking.

### Track B: User Experience (UI)
1. **Side Panel** — Requires Legacy Sync data.
2. **Inline Edit** — Can proceed in parallel.
3. **Bulk Edit** — Dependent on Side Panel logic.

---

## 📚 Reference Docs

| Doc | Purpose |
|-----|---------|
| [DATABASE.md](design/DATABASE.md) | Schema governance |
| [TESTING.md](TESTING.md) | 9-layer yelling |
| [LOGGING.md](design/LOGGING.md) | Logging Architecture |
