# T-49: Radio Automation Layout Conversion (Spec)

**Status**: Planning / Staging
**Objective**: Pivot the UI from "Consumer Player" (Spotify-drift) to "Workstation Dashboard" (Radio Excellence).

---

## 1. The Design Pivot: "Modular Pro"
Spotify uses a "Side-Rail / Main / Utility" layout. Radio automation (Selector/WideOrbit) often uses a **Modular Dashboard** look that keeps editing and playout in immediate reach.

### THE HYBRID WORKSTATION AXIOM:
> **"Library Curation is a Live Action."** 
> Edits to the database should not require jumping through hoops or opening modal windows. If a track is selected, the tools to fix it must be one click away in a permanent side-car.

### THE DJ-MODE MANDATE:
> **"The Now and the Next govern the screen."**
> Search must deliver results in under 60 seconds (Sub-Minute Search). The player must show Cues and Hooks as first-class visual data.

### THE SHELL MANDATE:
> **"The Frame is part of the Tool."**
> To maximize immersion and space, the app moves to a Frameless Window. Custom controls for Minimize/Close and custom Title Bar dragging are required.

---

### A. Layout Rearrangement (The Wireframe)
*   **The Problem**: Vertical space is at a premium. Standard OS title bars are wasted space.
*   **The Shift**: We are moving to an **Integrated Workspace** with a dynamic "Curtain" soundboard, sliding drawers, and a Frameless Shell.
*   **Historical Log (Slide-out)**: A secondary left-side drawer that can slide out to show recently played songs (The "As Played" Log) for quick verification of what played 20+ minutes ago.


```text
+-------------------------------------------------------------+
| [LOGO]       [SEARCH BAR (Center-Balanced)]       [SETTINGS]|
+----------+----------------------------------------+----------+
|          | ( ALL ) ( MUS ) ( JIN ) ( COM ) ( SP ) | [LOAD    |
| [JINGLES +========================================|   LOG]   |
|  TRIGGER]|   <--  THE OVERHEAD BAY (Jingles)  --> |  RIGHT   |
|          |   [  (Slides down over the Stage)    ] | CHANNEL  |
|  CAT-    |                                        |          |
|  ALOG    |          THE STAGE (Library)           | (LOG or  |
|          |   [  Blade-Edge Grid / High Density ]  |  EDITOR) |
+----------+----------------------------------------+----------+
|            THE MASTER DECK               |                  |
| [NOW PLAYING]     [   BIG   ]   [TIMERS] |                  |
| [   COVER   ]     [ CONTROLS]   [FADER ] |                  |
+-------------------+----------------------+------------------+
```

*   **Load Log (The Playlist Trigger)**: A dedicated button at the top of the **Right Channel** to open the playlist/block picker. This allows transitioning from a dynamic library search back to a structured broadcast log instantly.
*   **Shorthand Integrated Tabs**: Using `MUS`, `JIN`, `COM`, `SP ` level with the library header to recover ~40px.
*   **The Overhead Bay (The Curtain)**: A top-down sliding soundboard. It covers the Stage when triggered, preserving the Live Deck and Log visibility. 
*   **The Dynamic Right-Channel (The Two States)**:
    1.  **Playout Focus (High-Fidelity Log)**: 100% height. Shows ~10 upcoming tracks in high detail: **Album Art**, **Duration**, **Cue Points**, and **Sweeper Info**.
    2.  **Surgical Focus (Editor Mode)**: The **Inspector (Editor)** takes the "Bulk" of the space. The Playlist minimizes to the bottom as a **Mini-Log**, showing only the next 3 tracks with simplified info (Title, Artist, Duration).

---

## 2. Component Design Specs (The "Pro" Look)

### B. The Library Table (High-Density Grid)
*   **Grid Style**: 
    *   Remove all vertical lines.
    *   Keep horizontal lines very subtle (1px, `#222`).
    *   Row Height: Set to fixed `28px` or `24px` for maximum visibility.
