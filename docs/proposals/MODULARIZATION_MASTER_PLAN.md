# Gosling2 Modularization Master Plan

> **Status**: Draft - For Review
> **Created**: 2026-01-01
> **Priority**: v0.2 Phase A-C
> **Depends On**: Core feature completion (Multi-Album, Multi-Publisher)

---

## Overview

This document consolidates all planned refactoring for large files that have grown beyond maintainable sizes.

| File | Lines | Priority | Phase |
|------|-------|----------|-------|
| `library_widget.py` | 2032 | 🔴 Critical | C |
| `side_panel_widget.py` | 1465 | 🔴 Critical | C |
| `main_window.py` | 763 | 🟡 High | B |
| `filter_widget.py` | 730 | 🟡 High | C |
| `yellberus.py` | 673 | 🟢 Medium | A |
| `song_repository.py` | 607 | 🟢 OK | - |

---

# 1. YELLBERUS.PY (673 lines)

## Problem
Mixes field definitions, validation, query building, ID3 mapping, and grouping functions.

## Proposed Split

| New File | Responsibility | Est. Lines |
|----------|----------------|------------|
| `src/core/fields.py` | `FieldDef` class + `FIELDS` list | ~200 |
| `src/core/validation.py` | `validate_row()`, `yell()`, schema checks | ~150 |
| `src/core/groupers.py` | `decade_grouper`, `first_letter_grouper` | ~50 |
| `src/core/query_builder.py` | `build_query_select()`, SQL helpers | ~100 |
| `src/core/id3_adapter.py` | `row_to_tagged_tuples()`, ID3 mapping | ~150 |

## After Structure
```
src/core/
├── __init__.py          (re-exports)
├── fields.py            - FieldDef + FIELDS
├── validation.py        - validate_row, yell
├── groupers.py          - decade_grouper, etc.
├── query_builder.py     - SQL generation
├── id3_adapter.py       - row_to_tagged_tuples
├── yellberus.py         - SHIM: from .fields import *
└── logger.py            (unchanged)
```

## Backward Compatibility
`yellberus.py` becomes a re-export shim (like `glow_factory.py`):
```python
from .fields import FieldDef, FIELDS, get_field, get_visible_fields
from .validation import validate_row, yell, validate_schema
from .groupers import decade_grouper, first_letter_grouper
from .query_builder import build_query_select
from .id3_adapter import row_to_tagged_tuples, cast_from_string
```

---

# 2. LIBRARY_WIDGET.PY (2032 lines) - HIGHEST PRIORITY

## Problem
The largest file in the project. Mixes:
- Table model and data binding
- Selection logic and multi-select
- Drag and drop handling
- Sorting and filtering proxy
- Context menu actions
- Keyboard shortcuts
- Column visibility management
- Search integration

## Proposed Split

| New File | Responsibility | Est. Lines |
|----------|----------------|------------|
| `src/presentation/widgets/library/table_model.py` | `LibraryTableModel` - data roles, row colors | ~300 |
| `src/presentation/widgets/library/selection_manager.py` | Multi-select logic, range selection | ~150 |
| `src/presentation/widgets/library/drag_drop_handler.py` | Mime data, drop acceptance, playlist drops | ~200 |
| `src/presentation/widgets/library/sort_proxy.py` | `QSortFilterProxyModel` subclass | ~150 |
| `src/presentation/widgets/library/column_manager.py` | Column visibility, reordering, persistence | ~150 |
| `src/presentation/widgets/library/context_menu.py` | Right-click actions, keyboard shortcuts | ~200 |
| `src/presentation/widgets/library/search_bar.py` | Search input, highlight, filter | ~100 |
| `src/presentation/widgets/library_widget.py` | Orchestrator - wires components | ~400 |

## After Structure
```
src/presentation/widgets/library/
├── __init__.py
├── table_model.py
├── selection_manager.py
├── drag_drop_handler.py
├── sort_proxy.py
├── column_manager.py
├── context_menu.py
└── search_bar.py

src/presentation/widgets/
├── library_widget.py    (orchestrator, imports from library/)
└── ...
```

## Testing Benefit
| Component | Test Type | What It Catches |
|-----------|-----------|-----------------|
| `table_model.py` | Unit | Data binding, role mapping |
| `selection_manager.py` | Unit | Multi-select algorithms |
| `drag_drop_handler.py` | Integration | Mime type parsing |
| `sort_proxy.py` | Unit | Sort order, filter logic |
| `library_widget.py` | Widget | Wiring/integration only |

---

# 3. SIDE_PANEL_WIDGET.PY (1465 lines)

