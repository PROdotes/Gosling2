---
tags:
  - layer/core
  - domain/database
  - status/active
  - type/task
  - size/large
  - priority/high
  - blocked/no
links:
  - "[[PROPOSAL_FIELD_REGISTRY]]"
  - "[[T-01_type_tabs]]"
  - "[[DATABASE]]"
---
# Field Registry (Yellberus)

**Task ID:** T-02  
**Layer:** Core  
**Score:** 10  
**Status:** � Next  
**Estimate:** 2-3 days

---

## Summary

Replace the manual "9 Layers of Yell" with **Yellberus** 🐕‍🦺 — a centralized field registry that becomes the single source of truth for all data fields. Adding a new field becomes trivial: define it once, and the UI, validation, and persistence automatically pick it up.

---

## The Problem

Currently, adding a column like `TypeID` requires touching:

1. `song_repository.py` — SQL query
2. `library_widget.py` — `COL_*` constants
3. `library_widget.py` — `COL_TO_FIELD` map
4. `completeness_criteria.json` — validation rules
5. `Song` model — property
6. Tests (multiple files)

This is error-prone and tedious.

---

## The Solution: Yellberus 🐕‍🦺

A single Python file (`src/core/yellberus.py`) containing:

```python
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Any
from enum import Enum, auto

class FieldType(Enum):
    TEXT = auto()
    INTEGER = auto()
    REAL = auto()
    BOOLEAN = auto()
    LIST = auto()      # Comma-separated (e.g., performers)
    DURATION = auto()  # Seconds, formatted as mm:ss

@dataclass
class FieldDef:
    """Single source of truth for a data field."""
    name: str                      # Internal key (e.g., "title")
    ui_header: str                 # Column header (e.g., "Title")
    db_column: str                 # SQL column name (e.g., "MS.Name")
    field_type: FieldType = FieldType.TEXT
    
    # Validation
    required: bool = False
    min_value: Optional[float] = None
    min_length: Optional[int] = None
    
    # UI behavior
    visible: bool = True           # Show in table by default
    editable: bool = True          # Allow inline editing (future)
    sortable: bool = True
    searchable: bool = True
    
    # Filter behavior (NEW)
    filterable: bool = False       # Show in filter sidebar
    filter_type: str = "list"      # "list", "range", "boolean"
    grouping_function: Optional[Callable[[Any], str]] = None # Logic for branches (e.g. 1984 -> "1980s")
    
    # Mapping
    model_attr: Optional[str] = None  # Song model property (defaults to name)
    id3_frame: Optional[str] = None   # Primary ID3 frame


# ==================== THE REGISTRY ====================

FIELDS: List[FieldDef] = [
    FieldDef(
        name="file_id",
        ui_header="ID",
        db_column="MS.SourceID",
        field_type=FieldType.INTEGER,
        visible=False,
        editable=False,
    ),
    FieldDef(
        name="type_id",
        ui_header="Type",
        db_column="MS.TypeID",
        field_type=FieldType.INTEGER,
        visible=False,
        editable=False,
        filterable=True,  # Filter by Type
    ),
    FieldDef(
        name="performers",
        ui_header="Artist",
        db_column="(SELECT GROUP_CONCAT...)",
        field_type=FieldType.LIST,
        required=True,
        min_length=1,
        id3_frame="TPE1",
        filterable=True, # Filter by Artist
        searchable=True,
    ),
    FieldDef(
        name="title",
        ui_header="Title",
        db_column="MS.Name",
        required=True,
        id3_frame="TIT2",
        filterable=False, # Don't filter by unique titles
        searchable=True,
    ),
    FieldDef(
        name="duration",
        ui_header="Duration",
        db_column="MS.Duration",
        field_type=FieldType.DURATION,
        required=True,
        min_value=30,
        filterable=False,
    ),
    # ... more fields
]

# ==================== HELPERS ====================

def get_field(name: str) -> Optional[FieldDef]:
    """Lookup a field by name."""
    return next((f for f in FIELDS if f.name == name), None)

def get_visible_fields() -> List[FieldDef]:
    """Get fields that should appear in the table."""
    return [f for f in FIELDS if f.visible]

def get_required_fields() -> List[FieldDef]:
    """Get fields marked as required for validation."""
    return [f for f in FIELDS if f.required]
```