*   **Color Coding**:
    *   Implement **Content-Type Tinting**:
        *   `Music`: Default (`#1E1E1E`)
        *   `Jingles`: Subtle Purple Tint (`#251B2E`)
        *   `Commercials`: Subtle Green Tint (`#1B2E1B`)
        *   `Speech`: Subtle Grey Tint (`#252525`)
*   **Status Indicators**:
    *   No more standard checkboxes for "Done". Replace with **Small LED Indicators** (Colored dots or thin status bars on the left edge of the row).

### C. The Tab Bar (The "Pill" Paradigm)
*   Convert standard `QTabBar` to a custom-styled sequence of `QPushButton` pills.
*   **Active State**: High-contrast border or background (e.g., Neon Blue or Lime Green).

### D. The Master Deck (The Pulse)
*   **Visibility**: Tallest component (approx 20% height).
*   **Waveform/Progress**: Must show markers for `Intro`, `Hook`, and `Outro`.
*   **Log (Playlist)**: Integrated mini-table for reordering the upcoming 10 tracks.

### E. The Sub-Minute Search (The Catalog)
*   **Multi-Field Velocity**: The UI must support rapid toggling of multiple filters (e.g. Genre:Pop + Year:1990s) without reloading the entire model from scratch where possible.
*   **Decade Filtering**: Add shorthand decade filters (90s, 00s, 10s) to the Filter Sidebar to speed up broad searches.

### F. The Overhead Bay (The Curtain)
*   **Interaction**: Top-down sliding overlay. Anchored to the top-left of the Stage.
*   **Content**: 24-slot "QuickCart" Grid (6x4).
*   **Overlay Logic**: Uses a slight transparency/shadow to distinguish from the library rows below.

### G. The Frameless Shell (WORKSTATION MANDATE)
To achieve maximum immersion and pixel-perfect layouts, Gosling2 uses a `FramelessWindowHint` shell. This requires re-implementing standard OS behaviors:

1.  **Draggable Region**: The entire `CustomTitleBar` (GOSLING // WORKSTATION logo + search background) acts as the drag handle.
2.  **Custom System Controls**: 
    *   `MinimizeButton`: (`showMinimized`)
    *   `MaximizeButton`: (`showMaximized`/`showNormal` toggle)
    *   `CloseButton`: Emergeny red hover effect; triggers full app cleanup.
3.  **Double-Click to Toggle**: The Title Bar captures `mouseDoubleClickEvent` to toggle Maximize/Restore states.
4.  **Manual Resize Grip**: A custom `QSizeGrip` is positioned in the bottom-right corner of the content area, styled as a diagonal triangle handle.
5.  **Global Search Strip**: The search box is hosted in the Title Bar to satisfy the "Vertical Rescue" protocol, communicating with the `LibraryWidget` via signals.

---

## 3. The "Staged" Documentation Protocol
To ensure continuity across sessions:
1.  **CSS Variable Source**: Define all colors and sizes in `src/resources/theme.qss` FIRST.
2.  **Yellberus Integration**: Any new status field (e.g., Bitrate, Sample Rate) MUST be added to the Field Registry first.
3.  **UI Testing**: Use `conftest.py` fixtures to verify that layout changes don't break the resizing logic.

---

## 4. Work Order (UI Refinement)
- [x] **Gridless Stylesheet**: `theme.qss` updated with Blade-Edge variables. (DONE)
- [x] **Frameless Prototype**: Custom title bar + logo/search strip. (DONE)
- [x] **Tab-to-Pill Conversion**: Refactor `LibraryWidget` tabs. (DONE)
- [x] **Vertical Rescue**: Consolidate header elements and move search to Title Bar. (DONE)
- [x] **Historical Log (Slide-Out)**: Implement left-hand drawer for session history. (DONE)
- [x] **Jingle Bay (The Curtain)**: Implement top-down sliding grid panel. (DONE)
- [x] **Transport Polish**: Fusion styling, ghost-busting, and layout logic. (DONE)
