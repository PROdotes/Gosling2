# Yellberus Modularization Proposal

> **Status**: Draft - For Review
> **Created**: 2026-01-01
> **Priority**: v0.2 Phase A (after Multi-Album support)
> **Depends On**: Core feature completion (Artist tags, Album tags)

---

## 1. Problem Statement

`yellberus.py` has grown to **673 lines** and mixes multiple concerns:
- Field definitions (data schema)
- Validation logic (business rules)
- Query building (SQL generation)
- ID3 mapping (file I/O adaptation)
- Grouping functions (UI helpers)

This makes it:
- **Hard to test** (77% coverage, some functions at 4%)
- **Hard to debug** (when a field fails, is it the definition, validation, or I/O?)
- **Brittle** (changing one thing breaks unrelated features)

---

## 2. Proposed Split

| New File | Responsibility | From Yellberus |
|----------|----------------|----------------|
| `src/core/fields.py` | `FieldDef` class + `FIELDS` list | Lines 1-300 (field definitions) |
| `src/core/validation.py` | `validate_row()`, `yell()`, schema checks | `validate_*` functions |
| `src/core/groupers.py` | `decade_grouper`, `first_letter_grouper` | Grouping lambdas |
| `src/core/query_builder.py` | `build_query_select()`, SQL helpers | Query construction |
| `src/core/id3_adapter.py` | `row_to_tagged_tuples()`, ID3 mapping | ID3 translation layer |

### After:
```
src/core/
├── __init__.py          (re-exports for backward compat)
├── fields.py            (~200 lines) - FieldDef + FIELDS
├── validation.py        (~150 lines) - validate_row, yell
├── groupers.py          (~50 lines)  - decade_grouper, etc.
├── query_builder.py     (~100 lines) - SQL generation
├── id3_adapter.py       (~150 lines) - row_to_tagged_tuples
├── yellberus.py         (~20 lines)  - SHIM: from .fields import *
└── logger.py            (unchanged)
```

---

## 3. Backward Compatibility

The existing `yellberus.py` becomes a **re-export shim** (like `glow_factory.py`):

```python
"""
yellberus.py - BACKWARD COMPATIBILITY SHIM
All logic has moved to focused modules. This file re-exports for import stability.
"""
from .fields import FieldDef, FIELDS, get_field, get_visible_fields, get_filterable_fields
from .validation import validate_row, yell, validate_schema, check_db_integrity
from .groupers import decade_grouper, first_letter_grouper
from .query_builder import build_query_select, build_where_clause
from .id3_adapter import row_to_tagged_tuples, cast_from_string
```

**Result**: Zero changes to existing imports. All `from src.core.yellberus import ...` continue working.

---

## 4. Testing Impact

### Before Split:
| Function | Coverage | Testability |
|----------|----------|-------------|
| `yell()` | 33% | Coupled to field definitions |
| `cast_from_string()` | 4% | Magic switch statement |
| `validate_row()` | 89% | OK but mixed concerns |

### After Split:
| Module | Target Coverage | Why Easier |
|--------|-----------------|------------|
| `fields.py` | 100% | Pure data, no logic |
| `validation.py` | 95% | Isolated rules, mockable |
| `groupers.py` | 100% | Pure functions |
| `query_builder.py` | 95% | String output, easy to verify |
| `id3_adapter.py` | 90% | Clear I/O boundary |

---

## 5. Implementation Checklist

### Phase 1: Prepare (No Code Changes)
- [ ] Run baseline tests: `pytest tests/unit/core/test_yellberus.py`
- [ ] Note coverage: `--cov=src/core/yellberus`
- [ ] Create migration log at `docs/state/YELLBERUS_MIGRATION.md`

### Phase 2: Extract Fields (Low Risk)
- [ ] Create `src/core/fields.py` with `FieldDef` class and `FIELDS` list
- [ ] Update `yellberus.py` to import from `fields.py`
- [ ] Run tests - must pass 100%
- [ ] Commit: "refactor(core): Extract fields.py from yellberus"

### Phase 3: Extract Validation
- [ ] Create `src/core/validation.py`
- [ ] Move `validate_row()`, `yell()`, `validate_schema()`
- [ ] Update shim
- [ ] Run tests - must pass 100%
- [ ] Commit

### Phase 4: Extract Groupers
- [ ] Create `src/core/groupers.py`
- [ ] Move grouping functions
- [ ] Update shim
- [ ] Run tests
- [ ] Commit

### Phase 5: Extract Query Builder
- [ ] Create `src/core/query_builder.py`
- [ ] Move SQL generation functions
- [ ] Update shim
- [ ] Run tests
- [ ] Commit

### Phase 6: Extract ID3 Adapter
- [ ] Create `src/core/id3_adapter.py`
- [ ] Move `row_to_tagged_tuples()`, `cast_from_string()`
- [ ] Update shim
- [ ] Run tests
- [ ] Commit

### Phase 7: Cleanup
- [ ] Remove dead code from yellberus shim
- [ ] Update imports in files that can use direct imports (optional)
- [ ] Update `STRATEGY_v0.2.md` to mark complete
- [ ] Final coverage check

---

## 6. Related Documents

| Document | Relevance |
|----------|-----------|
| `STRATEGY_v0.2.md` | Overall refactoring plan, mentions yellberus at line 40, 64 |
| `T-38_DYNAMIC_ID3_WRITE.md` | ID3 adapter design |
| `FIELD_EDITOR_SPEC.md` | Tooling for field management |
| `TESTING.md` | Test requirements for core modules |

---

## 7. Dependencies (Do First)

Before starting this refactor:
1. ✅ Test suite green (currently 430 tests passing)
2. ⬜ Multi-Album support complete (T-XX)
3. ⬜ Multi-Publisher support complete
4. ⬜ Human testing sign-off on current features

---

## Notes

> **Why not do this now?**  
> The new tag-based UI (Artist chips, Album picker) is still fresh. Before we refactor the core, we should prove the new patterns work in production. Multi-Album will likely add more fields to Yellberus, so better to have all fields in place before splitting.