---

## What Yellberus Replaces

| Before | After |
|--------|-------|
| `COL_FILE_ID = 0` | Auto-generated from `FIELDS` order |
| `COL_TO_FIELD = {...}` | Generated from registry |
| `completeness_criteria.json` | Derive from `required`, `min_value`, etc. |
| Manual SQL column list | Build from `db_column` |

---

## Implementation Plan

### Phase 1: Create Yellberus (Day 1)
- [ ] Create `src/core/yellberus.py` with `FieldDef` dataclass
- [ ] Define current 10 fields in `FIELDS` list
- [ ] Add helper functions

### Phase 2: Integrate with LibraryWidget (Day 1-2)
- [ ] Replace `COL_*` constants with index lookup
- [ ] Replace `COL_TO_FIELD` with registry-based map
- [ ] Generate column headers from registry

### Phase 3: Integrate with Validation (Day 2)
- [ ] Replace `completeness_criteria.json` with registry-derived rules
- [ ] Update `_get_incomplete_fields()` to use registry

### Phase 4: Dynamic Filter Widget (Day 2)
- [ ] Refactor `populate_tree` to iterate `yellberus.get_filterable_fields()`
- [ ] Implement generic tree node builder (Value/Range strategies)
- [ ] Remove hardcoded Years/Status logic

### Phase 5: Integrity Tests (Day 3)
- [ ] Create `test_yellberus.py` — Registry → Code check
- [ ] Create reverse check: DB columns → Registry
- [ ] Remove old scattered tests

### Phase 6: Add TypeID (Day 3)
- [ ] Add `type_id` to registry (already in example above)
- [ ] Verify it appears in query
- [ ] Unblocks T-01 Type Tabs

---

## Checklist

### Setup
- [ ] Create `src/core/` package (if not exists)
- [ ] Create `src/core/yellberus.py`
- [ ] Define `FieldDef` dataclass
- [ ] Define `FIELDS` list with current fields

### Migration
- [ ] `library_widget.py`: Remove `COL_*` constants
- [ ] `library_widget.py`: Replace `COL_TO_FIELD` 
- [ ] `library_widget.py`: Use registry for headers
- [ ] `song_repository.py`: (optional) Build SELECT from registry
- [ ] Delete `completeness_criteria.json`

### Testing
- [ ] Bi-directional integrity test
- [ ] All existing tests still pass
- [ ] Add TypeID field, verify no manual changes needed

---

## Open Questions

### 1. Query Architecture (The Big One)

Yellberus sits between DB and services. Who owns what?

---

#### Option A: Validate Only
```
Hades (Repository) → writes full SQL
Yellberus → validates result columns match registry
```
| Pros | Cons |
|------|------|
| Simple to implement | Duplicate SELECT clauses everywhere |
| Full flexibility for complex queries | Easy to drift from registry |
| No breaking changes to existing code | "9 Layers" problem just moves |

---

#### Option B: Generate SELECT Only
```
Yellberus → generates SELECT columns + aliases
Hades → adds FROM, JOINs, WHERE
```
| Pros | Cons |
|------|------|
| Column list is DRY | FROM/JOINs still duplicated |
| Adding field = 1 place | Awkward string concatenation |
| Registry IS the query source | Complex JOINs harder |

---

#### Option C: Generate Base Query
```
Yellberus → SELECT + FROM + base JOINs
Hades → just adds WHERE clauses
```
| Pros | Cons |
|------|------|
| Most DRY | JOINs can vary per query type |
| Repository methods tiny | Less flexible |
| Clear ownership | Need variants for different base queries |

---

