---
tags:
  - layer/ui
  - status/done
  - type/design
links:
  - "[[PROPOSAL_UX_STYLING]]"
---
# UX Design Brainstorm: The "Gosling" Experience

## Overview
This document serves as a "parking lot" for high-level UX/UI ideas to be explored once the core Registry and Editor logic are stable.

## 1. The "Glassmorphism" Implementation Strategy
Since we are using **PyQt6**, we need to weigh visual fidelity against performance.
- **Level 1 (Safe):** Semi-transparent QSS (rgba backgrounds) + high-contrast borders. Zero performance hit.
- **Level 2 (Polished):** Simulated blur using a static frosted-glass texture overlaid on the background.
- **Level 3 (Hardcore):** Win32 API calls for native Windows 11 Acrylic/Mica effects.
- **Question for later:** Do we value "Pure Cross-Platform" or "Deep Windows Integration"?

## 2. Interactive States & Micro-animations
How does the app *feel* when you move data around?
- **The "Snap":** When dragging a song into an Album or Genre tree, provide a subtle haptic-style visual pulse (scale transform) on the target.
- **The "Breeze":** Smooth sliding animations for the Metadata Side Panel (Opening from 0px to 300px width).
- **The "Sync Pulse":** When a background check finds a discrepancy, the "Out of Sync" red dot shouldn't just appear—it should fade in with a subtle glow.

## 3. Keyboard-First "Power User" Flow
Librarians and Radio DJs hate using the mouse for 5,000 files.
- **Shortcut Language:**
    - `Ctrl + E`: Open Editor Panel.
    - `Tab / Shift+Tab`: Cycles through staging fields.
    - `Ctrl + S`: Commit Staged Changes to DB.
    - `Ctrl + Shift + S`: Commit to DB AND Export to ID3 immediately.
- **Command Palette:** `Ctrl + K` to open a search-style bar where you can type commands: `> add genre Jazz`, `> set bpm 124`.

## 4. Visualizing Relationships
How do we show the "Hierarchy" in the UI?
- **The "Breadcrumb" Header:** Instead of just "Publisher", the editor shows `Universal > Island > Def Jam`. Clicking any part of the breadcrumb centers the library on that level.
- **The "Junction List":** If a song is on 3 albums, show them as "Chips" or "Tags" in the editor, rather than a single text block.

## 5. Audio-Visual Feedback
- **Waveform Editor Integration:** Should the Metadata Editor show a small, non-interactive waveform of the track for quick visual BPM/Peak verification?
- **Audition Mode:** A "Quick-Play" button directly next to the Artist/Title fields so you can hear the song while editing to verify the info.

---
*Note: These are high-level UX targets. Do not implement until the Field Registry is functionally complete.*
