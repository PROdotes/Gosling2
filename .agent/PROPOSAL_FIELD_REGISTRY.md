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
from typing import Optional, Callable, List

class FieldType(Enum):
    SCALAR = auto()      # Normal column in Files table
    RELATIONAL = auto()  # Many-to-many or Hierarchical (linked tables)

class RelationType(Enum):
    MANY_TO_MANY = auto() # e.g., Genres, Albums
    HIERARCHICAL = auto() # e.g., Publishers

@dataclass
class DataField:
    name: str                  # Internal system name
    ui_header: str             # UI Table Header
    field_type: FieldType = FieldType.SCALAR
    
    # 1. Database Mapping
    db_col: Optional[str] = None      # For SCALAR
    db_path: Optional[List[str]] = None # For RELATIONAL (e.g., ["FileGenres", "Genres"])
    
    # 2. Logic Mapping
    model_attr: str            # Song model attribute
    id3_frame: Optional[str] = None   # Primary ID3 Frame ID (e.g., "TIT2")
    id3_fallback: Optional[str] = None # Fallback frame (e.g., "TPE1" vs "TIPL")
    
    # 3. Validation & UI
    is_editable: bool = True
    ui_widget: str = "LineEdit" # Default widget type
    validator: Optional[Callable] = None
```

## 🗺️ The "Master Path" (Order of Operations)

To avoid duplicate work, we follow this strict sequence:

1.  **Test Audit & Cleanup:** Consolidate 56 test files down to ~30 to ensure a clear workspace.
2.  **Phase 1: The Manager (Integrity):** Build the automated test that iterates the Registry.
3.  **Phase 2: The Chef (Logic):** Refactor `MetadataService` and `LibraryWidget` to use the Registry.
4.  **Schema Update (Bundled):** Add Genres, Publishers, and Albums by simply adding entries to the Registry.

---

## 🔗 Handling Complex Relationships (The "Big Three")

Mapping the Registry to the `DATABASE.md` specifications:

### 1. Genres (Many-to-Many)
```python
DataField(
    name="genres",
    ui_header="Genres",
    field_type=FieldType.RELATIONAL,
    db_path=["Files", "FileGenres", "Genres"],
    id3_frame="TCON",
    ui_widget="TagEditor" # Comma-separated UI, normalized storage
)
```

### 2. Publishers (Recursive Hierarchical)
```python
DataField(
    name="publisher",
    ui_header="Publisher",
    field_type=FieldType.RELATIONAL,
    db_path=["Files", "FileAlbums", "Albums", "AlbumPublishers", "Publishers"],
    id3_frame="TPUB",
    ui_widget="TreeSearch" # Displays breadcrumb/hierarchy chain
)
```

### 3. Albums (Many-to-Many)
```python
DataField(
    name="albums",
    ui_header="Albums",
    field_type=FieldType.RELATIONAL,
    db_path=["Files", "FileAlbums", "Albums"],
    id3_frame="TALB"
)
```

---

## 🕵️ The "Bi-Directional Manager" (Silent Drift Protection)

The Registry Integrity Test will perform a dual scan to ensure perfect alignment:

1.  **Registry → Code:** *"The Registry says field 'X' exists. Is it in the DB? Table? Metadata? Search? Service?"*
2.  **Code → Registry (The Neat-Freak):**
    -   Scan `sqlite_master`: *"Found column 'Y' in DB. Is it in the Registry? NO? -> **YELL.**"*
    -   Scan `id3_frames.json`: *"Found frame 'Z' assigned in code. Is it in the Registry? NO? -> **YELL.**"*

## 🚀 Benefits Recap
- **Adding a field:** Add 1 line in `registry.py`.
- **Database Safety:** Zero "mystery columns" allowed.
- **UI Consistency:** Headers and search fields always match the data.
- **Architectural Shift:** From **Building** features to **Describing** data.