#### Option D: Query Builder Pattern
```
Yellberus → provides QueryBuilder class
Hades → uses builder fluent API
```
```python
query = Yellberus.query() \
    .select_visible() \
    .join_contributors() \
    .where("RecordingYear", "=", year) \
    .build()
```
| Pros | Cons |
|------|------|
| Very flexible | More complex to build |
| Compile-time checks possible | Overkill for simple app? |
| Extensible | Learning curve |

---

#### Option E: View-Based (DB does the work)
```
DB → CREATE VIEW LibraryView AS SELECT...
Hades → SELECT * FROM LibraryView WHERE...
Yellberus → validates View columns match registry
```
| Pros | Cons |
|------|------|
| SQL stays in SQL | Schema migration needed |
| Query is super simple | View maintenance |
| DB optimizes it | Harder to debug |

---

### ✅ Decision: **Option C (Base Query)**

Chosen for readability and maintainability.

```python
# yellberus.py
BASE_QUERY = """
    SELECT MS.SourceID, MS.Name, MS.Duration, S.RecordingYear, S.IsDone,
           GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Performers
    FROM MediaSources MS
    JOIN Songs S ON MS.SourceID = S.SourceID
    LEFT JOIN MediaSourceContributorRoles MSCR ON MS.SourceID = MSCR.SourceID
    LEFT JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
    LEFT JOIN Roles R ON MSCR.RoleID = R.RoleID
    WHERE MS.IsActive = 1
    GROUP BY MS.SourceID
"""

# song_repository.py - becomes simple
def get_all(self):
    return self.execute(yellberus.BASE_QUERY)

def get_by_year(self, year):
    return self.execute(yellberus.BASE_QUERY + " HAVING S.RecordingYear = ?", [year])

def get_by_performer(self, name):
    return self.execute(yellberus.BASE_QUERY + " HAVING Performers LIKE ?", [f"%{name}%"])
```

---

### 2. Relational Fields

Performers/Composers are included in the BASE_QUERY via GROUP_CONCAT. 
Mark as `field_type=LIST` in registry, the query handles the actual SQL.


---

## 🚨 Known Issues

**Stale Test:** `test_filter_widget_integrity.py` and `test_schema_model_cross_ref.py` have been patched to work with the new schema, BUT:

**Legacy Failures:** ~18 other tests (e.g., `test_database_schema_integrity`) are currently failing because they reference the old "Files" table.
- **Decision:** Do NOT fix these individually.
- **Plan:** They will be replaced or fixed en-masse during **Phase 5 (Integrity Tests)** once Yellberus is the source of truth.

---

## Example: Adding `HookIn` Field (Future)

**Scenario:** We want to add the `HookIn` timing field (teaser start point).

### Before Yellberus (old way):
1. Add column to `Songs` table → modify `base_repository.py`
2. Add to `Song` model → modify `song.py`
---

## 🌲 Filter Widget Protocol

How dynamic filtering works between components.

### 1. Discovery
`FilterWidget` iterates `yellberus.get_filterable_fields()` to create top-level tree nodes (e.g., "Year", "Artist").

### 2. Population (Getting Values)
For each field, the widget requests values. The repository generates this query dynamically:

```python
# song_repository.py
def get_field_values(self, field_def: FieldDef) -> List[Tuple[Any, int]]:
    """
    Returns unique values and counts for a field.
    e.g. [('2024', 50), ('2023', 120)]
    """
    col = field_def.db_column
    
    # Use BASE_QUERY parts to ensure correct JOINs
    query = f"""
        SELECT {col}, COUNT(*)
        FROM MediaSources MS
        JOIN Songs S ON MS.SourceID = S.SourceID
        LEFT JOIN ... (standard base joins)
        WHERE {col} IS NOT NULL
        GROUP BY {col}
        ORDER BY {col} DESC
    """
    return self.execute(query)
```

### 3. Application (Filtering)
When a user selects "2024" under "Year", the `FilterWidget` sends:
`filter_state = {"recording_year": 2024}`

The repository applies it:
```python
def get_filtered(self, filters: dict):
    query = yellberus.BASE_QUERY
    params = []
    
    for field_name, value in filters.items():
        field = yellberus.get_field(field_name)
        query += f" AND {field.db_column} = ?"
        params.append(value)
        
    return self.execute(query, params)
```

