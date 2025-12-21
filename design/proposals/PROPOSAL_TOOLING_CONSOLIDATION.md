# Proposal: Tooling & Registry Consolidation

**Status**: Draft  
**Related**: T-17, T-06, T-16  

## 🚨 The Problem (Technical Debt)
During the implementation of **T-17 (Unified Artist View)**, we bypassed standard patterns to deliver complex logic quickly ("Bob Scenario"). This created two main debt vectors:

1.  **Field Editor Incompatibility**:
    *   `yellberus.py` now uses advanced properties (`query_expression`, `VALIDATION_GROUPS`).
    *   The `Field Editor` tool (UI) does not support these.
    *   *Risk*: Using the Field Editor (as required for T-06) currently relies on a patched Parser to avoid deleting these manual changes. It is a fragile "Safe Read" rather than a "Full Edit".

2.  **Hardcoded Logic (Clean Code Violation)**:
    *   The Logic for "Identity Graph" filtering and "Recursive Group" searching is hardcoded in `LibraryService` and `FilterWidget`.
    *   *Violation*: The application has "Special Case" `if` statements for `unified_artist`, rather than asking the Registry *how* to filter.
    *   *Impact*: Adding new complex fields (e.g. "Genre Families" in T-06) requires duplicating this hardcoded mess.

## 🛠️ The Fix: Consolidation Plan

### 1. Upgrade Field Editor (UI & Core)
*   **Goal**: The Editor must be the Source of Truth/Edit for *all* Yellberus features.
*   **Tasks**:
    *   Add "Advanced Props" tab/section to Field Editor.
    *   Allow editing raw `query_expression` (SQL snippet).
    *   Allow managing `VALIDATION_GROUPS` (Checkbox matrix for "One Or The Other" rules).

### 2. Registry-Driven Patterns (Decoupling)
*   **Goal**: Remove `if field == 'unified_artist'` from the Widget layer.
*   **Implementation**:
    *   Add `SearchStrategy` and `FilterStrategy` enums to `FieldDef`.
    *   Example:
        ```python
        FieldDef(
            name="unified_artist",
            search_strategy=SearchStrategy.IDENTITY_GRAPH,  # Service knows to recursive-expand
            filter_strategy=FilterStrategy.TREE_MERGE       # Widget knows to merge Groups/Performers
        )
        ```
    *   **Refactor**: Update `LibraryService` to dispatch logic based on Strategy, not Name.

### 3. Preparation for Advanced Search (T-16)
*   By centralizing the *Search Strategy* in the Registry, we pave the way for a query parser (T-16) to genericize:
    *   `artist:bob` -> Lookup Strategy for `Artist` -> Execute Identity Graph logic.
    *   `year:2025` -> Lookup Strategy for `Year` -> Execute Range logic.

## 💡 Concrete Use Case (The "Why")
User Requirements dictate flexible grouping logic that must be managed by Yellberus, not code:
*   **Alphabetical Grouping**: Currently `Composers` are grouped by First Letter, but `Artists` are not. Both should be configurable.
*   **Future "People" Field**: A planned Unified Field merging Artists + Composers + Lyricists will also need grouping logic.
*   **Requirement**: We must be able to toggle "Group by First Letter" in the **Field Editor** (Yellberus), and the Filter Sidebar must automatically respect this, without touching `FilterWidget` code.

## 🔍 Gap Analysis (Yellberus vs Tooling)
The following features exist in Code but are missing from Editor/Documentation:

| Feature | Status in Code | Status in Editor | Status in Docs |
| :--- | :--- | :--- | :--- |
| **`VALIDATION_GROUPS`** | Enforced (e.g. One-or-Other) | ❌ **Invisible** | ❌ **Missing** |
| **`filter_type`** | Used (e.g. `range`, `boolean`) | ❌ **Missing Column** | ❌ **Missing** |
| **`grouping_function`** | Used (e.g. `decade_grouper`) | ❌ **Missing Column** | ❌ **Missing** |
| **`query_expression`** | Active (Complex SQL) | ⚠️ **Manual Only** | ✅ Manual Note |

## 📅 Roadmap
This consolidation should be tackled **Before or During T-06**, or immediately after the T-06 legacy sync confirms the need for more fields.
