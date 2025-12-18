# Gosling2 Task Registry

> **Score** = Priority × (6 - Complexity) — Higher = better value

---

## 🎯 What's Next

> **T-01: Type Tabs** — Filter library by content type (Music/Jingles/Commercials)  
> [Spec](design/issues/T-01_type_tabs.md) · Layer: UI · Score: 15

---

## 📍 Current State

| Area | Status |
|------|--------|
| Schema Migration | ✅ MediaSources/Songs (MVP) |
| Drag & Drop Import | ✅ Complete |
| Settings Manager | ✅ Centralized |
| Schema Integrity | ✅ 9 Layers active |

---

## 🟢 Active Development

| ID | Task | Layer | Score | Status | Spec |
|----|------|-------|-------|--------|------|
| T-01 | Type Tabs | UI | 15 | 🟢 Next | [spec](design/issues/T-01_type_tabs.md) |
| T-02 | Field Registry | Core | 10 | 🟡 Planned | [spec](design/issues/T-02_field_registry.md) |
| T-03 | Inline Edit | UI | 8 | 🟡 Planned | [spec](design/issues/T-03_inline_edit.md) |
| T-04 | Test Audit | Core | 8 | 🟡 Planned | [spec](design/proposals/TEST_AUDIT_PLAN.md) |
| T-05 | Log Core | Core | 8 | 🟡 Planned | [spec](design/issues/T-05_log_core.md) |

---

## 🟡 Planned (Queued)

| ID | Task | Layer | Score | Status | Blocked By | Spec |
|----|------|-------|-------|--------|------------|------|
| T-10 | Basic Chips | UI | 6 | 📋 | — | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-11 | View Modes | UI | 6 | 📋 | Type Tabs | [spec](design/proposals/PROPOSAL_LIBRARY_VIEWS.md) |
| T-12 | Side Panel | UI | 8 | 📋 | Field Registry | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-13 | Undo Core | Core | 8 | 📋 | Log Core | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-14 | Smart Chips | UI | 6 | 📋 | Basic Chips | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-15 | Column Customization | UI | 8 | 📋 | — | [spec](design/issues/T-15_column_customization.md) |
| T-16 | Advanced Search | UI | 9 | 📋 | — | GitHub #10 |
| T-17 | Splashscreen | UI | 10 | 📋 | — | GitHub #11 |

---

## ⏸️ Deferred (Heavy Lift)

| ID | Task | Layer | Score | Blocked By | Spec |
|----|------|-------|-------|------------|------|
| T-20 | Bulk Edit | UI | 8 | Side Panel | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-21 | Saved Playlists | Data | 8 | — | [spec](design/proposals/PROPOSAL_PLAYLISTS.md) |
| T-22 | Albums | Data | 8 | — | [spec](design/proposals/PROPOSAL_ALBUMS.md) |
| T-23 | Filter Trees | UI | 6 | — | [spec](design/proposals/PROPOSAL_FILTER_TREES.md) |
| T-24 | Renaming Service | Core | 8 | Field Registry | [spec](design/proposals/PROPOSAL_RENAMING_SERVICE.md) |
| T-25 | PlayHistory | Data | 9 | Log Core | DATABASE.md |
| T-26 | Audit UI | UI | 6 | Relational Logging | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |

---

## 🔮 Future (Far Out)

| ID | Task | Layer | Notes | Spec |
|----|------|-------|-------|------|
| T-30 | Broadcast Automation | Core | Needs everything | [spec](design/proposals/PROPOSAL_BROADCAST_AUTOMATION.md) |
| T-31 | On-Air UI | UI | After automation | [spec](design/proposals/PROPOSAL_ONAIR_UI.md) |
| T-32 | More Ideas | — | — | [WISHLIST](design/WISHLIST.md) |

---

## ✅ Completed

- Schema Migration (MVP)
- Drag & Drop Import (Issue #8)
- Settings Manager Centralization (Issue #9)
- Main Window Elements (Issue #1)
- Database Schema (Issue #4)

---

## 🚀 The Golden Path

```
TRACK A (UI):   Type Tabs ──► Inline Edit ──► Side Panel ──► Bulk Edit
                    🏷️           ✏️              📋            📝

TRACK B (Core): Field Registry ──► Test Audit ──► Log+Undo
                    🏗️               🧹             📜
```

**Crossover:** Side Panel requires Field Registry (Track B step 1)