---
4. Add `COL_HOOK_IN = 11` → modify `library_widget.py`
5. Add to `COL_TO_FIELD` → same file
6. Add validation → modify `completeness_criteria.json`
7. Update 3+ tests

### After Yellberus (new way):
```python
# Add ONE entry to yellberus.py:
FieldDef(
    name="hook_in",
    ui_header="Hook In",
    db_column="S.HookIn",
    field_type=FieldType.DURATION,
    visible=False,        # Only show in edit mode
    editable=True,
    filterable=False,
),
```

**What happens automatically:**
- Column index auto-generated ✅
- Header appears in table ✅  
- Validation (if any) applies ✅
- Filter sidebar knows to skip it ✅

**What you still do manually:**
- Add column to DB schema (migration)
- Add property to `Song` model
- Add to repository SELECT query
- Integrity test forces you to align everything

---

## Layers Yellberus Guards

| Layer | FieldDef Property | Notes |
|-------|------------------|-------|
| DB Column | `db_column` | Validated against actual schema |
| Model Attr | `model_attr` | Cross-ref with Song dataclass |
| Table Column | `visible`, `ui_header` | Auto-generates COL_* |
| Validation | `required`, `min_value` | Replaces criteria.json |
| ID3 Mapping | `id3_frame` | Cross-ref with metadata service |
| Filter Sidebar | `filterable` | NEW: Controls filter widget |
| Search | `searchable` | Which cols to include in search |

---

## Updated FieldDef

```python
@dataclass
class FieldDef:
    name: str
    ui_header: str
    db_column: str
    field_type: FieldType = FieldType.TEXT
    
    # Validation
    required: bool = False
    min_value: Optional[float] = None
    min_length: Optional[int] = None
    
    # UI - Table
    visible: bool = True
    editable: bool = True
    sortable: bool = True
    
    # Filter behavior
    filterable: bool = False          # Show in filter sidebar?
    filter_type: str = "list"         # "list", "range", "boolean"
    grouping_function: Optional[Callable[[Any], str]] = None # Logic for branches (e.g. 1984 -> "1980s")
    
    # Search
    searchable: bool = True
    
    # Mapping
    model_attr: Optional[str] = None
    id3_frame: Optional[str] = None
```

---

## 🏛️ The Underworld Architecture (Metaphor)

| Mythological | Code Entity | Role |
|--------------|------------|------|
| **Yellberus** 🐕‍🦺 | `yellberus.py` | The Gatekeeper. Holds the map coverage. |
| **Yellberus Pups** 🐶 | `field_logic.py` | (Future) Helper logic for complex grouping/validation. |
| **Hades** 💀 | `song_repository.py` | Rules the dark. Fetches raw data efficiently. |
| **Hermes** ⚡ | `FilterWidget` | The Messenger. Delivers data to UI. Dumb but fast. |

### Filter Flow with Gropering
1. **Hermes** asks **Yellberus**: "How do I group `RecordingYear`?"
2. **Yellberus** gives a function: `lambda y: f"{y//10*10}s"`
3. **Hermes** asks **Hades**: "Give me all years." -> `[1984, 1991...]`
4. **Hermes** runs values through function -> `1980s`, `1990s`
5. **Hermes** builds the branches himself.

With Option C, Yellberus provides the BASE_QUERY (the map of the underworld), and Hades just filters souls based on criteria.

---

## Summary

**Before Yellberus:**
- Adding a field = touching 6+ files
- Easy to forget a layer
- Tests scattered everywhere

**After Yellberus:**
- Adding a field = 1 entry in registry + 3 manual steps
- Integrity test forces alignment
- Single source of truth

**Architecture Decision:**
- Option C (Base Query) chosen for readability
- Yellberus owns the SELECT + JOINs
- Repository just adds WHERE clauses

---

## Links

- [[PROPOSAL_FIELD_REGISTRY]] — Full architectural design
- [[T-01_type_tabs]] — Blocked on this
