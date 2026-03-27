## Codebase Navigation

### Documentation First
Before exploring the codebase or launching agents to search files, **always check `docs/lookup/` first**. This directory contains quick-reference documentation for LLMs covering:
- `data.md` - Data layer (repositories, schema)
- `engine_routers.md` - API endpoints and routers
- `services.md` - Service layer
- `src.md` - Source structure overview
- `utils.md` - Utility functions

Only launch Explore agents or perform deep file searches if the lookup docs don't answer your question.

---

## Search Performance Optimization
- [Search slim query architecture](project_search_optimization.md) — slim queries replacing hydration on list views, duplicate identity bug fix, what's pending

---

## Missing Data Filter Bug Fix

### Issue
The "Missing Data" filter was showing songs that had all required fields complete (e.g., "Prsti zapleteni").

### Root Cause
In `LibraryFilterProxyModel.acceptRow()` (library_widget.py ~line 292), the code was building a `completeness_row` using field indices from a `_field_indices` dictionary:
```python
f_idx = self._field_indices.get(f.name, -1)
val = model.data(...) if f_idx >= 0 else None
```

If a field wasn't in the dict, it would append `None`, which `check_completeness()` would interpret as "missing data" for required fields - even if the data actually existed in the model.

### Solution
Changed the code to read columns directly by their numerical index (which is guaranteed to match `yellberus.FIELDS` order):
```python
for col_idx in range(min(model.columnCount(), len(yellberus.FIELDS))):
    val = model.data(model.index(row, col_idx, parent), Qt.ItemDataRole.UserRole)
    completeness_row.append(val)
```

This eliminates dependency on `_field_indices` staying in sync and ensures actual data is checked, not phantom None values.

### Key Insight
Model columns are always in the same order as `yellberus.FIELDS` because `_populate_table()` iterates through `row_data` in order and creates items matching that order. So using `col_idx` directly is both simpler and more reliable than maintaining a separate index mapping.

---

## Phase 2 CRUD Implementation
- [Phase 2 progress and next steps](project_phase2_progress.md) — data layer complete, tests partially written, service/API layer pending
