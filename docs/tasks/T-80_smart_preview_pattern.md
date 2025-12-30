# T-80 Smart Preview Pattern

## Objective
Generalize the "Passive Preview" interaction pattern—currently pioneered on the `Composers` field—to all complex or multi-value fields in the application (Artists, Album, Producers, etc.).

## Problem
In a dense "Side Panel" editor, text fields have limited horizontal space. Long data (e.g., "Marko Purišić, Andrija Vujević, ...") gets truncated. Scrolling horizontally to edit specific items is tedious and lacks context ("Where am I in this string?").

## Solution: The Smart Preview Tooltip
A lightweight, non-modal overlay that appears when the user interacts with a field, acting as a dynamic "Heads-Up Display" for the data.

### Key Features (Already Prototyped in `Composers`)
1.  **Passive Visibility**: 
    - Appears automatically on `FocusIn` **only if** the text is truncated OR contains multiple items.
    - Hides on `FocusOut`.
2.  **Smart Formatting**: 
    - Auto-splits comma-separated lists into a clean **Vertical List**.
    - Matches the width of the parent input field exactly (creating a seamless "dropdown" aesthetic).
    - Uses High-Contrast colors (Light Gray text on Dark Background).
3.  **Active Item Highlight (Cursor Tracking)**: 
    - Tracks the cursor position in the input box in real-time.
    - Highlights the corresponding item in the preview list (e.g., Bold + Amber Glow) so the user knows exactly which "item" they are editing.
4.  **Click-to-Nav**: 
    - Clicking an item in the preview list instantly moves the cursor to the start of that item in the input box.
    - Includes a logic hack (Jump-to-End -> Defer -> Jump-to-Pos) to ensure the `QLineEdit` scrolls correctly to show the target item.
5.  **Non-Blocking / Stability**: 
    - Does *not* steal focus (prevents flicker).
    - Uses `WindowDoesNotAcceptFocus` and specialized Event Filters to allow mouse interaction without breaking the edit flow.

## Scope of Work

### 1. Refactor `GlowFactory`
- Ensure `ReviewTooltip` logic is standardized.
- **Configurable Delimiters**: Currently hardcoded to `,`. Needs to support other separators if necessary (e.g., `/` for paths, `;` for others).
- **Styling**: Ensure specialized HTML generation (links, colors) is clean.

### 2. Apply to Target Fields
Extend the `enable_overlay()` (or renamed `enable_preview()`) call in `SidePanelWidget` factory to:
- **Artists / Performers** (Critical)
- **Album Artist**
- **Producers**
- **Comment / Lyrics** (Might need different handling? Or just word wrap?)
- **Path** (Special Case: Split by directory separator `\` or `/` to show folder hierarchy?)

### 3. Edge Cases
- **Single Values**: Ensure it still triggers if a single value is just *very long* (using `fontMetrics` check).
- **Paths**: Path editing is rare, but viewing full path is useful.
- **Performance**: Ensure generating the HTML/Indices on every `textChanged` doesn't lag for massive strings (unlikely in metadata, but possible).

## Implementation Details
- **Source**: `src/presentation/widgets/glow_factory.py` (Classes: `ReviewTooltip`, `GlowLineEdit`)
- **Usage**: `src/presentation/widgets/side_panel_widget.py` -> `_create_field_widget`

## Status
- **Prototype**: Implemented and Verified for 'Composers'.
- **Next Steps**: Refactor `enable_overlay` to `enable_preview` (naming consistency) and apply to other fields.
