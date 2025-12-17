# Architectural Proposal: Field Registry Pattern

## Problem
The "9-Layer Yelling Mechanism" (now 10 layers) is effective but manually intensive. 
Consistency is enforced by **distributed redundancy** — 10 separate test files must be manually checked.
Adding a field requires touching 10+ files, increasing the risk of human error or fatigue.

## Solution: The Field Registry Pattern

Centralize the "Truth" of the data model into a single configuration source.

### 1. The Registry (`src/core/registry.py`)

A single, declarative definition of every data field in the system.

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable

class Layer(Enum):
    DB = auto()
    MODEL = auto()
    SERVICE = auto()
    UI_TABLE = auto()
    METADATA_READ = auto()
    METADATA_WRITE = auto()
    # ... etc

@dataclass
class DataField:
    name: str                  # Internal system name
    db_col: str                # Database column name
    model_attr: str            # Song model attribute
    ui_header: str             # UI Table Header
    id3_frame: Optional[str]   # ID3 Frame ID (if applicable)
    
    # Validation flags
    required_layers: list[Layer] = field(default_factory=lambda: [l for l in Layer])
    is_editable: bool = True
    
    # Future extensibility
    validator: Optional[Callable] = None

# THE SOURCE OF TRUTH
FIELD_REGISTRY = [
    DataField(
        name="title",
        db_col="Title",
        model_attr="title",
        ui_header="Title",
        id3_frame="TIT2"
    ),
    DataField(
        name="isrc",
        db_col="ISRC",
        model_attr="isrc",
        ui_header="ISRC",
        id3_frame="TSRC",
        validator=validate_isrc
    ),
    # ... defining all fields here
]
```

### 2. Implementation Strategy

#### Phase 1: Passive Enforcement (Test-Only Refactor)
Instead of 10 disparate test files manually listing fields, we have **one** master integrity test that iterates the registry.

```python
# tests/integrity/test_registry_integrity.py

def test_database_layer():
    """Layer 1: Verify DB has all registry columns"""
    db_cols = get_db_columns()
    for field in FIELD_REGISTRY:
        assert field.db_col in db_cols

def test_model_layer():
    """Layer 2: Verify Song model has attributes"""
    for field in FIELD_REGISTRY:
        assert hasattr(Song, field.model_attr)

# ... and so on for all 10 layers
```

**benefit:** Adding a field means adding 1 line to `registry.py`. The test suite automatically "yells" if you miss any implementation detail in the actual code.

#### Phase 2: Active Generation (Code Refactor)
The application code itself uses the registry to generate UI and logic.

*   **MetadataService:** `for field in FIELD_REGISTRY: ...`
*   **LibraryWidget:** `columns = [f.ui_header for f in FIELD_REGISTRY]`

### 3. Benefits
1.  **Single Source of Truth:** `registry.py` defines the entire data shape.
2.  **Automated Yelling:** Tests are generated dynamically; you can't "forget" to write a test for a new field.
3.  **DRY (Don't Repeat Yourself):** Removes massive duplication across the codebase.
4.  **Extensibility:** Easy to add new layers (e.g., "Export") by adding a flag to the registry.

### 4. Risk / Cost
*   **High Refactor Cost:** requires touching core files (`Song`, `LibraryService`, `MetadataService`).
*   **Recommendation:** Implement **Phase 1** first (Test-Only). It provides 80% of the value (safety) with 20% of the risk.
