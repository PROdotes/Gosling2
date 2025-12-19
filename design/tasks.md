---
tags:
  - type/index
  - status/active
links: []
---
# Gosling2 — Tasks (Dec 18th)

## 📍 Current State

| Area | Status |
|------|--------|
| **Schema Awareness** | ✅ Active (9-layer yelling) |
| **Schema Migration** | ✅ MediaSources/Songs (MVP) |
| **Drag & Drop Import** | ✅ Complete (Issue #8) |
| **Metadata Write** | ✅ 28 tests passing |
| **Settings Manager** | ✅ Centralized with DI |

---

## 🎯 Priority Matrix (Re-scored)

> **Score** = Priority × (6 - Complexity) — Higher = better value

### Quick Wins (Score ≥10)
| Task | Pri | Cmplx | Score | Status |
|------|-----|-------|-------|--------|
| **Type Tabs** | 3 | 1 | 15 | ✅ |
| **Field Registry** | 5 | 4 | 10 | ✅ (T-02) |
| **Completeness Check** | 3 | 1 | 15 | ✅ |
| **Inline Edit** | 4 | 2 | 8 | 📋 |
| **Test Audit** | 4 | 2 | 8 | 📋 |

### Foundation Work
| Task | Pri | Cmplx | Score | Status | Blocked By |
|------|-----|-------|-------|--------|------------|
| **Schema Update** | 5 | 3 | 10 | ✅ | — |
| **Log Core** | 4 | 2 | 8 | 📋 | Schema |
| **Undo Core** | 4 | 2 | 8 | 📋 | Log Core |

### Feature Work
| Task | Pri | Cmplx | Score | Status | Blocked By |
|------|-----|-------|-------|--------|------------|
| **Basic Chips** | 3 | 2 | 6 | 📋 | — |
| **View Modes** | 3 | 4 | 6 | 📋 | Type Tabs |
| **Side Panel** | 4 | 3 | 8 | 📋 | Field Registry |
| **Smart Chips** | 3 | 3 | 6 | 📋 | Basic Chips |

### Heavy Lift (Defer)
| Task | Pri | Cmplx | Score | Status | Blocked By |
|------|-----|-------|-------|--------|------------|
| **Bulk Edit** | 4 | 4 | 8 | ⏸️ | Side Panel |
| **Saved Playlists** | 4 | 3 | 8 | 📋 | — |
| **Relational Logging** | 3 | 4 | 6 | ⏸️ | Undo Core |
| **Audit UI** | 3 | 3 | 6 | ⏸️ | Relational Logging |
| **Albums** | 4 | 4 | 8 | 📋 | — |
| **Filter Trees** | 3 | 3 | 6 | 📋 | — |
| **Renaming Service** | 4 | 4 | 8 | ⏸️ | Field Registry |
| **PlayHistory** | 3 | 3 | 9 | ⏸️ | Log Core |
| **Advanced Search** | 3 | 3 | 9 | 📋 | — | <!-- Issue #10 -->
| **Splashscreen** | 2 | 1 | 10 | 📋 | — | <!-- Issue #11 -->
| **Broadcast Automation** | 2 | 5 | 2 | ⏸️ | Everything |
| **More Stuff** | — | — | — | 📜 | [WISHLIST](.agent/WISHLIST.md) |

---

## 🚀 The Golden Path (v2)

> **Parallel Tracks** — UI features and Core infrastructure can proceed independently.

```
 TRACK A (UI):     Type Tabs ──► Inline Edit ──► Side Panel ──► Bulk Edit
                       🏷️           ✏️              📋            📝
                   [1 day]       [1 day]        [2 days]      [2 days]

 TRACK B (Core):   Field Registry ──► Test Audit ──► Log+Undo
                        🏗️              🧹             📜
                     [2 days]        [1 day]       [2 days]

                   ✅ Schema Migration — DONE
```

### Track A: User-Facing (UI)
1. **Type Tabs** — Filter by content type (immediate, no blockers)
2. **Inline Edit** — Editable metadata cells
3. **Side Panel** — Selection-aware metadata (needs Field Registry)
4. **Bulk Edit** — Multi-select operations

### Track B: Developer-Facing (Core)
1. **Field Registry** — Single source of truth for field definitions
2. **Test Audit** — Consolidate tests using the Registry
3. **Log+Undo** — Transaction safety net

### Crossover Points
- **Side Panel** requires Field Registry (Track B must reach step 1)
- **Test Audit** cleans up the "9 layers of yell" into Registry-based checks

---

## 📦 Task Breakdown

### Library Views → 2 tasks
| Phase | Scope | Proposal |
|-------|-------|----------|
| Type Tabs | Filter tabs for content type | [PROPOSAL_LIBRARY_VIEWS](.agent/PROPOSAL_LIBRARY_VIEWS.md) |
| View Modes | Grid/Detail/Compact switching | ↑ |

### Metadata Editor → 3 tasks
| Phase | Scope | Proposal |
|-------|-------|----------|
| Inline Edit | Editable dialog cells | [PROPOSAL_METADATA_EDITOR](.agent/PROPOSAL_METADATA_EDITOR.md) |
| Side Panel | Single-track panel | ↑ |
| Bulk Edit | Multi-select append/remove | ↑ |

### Transaction Log → 4 tasks
| Phase | Scope | Proposal |
|-------|-------|----------|
| Log Core | ChangeLog table + basic logging | [PROPOSAL_TRANSACTION_LOG](.agent/PROPOSAL_TRANSACTION_LOG.md) |
| Undo Core | Simple field revert | ↑ |
| Relational Logging | Junction + hierarchy edits | ↑ |
| Audit UI | History views | ↑ |

### Tag Editor → 2 tasks
| Phase | Scope | Proposal |
|-------|-------|----------|
| Basic Chips | Visual chip input | [PROPOSAL_TAG_EDITOR](.agent/PROPOSAL_TAG_EDITOR.md) |
| Smart Chips | Autocomplete + create-new | ↑ |

---

## 📚 Reference Docs

| Doc | Purpose |
|-----|---------|
| [DATABASE.md](DATABASE.md) | Schema governance |
| [TESTING.md](TESTING.md) | 9-layer yelling |
| [plan_database.md](plan_database.md) | Phases 1-3 |
| [plan_player.md](plan_player.md) | Phases 4-5 (deferred) |

---

## ✅ Completed
- Settings Manager · Context Menu validation · Drag & Drop · Metadata Write · TKEY flag · Schema enforcement
- **Schema Migration (MVP)**: Files → MediaSources/Songs split, Contributor Roles, DB strictness

