# Idea: Universal Tag Picker

## Problem
Currently, adding tags (Genre, Mood, etc.) is scattered or text-based. Users need a centralized, visual way to explore and apply tags from the taxonomy.

## Proposed Solution
A "Universal Tag Picker" dialog that allows searching and selecting tags from a hierarchical tree.

### UI Concepts
1.  **Tree View**: Display the tag hierarchy (e.g. `Genre` -> `Rock` -> `Alt-Rock`).
2.  **Universal Search**: Typing "rock" filters the tree to show matching nodes and their parents.
    *   Result: `Genre > Rock`
    *   Result: `Style > Rock & Roll`
3.  **Visual Feedback (Pills)**:
    *   Tags are displayed as **Pills**.
    *   **Color Coding**: Each Category (Genre, Mood, Era) has a distinct semantic color.
    *   Example: Genre = Blue, Mood = Orange.
4.  **Interaction**:
    *   Clicking a node adds the "Pill" to the selected song(s).
    *   Pills in the editor can be removed with an `X`.

### Technical Stack
*   `QTreeWidget` or `QTreeView` with custom ItemDelegate for Pills within the tree or standard items.
*   `TagRepository` for the hierarchy.
*   `SearchBox` filtering the model.

### User Story
"As a user, I want to type 'happy' and see 'Mood > Happy' and 'Genre > Happy Hardcore', then click one to tag my song with a color-coded pill."
