# Proposal: Gosling2 "Production Rail" & Smart Drag

This document outlines the transition from a "Player" UI to a "Radio Workstation" paradigm. The goal is to separate **DJ Operations** (soft selection, drag & drop) from **Surgical Operations** (hard selection, metadata editing).

## 1. The Visual Concept: The Twin Rail
The existing magenta "LOG" handle on the sidebar becomes a vertical control strip with two distinct toggles.

```text
+-------------------+----------------------------+-----------------------------+
|    [FILTERS]      |        MAIN LIBRARY        | [x][-]  [  PREP LOG  ] [LED]|
|                   |                            +-----------------------------+
| (PURE INPUT SIDE) |       (THE WAREHOUSE)      |       [SURGERY EDITOR]      |
|                   |                            |          (ON TOGGLE)        |
|                   |                            +-----------------------------+
|   [CHIP BAY]      |                            |      [PLAYLIST / LOG]       |
+-------------------+----------------------------+-----------------------------+
                    ^                            ^
              DB FOCUSED                    TERMINAL FOCUSED
```

### The "Surgical Symmetry" Logic
*   **Left Side Cleanup:** The magenta "L O G" rail is removed from the left sidebar. The filters now have full horizontal real-estate.
*   **The Independent Terminal:** The Right Sidebar (Playlist + Editor) gets a top-mounted `TerminalHeader`.
*   **The Header Layout:**
    *   **LEFT:** Window-style controls (Min/Max/Close) to reinforce the "Floating Terminal" feel.
    *   **CENTER:** The "PREP LOG" button. 
    *   **RIGHT:** A status LED showing current mode (Standby vs. Surgery).
*   **Workflow:** You filter on the left, you pick in the middle, and you operate/play on the terminal-right.

---

## 2. Smart Drag & Drop Logic
To facilitate the "New User" experience, dragging from Library to Playlist will use **Relative Insertion**.

| Drop Position | Logic |
| :--- | :--- |
| **Top 50% of Row** | Insert **ABOVE** the target song. |
| **Bottom 50% of Row** | Insert **BELOW** the target song. |
| **Empty Area** | Append to **END** of Playlist. |

### Visual Feedback
*   When dragging, a clear **Drop Gap Line** (Neon Green) will appear between rows in the Playlist to show exactly where the insert will happen.

---

## 3. Keyboard Shortcuts
*   **`F2`**: Toggle Surgical Mode.
*   **`TAB`**: Move between Library and Playlist.
*   **`DEL`**: Remove from Playlist.

---

## Technical Action Plan (On Hold)
1.  **MainWindow:** Add `surgical_mode_enabled` boolean state.
2.  **LibraryWidget:** Split the History "Rail" into a `QVBoxLayout` with two vertical `QPushButton` units.
3.  **Signals:** Wire `surgical_btn.toggled` to control the splitter sizes and the editor visibility.
4.  **Drag Logic:** Update `PlaylistWidget.dropEvent` to calculate `event.position().y()` relative to `rowHeight`.

**Status:** Awaiting user "Go" for implementation.
