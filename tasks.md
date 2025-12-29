
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
| T-44 | **Refactor: Dynamic ID3 Read** | 5 | 2 | 20 | ✅ | Dynamic extraction from `id3_frames.json` fully implemented. All 45 tests passing. |
| T-46 | **Proper Album Editor** | 5 | 3 | 15 | ✅ | [spec](design/specs/T-46_PROPER_ALBUM_EDITOR.md) — 4-Pane Console (Context/Vault/Inspector/Sidecar) implemented. |
| T-70 | **Artist Selector** | 5 | 3 | 12 | 🚀 (Next) | T-17 | Replace plain text Artist field with searchable picker (database-backed). Essential for consistent Group metadata. |
| T-17 | **Unified Artist View** | 5 | 3 | 15 | ✅ | [spec](design/issues/T-17_unified_artist_view.md) <br> ([Groups Logic Status](design/state/GROUPS_LOGIC_STATUS.md)) |
| T-18 | **Column Resilience** | 5 | 2 | 20 | ✅ | [docs](design/issues/T-18_column_persistence.md) |
| T-19 | **Field Editor Hardening** | 5 | 3 | 15 | ✅ | [prop](design/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-27 | **Registry Strategies** | 5 | 3 | 15 | ✅ | [prop](design/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-06 | **Legacy Sync** | 5 | 4 | 10 | ✅ | [design/reference/LEGACY_LOGIC.md](design/reference/LEGACY_LOGIC.md) |
| T-01 | **Type Tabs** | 3 | 1 | 15 | ✅ | [done/T-01_type_tabs.md](design/done/T-01_type_tabs.md) |
| — | **Completeness Check** | 3 | 1 | 15 | ✅ | — |
| T-02 | **Field Registry** | 5 | 4 | 10 | ✅ | [done/T-02_field_registry.md](design/done/T-02_field_registry.md) |
| T-15 | **Column Customization**| 4 | 2 | 8 | ✅ | [done/T-15_column_customization.md](design/done/T-15_column_customization.md) |
| T-38 | **Dynamic ID3 Write** | 5 | 3 | 10 | ✅ | [spec](design/specs/T-38_DYNAMIC_ID3_WRITE.md) — Implemented via `FieldDef.id3_tag` in Yellberus (Python Source of Truth). JSON dependency removed.
| T-49 | **Layout Conversion** | 5 | 4 | 20 | ✅ | [spec](design/specs/T-49_RADIO_AUTOMATION_LAYOUT_CONVERSION.md) — Transformation to Frameless Workstation. |
| T-54 | **Surgical Right-Channel**| 5 | 3 | 15 | ✅ | [spec](design/specs/T-54_VISUAL_ARCHITECTURE.md) — The Command Deck (Toggle Stack) with Tactical Transitions. |
| T-50 | **Dynamic Renaming Rules** | 5 | 2 | 20 | ✅ | Externalize hardcoded 'Patriotic/Cro' logic to config file. |
| T-51 | **Tag Verification** | 5 | 1 | 25 | 📋 | Verify `TXXX:GOSLING_DONE` ID3 writes. |
| T-52 | **Settings UI** | 5 | 2 | 20 | 📋 | UI for Root Directory & Rules. |
| T-65 | **Audit Crossfade Logic** | 4 | 3 | 12 | 📋 | Investigate audio artifacts/timing in transitions. "Something sounds off". |

### Foundation Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-28 | **Refactor: Leviathans** | 4 | 4 | 8 | 📋 | — | SPLIT: library_widget, yellberus, field_editor, song_repository. **song_repository issues**: Raw SQL in `_sync_album`/`_sync_publisher` (should use repos with `conn` param); fragile tuple unpacking in `get_by_path` (use named columns). **Audit**: Remove useless 1-line wrapper methods (pointless indirection). |
| — | **Schema Update** | 5 | 3 | 10 | ✅ | — | — |
| T-05 | **Audit Log (History)** | 5 | 2 | 20 | 📋 | Schema | [spec](design/issues/T-05_log_core.md) |
| T-13 | **Undo Core** | 4 | 2 | 8 | 📋 | Log Core | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-07 | **Logging Migration** | 3 | 2 | 6 | 📋 | — | [design/LOGGING.md](design/LOGGING.md) |
| T-61 | **Universal Tag Picker** | 2 | 4 | 2 | 💡 | Core | Tree-based dialog for Tags (Genre/Mood/etc) with Color Pills. |
| T-62 | **Async Background Save** | 2 | 3 | 2 | ⚡ | Perf | Move save/renaming operations to background thread to prevent UI freeze on bulk edits. |
| T-63 | **Selectable Publisher Picker** | 2 | 2 | 2 | 🏢 | Core | Convert Publisher text input in Album Manager to a searchable picker/dropdown for data integrity. |
| T-68 | **Background Import** | 5 | 4 | 10 | 📋 | — | Move file copy, zip extraction, and FFmpeg conversion to worker thread. Fixes UI freeze during large imports. |
| T-64 | **Album Disambiguation** | 2 | 3 | 4 | 📀 | UX | Enhance Album Manager search results with sub-labels (Year, Publisher, etc.) to distinguish between duplicate titles like 'Greatest Hits'. |
| T-53 | **UI Polish (Cyber)** | 4 | 2 | 8 | 🏗️ PARTIAL | — | Grid Colors Done. **Issue**: SVG Icon renders tiny. |
| T-57 | **Settings Entry Point** | 3 | 1 | 15 | 💡 | — | Move App Icon to Top-Left and use as click-trigger for Settings. |
| T-34 | **MD Tagging Conventions** | 3 | 1 | 15 | 📋 | Post-0.1 | [spec](design/specs/T-34_MD_TAGGING_CONVENTIONS.md) — Document frontmatter tag vocabulary. *Logged by Vesper.* |
| T-36 | **Architecture Map Update** | 3 | 2 | 6 | 📋 | Post-0.1 | Update [ARCHITECTURE.md](ARCHITECTURE.md) — Missing: `src/core/`, `tools/`, `album.py`, `tag.py`, new repos. Schema section outdated. *Logged by Vesper.* |
| T-69 | **The Album Crisis** | 5 | 4 | 5 | 🧠 | T-46 | RETHINK: What is a "Delete"? Currently, unlinking an album stages $N$ file writes (too heavy). Deletion should probably be a lightweight consequence of empty state, not a mass-write event. |

### Feature Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-55 | **Custom Field Groups** | 4 | 2 | 12 | 🚀 (Next) | Field Editor | Allow users to define field groups (Collapsible) in Settings instead of hardcoded 'Core/Advanced'. Must include "ISRC" as collapsible/toggleable for workflow efficiency. |
| T-12 | **Side Panel** | 5 | 3 | 10 | ✅ | — | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) <br> (Includes: Validation, Editing, Ctrl+S) |
| T-03 | **Inline Edit** | 4 | 2 | 8 | 📋 | — | [spec](design/issues/T-03_inline_edit.md) |
| T-10 | **Basic Chips** | 3 | 2 | 6 | 📋 | — | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-11 | **View Modes** | 3 | 4 | 6 | 📋 | Type Tabs | [spec](design/proposals/PROPOSAL_LIBRARY_VIEWS.md) |
| T-14 | **Smart Chips** | 3 | 3 | 6 | 📋 | Basic Chips | [spec](design/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-16 | **Advanced Search** | 3 | 3 | 9 | 📋 | — | [spec](design/issues/T-16_advanced_search.md) |
| T-31 | **Legacy Shortcuts** | 4 | 2 | 8 | ✅ | — | [spec](design/issues/T-31_legacy_shortcuts.md) |
| T-40 | **Bulk Set Operations** | 3 | 4 | 6 | 📋 | Side Panel | (+/-) Additive/Subtractive tagging for genres/performers in bulk mode. |
| T-41 | **Portable/Required Audit** | 4 | 2 | 8 | 📋 | — | Ensure all `required=True` fields are also `portable=True` to prevent 'Ghost Metadata' that only exists in DB. |
| T-42 | **Field Reordering** | 4 | 3 | 12 | 📋 | Field Editor | Allow valid drag-and-drop reordering in Field Editor to control UI flow. |
| T-43 | **Custom Field Groups** | 3 | 2 | 12 | 📋 | Field Editor | Allow users to define custom groups in Field Editor instead of hardcoded 'Core/Advanced'. |
| T-45 | **Compilation Paradox** | 3 | 4 | 6 | 📋 | Renaming Service | Investigate/Solve handling of re-releases ("Best of") vs Original Year in folder structure to avoid duplicates/fragmentation. |
| T-48 | **Duplicate Detection** | 5 | 3 | 12 | ✅ | [proposal](design/proposals/PROPOSAL_DUPLICATE_DETECTION.md) |
| T-47 | **Duplicate Quality Upgrade Prompt** | 3 | 2 | 9 | 📋 | Duplicate Detection (T-48) | When ISRC duplicate found with higher bitrate, prompt user: "Higher quality version found. Replace existing?" instead of auto-importing both. |
| T-97 | **Surgery Safety Integration** | 5 | 2 | 15 | 💡 | T-54 | **The Lockout Protocol**. When `[SURGERY]` is active: Transport outlines turn "Caution Yellow"; Hotkeys disabled; Buttons require Long-Press. |
| T-66 | **Scrubber Window** | 4 | 3 | 12 | 💡 | — | Double-click (or modifier-click TBD) on library song opens floating scrubber window. Allows preview playback, timeline jumping, without affecting main playback. Like a mini-player popup. |
| T-67 | **Filter Tree LCD Glow** | 4 | 2 | 8 | 📋 | — | Add cyber-glow effect to the count LCDs in the filter tree for consistent aesthetics. |

### Heavy Lift (Defer)
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-20 | **Bulk Edit** | 4 | 4 | 8 | 🚀 | Side Panel | [spec](design/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-21 | **Saved Playlists** | 4 | 3 | 8 | 📋 | — | [spec](design/proposals/PROPOSAL_PLAYLISTS.md) |
| — | **Relational Logging** | 3 | 4 | 6 | ⏸️ | Undo Core | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-26 | **Audit UI** | 3 | 3 | 6 | ⏸️ | Relational Logging | [spec](design/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-22 | **Albums** | 4 | 4 | 8 | 📋 | Legacy Sync | [spec](design/proposals/PROPOSAL_ALBUMS.md) |
| T-37 | **Album Filter Disambiguation** | 2 | 2 | 4 | 📋 | T-22 | Show "(Artist)" in album filter to distinguish "Greatest Hits (ABBA)" from "Greatest Hits (Queen)". *Logged by Vesper.* |
| T-23 | **Filter Trees** | 3 | 3 | 6 | 📋 | Legacy Sync | [spec](design/proposals/PROPOSAL_FILTER_TREES.md) <br>*(Note: Treat 'Groups' as meta-Artist for filtering)* |
| T-24 | **Renaming Service** | 4 | 4 | 8 | ⏸️ | Field Registry | [spec](design/proposals/PROPOSAL_RENAMING_SERVICE.md) |
| T-25 | **PlayHistory** | 3 | 3 | 9 | ⏸️ | Log Core | DATABASE.md |
| T-30 | **Broadcast Automation** | 2 | 5 | 2 | ⏸️ | Everything | [spec](design/proposals/PROPOSAL_BROADCAST_AUTOMATION.md) |
| T-32 | **Pending Review Workflow** | 3 | 3 | 6 | 📋 | Tags (T-06 Phase 3) | [spec](design/proposals/PROPOSAL_ALBUMS.md#7-migration-plan-task-t-22) |
| T-33 | **AI Playlist Generation** | 2 | 5 | 2 | 💡 | Post-1.0 | [spec](design/ideas/T-33_AI_PLAYLIST.md) |
| T-35 | **Music API Lookup** | 3 | 4 | 6 | 💡 | Post-1.0 | [spec](design/ideas/IDEA_music_api_lookup.md) — MusicBrainz/Discogs/Spotify. Workflow: Import (Pending Check) -> Background Worker -> (Found Data) -> Tag as 'Pending Review' -> Human Review -> Mark 'Done'. *Logged by Vesper.* |
| T-39 | **MediaItem Composition** | 2 | 3 | 4 | 💡 | Post-1.0 | [idea](design/ideas/IDEA_media_item_composition.md) — Wrapper for Song/Jingle/VoiceTrack for radio automation. Option 3. *Logged by Vesper.* |

---

## 🚀 The Golden Path (v2.2)

> **Revised**: Tests must be hardened (dynamic) BEFORE schema expansion (Migration) to avoid breaking.

```
 TRACK A (Data):   Item Cleaning ──► Legacy Sync ──► Log+Undo
                       🧹             💾             📜
                   [Immediate]       [Next]         [Soon]

 TRACK B (UI):     Side Panel ──► Inline Edit ──► Bulk Edit
                       ✅              ✏️             📝
                   [Complete]      [Parallel]      [Next]

                   ✅ Field Editor — DONE
```

### Track A: Data Integrity (Critical Path)
1. **Item Cleaning** — ✅ DONE (Field Editor Verified)
2. **Unified Artist View** — ✅ DONE (Combined Groups + Artists)
3. **Legacy Sync** — ✅ DONE (Albums, Genres, Publishers implemented).
4. **Log Core** — Add history tracking. (T-05)

### Track B: User Experience (UI)
1. **Side Panel** — ✅ DONE (Validation, Editing, Shortcuts).
2. **Inline Edit** — Can proceed in parallel.
3. **Bulk Edit** — Next Logic Step.

---

## ⚠️ Known Tech Debt

| Area | Issue | Trigger to Fix |
|------|-------|----------------|
| **Hardcoded ID3 Read** | `metadata_service.py` manually calls `get_text_list("TCON")` etc. MUST use `id3_frames.json` mapping. | TOMORROW (T-44). |
| **ID3 Lookup** | JSON loaded twice: once in `field_editor.py` (cached), once in `yellberus_parser.write_field_registry_md()` (not cached). Lookup logic also duplicated. | If this area causes more bugs, extract shared `id3_lookup.py` module. |
| **Custom ID3 Tags** | No way to make a field portable without a JSON mapping. User can't specify TXXX:fieldname or custom frames through UI. | ✅ FIXED (Popup implemented) |
| **Album Duplicates** | `find_by_title` is case-sensitive ("nevermind" != "Nevermind"). And `Greatest Hits` titles merge different artists. | Fix case-sensitivity ASAP. Defer "AlbumArtist" schema change. |
| **Album Renaming** | `AlbumRepository` has no `update()` method. Typo corrections create orphan albums. | Implement update() + proper migration logic. |
| **Publisher Hierarchy** | `Publisher.parent_publisher_id` allows circular references (A→B→A). No validation exists. ~~Also: no "get descendants" query.~~ | Add cycle detection in `set_parent()`. ✅ `get_with_descendants()` implemented. |
| **Repository Duplication** | `AlbumRepository`, `PublisherRepository`, `TagRepository` all have identical CRUD patterns (`get_by_id`, `find_by_name`, `get_or_create`). | Refactor to generic `EntityRepository[T]` base class. ~1 day. |
| **Filter Widget Legacy** | `library_widget.py` has hardcoded legacy filter methods (`_filter_by_performer`, etc.) that are thin wrappers. `filter_widget.py` has legacy signals. | 🏗️ PARTIAL: Moved Incomplete checkbox and cleaned up top layout (Dec 25). |
| **Hardcoded Year Autofill** | `SidePanel` hardcodes "Set current year if empty". Should be configurable in Settings. | One Day (Settings UI). |
| **Hardcoded Composer Splitter** | `SidePanel` auto-splits CamelCase composers if ending in comma. | One Day (Settings UI). |
| **Editor Footer Layout** | Status Pill (AIR) text clipped by Save Button. Buttons too wide for panel. | ⚠️ URGENT (T-60 UI Polish). |

---

## 📚 Reference Docs

| Doc | Purpose |
|-----|---------|
| [DATABASE.md](design/DATABASE.md) | Schema governance |
| [TESTING.md](TESTING.md) | 10-layer yelling |
| [LOGGING.md](design/LOGGING.md) | Logging Architecture |
| [UX_UI_CONSTITUTION.md](design/UX_UI_CONSTITUTION.md) | Radio Automation Design Philosophy |
| [METADATA_CONSTITUTION.md](METADATA_CONSTITUTION.md) | The Law of Data Relationships |
