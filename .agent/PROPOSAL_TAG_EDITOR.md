# Architectural Proposal: Universal Tag Editor Widget

## Objective
Create a reusable UI component (`TagInputWidget`) for managing many-to-many relationships (Genres, Performers, Composers) with a modern "Chip/Token" interface.

## 1. UX Design
- **Visuals:** A text entry field that converts confirmed inputs into graphical "Chips" (rounded rectangles with an 'X' button).
- **Interaction:**
    - **Type:** "Hou" -> Autocomplete popup shows "House", "Deep House".
    - **Select:** Press Enter/Tab or click suggestion -> Text becomes a "House" chip.
    - **Remove:** Backspace from the end deletes the last chip. Click 'X' to remove specific chip.
- **Mockup Reference:** Similar to email recipient fields (Outlook/Gmail) or YouTube tag editor.

## 2. Technical Implementation

### A. The Widget Structure
- **Base:** `QFrame` mimicking a `QLineEdit`.
- **Layout:** `FlowLayout` (custom layout handling wrapping to next line).
- **Components:** 
    - List of `QChip` widgets (QLabel + QToolButton).
    - One `QLineEdit` at the end for typing new entries.

### B. Data & Normalization
The widget essentially translates between **Names** and **IDs**.

- **Input:** `set_ids([10, 45])`
    - Widget queries Registry/DB: "What are 10 and 45?"
    - Returns: "House", "Techno".
    - Widget renders 2 chips.
- **Output:** `get_ids()`
    - Widget returns `[10, 45]`.
    - *Crucial:* It does NOT return text. It returns Normalized IDs.

### C. The "New Entry" Workflow
What happens if the user types a Genre that doesn't exist?

1. **User types:** "Space Jazz" and hits Enter.
2. **Lookup:** Widget checks Registry. "Space Jazz" not found.
3. **Prompt:** "Create new Genre 'Space Jazz'?"
4. **Action:** 
    - If Yes: Calls `GenreRepository.create("Space Jazz")`.
    - Gets back new ID (e.g., 99).
    - Adds Chip for ID 99.
    - Fires `on_change` signal.

## 3. Usage in Metadata Editor
The `Field Registry` determines when to use this widget.

```python
# In Registry logic
if field.name == "genres":
    widget = TagInputWidget(repository=GenreRepository)
    widget.set_allow_creation(True) # Allow new genres?
```

## 4. "Comma-Separated" Fallback
- For simple fallback (e.g., ID3 TPE1 frame), the widget also provides a `get_text()` method that joins names with `/` or `;`.

## 🚀 Implementation Roadmap
1. [ ] Implement `FlowLayout` (PyQt doesn't have one built-in, need standard recipe).
2. [ ] Build `QChip` visual component.
3. [ ] Build `TagInputWidget` with `QCompleter`.
4. [ ] Connect to `BaseRepository` for ID/Name resolution.
