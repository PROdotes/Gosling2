# Dashboard UI Architecture
*Location: `src/static/js/dashboard/`*

**Responsibility**: Professional-grade, high-density discovery and metadata triage interface.

---

## 🏗️ Architectural Layers

#### 1. The Core (main.js)
Coordinates global state, navigation modes, and top-level search orchestration. It acts as the "braid" connecting specialized handlers and renderers.

#### 2. The Protocol (api.js)
Centralized communication layer with the backend. Implements strict `AbortController` management to ensure that "Search on Type" never results in race conditions or jitter.

#### 3. Handlers (handlers/)
Self-contained logic for user interaction. 
- **SongActions**: Mutations and file operations.
- **Navigation**: Hotkeys and view switching.
- **FilterSidebar**: Multi-select faceting.
- **WebSearch**: External metadata lookup.

#### 4. Renderers (renderers/)
Pure UI generation logic. Responsible for translating API JSON into high-density interactive DOM structures.

#### 5. Components (components/)
Reusable UI widgets (Modals, Toasts, Chip Inputs) and shared DOM utility functions.

---

## 🛠️ Key Interaction Paradigms

#### Double-Stage Confirmation
Critical mutations (Song Deletion, Bulk Cleanup) use a custom `confirm_modal` to prevent accidental data loss in high-speed sessions.

#### In-Place Editing (Scalars)
Standardized BPM/Year/ISRC editing using `inline_editor.js`, allowing triage without context switching.

#### Relationship Orchestration
All linking (Artist, Album, Tag) is routed through the `orchestrator.js` to ensure consistent modal logic and UI refresh patterns.

---

## 📋 Lookup Registry
Detailed function signatures and file-specific contracts are found in modular lookup files:
- [js_api.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_api.md)
- [js_core.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_core.md)
- [js_handlers.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_handlers.md)
- [js_renderers.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_renderers.md)
- [js_components.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_components.md)
- [js_orchestrator.md](file:///c:/Users/glazb/PycharmProjects/gosling2/docs/lookup/js_orchestrator.md)