## Problem
Second largest file. Mixes:
- Dynamic field building from Yellberus
- Bulk value calculation for multi-select
- Field widget creation (text, checkbox, pickers)
- Validation and yelling (ISRC, required fields)
- Staged change management
- Save logic and ID3 writing
- Album/Publisher/Tag picker integration

## Proposed Split

| New File | Responsibility | Est. Lines |
|----------|----------------|------------|
| `src/presentation/widgets/editor/field_value_calculator.py` | Bulk value logic for multi-select | ~150 |
| `src/presentation/widgets/editor/field_widget_factory.py` | Creates widgets based on field type | ~200 |
| `src/presentation/widgets/editor/staged_changes.py` | Change tracking, dirty detection | ~100 |
| `src/presentation/widgets/editor/validation_engine.py` | ISRC checks, required field validation | ~150 |
| `src/presentation/widgets/editor/save_controller.py` | DB update + ID3 write orchestration | ~200 |
| `src/presentation/widgets/side_panel_widget.py` | Layout + wiring | ~400 |

## After Structure
```
src/presentation/widgets/editor/
├── __init__.py
├── field_value_calculator.py
├── field_widget_factory.py
├── staged_changes.py
├── validation_engine.py
└── save_controller.py

src/presentation/widgets/
├── side_panel_widget.py    (imports from editor/)
└── ...
```

## Testing Benefit
| Component | Test Type | What It Catches |
|-----------|-----------|-----------------|
| `field_value_calculator.py` | Unit (pure logic) | Bulk value bugs |
| `validation_engine.py` | Unit | ISRC format, conflict detection |
| `staged_changes.py` | Unit | Dirty tracking |
| `save_controller.py` | Integration | DB + ID3 coordination |

---

# 4. MAIN_WINDOW.PY (763 lines)

## Problem
Application controller mixed with:
- Service instantiation
- Window state persistence
- Splitter management
- Shortcut bindings
- Menu actions
- Signal wiring

## Proposed Split

| New File | Responsibility | Est. Lines |
|----------|----------------|------------|
| `src/presentation/views/window_state.py` | Geometry, splitters, layout save/restore | ~100 |
| `src/presentation/views/shortcut_manager.py` | Keyboard bindings | ~100 |
| `src/presentation/views/menu_builder.py` | Menu bar construction | ~100 |
| `src/presentation/views/service_container.py` | DI container for services | ~150 |
| `src/presentation/views/main_window.py` | Window shell + wiring | ~300 |

## After Structure
```
src/presentation/views/
├── __init__.py
├── window_state.py
├── shortcut_manager.py
├── menu_builder.py
├── service_container.py
└── main_window.py
```

---

# 5. FILTER_WIDGET.PY (730 lines)

## Problem
Filter tree logic mixed with:
- Tree building and population
- Item visibility during search
- Expansion state persistence
- Filter application to library
- Count badges

## Proposed Split

| New File | Responsibility | Est. Lines |
|----------|----------------|------------|
| `src/presentation/widgets/filter/tree_model.py` | Tree data model, item hierarchy | ~200 |
| `src/presentation/widgets/filter/expansion_state.py` | Save/restore expansion to settings | ~100 |
| `src/presentation/widgets/filter/filter_logic.py` | Apply filter to library, badge counts | ~150 |
| `src/presentation/widgets/filter_widget.py` | UI orchestrator | ~250 |

---

# Implementation Order

## Phase A: Core Layer (No UI changes)
1. [ ] `yellberus.py` → Split into 5 modules
2. [ ] Verify all tests pass

## Phase B: Application Layer
1. [ ] `main_window.py` → Extract state management
2. [ ] Service container cleanup

## Phase C: Presentation Layer (Highest risk)
1. [ ] `library_widget.py` → Extract table model first (lowest risk)
2. [ ] `side_panel_widget.py` → Extract validation engine
3. [ ] `filter_widget.py` → Extract expansion state

---

# Safety Protocol

1. **Before ANY refactor**: Run full test suite, note baseline coverage
2. **One file at a time**: Complete and commit before starting next
3. **Shim pattern**: Original file becomes re-export, zero import changes
4. **Migration log**: Update `docs/state/MODULARIZATION_LOG.md` after each step
5. **No "Cowboy Coding"**: If tests fail, revert immediately

---

# Dependencies

Complete these BEFORE starting refactoring:
- [ ] Multi-Album support (T-XX) - may add fields
- [ ] Multi-Publisher support - may add fields  
- [ ] Human testing sign-off on tag UI
- [ ] Test suite at 100% pass (currently 430 tests ✅)

---

# References

| Document | Content |
|----------|---------|
| `STRATEGY_v0.2.md` | Overall Strangler Fig approach |
| `TESTING.md` | Test requirements |
| `TEST_REMEDIATION_PLAN.md` | Current test status |
