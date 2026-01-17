
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
| T-46 | **Proper Album Editor** | 5 | 3 | 15 | ✅ | [spec](docs/specs/T-46_PROPER_ALBUM_EDITOR.md) — 4-Pane Console (Context/Vault/Inspector/Sidecar) implemented. |
| T-70 | **Artist Selector** | 5 | 3 | 12 | ✅ | T-17 | Replace plain text Artist field with searchable picker (database-backed). Essential for consistent Group metadata. |
| T-71 | **All Contributors Filter** | 5 | 2 | 20 | ✅ | Implemented recursive "All Contributors" view in Filter Tree with Type Grouping (Groups/People). |
| T-17 | **Unified Artist View** | 5 | 3 | 15 | ✅ | [spec](docs/issues/T-17_unified_artist_view.md) <br> ([Groups Logic Status](docs/state/GROUPS_LOGIC_STATUS.md)) |
| T-18 | **Column Resilience** | 5 | 2 | 20 | ✅ | [docs](docs/issues/T-18_column_persistence.md) |
| T-19 | **Field Editor Hardening** | 5 | 3 | 15 | ✅ | [prop](docs/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-27 | **Registry Strategies** | 5 | 3 | 15 | ✅ | [prop](docs/proposals/PROPOSAL_TOOLING_CONSOLIDATION.md) |
| T-06 | **Legacy Sync** | 5 | 4 | 10 | ✅ | [docs/reference/LEGACY_LOGIC.md](docs/reference/LEGACY_LOGIC.md) |
| T-01 | **Type Tabs** | 3 | 1 | 15 | ✅ | [done/T-01_type_tabs.md](docs/done/T-01_type_tabs.md) |
| — | **Completeness Check** | 3 | 1 | 15 | ✅ | — |
| T-02 | **Field Registry** | 5 | 4 | 10 | ✅ | [done/T-02_field_registry.md](docs/done/T-02_field_registry.md) |
| T-15 | **Column Customization**| 4 | 2 | 8 | ✅ | [done/T-15_column_customization.md](docs/done/T-15_column_customization.md) |
| T-38 | **Dynamic ID3 Write** | 5 | 3 | 10 | ✅ | [spec](docs/specs/T-38_DYNAMIC_ID3_WRITE.md) — Implemented via `FieldDef.id3_tag` in Yellberus (Python Source of Truth). JSON dependency removed.
| T-47 | **GlowFactory Refactor** | 5 | 2 | 20 | ✅ | Split monolithic factory into modular `glow/` package. Implemented `GlowLED`. Unified border/glow logic for inputs and buttons.
| T-49 | **Layout Conversion** | 5 | 4 | 20 | ✅ | [spec](docs/specs/T-49_RADIO_AUTOMATION_LAYOUT_CONVERSION.md) — Transformation to Frameless Workstation. |
| T-54 | **Surgical Right-Channel**| 5 | 3 | 15 | ✅ | [spec](docs/specs/T-54_VISUAL_ARCHITECTURE.md) — The Command Deck (Toggle Stack) with Tactical Transitions. |
| T-50 | **Dynamic Renaming Rules** | 5 | 2 | 20 | ✅ | Externalize hardcoded 'Patriotic/Cro' logic to config file. |
| T-51 | **Tag Verification** | 5 | 1 | 25 | ✅ | Verify `TXXX:GOSLING_DONE` ID3 writes. |
| T-52 | **Settings UI** | 5 | 2 | 20 | 📋 | UI for Root Directory & Rules. |
| T-102 | **"Show Truncated" Filter** | 5 | 2 | 20 | 📋 | Gosling 1 parity: filter songs missing Composer/Publisher. Weekly workflow essential. |
| T-103 | **ZAMP Search Button** | 5 | 1 | 25 | 📋 | Add ZAMP.hr to web search buttons for Croatian rights lookup. |
| T-104 | **Completeness Indicator** | 5 | 2 | 20 | 📋 | Visual marker in grid showing missing required fields. |
| T-105 | **Quick Lookup (Ctrl+F)** | 4 | 1 | 20 | 📋 | Focus search box on Ctrl+F for fast Title+Artist lookup. |
| T-65 | **Audit Crossfade Logic** | 4 | 3 | 12 | ⏸️ Post-0.1 | Investigate audio artifacts/timing in transitions. |

### Foundation Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-28 | **Refactor: Leviathans** | 4 | 4 | 8 | 📋 | — | [**MASTER PLAN**](docs/proposals/MODULARIZATION_MASTER_PLAN.md) — SPLIT: `library_widget` (2032→7 modules), `side_panel_widget` (1465→6), `yellberus` (673→5), `main_window` (763→5), `filter_widget` (730→4). |
| — | **Schema Update** | 5 | 3 | 10 | ✅ | — | — |
| T-05 | **Audit Log (History)** | 5 | 2 | 20 | 📋 | Schema | [spec](docs/issues/T-05_log_core.md) |
| T-13 | **Undo Core** | 4 | 2 | 8 | 📋 | Log Core | [spec](docs/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-07 | **Logging Migration** | 3 | 2 | 6 | 📋 | — | [docs/LOGGING.md](docs/LOGGING.md) |
| T-61 | **Universal Tag Picker** | 2 | 4 | 2 | 💡 | Core | Tree-based dialog for Tags (Genre/Mood/etc) with Color Pills. |
| T-62 | **Async Background Save** | 2 | 3 | 2 | ⚡ | Perf | Move save/renaming operations to background thread to prevent UI freeze on bulk edits. |
| T-82 | **Web Search Affinity** | 4 | 2 | 8 | ✅ | — | [prop](docs/proposals/PROPOSAL_WEB_SEARCH_AFFINITY.md) — Connect empty fields (Composer) to search button via inline icons/labels. |
| T-83 | **Publisher Jump** | 4 | 2 | 8 | ✅ | — | [prop](docs/proposals/PROPOSAL_PUBLISHER_JUMP.md) — Allow editing album properties (Publisher) directly from Song view via jump-badge/link. |
| T-63 | **Selectable Publisher Picker** | 2 | 2 | 2 | 🏢 | Core | Convert Publisher text input in Album Manager to a searchable picker/dropdown for data integrity. |
| T-68 | **Background Import** | 5 | 4 | 10 | 📋 | — | Move file copy, zip extraction, and FFmpeg conversion to worker thread. Fixes UI freeze during large imports. |
| T-64 | **Album Disambiguation** | 2 | 3 | 4 | 📀 | UX | Enhance Album Manager search results with sub-labels (Year, Publisher, etc.) to distinguish between duplicate titles like 'Greatest Hits'. |
| T-53 | **UI Polish (Cyber)** | 4 | 2 | 8 | 🏗️ PARTIAL | — | Grid Colors Done. **Issue**: SVG Icon renders tiny. |
| T-57 | **Settings Entry Point** | 3 | 1 | 15 | ✅ | — | Move App Icon to Top-Left and use as click-trigger for Settings. |
| T-34 | **MD Tagging Conventions** | 3 | 1 | 15 | 📋 | Post-0.1 | [spec](docs/specs/T-34_MD_TAGGING_CONVENTIONS.md) — Document frontmatter tag vocabulary. *Logged by Vesper.* |
| T-36 | **Architecture Map Update** | 3 | 2 | 6 | 📋 | Post-0.1 | Update [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Missing: `src/core/`, `tools/`, `album.py`, `tag.py`, new repos. Schema section outdated. *Logged by Vesper.* |
| T-69 | **The Album Crisis** | 5 | 4 | 5 | 🧠 | T-46 | RETHINK: What is a "Delete"? Currently, unlinking an album stages $N$ file writes (too heavy). Deletion should probably be a lightweight consequence of empty state, not a mass-write event. |

### Feature Work
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-55 | **Custom Field Groups** | 4 | 2 | 12 | 🚀 (Next) | Field Editor | Allow users to define field groups (Collapsible) in Settings instead of hardcoded 'Core/Advanced'. Must include "ISRC" as collapsible/toggleable for workflow efficiency. |
| T-12 | **Side Panel** | 5 | 3 | 10 | ✅ | — | [spec](docs/proposals/PROPOSAL_METADATA_EDITOR.md) <br> (Includes: Validation, Editing, Ctrl+S) |
| T-03 | **Inline Edit** | 4 | 2 | 8 | 📋 | — | [spec](docs/issues/T-03_inline_edit.md) |
| T-10 | **Basic Chips** | 3 | 2 | 6 | 📋 | — | [spec](docs/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-14 | **Smart Chips** | 3 | 3 | 6 | 📋 | Basic Chips | [spec](docs/proposals/PROPOSAL_TAG_EDITOR.md) |
| T-16 | **Advanced Search** | 3 | 3 | 9 | 📋 | — | [spec](docs/issues/T-16_advanced_search.md) |
| T-31 | **Legacy Shortcuts** | 4 | 2 | 8 | ✅ | — | [spec](docs/issues/T-31_legacy_shortcuts.md) |
| T-40 | **Bulk Set Operations** | 3 | 4 | 6 | 📋 | Side Panel | (+/-) Additive/Subtractive tagging for genres/performers in bulk mode. |
| T-41 | **Portable/Required Audit** | 4 | 2 | 8 | 📋 | — | Ensure all `required=True` fields are also `portable=True` to prevent 'Ghost Metadata' that only exists in DB. |
| T-42 | **Field Reordering** | 4 | 3 | 12 | 📋 | Field Editor | Allow valid drag-and-drop reordering in Field Editor to control UI flow. |
| T-43 | **Custom Field Groups** | 3 | 2 | 12 | 📋 | Field Editor | Allow users to define custom groups in Field Editor instead of hardcoded 'Core/Advanced'. |
| T-45 | **Compilation Paradox** | 3 | 4 | 6 | 📋 | Renaming Service | Investigate/Solve handling of re-releases ("Best of") vs Original Year in folder structure to avoid duplicates/fragmentation. |
| T-48 | **Duplicate Detection** | 5 | 3 | 12 | ✅ | [proposal](docs/proposals/PROPOSAL_DUPLICATE_DETECTION.md) |
| T-98 | **Mood Support** | 5 | 2 | 20 | ✅ | — | Implemented distinct tagging system (TMOO) parallel to Genre. |
| T-47 | **Duplicate Quality Upgrade Prompt** | 3 | 2 | 9 | 📋 | Duplicate Detection (T-48) | When ISRC duplicate found with higher bitrate, prompt user: "Higher quality version found. Replace existing?" instead of auto-importing both. |
| T-84 | **System SVGs** | 4 | 2 | 8 | ⏸️ Post-0.1 | UI | Replace Unicode icons in TitleBar/SystemIsland with crisp SVGs. |
| T-97 | **Surgery Safety Integration** | 5 | 2 | 15 | ⏸️ Post-0.1 | T-54 | Automation feature. Defer to v0.2. |
| T-101 | **Surgical Credits (Jobs)** | 3 | 4 | 12 | 💡 | Core | [spec](docs/tasks/T-101_surgical_credits_plan.md) — Multi-role support for ZAMP. |
| T-66 | **Scrubber Window** | 4 | 3 | 12 | ⏸️ Post-0.1 | — | Playback feature. Defer to v0.2. |
| T-67 | **Filter Tree LCD Glow** | 4 | 2 | 8 | ⏸️ Post-0.1 | — | UI polish. Defer to v0.2. |
| T-106 | **Song Relationships** | 3 | 3 | 9 | 📋 | — | [spec](docs/specs/song_relationships_spec.md) — Link songs (remixes, samples, covers, parodies). Includes Version Folding plan. |

### Heavy Lift (Defer)
| ID | Task | Pri | Cmplx | Score | Status | Blocked By | Spec |
|----|------|-----|-------|-------|--------|------------|------|
| T-20 | **Bulk Edit** | 4 | 4 | 8 | 🚀 | Side Panel | [spec](docs/proposals/PROPOSAL_METADATA_EDITOR.md) |
| T-21 | **Saved Playlists** | 4 | 3 | 8 | ⏸️ Post-0.1 | — | Automation feature. Defer to v0.2. |
| — | **Relational Logging** | 3 | 4 | 6 | ⏸️ | Undo Core | [spec](docs/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-26 | **Audit UI** | 3 | 3 | 6 | ⏸️ | Relational Logging | [spec](docs/proposals/PROPOSAL_TRANSACTION_LOG.md) |
| T-22 | **Albums** | 4 | 4 | 8 | 📋 | Legacy Sync | [spec](docs/proposals/PROPOSAL_ALBUMS.md) |
| T-37 | **Album Filter Disambiguation** | 2 | 2 | 4 | 📋 | T-22 | Show "(Artist)" in album filter to distinguish "Greatest Hits (ABBA)" from "Greatest Hits (Queen)". *Logged by Vesper.* |
| T-23 | **Filter Trees** | 3 | 3 | 6 | 📋 | Legacy Sync | [spec](docs/proposals/PROPOSAL_FILTER_TREES.md) <br>*(Note: Treat 'Groups' as meta-Artist for filtering)* |
| T-24 | **Renaming Service** | 4 | 4 | 8 | ⏸️ | Field Registry | [spec](docs/proposals/PROPOSAL_RENAMING_SERVICE.md) |
| T-25 | **PlayHistory** | 3 | 3 | 9 | ⏸️ Post-0.1 | Log Core | Automation feature. Defer to v0.2. |
| T-30 | **Broadcast Automation** | 2 | 5 | 2 | ⏸️ | Everything | [spec](docs/proposals/PROPOSAL_BROADCAST_AUTOMATION.md) |
| T-32 | **Pending Review Workflow** | 3 | 3 | 6 | 📋 | Tags (T-06 Phase 3) | [spec](docs/proposals/PROPOSAL_ALBUMS.md#7-migration-plan-task-t-22) |
| T-33 | **AI Playlist Generation** | 2 | 5 | 2 | 💡 | Post-1.0 | [spec](docs/ideas/T-33_AI_PLAYLIST.md) |
| T-35 | **Music API Lookup** | 3 | 4 | 6 | 💡 | Post-1.0 | [spec](docs/ideas/IDEA_music_api_lookup.md) — MusicBrainz/Discogs/Spotify. Workflow: Import (Pending Check) -> Background Worker -> (Found Data) -> Tag as 'Pending Review' -> Human Review -> Mark 'Done'. *Logged by Vesper.* |
| T-81 | [Heavy Lift] Restore Web Search & Settings |  | **DONE** | [Spec](docs/specs/T-81_restore_web_search.md) |
| T-39 | **MediaItem Composition** | 2 | 3 | 4 | 💡 | Post-1.0 | [idea](docs/ideas/IDEA_media_item_composition.md) — Wrapper for Song/Jingle/VoiceTrack for radio automation. Option 3. *Logged by Vesper.* |

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
| **Hardcoded Year Autofill** | `SidePanel` hardcodes "Set current year if empty". Should be configurable in Settings. | One Day (Settings UI). |
| **Hardcoded Composer Splitter** | `SidePanel` auto-splits CamelCase composers if ending in comma. | One Day (Settings UI). |
| **Publisher Hierarchy** | `Publisher.parent_publisher_id` allows circular references (A→B→A). No validation exists. | ✅ `get_with_descendants()` implemented. UI visualization added. |

---

## 📚 Reference Docs

| Doc | Purpose |
|-----|---------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Release milestones & progress |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema governance |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture overview |
| [docs/TESTING.md](docs/TESTING.md) | 10-layer yelling |
| [docs/LOGGING.md](docs/LOGGING.md) | Logging Architecture |
| [docs/QUICK_START.md](docs/QUICK_START.md) | Developer onboarding |
| [docs/UX_UI_CONSTITUTION.md](docs/UX_UI_CONSTITUTION.md) | Radio Automation Design Philosophy |
| [docs/METADATA_CONSTITUTION.md](docs/METADATA_CONSTITUTION.md) | The Law of Data Relationships |
| [docs/FIELD_REGISTRY.md](docs/FIELD_REGISTRY.md) | Field definitions & ID3 mappings |
| [docs/proposals/MODULARIZATION_MASTER_PLAN.md](docs/proposals/MODULARIZATION_MASTER_PLAN.md) | Big File Refactoring Plan (T-28) |
| [docs/proposals/GENERIC_REPOSITORY_ARCHITECTURE.md](docs/proposals/GENERIC_REPOSITORY_ARCHITECTURE.md) | Repository pattern design |
| [docs/TEST_REMEDIATION_PLAN.md](docs/TEST_REMEDIATION_PLAN.md) | Test Suite Status (430 tests) |
| [docs/MASS_REFACTOR_WORKFLOW.md](docs/MASS_REFACTOR_WORKFLOW.md) | Mass Refactor / Audit Protocol |
| [docs/REFACTOR_AUDIT.md](docs/REFACTOR_AUDIT.md) | Refactor Audit: Tag Categories |
| [docs/STRATEGY_v0.2.md](docs/STRATEGY_v0.2.md) | Strangler Fig Refactor Strategy |
| [docs/LOCALIZATION_STRATEGY.md](docs/LOCALIZATION_STRATEGY.md) | i18n implementation plan |
| [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md) | High-level project overview |
| [docs/VERSION_PLAN.md](docs/specs/VERSION_PLAN.md) | Release versioning strategy |
| [docs/proposals/YELLBERUS_MODULARIZATION.md](docs/proposals/YELLBERUS_MODULARIZATION.md) | Yellberus split plan (T-28) |
| [docs/WISHLIST.md](docs/specs/WISHLIST.md) | User-requested features backlog |

---

## 🗃️ Completed Task Archive

Specs for completed tasks are archived in `docs/done/`:

| Task | Spec |
|------|------|
| T-01 | [Type Tabs](docs/done/T-01_type_tabs.md) |
| T-02 | [Field Registry](docs/done/T-02_field_registry.md) |
| T-04 | [Test Consolidation](docs/done/T04_TEST_CONSOLIDATION_PLAN.md) |
| T-05 | [Audit Log Viewer](docs/done/T-05_audit_log_viewer_plan.md) |
| T-12 | [Side Panel Alpha](docs/done/T12_SIDE_PANEL_ALPHA_SPEC.md) |
| T-15 | [Column Customization](docs/done/T-15_column_customization.md) |
| T-19 | [Field Editor Hardening](docs/done/T-19_field_editor_hardening.md) |
| T-38 | [Dynamic ID3 Write](docs/done/T-38_DYNAMIC_ID3_WRITE.md) |
| T-44 | [Dynamic ID3 Read](docs/done/T-44_DYNAMIC_ID3_READ.md) |
| T-46 | [Proper Album Editor](docs/done/T-46_PROPER_ALBUM_EDITOR.md) |
| T-49 | [Radio Automation Layout](docs/done/T-49_RADIO_AUTOMATION_LAYOUT_CONVERSION.md) |
| T-54 | [Visual Architecture](docs/done/T-54_VISUAL_ARCHITECTURE.md) |
| T-55 | [Chip Bay Styles](docs/done/T-55_CHIP_BAY_STYLES.md) |
| T-70 | [Artist Manager](docs/done/T-70_artist_manager_plan.md) |
| T-81 | [Restore Web Search](docs/done/T-81_restore_web_search.md) |
| T-85 | [Universal Input Dialog](docs/done/T-85_universal_input_dialog.md) |

---

## 💡 Idea Bank (Future Features)

All ideas are stored in `docs/ideas/`. Browse by category:

### 🎙️ Broadcast & Automation
| Idea | Description |
|------|-------------|
| [Broadcast Automation](docs/proposals/PROPOSAL_BROADCAST_AUTOMATION.md) | Full radio automation system |
| [Clock Templates](docs/ideas/IDEA_clock_templates.md) | Hour format templates |
| [Commercial Scheduler](docs/ideas/IDEA_commercial_scheduler.md) | Ad scheduling system |
| [Dayparting](docs/ideas/IDEA_dayparting.md) | Time-based scheduling |
| [Rotation Rules](docs/ideas/IDEA_rotation_rules.md) | Music rotation logic |
| [Schedule Generator](docs/ideas/IDEA_schedule_generator.md) | Auto-generate playlists |
| [Separation Rules](docs/ideas/IDEA_separation_rules.md) | Artist/song spacing |
| [Silence Detection](docs/ideas/IDEA_silence_detection.md) | Dead air detection |
| [Silence Failover](docs/ideas/IDEA_silence_failover.md) | Auto-recovery from silence |
| [Teaser Mode](docs/ideas/IDEA_teaser_mode.md) | Song preview snippets |
| [Voice Ducking](docs/ideas/IDEA_voice_ducking.md) | Auto-lower music for voice |

### 🎵 Audio & Processing
| Idea | Description |
|------|-------------|
| [Audio Fingerprinting](docs/ideas/IDEA_audio_fingerprinting.md) | AcoustID/Shazam matching |
| [Auto Audio Analysis](docs/ideas/IDEA_auto_audio_analysis.md) | BPM, cue points, voice detection on import |
| [Audio Cue Detection](docs/ideas/IDEA_audio_cue_detection.md) | Detect news outro → trigger fade (standalone bot!) |
| [Auto Teaser Generator](docs/ideas/IDEA_auto_teaser_generator.md) | Generate song previews |
| [Builtin Encoder](docs/ideas/IDEA_builtin_encoder.md) | Streaming encoder |
| [File Format Conversion](docs/ideas/IDEA_file_format_conversion.md) | Transcode on import |
| [Loudness Normalization](docs/ideas/IDEA_loudness_normalization.md) | EBU R128 compliance |
| [Multiple Outputs](docs/ideas/IDEA_multiple_outputs.md) | Multi-channel routing |
| [Preview Hook](docs/ideas/IDEA_preview_hook.md) | Headphone cue system |
| [VST/DSP Support](docs/ideas/IDEA_vst_dsp_support.md) | Audio plugin hosting |

### 📊 Data & Metadata
| Idea | Description |
|------|-------------|
| [AI Playlist Generation](docs/ideas/T-33_AI_PLAYLIST.md) | ML-powered playlists |
| [Autofill on Import](docs/ideas/IDEA_autofill_on_import.md) | Auto-populate metadata |
| [Crowd Sourced Data](docs/ideas/IDEA_crowd_sourced_data.md) | Community metadata |
| [Last Played Tracking](docs/ideas/IDEA_last_played_tracking.md) | Play history analytics |
| [Library Intelligence](docs/ideas/IDEA_library_intelligence.md) | Chart gaps, wishlist, alias search |
| [Music API Lookup](docs/ideas/IDEA_music_api_lookup.md) | MusicBrainz/Discogs/Spotify |
| [Statistics Dashboard](docs/ideas/IDEA_statistics_dashboard.md) | Usage analytics |
| [Universal Tag Picker](docs/ideas/IDEA_UNIVERSAL_TAG_PICKER.md) | Tree-based tag selection |

### 🌐 Remote & Integration
| Idea | Description |
|------|-------------|
| [ASCAP/BMI Export](docs/ideas/IDEA_export_ascap_bmi.md) | Royalty reporting |
| [Affidavit Generator](docs/ideas/IDEA_affidavit_generator.md) | Proof of airing reports |
| [Cloud Sync](docs/ideas/IDEA_gosling_cloud_sync.md) | Multi-station sync |
| [GPIO Fader Start](docs/ideas/IDEA_gpio_fader_start.md) | Hardware integration |
| [MIDI Control](docs/ideas/IDEA_midi_control.md) | MIDI surface control |
| [Multi-User Remote](docs/ideas/IDEA_multi_user_remote.md) | Collaborative editing |
| [Now Playing Push](docs/ideas/IDEA_now_playing_push.md) | RDS/Web integration |
| [Remote App Connection](docs/ideas/IDEA_remote_app_connection.md) | Mobile app API |
| [Remote Audio Monitor](docs/ideas/IDEA_remote_audio_monitor.md) | Off-site listening |
| [Remote Control](docs/ideas/IDEA_remote_control.md) | Web-based control panel |

### 🎨 UI & UX
| Idea | Description |
|------|-------------|
| [Column Loadouts](docs/ideas/IDEA_column_loadouts.md) | Saved column presets |
| [Contract Management](docs/ideas/IDEA_contract_management.md) | Artist/license tracking |
| [Cycle Detection Warning](docs/ideas/IDEA_cycle_detection_warning.md) | Circular reference alerts |
| [Media Item Composition](docs/ideas/IDEA_media_item_composition.md) | Song/Jingle/Voice wrapper |
| [Mirror View](docs/ideas/IDEA_mirror_view.md) | On-air display clone |
| [Rule Graph Visualization](docs/ideas/IDEA_rule_graph_visualization.md) | Visual rule editor |
| [Rule Testing](docs/ideas/IDEA_rule_testing.md) | Validate rules before deploy |
| [Voice Recorder](docs/ideas/IDEA_voice_recorder.md) | Built-in recording |

---

## 📝 Notes

- language options... extract all text into a file so languages can easily be implemented...
- custom icon picker for tags, and maybe other stuff
