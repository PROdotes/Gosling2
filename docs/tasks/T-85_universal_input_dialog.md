---
tags:
  - task
  - type/refactor
  - area/ui
  - status/todo
---

# T-85: Universal Input Dialog Refactor

## Objective
Consolidate the various "Add Item", "Rename Item", "Create Alias", and "Input Text" dialogs into a single, reusable `UniversalInputDialog` (or `UniversalDataEditor`).
This will eliminate code duplication, standardize the "Morning Logic" UI (GlowButtons, Dark Theme), and significantly simplify unit testing by providing a single target to mock.

## Current Fragmentation (Tech Debt)
The following instances of ad-hoc or specialized input dialogs have been identified and should be replaced:

| Current Implementation | Location | Usage | Logic to Generalize |
| :--- | :--- | :--- | :--- |
| `_add_alias` (Inline `QDialog`) | `artist_manager_dialog.py` (Line ~800) | Adding aliases to an artist. | Text Input + "Select Existing" Combo + Validation. |
| `PublisherCreatorDialog` | `publisher_manager_dialog.py` | Creating/Renaming Publishers. | Simple "Name" Field. |
| `ArtistCreatorDialog` | `artist_manager_dialog.py` | Creating Artists. | Name Field + Type Toggle (Person/Group). |
| `TagRenameDialog` (deprecated?) | *Various calls to `QInputDialog`* | Renaming Tags. | Simple Text Input. |
| `IdentityCollisionDialog` | `artist_manager_dialog.py` | resolving naming conflicts | *Keep separate?* Or effectively a "Conformation" variant. |

## Proposed Design: `UniversalInputDialog`

### Known UX Issues (To Fix)
1.  **Aggressive Auto-Select**: If a user types "Roc" and hits Enter, the dialog often selects the first match (e.g., "Rocket") instead of accepting the exact text "Roc".
    *   *Requirement*: Enter should prioritize "Exact Match" or "Create New" if the user hasn't actively navigated down the list.
2.  **Rename vs. Create**: Renaming a tag (e.g. "Roc" -> "Rock") currently creates a NEW tag "Rock" and links it, leaving the old "Roc" tag as a ghost.
    *   *Requirement*: Explicit "Rename" mode that updates the ID's value, versus "Switch" mode that changes the link.

### Features
1.  **Unified Styling**: Inherits `GlowDialog`, `GlowLineEdit`, `GlowButton` automatically.
2.  **Flexible Fields**:
    *   `TextField` (Name)
    *   `TypeToggle` (Optional: Person/Group, Category Select).
    *   `ComboMode` (Optional: Allow selecting from existing items instead of typing new).
3.  **Validation**: Built-in support for "Check for Conflicts" callbacks.
4.  **Mockability**: One class to mock in `conftest.py` -> `mock_input_dialog`.

### User Interface Design: "Action Rows"
To solve the "Enter Key Ambiguity", the results list will strictly follow this order:

1.  **Index 0 (Action Row)**: Always the default action based on context.
    *   **Edit Mode**: "Rename 'OldName' to 'NewInput' ✏️"
    *   **Add Mode**: "Create New 'NewInput' ➕"
2.  **Index 1+ (Search Results)**: Existing database matches (e.g., "Rocket", "Hard Rock").

**Behavior**:
*   Hitting `Enter` defaults to Index 0 (Rename/Create).
*   User must actively `Arrow Down` to select an existing item for linking/merging.
*   This ensures "Renaming" is effortless and "Linking" is deliberate.

### Interface Draft
```python
class UniversalInputDialog(QDialog):
    def __init__(self, service, mode=InputMode.ADD, initial_text="", target_id=None):
        # mode: ADD | EDIT | SEARCH
        # target_id: The ID of the item being edited (if EDIT mode)
        ...
```

## Implementation Plan
1.  **Create `src/presentation/dialogs/universal_input_dialog.py`**.
2.  **Refactor `PublisherCreatorDialog` first** (Simplest case).
3.  **Refactor `ArtistCreatorDialog`** (Add "Type Toggle" support to the universal dialog).
4.  **Refactor `_add_alias`** (Complex case: Needs "Combo Mode" or "Search Mode").
5.  **Search & Replace `QInputDialog` usages** across the app.
6.  **Update Tests**: Replace individual mock setups with a standard `mock_universal_input` fixture.
